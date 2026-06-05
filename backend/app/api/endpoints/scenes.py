import os
import shutil
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db
from app.models import Scene
from app.schemas import SceneResponse, SceneCreate, SceneUpdate, SceneQueryRequest, SceneQueryResponse
from app.services.document import get_document_chunks
from app.services.rag import add_documents_to_scene, query_scene_knowledge, clear_scene_knowledge

router = APIRouter()

@router.get("/", response_model=List[SceneResponse])
def read_scenes(db: Session = Depends(get_db)):
    """
    获取所有已注册的练习场景列表（包含默认场景与用户自定义场景）
    """
    return db.query(Scene).all()

@router.get("/{scene_id}", response_model=SceneResponse)
def read_scene(scene_id: str, db: Session = Depends(get_db)):
    """
    根据场景 ID 获取单个场景的详细参数配置与 RAG 文档元数据
    """
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"场景 '{scene_id}' 未找到"
        )
    return scene

@router.post("/", response_model=SceneResponse, status_code=status.HTTP_201_CREATED)
def create_scene(scene_in: SceneCreate, db: Session = Depends(get_db)):
    """
    创建全新的自定义口语对话场景，支持配置系统 Prompt 和默认参数
    """
    existing = db.query(Scene).filter(Scene.id == scene_in.id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ID 为 '{scene_in.id}' 的场景已存在"
        )
    
    scene = Scene(
        id=scene_in.id,
        name=scene_in.name,
        description=scene_in.description,
        category=scene_in.category,
        default_params=scene_in.default_params,
        system_prompt=scene_in.system_prompt,
        rag_metadata=[]
    )
    db.add(scene)
    db.commit()
    db.refresh(scene)
    return scene

@router.put("/{scene_id}", response_model=SceneResponse)
def update_scene(scene_id: str, scene_in: SceneUpdate, db: Session = Depends(get_db)):
    """
    编辑修改已有场景的参数设置（如性格、天气、限定条件）或更新 RAG 知识库配置
    """
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"场景 '{scene_id}' 未找到"
        )
    
    # 提取修改数据
    update_data = scene_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(scene, field, value)
        
    db.commit()
    db.refresh(scene)
    return scene


@router.post("/{scene_id}/upload", response_model=SceneResponse)
def upload_scene_document(
    scene_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    接收用户上传的 PDF/TXT/MD 场景文档，解析、切片并录入本地 RAG 知识库，同步更新场景文档元数据。
    """
    # 验证场景是否存在
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"场景 '{scene_id}' 不存在"
        )

    # 验证文件类型
    filename = file.filename
    _, ext = os.path.splitext(filename.lower())
    if ext not in [".pdf", ".txt", ".md", ".markdown"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件格式 '{ext}'。请上传 PDF、TXT 或 Markdown 格式文档。"
        )

    # 创建临时上传目录，写入文件
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    temp_dir = os.path.join(backend_dir, "static", "rag", "temp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, filename)

    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 提取并分块
        chunks = get_document_chunks(temp_file_path)
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未能从上传的文档中解析提取到有效文本内容。"
            )

        # 录入 RAG 库
        add_documents_to_scene(scene_id, chunks)

        # 更新元数据。注意 rag_metadata 可能是 None
        current_metadata = list(scene.rag_metadata) if scene.rag_metadata else []
        
        # 避免重复记录相同文件名的元数据（如果已存在，则先过滤掉旧记录）
        current_metadata = [item for item in current_metadata if item.get("filename") != filename]
        
        # 追加新上传文件元数据
        current_metadata.append({
            "filename": filename,
            "content_type": file.content_type,
            "chunk_count": len(chunks),
            "uploaded_at": datetime.utcnow().isoformat()
        })
        
        # 更新数据库
        scene.rag_metadata = current_metadata
        db.commit()
        db.refresh(scene)

        return scene

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理文档失败: {str(e)}"
        )
    finally:
        # 清理临时物理文件
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass


@router.delete("/{scene_id}/documents", response_model=SceneResponse)
def clear_scene_documents(scene_id: str, db: Session = Depends(get_db)):
    """
    清除指定场景的本地 RAG 知识库文件、FAISS 索引并清空场景的文档元数据。
    """
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"场景 '{scene_id}' 未找到"
        )

    # 物理清理 RAG 本地索引和文件
    clear_scene_knowledge(scene_id)

    # 清空数据库元数据
    scene.rag_metadata = []
    db.commit()
    db.refresh(scene)

    return scene


@router.post("/{scene_id}/query", response_model=SceneQueryResponse)
def query_scene_rag(scene_id: str, req: SceneQueryRequest, db: Session = Depends(get_db)):
    """
    语义检索测试端点：根据用户提问，在当前场景知识库中检索并匹配最相关的 Top-K 分块（用于调试验证）。
    """
    # 验证场景是否存在
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"场景 '{scene_id}' 未找到"
        )

    # 查询匹配的分块
    matched_chunks = query_scene_knowledge(scene_id, req.query, req.top_k)

    return SceneQueryResponse(
        scene_id=scene_id,
        query=req.query,
        results=matched_chunks
    )

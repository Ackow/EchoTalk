import os
import shutil
import io
import json
import zipfile
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db
from app.models import Scene, DialogueHistory
from app.schemas import SceneResponse, SceneCreate, SceneUpdate, SceneQueryRequest, SceneQueryResponse
from app.core.config import settings
from app.services.document import get_document_chunks
from app.services.rag import add_documents_to_scene, query_scene_knowledge, clear_scene_knowledge

router = APIRouter()

import time

def generate_and_upload_greeting_audio(scene_id: str, greeting_text: str) -> str:
    """
    通用打招呼语音合成上传函数：生成 edge-tts 神经网络语音并托管上传
    """
    if not greeting_text:
        return None
    filename = f"scene_greeting_{scene_id}_{int(time.time())}.mp3"
    temp_dir = settings.static_audio_dir
    os.makedirs(temp_dir, exist_ok=True)
    local_path = os.path.join(temp_dir, filename)
    
    audio_url = None
    try:
        from app.services.tts import text_to_speech
        from app.services.storage import upload_audio_to_kodo
        text_to_speech(greeting_text, local_path)
        audio_url = upload_audio_to_kodo(local_path, filename)
        return audio_url
    except Exception as e:
        print(f"[预生成问候语异常] 场景 {scene_id} 生成问候语语音失败: {e}")
        return None
    finally:
        # 清理物理本地冗余
        if audio_url and "static/audio" not in audio_url:
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                except Exception:
                    pass

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
    
    # 预合成打招呼语音
    greeting_audio_url = generate_and_upload_greeting_audio(scene_in.id, scene_in.greeting_text)

    scene = Scene(
        id=scene_in.id,
        name=scene_in.name,
        description=scene_in.description,
        category=scene_in.category,
        default_params=scene_in.default_params,
        system_prompt=scene_in.system_prompt,
        greeting_text=scene_in.greeting_text,
        greeting_audio_url=greeting_audio_url,
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
    
    # 如果修改数据中包含 greeting_text 且有变动，则重新预合成打招呼语音
    if "greeting_text" in update_data and update_data["greeting_text"] != scene.greeting_text:
        new_greeting = update_data["greeting_text"]
        new_audio_url = generate_and_upload_greeting_audio(scene_id, new_greeting)
        update_data["greeting_audio_url"] = new_audio_url
        
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
    temp_dir = settings.static_rag_temp_dir
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


@router.get("/{scene_id}/export")
def export_scene(scene_id: str, db: Session = Depends(get_db)):
    """
    导出场景：将该场景的所有配置参数（包含新设定的问候语）以及其在 static/rag/indices/ 下的 RAG 向量索引文件打包为 .zip 压缩流返回下载。
    """
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"场景 '{scene_id}' 未找到"
        )
        
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # 1. 写入场景基本配置文件 scene_config.json
        scene_config = {
            "id": scene.id,
            "name": scene.name,
            "description": scene.description,
            "category": scene.category,
            "default_params": scene.default_params or {},
            "system_prompt": scene.system_prompt,
            "greeting_text": scene.greeting_text,
            "rag_metadata": scene.rag_metadata or []
        }
        zip_file.writestr("scene_config.json", json.dumps(scene_config, indent=4, ensure_ascii=False))
        
        # 2. 写入关联的 RAG 向量索引物理文件 (f"{scene_id}.index" 和 f"{scene_id}.json")
        indices_dir = settings.static_rag_indices_dir
        
        index_file = os.path.join(indices_dir, f"{scene_id}.index")
        json_file = os.path.join(indices_dir, f"{scene_id}.json")
        
        if os.path.exists(index_file):
            zip_file.write(index_file, f"{scene_id}.index")
        if os.path.exists(json_file):
            zip_file.write(json_file, f"{scene_id}.json")
            
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=scene_{scene_id}.zip"}
    )


@router.post("/import", response_model=SceneResponse, status_code=status.HTTP_201_CREATED)
def import_scene(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    导入场景：上传导出的场景 .zip 包，自动还原数据库配置并写入 RAG 本地向量索引（支持覆盖更新）。
    """
    if not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请上传有效的场景 .zip 压缩文件包"
        )
        
    try:
        zip_contents = file.file.read()
        zip_buffer = io.BytesIO(zip_contents)
        
        with zipfile.ZipFile(zip_buffer, "r") as zip_file:
            # 1. 验证配置文件 scene_config.json
            if "scene_config.json" not in zip_file.namelist():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="场景压缩包中缺少必要的 scene_config.json 配置文件"
                )
                
            config_bytes = zip_file.read("scene_config.json")
            scene_config = json.loads(config_bytes.decode("utf-8"))
            
            scene_id = scene_config.get("id")
            if not scene_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="scene_config.json 中缺失场景 id"
                )
                
            # 2. 写入或覆盖数据库记录
            scene = db.query(Scene).filter(Scene.id == scene_id).first()
            
            greeting_text = scene_config.get("greeting_text", "Hello! Let's start practicing.")
            
            if not scene:
                # 预合成打招呼语音
                greeting_audio_url = generate_and_upload_greeting_audio(scene_id, greeting_text)
                
                scene = Scene(
                    id=scene_id,
                    name=scene_config.get("name", scene_id),
                    description=scene_config.get("description", ""),
                    category=scene_config.get("category", "custom"),
                    default_params=scene_config.get("default_params", {}),
                    system_prompt=scene_config.get("system_prompt", ""),
                    greeting_text=greeting_text,
                    greeting_audio_url=greeting_audio_url,
                    rag_metadata=scene_config.get("rag_metadata", [])
                )
                db.add(scene)
            else:
                scene.name = scene_config.get("name", scene.name)
                scene.description = scene_config.get("description", scene.description)
                scene.category = scene_config.get("category", scene.category)
                scene.default_params = scene_config.get("default_params", scene.default_params)
                scene.system_prompt = scene_config.get("system_prompt", scene.system_prompt)
                
                # 如果问候语改变或缺少音频地址，则重新预合成
                old_greeting = scene.greeting_text
                scene.greeting_text = greeting_text
                if old_greeting != greeting_text or not scene.greeting_audio_url:
                    scene.greeting_audio_url = generate_and_upload_greeting_audio(scene_id, greeting_text)
                    
                scene.rag_metadata = scene_config.get("rag_metadata", scene.rag_metadata or [])
                
            # 3. 解压并写入对应的 RAG 向量物理索引文件
            indices_dir = settings.static_rag_indices_dir
            os.makedirs(indices_dir, exist_ok=True)
            
            index_name = f"{scene_id}.index"
            json_name = f"{scene_id}.json"
            
            if index_name in zip_file.namelist():
                index_bytes = zip_file.read(index_name)
                with open(os.path.join(indices_dir, index_name), "wb") as f:
                    f.write(index_bytes)
                    
            if json_name in zip_file.namelist():
                json_bytes = zip_file.read(json_name)
                with open(os.path.join(indices_dir, json_name), "wb") as f:
                    f.write(json_bytes)
                    
            db.commit()
            db.refresh(scene)
            
            return scene
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导入场景包发生异常: {str(e)}"
        )


@router.delete("/{scene_id}", status_code=status.HTTP_200_OK)
def delete_scene(scene_id: str, db: Session = Depends(get_db)):
    """
    删除场景：彻底删除指定场景的数据库记录、关联的练习历史会话与对话明细轮次，并物理清理其 RAG 知识库索引与物理文档。
    """
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"场景 '{scene_id}' 未找到"
        )
        
    # 1. 物理清理该场景的本地 RAG 知识库和向量索引物理文件
    try:
        clear_scene_knowledge(scene_id)
    except Exception as e:
        print(f"[RAG 物理清理异常] 场景 '{scene_id}' 的向量文件清理失败: {e}")
        
    # 2. 级联删除与该场景关联的历史会话纪录
    histories = db.query(DialogueHistory).filter(DialogueHistory.scene_id == scene_id).all()
    for history in histories:
        # 由于 models.py 里对 turns 设置了 cascade="all, delete-orphan"，
        # 直接删除 history 记录会级联清空其下的所有 turns 对话明细
        db.delete(history)
        
    # 3. 删除场景本身
    db.delete(scene)
    db.commit()
    
    return {"message": f"场景 '{scene_id}' 及其所有关联练习历史和 RAG 知识库已成功彻底清除"}

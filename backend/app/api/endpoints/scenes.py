from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db
from app.models import Scene
from app.schemas import SceneResponse, SceneCreate, SceneUpdate

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

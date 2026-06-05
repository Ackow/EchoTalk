from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db
from app.models import DialogueHistory, Scene, User
from app.schemas import DialogueHistoryResponse, DialogueStartRequest

router = APIRouter()

@router.post("/start", response_model=DialogueHistoryResponse, status_code=status.HTTP_201_CREATED)
def start_dialogue(req: DialogueStartRequest, db: Session = Depends(get_db)):
    """
    启动一轮新的口语交互练习会话。如果指定了 custom_params，将覆盖默认场景的属性配置。
    """
    # 验证场景与用户是否存在
    scene = db.query(Scene).filter(Scene.id == req.scene_id).first()
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"场景 '{req.scene_id}' 不存在"
        )
        
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 ID '{req.user_id}' 未注册"
        )

    # 创建会话历史记录
    history = DialogueHistory(
        user_id=req.user_id,
        scene_id=req.scene_id,
        turns=[]
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return history

@router.get("/{history_id}", response_model=DialogueHistoryResponse)
def read_dialogue(history_id: int, db: Session = Depends(get_db)):
    """
    查询指定会话的完整历史详情，包括每一轮的语音 URL、发音评分及语法纠错结果。
    """
    history = db.query(DialogueHistory).filter(DialogueHistory.id == history_id).first()
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话记录 ID '{history_id}' 未找到"
        )
    return history

@router.get("/", response_model=List[DialogueHistoryResponse])
def list_dialogues(user_id: int, db: Session = Depends(get_db)):
    """
    获取指定用户的所有练习会话历史记录列表，按开始时间倒序排列
    """
    return db.query(DialogueHistory)\
             .filter(DialogueHistory.user_id == user_id)\
             .order_by(DialogueHistory.start_time.desc())\
             .all()

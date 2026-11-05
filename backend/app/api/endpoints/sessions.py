"""首期文字练习接口，均要求登录且按用户隔离。"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.session import CreateSession, SubmitTurn
from app.schemas.tts import VoiceOptions
from app.services import session_service
from app.services import greeting_audio_service

router = APIRouter(prefix="/sessions", tags=["对话练习"])


@router.post("", status_code=201)
def create_session(payload: CreateSession, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """为当前用户创建练习会话，返回开场白和初始任务状态。"""
    return session_service.create_session(db, user, payload.scene_id)


@router.get("/{session_id}")
def get_session(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """恢复当前用户的一条练习会话及其公开轮次。"""
    return session_service.get_session(db, user.id, session_id)


@router.post("/{session_id}/turns")
def submit_turn(session_id: str, payload: SubmitTurn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """提交文字轮次并返回 Agent 回复；重试时复用相同 request_id。"""
    return session_service.run_turn(db, user.id, session_id, payload.request_id, payload.text)


@router.get("/{session_id}/greeting-audio")
async def greeting_audio(
    session_id: str,
    options: Annotated[VoiceOptions, Query()],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """读取本人的会话问候音频，缓存命中时直接读取文件。"""
    row = session_service.owned_session(db, session_id, user.id)
    text = row.greeting
    db.rollback()  # 音频合成期间不持有身份查询与会话读取事务。
    path = await greeting_audio_service.get_audio(text, options.voice_style, options.speech_rate)
    return FileResponse(path, media_type="audio/mpeg", headers={"Cache-Control": "private, max-age=86400"})

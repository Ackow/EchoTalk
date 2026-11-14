"""首期文字练习接口，均要求登录且按用户隔离。"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.models import PracticeTurn
from sqlalchemy import select
from app.core.errors import AppError
from app.schemas.session import CreateSession, SubmitTurn, SubmitTurnStream
from app.schemas.tts import VoiceOptions
from app.services import analytics_service
from app.services import session_service
from app.services import greeting_audio_service

router = APIRouter(prefix="/sessions", tags=["对话练习"])


@router.post("", status_code=201)
def create_session(payload: CreateSession, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """为当前用户创建练习会话，返回开场白和初始任务状态。"""
    return session_service.create_session(db, user, payload.scene_id)


@router.get("")
def list_sessions(
    scene_id: str | None = Query(default=None, min_length=2, max_length=50),
    status: str | None = Query(default=None, pattern="^(active|finished)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """分页读取当前用户的历史练习记录，附带全局统计。"""
    return session_service.list_sessions(db, user.id, scene_id=scene_id, status=status, page=page, page_size=page_size)


@router.get("/latest")
def latest_session(scene_id: str = Query(min_length=2, max_length=50), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"session": session_service.latest_session(db, user, scene_id)}


@router.get("/analytics")
def get_analytics(
    days: int = Query(default=30, ge=0, le=365),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """汇总当前用户在指定时间范围内的成长分析数据（发音雷达、趋势、错因、场景分布与薄弱词）。"""
    return analytics_service.get_growth_analytics(db, user.id, days=days)


@router.get("/{session_id}")
def get_session(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """恢复当前用户的一条练习会话及其公开轮次。"""
    return session_service.get_session(db, user.id, session_id)


@router.get("/{session_id}/report")
def get_session_report(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """生成本场练习的多维评测报告（讯飞发音多维分 + 语速 + 逐词表现 + 语法纠错 + 目标完成度）。"""
    return session_service.get_session_report(db, user.id, session_id)


@router.post("/{session_id}/turns")
def submit_turn(session_id: str, payload: SubmitTurn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """提交文字轮次并返回 Agent 回复；重试时复用相同 request_id。"""
    return session_service.run_turn(db, user.id, session_id, payload.request_id, payload.text)


@router.post("/{session_id}/turns/stream")
async def submit_turn_stream(
    session_id: str,
    payload: SubmitTurnStream,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """流式提交文字轮次（SSE）：增量返回文本与按句合成的 MP3 音频分段。"""
    bind = db.get_bind()
    db.rollback()
    return StreamingResponse(
        session_service.stream_turn(
            bind,
            user.id,
            session_id,
            payload.request_id,
            payload.text,
            voice_style=payload.voice_style,
            include_audio=payload.include_audio,
            audio_token=payload.audio_token,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{session_id}/suggest-reply")
async def suggest_reply(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """根据当前对话上下文与训练目标，生成 AI 参考回复建议。"""
    return await session_service.suggest_reply(db, user.id, session_id)


class SessionActionIn(BaseModel):
    action: str = Field(min_length=1, max_length=32)
    payload: dict = Field(default_factory=dict)


@router.post("/{session_id}/action")
def session_action(session_id: str, payload: SessionActionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """执行场景交互动作（如咖啡厅结账付款、确认结束卡片）。"""
    return session_service.apply_session_action(db, user.id, session_id, payload.action, payload.payload)


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


@router.get("/{session_id}/turns/{turn_id}/audio")
async def turn_audio(session_id: str, turn_id: str, options: Annotated[VoiceOptions, Query()], user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """只按已保存的回复生成音频，且先验证会话和轮次归属。"""
    session_service.owned_session(db, session_id, user.id)
    turn = db.scalar(select(PracticeTurn).where(PracticeTurn.id == turn_id, PracticeTurn.session_id == session_id))
    if turn is None:
        raise AppError("对话记录不存在", code="TURN_NOT_FOUND", status_code=404)
    text = turn.response_json["text"]
    owner_id = user.id
    db.rollback()
    from app.services import practice_audio_service
    path = await practice_audio_service.get_audio(owner_id, session_id, turn_id, text, options.voice_style, options.speech_rate)
    return FileResponse(path, media_type="audio/mpeg", headers={"Cache-Control": "private, max-age=86400"})


@router.get("/{session_id}/turns/{turn_id}/user-audio")
def user_turn_audio(session_id: str, turn_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """读取用户自己在某一轮次提交的录音 WAV（仅本人会话可访问）。"""
    session_service.owned_session(db, session_id, user.id)
    turn = db.scalar(select(PracticeTurn).where(PracticeTurn.id == turn_id, PracticeTurn.session_id == session_id))
    if turn is None:
        raise AppError("对话记录不存在", code="TURN_NOT_FOUND", status_code=404)
    path = session_service._user_audio_path(turn_id)
    if not path.exists():
        raise AppError("该轮次未保留用户录音", code="USER_AUDIO_NOT_FOUND", status_code=404)
    return FileResponse(path, media_type="audio/wav", headers={"Cache-Control": "private, max-age=86400"})
    return FileResponse(path, media_type="audio/mpeg", headers={"Cache-Control": "private, no-store"})

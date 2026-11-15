"""多角色辩论接口：话题列表、创建会话、提交发言（含 AI 辩手与评委协同）、结束裁决。"""
from fastapi import APIRouter, Depends, File, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_optional_user
from app.core.errors import AppError
from app.models import User
from app.services import debate_service

router = APIRouter(prefix="/debate", tags=["多角色对话"])


class CreateDebateIn(BaseModel):
    topic_id: str = Field(min_length=2, max_length=64)
    user_side: str = Field(default="pro", pattern="^(pro|con)$")
    difficulty_level: str = Field(default="balanced", pattern="^(supportive|balanced|sharp)$")


class SubmitDebateTurnIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    is_voice: bool = False
    duration: int | None = Field(default=None, ge=1, le=300)


class DebateTopicGenerateIn(BaseModel):
    idea: str = Field(min_length=2, max_length=300)
    sceneType: str = Field(default="debate", pattern="^(debate|panel)$")


class DebateRoleIn(BaseModel):
    id: str = Field(default="", max_length=32)
    roleType: str = Field(default="interviewer", pattern="^(moderator|interviewer|opponent|judge)$")
    name: str = Field(min_length=1, max_length=64)
    title: str = Field(default="", max_length=64)
    persona: str = Field(default="", max_length=800)
    voice: str = Field(default="sonia", max_length=32)
    avatarId: str = Field(default="sarah_2d", max_length=32)


class DebateStageIn(BaseModel):
    id: str = Field(default="", max_length=32)
    shortTag: str = Field(default="", max_length=16)
    label: str = Field(min_length=1, max_length=48)


class DebateTopicIn(BaseModel):
    sceneType: str = Field(default="debate", pattern="^(debate|panel)$")
    userRoleLabel: str = Field(default="候选人 / 主讲人", max_length=64)
    titleZh: str = Field(min_length=2, max_length=180)
    motionEn: str = Field(min_length=4, max_length=1000)
    category: str = Field(default="tech", pattern="^(tech|workplace|education|society)$")
    difficulty: str = Field(default="intermediate", pattern="^(beginner|intermediate|advanced)$")
    duration: str = Field(default="8 分钟", max_length=32)
    proSummary: str = Field(default="", max_length=500)
    conSummary: str = Field(default="", max_length=500)
    backgroundContext: str = Field(default="", max_length=1500)
    keyExpressions: list[str] = Field(default_factory=list)
    defaultStyle: str = Field(default="balanced", pattern="^(supportive|balanced|sharp)$")
    opponentName: str = Field(default="Sonia", max_length=64)
    opponentTitle: str = Field(default="对手辩手", max_length=64)
    opponentPersona: str = Field(default="", max_length=800)
    opponentVoice: str = Field(default="sonia", max_length=32)
    opponentAvatarId: str = Field(default="sarah_2d", max_length=32)
    roles: list[DebateRoleIn] = Field(default_factory=list, max_length=4)
    stages: list[DebateStageIn] = Field(default_factory=list, max_length=6)
    knowledgeDocIds: list[int] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=lambda: ["search_knowledge", "rebuttal_hint", "judge_score"])


@router.get("/topics")
def list_debate_topics(
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """返回内置与本人自建的多角色对话场景列表。"""
    return {"items": debate_service.list_topics(db, user=user)}


@router.post("/topics/generate")
async def generate_debate_topic_draft(
    payload: DebateTopicGenerateIn,
    user: User = Depends(get_current_user),
):
    """根据一句想法由 AI 一键生成结构化多角色对话/辩论场景包草稿。"""
    return {"draft": await debate_service.generate_debate_topic_draft(payload.idea, scene_type=payload.sceneType)}


@router.post("/topics", status_code=201)
def create_debate_topic(
    payload: DebateTopicIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建自定义辩论话题。"""
    return {"topic": debate_service.create_debate_topic(db, user, payload.model_dump())}


@router.put("/topics/{topic_id}")
def update_debate_topic(
    topic_id: str,
    payload: DebateTopicIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新自定义或管理员管理的辩论话题。"""
    return {"topic": debate_service.update_debate_topic(db, user, topic_id, payload.model_dump())}


@router.delete("/topics/{topic_id}")
def delete_debate_topic(
    topic_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除自定义或管理员管理的辩论话题。"""
    debate_service.delete_debate_topic(db, user, topic_id)
    return {"ok": True}


@router.post("/topics/{topic_id}/cover", status_code=201)
async def upload_debate_cover(
    topic_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传辩论封面图（仅作者）：jpg / png / webp，上限 5 MB。"""
    relative = debate_service.set_debate_cover(db, user, topic_id, file.filename, await file.read())
    return {"cover_path": relative, "coverUrl": f"/api/v1/debate/topics/{topic_id}/cover"}


@router.get("/topics/{topic_id}/cover")
def get_debate_cover(topic_id: str, db: Session = Depends(get_db)):
    """读取辩论封面图（公开访问）。"""
    path = debate_service.get_debate_cover_file(db, topic_id)
    if path is None:
        raise AppError("辩论场景未设置封面", code="DEBATE_NO_COVER", status_code=404)
    return FileResponse(path)


@router.delete("/topics/{topic_id}/cover")
def remove_debate_cover(
    topic_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """移除辩论封面图（仅作者）。"""
    removed = debate_service.remove_debate_cover(db, user, topic_id)
    return {"removed": removed}


@router.post("/topics/{topic_id}/like")
def like_debate_topic(
    topic_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """切换辩题点赞状态。"""
    return debate_service.toggle_topic_reaction(db, user, topic_id, "like")


@router.post("/topics/{topic_id}/favorite")
def favorite_debate_topic(
    topic_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """切换辩题收藏状态。"""
    return debate_service.toggle_topic_reaction(db, user, topic_id, "favorite")


@router.post("/topics/{topic_id}/publish")
def publish_debate_topic(
    topic_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """发布自建辩题到社区。"""
    return {"topic": debate_service.set_topic_publish(db, user, topic_id, True)}


@router.post("/topics/{topic_id}/unpublish")
def unpublish_debate_topic(
    topic_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """取消辩题社区发布。"""
    return {"topic": debate_service.set_topic_publish(db, user, topic_id, False)}


@router.post("/topics/import", status_code=201)
async def import_debate_topic(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导入 .zip 或 .json 辩论包为个人辩题。"""
    raw = await file.read()
    return {"topic": debate_service.import_debate_topic_package(db, user, raw, file.filename or "")}


@router.get("/topics/{topic_id}/export")
def export_debate_topic(
    topic_id: str,
    db: Session = Depends(get_db),
):
    """导出辩题为 .zip 辩论包。"""
    zip_bytes = debate_service.export_debate_topic_zip(db, topic_id)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="echotalk_debate_{topic_id}.zip"'},
    )


@router.post("/topics/{topic_id}/duplicate", status_code=201)
def duplicate_debate_topic(
    topic_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """复制辩题为我的私有辩题。"""
    return {"topic": debate_service.duplicate_debate_topic(db, user, topic_id)}


@router.post("/sessions", status_code=201)
def create_debate_session(
    payload: CreateDebateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建一场多角色辩论并返回主持人开场。"""
    return debate_service.create_debate_session(
        db,
        user,
        topic_id=payload.topic_id,
        user_side=payload.user_side,
        difficulty_level=payload.difficulty_level,
    )


@router.get("/sessions/{session_id}")
def get_debate_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """恢复指定辩论会话与历史发言。"""
    return debate_service.get_debate_session(db, user.id, session_id)


@router.post("/sessions/{session_id}/turns")
async def submit_debate_turn(
    session_id: str,
    payload: SubmitDebateTurnIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """提交我方辩词，生成 AI 对手反驳、评委点评并沉淀复习表达。"""
    return await debate_service.submit_debate_turn(
        db,
        user,
        session_id=session_id,
        text=payload.text,
        is_voice=payload.is_voice,
        duration=payload.duration,
    )


@router.post("/sessions/{session_id}/suggest-reply")
async def suggest_debate_reply(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """根据当前辩题与对手最新发言，生成真实 AI 参考辩词建议。"""
    return await debate_service.suggest_debate_reply(db, user, session_id=session_id)


@router.post("/sessions/{session_id}/finish")
def finish_debate_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """结束辩论并生成最终裁决报告、发放 XP。"""
    return debate_service.finish_debate_session(db, user, session_id=session_id)

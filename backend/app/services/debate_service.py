"""多角色辩论服务：话题目录、AI 辩手/评委协同推演、评分雷达、复习沉淀与 XP 奖励。"""
import io
import json
import re
import uuid
import zipfile
from datetime import timedelta
from pathlib import Path
from typing import Any

import yaml

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.agents.model_gateway import create_chat_model
from app.core.errors import AppError
from app.core.timeutil import utcnow
from app.models import DebateSession, DebateTopic, DebateTurn, PersonalChunk, ReviewItem, User, UserXpState
from app.models.debate import DebateTopicReaction

_BUILTIN_COVER_DIRS = (
    Path(__file__).resolve().parent.parent / "content" / "debates" / "covers",
    Path(__file__).resolve().parent.parent / "content" / "scenes" / "covers",
)
_COVER_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def _builtin_cover_file(topic_id: str) -> Path | None:
    for cover_dir in _BUILTIN_COVER_DIRS:
        for ext in _COVER_EXTENSIONS:
            candidate = cover_dir / f"{topic_id}{ext}"
            if candidate.is_file():
                return candidate
    return None


STAGES = [
    {"id": "opening", "label": "开篇立论", "shortTag": "立论"},
    {"id": "cross", "label": "交叉质询", "shortTag": "质询"},
    {"id": "rebuttal", "label": "焦点攻防", "shortTag": "攻防"},
    {"id": "closing", "label": "总结裁决", "shortTag": "裁决"},
]

PANEL_STAGES = [
    {"id": "opening", "label": "自我陈述", "shortTag": "陈述"},
    {"id": "deep_dive", "label": "深度追问", "shortTag": "追问"},
    {"id": "pressure", "label": "压力挑战", "shortTag": "挑战"},
    {"id": "summary", "label": "委员会评估", "shortTag": "评估"},
]

DEFAULT_TOOLS = ["search_knowledge", "rebuttal_hint", "judge_score", "add_review_task"]


def _resolve_duration_turns(duration: str | None) -> int:
    """将场景时长文案映射为最大用户发言轮数（4 / 6 / 8）。"""
    m = re.search(r"(\d+)", str(duration or ""))
    if not m:
        return 6
    mins = int(m.group(1))
    if mins <= 6:
        return 4
    if mins <= 9:
        return 6
    return 8


def _resolve_topic_tools(topic: Any) -> list[str]:
    """解析启用工具列表；仅当字段缺失(None)时回退默认，显式 [] 则尊重禁用。"""
    if topic is None:
        return list(DEFAULT_TOOLS)
    raw = topic.get("tools") if isinstance(topic, dict) else getattr(topic, "tools_config", None)
    if raw is None:
        return list(DEFAULT_TOOLS)
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    return list(DEFAULT_TOOLS)


def resolve_topic_roles(topic: Any) -> list[dict]:
    """统一解析多角色名单（2–4 个），兼容旧版仅配置单一 opponent_* 的辩题。"""
    scene_type = (topic.get("sceneType") if isinstance(topic, dict) else getattr(topic, "scene_type", None)) or "debate"
    raw_roles = (topic.get("roles") if isinstance(topic, dict) else getattr(topic, "roles_config", None)) or []
    if isinstance(raw_roles, list) and raw_roles:
        cleaned: list[dict] = []
        seen_ids: set[str] = set()
        for idx, r in enumerate(raw_roles[:4]):
            if not isinstance(r, dict):
                continue
            rid = str(r.get("id") or f"role_{idx + 1}").strip()
            if rid in seen_ids:
                rid = f"{rid}_{idx + 1}"
            seen_ids.add(rid)
            default_rtype = "interviewer" if scene_type == "panel" else ("moderator" if idx == 0 else "opponent")
            cleaned.append({
                "id": rid,
                "roleType": str(r.get("roleType") or default_rtype).strip(),
                "name": str(r.get("name") or f"Role {idx + 1}").strip(),
                "title": str(r.get("title") or "").strip(),
                "persona": str(r.get("persona") or "").strip(),
                "voice": str(r.get("voice") or "sonia").strip(),
                "avatarId": str(r.get("avatarId") or "sarah_2d").strip(),
            })
        if cleaned:
            return cleaned

    opp_name = (topic.get("opponentName") if isinstance(topic, dict) else getattr(topic, "opponent_name", None)) or "Sonia"
    opp_title = (topic.get("opponentTitle") if isinstance(topic, dict) else getattr(topic, "opponent_title", None)) or "对手辩手"
    opp_persona = (topic.get("opponentPersona") if isinstance(topic, dict) else getattr(topic, "opponent_persona", None)) or ""
    opp_voice = (topic.get("opponentVoice") if isinstance(topic, dict) else getattr(topic, "opponent_voice", None)) or "sonia"
    opp_avatar = (topic.get("opponentAvatarId") if isinstance(topic, dict) else getattr(topic, "opponent_avatar_id", None)) or "sarah_2d"
    return [
        {
            "id": "moderator",
            "roleType": "moderator",
            "name": "Brian",
            "title": "主持人",
            "persona": "中立控场的主持人，引导双方围绕核心论点展开交锋并把控流程。",
            "voice": "brian",
            "avatarId": "david_2d",
        },
        {
            "id": "opponent",
            "roleType": "opponent",
            "name": opp_name,
            "title": opp_title,
            "persona": opp_persona,
            "voice": opp_voice,
            "avatarId": opp_avatar,
        },
        {
            "id": "judge",
            "roleType": "judge",
            "name": "Andrew",
            "title": "特邀评委",
            "persona": "关注论据严谨度与质询回应质量的专业评委。",
            "voice": "andrew",
            "avatarId": "leo_2d",
        },
    ]


def resolve_topic_stages(topic: Any) -> list[dict]:
    """解析流程阶段；优先使用场景自定义 stages，否则按模式返回默认四阶段。"""
    scene_type = (topic.get("sceneType") if isinstance(topic, dict) else getattr(topic, "scene_type", None)) or "debate"
    raw = (topic.get("stages") if isinstance(topic, dict) else getattr(topic, "stages_config", None)) or []
    if isinstance(raw, list) and raw:
        cleaned: list[dict] = []
        for idx, s in enumerate(raw[:6]):
            if not isinstance(s, dict):
                continue
            label = str(s.get("label") or "").strip()
            if not label:
                continue
            short_tag = str(s.get("shortTag") or label[:2]).strip()
            cleaned.append({
                "id": str(s.get("id") or f"stage_{idx + 1}").strip(),
                "label": label,
                "shortTag": short_tag,
            })
        if cleaned:
            return cleaned
    return [dict(x) for x in (PANEL_STAGES if scene_type == "panel" else STAGES)]

_BUILTIN_DEBATE_DIR = Path(__file__).resolve().parent.parent / "content" / "debates"


def _load_builtin_debate_topics() -> list[dict[str, Any]]:
    topics: list[dict[str, Any]] = []
    if not _BUILTIN_DEBATE_DIR.is_dir():
        return topics
    for path in sorted(_BUILTIN_DEBATE_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not data.get("id"):
            continue
        if not data.get("stages"):
            scene_type = data.get("sceneType") or "debate"
            data["stages"] = [dict(x) for x in (PANEL_STAGES if scene_type == "panel" else STAGES)]
        topics.append(data)
    return topics


DEBATE_TOPICS = _load_builtin_debate_topics()

_TOPIC_MAP = {t["id"]: t for t in DEBATE_TOPICS}


_CATEGORY_LABELS = {
    "tech": "科技伦理",
    "workplace": "职场文化",
    "education": "教育成长",
    "society": "社会生活",
}

_DIFFICULTY_LABELS = {
    "beginner": "入门",
    "intermediate": "进阶",
    "advanced": "挑战",
}


def ensure_debate_tables(db: Session) -> None:
    from app.core.migrations import ensure_debate_schema

    ensure_debate_schema(db.get_bind())
    _seed_builtin_topics(db)


def _seed_builtin_topics(db: Session) -> None:
    active_ids = {t["id"] for t in DEBATE_TOPICS}
    existing_map = {row.id: row for row in db.scalars(select(DebateTopic)).all()}
    changed = False
    for row_id, row in list(existing_map.items()):
        if row.is_builtin and row_id not in active_ids:
            db.delete(row)
            existing_map.pop(row_id, None)
            changed = True
    for t in DEBATE_TOPICS:
        row = existing_map.get(t["id"])
        if row is None:
            db.add(
                DebateTopic(
                    id=t["id"],
                    title_zh=t["titleZh"],
                    motion_en=t["motionEn"],
                    category=t["category"],
                    category_label=t["categoryLabel"],
                    difficulty=t["difficulty"],
                    difficulty_label=t["difficultyLabel"],
                    duration=t["duration"],
                    pro_summary=t["proSummary"],
                    con_summary=t["conSummary"],
                    background_context=t.get("backgroundContext", ""),
                    key_expressions=t.get("keyExpressions", []),
                    scene_type=t.get("sceneType", "debate"),
                    user_role_label=t.get("userRoleLabel", "候选人 / 主讲人"),
                    roles_config=t.get("roles", []),
                    stages_config=t.get("stages", []),
                    tools_config=list(t.get("tools") or DEFAULT_TOOLS),
                    opponent_name=t.get("opponentName", "Sonia"),
                    opponent_title=t.get("opponentTitle", "对手辩手"),
                    opponent_persona=t.get("opponentPersona", ""),
                    opponent_voice=t.get("opponentVoice", "sonia"),
                    opponent_avatar_id=t.get("opponentAvatarId", "sarah_2d"),
                    is_builtin=True,
                    owner_id=None,
                )
            )
            changed = True
        else:
            if not row.opponent_persona:
                row.background_context = t.get("backgroundContext", "")
                row.key_expressions = t.get("keyExpressions", [])
                row.opponent_name = t.get("opponentName", "Sonia")
                row.opponent_title = t.get("opponentTitle", "对手辩手")
                row.opponent_persona = t.get("opponentPersona", "")
                row.opponent_voice = t.get("opponentVoice", "sonia")
                row.opponent_avatar_id = t.get("opponentAvatarId", "sarah_2d")
                changed = True
            if t.get("sceneType") and getattr(row, "scene_type", "debate") != t.get("sceneType"):
                row.scene_type = t["sceneType"]
                changed = True
            if t.get("userRoleLabel") and not getattr(row, "user_role_label", None):
                row.user_role_label = t["userRoleLabel"]
                changed = True
            if t.get("roles") and not getattr(row, "roles_config", None):
                row.roles_config = t["roles"]
                changed = True
            if t.get("stages") and not getattr(row, "stages_config", None):
                row.stages_config = t["stages"]
                changed = True
            if not getattr(row, "tools_config", None):
                row.tools_config = list(t.get("tools") or DEFAULT_TOOLS)
                changed = True
    if changed:
        db.commit()


def _normalize_roles_input(raw_roles: list[dict] | None, scene_type: str) -> list[dict]:
    if not isinstance(raw_roles, list):
        return []
    cleaned: list[dict] = []
    seen: set[str] = set()
    for idx, r in enumerate(raw_roles[:4]):
        if not isinstance(r, dict):
            continue
        name = str(r.get("name") or "").strip()
        if not name:
            continue
        rid = str(r.get("id") or f"role_{idx + 1}").strip()
        if rid in seen:
            rid = f"{rid}_{idx + 1}"
        seen.add(rid)
        default_type = "interviewer" if scene_type == "panel" else ("moderator" if idx == 0 else "opponent")
        rtype = str(r.get("roleType") or default_type).strip()
        if rtype not in ("moderator", "interviewer", "opponent", "judge"):
            rtype = default_type
        cleaned.append({
            "id": rid,
            "roleType": rtype,
            "name": name,
            "title": str(r.get("title") or "").strip(),
            "persona": str(r.get("persona") or "").strip(),
            "voice": str(r.get("voice") or "sonia").strip(),
            "avatarId": str(r.get("avatarId") or "sarah_2d").strip(),
        })
    return cleaned


def _normalize_stages_input(raw_stages: list[dict] | None) -> list[dict]:
    if not isinstance(raw_stages, list):
        return []
    cleaned: list[dict] = []
    for idx, s in enumerate(raw_stages[:6]):
        if not isinstance(s, dict):
            continue
        label = str(s.get("label") or "").strip()
        if not label:
            continue
        short_tag = str(s.get("shortTag") or label[:2]).strip()
        cleaned.append({
            "id": str(s.get("id") or f"stage_{idx + 1}").strip(),
            "label": label,
            "shortTag": short_tag,
        })
    return cleaned


def _extract_primary_opponent(roles: list[dict], payload: dict) -> tuple[str, str, str, str, str]:
    primary = (
        next((r for r in roles if r.get("roleType") == "opponent"), None)
        or next((r for r in roles if r.get("roleType") == "interviewer"), None)
        or (roles[0] if roles else None)
    )
    if primary:
        return (
            primary.get("name") or "Sonia",
            primary.get("title") or "对手辩手",
            primary.get("persona") or "",
            primary.get("voice") or "sonia",
            primary.get("avatarId") or "sarah_2d",
        )
    return (
        (payload.get("opponentName") or "Sonia").strip(),
        (payload.get("opponentTitle") or "对手辩手").strip(),
        (payload.get("opponentPersona") or "").strip(),
        (payload.get("opponentVoice") or "sonia").strip(),
        (payload.get("opponentAvatarId") or "sarah_2d").strip(),
    )


def serialize_topic(
    topic: DebateTopic,
    user: User | None = None,
    *,
    author_name: str | None = None,
    liked: bool = False,
    favorited: bool = False,
    plays: int = 0,
) -> dict:
    is_admin = bool(user and getattr(user, "is_admin", False))
    is_mine = bool(user and not topic.is_builtin and topic.owner_id == user.id)
    can_manage = bool(user and not topic.is_builtin and (is_admin or is_mine))
    resolved_status = "published" if topic.is_builtin else (getattr(topic, "status", None) or "private")
    scene_type = getattr(topic, "scene_type", None) or "debate"
    if scene_type not in ("debate", "panel"):
        scene_type = "debate"
    tools = _resolve_topic_tools(topic)
    roles = resolve_topic_roles(topic)
    stages = resolve_topic_stages(topic)
    return {
        "id": topic.id,
        "sceneType": scene_type,
        "category": topic.category,
        "categoryLabel": topic.category_label,
        "difficulty": topic.difficulty,
        "difficultyLabel": topic.difficulty_label,
        "duration": topic.duration,
        "maxTurns": _resolve_duration_turns(topic.duration),
        "userRoleLabel": getattr(topic, "user_role_label", None) or ("候选人 / 主讲人" if scene_type == "panel" else "辩手"),
        "titleZh": topic.title_zh,
        "motionEn": topic.motion_en,
        "proSummary": topic.pro_summary,
        "conSummary": topic.con_summary,
        "backgroundContext": topic.background_context or "",
        "keyExpressions": topic.key_expressions or [],
        "defaultStyle": topic.default_style or "balanced",
        "opponentName": topic.opponent_name or "Sonia",
        "opponentTitle": topic.opponent_title or "对手辩手",
        "opponentPersona": topic.opponent_persona or "",
        "opponentVoice": topic.opponent_voice or "sonia",
        "opponentAvatarId": topic.opponent_avatar_id or "sarah_2d",
        "roles": roles,
        "stages": stages,
        "knowledgeDocIds": topic.knowledge_doc_ids or [],
        "coverUrl": (
            f"/api/debate/topics/{topic.id}/cover"
            if (getattr(topic, "cover_path", None) or _builtin_cover_file(topic.id))
            else ""
        ),
        "tools": tools,
        "status": resolved_status,
        "authorId": topic.owner_id,
        "authorName": "EchoTalk 官方" if topic.is_builtin else (author_name or "学习者"),
        "isMine": is_mine,
        "isBuiltin": bool(topic.is_builtin),
        "canManage": can_manage,
        "createdAt": topic.created_at.isoformat() if topic.created_at else "",
        "stats": {
            "likes": int(getattr(topic, "likes_count", 0) or 0),
            "favorites": int(getattr(topic, "favorites_count", 0) or 0),
            "plays": int(plays or 0),
            "liked": bool(liked),
            "favorited": bool(favorited),
        },
    }


def list_topics(db: Session, user: User | None = None) -> list[dict]:
    ensure_debate_tables(db)
    stmt = select(DebateTopic)
    if user is None:
        stmt = stmt.where(or_(DebateTopic.is_builtin.is_(True), DebateTopic.status == "published"))
    elif not getattr(user, "is_admin", False):
        stmt = stmt.where(
            or_(DebateTopic.is_builtin.is_(True), DebateTopic.owner_id == user.id, DebateTopic.status == "published")
        )
    rows = db.scalars(stmt.order_by(DebateTopic.is_builtin.desc(), DebateTopic.created_at.asc())).all()

    owner_ids = {row.owner_id for row in rows if row.owner_id}
    author_map: dict[int, str] = {}
    if owner_ids:
        for u in db.scalars(select(User).where(User.id.in_(owner_ids))).all():
            author_map[u.id] = u.username

    liked_ids: set[str] = set()
    favorited_ids: set[str] = set()
    plays_by_id: dict[str, int] = {}
    if rows:
        topic_ids = [r.id for r in rows]
        play_rows = db.execute(
            select(DebateSession.topic_id, func.count(DebateSession.id))
            .where(DebateSession.topic_id.in_(topic_ids))
            .group_by(DebateSession.topic_id)
        ).all()
        plays_by_id = {tid: int(cnt or 0) for tid, cnt in play_rows}
    if user is not None and rows:
        topic_ids = [r.id for r in rows]
        reactions = db.scalars(
            select(DebateTopicReaction).where(
                DebateTopicReaction.user_id == user.id,
                DebateTopicReaction.topic_id.in_(topic_ids),
            )
        ).all()
        for rx in reactions:
            if rx.kind == "like":
                liked_ids.add(rx.topic_id)
            elif rx.kind == "favorite":
                favorited_ids.add(rx.topic_id)

    return [
        serialize_topic(
            row,
            user,
            author_name=author_map.get(row.owner_id) if row.owner_id else None,
            liked=row.id in liked_ids,
            favorited=row.id in favorited_ids,
            plays=plays_by_id.get(row.id, 0),
        )
        for row in rows
    ]


def create_debate_topic(db: Session, user: User, payload: dict) -> dict:
    ensure_debate_tables(db)
    cat = payload.get("category") or "tech"
    diff = payload.get("difficulty") or "intermediate"
    scene_type = "panel" if payload.get("sceneType") == "panel" else "debate"
    roles = _normalize_roles_input(payload.get("roles"), scene_type)
    stages = _normalize_stages_input(payload.get("stages"))
    opp_name, opp_title, opp_persona, opp_voice, opp_avatar = _extract_primary_opponent(roles, payload)
    raw_tools = payload.get("tools")
    tools_cfg = [str(x).strip() for x in raw_tools if str(x).strip()] if isinstance(raw_tools, list) else list(DEFAULT_TOOLS)
    topic = DebateTopic(
        id=f"custom-{uuid.uuid4().hex[:10]}",
        title_zh=payload["titleZh"].strip(),
        motion_en=payload["motionEn"].strip(),
        category=cat,
        category_label=_CATEGORY_LABELS.get(cat, "科技伦理"),
        difficulty=diff,
        difficulty_label=_DIFFICULTY_LABELS.get(diff, "进阶"),
        duration=(payload.get("duration") or "8 分钟").strip(),
        pro_summary=(payload.get("proSummary") or "").strip(),
        con_summary=(payload.get("conSummary") or "").strip(),
        background_context=(payload.get("backgroundContext") or "").strip(),
        key_expressions=[str(x).strip() for x in (payload.get("keyExpressions") or []) if str(x).strip()][:8],
        default_style=(payload.get("defaultStyle") or "balanced").strip(),
        scene_type=scene_type,
        user_role_label=(payload.get("userRoleLabel") or ("候选人 / 主讲人" if scene_type == "panel" else "辩手")).strip(),
        roles_config=roles,
        stages_config=stages,
        opponent_name=opp_name,
        opponent_title=opp_title,
        opponent_persona=opp_persona,
        opponent_voice=opp_voice,
        opponent_avatar_id=opp_avatar,
        knowledge_doc_ids=[int(x) for x in (payload.get("knowledgeDocIds") or []) if str(x).isdigit()][:5],
        tools_config=tools_cfg,
        is_builtin=False,
        owner_id=user.id,
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return serialize_topic(topic, user)


def update_debate_topic(db: Session, user: User, topic_id: str, payload: dict) -> dict:
    ensure_debate_tables(db)
    topic = db.scalar(select(DebateTopic).where(DebateTopic.id == topic_id))
    if not topic:
        raise AppError("未找到该多角色对话场景", code="DEBATE_TOPIC_NOT_FOUND", status_code=404)
    if topic.is_builtin:
        raise AppError("内置场景受保护，请复制为我的场景后再编辑", code="DEBATE_BUILTIN_READONLY", status_code=403)
    is_admin = bool(getattr(user, "is_admin", False))
    if not is_admin and topic.owner_id != user.id:
        raise AppError("无权修改该多角色场景", code="FORBIDDEN", status_code=403)

    if payload.get("sceneType") is not None:
        topic.scene_type = "panel" if payload["sceneType"] == "panel" else "debate"
    scene_type = getattr(topic, "scene_type", "debate") or "debate"

    if payload.get("userRoleLabel") is not None:
        topic.user_role_label = payload["userRoleLabel"].strip() or ("候选人 / 主讲人" if scene_type == "panel" else "辩手")
    if payload.get("titleZh") is not None:
        topic.title_zh = payload["titleZh"].strip()
    if payload.get("motionEn") is not None:
        topic.motion_en = payload["motionEn"].strip()
    if payload.get("category") is not None:
        topic.category = payload["category"]
        topic.category_label = _CATEGORY_LABELS.get(topic.category, "科技伦理")
    if payload.get("difficulty") is not None:
        topic.difficulty = payload["difficulty"]
        topic.difficulty_label = _DIFFICULTY_LABELS.get(topic.difficulty, "进阶")
    if payload.get("duration") is not None:
        topic.duration = payload["duration"].strip()
    if payload.get("proSummary") is not None:
        topic.pro_summary = payload["proSummary"].strip()
    if payload.get("conSummary") is not None:
        topic.con_summary = payload["conSummary"].strip()
    if payload.get("backgroundContext") is not None:
        topic.background_context = payload["backgroundContext"].strip()
    if payload.get("keyExpressions") is not None:
        topic.key_expressions = [str(x).strip() for x in payload["keyExpressions"] if str(x).strip()][:8]
    if payload.get("defaultStyle") is not None:
        topic.default_style = payload["defaultStyle"].strip()
    if payload.get("roles") is not None:
        norm_roles = _normalize_roles_input(payload["roles"], scene_type)
        topic.roles_config = norm_roles
        if norm_roles:
            opp_name, opp_title, opp_persona, opp_voice, opp_avatar = _extract_primary_opponent(norm_roles, payload)
            topic.opponent_name = opp_name
            topic.opponent_title = opp_title
            topic.opponent_persona = opp_persona
            topic.opponent_voice = opp_voice
            topic.opponent_avatar_id = opp_avatar
    else:
        if payload.get("opponentName") is not None:
            topic.opponent_name = payload["opponentName"].strip() or "Sonia"
        if payload.get("opponentTitle") is not None:
            topic.opponent_title = payload["opponentTitle"].strip() or "对手辩手"
        if payload.get("opponentPersona") is not None:
            topic.opponent_persona = payload["opponentPersona"].strip()
        if payload.get("opponentVoice") is not None:
            topic.opponent_voice = payload["opponentVoice"].strip() or "sonia"
        if payload.get("opponentAvatarId") is not None:
            topic.opponent_avatar_id = payload["opponentAvatarId"].strip() or "sarah_2d"
    if payload.get("stages") is not None:
        topic.stages_config = _normalize_stages_input(payload["stages"])
    if payload.get("knowledgeDocIds") is not None:
        topic.knowledge_doc_ids = [int(x) for x in payload["knowledgeDocIds"] if str(x).isdigit()][:5]
    if "tools" in payload and payload["tools"] is not None:
        topic.tools_config = [str(x).strip() for x in payload["tools"] if str(x).strip()]

    db.commit()
    db.refresh(topic)
    return serialize_topic(topic, user)


def toggle_topic_reaction(db: Session, user: User, topic_id: str, kind: str) -> dict:
    ensure_debate_tables(db)
    topic = db.get(DebateTopic, topic_id)
    if not topic:
        raise AppError("辩题不存在", code="DEBATE_TOPIC_NOT_FOUND", status_code=404)
    existing = db.scalar(
        select(DebateTopicReaction).where(
            DebateTopicReaction.topic_id == topic_id,
            DebateTopicReaction.user_id == user.id,
            DebateTopicReaction.kind == kind,
        )
    )
    if existing:
        db.delete(existing)
        active = False
        if kind == "like":
            topic.likes_count = max(0, int(topic.likes_count or 0) - 1)
        else:
            topic.favorites_count = max(0, int(topic.favorites_count or 0) - 1)
    else:
        db.add(DebateTopicReaction(topic_id=topic_id, user_id=user.id, kind=kind))
        active = True
        if kind == "like":
            topic.likes_count = int(topic.likes_count or 0) + 1
        else:
            topic.favorites_count = int(topic.favorites_count or 0) + 1
    db.commit()
    db.refresh(topic)
    if kind == "like":
        return {"liked": active, "likes": int(topic.likes_count or 0)}
    return {"favorited": active, "favorites": int(topic.favorites_count or 0)}


def set_topic_publish(db: Session, user: User, topic_id: str, publish: bool) -> dict:
    ensure_debate_tables(db)
    topic = db.get(DebateTopic, topic_id)
    if not topic:
        raise AppError("辩题不存在", code="DEBATE_TOPIC_NOT_FOUND", status_code=404)
    is_admin = bool(getattr(user, "is_admin", False))
    if topic.is_builtin or (not is_admin and topic.owner_id != user.id):
        raise AppError("无权更改该辩题发布状态", code="FORBIDDEN", status_code=403)
    topic.status = "published" if publish else "private"
    db.commit()
    db.refresh(topic)
    return serialize_topic(topic, user, author_name=user.username)


def duplicate_debate_topic(db: Session, user: User, topic_id: str) -> dict:
    ensure_debate_tables(db)
    src = db.get(DebateTopic, topic_id)
    if not src:
        raise AppError("场景不存在", code="DEBATE_TOPIC_NOT_FOUND", status_code=404)
    new_id = f"custom-{uuid.uuid4().hex[:10]}"
    copied_cover: str | None = None
    if getattr(src, "cover_path", None):
        from app.scenes import knowledge as knowledge_svc
        src_cover = knowledge_svc.cover_file(src.cover_path)
        if src_cover.exists():
            copied_cover = knowledge_svc.save_cover(f"debate_{new_id}", src_cover.name, src_cover.read_bytes())

    clone = DebateTopic(
        id=new_id,
        title_zh=f"{src.title_zh}（副本）",
        motion_en=src.motion_en,
        category=src.category,
        category_label=src.category_label,
        difficulty=src.difficulty,
        difficulty_label=src.difficulty_label,
        duration=src.duration,
        pro_summary=src.pro_summary,
        con_summary=src.con_summary,
        background_context=src.background_context,
        key_expressions=list(src.key_expressions or []),
        default_style=src.default_style,
        scene_type=getattr(src, "scene_type", "debate") or "debate",
        user_role_label=getattr(src, "user_role_label", "候选人 / 主讲人") or "候选人 / 主讲人",
        roles_config=resolve_topic_roles(src),
        stages_config=resolve_topic_stages(src),
        opponent_name=src.opponent_name,
        opponent_title=src.opponent_title,
        opponent_persona=src.opponent_persona,
        opponent_voice=src.opponent_voice,
        opponent_avatar_id=src.opponent_avatar_id,
        cover_path=copied_cover,
        knowledge_doc_ids=[],
        tools_config=_resolve_topic_tools(src),
        status="private",
        is_builtin=False,
        owner_id=user.id,
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return serialize_topic(clone, user, author_name=user.username)


def export_debate_topic_zip(db: Session, topic_id: str) -> bytes:
    """将多角色对话/辩论场景打包为含 manifest.json、debate.json 与封面的 ZIP 字节流。"""
    ensure_debate_tables(db)
    topic = db.get(DebateTopic, topic_id)
    if not topic:
        raise AppError("场景不存在", code="DEBATE_TOPIC_NOT_FOUND", status_code=404)
    cover_entry: str | None = None
    cover_bytes: bytes | None = None
    if getattr(topic, "cover_path", None):
        from app.scenes import knowledge as knowledge_svc
        cover_path = knowledge_svc.cover_file(topic.cover_path)
        if cover_path.exists():
            cover_entry = f"cover{cover_path.suffix or '.png'}"
            cover_bytes = cover_path.read_bytes()

    scene_type = getattr(topic, "scene_type", "debate") or "debate"
    payload = {
        "schemaVersion": 2,
        "type": "echotalk-debate-topic",
        "sceneType": scene_type,
        "userRoleLabel": getattr(topic, "user_role_label", "候选人 / 主讲人") or "候选人 / 主讲人",
        "titleZh": topic.title_zh,
        "motionEn": topic.motion_en,
        "category": topic.category,
        "difficulty": topic.difficulty,
        "duration": topic.duration,
        "proSummary": topic.pro_summary,
        "conSummary": topic.con_summary,
        "backgroundContext": topic.background_context or "",
        "keyExpressions": topic.key_expressions or [],
        "defaultStyle": topic.default_style or "balanced",
        "opponentName": topic.opponent_name or "Sonia",
        "opponentTitle": topic.opponent_title or "对手辩手",
        "opponentPersona": topic.opponent_persona or "",
        "opponentVoice": topic.opponent_voice or "sonia",
        "opponentAvatarId": topic.opponent_avatar_id or "sarah_2d",
        "roles": resolve_topic_roles(topic),
        "stages": resolve_topic_stages(topic),
        "tools": _resolve_topic_tools(topic),
        **({"coverFile": cover_entry} if cover_entry else {}),
    }
    manifest = {
        "format": "echotalk-debate-package",
        "schemaVersion": 2,
        "id": topic.id,
        "sceneType": scene_type,
        "title": topic.title_zh,
        "hasCover": bool(cover_entry),
        "coverFile": cover_entry,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        zf.writestr("debate.json", json.dumps(payload, ensure_ascii=False, indent=2))
        if cover_entry and cover_bytes is not None:
            zf.writestr(cover_entry, cover_bytes)
    return buf.getvalue()


def import_debate_topic_package(db: Session, user: User, raw_bytes: bytes, filename: str = "") -> dict:
    """从 .zip 或 .json 多角色包导入场景（含封面图还原）并归入当前用户。"""
    ensure_debate_tables(db)
    if not raw_bytes:
        raise AppError("导入文件为空", code="EMPTY_DEBATE_PACKAGE", status_code=400)
    data: dict | None = None
    cover_bytes: bytes | None = None
    cover_name: str | None = None
    lower_name = (filename or "").lower()
    if lower_name.endswith(".json") and not raw_bytes.startswith(b"PK"):
        try:
            data = json.loads(raw_bytes.decode("utf-8"))
        except Exception as exc:
            raise AppError(f"JSON 解析失败：{exc}", code="INVALID_DEBATE_PACKAGE", status_code=400) from exc
    else:
        try:
            with zipfile.ZipFile(io.BytesIO(raw_bytes), "r") as zf:
                names = zf.namelist()
                target_name = "debate.json" if "debate.json" in names else next(
                    (n for n in names if n.lower().endswith(".json") and not n.lower().endswith("manifest.json")),
                    None,
                )
                if not target_name:
                    raise AppError("ZIP 包内未找到 debate.json", code="INVALID_DEBATE_PACKAGE", status_code=400)
                data = json.loads(zf.read(target_name).decode("utf-8"))
                preferred_cover = data.get("coverFile") if isinstance(data, dict) else None
                cover_member = (
                    preferred_cover
                    if isinstance(preferred_cover, str) and preferred_cover in names
                    else next((n for n in names if n.lower().startswith("cover.")), None)
                )
                if cover_member:
                    cover_name = cover_member
                    cover_bytes = zf.read(cover_member)
        except AppError:
            raise
        except Exception as exc:
            raise AppError(f"多角色场景包读取失败：{exc}", code="INVALID_DEBATE_PACKAGE", status_code=400) from exc

    if not isinstance(data, dict) or not str(data.get("titleZh") or "").strip() or not str(data.get("motionEn") or "").strip():
        raise AppError("场景包缺少有效的 titleZh 或 motionEn 字段", code="INVALID_DEBATE_PACKAGE", status_code=400)

    created = create_debate_topic(db, user, data)
    if cover_bytes and cover_name:
        try:
            set_debate_cover(db, user, created["id"], cover_name, cover_bytes)
            topic = db.get(DebateTopic, created["id"])
            if topic:
                return serialize_topic(topic, user, author_name=user.username)
        except Exception:
            pass
    return created


async def generate_debate_topic_draft(idea: str, scene_type: str = "debate") -> dict:
    """根据用户想法由 AI 一键生成双语多角色对话或辩论场景包草稿。"""
    clean_idea = idea.strip()
    if not clean_idea:
        raise AppError("请输入场景主题想法或关键词", code="EMPTY_DEBATE_IDEA", status_code=400)
    resolved_type = "panel" if scene_type == "panel" else "debate"

    if resolved_type == "panel":
        fallback = {
            "sceneType": "panel",
            "titleZh": clean_idea[:28] if len(clean_idea) > 2 else f"{clean_idea}多角色评审",
            "motionEn": f"Panel Discussion & Evaluation: Present and defend your approach to {clean_idea} across technical depth, feasibility, and business impact.",
            "category": "workplace",
            "difficulty": "intermediate",
            "duration": "8 分钟",
            "defaultStyle": "balanced",
            "userRoleLabel": "候选人 / 项目负责人",
            "proSummary": "清晰阐述核心思路、关键取舍与可量化业务结果。",
            "conSummary": "主动直面架构瓶颈、实施风险与跨部门协调挑战。",
            "backgroundContext": f"围绕「{clean_idea}」开展多视角圆桌追问，三位专家从各自职能出发轮流深挖真实细节与压力边界。",
            "keyExpressions": [
                "walk through the key trade-offs",
                "quantify the measurable impact",
                "mitigate operational bottleneck",
                "align across stakeholders",
            ],
            "roles": [
                {
                    "id": "lead",
                    "roleType": "interviewer",
                    "name": "Claire",
                    "title": "业务与架构负责人",
                    "voice": "emma",
                    "avatarId": "claire_2d",
                    "persona": "关注方案核心架构与量化成效，擅长就细节连续追问。",
                },
                {
                    "id": "partner",
                    "roleType": "interviewer",
                    "name": "Emily",
                    "title": "跨部门协作者 / HRBP",
                    "voice": "aria",
                    "avatarId": "emily_2d",
                    "persona": "聚焦团队沟通冲突、推动落地阻力与复盘思考。",
                },
                {
                    "id": "evaluator",
                    "roleType": "judge",
                    "name": "Leo",
                    "title": "委员会决策官",
                    "voice": "brian",
                    "avatarId": "leo_2d",
                    "persona": "站在长期收益与风险可控角度做总结性评估。",
                },
            ],
            "stages": [dict(s) for s in PANEL_STAGES],
        }
    else:
        fallback = {
            "sceneType": "debate",
            "titleZh": clean_idea if clean_idea.endswith("？") else f"{clean_idea}是否利大于弊？",
            "motionEn": f"This house believes that {clean_idea} brings more long-term benefits than risks.",
            "category": "society",
            "difficulty": "intermediate",
            "duration": "8 分钟",
            "defaultStyle": "balanced",
            "userRoleLabel": "辩手",
            "proSummary": "从效率提升、资源优化与长期发展角度看，正向收益更加显著。",
            "conSummary": "需警惕潜在副作用、公平性冲击以及执行落地的隐性成本。",
            "backgroundContext": "围绕现实场景中的实际权衡、制度边界与长期影响展开交锋，注重用具体案例支撑立论。",
            "keyExpressions": [
                "weigh the long-term benefits against short-term friction",
                "address the unintended trade-offs",
                "strike a practical balance between",
                "anchor the argument in real-world impact",
            ],
            "roles": resolve_topic_roles({"sceneType": "debate"}),
            "stages": [dict(s) for s in STAGES],
        }

    try:
        llm = create_chat_model()
    except AppError:
        return fallback

    if resolved_type == "panel":
        prompt = f"""You are designing a rich multi-role English panel simulation (like a panel interview, project review, or mock board meeting) for Chinese ESL learners.
User's topic idea: "{clean_idea}"

Available avatarId & voice pairs:
- claire_2d (voice: emma)
- emily_2d (voice: aria)
- sarah_2d (voice: sonia)
- david_2d (voice: andrew)
- leo_2d (voice: brian)

Return ONLY valid JSON (no markdown fences) with these exact keys:
{{
  "titleZh": "Concise natural Chinese scenario title (8-22 chars)",
  "motionEn": "Clear English panel prompt / briefing setting the goal and challenge for the learner.",
  "userRoleLabel": "Short Chinese label for the learner's role (e.g. 高级工程师候选人 / 产品负责人)",
  "category": "one of: tech, workplace, education, society",
  "difficulty": "one of: beginner, intermediate, advanced",
  "duration": "6 分钟 or 8 分钟 or 10 分钟",
  "defaultStyle": "one of: supportive, balanced, sharp",
  "proSummary": "1 concise Chinese sentence describing key strengths to demonstrate.",
  "conSummary": "1 concise Chinese sentence describing key tough challenges or scrutiny to handle.",
  "backgroundContext": "2-3 concise Chinese sentences giving realistic background context and evaluation criteria.",
  "keyExpressions": ["4 useful English phrases tailored to this panel scenario"],
  "roles": [
    {{"id": "role_1", "roleType": "interviewer", "name": "English First Name", "title": "Chinese Role Title", "avatarId": "claire_2d", "voice": "emma", "persona": "1-2 Chinese sentences describing persona and questioning angle"}},
    {{"id": "role_2", "roleType": "interviewer", "name": "English First Name", "title": "Chinese Role Title", "avatarId": "emily_2d", "voice": "aria", "persona": "1-2 Chinese sentences describing persona and questioning angle"}},
    {{"id": "role_3", "roleType": "judge", "name": "English First Name", "title": "Chinese Role Title", "avatarId": "leo_2d", "voice": "brian", "persona": "1-2 Chinese sentences describing persona and evaluation angle"}}
  ],
  "stages": [
    {{"id": "s1", "shortTag": "陈述", "label": "Chinese stage name (4-6 chars)"}},
    {{"id": "s2", "shortTag": "追问", "label": "Chinese stage name"}},
    {{"id": "s3", "shortTag": "挑战", "label": "Chinese stage name"}},
    {{"id": "s4", "shortTag": "评估", "label": "Chinese stage name"}}
  ]
}}"""
    else:
        prompt = f"""You are designing a rich English debate topic package for Chinese ESL learners.
User's topic idea: "{clean_idea}"

Return ONLY valid JSON (no markdown fences) with these exact keys:
{{
  "titleZh": "Natural Chinese debate question ending with ？",
  "motionEn": "Formal English parliamentary debate motion starting with 'This house believes...' or similar clear statement.",
  "category": "one of: tech, workplace, education, society",
  "difficulty": "one of: beginner, intermediate, advanced",
  "duration": "6 分钟 or 8 分钟 or 10 分钟",
  "defaultStyle": "one of: supportive, balanced, sharp",
  "proSummary": "1 concise Chinese sentence summarizing the strongest Proposition argument.",
  "conSummary": "1 concise Chinese sentence summarizing the strongest Opposition argument.",
  "backgroundContext": "2-3 concise Chinese sentences providing real-world context and clash points for the debaters.",
  "keyExpressions": ["4 useful English debate phrases or collocations tailored to this motion"]
}}"""

    try:
        resp = await llm.ainvoke(prompt)
        raw = str(getattr(resp, "content", "") or "").strip()
        if raw.startswith("```"):
            raw = raw.strip("`").lstrip("json").strip()
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and parsed.get("titleZh") and parsed.get("motionEn"):
            return {
                "sceneType": resolved_type,
                "titleZh": str(parsed["titleZh"]).strip(),
                "motionEn": str(parsed["motionEn"]).strip(),
                "userRoleLabel": str(parsed.get("userRoleLabel") or fallback["userRoleLabel"]).strip(),
                "category": parsed["category"] if parsed.get("category") in _CATEGORY_LABELS else fallback["category"],
                "difficulty": parsed["difficulty"] if parsed.get("difficulty") in _DIFFICULTY_LABELS else "intermediate",
                "duration": str(parsed.get("duration") or "8 分钟").strip(),
                "defaultStyle": parsed["defaultStyle"] if parsed.get("defaultStyle") in ("supportive", "balanced", "sharp") else "balanced",
                "proSummary": str(parsed.get("proSummary") or fallback["proSummary"]).strip(),
                "conSummary": str(parsed.get("conSummary") or fallback["conSummary"]).strip(),
                "backgroundContext": str(parsed.get("backgroundContext") or fallback["backgroundContext"]).strip(),
                "keyExpressions": [str(x).strip() for x in (parsed.get("keyExpressions") or fallback["keyExpressions"]) if str(x).strip()][:6],
                "roles": _normalize_roles_input(parsed.get("roles"), resolved_type) or fallback["roles"],
                "stages": _normalize_stages_input(parsed.get("stages")) or fallback["stages"],
            }
    except Exception:
        pass
    return fallback


def delete_debate_topic(db: Session, user: User, topic_id: str) -> None:
    ensure_debate_tables(db)
    topic = db.scalar(select(DebateTopic).where(DebateTopic.id == topic_id))
    if not topic:
        raise AppError("未找到该辩论话题", code="DEBATE_TOPIC_NOT_FOUND", status_code=404)
    is_admin = bool(getattr(user, "is_admin", False))
    if not is_admin and (topic.is_builtin or topic.owner_id != user.id):
        raise AppError("无权删除该辩论话题", code="FORBIDDEN", status_code=403)
    from app.scenes import knowledge as knowledge_svc
    knowledge_svc.remove_scene_files(f"debate_{topic_id}")
    db.query(DebateTopicReaction).filter(DebateTopicReaction.topic_id == topic_id).delete()
    db.delete(topic)
    db.commit()


def set_debate_cover(db: Session, user: User, topic_id: str, filename: str | None, content: bytes) -> str:
    ensure_debate_tables(db)
    topic = db.scalar(select(DebateTopic).where(DebateTopic.id == topic_id))
    if not topic:
        raise AppError("未找到该辩论话题", code="DEBATE_TOPIC_NOT_FOUND", status_code=404)
    if topic.is_builtin:
        raise AppError("内置辩题不可修改封面", code="DEBATE_BUILTIN_READONLY", status_code=403)
    is_admin = bool(getattr(user, "is_admin", False))
    if not is_admin and topic.owner_id != user.id:
        raise AppError("无权修改该辩论话题封面", code="FORBIDDEN", status_code=403)
    from app.scenes import knowledge as knowledge_svc
    relative = knowledge_svc.save_cover(f"debate_{topic_id}", filename or "cover.png", content)
    topic.cover_path = relative
    db.commit()
    return relative


def get_debate_cover_file(db: Session, topic_id: str):
    ensure_debate_tables(db)
    topic = db.scalar(select(DebateTopic).where(DebateTopic.id == topic_id))
    if not topic:
        return None
    if getattr(topic, "cover_path", None):
        from app.scenes import knowledge as knowledge_svc
        path = knowledge_svc.cover_file(topic.cover_path)
        if path.exists():
            return path
    return _builtin_cover_file(topic_id)


def remove_debate_cover(db: Session, user: User, topic_id: str) -> bool:
    ensure_debate_tables(db)
    topic = db.scalar(select(DebateTopic).where(DebateTopic.id == topic_id))
    if not topic:
        raise AppError("未找到该辩论话题", code="DEBATE_TOPIC_NOT_FOUND", status_code=404)
    if topic.is_builtin:
        raise AppError("内置辩题不可修改封面", code="DEBATE_BUILTIN_READONLY", status_code=403)
    is_admin = bool(getattr(user, "is_admin", False))
    if not is_admin and topic.owner_id != user.id:
        raise AppError("无权修改该辩论话题封面", code="FORBIDDEN", status_code=403)
    if not getattr(topic, "cover_path", None):
        return False
    from app.scenes import knowledge as knowledge_svc
    path = knowledge_svc.cover_file(topic.cover_path)
    if path.exists():
        path.unlink()
    topic.cover_path = None
    db.commit()
    return True


def _role_label(role: str, user_side: str, scene_type: str = "debate", role_title: str = "") -> str:
    if scene_type == "panel":
        if role == "user":
            return role_title or "我方"
        if role_title:
            return role_title
        if role == "judge":
            return "评估官"
        if role == "moderator":
            return "主理人"
        return "面试/评审官"
    if role == "moderator":
        return "主持"
    if role == "judge":
        return role_title or "评委点评"
    if role == "user":
        return "正方 · 我方" if user_side == "pro" else "反方 · 我方"
    return role_title or ("反方" if user_side == "pro" else "正方")


def _turn_role_rank(role: str | None) -> int:
    if role == "user":
        return 0
    if role == "judge":
        return 2
    return 1


def _load_ordered_turns(db: Session, session_id: str) -> list[DebateTurn]:
    """按时间戳与同轮次角色顺序（用户 -> 对手/评审 -> 评委）确定性加载会话消息。"""
    rows = db.scalars(
        select(DebateTurn)
        .where(DebateTurn.session_id == session_id)
        .order_by(DebateTurn.created_at.asc(), DebateTurn.turn_number.asc())
    ).all()
    return sorted(rows, key=lambda t: (t.created_at, t.turn_number or 0, _turn_role_rank(t.role)))


def serialize_turn(turn: DebateTurn, user_side: str, scene_type: str = "debate") -> dict:
    role_title = getattr(turn, "role_title", "") or ""
    avatar_id = getattr(turn, "avatar_id", "") or ""
    return {
        "id": turn.id,
        "role": turn.role,
        "roleLabel": _role_label(turn.role, user_side, scene_type=scene_type, role_title=role_title),
        "roleTitle": role_title,
        "avatarId": avatar_id,
        "speaker": turn.speaker,
        "voiceStyle": turn.voice_style,
        "isVoice": bool(turn.is_voice),
        "duration": turn.duration,
        "stageLabel": turn.stage_label,
        "en": turn.en_text,
        "zh": turn.zh_text,
        "created_at": turn.created_at.isoformat() if turn.created_at else None,
    }


def serialize_session(session: DebateSession, max_turns: int = 6) -> dict:
    return {
        "id": session.id,
        "topic_id": session.topic_id,
        "topic_title": session.topic_title,
        "motion_en": session.motion_en,
        "category": session.category,
        "difficulty": session.difficulty,
        "scene_type": getattr(session, "scene_type", None) or "debate",
        "user_side": session.user_side,
        "difficulty_level": session.difficulty_level,
        "stage_index": session.stage_index,
        "turn_count": session.turn_count,
        "max_turns": max_turns,
        "status": session.status,
        "win_rate": session.win_rate,
        "combo_count": session.combo_count,
        "scores": session.scores_json or {"logic": 0, "rebuttal": 0, "fluency": 0, "presence": 0},
        "verdict": session.verdict_json,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }


def create_debate_session(
    db: Session,
    user: User,
    topic_id: str,
    user_side: str = "pro",
    difficulty_level: str = "balanced",
) -> dict:
    ensure_debate_tables(db)
    topic_row = db.scalar(select(DebateTopic).where(DebateTopic.id == topic_id))
    if not topic_row:
        raise AppError("未找到该多角色对话场景", code="DEBATE_TOPIC_NOT_FOUND", status_code=404)
    topic = serialize_topic(topic_row, user)
    scene_type = topic["sceneType"]
    roles = topic["roles"]
    stages = topic["stages"]
    max_turns = topic["maxTurns"]

    side = "pro" if scene_type == "panel" else ("con" if user_side == "con" else "pro")
    level = difficulty_level if difficulty_level in ("supportive", "balanced", "sharp") else "balanced"

    session = DebateSession(
        id=str(uuid.uuid4()),
        user_id=user.id,
        topic_id=topic["id"],
        topic_title=topic["titleZh"],
        motion_en=topic["motionEn"],
        category=topic["category"],
        difficulty=topic["difficulty"],
        scene_type=scene_type,
        user_side=side,
        difficulty_level=level,
        stage_index=0,
        turn_count=0,
        status="active",
        win_rate=50,
        combo_count=0,
        scores_json={"logic": 0, "rebuttal": 0, "fluency": 0, "presence": 0},
    )
    db.add(session)

    if scene_type == "panel":
        opener = next((r for r in roles if r.get("roleType") == "moderator"), None) or roles[0]
        user_role = topic.get("userRoleLabel") or "候选人 / 主讲人"
        opening_turn = DebateTurn(
            id=str(uuid.uuid4()),
            session_id=session.id,
            turn_number=1,
            stage_label=stages[0]["label"],
            role=opener.get("roleType") or "interviewer",
            speaker=opener["name"],
            role_title=opener.get("title") or "主理人",
            avatar_id=opener.get("avatarId") or "claire_2d",
            voice_style=opener.get("voice") or "emma",
            is_voice=False,
            en_text=f'Welcome to this session: "{topic["motionEn"]}" I am {opener["name"]}, {opener.get("title") or "panel member"}. To get started, could you briefly introduce your core approach?',
            zh_text=f'欢迎来到本场圆桌对话，你将以「{user_role}」身份参与。我是{opener.get("title") or "评审成员"} {opener["name"]}，请先用英语做简短开场陈述。',
        )
    else:
        opener = next((r for r in roles if r.get("roleType") == "moderator"), None) or {
            "name": "Brian",
            "title": "主持人",
            "voice": "brian",
            "avatarId": "david_2d",
        }
        side_en = "Proposition" if side == "pro" else "Opposition"
        side_zh = "正方" if side == "pro" else "反方"
        opening_turn = DebateTurn(
            id=str(uuid.uuid4()),
            session_id=session.id,
            turn_number=1,
            stage_label=stages[0]["label"],
            role="moderator",
            speaker=opener["name"],
            role_title=opener.get("title") or "主持人",
            avatar_id=opener.get("avatarId") or "david_2d",
            voice_style=opener.get("voice") or "brian",
            is_voice=False,
            en_text=f'Welcome to today\'s debate: "{topic["motionEn"]}" You will represent the {side_en}. Please deliver your opening statement.',
            zh_text=f"欢迎来到本场辩论。本场你将代表{side_zh}发言，请先进行开篇立论。",
        )
    db.add(opening_turn)
    db.commit()
    db.refresh(session)
    db.refresh(opening_turn)

    return {
        "session": serialize_session(session, max_turns=max_turns),
        "topic": topic,
        "messages": [serialize_turn(opening_turn, side, scene_type=scene_type)],
    }


def get_latest_debate_session(db: Session, user_id: int, topic_id: str) -> dict:
    ensure_debate_tables(db)
    row = db.scalar(
        select(DebateSession)
        .where(
            DebateSession.user_id == user_id,
            DebateSession.topic_id == topic_id,
            DebateSession.status == "active",
            DebateSession.turn_count >= 1,
        )
        .order_by(DebateSession.updated_at.desc(), DebateSession.created_at.desc())
    )
    return {"session": serialize_session(row) if row else None}


def get_debate_session(db: Session, user_id: int, session_id: str) -> dict:
    ensure_debate_tables(db)
    session = db.scalar(
        select(DebateSession).where(DebateSession.id == session_id, DebateSession.user_id == user_id)
    )
    if not session:
        raise AppError("未找到该多角色对话会话", code="DEBATE_NOT_FOUND", status_code=404)

    turns = _load_ordered_turns(db, session.id)

    topic_row = db.scalar(select(DebateTopic).where(DebateTopic.id == session.topic_id))
    topic_data = serialize_topic(topic_row) if topic_row else _TOPIC_MAP.get(session.topic_id)
    scene_type = (topic_data.get("sceneType") if topic_data else None) or getattr(session, "scene_type", "debate") or "debate"
    max_turns = (topic_data.get("maxTurns") if topic_data else None) or 6
    return {
        "session": serialize_session(session, max_turns=max_turns),
        "topic": topic_data,
        "messages": [serialize_turn(t, session.user_side, scene_type=scene_type) for t in turns],
    }


def _fallback_ai_turn(
    session: DebateSession,
    user_text: str,
    next_stage: int,
    stages_count: int,
    scene_type: str,
    speaker_role: dict,
    eval_role: dict | None,
    judge_score_enabled: bool,
) -> dict[str, Any]:
    word_count = len(user_text.split())
    if word_count < 6:
        score_deltas = {"logic": -2, "rebuttal": -2, "fluency": -1, "presence": -2} if judge_score_enabled else {}
        win_delta = -4 if judge_score_enabled else 0
    elif word_count < 14:
        score_deltas = {"logic": 1, "rebuttal": 1, "fluency": 2, "presence": 1} if judge_score_enabled else {}
        win_delta = 1 if judge_score_enabled else 0
    else:
        score_deltas = {"logic": 3, "rebuttal": 4, "fluency": 3, "presence": 3} if judge_score_enabled else {}
        win_delta = 4 if judge_score_enabled else 0

    show_eval = judge_score_enabled and bool(eval_role) and next_stage >= max(1, stages_count - 2)
    if scene_type == "panel":
        speaker_name = speaker_role.get("name") or "Claire"
        speaker_title = speaker_role.get("title") or "评审成员"
        if word_count < 6:
            opp_en = (
                f"Thank you for sharing briefly, though we still need specific context from your side. "
                f"From my perspective as {speaker_title}, could you walk us through a concrete example or trade-off?"
            )
            opp_zh = f"感谢你的简短回应，不过我们还需要更具体的背景信息。从{speaker_title}视角看，能否举一个实际案例或权衡细节？"
        else:
            opp_en = (
                f"Thanks for explaining that rationale clearly. Looking closely from the {speaker_title} lens, "
                "what measurable signal convinced your team that this trade-off held up under peak pressure?"
            )
            opp_zh = f"你刚才的思路阐述比较清楚。进一步从{speaker_title}视角追问：在高并发或资源紧张压力下，有哪些量化指标验证了该方案有效？"
        judge_en = (
            f"{eval_role['name']} ({eval_role.get('title') or '评估官'}): Well-structured framing with clear ownership; backing your claim with one before-and-after metric will make the panel far more confident."
            if show_eval and eval_role
            else ""
        )
        judge_zh = (
            f"{eval_role['name']}（{eval_role.get('title') or '评估官'}）：表达有条理且主体责任明确，若再补充一组前后对比数据会更有说服力。"
            if show_eval and eval_role
            else ""
        )
        review_expr = {
            "prompt": f"群面/圆桌深度追问高分句式（{session.topic_title}）",
            "answer": "The decisive trade-off was prioritizing reliability over short-term velocity, which cut incident recovery time noticeably.",
            "note": "先明确核心取舍（prioritizing A over B），再用结果从句交代量化或可观察收益，适合回应技术与管理追问。",
        }
    else:
        opp_side = "Opposition" if session.user_side == "pro" else "Proposition"
        if word_count < 6:
            opp_en = (
                f"As the {opp_side}, that statement feels too brief to address the core clash. "
                "Could you spell out the causal mechanism and concrete evidence behind your stance?"
            )
            opp_zh = f"作为{('反方' if session.user_side == 'pro' else '正方')}，这段陈述过于简略，尚未触及核心冲突。请进一步展开你的因果论证与事实依据。"
        else:
            opp_en = (
                f"As the {opp_side}, I see why you emphasize that point, yet it assumes ideal conditions. "
                "When teams face tight deadlines and real-world accountability, how do you prevent unintended trade-offs?"
            )
            opp_zh = (
                f"作为{('反方' if session.user_side == 'pro' else '正方')}，我理解你的出发点，但这预设了过于理想的前提。"
                "在真实高压交付与责任边界下，你如何避免隐性代价？"
            )
        judge_en = (
            "Clear framing and solid clash on the core premise. Anchor your next rebuttal with one concrete real-world example."
            if show_eval
            else ""
        )
        judge_zh = (
            "立论结构清晰，已切中核心前提；下一轮建议补充一个具体现实案例来巩固反驳。"
            if show_eval
            else ""
        )
        review_expr = {
            "prompt": f"辩论反驳常用表达（{session.topic_title}）",
            "answer": "While that point holds merit on the surface, it overlooks the long-term trade-off in practice.",
            "note": "先让步肯定对方合理之处，再用 it overlooks 转折切入现实代价，适合交叉质询与焦点攻防。",
        }

    return {
        "opponent_en": opp_en,
        "opponent_zh": opp_zh,
        "judge_en": judge_en,
        "judge_zh": judge_zh,
        "score_deltas": score_deltas,
        "win_rate_delta": win_delta,
        "review_expression": review_expr,
    }


def _load_topic_knowledge(db: Session, topic: DebateTopic | None, *, include_docs: bool = True) -> str:
    if not topic:
        return ""
    parts: list[str] = []
    if topic.background_context:
        parts.append(f"Background: {topic.background_context}")
    if topic.key_expressions:
        parts.append(f"Target expressions: {', '.join(topic.key_expressions[:6])}")
    if include_docs:
        doc_ids = topic.knowledge_doc_ids or []
        if doc_ids:
            chunks = db.scalars(
                select(PersonalChunk.content)
                .where(PersonalChunk.document_id.in_(doc_ids))
                .limit(4)
            ).all()
            if chunks:
                parts.append("Knowledge snippets:\n" + "\n".join(f"- {c[:240]}" for c in chunks))
    return "\n".join(parts)


async def _generate_ai_turn(
    session: DebateSession,
    history_turns: list[DebateTurn],
    user_text: str,
    next_stage: int,
    stages: list[dict],
    scene_type: str,
    speaker_role: dict,
    eval_role: dict | None,
    tools: list[str],
    topic: DebateTopic | None = None,
    knowledge_text: str = "",
    show_eval: bool | None = None,
) -> dict[str, Any]:
    judge_score_enabled = "judge_score" in tools
    fact_check_enabled = "fact_check" in tools
    rebuttal_hint_enabled = "rebuttal_hint" in tools or "get_hint" in tools
    lookup_word_enabled = "lookup_word" in tools
    calc_enabled = "calculate_expression" in tools
    review_enabled = "add_review_task" in tools

    try:
        llm = create_chat_model()
    except AppError:
        return _fallback_ai_turn(
            session, user_text, next_stage, len(stages), scene_type, speaker_role, eval_role, judge_score_enabled
        )

    stage_label = stages[next_stage]["label"]
    recent_lines = "\n".join(f"- {t.speaker} ({getattr(t, 'role_title', None) or t.role}): {t.en_text}" for t in history_turns[-6:])
    style_hint = {
        "supportive": "friendly, constructive, B1-B2 English",
        "balanced": "sharp yet respectful professional style, B2-C1 English",
        "sharp": "rigorous, incisive, high-pressure style, C1 English",
    }.get(session.difficulty_level, "balanced")
    extra_rules = []
    if fact_check_enabled:
        extra_rules.append("Actively scrutinize any numbers, assumptions, or factual claims against the background context and point out unverified gaps if any.")
    if lookup_word_enabled:
        extra_rules.append("Naturally clarify or model precise domain terminology when helpful.")
    if calc_enabled:
        extra_rules.append("Verify any percentages, budgets, or quantitative trade-offs mentioned by the user.")
    fact_rule = " ".join(extra_rules)
    hint_or_review = rebuttal_hint_enabled or review_enabled
    scoring_rule = (
        "Evaluate the latest user statement honestly: give negative deltas (-4 to -1) for score_deltas and win_rate_delta if the answer is vague, off-topic, lacks reasoning, or < 8 words; give positive deltas (+1 to +5) if well-reasoned and fluent."
        if judge_score_enabled
        else "Return 0 for all score_deltas and win_rate_delta, and empty strings for judge_en and judge_zh."
    )
    if show_eval is None:
        show_eval = judge_score_enabled and bool(eval_role) and (
            next_stage > session.stage_index or next_stage >= max(1, len(stages) - 1)
        )
    if not show_eval:
        scoring_rule += " Leave judge_en and judge_zh as empty strings \"\" on this turn."

    speaker_name = speaker_role.get("name") or "Claire"
    speaker_title = speaker_role.get("title") or "Participant"
    speaker_persona = speaker_role.get("persona") or "Sharp, structured and engaging."

    if scene_type == "panel":
        user_role_label = getattr(topic, "user_role_label", None) or "Candidate / Proposer"
        eval_instruction = (
            f"1-2 concise sentences from {eval_role['name']} ({eval_role.get('title') or 'Evaluator'}) commenting on strengths/gaps."
            if show_eval and eval_role
            else ""
        )
        prompt = f"""You are orchestrating a multi-role English panel discussion / panel interview.
Scenario prompt: "{session.motion_en}"
User role: {user_role_label}
Active panelist speaking next: {speaker_name} ({speaker_title})
Speaker persona: {speaker_persona}
Style: {style_hint}
{fact_rule}
{knowledge_text}
Current stage: {stage_label}
Recent transcript:
{recent_lines}
Latest user statement: "{user_text}"

{scoring_rule}
Respond ONLY with valid JSON (no markdown fences):
{{
  "opponent_en": "2-3 concise, natural English sentences directly from {speaker_name} reacting to what the user just said from the {speaker_title} perspective, and asking 1 focused follow-up question.",
  "opponent_zh": "Natural Chinese translation of opponent_en.",
  "judge_en": "{eval_instruction}",
  "judge_zh": "{'Chinese translation of judge_en.' if eval_instruction else ''}",
  "score_deltas": {{"logic": 2, "rebuttal": 2, "fluency": 2, "presence": 2}},
  "win_rate_delta": 3,
  "review_expression": {{
    "prompt": "{ '一句适合当前追问场景的中文表达提示' if rebuttal_hint_enabled else '' }",
    "answer": "{ 'A concise, high-scoring English sentence upgrading what the user just explained.' if rebuttal_hint_enabled else '' }",
    "note": "{ '简短中文句式亮点说明' if rebuttal_hint_enabled else '' }"
  }}
}}"""
    else:
        opp_side = "Opposition" if session.user_side == "pro" else "Proposition"
        eval_name = eval_role["name"] if eval_role else "Judge Andrew"
        prompt = f"""You are orchestrating an English multi-role debate.
Motion: "{session.motion_en}"
User represents: {"Proposition" if session.user_side == "pro" else "Opposition"}
AI Opponent speaking: {speaker_name} ({speaker_title}) represents {opp_side} ({style_hint})
Opponent Persona: {speaker_persona}
{fact_rule}
{knowledge_text}
Current stage: {stage_label}
Recent transcript:
{recent_lines}
Latest user statement: "{user_text}"

{scoring_rule}
Respond ONLY with valid JSON (no markdown fences):
{{
  "opponent_en": "2-3 concise, natural English sentences from {speaker_name} staying true to the persona, grounding the rebuttal in the background knowledge, and posing 1 sharp question.",
  "opponent_zh": "Natural Chinese translation of opponent_en.",
  "judge_en": "{ f'1-2 concise sentences from {eval_name} evaluating the clash and giving 1 actionable tip.' if show_eval else '' }",
  "judge_zh": "{ 'Chinese translation of judge_en.' if show_eval else '' }",
  "score_deltas": {{"logic": 2, "rebuttal": 2, "fluency": 2, "presence": 2}},
  "win_rate_delta": 3,
  "review_expression": {{
    "prompt": "{ '一句适合本轮辩论场景的中文表达提示' if rebuttal_hint_enabled else '' }",
    "answer": "{ 'A natural, high-scoring English debate sentence upgrading or complementing what the user just argued.' if rebuttal_hint_enabled else '' }",
    "note": "{ '简短说明句式亮点或使用场景（中文）' if rebuttal_hint_enabled else '' }"
  }}
}}"""

    try:
        resp = await llm.ainvoke(prompt)
        raw = str(getattr(resp, "content", "") or "").strip()
        if raw.startswith("```"):
            raw = raw.strip("`").lstrip("json").strip()
        parsed = json.loads(raw)
        if not isinstance(parsed, dict) or not parsed.get("opponent_en"):
            return _fallback_ai_turn(
                session, user_text, next_stage, len(stages), scene_type, speaker_role, eval_role, judge_score_enabled
            )
        return parsed
    except Exception:
        return _fallback_ai_turn(
            session, user_text, next_stage, len(stages), scene_type, speaker_role, eval_role, judge_score_enabled
        )


async def submit_debate_turn(
    db: Session,
    user: User,
    session_id: str,
    text: str,
    is_voice: bool = False,
    duration: int | None = None,
) -> dict:
    ensure_debate_tables(db)
    clean_text = text.strip()
    if not clean_text:
        raise AppError("发言内容不能为空", code="EMPTY_DEBATE_TURN", status_code=400)

    session = db.scalar(
        select(DebateSession).where(DebateSession.id == session_id, DebateSession.user_id == user.id)
    )
    if not session:
        raise AppError("未找到该多角色对话会话", code="DEBATE_NOT_FOUND", status_code=404)
    if session.status == "finished":
        raise AppError("该场对话已结束并归档", code="DEBATE_ALREADY_FINISHED", status_code=400)

    history_turns = _load_ordered_turns(db, session.id)

    topic_row = db.scalar(select(DebateTopic).where(DebateTopic.id == session.topic_id))
    scene_type = (getattr(topic_row, "scene_type", None) if topic_row else None) or getattr(session, "scene_type", "debate") or "debate"
    roles = resolve_topic_roles(topic_row) if topic_row else resolve_topic_roles({"sceneType": scene_type})
    stages = resolve_topic_stages(topic_row) if topic_row else resolve_topic_stages({"sceneType": scene_type})
    tools = _resolve_topic_tools(topic_row)
    max_turns = _resolve_duration_turns(topic_row.duration if topic_row else None)

    current_stage = min(len(stages) - 1, max(0, session.stage_index))
    user_turns_done = sum(1 for t in history_turns if t.role == "user") + 1
    user_role_label = (getattr(topic_row, "user_role_label", None) if topic_row else None) or ("候选人 / 主讲人" if scene_type == "panel" else "辩手")
    turn_base_ts = utcnow()
    user_turn = DebateTurn(
        id=str(uuid.uuid4()),
        session_id=session.id,
        turn_number=user_turns_done,
        stage_label=stages[current_stage]["label"],
        role="user",
        speaker="我",
        role_title=user_role_label if scene_type == "panel" else "",
        avatar_id="",
        voice_style="user",
        is_voice=is_voice,
        duration=duration,
        en_text=clean_text,
        zh_text="",
        created_at=turn_base_ts,
    )
    db.add(user_turn)

    progress = min(1.0, user_turns_done / max(1, max_turns))
    next_stage = min(len(stages) - 1, int(progress * (len(stages) - 1) + 0.0001))

    # 选择本轮发言 AI 角色：群面/圆桌按成员池轮流切换；辩论固定反方/挑战方 + 评委点评
    if scene_type == "panel":
        questioners = [r for r in roles if r.get("roleType") != "judge"]
        pool = questioners if len(questioners) >= 2 else roles
        idx = user_turns_done % len(pool)
        speaker_role = pool[idx]
        last_ai = next((t for t in reversed(history_turns) if t.role != "user"), None)
        if len(pool) >= 2 and last_ai and last_ai.speaker == speaker_role["name"]:
            speaker_role = pool[(idx + 1) % len(pool)]
        eval_role = next((r for r in roles if r.get("roleType") == "judge" and r["name"] != speaker_role["name"]), None)
    else:
        speaker_role = next((r for r in roles if r.get("roleType") == "opponent"), None) or roles[0]
        eval_role = next((r for r in roles if r.get("roleType") == "judge"), None) or {
            "id": "judge",
            "roleType": "judge",
            "name": "Andrew",
            "title": "特邀评委",
            "voice": "andrew",
            "avatarId": "leo_2d",
        }

    judge_score_enabled = "judge_score" in tools
    should_eval_speak = judge_score_enabled and bool(eval_role) and (
        next_stage > session.stage_index or user_turns_done >= max_turns
    )
    knowledge_text = _load_topic_knowledge(db, topic_row, include_docs=("search_knowledge" in tools))
    ai_data = await _generate_ai_turn(
        session,
        history_turns,
        clean_text,
        next_stage,
        stages=stages,
        scene_type=scene_type,
        speaker_role=speaker_role,
        eval_role=eval_role,
        tools=tools,
        topic=topic_row,
        knowledge_text=knowledge_text,
        show_eval=should_eval_speak,
    )
    deltas = ai_data.get("score_deltas") or {}
    cur_scores = dict(session.scores_json or {"logic": 0, "rebuttal": 0, "fluency": 0, "presence": 0})
    if judge_score_enabled:
        for k in ("logic", "rebuttal", "fluency", "presence"):
            try:
                raw_d = int(deltas.get(k, 1))
            except (TypeError, ValueError):
                raw_d = 1
            clamped_d = max(-5, min(6, raw_d))
            base = int(cur_scores.get(k, 0)) or 60
            cur_scores[k] = max(45, min(98, base + clamped_d))
        try:
            raw_win = int(ai_data.get("win_rate_delta", 2))
        except (TypeError, ValueError):
            raw_win = 2
        voice_bonus = 1 if (is_voice and len(clean_text.split()) >= 6) else 0
        win_delta = max(-8, min(8, raw_win)) + voice_bonus
    else:
        win_delta = 0

    session.stage_index = next_stage
    session.turn_count = min(max_turns, user_turns_done)
    session.combo_count = 0 if win_delta < 0 else (session.combo_count + 1)
    session.win_rate = max(20, min(95, session.win_rate + win_delta))
    session.scores_json = cur_scores
    session.updated_at = utcnow()

    new_turns: list[DebateTurn] = [user_turn]

    opp_role_type = speaker_role.get("roleType") or ("interviewer" if scene_type == "panel" else "opponent")
    opp_turn = DebateTurn(
        id=str(uuid.uuid4()),
        session_id=session.id,
        turn_number=session.turn_count,
        stage_label=stages[next_stage]["label"],
        role=opp_role_type,
        speaker=speaker_role.get("name") or "Sonia",
        role_title=speaker_role.get("title") or ("评审成员" if scene_type == "panel" else "对手辩手"),
        avatar_id=speaker_role.get("avatarId") or "sarah_2d",
        voice_style=speaker_role.get("voice") or "sonia",
        is_voice=False,
        en_text=str(ai_data.get("opponent_en") or "").strip(),
        zh_text=str(ai_data.get("opponent_zh") or "").strip(),
        created_at=turn_base_ts + timedelta(milliseconds=1),
    )
    db.add(opp_turn)
    new_turns.append(opp_turn)

    judge_en = str(ai_data.get("judge_en") or "").strip() if should_eval_speak else ""
    if judge_en and eval_role:
        judge_turn = DebateTurn(
            id=str(uuid.uuid4()),
            session_id=session.id,
            turn_number=session.turn_count,
            stage_label=stages[next_stage]["label"],
            role="judge",
            speaker=eval_role.get("name") or "Andrew",
            role_title=eval_role.get("title") or ("委员会评估官" if scene_type == "panel" else "特邀评委"),
            avatar_id=eval_role.get("avatarId") or "leo_2d",
            voice_style=eval_role.get("voice") or "andrew",
            is_voice=False,
            en_text=judge_en,
            zh_text=str(ai_data.get("judge_zh") or "").strip(),
            created_at=turn_base_ts + timedelta(milliseconds=2),
        )
        db.add(judge_turn)
        new_turns.append(judge_turn)

    rev = ai_data.get("review_expression") or {}
    if "add_review_task" in tools and rev.get("answer"):
        source_key = f"debate:{session.id}:{user_turn.id}"
        existing_rev = db.scalar(
            select(ReviewItem).where(ReviewItem.user_id == user.id, ReviewItem.source_key == source_key)
        )
        if not existing_rev:
            db.add(
                ReviewItem(
                    user_id=user.id,
                    kind="debate",
                    prompt=str(rev.get("prompt") or f"多角色表达：{session.topic_title}"),
                    answer=str(rev.get("answer")),
                    note=str(rev.get("note") or "来自多角色对话实战推荐表达。"),
                    context_text=clean_text[:280],
                    source_type="debate",
                    source_key=source_key,
                    source_session_id=session.id,
                    scene_id=session.topic_id,
                    scene_name=session.topic_title,
                    due_at=utcnow(),
                )
            )

    db.commit()
    db.refresh(session)
    return {
        "session": serialize_session(session, max_turns=max_turns),
        "new_messages": [serialize_turn(t, session.user_side, scene_type=scene_type) for t in new_turns],
    }


def _award_debate_xp(db: Session, user_id: int, xp_delta: int) -> None:
    state = db.scalar(select(UserXpState).where(UserXpState.user_id == user_id))
    today = utcnow().strftime("%Y-%m-%d")
    if not state:
        state = UserXpState(
            user_id=user_id,
            total_xp=xp_delta,
            today_xp=xp_delta,
            today_date=today,
            streak_days=1,
        )
        db.add(state)
    else:
        if state.today_date != today:
            state.today_date = today
            state.today_xp = 0
            state.streak_days = max(1, state.streak_days + 1)
        state.total_xp += xp_delta
        state.today_xp += xp_delta


def finish_debate_session(db: Session, user: User, session_id: str) -> dict:
    ensure_debate_tables(db)
    session = db.scalar(
        select(DebateSession).where(DebateSession.id == session_id, DebateSession.user_id == user.id)
    )
    if not session:
        raise AppError("未找到该多角色对话会话", code="DEBATE_NOT_FOUND", status_code=404)

    topic_row = db.scalar(select(DebateTopic).where(DebateTopic.id == session.topic_id))
    scene_type = (getattr(topic_row, "scene_type", None) if topic_row else None) or getattr(session, "scene_type", "debate") or "debate"
    max_turns = _resolve_duration_turns(topic_row.duration if topic_row else None)

    already_finished = session.status == "finished"
    scores = session.scores_json or {"logic": 0, "rebuttal": 0, "fluency": 0, "presence": 0}
    avg_score = round(sum(scores.values()) / max(1, len(scores)))
    xp_awarded = 0 if already_finished else 40

    if scene_type == "panel":
        verdict = session.verdict_json or {
            "winner": "user" if session.win_rate >= 60 else "opponent",
            "avg_score": avg_score,
            "xp_awarded": 40,
            "summary": (
                f"你在「{session.topic_title}」中获得了 {session.win_rate}% 的委员会认可度，"
                f"四维综合得分 {avg_score} 分，已应对多角色连续追问 {session.combo_count} 轮。"
            ),
            "strengths": [
                f"结构化表达 {scores.get('logic', 80)} 分，核心方案立场清晰",
                f"抗压临场度 {scores.get('presence', 80)} 分，能针对不同角色诉求精准作答",
            ],
            "next_tip": "下一次回应多方追问时，建议先用一句话给结论（BLUF），再补充 1 组可量化指标收尾。",
        }
    else:
        verdict = session.verdict_json or {
            "winner": "user" if session.win_rate >= 50 else "opponent",
            "avg_score": avg_score,
            "xp_awarded": 40,
            "summary": (
                f"你在本场关于「{session.topic_title}」的辩论中保持了 {session.win_rate}% 的优势胜率，"
                f"连续有效交锋 {session.combo_count} 次，逻辑与反驳表现稳定。"
            ),
            "strengths": [
                f"逻辑说服力达到 {scores.get('logic', 80)} 分，立场表达明确",
                f"临场气场 {scores.get('presence', 80)} 分，能围绕对方质疑正面回应",
            ],
            "next_tip": "下一次可在交叉质询环节加入具体数据或真实案例，进一步拉开胜率差距。",
        }

    if not already_finished:
        session.status = "finished"
        session.verdict_json = verdict
        session.updated_at = utcnow()
        _award_debate_xp(db, user.id, xp_awarded)
        db.commit()
        db.refresh(session)

    return {
        "session": serialize_session(session, max_turns=max_turns),
        "verdict": verdict,
        "xp_awarded": xp_awarded,
    }


async def suggest_debate_reply(db: Session, user: User, session_id: str) -> dict:
    """根据当前多角色场景与最新对方发言，生成 3 条英文参考回复。"""
    ensure_debate_tables(db)
    session = db.scalar(
        select(DebateSession).where(DebateSession.id == session_id, DebateSession.user_id == user.id)
    )
    if not session:
        raise AppError("未找到该多角色对话会话", code="DEBATE_NOT_FOUND", status_code=404)

    topic_row = db.scalar(select(DebateTopic).where(DebateTopic.id == session.topic_id))
    tools = _resolve_topic_tools(topic_row)
    if "rebuttal_hint" not in tools:
        raise AppError("当前场景未启用参考表达提示工具", code="DEBATE_TOOL_DISABLED", status_code=403)

    scene_type = (getattr(topic_row, "scene_type", None) if topic_row else None) or getattr(session, "scene_type", "debate") or "debate"
    stages = resolve_topic_stages(topic_row) if topic_row else resolve_topic_stages({"sceneType": scene_type})
    turns = _load_ordered_turns(db, session.id)
    stage = stages[min(len(stages) - 1, max(0, session.stage_index))]["label"]
    last_speaker = next((t.speaker for t in reversed(turns) if t.role != "user"), "the panel" if scene_type == "panel" else "the opponent")
    recent_lines = "\n".join(f"- {t.speaker} ({getattr(t, 'role_title', None) or t.role}): {t.en_text}" for t in turns[-5:])

    if scene_type == "panel":
        user_role = (getattr(topic_row, "user_role_label", None) if topic_row else None) or "Candidate / Proposer"
        fallback_items = (
            [
                {
                    "en": f"To anchor the discussion, let me walk through the core architecture and trade-offs I owned in this initiative.",
                    "zh": "总起框架：先给出整体背景与你主导的关键权衡。",
                },
                {
                    "en": "The clearest constraint we balanced was reliability versus delivery speed under peak traffic.",
                    "zh": "聚焦取舍：用一句话亮出最关键的平衡点。",
                },
                {
                    "en": "Happy to zoom into the metrics or cross-team alignment steps first—which would be more helpful?",
                    "zh": "主动引导：展现条理性，把深入方向交还给评审团队。",
                },
            ]
            if session.stage_index == 0
            else [
                {
                    "en": f"To answer {last_speaker}'s point directly, we validated that threshold with phased canary metrics first.",
                    "zh": f"正面回应 {last_speaker}：先给结论，再用灰度量化验证支撑。",
                },
                {
                    "en": "Rather than adding complexity upfront, we isolated the critical path and set clear rollback triggers.",
                    "zh": "稳健落地：强调风险隔离与回滚预案，打消工程/财务疑虑。",
                },
                {
                    "en": "In hindsight, aligning stakeholders earlier on success criteria saved two weeks of rework.",
                    "zh": "复盘视角：展示跨团队沟通意识与改进沉淀。",
                },
            ]
        )
        prompt = f"""You are a senior career & communication coach helping a learner respond in an English multi-role panel session.
Scenario: "{session.motion_en}"
Learner's role: {user_role}
Current stage: {stage}
Recent transcript:
{recent_lines}

Generate 3 distinct, natural, ready-to-speak English responses (1-2 sentences each) that directly answer {last_speaker}'s latest question and demonstrate clarity, ownership, and data awareness.
Respond ONLY with valid JSON (no markdown fences):
{{"suggestions": [{{"en": "...", "zh": "简短中文策略说明与译意"}}, ...]}}"""
    else:
        user_side_en = "Proposition (supporting)" if session.user_side == "pro" else "Opposition (opposing)"
        fallback_items = (
            [
                {
                    "en": f'Regarding "{session.motion_en}", I stand with the {user_side_en} because long-term practical outcomes matter most.',
                    "zh": "开篇立论：围绕核心长期实际影响亮明我方立场。",
                },
                {
                    "en": "Let us anchor this debate in a concrete workplace scenario rather than abstract assumptions.",
                    "zh": "限定场景：用真实场景锚定讨论前提。",
                },
                {
                    "en": "The core trade-off comes down to sustainability and human accountability.",
                    "zh": "提炼焦点：点明可持续性与人类责任这一核心权衡。",
                },
            ]
            if session.stage_index == 0
            else [
                {
                    "en": f"While {last_speaker} raises a fair concern, it overlooks how teams adapt workflows in practice.",
                    "zh": f"让步反驳 {last_speaker}：先肯定合理点，再指出其忽略的现实适配能力。",
                },
                {
                    "en": "That assumption holds only in extreme cases; under normal conditions, the net benefit remains clear.",
                    "zh": "限定边界：指出对方论据仅在极端情况下成立。",
                },
                {
                    "en": "To address your question directly, clear accountability standards resolve that trade-off.",
                    "zh": "正面回应：直接回答对手质询，给出可落地标准。",
                },
            ]
        )
        prompt = f"""You are a debate coach helping a learner reply in an English debate.
Motion: "{session.motion_en}"
Learner's side: {user_side_en}
Current stage: {stage}
Recent debate transcript:
{recent_lines}

Generate 3 distinct, natural, ready-to-speak English reply suggestions (1-2 sentences each) that directly respond to {last_speaker}'s latest argument and advance the learner's side.
Respond ONLY with valid JSON (no markdown fences):
{{"suggestions": [{{"en": "...", "zh": "简短中文策略说明与译意"}}, ...]}}"""

    try:
        llm = create_chat_model()
        resp = await llm.ainvoke(prompt)
        raw = str(getattr(resp, "content", "") or "").strip()
        if raw.startswith("```"):
            raw = raw.strip("`").lstrip("json").strip()
        parsed = json.loads(raw)
        items = parsed.get("suggestions") if isinstance(parsed, dict) else None
        if isinstance(items, list) and items:
            cleaned = [
                {"en": str(x.get("en") or "").strip(), "zh": str(x.get("zh") or "").strip()}
                for x in items[:3]
                if isinstance(x, dict) and str(x.get("en") or "").strip()
            ]
            if cleaned:
                return {"suggestions": cleaned}
    except Exception:
        pass
    return {"suggestions": fallback_items}

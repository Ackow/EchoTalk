"""练习会话基础 CRUD、历史列表与交互动作。"""
from copy import deepcopy
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.context import opening_message
from app.core.errors import AppError
from app.core.timeutil import utcnow
from app.models import DebateSession, DebateTurn, ListeningProgress, ListeningUnit, PracticeSession, PracticeTurn, User
from app.scenes.registry import validate
from app.services.scene_runtime import advance, initial_state
from app.services.scene_service import ensure_visible, load_scene


def owned_session(db: Session, session_id: str, user_id: int) -> PracticeSession:
    """按会话 ID 和当前用户 ID 查询会话；不存在或不属于本人时统一返回 404。"""
    row = db.scalar(select(PracticeSession).where(PracticeSession.id == session_id, PracticeSession.user_id == user_id))
    if row is None:
        raise AppError("练习会话不存在", code="SESSION_NOT_FOUND", status_code=404)
    return row


def public_session(row: PracticeSession) -> dict:
    """构造会话公开字段，不下发完整场景快照或内部 Agent 轨迹。"""
    package = validate(row.scene_snapshot)
    display = {
        "meta": package.meta.model_dump(mode="json"),
        "roles": [role.model_dump(mode="json") for role in package.roles if not role.backstage],
        "stages": [stage.model_dump(mode="json") for stage in package.stages],
        "objectives": [goal.model_dump(mode="json") for goal in package.objectives],
    }
    return {
        "id": row.id,
        "scene_id": row.scene_id,
        "greeting": row.greeting,
        "greeting_audio_url": f"/api/sessions/{row.id}/greeting-audio",
        "state": row.state_json,
        "version": row.version,
        "scene_display": display,
    }


def latest_session(db: Session, user: User, scene_id: str) -> dict | None:
    """返回当前用户该场景最近有实际轮次的会话；空会话不打扰选择。"""
    ensure_visible(load_scene(db, scene_id), user)
    row = db.scalar(
        select(PracticeSession)
        .join(PracticeTurn, PracticeTurn.session_id == PracticeSession.id)
        .where(PracticeSession.user_id == user.id, PracticeSession.scene_id == scene_id)
        .group_by(PracticeSession.id)
        .order_by(func.max(PracticeTurn.created_at).desc(), PracticeSession.id.desc())
        .limit(1)
    )
    return public_session(row) if row else None


def create_session(db: Session, user, scene_id: str) -> dict:
    """检查场景访问权限、冻结场景包并持久化一条新练习会话。"""
    scene = load_scene(db, scene_id)
    ensure_visible(scene, user)
    package = validate(scene.package_json)
    row = PracticeSession(
        id=str(uuid4()),
        user_id=user.id,
        scene_id=scene.id,
        scene_snapshot=package.model_dump(mode="json"),
        state_json=initial_state(package),
        greeting=opening_message(package),
        version=0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return public_session(row)


def _session_summary(row: PracticeSession, turn_count: int, last_at) -> dict:
    """由会话快照与运行状态构造历史列表条目，不校验整包以保证列表查询开销稳定。"""
    snapshot = row.scene_snapshot or {}
    meta = snapshot.get("meta") or {}
    state = row.state_json or {}
    stages = snapshot.get("stages") or []
    goals = state.get("goals") or []
    stage_ids = [stage.get("id") for stage in stages]
    stage_index = stage_ids.index(state.get("stage")) + 1 if state.get("stage") in stage_ids else 0
    return {
        "id": row.id,
        "scene_id": row.scene_id,
        "scene_name": meta.get("name") or row.scene_id,
        "category": meta.get("category"),
        "difficulty": meta.get("difficulty"),
        "description": meta.get("description") or "",
        "turn_count": turn_count,
        "goals_done": sum(1 for goal in goals if goal.get("done")),
        "goals_total": len(goals),
        "status": state.get("status") or "active",
        "finish_reason": state.get("finish_reason"),
        "stage_name": stages[stage_index - 1].get("name") if stage_index else None,
        "stage_index": stage_index,
        "stage_total": len(stages),
        "created_at": row.created_at,
        "last_active_at": last_at,
    }


def list_sessions(
    db: Session,
    user_id: int,
    *,
    scene_id: str | None = None,
    status: str | None = None,
    mode: str | None = None,
    page: int = 1,
    page_size: int = 12,
) -> dict:
    """分页读取本人有实际记录的练习历史（对话、听力、辩论），附带全局统计。"""
    target_mode = mode or "all"
    all_items: list[dict] = []

    # 1. 对话练习会话
    agg = (
        select(
            PracticeTurn.session_id.label("sid"),
            func.count().label("turns"),
            func.max(PracticeTurn.created_at).label("last_at"),
        )
        .group_by(PracticeTurn.session_id)
        .subquery()
    )
    conv_rows = db.execute(
        select(PracticeSession, agg.c.turns, agg.c.last_at)
        .join(agg, agg.c.sid == PracticeSession.id)
        .where(PracticeSession.user_id == user_id)
    ).all()
    conv_ids = [row.id for row, _, _ in conv_rows]
    conv_previews: dict[str, str] = {}
    if conv_ids:
        for sid, text in db.execute(
            select(PracticeTurn.session_id, PracticeTurn.input_text)
            .where(PracticeTurn.session_id.in_(conv_ids))
            .order_by(PracticeTurn.session_id, PracticeTurn.number.desc())
        ).all():
            conv_previews[sid] = text

    conv_items: list[dict] = []
    for row, turns, last_at in conv_rows:
        item = _session_summary(row, turns, last_at)
        item["record_type"] = "conversation"
        item["preview"] = (conv_previews.get(item["id"]) or "").strip().replace("\n", " ")[:80]
        conv_items.append(item)

    # 2. 多角色辩论会话
    DebateSession.__table__.create(bind=db.get_bind(), checkfirst=True)
    DebateTurn.__table__.create(bind=db.get_bind(), checkfirst=True)
    debate_rows = db.scalars(
        select(DebateSession).where(DebateSession.user_id == user_id)
    ).all()
    debate_items: list[dict] = []
    for d in debate_rows:
        if d.turn_count <= 1 and d.status != "finished":
            continue
        debate_items.append({
            "id": d.id,
            "record_type": "debate",
            "scene_id": d.topic_id,
            "scene_name": d.topic_title,
            "category": "debate",
            "difficulty": d.difficulty,
            "description": d.motion_en,
            "turn_count": d.turn_count,
            "goals_done": 1 if d.status == "finished" else 0,
            "goals_total": 1,
            "status": d.status,
            "finish_reason": None,
            "stage_name": f"胜率 {d.win_rate}%",
            "stage_index": min(4, d.stage_index + 1),
            "stage_total": 4,
            "created_at": d.created_at,
            "last_active_at": d.updated_at or d.created_at,
            "preview": d.motion_en[:80],
        })

    # 3. 听力工作室单元进度
    listening_rows = db.execute(
        select(ListeningProgress, ListeningUnit)
        .join(ListeningUnit, ListeningUnit.id == ListeningProgress.unit_id)
        .where(ListeningProgress.user_id == user_id, ListeningProgress.progress > 0)
    ).all()
    listening_items: list[dict] = []
    for prog, unit in listening_rows:
        listening_items.append({
            "id": f"listening:{unit.id}",
            "record_type": "listening",
            "scene_id": unit.id,
            "scene_name": unit.title,
            "category": "listening",
            "difficulty": "intermediate",
            "description": unit.subtitle,
            "turn_count": max(1, prog.completed_count or 1),
            "goals_done": 1 if prog.progress >= 100 else 0,
            "goals_total": 1,
            "status": "finished" if prog.progress >= 100 else "active",
            "finish_reason": None,
            "stage_name": f"完成度 {prog.progress}%",
            "stage_index": 1 if prog.progress >= 100 else 0,
            "stage_total": 1,
            "created_at": prog.updated_at,
            "last_active_at": prog.updated_at,
            "preview": (unit.subtitle or unit.channel_label)[:80],
        })

    all_records = conv_items + debate_items + listening_items
    stats = {
        "sessions": len(all_records),
        "turns": sum(int(item.get("turn_count") or 0) for item in all_records),
        "finished": sum(1 for item in all_records if item.get("status") == "finished"),
    }

    filtered = all_records
    if target_mode != "all":
        filtered = [item for item in filtered if item.get("record_type") == target_mode]
    if scene_id:
        filtered = [item for item in filtered if item.get("scene_id") == scene_id]
    if status:
        filtered = [item for item in filtered if item.get("status") == status]

    filtered.sort(key=lambda item: item.get("last_active_at") or utcnow(), reverse=True)
    total = len(filtered)
    start = (page - 1) * page_size
    paged = filtered[start : start + page_size]

    return {"items": paged, "total": total, "page": page, "page_size": page_size, "stats": stats}


def _user_audio_path(turn_id: str):
    from app.core import config

    return config.BACKEND_DIR / "storage" / "turn_audio" / f"{turn_id}.wav"


def get_session(db: Session, user_id: int, session_id: str) -> dict:
    """读取本人会话和按轮次排序的公开对话记录，用于页面恢复。"""
    row = owned_session(db, session_id, user_id)
    turns = db.scalars(select(PracticeTurn).where(PracticeTurn.session_id == session_id).order_by(PracticeTurn.number)).all()
    return {
        **public_session(row),
        "turns": [
            {
                **t.response_json,
                "pronunciation_score": t.pronunciation_score,
                "grammar_correction": t.grammar_correction,
                "has_user_audio": _user_audio_path(t.id).exists(),
            }
            for t in turns
        ],
    }


def apply_session_action(db: Session, user_id: int, session_id: str, action: str, payload: dict | None = None) -> dict:
    """执行场景交互动作（如点餐付款确认、结束确认），推进场景状态并持久化。"""
    row = owned_session(db, session_id, user_id)
    package = validate(row.scene_snapshot)
    state = deepcopy(row.state_json)
    before = deepcopy(state.get("scenario_state", {}))
    scenario_state = state.setdefault("scenario_state", {})
    payload = payload or {}

    if action == "pay":
        if "confirmed" in scenario_state:
            scenario_state["confirmed"] = True
        scenario_state["paid"] = True
        scenario_state["payment_method"] = str(payload.get("method") or "card")
        if payload.get("amount") not in (None, ""):
            scenario_state["paid_amount"] = str(payload["amount"])
    elif action == "finish":
        updates = payload.get("state_updates")
        if isinstance(updates, dict):
            for key, value in updates.items():
                if key in package.state or key in ("selected_option", "self_rating"):
                    scenario_state[key] = value
        state["finish_reason"] = state.get("finish_reason") or "condition_met"
        state["status"] = "finished"
    else:
        raise AppError("不支持的会话交互动作", code="INVALID_SESSION_ACTION", status_code=400)

    state["tool_results"] = []
    state.update(advance(package, state, before))
    if action in ("pay", "finish") and state.get("status") != "finished":
        state["finish_reason"] = state.get("finish_reason") or "condition_met"
        state["status"] = "finished"
    if state.get("status") == "finished" and package.stages and state.get("stage") != package.stages[-1].id:
        state["stage"] = package.stages[-1].id
        state["stage_turns"] = 0

    row.state_json = state
    row.version += 1
    row.updated_at = utcnow()
    db.commit()
    db.refresh(row)
    return {"session": public_session(row)}

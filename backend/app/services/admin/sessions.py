"""管理端对话记录管理：列表查询、详情排查与单条/批量删除。"""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import PracticeSession, PracticeTurn, User


def list_sessions(
    db: Session,
    *,
    user_id: int | None = None,
    scene_id: str | None = None,
    status: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """分页查询全平台用户的练习对话记录。"""
    turn_agg = (
        select(
            PracticeTurn.session_id.label("sid"),
            func.count().label("turns"),
            func.max(PracticeTurn.created_at).label("last_at"),
        )
        .group_by(PracticeTurn.session_id)
        .subquery()
    )
    conditions = []
    if user_id is not None:
        conditions.append(PracticeSession.user_id == user_id)
    if scene_id:
        conditions.append(PracticeSession.scene_id == scene_id)
    if status:
        conditions.append(PracticeSession.state_json["status"].as_string() == status)
    if q and q.strip():
        kw = f"%{q.strip()}%"
        conditions.append(or_(User.username.ilike(kw), PracticeSession.scene_id.ilike(kw), PracticeSession.id.ilike(kw)))

    total = (
        db.scalar(
            select(func.count())
            .select_from(PracticeSession)
            .join(User, User.id == PracticeSession.user_id)
            .where(*conditions)
        )
        or 0
    )
    rows = db.execute(
        select(PracticeSession, User.username, turn_agg.c.turns, turn_agg.c.last_at)
        .join(User, User.id == PracticeSession.user_id)
        .outerjoin(turn_agg, turn_agg.c.sid == PracticeSession.id)
        .where(*conditions)
        .order_by(func.coalesce(turn_agg.c.last_at, PracticeSession.created_at).desc(), PracticeSession.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    items = []
    for ps, uname, turns, last_at in rows:
        snapshot = ps.scene_snapshot or {}
        meta = snapshot.get("meta") or {}
        state = ps.state_json or {}
        stages = snapshot.get("stages") or []
        goals = state.get("goals") or []
        stage_ids = [s.get("id") for s in stages]
        stage_index = stage_ids.index(state.get("stage")) + 1 if state.get("stage") in stage_ids else 0
        items.append(
            {
                "id": ps.id,
                "user_id": ps.user_id,
                "username": uname,
                "scene_id": ps.scene_id,
                "scene_name": meta.get("name") or ps.scene_id,
                "category": meta.get("category"),
                "difficulty": meta.get("difficulty"),
                "turn_count": turns or 0,
                "goals_done": sum(1 for g in goals if g.get("done")),
                "goals_total": len(goals),
                "status": state.get("status") or "active",
                "finish_reason": state.get("finish_reason"),
                "stage_name": stages[stage_index - 1].get("name") if stage_index else None,
                "stage_index": stage_index,
                "stage_total": len(stages),
                "created_at": ps.created_at,
                "last_active_at": last_at or ps.created_at,
            }
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def get_session_detail(db: Session, session_id: str) -> dict:
    """获取单条对话会话及完整轮次记录（含 trace_json 供管理员排查）。"""
    row = db.execute(
        select(PracticeSession, User.username)
        .join(User, User.id == PracticeSession.user_id)
        .where(PracticeSession.id == session_id)
    ).first()
    if row is None:
        raise AppError("对话记录不存在", code="SESSION_NOT_FOUND", status_code=404)
    ps, uname = row
    turns = db.scalars(
        select(PracticeTurn).where(PracticeTurn.session_id == session_id).order_by(PracticeTurn.number.asc())
    ).all()
    snapshot = ps.scene_snapshot or {}
    meta = snapshot.get("meta") or {}
    return {
        "id": ps.id,
        "user_id": ps.user_id,
        "username": uname,
        "scene_id": ps.scene_id,
        "scene_name": meta.get("name") or ps.scene_id,
        "greeting": ps.greeting,
        "state": ps.state_json or {},
        "version": ps.version,
        "created_at": ps.created_at,
        "turns": [
            {
                "id": t.id,
                "number": t.number,
                "input_text": t.input_text,
                "response": t.response_json,
                "trace": t.trace_json,
                "created_at": t.created_at,
            }
            for t in turns
        ],
    }


def delete_session(db: Session, session_id: str) -> None:
    """删除对话会话及其所有轮次。"""
    ps = db.get(PracticeSession, session_id)
    if ps is None:
        raise AppError("对话记录不存在", code="SESSION_NOT_FOUND", status_code=404)
    db.query(PracticeTurn).filter(PracticeTurn.session_id == session_id).delete(synchronize_session=False)
    db.delete(ps)
    db.commit()


def batch_delete_sessions(db: Session, session_ids: list[str]) -> dict:
    """批量删除对话会话及其所有轮次。"""
    unique_ids = list(dict.fromkeys(session_ids))
    if not unique_ids:
        return {"deleted": 0}
    db.query(PracticeTurn).filter(PracticeTurn.session_id.in_(unique_ids)).delete(synchronize_session=False)
    deleted = db.query(PracticeSession).filter(PracticeSession.id.in_(unique_ids)).delete(synchronize_session=False)
    db.commit()
    return {"deleted": deleted}

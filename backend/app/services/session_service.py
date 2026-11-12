"""练习会话与 Agent 的应用编排；网络调用期间不占用数据库事务。"""
from copy import deepcopy
import logging
import time
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.agents.context import opening_message
from app.agents.conversation import build_conversation_graph
from app.agents.model_gateway import create_chat_model
from app.agents.tools import ToolRegistry
from app.core.errors import AppError
from app.core.timeutil import utcnow
from app.models import PracticeSession, PracticeTurn, User
from app.scenes.registry import validate
from app.services.scene_runtime import advance, initial_state
from app.services.scene_service import ensure_visible, load_scene

logger = logging.getLogger("echotalk")


def owned_session(db: Session, session_id: str, user_id: int) -> PracticeSession:
    """按会话 ID 和当前用户 ID 查询会话；不存在或不属于本人时统一返回 404。"""
    row = db.scalar(select(PracticeSession).where(PracticeSession.id == session_id, PracticeSession.user_id == user_id))
    if row is None:
        raise AppError("练习会话不存在", code="SESSION_NOT_FOUND", status_code=404)
    return row


def public_session(row: PracticeSession) -> dict:
    """构造会话公开字段，不下发完整场景快照或内部 Agent 轨迹。"""
    package = validate(row.scene_snapshot)
    display = {"meta": package.meta.model_dump(mode="json"), "roles": [role.model_dump(mode="json") for role in package.roles if not role.backstage], "stages": [stage.model_dump(mode="json") for stage in package.stages], "objectives": [goal.model_dump(mode="json") for goal in package.objectives]}
    return {"id": row.id, "scene_id": row.scene_id, "greeting": row.greeting, "greeting_audio_url": f"/api/sessions/{row.id}/greeting-audio", "state": row.state_json, "version": row.version, "scene_display": display}


def latest_session(db: Session, user: User, scene_id: str) -> dict | None:
    """返回当前用户该场景最近有实际轮次的会话；空会话不打扰选择。"""
    ensure_visible(load_scene(db, scene_id), user)
    row = db.scalar(select(PracticeSession).join(PracticeTurn, PracticeTurn.session_id == PracticeSession.id)
                    .where(PracticeSession.user_id == user.id, PracticeSession.scene_id == scene_id)
                    .group_by(PracticeSession.id).order_by(func.max(PracticeTurn.created_at).desc(), PracticeSession.id.desc()).limit(1))
    return public_session(row) if row else None


def create_session(db: Session, user, scene_id: str) -> dict:
    """检查场景访问权限、冻结场景包并持久化一条新练习会话。"""
    scene = load_scene(db, scene_id)
    ensure_visible(scene, user)
    package = validate(scene.package_json)
    row = PracticeSession(
        id=str(uuid4()), user_id=user.id, scene_id=scene.id,
        scene_snapshot=package.model_dump(mode="json"), state_json=initial_state(package),
        greeting=opening_message(package), version=0,
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
        "id": row.id, "scene_id": row.scene_id,
        "scene_name": meta.get("name") or row.scene_id, "category": meta.get("category"),
        "difficulty": meta.get("difficulty"), "description": meta.get("description") or "",
        "turn_count": turn_count, "goals_done": sum(1 for goal in goals if goal.get("done")), "goals_total": len(goals),
        "status": state.get("status") or "active", "finish_reason": state.get("finish_reason"),
        "stage_name": stages[stage_index - 1].get("name") if stage_index else None,
        "stage_index": stage_index, "stage_total": len(stages),
        "created_at": row.created_at, "last_active_at": last_at,
    }


def list_sessions(db: Session, user_id: int, *, scene_id: str | None = None, status: str | None = None, page: int = 1, page_size: int = 12) -> dict:
    """分页读取本人有实际轮次的会话，附带最后一轮预览与全局统计。

    空会话（创建后未发言）不计入历史；统计口径与筛选条件无关，始终反映全部记录。
    """
    agg = (select(PracticeTurn.session_id.label("sid"), func.count().label("turns"), func.max(PracticeTurn.created_at).label("last_at"))
           .group_by(PracticeTurn.session_id).subquery())
    conditions = [PracticeSession.user_id == user_id]
    if scene_id:
        conditions.append(PracticeSession.scene_id == scene_id)
    if status:
        conditions.append(PracticeSession.state_json["status"].as_string() == status)  # MySQL JSON 提取，状态由程序写入
    total = db.scalar(select(func.count()).select_from(PracticeSession).join(agg, agg.c.sid == PracticeSession.id).where(*conditions)) or 0
    rows = db.execute(select(PracticeSession, agg.c.turns, agg.c.last_at).join(agg, agg.c.sid == PracticeSession.id)
                      .where(*conditions).order_by(agg.c.last_at.desc(), PracticeSession.id.desc())
                      .offset((page - 1) * page_size).limit(page_size)).all()
    items = [_session_summary(row, turns, last_at) for row, turns, last_at in rows]
    # 最后一轮预览：只查当前页会话，按轮次倒序后取每个会话的首条
    previews: dict[str, str] = {}
    ids = [item["id"] for item in items]
    if ids:
        for sid, text in db.execute(select(PracticeTurn.session_id, PracticeTurn.input_text)
                                    .where(PracticeTurn.session_id.in_(ids)).order_by(PracticeTurn.session_id, PracticeTurn.number.desc())).all():
            previews[sid] = text
        for item in items:
            item["preview"] = (previews.get(item["id"]) or "").strip().replace("\n", " ")[:80]
    joined = PracticeSession.id.in_(select(PracticeTurn.session_id))
    stats = {
        "sessions": db.scalar(select(func.count()).select_from(PracticeSession).where(PracticeSession.user_id == user_id, joined)) or 0,
        "turns": db.scalar(select(func.count()).select_from(PracticeTurn).join(PracticeSession, PracticeSession.id == PracticeTurn.session_id)
                           .where(PracticeSession.user_id == user_id)) or 0,
        "finished": db.scalar(select(func.count()).select_from(PracticeSession).where(
            PracticeSession.user_id == user_id, joined, PracticeSession.state_json["status"].as_string() == "finished")) or 0,
    }
    return {"items": items, "total": total, "page": page, "page_size": page_size, "stats": stats}


def get_session(db: Session, user_id: int, session_id: str) -> dict:
    """读取本人会话和按轮次排序的公开对话记录，用于页面恢复。"""
    row = owned_session(db, session_id, user_id)
    turns = db.scalars(select(PracticeTurn).where(PracticeTurn.session_id == session_id).order_by(PracticeTurn.number)).all()
    return {**public_session(row), "turns": [t.response_json for t in turns]}


def run_turn(db: Session, user_id: int, session_id: str, request_id: str, text: str, *, model=None, search=None) -> dict:
    """运行一个文字轮次，并以版本比较原子提交状态、回复和工具轨迹。

    request_id 提供安全重试；模型调用期间释放数据库读取事务。model/search
    可在离线测试中注入，线上默认使用配置模型和场景 Hybrid 检索。
    """
    row = owned_session(db, session_id, user_id)
    existing = db.scalar(select(PracticeTurn).where(PracticeTurn.session_id == session_id, PracticeTurn.request_id == request_id))
    if existing:
        if existing.input_text != text:
            raise AppError("同一 request_id 不能用于不同输入", code="TURN_ID_CONFLICT", status_code=409)
        return existing.response_json
    if row.state_json["status"] != "active":
        raise AppError("本次练习已结束", code="SESSION_FINISHED", status_code=409)
    package, version = validate(deepcopy(row.scene_snapshot)), row.version
    state, greeting = deepcopy(row.state_json), row.greeting
    # 按完整轮次截取，避免残缺工具消息；工具内部消息不写入聊天历史。
    recent = list(reversed(db.scalars(select(PracticeTurn).where(PracticeTurn.session_id == session_id).order_by(PracticeTurn.number.desc()).limit(8)).all()))
    messages = [AIMessage(greeting)] if greeting else []
    for turn in recent:
        messages.extend([HumanMessage(turn.input_text), AIMessage(turn.response_json["text"])])
    db.rollback()  # 释放读取事务和连接，再进入模型调用
    messages.append(HumanMessage(text))
    before = deepcopy(state["scenario_state"])
    state.update(messages=messages, tool_results=[], model_calls=0, final_text="")
    state["turn_count"] += 1
    state["stage_turns"] += 1
    # 先检查当前轮数/已有状态，模型可在达到上限的本轮直接收尾。
    state.update(advance(package, state, before))

    if search is None:
        def search(query, top_k):
            """用独立数据库连接执行场景检索，并再次验证当前资料访问权限。"""
            # 独立连接：现有检索可能补建索引并提交，不影响会话提交事务。
            from app.scenes.retrieval import search_scene
            with Session(bind=db.get_bind()) as read_db:
                # 发布状态可能在创建会话后变化，历史快照不授予继续读取资料的权限。
                scene = load_scene(read_db, package.meta.id)
                ensure_visible(scene, read_db.get(User, user_id))
                return search_scene(read_db, package.meta.id, query, top_k)

    registry = ToolRegistry(package, text, search)
    graph = build_conversation_graph(package, model if model is not None else create_chat_model(), registry, before)
    started = time.perf_counter()
    result = graph.invoke(state, {"recursion_limit": 16})
    logger.info("对话轮次执行耗时 %.2fs，模型调用 %d 次，工具调用 %d 次", time.perf_counter() - started, result["model_calls"], len(result["tool_results"]))
    saved_state = {key: result[key] for key in initial_state(package)}
    turn_id = str(uuid4())
    response = {
        "session_id": session_id, "turn_id": turn_id, "request_id": request_id,
        "number": result["turn_count"], "input_text": text, "text": result["final_text"],
        "state": saved_state, "version": version + 1,
    }
    # CAS：并发请求至多一个提交，所有工具变更此前仅作用于本轮内存。
    changed = db.execute(update(PracticeSession).where(
        PracticeSession.id == session_id, PracticeSession.user_id == user_id, PracticeSession.version == version,
    ).values(state_json=saved_state, version=version + 1))
    if changed.rowcount != 1:
        db.rollback()
        winner = db.scalar(select(PracticeTurn).where(PracticeTurn.session_id == session_id, PracticeTurn.request_id == request_id))
        if winner and winner.input_text == text:
            return winner.response_json
        raise AppError("会话已更新，请刷新后重试", code="SESSION_VERSION_CONFLICT", status_code=409)
    db.add(PracticeTurn(
        id=turn_id, session_id=session_id, request_id=request_id, number=result["turn_count"],
        input_text=text, response_json=response, trace_json=result["tool_results"], created_at=utcnow(),
    ))
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return response

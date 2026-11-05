"""练习会话与 Agent 的应用编排；网络调用期间不占用数据库事务。"""
from copy import deepcopy
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import select, update
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


def owned_session(db: Session, session_id: str, user_id: int) -> PracticeSession:
    """按会话 ID 和当前用户 ID 查询会话；不存在或不属于本人时统一返回 404。"""
    row = db.scalar(select(PracticeSession).where(PracticeSession.id == session_id, PracticeSession.user_id == user_id))
    if row is None:
        raise AppError("练习会话不存在", code="SESSION_NOT_FOUND", status_code=404)
    return row


def public_session(row: PracticeSession) -> dict:
    """构造会话公开字段，不下发完整场景快照或内部 Agent 轨迹。"""
    return {"id": row.id, "scene_id": row.scene_id, "greeting": row.greeting, "greeting_audio_url": f"/api/sessions/{row.id}/greeting-audio", "state": row.state_json, "version": row.version}


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
    result = graph.invoke(state, {"recursion_limit": 16})
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

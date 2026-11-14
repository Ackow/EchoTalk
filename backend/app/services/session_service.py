"""练习会话与 Agent 的应用编排；网络调用期间不占用数据库事务。"""
import asyncio
import base64
from copy import deepcopy
import json
import logging
import re
import time
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.agents.context import opening_message
from app.agents.conversation import build_async_conversation_graph, build_conversation_graph
from app.agents.model_gateway import create_chat_model
from app.agents.tools import ToolRegistry
from app.core.errors import AppError
from app.core.timeutil import utcnow
from app.models import PracticeSession, PracticeTurn, User
from app.scenes.registry import validate
from app.services.scene_runtime import advance, initial_state
from app.services.scene_service import ensure_visible, load_scene
from app.services.token_usage_service import extract_langchain_usage, record_usage

logger = logging.getLogger("echotalk")
_POLITE_RE = re.compile(r"\b(?:please|could i|could you|would you|would like|i'd like|may i|thank you|thanks|appreciate)\b", re.IGNORECASE)


def _auto_detect_turn_signals(text: str, scenario_state: dict) -> None:
    """对明确可由用户输入判定的礼貌请求信号做兜底同步，避免模型漏调工具导致目标未亮。"""
    if isinstance(scenario_state.get("polite_request"), bool) and not scenario_state["polite_request"]:
        if _POLITE_RE.search(text or ""):
            scenario_state["polite_request"] = True


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


def get_session_report(db: Session, user_id: int, session_id: str) -> dict:
    """汇总本场练习的多维评分报告（充分利用讯飞 ISE 发音/语调/连读/流利度/逐词分 + 语法纠错 + 目标完成度）。"""
    row = owned_session(db, session_id, user_id)
    turns = db.scalars(select(PracticeTurn).where(PracticeTurn.session_id == session_id).order_by(PracticeTurn.number)).all()
    state = row.state_json or {}
    snapshot = row.scene_snapshot or {}
    meta = snapshot.get("meta") or {}
    goals = state.get("goals") or []
    goals_done = sum(1 for g in goals if g.get("done"))
    goals_total = len(goals)
    task_score = round(goals_done / goals_total * 100) if goals_total else 100

    voice_scores = [t.pronunciation_score for t in turns if isinstance(t.pronunciation_score, dict)]
    grammar_items = [t for t in turns if isinstance(t.grammar_correction, dict)]

    def _avg(key: str) -> float | None:
        vals = [float(s[key]) for s in voice_scores if s.get(key) is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    pronunciation_dims = None
    weak_words: list[dict] = []
    strong_words: list[dict] = []
    turn_scores: list[dict] = []
    if voice_scores:
        for t in turns:
            ps = t.pronunciation_score
            if not isinstance(ps, dict):
                continue
            turn_scores.append({
                "turn": t.number,
                "total": round(float(ps.get("total_score") or 0), 1),
                "accuracy": round(float(ps.get("accuracy_score") or 0), 1),
                "fluency": round(float(ps.get("fluency_score") or 0), 1),
                "wpm": round(float(ps.get("speech_rate_wpm") or 0)),
            })
        avg_wpm = _avg("speech_rate_wpm")
        rate_level = "unknown"
        if avg_wpm is not None:
            rate_level = "slow" if avg_wpm < 100 else ("natural" if avg_wpm <= 150 else "fast")
        pronunciation_dims = {
            "voice_turn_count": len(voice_scores),
            "total_score": _avg("total_score"),
            "accuracy_score": _avg("accuracy_score"),
            "fluency_score": _avg("fluency_score"),
            "integrity_score": _avg("integrity_score"),
            "intonation_score": _avg("intonation_score"),
            "liaison_score": _avg("liaison_score"),
            "avg_wpm": round(avg_wpm) if avg_wpm is not None else 0,
            "rate_level": rate_level,
            "has_mock": any(bool(s.get("is_mock")) for s in voice_scores),
        }
        word_best: dict[str, float] = {}
        word_worst: dict[str, float] = {}
        for s in voice_scores:
            for w in s.get("words") or []:
                word_txt = str(w.get("word") or "").strip()
                raw_score = w.get("score") if w.get("score") is not None else w.get("total_score")
                if not word_txt or raw_score is None:
                    continue
                val = round(float(raw_score), 1)
                key = word_txt.lower()
                if key not in word_worst or val < word_worst[key][1]:
                    word_worst[key] = (word_txt, val)
                if key not in word_best or val > word_best[key][1]:
                    word_best[key] = (word_txt, val)
        weak_words = [{"word": txt, "score": sc} for txt, sc in sorted(word_worst.values(), key=lambda x: x[1]) if sc < 78][:8]
        strong_words = [{"word": txt, "score": sc} for txt, sc in sorted(word_best.values(), key=lambda x: -x[1]) if sc >= 88][:6]

    corrections: list[dict] = []
    natural_count = 0
    for t in grammar_items:
        gc = t.grammar_correction
        if gc.get("has_error"):
            corrections.append({
                "turn_number": t.number,
                "original": gc.get("original") or t.input_text,
                "corrected": gc.get("corrected") or "",
                "issue_type": gc.get("issue_type") or "grammar",
                "explanation": gc.get("explanation") or "",
                "better_expressions": gc.get("better_expressions") or [],
            })
        else:
            natural_count += 1

    grammar_score = round((natural_count + len(corrections) * 0.55) / len(grammar_items) * 100) if grammar_items else (85 if turns else 0)

    if pronunciation_dims and pronunciation_dims["total_score"] is not None:
        overall_score = round(
            pronunciation_dims["total_score"] * 0.5
            + grammar_score * 0.3
            + task_score * 0.2
        )
    elif turns:
        overall_score = round(grammar_score * 0.65 + task_score * 0.35)
    else:
        overall_score = 0

    tips: list[str] = []
    if pronunciation_dims:
        dim_map = [
            ("accuracy_score", "发音准确度"),
            ("fluency_score", "口语流利度"),
            ("intonation_score", "语调韵律"),
            ("liaison_score", "连读自然度"),
        ]
        valid_dims = [(label, pronunciation_dims[k]) for k, label in dim_map if pronunciation_dims.get(k) is not None]
        if valid_dims:
            lowest_label, lowest_val = min(valid_dims, key=lambda x: x[1])
            if lowest_val < 85:
                tips.append(f"本次语音评测中「{lowest_label}」（{lowest_val} 分）相对有提升空间，可针对性跟读回放。")
        if pronunciation_dims["rate_level"] == "slow":
            tips.append(f"平均语速为 {pronunciation_dims['avg_wpm']} WPM（偏慢），建议成组连贯说出意群，减少词间停顿。")
        elif pronunciation_dims["rate_level"] == "fast":
            tips.append(f"平均语速为 {pronunciation_dims['avg_wpm']} WPM（偏快），注意句尾重读与元音饱满度。")
    if weak_words:
        tips.append("重点巩固低分词汇：" + "、".join(w["word"] for w in weak_words[:4]) + "。")
    if corrections:
        tips.append(f"共发现 {len(corrections)} 处可优化表达，建议结合推荐句型再朗读一遍。")
    if not tips and turns:
        tips.append("整体发音清晰自然，表达贴合场景，继续保持当前节奏！")

    return {
        "session_id": row.id,
        "scene_name": meta.get("name") or row.scene_id,
        "status": state.get("status") or "active",
        "turn_count": len(turns),
        "overall_score": overall_score,
        "task_score": task_score,
        "goals_done": goals_done,
        "goals_total": goals_total,
        "grammar_score": grammar_score,
        "pronunciation": pronunciation_dims,
        "turn_scores": turn_scores,
        "weak_words": weak_words,
        "strong_words": strong_words,
        "corrections": corrections,
        "tips": tips,
    }


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
    _auto_detect_turn_signals(text, state["scenario_state"])
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
    if saved_state.get("status") == "finished" and package.stages:
        saved_state["stage"] = package.stages[-1].id
        saved_state["stage_turns"] = 0
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
    usage = extract_langchain_usage(result["messages"][len(messages):])
    record_usage(
        db,
        category="chat",
        model=usage["model"],
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
        total_tokens=usage["total_tokens"],
        call_count=usage["call_count"],
        user_id=user_id,
        session_id=session_id,
        scene_id=package.meta.id,
        turn_id=turn_id,
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return response


class _SentenceBuffer:
    """增量切句缓冲：遇到完整句末标点或换行时尽早切出句子供并行 TTS 合成。"""

    _BOUNDARY = re.compile(r"(?<=[。！？!?]|(?<!\d)\.(?!\d))\s+|\n+")

    def __init__(self) -> None:
        self._buf = ""

    def push(self, delta: str) -> list[str]:
        self._buf += delta
        out: list[str] = []
        while True:
            m = self._BOUNDARY.search(self._buf)
            if not m:
                break
            head = self._buf[: m.start()].strip()
            tail = self._buf[m.end() :]
            # 过短缩写（如 "Mr."、"Dr."、"No."）等下一句合并
            if len(head) < 10 and not head.endswith(("!", "?", "！", "？", "。")):
                break
            if head:
                out.append(head)
            self._buf = tail
        return out

    def flush(self) -> str | None:
        rest = self._buf.strip()
        self._buf = ""
        return rest or None


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _evaluate_grammar(
    package,
    text: str,
    recent_turns: list[PracticeTurn],
    greeting: str | None = None,
) -> dict:
    """并行评估学习者本轮英语表达的语法准确性与地道程度，不阻塞主回复流。"""
    cleaned_input = (text or "").strip()
    if not cleaned_input:
        return {"has_error": False, "original": text, "corrected": text, "issue_type": "none", "explanation": "", "better_expressions": []}

    context_lines: list[str] = []
    if greeting:
        context_lines.append(f"Partner: {greeting}")
    for t in recent_turns[-3:]:
        context_lines.append(f"Learner: {t.input_text}")
        context_lines.append(f"Partner: {t.response_json.get('text', '')}")

    system_msg = (
        "You are an expert English speaking coach inside EchoTalk. "
        "Evaluate ONLY the learner's latest spoken/written utterance for grammar errors, awkward phrasing, or unnatural expressions. "
        "CRITICAL RULES:\n"
        "1. Preserve the learner's exact intent, proper nouns, menu items, quantities, and factual choices—never change what they ordered or decided.\n"
        "2. If the utterance is already grammatical and natural for casual spoken English, set has_error to false and issue_type to 'none'.\n"
        "3. If there is a grammar mistake (tense, agreement, article, preposition, word order), set has_error=true, issue_type='grammar'.\n"
        "4. If grammar is okay but phrasing is unnatural/Chinglish/too stiff for spoken English, set has_error=true, issue_type='naturalness'.\n"
        "5. Return STRICT JSON only (no markdown fences):\n"
        '{"has_error": true|false, "corrected": "corrected or more natural sentence", '
        '"issue_type": "none"|"grammar"|"naturalness", '
        '"explanation": "1-2 concise sentences in Chinese explaining the fix", '
        '"better_expressions": ["1-2 short natural spoken alternatives"]}'
    )
    user_msg = (
        f"Scenario: {package.meta.name}\n"
        "Recent context:\n"
        + ("\n".join(context_lines) if context_lines else "(First turn)")
        + f"\n\nLearner's latest utterance:\n{cleaned_input}"
    )

    try:
        model = create_chat_model()
        ai_msg = await model.ainvoke([("system", system_msg), ("human", user_msg)])
        raw = ai_msg.content if isinstance(ai_msg.content, str) else str(ai_msg.content)
        stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE | re.MULTILINE).strip()
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise ValueError("invalid grammar json")
        has_error = bool(parsed.get("has_error", False))
        issue_type = str(parsed.get("issue_type") or ("grammar" if has_error else "none")).strip().lower()
        if issue_type not in {"none", "grammar", "naturalness"}:
            issue_type = "grammar" if has_error else "none"
        corrected = str(parsed.get("corrected") or cleaned_input).strip()
        explanation = str(parsed.get("explanation") or "").strip()
        better = parsed.get("better_expressions") or []
        if not isinstance(better, list):
            better = []
        better_list = [str(item).strip() for item in better[:2] if str(item).strip()]
        return {
            "has_error": has_error,
            "original": cleaned_input,
            "corrected": corrected,
            "issue_type": issue_type,
            "explanation": explanation,
            "better_expressions": better_list,
        }
    except Exception:
        return {
            "has_error": False,
            "original": cleaned_input,
            "corrected": cleaned_input,
            "issue_type": "none",
            "explanation": "",
            "better_expressions": [],
        }


async def stream_turn(
    bind,
    user_id: int,
    session_id: str,
    request_id: str,
    text: str,
    *,
    voice_style: str | None = None,
    include_audio: bool = True,
    audio_token: str | None = None,
):
    """流式执行一轮对话（SSE）：边生成文本边按句并行合成并逐步下发 MP3 分段，同时并行执行语法纠错与发音评估。"""
    from app.services import pronunciation_service, tts_service

    with Session(bind=bind) as read_db:
        row = owned_session(read_db, session_id, user_id)
        existing = read_db.scalar(
            select(PracticeTurn).where(PracticeTurn.session_id == session_id, PracticeTurn.request_id == request_id)
        )
        if existing:
            if existing.input_text != text:
                raise AppError("同一 request_id 不能用于不同输入", code="TURN_ID_CONFLICT", status_code=409)
            cached_resp = existing.response_json
            yield _sse("delta", {"text": cached_resp["text"]})
            yield _sse("done", cached_resp)
            if existing.grammar_correction:
                yield _sse("correction", existing.grammar_correction)
            if existing.pronunciation_score:
                yield _sse("pronunciation", existing.pronunciation_score)
            if include_audio and voice_style:
                try:
                    audio = await tts_service.synthesize(cached_resp["text"], voice_style, 1.0)
                    yield _sse("audio", {"index": 0, "text": cached_resp["text"], "audio_b64": base64.b64encode(audio).decode("ascii")})
                except Exception as exc:
                    yield _sse("audio_error", {"index": 0, "message": getattr(exc, "message", str(exc))})
            yield _sse("audio_end", {})
            return
        if row.state_json["status"] != "active":
            raise AppError("本次练习已结束", code="SESSION_FINISHED", status_code=409)
        package, version = validate(deepcopy(row.scene_snapshot)), row.version
        state, greeting = deepcopy(row.state_json), row.greeting
        recent = list(
            reversed(
                read_db.scalars(
                    select(PracticeTurn)
                    .where(PracticeTurn.session_id == session_id)
                    .order_by(PracticeTurn.number.desc())
                    .limit(8)
                ).all()
            )
        )

    messages = [AIMessage(greeting)] if greeting else []
    for turn in recent:
        messages.extend([HumanMessage(turn.input_text), AIMessage(turn.response_json["text"])])
    messages.append(HumanMessage(text))
    before = deepcopy(state["scenario_state"])
    _auto_detect_turn_signals(text, state["scenario_state"])
    state.update(messages=messages, tool_results=[], model_calls=0, final_text="")
    state["turn_count"] += 1
    state["stage_turns"] += 1
    state.update(advance(package, state, before))

    def search(query, top_k):
        from app.scenes.retrieval import search_scene
        with Session(bind=bind) as rdb:
            scene = load_scene(rdb, package.meta.id)
            ensure_visible(scene, rdb.get(User, user_id))
            return search_scene(rdb, package.meta.id, query, top_k)

    queue: asyncio.Queue = asyncio.Queue()
    registry = ToolRegistry(package, text, search)

    async def on_delta(delta: str):
        await queue.put(("delta", delta))

    graph = build_async_conversation_graph(package, create_chat_model(), registry, before, on_delta=on_delta)

    async def run_graph():
        started = time.perf_counter()
        try:
            result = await graph.ainvoke(state, {"recursion_limit": 16})
            logger.info(
                "流式对话轮次耗时 %.2fs，模型调用 %d 次，工具调用 %d 次",
                time.perf_counter() - started,
                result["model_calls"],
                len(result["tool_results"]),
            )
            saved_state = {key: result[key] for key in initial_state(package)}
            if saved_state.get("status") == "finished" and package.stages:
                saved_state["stage"] = package.stages[-1].id
                saved_state["stage_turns"] = 0
            turn_id = str(uuid4())
            response = {
                "session_id": session_id,
                "turn_id": turn_id,
                "request_id": request_id,
                "number": result["turn_count"],
                "input_text": text,
                "text": result["final_text"],
                "state": saved_state,
                "version": version + 1,
            }
            with Session(bind=bind) as write_db:
                changed = write_db.execute(
                    update(PracticeSession)
                    .where(
                        PracticeSession.id == session_id,
                        PracticeSession.user_id == user_id,
                        PracticeSession.version == version,
                    )
                    .values(state_json=saved_state, version=version + 1)
                )
                if changed.rowcount != 1:
                    write_db.rollback()
                    winner = write_db.scalar(
                        select(PracticeTurn).where(
                            PracticeTurn.session_id == session_id,
                            PracticeTurn.request_id == request_id,
                        )
                    )
                    if winner and winner.input_text == text:
                        await queue.put(("turn_done", winner.response_json))
                        return
                    raise AppError("会话已更新，请刷新后重试", code="SESSION_VERSION_CONFLICT", status_code=409)
                write_db.add(
                    PracticeTurn(
                        id=turn_id,
                        session_id=session_id,
                        request_id=request_id,
                        number=result["turn_count"],
                        input_text=text,
                        response_json=response,
                        trace_json=result["tool_results"],
                        pronunciation_score=pronunciation_result,
                        grammar_correction=correction_result,
                        created_at=utcnow(),
                    )
                )
                usage = extract_langchain_usage(result["messages"][len(messages):])
                record_usage(
                    write_db,
                    category="chat",
                    model=usage["model"],
                    prompt_tokens=usage["prompt_tokens"],
                    completion_tokens=usage["completion_tokens"],
                    total_tokens=usage["total_tokens"],
                    call_count=usage["call_count"],
                    user_id=user_id,
                    session_id=session_id,
                    scene_id=package.meta.id,
                    turn_id=turn_id,
                )
                write_db.commit()
                saved_turn_id = turn_id
                if staged:
                    try:
                        audio_path = _user_audio_path(turn_id)
                        audio_path.parent.mkdir(parents=True, exist_ok=True)
                        audio_path.write_bytes(staged[0])
                    except OSError:
                        pass
            await queue.put(("turn_done", response))
        except Exception as exc:
            await queue.put(("error", exc))

    staged = pronunciation_service.pop_staged_audio(user_id, audio_token) if audio_token else None
    correction_result: dict | None = None
    pronunciation_result: dict | None = None
    saved_turn_id: str | None = None
    correction_sent = False
    pronunciation_sent = staged is None

    correction_task = asyncio.create_task(_evaluate_grammar(package, text, recent, greeting))
    pronunciation_task = (
        asyncio.create_task(pronunciation_service.assess_pronunciation(staged[0], text, staged[1]))
        if staged
        else None
    )

    graph_task = asyncio.create_task(run_graph())
    sentence_buf = _SentenceBuffer()
    tts_tasks: list[tuple[int, str, asyncio.Task]] = []
    next_audio_idx = 0
    turn_finished = False
    can_tts = bool(include_audio and voice_style)

    def schedule_tts(sentence: str) -> None:
        if not can_tts or not sentence:
            return
        idx = len(tts_tasks)
        task = asyncio.create_task(tts_service.synthesize(sentence, voice_style, 1.0))
        tts_tasks.append((idx, sentence, task))

    def _persist_turn_feedback(field: str, value: dict) -> None:
        if not saved_turn_id:
            return
        with Session(bind=bind) as upd_db:
            upd_db.execute(
                update(PracticeTurn).where(PracticeTurn.id == saved_turn_id).values(**{field: value})
            )
            upd_db.commit()

    try:
        while True:
            # 尽量边生成边下发已完成的句段音频
            while next_audio_idx < len(tts_tasks) and tts_tasks[next_audio_idx][2].done():
                idx, sent, task = tts_tasks[next_audio_idx]
                next_audio_idx += 1
                try:
                    audio_bytes = task.result()
                    yield _sse("audio", {"index": idx, "text": sent, "audio_b64": base64.b64encode(audio_bytes).decode("ascii")})
                except Exception as exc:
                    yield _sse("audio_error", {"index": idx, "message": getattr(exc, "message", str(exc))})

            if not correction_sent and correction_task.done():
                correction_sent = True
                try:
                    correction_result = correction_task.result()
                except Exception:
                    correction_result = None
                if correction_result:
                    _persist_turn_feedback("grammar_correction", correction_result)
                    yield _sse("correction", correction_result)

            if not pronunciation_sent and pronunciation_task is not None and pronunciation_task.done():
                pronunciation_sent = True
                try:
                    pronunciation_result = pronunciation_task.result()
                except Exception:
                    pronunciation_result = None
                if pronunciation_result:
                    _persist_turn_feedback("pronunciation_score", pronunciation_result)
                    yield _sse("pronunciation", pronunciation_result)

            if turn_finished and next_audio_idx >= len(tts_tasks) and correction_sent and pronunciation_sent:
                yield _sse("audio_end", {})
                break

            wait_tasks: list[asyncio.Task] = []
            get_task = asyncio.create_task(queue.get()) if not turn_finished else None
            if get_task is not None:
                wait_tasks.append(get_task)
            if next_audio_idx < len(tts_tasks):
                wait_tasks.append(tts_tasks[next_audio_idx][2])
            if not correction_sent:
                wait_tasks.append(correction_task)
            if not pronunciation_sent and pronunciation_task is not None:
                wait_tasks.append(pronunciation_task)

            done_set, _ = await asyncio.wait(wait_tasks, return_when=asyncio.FIRST_COMPLETED)
            if get_task is not None and get_task not in done_set:
                get_task.cancel()
                try:
                    await get_task
                except asyncio.CancelledError:
                    pass
                continue

            if get_task is not None and get_task in done_set:
                kind, payload = get_task.result()
                if kind == "delta":
                    yield _sse("delta", {"text": payload})
                    for sent in sentence_buf.push(payload):
                        schedule_tts(sent)
                elif kind == "turn_done":
                    tail = sentence_buf.flush()
                    if tail:
                        schedule_tts(tail)
                    yield _sse("done", payload)
                    turn_finished = True
                elif kind == "error":
                    msg = getattr(payload, "message", str(payload))
                    code = getattr(payload, "code", "STREAM_FAILED")
                    yield _sse("error", {"message": msg, "code": code})
                    break
    finally:
        if not graph_task.done():
            graph_task.cancel()
        if not correction_task.done():
            correction_task.cancel()
        if pronunciation_task is not None and not pronunciation_task.done():
            pronunciation_task.cancel()
        for _, _, t in tts_tasks:
            if not t.done():
                t.cancel()


async def suggest_reply(db: Session, user_id: int, session_id: str) -> dict:
    """结合当前场景阶段、目标与最近对话，生成 2~3 条地道英语参考回复。"""
    row = owned_session(db, session_id, user_id)
    if row.state_json.get("status") != "active":
        raise AppError("本次练习已结束", code="SESSION_FINISHED", status_code=409)
    package = validate(deepcopy(row.scene_snapshot))
    state, greeting = deepcopy(row.state_json), row.greeting
    recent = list(
        reversed(
            db.scalars(
                select(PracticeTurn)
                .where(PracticeTurn.session_id == session_id)
                .order_by(PracticeTurn.number.desc())
                .limit(6)
            ).all()
        )
    )
    from app.models import Chunk, Document
    pkg_ai_only = {f.path for f in package.knowledge.files if f.visibility == "ai_only"}
    user_visible_files = {f.path for f in package.knowledge.files if f.visibility == "user"}
    db_user_docs = db.scalars(
        select(Document.filename).where(Document.scene_id == package.meta.id, Document.visibility == "user")
    ).all()
    user_visible_files.update(name for name in db_user_docs if name not in pkg_ai_only)
    kb_snippets: list[str] = []
    if user_visible_files:
        from app.scenes.retrieval import search_scene

        last_partner = recent[-1].response_json.get("text", "") if recent else greeting
        kb_query = f"{package.meta.name} {last_partner}".strip()[:200]
        try:
            hits = search_scene(db, package.meta.id, kb_query, top_k=5).get("items") or []
            for item in hits:
                fname = item.get("filename") or ""
                if fname in user_visible_files and item.get("text"):
                    kb_snippets.append(f"[{fname}] {item['text']}")
        except Exception:
            pass
        if not kb_snippets:
            rows = db.scalars(
                select(Chunk)
                .join(Document, Chunk.doc_id == Document.id)
                .where(Chunk.scene_id == package.meta.id, Document.filename.in_(user_visible_files))
                .order_by(Chunk.chunk_index.asc())
                .limit(3)
            ).all()
            kb_snippets = [c.text for c in rows if c.text]
    db.rollback()

    stage_id = state.get("stage")
    stage = next((s for s in package.stages if s.id == stage_id), None)
    stage_desc = f"{stage.name}: {stage.guidance}" if stage and stage.guidance else (stage.name if stage else "")
    pending_goals = [g["label"] for g in state.get("goals", []) if not g.get("done")][:3]

    history_lines = []
    if greeting:
        history_lines.append(f"Partner: {greeting}")
    for t in recent:
        history_lines.append(f"Learner: {t.input_text}")
        history_lines.append(f"Partner: {t.response_json.get('text', '')}")

    system_msg = (
        "You are an English speaking coach inside EchoTalk. "
        "Suggest 3 short, natural, spoken English replies the learner can say next in this roleplay. "
        "Keep each reply concise (1-2 sentences) and suited to the current stage and goals. "
        "If reference material is provided, ONLY suggest items/options/facts that appear in it. "
        'Return strict JSON only: {"suggestions": [{"en": "...", "zh": "简短中文意思"}, ...]}.'
    )
    kb_block = ("\n\nReference material (visible to learner):\n" + "\n---\n".join(kb_snippets[:3])) if kb_snippets else ""
    user_msg = (
        f"Scenario: {package.meta.name} ({package.meta.description})\n"
        f"Current stage: {stage_desc}\n"
        f"Pending goals: {', '.join(pending_goals) if pending_goals else 'Continue natural conversation'}"
        f"{kb_block}\n\n"
        "Recent dialogue:\n"
        + ("\n".join(history_lines) if history_lines else "(Just started)")
    )

    def _parse_suggestions(raw_text: str) -> list[dict[str, str]]:
        cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw_text, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.MULTILINE).strip()
        m = re.search(r"\{[\s\S]*\}", cleaned)
        if m:
            cleaned = m.group(0)
        parsed_list: list[dict[str, str]] = []
        try:
            parsed = json.loads(cleaned)
            items = parsed.get("suggestions") if isinstance(parsed, dict) else parsed
            if isinstance(items, list):
                for item in items[:3]:
                    if isinstance(item, dict) and str(item.get("en", "")).strip():
                        parsed_list.append({
                            "en": str(item["en"]).strip(),
                            "zh": str(item.get("zh", "")).strip(),
                        })
        except Exception:
            pass
        if not parsed_list and cleaned:
            lines = [ln.strip("-• 1234567890.") for ln in cleaned.splitlines() if ln.strip() and not ln.strip().startswith(("{", "}", "[", "]"))]
            parsed_list = [{"en": ln, "zh": ""} for ln in lines[:3] if ln]
        return parsed_list

    model = create_chat_model()
    suggestions: list[dict[str, str]] = []
    for _ in range(2):
        ai_msg = await model.ainvoke([("system", system_msg), ("human", user_msg)])
        raw = ai_msg.content if isinstance(ai_msg.content, str) else str(ai_msg.content)
        suggestions = _parse_suggestions(raw)
        if suggestions:
            break
    if not suggestions:
        raise AppError("AI 暂未生成有效参考回复，请重试", code="SUGGEST_REPLY_EMPTY", status_code=502)
    return {"suggestions": suggestions}


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

"""练习会话轮次执行（同步与 SSE 流式），含增量切句 TTS 与并行语法/发音评估。"""
import asyncio
import base64
from copy import deepcopy
import json
import logging
import re
import time
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.agents.conversation import build_async_conversation_graph, build_conversation_graph
from app.agents.model_gateway import create_chat_model
from app.agents.tools import ToolRegistry
from app.core.errors import AppError
from app.core.timeutil import utcnow
from app.models import PracticeSession, PracticeTurn, User
from app.scenes.registry import validate
from app.services.listening_service import award_xp
from app.services.scene_runtime import advance, initial_state
from app.services.scene_service import ensure_visible, load_scene
from app.services.session.crud import _user_audio_path, owned_session
from app.services.token_usage_service import extract_langchain_usage, record_usage

logger = logging.getLogger("echotalk")
_POLITE_RE = re.compile(r"\b(?:please|could i|could you|would you|would like|i'd like|may i|thank you|thanks|appreciate)\b", re.IGNORECASE)


def _auto_detect_turn_signals(text: str, scenario_state: dict) -> None:
    """对明确可由用户输入判定的礼貌请求信号做兜底同步，避免模型漏调工具导致目标未亮。"""
    if isinstance(scenario_state.get("polite_request"), bool) and not scenario_state["polite_request"]:
        if _POLITE_RE.search(text or ""):
            scenario_state["polite_request"] = True


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
    recent = list(reversed(db.scalars(select(PracticeTurn).where(PracticeTurn.session_id == session_id).order_by(PracticeTurn.number.desc()).limit(8)).all()))
    messages = [AIMessage(greeting)] if greeting else []
    for turn in recent:
        messages.extend([HumanMessage(turn.input_text), AIMessage(turn.response_json["text"])])
    db.rollback()
    messages.append(HumanMessage(text))
    before = deepcopy(state["scenario_state"])
    _auto_detect_turn_signals(text, state["scenario_state"])
    state.update(messages=messages, tool_results=[], model_calls=0, final_text="")
    state["turn_count"] += 1
    state["stage_turns"] += 1
    state.update(advance(package, state, before))

    if search is None:
        def search(query, top_k):
            """用独立数据库连接执行场景检索，并再次验证当前资料访问权限。"""
            from app.scenes.retrieval import search_scene
            with Session(bind=db.get_bind()) as read_db:
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
    xp_gain = 5 + (20 if saved_state.get("status") == "finished" else 0)
    award_xp(db, user_id, xp_gain)
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
                xp_gain = 5 + (20 if saved_state.get("status") == "finished" else 0)
                award_xp(write_db, user_id, xp_gain)
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

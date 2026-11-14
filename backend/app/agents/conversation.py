"""LangGraph 单轮执行：模型 → 受控工具循环 → 最终回复。"""
import asyncio
import json
import logging
import re
import time
from copy import deepcopy
from uuid import uuid4

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph

from app.agents.context import system_prompt
from app.agents.state import ConversationState
from app.agents.tools import ToolRegistry
from app.core.errors import AppError
from app.services.scene_runtime import advance

logger = logging.getLogger("echotalk")
MAX_MODEL_CALLS = 4
MAX_TOOL_CALLS = 6

_TOOL_CALL_BLOCK_RE = re.compile(r"<tool_call>([\s\S]*?)</tool_call>", re.IGNORECASE)
_TOOL_CALL_TRAIL_RE = re.compile(r"<tool_call>[\s\S]*$", re.IGNORECASE)
_XML_FN_RE = re.compile(r"<function=([a-zA-Z0-9_]+)>([\s\S]*?)(?:</function>|$)", re.IGNORECASE)
_XML_PARAM_RE = re.compile(r"<parameter=([a-zA-Z0-9_]+)>\s*([\s\S]*?)\s*</parameter>", re.IGNORECASE)


def _coerce_xml_param(key: str, raw: str):
    """将 XML 参数文本按常见标量/JSON 还原，evidence 等说明字段保留原字符串。"""
    val = raw.strip()
    if key in ("evidence", "query", "key", "item", "word", "reason", "category", "summary"):
        return val
    low = val.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low == "null":
        return None
    if val.startswith(("{", "[")) or re.fullmatch(r"-?\d+(?:\.\d+)?", val):
        try:
            return json.loads(val)
        except Exception:
            pass
    return val


def _strip_tool_call_markup(text: str) -> str:
    """移除模型文本中意外泄露的 <tool_call>...</tool_call> 标签块。"""
    cleaned = _TOOL_CALL_BLOCK_RE.sub("", text)
    cleaned = _TOOL_CALL_TRAIL_RE.sub("", cleaned)
    return cleaned.strip()


def _normalize_xml_tool_message(message: AIMessage, allow_tools: bool) -> AIMessage:
    """兼容部分模型把工具调用写成文本 <tool_call> 标签的情况，恢复为标准 tool_calls 并清理正文。"""
    if not isinstance(message.content, str) or "<tool_call" not in message.content.lower():
        return message
    parsed_calls: list[dict] = []
    if allow_tools and not message.tool_calls:
        for match in _TOOL_CALL_BLOCK_RE.finditer(message.content):
            body = match.group(1).strip()
            fn_match = _XML_FN_RE.search(body)
            if fn_match:
                fn_name = fn_match.group(1).strip()
                fn_body = fn_match.group(2)
                args = {pm.group(1).strip(): _coerce_xml_param(pm.group(1).strip(), pm.group(2)) for pm in _XML_PARAM_RE.finditer(fn_body)}
                parsed_calls.append({"id": f"call_xml_{uuid4().hex[:12]}", "name": fn_name, "args": args, "type": "tool_call"})
                continue
            try:
                obj = json.loads(body)
                if isinstance(obj, dict) and obj.get("name"):
                    args = obj.get("arguments") or obj.get("args") or {}
                    if isinstance(args, str):
                        args = json.loads(args)
                    if isinstance(args, dict):
                        parsed_calls.append({"id": f"call_xml_{uuid4().hex[:12]}", "name": str(obj["name"]), "args": args, "type": "tool_call"})
            except Exception:
                pass
    cleaned = _strip_tool_call_markup(message.content)
    if parsed_calls:
        return AIMessage(content=cleaned, tool_calls=parsed_calls)
    return AIMessage(content=cleaned, tool_calls=message.tool_calls, additional_kwargs=message.additional_kwargs)


def build_conversation_graph(package, model, registry: ToolRegistry, before: dict):
    """依赖通过请求级闭包注入；不使用进程内共享会话或内存 checkpoint。"""
    schemas = registry.schemas()
    bound = model.bind_tools(schemas) if schemas else model

    def agent(state):
        """调用模型做一次回应或工具决策，并累计模型调用次数。"""
        final_attempt = state["model_calls"] >= MAX_MODEL_CALLS - 1 or state["status"] == "finished"
        prompt = system_prompt(package, state, [t.name for t in schemas])
        if final_attempt:
            prompt += "\nNo further tool calls are allowed. Reply using available results only."
        try:
            started = time.perf_counter()
            message = (model if final_attempt else bound).invoke([SystemMessage(prompt), *state["messages"]])
        except Exception as exc:
            logger.warning("对话模型调用失败：%s", type(exc).__name__)
            raise AppError("对话模型暂不可用，请重试", code="CHAT_MODEL_FAILED", status_code=502) from exc
        logger.info("对话模型调用耗时 %.2fs，调用序号 %d", time.perf_counter() - started, state["model_calls"] + 1)
        if not isinstance(message, AIMessage) or message.invalid_tool_calls:
            raise AppError("模型返回了无效的工具调用", code="CHAT_INVALID_RESPONSE", status_code=502)
        message = _normalize_xml_tool_message(message, allow_tools=not final_attempt)
        if final_attempt and message.tool_calls:
            raise AppError("模型超出工具调用预算", code="CHAT_TOOL_LIMIT", status_code=502)
        return {"messages": [*state["messages"], message], "model_calls": state["model_calls"] + 1}

    def tools(state):
        """顺序执行模型提出的工具调用，将成功或失败结果回传给模型。

        每个工具都使用本地状态快照执行；失败时恢复该工具前的状态，避免部分
        写入。调用预算耗尽、会话已结束和参数错误均转成工具结果供模型处理。
        """
        scenario = deepcopy(state["scenario_state"])
        results, messages = list(state["tool_results"]), list(state["messages"])
        for call in messages[-1].tool_calls:
            started = time.perf_counter()
            snapshot = deepcopy(scenario)
            try:
                if len(results) >= MAX_TOOL_CALLS:
                    raise ValueError("Tool call budget exhausted")
                if state["status"] == "finished":
                    raise ValueError("Session has finished")
                data = registry.execute(call["name"], call["args"], scenario)
                result = {"name": call["name"], "ok": True, "data": data}
            except (ValueError, TypeError):
                scenario = snapshot
                result = {"name": call["name"], "ok": False, "error": "Invalid arguments, unavailable tool, or execution budget exceeded"}
            except Exception as exc:
                scenario = snapshot
                logger.warning("工具执行失败：%s %s", call["name"], type(exc).__name__)
                result = {"name": call["name"], "ok": False, "error": "Tool temporarily unavailable"}
            result.update(call_id=call["id"], args=call["args"])
            logger.info("对话工具 %s 耗时 %.2fs，成功=%s", call["name"], time.perf_counter() - started, result["ok"])
            results.append(result)
            messages.append(ToolMessage(content=json.dumps(result, ensure_ascii=False), tool_call_id=call["id"]))
            state = {**state, "scenario_state": scenario, "tool_results": results}
            state.update(advance(package, state, before))
        return {**state, "messages": messages}

    def finalize(state):
        """验证最终回复非空，并由程序更新目标、阶段和会话完成状态。"""
        content = state["messages"][-1].content
        text = content if isinstance(content, str) else "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
        text = _strip_tool_call_markup(text)
        if not text:
            raise AppError("模型未返回有效回复", code="CHAT_EMPTY_RESPONSE", status_code=502)
        return {**advance(package, state, before), "final_text": text}

    graph = StateGraph(ConversationState)
    graph.add_node("agent", agent)
    graph.add_node("tools", tools)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", lambda s: "tools" if s["messages"][-1].tool_calls else "finalize")
    graph.add_edge("tools", "agent")
    graph.add_edge("finalize", END)
    return graph.compile()


def _chunk_to_ai_message(merged) -> AIMessage:
    """将流式累加的 AIMessageChunk 归一为标准 AIMessage。"""
    if merged is None:
        return AIMessage(content="")
    if isinstance(merged, AIMessage) and type(merged) is AIMessage:
        return merged
    return AIMessage(
        content=merged.content,
        tool_calls=list(getattr(merged, "tool_calls", None) or []),
        invalid_tool_calls=list(getattr(merged, "invalid_tool_calls", None) or []),
        additional_kwargs=dict(getattr(merged, "additional_kwargs", None) or {}),
        response_metadata=dict(getattr(merged, "response_metadata", None) or {}),
        usage_metadata=getattr(merged, "usage_metadata", None),
    )


def build_async_conversation_graph(package, model, registry: ToolRegistry, before: dict, on_delta=None):
    """异步流式版单轮对话图：通过 on_delta 实时推送文本增量，工具节点在线程池执行。"""
    schemas = registry.schemas()
    bound = model.bind_tools(schemas) if schemas else model

    async def agent(state):
        final_attempt = state["model_calls"] >= MAX_MODEL_CALLS - 1 or state["status"] == "finished"
        prompt = system_prompt(package, state, [t.name for t in schemas])
        if final_attempt:
            prompt += "\nNo further tool calls are allowed. Reply using available results only."
        target_model = model if final_attempt else bound
        merged = None
        stream_buf = ""
        in_tool_xml = False
        try:
            started = time.perf_counter()
            async for chunk in target_model.astream([SystemMessage(prompt), *state["messages"]]):
                merged = chunk if merged is None else merged + chunk
                delta = chunk.content if isinstance(chunk.content, str) else ""
                if not delta or getattr(chunk, "tool_call_chunks", None) or on_delta is None:
                    continue
                stream_buf += delta
                while stream_buf:
                    if in_tool_xml:
                        end_idx = stream_buf.lower().find("</tool_call>")
                        if end_idx == -1:
                            stream_buf = stream_buf[-12:] if len(stream_buf) > 12 else stream_buf
                            break
                        stream_buf = stream_buf[end_idx + len("</tool_call>"):]
                        in_tool_xml = False
                        continue
                    start_idx = stream_buf.lower().find("<tool_call")
                    if start_idx != -1:
                        emit_part = stream_buf[:start_idx]
                        if emit_part:
                            await on_delta(emit_part)
                        stream_buf = stream_buf[start_idx:]
                        in_tool_xml = True
                        continue
                    lt_idx = stream_buf.rfind("<")
                    if lt_idx != -1 and "<tool_call".startswith(stream_buf[lt_idx:].lower()):
                        emit_part = stream_buf[:lt_idx]
                        if emit_part:
                            await on_delta(emit_part)
                        stream_buf = stream_buf[lt_idx:]
                        break
                    await on_delta(stream_buf)
                    stream_buf = ""
            if stream_buf and not in_tool_xml and on_delta is not None:
                await on_delta(stream_buf)
        except Exception as exc:
            logger.warning("流式对话模型调用失败：%s", type(exc).__name__)
            raise AppError("对话模型暂不可用，请重试", code="CHAT_MODEL_FAILED", status_code=502) from exc
        message = _chunk_to_ai_message(merged)
        logger.info("流式对话模型调用耗时 %.2fs，调用序号 %d", time.perf_counter() - started, state["model_calls"] + 1)
        if not isinstance(message, AIMessage) or message.invalid_tool_calls:
            raise AppError("模型返回了无效的工具调用", code="CHAT_INVALID_RESPONSE", status_code=502)
        message = _normalize_xml_tool_message(message, allow_tools=not final_attempt)
        if final_attempt and message.tool_calls:
            raise AppError("模型超出工具调用预算", code="CHAT_TOOL_LIMIT", status_code=502)
        return {"messages": [*state["messages"], message], "model_calls": state["model_calls"] + 1}

    async def tools(state):
        scenario = deepcopy(state["scenario_state"])
        results, messages = list(state["tool_results"]), list(state["messages"])
        for call in messages[-1].tool_calls:
            started = time.perf_counter()
            snapshot = deepcopy(scenario)
            try:
                if len(results) >= MAX_TOOL_CALLS:
                    raise ValueError("Tool call budget exhausted")
                if state["status"] == "finished":
                    raise ValueError("Session has finished")
                data = await asyncio.to_thread(registry.execute, call["name"], call["args"], scenario)
                result = {"name": call["name"], "ok": True, "data": data}
            except (ValueError, TypeError):
                scenario = snapshot
                result = {"name": call["name"], "ok": False, "error": "Invalid arguments, unavailable tool, or execution budget exceeded"}
            except Exception as exc:
                scenario = snapshot
                logger.warning("工具执行失败：%s %s", call["name"], type(exc).__name__)
                result = {"name": call["name"], "ok": False, "error": "Tool temporarily unavailable"}
            result.update(call_id=call["id"], args=call["args"])
            logger.info("对话工具 %s 耗时 %.2fs，成功=%s", call["name"], time.perf_counter() - started, result["ok"])
            results.append(result)
            messages.append(ToolMessage(content=json.dumps(result, ensure_ascii=False), tool_call_id=call["id"]))
            state = {**state, "scenario_state": scenario, "tool_results": results}
            state.update(advance(package, state, before))
        return {**state, "messages": messages}

    def finalize(state):
        content = state["messages"][-1].content
        text = content if isinstance(content, str) else "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
        text = _strip_tool_call_markup(text)
        if not text:
            raise AppError("模型未返回有效回复", code="CHAT_EMPTY_RESPONSE", status_code=502)
        return {**advance(package, state, before), "final_text": text}

    graph = StateGraph(ConversationState)
    graph.add_node("agent", agent)
    graph.add_node("tools", tools)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", lambda s: "tools" if s["messages"][-1].tool_calls else "finalize")
    graph.add_edge("tools", "agent")
    graph.add_edge("finalize", END)
    return graph.compile()

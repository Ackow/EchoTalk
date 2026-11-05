"""LangGraph 单轮执行：模型 → 受控工具循环 → 最终回复。"""
import json
import logging
from copy import deepcopy

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
            message = (model if final_attempt else bound).invoke([SystemMessage(prompt), *state["messages"]])
        except Exception as exc:
            logger.warning("对话模型调用失败：%s", type(exc).__name__)
            raise AppError("对话模型暂不可用，请重试", code="CHAT_MODEL_FAILED", status_code=502) from exc
        if not isinstance(message, AIMessage) or message.invalid_tool_calls:
            raise AppError("模型返回了无效的工具调用", code="CHAT_INVALID_RESPONSE", status_code=502)
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
            results.append(result)
            messages.append(ToolMessage(content=json.dumps(result, ensure_ascii=False), tool_call_id=call["id"]))
            state = {**state, "scenario_state": scenario, "tool_results": results}
            state.update(advance(package, state, before))
        return {**state, "messages": messages}

    def finalize(state):
        """验证最终回复非空，并由程序更新目标、阶段和会话完成状态。"""
        content = state["messages"][-1].content
        text = content if isinstance(content, str) else "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
        if not text.strip():
            raise AppError("模型未返回有效回复", code="CHAT_EMPTY_RESPONSE", status_code=502)
        return {**advance(package, state, before), "final_text": text.strip()}

    graph = StateGraph(ConversationState)
    graph.add_node("agent", agent)
    graph.add_node("tools", tools)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", lambda s: "tools" if s["messages"][-1].tool_calls else "finalize")
    graph.add_edge("tools", "agent")
    graph.add_edge("finalize", END)
    return graph.compile()

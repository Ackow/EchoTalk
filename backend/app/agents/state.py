from typing import Any, TypedDict

from langchain_core.messages import BaseMessage


class ConversationState(TypedDict):
    """一次图调用对应一个用户轮次；所有状态均为当前请求私有。"""

    messages: list[BaseMessage]
    scenario_state: dict[str, Any]
    stage: str | None
    stage_turns: int
    turn_count: int
    goals: list[dict]
    status: str
    finish_reason: str | None
    tool_results: list[dict]
    model_calls: int
    final_text: str

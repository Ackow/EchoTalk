"""API Token 消耗提取与落库服务。"""
import logging
import os
from typing import Iterable

from langchain_core.messages import AIMessage
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import ApiTokenUsage

logger = logging.getLogger("echotalk")


def extract_langchain_usage(messages: Iterable) -> dict:
    """从 LangChain AIMessage 列表中汇总 Token 消耗与模型名。"""
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    call_count = 0
    model_name = ""

    for msg in messages:
        if not isinstance(msg, AIMessage):
            continue
        meta = getattr(msg, "response_metadata", None) or {}
        usage_meta = getattr(msg, "usage_metadata", None) or {}
        token_usage = meta.get("token_usage") or {}

        p = int(usage_meta.get("input_tokens") or token_usage.get("prompt_tokens") or 0)
        c = int(usage_meta.get("output_tokens") or token_usage.get("completion_tokens") or 0)
        t = int(usage_meta.get("total_tokens") or token_usage.get("total_tokens") or (p + c))

        if p or c or t or usage_meta or token_usage:
            call_count += 1
            prompt_tokens += p
            completion_tokens += c
            total_tokens += t

        if not model_name:
            model_name = str(meta.get("model_name") or meta.get("model") or "")

    if not model_name:
        model_name = os.getenv("ECHOTALK_CHAT_MODEL", "").strip() or "unknown"

    return {
        "model": model_name,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "call_count": max(call_count, 1) if total_tokens > 0 else call_count,
    }


def record_usage(
    db: Session | None = None,
    *,
    category: str,
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    call_count: int = 1,
    user_id: int | None = None,
    session_id: str | None = None,
    scene_id: str | None = None,
    turn_id: str | None = None,
) -> None:
    """记录一次 API Token 消耗；异常仅记告警，不阻断主流程。"""
    if total_tokens <= 0 and prompt_tokens <= 0 and completion_tokens <= 0:
        return
    final_total = total_tokens or (prompt_tokens + completion_tokens)
    row = ApiTokenUsage(
        user_id=user_id,
        session_id=session_id,
        scene_id=scene_id,
        turn_id=turn_id,
        category=category,
        model=(model or "unknown")[:100],
        prompt_tokens=max(0, int(prompt_tokens)),
        completion_tokens=max(0, int(completion_tokens)),
        total_tokens=max(0, int(final_total)),
        call_count=max(1, int(call_count)),
    )
    try:
        if db is not None:
            db.add(row)
        else:
            with SessionLocal() as own_db:
                own_db.add(row)
                own_db.commit()
    except Exception:
        logger.warning("记录 API Token 消耗失败", exc_info=True)

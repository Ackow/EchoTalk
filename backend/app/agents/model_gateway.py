"""模型适配入口：缺少配置时显式失败，不伪造模型回复。"""
import os

from langchain_openai import ChatOpenAI

from app.core.errors import AppError


def create_chat_model():
    """按环境配置创建 LangChain 对话模型。

    读取服务端 API Key、模型名和兼容接口地址；缺少必填配置时返回可识别的
    503 业务错误，不创建模拟模型或伪造对话结果。
    """
    key = os.getenv("ECHOTALK_CHAT_API_KEY", "").strip()
    model = os.getenv("ECHOTALK_CHAT_MODEL", "").strip()
    if not key or not model:
        raise AppError("请配置 ECHOTALK_CHAT_API_KEY 和 ECHOTALK_CHAT_MODEL", code="CHAT_NOT_CONFIGURED", status_code=503)
    return ChatOpenAI(
        api_key=key,
        model=model,
        base_url=os.getenv("ECHOTALK_CHAT_API_BASE", "https://api.openai.com/v1"),
        timeout=45,
        max_retries=1,
        max_tokens=700,
    )

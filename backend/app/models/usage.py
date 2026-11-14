"""API Token 消耗记录数据模型。"""
from sqlalchemy import Column, DateTime, Integer, String

from app.core.database import Base
from app.core.timeutil import utcnow


class ApiTokenUsage(Base):
    """API Token 使用流水表：记录每次对话轮次、向量嵌入等模型调用的 Token 消耗。"""

    __tablename__ = "api_token_usage"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True, index=True)
    session_id = Column(String(36), nullable=True, index=True)
    scene_id = Column(String(50), nullable=True, index=True)
    turn_id = Column(String(36), nullable=True)
    category = Column(String(30), nullable=False, index=True)  # chat / embedding / lightrag_llm
    model = Column(String(100), nullable=False, index=True)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    call_count = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)

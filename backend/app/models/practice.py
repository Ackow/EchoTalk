"""practice 数据模型。"""
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.timeutil import utcnow

class PracticeSession(Base):
    """练习会话：冻结场景包，保存最后一个成功提交轮次的状态。"""

    __tablename__ = "practice_sessions"
    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    scene_id = Column(String(50), nullable=False)  # 不关联删除：历史以快照恢复
    scene_snapshot = Column(JSON, nullable=False)
    state_json = Column(JSON, nullable=False)
    greeting = Column(Text, nullable=False, default="")
    version = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class PracticeTurn(Base):
    """提交成功的轮次；请求 ID 在会话内唯一，用于安全重试。"""

    __tablename__ = "practice_turns"
    __table_args__ = (
        UniqueConstraint("session_id", "request_id", name="uq_practice_request"),
        UniqueConstraint("session_id", "number", name="uq_practice_number"),
    )
    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), ForeignKey("practice_sessions.id"), nullable=False, index=True)
    request_id = Column(String(64), nullable=False)
    number = Column(Integer, nullable=False)
    input_text = Column(Text, nullable=False)
    response_json = Column(JSON, nullable=False)  # 仅公开回复与任务状态
    trace_json = Column(JSON, nullable=False)  # 内部工具轨迹，禁止通过接口直接下发
    created_at = Column(DateTime, default=utcnow, nullable=False)



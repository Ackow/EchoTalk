"""复习计划数据模型。"""
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint

from app.core.database import Base
from app.core.timeutil import utcnow


class ReviewItem(Base):
    """用户的间隔重复复习项，可来自对话纠错、发音评测、Agent 标记或手动添加。"""

    __tablename__ = "review_items"
    __table_args__ = (
        UniqueConstraint("user_id", "source_key", name="uq_review_user_source_key"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    kind = Column(String(24), nullable=False, default="expression")  # expression | pronunciation | grammar | listening
    prompt = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    phonetic = Column(String(255), nullable=False, default="")
    note = Column(Text, nullable=False, default="")
    context_text = Column(Text, nullable=False, default="")
    source_type = Column(String(24), nullable=False, default="manual")  # manual | correction | pronunciation | agent_task
    source_key = Column(String(120), nullable=True)  # 幂等去重键；手动添加为 NULL
    source_session_id = Column(String(36), nullable=True, index=True)
    scene_id = Column(String(50), nullable=True)
    scene_name = Column(String(120), nullable=False, default="")
    repetitions = Column(Integer, nullable=False, default=0)
    interval_days = Column(Integer, nullable=False, default=0)
    ease_factor = Column(Float, nullable=False, default=2.5)
    mastery = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="active")  # active | mastered
    due_at = Column(DateTime, nullable=False, default=utcnow)
    last_reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

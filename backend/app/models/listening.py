"""听力工作室与全局经验值数据模型。"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint

from app.core.database import Base
from app.core.timeutil import utcnow


class ListeningUnit(Base):
    """听力训练单元（含日常精听、四六级专项、英语电台、演讲访谈及用户导入包）。"""

    __tablename__ = "listening_units"

    id = Column(String(80), primary_key=True)
    channel = Column(String(24), nullable=False, index=True)  # daily | cet | radio | talks
    cet_level = Column(String(16), nullable=True, index=True)  # cet4 | cet6
    cet_section = Column(String(24), nullable=True)  # news | conversation | passage | lecture
    channel_label = Column(String(64), nullable=False)
    level = Column(String(48), nullable=False)
    title = Column(String(180), nullable=False)
    subtitle = Column(Text, nullable=False, default="")
    duration = Column(String(32), nullable=False, default="5 分钟")
    xp = Column(Integer, nullable=False, default=25)
    accent = Column(String(48), nullable=False, default="美音 · 常速")
    exercises_json = Column(JSON, nullable=False)
    is_builtin = Column(Boolean, nullable=False, default=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class ListeningProgress(Base):
    """用户在每个听力单元的完成进度。"""

    __tablename__ = "listening_progress"
    __table_args__ = (UniqueConstraint("user_id", "unit_id", name="uq_listening_user_unit"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    unit_id = Column(String(80), ForeignKey("listening_units.id"), nullable=False, index=True)
    progress = Column(Integer, nullable=False, default=0)  # 0..100
    completed_count = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class ListeningAttempt(Base):
    """单题作答记录：严格区分原速独立作答（is_independent=True）与辅助作答。"""

    __tablename__ = "listening_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    unit_id = Column(String(80), nullable=False, index=True)
    exercise_id = Column(String(64), nullable=False)
    exercise_type = Column(String(24), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    is_independent = Column(Boolean, nullable=False, default=True)
    hints_used_json = Column(JSON, nullable=False, default=list)
    error_tag = Column(String(48), nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=utcnow, index=True)


class UserXpState(Base):
    """用户全局经验值与每日目标状态。"""

    __tablename__ = "user_xp_states"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    total_xp = Column(Integer, nullable=False, default=0)
    today_xp = Column(Integer, nullable=False, default=0)
    today_date = Column(String(10), nullable=False, default="")
    streak_days = Column(Integer, nullable=False, default=0)
    last_checkin_date = Column(String(10), nullable=False, default="")
    checkin_streak = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

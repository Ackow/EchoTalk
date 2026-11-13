"""avatar 数据模型。"""
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.timeutil import utcnow

class AvatarPreference(Base):
    """数字人偏好表：每用户 × 每场景一行，存「形象 × 音色 × 节奏」的组合。

    scene_id 为主键一部分：空串表示「跟随场景推荐」档，非空为具体场景 id，
    切换场景时各自独立保存与加载；形象清单写死前端，后端只存 id。
    """

    __tablename__ = "avatar_preferences"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)  # 用户 ID：随账户云端同步
    scene_id = Column(String(50), primary_key=True, default="", server_default="")  # 场景键：''=跟随推荐，其余为场景 id（不设外键，'' 不在 scenes 表）
    avatar_id = Column(String(50), nullable=False)  # 数字人形象 ID：前端固定形象清单内的 id（如 mira_2d）
    role_id = Column(String(50))  # 交流身份 ID：NULL 表示跟随缺省身份（已废弃，恒 NULL）
    voice_style = Column(String(50), nullable=False)  # 音色风格：前端音色清单内的 style（如 emma）
    speech_rate = Column(Float, nullable=False, default=1.0)  # 语速倍率：0.75~1.25
    lip_sync_enabled = Column(Integer, nullable=False, default=1)  # 口型演示开关：0/1（布尔语义）
    created_at = Column(DateTime, default=utcnow, nullable=False)  # 创建时间：UTC
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)  # 最近保存时间（UTC）


class AvatarPreset(Base):
    """数字人角色目录表：存储 4 个内置角色与用户自定义角色的外观/默认音色。"""

    __tablename__ = "avatars"

    id = Column(String(50), primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    is_builtin = Column(Integer, nullable=False, default=0)
    is_public = Column(Integer, nullable=False, default=0)
    author_name = Column(String(100), nullable=False, default="")
    source_avatar_id = Column(String(50), nullable=True, index=True)
    display_name = Column(String(100), nullable=False)
    kind = Column(String(20), nullable=False, default="2d")
    theme = Column(String(30), nullable=False, default="violet")
    tagline = Column(String(200), nullable=False, default="")
    description = Column(String(200), nullable=False, default="")
    greeting = Column(String(300), nullable=False, default="")
    default_voice = Column(String(50), nullable=False, default="emma")
    appearance = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)



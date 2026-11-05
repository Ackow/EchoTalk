"""scene 数据模型。"""
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.timeutil import utcnow

class Scene(Base):
    """场景包表：完整声明存 package_json，标量列仅为查询/展示冗余（设计稿 §6）。

    source: builtin（内置只读）/ custom（创建）/ imported（导入）。
    内置场景入库与自定义场景同构，统一查询与接口。
    """

    __tablename__ = "scenes"

    id = Column(String(50), primary_key=True)  # 场景 ID：即 meta.id，如 cafe_ordering
    name = Column(String(100), nullable=False)  # 显示名称
    description = Column(Text)  # 一句话描述：场景卡与列表展示
    category = Column(String(30), nullable=False, default="custom")  # 分类：daily/business/career/academic/custom
    mode = Column(String(20), nullable=False, default="conversation")  # 模式：conversation/interview/debate
    difficulty = Column(String(20))  # 难度五级：entry/easy/normal/hard/expert
    package_json = Column(JSON, nullable=False)  # 完整场景包声明（scene.yaml 解析结果）
    source = Column(String(20), nullable=False, default="custom", index=True)  # 来源：builtin/custom/imported
    status = Column(String(20), nullable=False, default="private")  # 发布状态：private（本地私有）/ published（社区可见）
    published_at = Column(DateTime)  # 发布时间：NULL 表示未发布
    pkg_version = Column(Integer, nullable=False, default=2)  # 包结构版本：v2
    author_id = Column(Integer, ForeignKey("users.id"))  # 所属用户：builtin 为 NULL
    author = relationship("User", lazy="joined")  # 作者对象：列表/详情展示作者名（builtin 为 NULL）
    cover_path = Column(String(512))  # 封面图本地相对路径（storage/scenes/{id}/cover.*），NULL 用缺省样式
    greeting_text = Column(Text)  # 问候语文本（TTS 预合成随语音模块接入）
    greeting_audio_path = Column(String(512))  # 预合成音频本地相对路径（语音模块接入后启用）
    domain_keywords = Column(JSON)  # 跑题检测域关键词（缺省时自动提取填充）
    created_at = Column(DateTime, default=utcnow, nullable=False)  # 创建时间：UTC
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)  # 更新时间：UTC


class SceneStats(Base):
    """场景社区统计表：点赞 / 下载 / 收藏计数（1 行对应 1 个场景）。"""

    __tablename__ = "scene_stats"

    scene_id = Column(String(50), ForeignKey("scenes.id", ondelete="CASCADE"), primary_key=True)  # 场景 ID
    likes = Column(Integer, nullable=False, default=0)  # 点赞数
    downloads = Column(Integer, nullable=False, default=0)  # 下载（导出）次数
    favorites = Column(Integer, nullable=False, default=0)  # 收藏数
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)  # 最近互动时间：UTC


class SceneUserStat(Base):
    """用户对场景的互动记录：去重点赞/收藏，一人一票。"""

    __tablename__ = "scene_user_stats"
    __table_args__ = (UniqueConstraint("scene_id", "user_id", name="uq_scene_user"),)

    id = Column(Integer, primary_key=True)  # 主键：自增
    scene_id = Column(String(50), ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False, index=True)  # 场景 ID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # 用户 ID
    liked = Column(Integer, nullable=False, default=0)  # 是否已点赞：0/1（布尔语义）
    favorited = Column(Integer, nullable=False, default=0)  # 是否已收藏：0/1（布尔语义）
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)  # 最近互动时间：UTC



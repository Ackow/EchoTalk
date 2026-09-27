"""账户与场景包的数据模型（users / auth_sessions / scenes / documents / chunks）。"""
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.timeutil import utcnow


class User(Base):
    """用户表：用户名 + 密码摘要（盐$摘要 格式，不存明文）。"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)  # 主键：用户唯一 ID，自增
    username = Column(String(50), unique=True, nullable=False, index=True)  # 用户名：3~50 字符，唯一、必填、有索引
    password_hash = Column(String(256), nullable=False)  # 密码摘要：PBKDF2-SHA256 的 salt$digest，必填
    created_at = Column(DateTime, default=utcnow, nullable=False)  # 注册时间：UTC，插入时自动填充


class AuthSession(Base):
    """登录会话表：记录每次签发的令牌摘要及有效期，原始令牌仅返回客户端一次。"""

    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True)  # 主键：会话记录 ID，自增
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # 所属用户 ID：外键 users.id，有索引
    token_hash = Column(String(64), unique=True, nullable=False, index=True)  # 令牌摘要：令牌的 SHA-256（64 字符），唯一、有索引
    expires_at = Column(DateTime, nullable=False)  # 过期时间：UTC，签发后 30 天
    revoked_at = Column(DateTime)  # 撤销时间：退出登录时写入，NULL 表示仍有效
    created_at = Column(DateTime, default=utcnow, nullable=False)  # 签发时间：UTC，插入时自动填充


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


class Document(Base):
    """场景知识资料表：源文件存本地 storage/scenes/{id}/knowledge/，元数据入库。"""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)  # 主键：资料 ID，自增
    scene_id = Column(String(50), ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False, index=True)  # 所属场景
    owner_id = Column(Integer, ForeignKey("users.id"))  # 上传者：内置资料为 NULL
    filename = Column(String(255), nullable=False)  # 原始文件名：导出时还原
    content_type = Column(String(100))  # MIME 类型
    chunk_count = Column(Integer, nullable=False, default=0)  # 分块数量
    visibility = Column(String(10), nullable=False, default="user")  # 文件级缺省可见性：user/ai_only
    created_at = Column(DateTime, default=utcnow, nullable=False)  # 上传时间：UTC


class Chunk(Base):
    """知识分块表：解析后的文本块；向量索引为运行时产物（阶段 3 Hybrid RAG）。"""

    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True)  # 主键：分块 ID，自增
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)  # 所属资料
    scene_id = Column(String(50), nullable=False, index=True)  # 场景冗余：便于按场景隔离与重建
    section = Column(String(100))  # 分节名：md 标题或文件名
    visibility = Column(String(10), nullable=False, default="user")  # 分节可见性：user/ai_only
    ordinal = Column(Integer, nullable=False)  # 块序号：同一资料内从 0 递增
    text = Column(Text, nullable=False)  # 分块文本内容


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

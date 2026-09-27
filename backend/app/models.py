"""登录功能使用的最小用户与会话数据模型（users / auth_sessions）。"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

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

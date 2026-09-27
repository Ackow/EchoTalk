"""账户业务逻辑：注册、登录、会话签发与撤销。

服务层只接收 SQLAlchemy 会话与业务参数，不接触任何 HTTP 类型；
数据库查询直接在此完成（当前规模暂不单独拆仓储层）。
"""
import hashlib
import secrets
from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AuthError, ConflictError
from app.core.timeutil import utcnow
from app.models import AuthSession, User

PBKDF2_ITERATIONS = 310_000  # 密码摘要迭代次数：增强抗暴力破解能力
SESSION_TTL_DAYS = 30  # 会话有效期：30 天
# 登录时对不存在的用户名也执行同等成本的校验，避免通过响应时间探测账户是否存在。
UNKNOWN_USER_PASSWORD_HASH = f"{'0' * 32}${'0' * 64}"


def hash_password(password: str) -> str:
    """使用每个账户独立盐值生成 PBKDF2-SHA256 密码摘要。"""
    salt = secrets.token_hex(16)  # 每账户独立的 16 字节随机盐
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS).hex()
    return f"{salt}${digest}"  # 存储格式：盐$摘要


def password_matches(password: str, password_hash: str) -> bool:
    """用固定迭代次数重算摘要并以恒定时间比较，防时序攻击。"""
    salt, expected = password_hash.split("$", 1)  # 从存储值中拆出盐与期望摘要
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS).hex()
    return secrets.compare_digest(actual, expected)


def create_session(db: Session, user: User) -> str:
    """签发新会话：仅向客户端返回随机令牌，数据库只保存 SHA-256 摘要。"""
    token = secrets.token_urlsafe(32)  # 原始令牌：仅此一次返回给客户端
    token_hash = hashlib.sha256(token.encode()).hexdigest()  # 泄露数据库也无法伪造令牌
    db.add(AuthSession(user_id=user.id, token_hash=token_hash, expires_at=utcnow() + timedelta(days=SESSION_TTL_DAYS)))
    db.commit()
    return token


def register(db: Session, username: str, password: str) -> tuple[User, str]:
    """注册新账户并签发会话，返回 ``(用户, 令牌)``；用户名重复抛 ConflictError。"""
    if db.query(User).filter(User.username == username).first():  # 用户名唯一性前置检查
        raise ConflictError("用户名已被注册")
    user = User(username=username, password_hash=hash_password(password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # 并发注册可能同时通过前置查询，唯一索引是最终一致性边界。
        db.rollback()
        raise ConflictError("用户名已被注册") from None
    db.refresh(user)  # 刷新以获取自增主键
    return user, create_session(db, user)


def login(db: Session, username: str, password: str) -> tuple[User, str]:
    """校验凭据并建立新的独立登录会话，失败抛 AuthError。"""
    user = db.query(User).filter(User.username == username).first()
    password_hash = user.password_hash if user else UNKNOWN_USER_PASSWORD_HASH  # 统一校验成本
    if user is None or not password_matches(password, password_hash):
        raise AuthError("用户名或密码错误")
    return user, create_session(db, user)


def revoke_session(db: Session, session: AuthSession) -> None:
    """撤销指定会话：写入撤销时间即宣告失效。"""
    session.revoked_at = utcnow()
    db.commit()

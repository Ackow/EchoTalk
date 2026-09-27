"""API 共享身份依赖。"""
import hashlib

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AuthError
from app.core.timeutil import utcnow
from app.models import AuthSession, User

bearer = HTTPBearer(auto_error=False)  # 从 Authorization: Bearer 头提取令牌；缺失时不自动报错，由下方自行处理


def get_current_session(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> AuthSession:
    """校验 Bearer 令牌并返回仍有效、未撤销的数据库会话。"""
    if credentials is None:  # 请求未携带令牌
        raise AuthError("请先登录")
    token_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()  # 库中只存摘要，先对原始令牌求 SHA-256
    session = db.query(AuthSession).filter(
        AuthSession.token_hash == token_hash,
        AuthSession.revoked_at.is_(None),  # 未被退出撤销
        AuthSession.expires_at > utcnow(),  # 尚未过期
    ).first()
    if session is None:
        raise AuthError("登录已失效，请重新登录")
    return session


def get_current_user(session: AuthSession = Depends(get_current_session), db: Session = Depends(get_db)) -> User:
    """从已验证会话解析用户，不接受客户端传入的用户 ID。"""
    return db.query(User).filter(User.id == session.user_id).one()  # 用户身份只来自令牌对应的会话


def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User | None:
    """可选身份：携带有效令牌时返回用户，游客（无令牌/令牌失效）返回 None。

    用于 builtin 全员可见、custom 仅作者可见的只读接口。
    """
    if credentials is None:
        return None
    token_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    auth_session = db.query(AuthSession).filter(
        AuthSession.token_hash == token_hash,
        AuthSession.revoked_at.is_(None),
        AuthSession.expires_at > utcnow(),
    ).first()
    if auth_session is None:
        return None  # 游客视角：不报 401，按未登录继续
    return db.query(User).filter(User.id == auth_session.user_id).one()

"""账户业务逻辑：注册、登录、会话签发与撤销、改密与头像。

服务层只接收 SQLAlchemy 会话与业务参数，不接触任何 HTTP 类型；
数据库查询直接在此完成（当前规模暂不单独拆仓储层）。
"""
import hashlib
import os
import secrets
from datetime import timedelta
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR
from app.core.errors import AppError, AuthError, ConflictError
from app.core.timeutil import utcnow
from app.models import AuthSession, User

PBKDF2_ITERATIONS = 310_000  # 密码摘要迭代次数：增强抗暴力破解能力
SESSION_TTL_DAYS = 30  # 会话有效期：30 天
# 登录时对不存在的用户名也执行同等成本的校验，避免通过响应时间探测账户是否存在。
UNKNOWN_USER_PASSWORD_HASH = f"{'0' * 32}${'0' * 64}"

# 头像文件与场景封面共用存储根，按用户分目录（users/{id}/avatar-<随机串>.<ext>）
STORAGE_ROOT = Path(os.getenv("ECHOTALK_STORAGE_ROOT", str(BACKEND_DIR / "storage"))).resolve()
ALLOWED_AVATAR_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 头像上限 2 MB：前端按 512px 裁切后远小于此


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


def change_password(db: Session, user: User, current_password: str, new_password: str, current_session: AuthSession) -> None:
    """修改密码：校验当前密码后重设摘要，并撤销除本次登录外的全部会话。

    旧密码错误与「新旧相同」都按业务错误（400）返回，不用 401——
    401 会触发前端的统一登出逻辑，用户只是输错一个字段不该被踢出。
    """
    if not password_matches(current_password, user.password_hash):
        raise AppError("当前密码不正确", code="INVALID_PASSWORD", status_code=400)
    if password_matches(new_password, user.password_hash):
        raise AppError("新密码不能与当前密码相同", code="PASSWORD_UNCHANGED", status_code=400)

    user.password_hash = hash_password(new_password)  # 新盐 + 新摘要
    others = db.query(AuthSession).filter(
        AuthSession.user_id == user.id,
        AuthSession.revoked_at.is_(None),
        AuthSession.id != current_session.id,  # 当前设备保持登录
    ).all()
    for other in others:
        other.revoked_at = utcnow()  # 其他设备的令牌立即失效
    db.commit()


def set_avatar(db: Session, user: User, filename: str | None, content: bytes) -> str:
    """保存用户头像并返回相对路径；旧头像文件按前缀清理，避免目录堆积。"""
    suffix = Path(filename or "").suffix.lower()
    if suffix not in ALLOWED_AVATAR_EXTENSIONS:
        supported = "、".join(sorted(ALLOWED_AVATAR_EXTENSIONS))
        raise AppError(f"不支持的头像格式 '{suffix or filename}'，仅支持：{supported}", code="AVATAR_UNSUPPORTED", status_code=400)
    if not content:
        raise AppError("头像文件为空", code="AVATAR_EMPTY", status_code=400)
    if len(content) > MAX_AVATAR_SIZE:
        raise AppError("头像图片过大（上限 2 MB）", code="AVATAR_TOO_LARGE", status_code=400)

    target_dir = STORAGE_ROOT / "users" / str(user.id)
    target_dir.mkdir(parents=True, exist_ok=True)
    for old in target_dir.glob("avatar-*"):  # 先清旧图：随机串命名保证新文件名不会与之重名
        old.unlink(missing_ok=True)
    target = target_dir / f"avatar-{secrets.token_hex(4)}{suffix}"
    target.write_bytes(content)

    user.avatar_path = f"users/{user.id}/{target.name}"  # 文件名自带随机串：URL 变化即绕开浏览器缓存
    db.commit()
    return user.avatar_path


def avatar_file(db: Session, user_id: int) -> Path | None:
    """按用户 ID 读取头像文件；未设置或文件已丢失时返回 None。"""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.avatar_path:
        return None
    path = STORAGE_ROOT / user.avatar_path
    return path if path.is_file() else None


def remove_avatar(db: Session, user: User) -> bool:
    """移除头像：文件与数据库引用一并清除（前端回落到用户名首字母）。"""
    if not user.avatar_path:
        return False
    (STORAGE_ROOT / user.avatar_path).unlink(missing_ok=True)
    user.avatar_path = None
    db.commit()
    return True

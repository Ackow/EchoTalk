"""管理端用户管理：列表查询、新建、权限更新、密码重置与级联删除。"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError
from app.core.timeutil import utcnow
from app.models import (
    AuthSession,
    AvatarPreference,
    Document,
    PersonalDocument,
    PracticeSession,
    PracticeTurn,
    Scene,
    SceneUserStat,
    User,
)
from app.services.auth_service import hash_password


def list_users(
    db: Session,
    *,
    q: str | None = None,
    is_admin: bool | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """分页查询用户列表，附带会话数、场景数、数字人偏好数。"""
    conditions = []
    if q and q.strip():
        conditions.append(User.username.ilike(f"%{q.strip()}%"))
    if is_admin is not None:
        conditions.append(User.is_admin == (1 if is_admin else 0))

    total = db.scalar(select(func.count()).select_from(User).where(*conditions)) or 0
    rows = db.scalars(
        select(User).where(*conditions).order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()

    user_ids = [u.id for u in rows]
    session_counts: dict[int, int] = {}
    scene_counts: dict[int, int] = {}
    pref_counts: dict[int, int] = {}
    personal_doc_counts: dict[int, int] = {}

    if user_ids:
        session_counts = dict(
            db.execute(
                select(PracticeSession.user_id, func.count())
                .where(PracticeSession.user_id.in_(user_ids))
                .group_by(PracticeSession.user_id)
            ).all()
        )
        scene_counts = dict(
            db.execute(
                select(Scene.author_id, func.count())
                .where(Scene.author_id.in_(user_ids))
                .group_by(Scene.author_id)
            ).all()
        )
        pref_counts = dict(
            db.execute(
                select(AvatarPreference.user_id, func.count())
                .where(AvatarPreference.user_id.in_(user_ids))
                .group_by(AvatarPreference.user_id)
            ).all()
        )
        personal_doc_counts = dict(
            db.execute(
                select(PersonalDocument.owner_id, func.count())
                .where(PersonalDocument.owner_id.in_(user_ids))
                .group_by(PersonalDocument.owner_id)
            ).all()
        )

    items = [
        {
            "id": u.id,
            "username": u.username,
            "avatar_path": u.avatar_path,
            "is_admin": bool(u.is_admin),
            "created_at": u.created_at,
            "session_count": session_counts.get(u.id, 0),
            "scene_count": scene_counts.get(u.id, 0),
            "avatar_pref_count": pref_counts.get(u.id, 0),
            "personal_doc_count": personal_doc_counts.get(u.id, 0),
        }
        for u in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def create_user(db: Session, username: str, password: str, is_admin: bool = False) -> dict:
    """管理员新建用户。"""
    uname = username.strip()
    if db.scalar(select(User).where(User.username == uname)):
        raise ConflictError("用户名已存在")
    user = User(username=uname, password_hash=hash_password(password), is_admin=1 if is_admin else 0)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "username": user.username,
        "avatar_path": user.avatar_path,
        "is_admin": bool(user.is_admin),
        "created_at": user.created_at,
    }


def update_user(
    db: Session,
    current_admin: User,
    user_id: int,
    *,
    is_admin: bool | None = None,
    password: str | None = None,
) -> dict:
    """管理员更新用户权限或重置密码。"""
    user = db.get(User, user_id)
    if user is None:
        raise AppError("用户不存在", code="USER_NOT_FOUND", status_code=404)
    if is_admin is not None:
        if user.id == current_admin.id and not is_admin:
            raise AppError("不能取消当前登录管理员自己的权限", code="SELF_DEMOTE_FORBIDDEN", status_code=400)
        user.is_admin = 1 if is_admin else 0
    if password is not None:
        user.password_hash = hash_password(password)
        db.query(AuthSession).filter(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)).update(
            {"revoked_at": utcnow()}
        )
    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "username": user.username,
        "avatar_path": user.avatar_path,
        "is_admin": bool(user.is_admin),
        "created_at": user.created_at,
    }


def _cleanup_users_relations(db: Session, user_ids: list[int]) -> None:
    """清理待删除用户的无级联关联数据。"""
    if not user_ids:
        return
    session_ids = db.scalars(select(PracticeSession.id).where(PracticeSession.user_id.in_(user_ids))).all()
    if session_ids:
        db.query(PracticeTurn).filter(PracticeTurn.session_id.in_(session_ids)).delete(synchronize_session=False)
        db.query(PracticeSession).filter(PracticeSession.id.in_(session_ids)).delete(synchronize_session=False)
    db.query(AuthSession).filter(AuthSession.user_id.in_(user_ids)).delete(synchronize_session=False)
    db.query(SceneUserStat).filter(SceneUserStat.user_id.in_(user_ids)).delete(synchronize_session=False)
    db.query(Scene).filter(Scene.author_id.in_(user_ids)).update({"author_id": None}, synchronize_session=False)
    db.query(Document).filter(Document.owner_id.in_(user_ids)).update({"owner_id": None}, synchronize_session=False)


def delete_user(db: Session, current_admin: User, user_id: int) -> None:
    """管理员删除用户及关联会话/偏好/文档。"""
    if user_id == current_admin.id:
        raise AppError("不能删除当前登录的管理员账号", code="SELF_DELETE_FORBIDDEN", status_code=400)
    user = db.get(User, user_id)
    if user is None:
        raise AppError("用户不存在", code="USER_NOT_FOUND", status_code=404)

    _cleanup_users_relations(db, [user_id])
    db.delete(user)
    db.commit()


def batch_delete_users(db: Session, current_admin: User, user_ids: list[int]) -> dict:
    """批量删除用户（自动跳过当前登录管理员自身）。"""
    unique_ids = list(dict.fromkeys(user_ids))
    skipped_self = current_admin.id in unique_ids
    target_ids = [uid for uid in unique_ids if uid != current_admin.id]
    if not target_ids:
        return {"deleted": 0, "skipped_self": skipped_self}

    existing_ids = db.scalars(select(User.id).where(User.id.in_(target_ids))).all()
    if not existing_ids:
        return {"deleted": 0, "skipped_self": skipped_self}

    _cleanup_users_relations(db, existing_ids)
    deleted = db.query(User).filter(User.id.in_(existing_ids)).delete(synchronize_session=False)
    db.commit()
    return {"deleted": deleted, "skipped_self": skipped_self}

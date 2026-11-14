"""管理端业务逻辑：概览统计、用户管理、数字人配置管理、全量场景管理与对话记录管理。"""
from datetime import timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError
from app.core.timeutil import utcnow
from app.models import (
    ApiTokenUsage,
    AuthSession,
    AvatarPreference,
    AvatarPreset,
    Document,
    PersonalDocument,
    PracticeSession,
    PracticeTurn,
    Scene,
    SceneStats,
    SceneUserStat,
    User,
)
from app.scenes.registry import validate
from app.services.auth_service import hash_password
from app.services.avatar_service import normalized_voice, scene_key


AVATAR_CATALOG = [
    {
        "id": "leo_2d",
        "display_name": "Leo · 利奥",
        "kind": "2d",
        "theme": "amber",
        "description": "浓眉短发 · 紫色围裙 · 咖啡师",
        "tagline": "热情忙碌但亲切，在纽约街头咖啡馆等你点单。",
        "default_voice": "andrew",
    },
    {
        "id": "emily_2d",
        "display_name": "Emily · 艾米丽",
        "kind": "2d",
        "theme": "teal",
        "description": "低发髻 · 薄荷丝巾 · 机场地勤",
        "tagline": "冷静从容、乐于助人，帮你妥善安排改签行程。",
        "default_voice": "emma",
    },
    {
        "id": "david_2d",
        "display_name": "David · 大卫",
        "kind": "2d",
        "theme": "blue",
        "description": "偏分短发 · 方框眼镜 · 产品经理",
        "tagline": "结果导向且注重协作，推进跨国项目发布节奏。",
        "default_voice": "brian",
    },
    {
        "id": "sarah_2d",
        "display_name": "Sarah · 莎拉",
        "kind": "2d",
        "theme": "violet",
        "description": "及肩偏分 · 细框圆镜 · 技术面试官",
        "tagline": "专业且略带严格，深入考察你的工程实践与表达。",
        "default_voice": "aria",
    },
]

VOICE_CATALOG = [
    {"style": "emma", "label": "Emma · 美式英语", "tts_voice": "en-US-EmmaNeural", "accent": "美式", "gender": "女声"},
    {"style": "aria", "label": "Aria · 美式英语", "tts_voice": "en-US-AriaNeural", "accent": "美式", "gender": "女声"},
    {"style": "jenny", "label": "Jenny · 美式英语", "tts_voice": "en-US-JennyNeural", "accent": "美式", "gender": "女声"},
    {"style": "andrew", "label": "Andrew · 美式英语", "tts_voice": "en-US-AndrewNeural", "accent": "美式", "gender": "男声"},
    {"style": "brian", "label": "Brian · 美式英语", "tts_voice": "en-US-BrianNeural", "accent": "美式", "gender": "男声"},
    {"style": "guy", "label": "Guy · 美式英语", "tts_voice": "en-US-GuyNeural", "accent": "美式", "gender": "男声"},
    {"style": "sonia", "label": "Sonia · 英式英语", "tts_voice": "en-GB-SoniaNeural", "accent": "英式", "gender": "女声"},
    {"style": "ryan", "label": "Ryan · 英式英语", "tts_voice": "en-GB-RyanNeural", "accent": "英式", "gender": "男声"},
    {"style": "natasha", "label": "Natasha · 澳式英语", "tts_voice": "en-AU-NatashaNeural", "accent": "澳式", "gender": "女声"},
    {"style": "william", "label": "William · 澳式英语", "tts_voice": "en-AU-WilliamNeural", "accent": "澳式", "gender": "男声"},
]


def get_dashboard(db: Session) -> dict:
    """汇总管理端首页概览数据。"""
    now = utcnow()
    user_total = db.scalar(select(func.count()).select_from(User)) or 0
    admin_total = db.scalar(select(func.count()).select_from(User).where(User.is_admin == 1)) or 0
    active_auth_sessions = (
        db.scalar(
            select(func.count())
            .select_from(AuthSession)
            .where(AuthSession.revoked_at.is_(None), AuthSession.expires_at > now)
        )
        or 0
    )

    scene_total = db.scalar(select(func.count()).select_from(Scene)) or 0
    scene_builtin = db.scalar(select(func.count()).select_from(Scene).where(Scene.source == "builtin")) or 0
    scene_published = db.scalar(select(func.count()).select_from(Scene).where(Scene.status == "published")) or 0
    scene_doc_total = db.scalar(select(func.count()).select_from(Document)) or 0

    session_total = db.scalar(select(func.count()).select_from(PracticeSession)) or 0
    session_finished = (
        db.scalar(
            select(func.count())
            .select_from(PracticeSession)
            .where(PracticeSession.state_json["status"].as_string() == "finished")
        )
        or 0
    )
    turn_total = db.scalar(select(func.count()).select_from(PracticeTurn)) or 0
    avatar_pref_total = db.scalar(select(func.count()).select_from(AvatarPreference)) or 0
    avatar_custom_total = db.scalar(select(func.count()).select_from(AvatarPreset).where(AvatarPreset.is_builtin == 0)) or 0
    avatar_public_total = db.scalar(select(func.count()).select_from(AvatarPreset).where(AvatarPreset.is_public == 1)) or 0
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    token_total = db.scalar(select(func.coalesce(func.sum(ApiTokenUsage.total_tokens), 0))) or 0
    token_today = (
        db.scalar(
            select(func.coalesce(func.sum(ApiTokenUsage.total_tokens), 0)).where(
                ApiTokenUsage.created_at >= today_start
            )
        )
        or 0
    )

    # 形象与音色使用分布
    avatar_dist_rows = db.execute(
        select(AvatarPreference.avatar_id, func.count().label("cnt")).group_by(AvatarPreference.avatar_id)
    ).all()
    voice_dist_rows = db.execute(
        select(AvatarPreference.voice_style, func.count().label("cnt")).group_by(AvatarPreference.voice_style)
    ).all()

    # 近 7 天每日练习轮次趋势
    start_day = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    turn_dates = db.scalars(select(PracticeTurn.created_at).where(PracticeTurn.created_at >= start_day)).all()
    daily_map: dict[str, int] = {}
    for offset in range(7):
        day_str = (start_day + timedelta(days=offset)).strftime("%m-%d")
        daily_map[day_str] = 0
    for dt in turn_dates:
        if dt is not None:
            key = dt.strftime("%m-%d")
            if key in daily_map:
                daily_map[key] += 1

    # 最近 8 条练习会话
    turn_agg = (
        select(
            PracticeTurn.session_id.label("sid"),
            func.count().label("turns"),
            func.max(PracticeTurn.created_at).label("last_at"),
        )
        .group_by(PracticeTurn.session_id)
        .subquery()
    )
    recent_rows = db.execute(
        select(PracticeSession, User.username, turn_agg.c.turns, turn_agg.c.last_at)
        .join(User, User.id == PracticeSession.user_id)
        .outerjoin(turn_agg, turn_agg.c.sid == PracticeSession.id)
        .order_by(func.coalesce(turn_agg.c.last_at, PracticeSession.created_at).desc())
        .limit(8)
    ).all()
    recent_sessions = []
    for ps, uname, turns, last_at in recent_rows:
        snapshot = ps.scene_snapshot or {}
        meta = snapshot.get("meta") or {}
        state = ps.state_json or {}
        recent_sessions.append(
            {
                "id": ps.id,
                "user_id": ps.user_id,
                "username": uname,
                "scene_id": ps.scene_id,
                "scene_name": meta.get("name") or ps.scene_id,
                "status": state.get("status") or "active",
                "turn_count": turns or 0,
                "created_at": ps.created_at,
                "last_active_at": last_at or ps.created_at,
            }
        )

    return {
        "users": {
            "total": user_total,
            "admins": admin_total,
            "active_tokens": active_auth_sessions,
        },
        "scenes": {
            "total": scene_total,
            "builtin": scene_builtin,
            "custom": scene_total - scene_builtin,
            "published": scene_published,
            "documents": scene_doc_total,
        },
        "sessions": {
            "total": session_total,
            "finished": session_finished,
            "active": session_total - session_finished,
            "turns": turn_total,
        },
        "avatars": {
            "preferences_total": avatar_pref_total,
            "catalog_count": len(AVATAR_CATALOG),
            "custom_count": avatar_custom_total,
            "public_count": avatar_public_total,
            "voice_count": len(VOICE_CATALOG),
            "avatar_distribution": [{"avatar_id": r[0], "count": r[1]} for r in avatar_dist_rows],
            "voice_distribution": [{"voice_style": normalized_voice(r[0]) or r[0], "count": r[1]} for r in voice_dist_rows],
        },
        "turn_trend": [{"date": k, "count": v} for k, v in daily_map.items()],
        "token_usage": {"total_tokens": int(token_total), "today_tokens": int(token_today)},
        "recent_sessions": recent_sessions,
    }


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
        # 重置密码后撤销该用户其他有效登录会话
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


def get_avatar_catalog(db: Session) -> dict:
    """返回系统数字人形象清单、音色清单及各自被配置次数。"""
    avatar_counts = dict(
        db.execute(select(AvatarPreference.avatar_id, func.count()).group_by(AvatarPreference.avatar_id)).all()
    )
    raw_voice_counts = db.execute(
        select(AvatarPreference.voice_style, func.count()).group_by(AvatarPreference.voice_style)
    ).all()
    voice_counts: dict[str, int] = {}
    for style, cnt in raw_voice_counts:
        norm = normalized_voice(style) or style
        voice_counts[norm] = voice_counts.get(norm, 0) + cnt

    avatars = [{**item, "usage_count": avatar_counts.get(item["id"], 0)} for item in AVATAR_CATALOG]
    voices = [{**item, "usage_count": voice_counts.get(item["style"], 0)} for item in VOICE_CATALOG]
    return {"avatars": avatars, "voices": voices}


def list_avatar_preferences(
    db: Session,
    *,
    user_id: int | None = None,
    scene_id: str | None = None,
    avatar_id: str | None = None,
    voice_style: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """分页查询全平台用户的数字人偏好配置。"""
    conditions = []
    if user_id is not None:
        conditions.append(AvatarPreference.user_id == user_id)
    if scene_id is not None:
        conditions.append(AvatarPreference.scene_id == scene_key(scene_id))
    if avatar_id:
        conditions.append(AvatarPreference.avatar_id == avatar_id)
    if voice_style:
        conditions.append(AvatarPreference.voice_style == voice_style)

    total = db.scalar(select(func.count()).select_from(AvatarPreference).where(*conditions)) or 0
    rows = db.execute(
        select(AvatarPreference, User.username, Scene.name)
        .join(User, User.id == AvatarPreference.user_id)
        .outerjoin(Scene, Scene.id == AvatarPreference.scene_id)
        .where(*conditions)
        .order_by(AvatarPreference.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    items = [
        {
            "user_id": pref.user_id,
            "username": uname,
            "scene_id": pref.scene_id or "",
            "scene_name": sname or ("跟随场景推荐" if not pref.scene_id else pref.scene_id),
            "avatar_id": pref.avatar_id,
            "voice_style": normalized_voice(pref.voice_style) or pref.voice_style,
            "speech_rate": pref.speech_rate,
            "lip_sync_enabled": bool(pref.lip_sync_enabled),
            "updated_at": pref.updated_at,
        }
        for pref, uname, sname in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def upsert_avatar_preference(
    db: Session,
    *,
    user_id: int,
    scene_id: str | None,
    avatar_id: str,
    voice_style: str,
    speech_rate: float,
    lip_sync_enabled: bool,
) -> dict:
    """管理员为指定用户与场景档设置数字人偏好。"""
    user = db.get(User, user_id)
    if user is None:
        raise AppError("用户不存在", code="USER_NOT_FOUND", status_code=404)
    key = scene_key(scene_id)
    if key and db.get(Scene, key) is None:
        raise AppError("目标场景不存在", code="SCENE_NOT_FOUND", status_code=404)
    norm_voice = normalized_voice(voice_style)
    if norm_voice is None:
        raise AppError("不支持的音色预设", code="AVATAR_VOICE_UNKNOWN", status_code=422)

    pref = db.get(AvatarPreference, (user_id, key))
    if pref is None:
        pref = AvatarPreference(user_id=user_id, scene_id=key)
        db.add(pref)
    pref.avatar_id = avatar_id
    pref.voice_style = norm_voice
    pref.speech_rate = speech_rate
    pref.lip_sync_enabled = 1 if lip_sync_enabled else 0
    db.commit()
    db.refresh(pref)
    return {
        "user_id": pref.user_id,
        "username": user.username,
        "scene_id": pref.scene_id or "",
        "avatar_id": pref.avatar_id,
        "voice_style": pref.voice_style,
        "speech_rate": pref.speech_rate,
        "lip_sync_enabled": bool(pref.lip_sync_enabled),
        "updated_at": pref.updated_at,
    }


def delete_avatar_preference(db: Session, user_id: int, scene_id: str | None) -> None:
    """管理员删除指定用户的数字人偏好配置。"""
    pref = db.get(AvatarPreference, (user_id, scene_key(scene_id)))
    if pref is None:
        raise AppError("数字人偏好配置不存在", code="PREF_NOT_FOUND", status_code=404)
    db.delete(pref)
    db.commit()


def list_scenes(
    db: Session,
    *,
    q: str | None = None,
    category: str | None = None,
    mode: str | None = None,
    source: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """分页查询全平台场景（含私有、已发布、内置、自定义）。"""
    conditions = []
    if q and q.strip():
        kw = f"%{q.strip()}%"
        conditions.append(or_(Scene.id.ilike(kw), Scene.name.ilike(kw), Scene.description.ilike(kw)))
    if category:
        conditions.append(Scene.category == category)
    if mode:
        conditions.append(Scene.mode == mode)
    if source:
        conditions.append(Scene.source == source)
    if status:
        conditions.append(Scene.status == status)

    total = db.scalar(select(func.count()).select_from(Scene).where(*conditions)) or 0
    rows = db.execute(
        select(Scene, SceneStats)
        .outerjoin(SceneStats, SceneStats.scene_id == Scene.id)
        .where(*conditions)
        .order_by(Scene.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    scene_ids = [s.id for s, _ in rows]
    doc_counts: dict[str, int] = {}
    session_counts: dict[str, int] = {}
    if scene_ids:
        doc_counts = dict(
            db.execute(
                select(Document.scene_id, func.count()).where(Document.scene_id.in_(scene_ids)).group_by(Document.scene_id)
            ).all()
        )
        session_counts = dict(
            db.execute(
                select(PracticeSession.scene_id, func.count())
                .where(PracticeSession.scene_id.in_(scene_ids))
                .group_by(PracticeSession.scene_id)
            ).all()
        )

    items = [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description or "",
            "category": s.category,
            "mode": s.mode,
            "difficulty": s.difficulty,
            "source": s.source,
            "status": s.status,
            "author_id": s.author_id,
            "author_name": s.author.username if s.author else "系统内置",
            "cover_url": f"/api/scenes/{s.id}/cover" if s.cover_path else None,
            "likes": st.likes if st else 0,
            "downloads": st.downloads if st else 0,
            "favorites": st.favorites if st else 0,
            "document_count": doc_counts.get(s.id, 0),
            "session_count": session_counts.get(s.id, 0),
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        }
        for s, st in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def get_scene_detail(db: Session, scene_id: str) -> dict:
    """获取场景完整详情，包含 package_json 与关联文档。"""
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise AppError("场景不存在", code="SCENE_NOT_FOUND", status_code=404)
    stats = db.get(SceneStats, scene_id)
    docs = db.scalars(select(Document).where(Document.scene_id == scene_id).order_by(Document.id.desc())).all()
    session_count = db.scalar(select(func.count()).select_from(PracticeSession).where(PracticeSession.scene_id == scene_id)) or 0
    return {
        "id": scene.id,
        "name": scene.name,
        "description": scene.description or "",
        "category": scene.category,
        "mode": scene.mode,
        "difficulty": scene.difficulty,
        "source": scene.source,
        "status": scene.status,
        "published_at": scene.published_at,
        "author_id": scene.author_id,
        "author_name": scene.author.username if scene.author else "系统内置",
        "cover_url": f"/api/scenes/{scene.id}/cover" if scene.cover_path else None,
        "greeting_text": scene.greeting_text,
        "domain_keywords": scene.domain_keywords or [],
        "package_json": scene.package_json,
        "stats": {
            "likes": stats.likes if stats else 0,
            "downloads": stats.downloads if stats else 0,
            "favorites": stats.favorites if stats else 0,
            "session_count": session_count,
        },
        "documents": [
            {
                "id": d.id,
                "filename": d.filename,
                "content_type": d.content_type,
                "chunk_count": d.chunk_count,
                "visibility": d.visibility,
                "created_at": d.created_at,
            }
            for d in docs
        ],
        "created_at": scene.created_at,
        "updated_at": scene.updated_at,
    }


def update_scene(db: Session, scene_id: str, data: dict) -> dict:
    """管理员更新场景信息或发布状态。"""
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise AppError("场景不存在", code="SCENE_NOT_FOUND", status_code=404)

    pkg = dict(scene.package_json or {})
    if data.get("package_json") is not None:
        validated = validate(data["package_json"])
        pkg = validated.model_dump(mode="json")
        scene.package_json = pkg
        scene.name = validated.meta.name
        scene.description = validated.meta.description
        scene.category = validated.meta.category
        scene.mode = validated.meta.mode
        scene.difficulty = validated.meta.difficulty
    else:
        meta = dict(pkg.get("meta") or {})
        for field in ("name", "description", "category", "mode", "difficulty"):
            if data.get(field) is not None:
                setattr(scene, field, data[field])
                meta[field] = data[field]
        pkg["meta"] = meta
        scene.package_json = pkg

    if data.get("status") is not None:
        if scene.source == "builtin" and data["status"] != "published":
            raise AppError("系统内置场景恒为公开状态，不可下架", code="BUILTIN_PROTECTED", status_code=400)
        scene.status = data["status"]
        scene.published_at = utcnow() if data["status"] == "published" else None

    db.commit()
    db.refresh(scene)
    return get_scene_detail(db, scene.id)


def delete_scene(db: Session, scene_id: str) -> None:
    """管理员删除非内置场景。"""
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise AppError("场景不存在", code="SCENE_NOT_FOUND", status_code=404)
    if scene.source == "builtin":
        raise AppError("内置场景受保护，不允许删除", code="BUILTIN_PROTECTED", status_code=400)
    db.delete(scene)
    db.commit()


def list_sessions(
    db: Session,
    *,
    user_id: int | None = None,
    scene_id: str | None = None,
    status: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """分页查询全平台用户的练习对话记录。"""
    turn_agg = (
        select(
            PracticeTurn.session_id.label("sid"),
            func.count().label("turns"),
            func.max(PracticeTurn.created_at).label("last_at"),
        )
        .group_by(PracticeTurn.session_id)
        .subquery()
    )
    conditions = []
    if user_id is not None:
        conditions.append(PracticeSession.user_id == user_id)
    if scene_id:
        conditions.append(PracticeSession.scene_id == scene_id)
    if status:
        conditions.append(PracticeSession.state_json["status"].as_string() == status)
    if q and q.strip():
        kw = f"%{q.strip()}%"
        conditions.append(or_(User.username.ilike(kw), PracticeSession.scene_id.ilike(kw), PracticeSession.id.ilike(kw)))

    total = (
        db.scalar(
            select(func.count())
            .select_from(PracticeSession)
            .join(User, User.id == PracticeSession.user_id)
            .where(*conditions)
        )
        or 0
    )
    rows = db.execute(
        select(PracticeSession, User.username, turn_agg.c.turns, turn_agg.c.last_at)
        .join(User, User.id == PracticeSession.user_id)
        .outerjoin(turn_agg, turn_agg.c.sid == PracticeSession.id)
        .where(*conditions)
        .order_by(func.coalesce(turn_agg.c.last_at, PracticeSession.created_at).desc(), PracticeSession.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    items = []
    for ps, uname, turns, last_at in rows:
        snapshot = ps.scene_snapshot or {}
        meta = snapshot.get("meta") or {}
        state = ps.state_json or {}
        stages = snapshot.get("stages") or []
        goals = state.get("goals") or []
        stage_ids = [s.get("id") for s in stages]
        stage_index = stage_ids.index(state.get("stage")) + 1 if state.get("stage") in stage_ids else 0
        items.append(
            {
                "id": ps.id,
                "user_id": ps.user_id,
                "username": uname,
                "scene_id": ps.scene_id,
                "scene_name": meta.get("name") or ps.scene_id,
                "category": meta.get("category"),
                "difficulty": meta.get("difficulty"),
                "turn_count": turns or 0,
                "goals_done": sum(1 for g in goals if g.get("done")),
                "goals_total": len(goals),
                "status": state.get("status") or "active",
                "finish_reason": state.get("finish_reason"),
                "stage_name": stages[stage_index - 1].get("name") if stage_index else None,
                "stage_index": stage_index,
                "stage_total": len(stages),
                "created_at": ps.created_at,
                "last_active_at": last_at or ps.created_at,
            }
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def get_session_detail(db: Session, session_id: str) -> dict:
    """获取单条对话会话及完整轮次记录（含 trace_json 供管理员排查）。"""
    row = db.execute(
        select(PracticeSession, User.username)
        .join(User, User.id == PracticeSession.user_id)
        .where(PracticeSession.id == session_id)
    ).first()
    if row is None:
        raise AppError("对话记录不存在", code="SESSION_NOT_FOUND", status_code=404)
    ps, uname = row
    turns = db.scalars(
        select(PracticeTurn).where(PracticeTurn.session_id == session_id).order_by(PracticeTurn.number.asc())
    ).all()
    snapshot = ps.scene_snapshot or {}
    meta = snapshot.get("meta") or {}
    return {
        "id": ps.id,
        "user_id": ps.user_id,
        "username": uname,
        "scene_id": ps.scene_id,
        "scene_name": meta.get("name") or ps.scene_id,
        "greeting": ps.greeting,
        "state": ps.state_json or {},
        "version": ps.version,
        "created_at": ps.created_at,
        "turns": [
            {
                "id": t.id,
                "number": t.number,
                "input_text": t.input_text,
                "response": t.response_json,
                "trace": t.trace_json,
                "created_at": t.created_at,
            }
            for t in turns
        ],
    }


def delete_session(db: Session, session_id: str) -> None:
    """删除对话会话及其所有轮次。"""
    ps = db.get(PracticeSession, session_id)
    if ps is None:
        raise AppError("对话记录不存在", code="SESSION_NOT_FOUND", status_code=404)
    db.query(PracticeTurn).filter(PracticeTurn.session_id == session_id).delete(synchronize_session=False)
    db.delete(ps)
    db.commit()


def batch_delete_avatar_preferences(db: Session, items: list[tuple[int, str]]) -> dict:
    """批量删除数字人偏好配置。"""
    deleted = 0
    for uid, sid in items:
        pref = db.get(AvatarPreference, (uid, scene_key(sid)))
        if pref is not None:
            db.delete(pref)
            deleted += 1
    db.commit()
    return {"deleted": deleted}


def batch_update_scenes_status(db: Session, scene_ids: list[str], status: str) -> dict:
    """批量发布或下架场景（内置场景不可下架）。"""
    unique_ids = list(dict.fromkeys(scene_ids))
    now = utcnow() if status == "published" else None
    q = db.query(Scene).filter(Scene.id.in_(unique_ids))
    if status != "published":
        q = q.filter(Scene.source != "builtin")
    updated = q.update({"status": status, "published_at": now}, synchronize_session=False)
    db.commit()
    return {"updated": updated}


def batch_delete_scenes(db: Session, scene_ids: list[str]) -> dict:
    """批量删除非内置场景（自动跳过内置场景）。"""
    unique_ids = list(dict.fromkeys(scene_ids))
    scenes = db.scalars(select(Scene).where(Scene.id.in_(unique_ids))).all()
    deleted = 0
    skipped_builtin = 0
    for scene in scenes:
        if scene.source == "builtin":
            skipped_builtin += 1
            continue
        db.delete(scene)
        deleted += 1
    db.commit()
    return {"deleted": deleted, "skipped_builtin": skipped_builtin}


def get_token_stats(
    db: Session,
    *,
    days: int = 7,
    category: str | None = None,
    model: str | None = None,
    user_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """汇总全平台 API Token 消耗统计、趋势、模型/用户分布及明细流水。"""
    now = utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_day = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)

    conditions = []
    if category:
        conditions.append(ApiTokenUsage.category == category)
    if model:
        conditions.append(ApiTokenUsage.model == model)
    if user_id is not None:
        conditions.append(ApiTokenUsage.user_id == user_id)

    summary_row = db.execute(
        select(
            func.coalesce(func.sum(ApiTokenUsage.total_tokens), 0),
            func.coalesce(func.sum(ApiTokenUsage.prompt_tokens), 0),
            func.coalesce(func.sum(ApiTokenUsage.completion_tokens), 0),
            func.coalesce(func.sum(ApiTokenUsage.call_count), 0),
        ).where(*conditions)
    ).one()

    today_tokens = (
        db.scalar(
            select(func.coalesce(func.sum(ApiTokenUsage.total_tokens), 0)).where(
                *conditions, ApiTokenUsage.created_at >= today_start
            )
        )
        or 0
    )

    # 近 N 天每日趋势
    daily_map: dict[str, dict] = {}
    for offset in range(days):
        d = (start_day + timedelta(days=offset)).strftime("%m-%d")
        daily_map[d] = {"date": d, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0}

    trend_rows = db.execute(
        select(
            ApiTokenUsage.created_at,
            ApiTokenUsage.prompt_tokens,
            ApiTokenUsage.completion_tokens,
            ApiTokenUsage.total_tokens,
            ApiTokenUsage.call_count,
        ).where(*conditions, ApiTokenUsage.created_at >= start_day)
    ).all()
    for dt, p, c, t, cnt in trend_rows:
        if dt is not None:
            key = dt.strftime("%m-%d")
            if key in daily_map:
                daily_map[key]["prompt_tokens"] += int(p or 0)
                daily_map[key]["completion_tokens"] += int(c or 0)
                daily_map[key]["total_tokens"] += int(t or 0)
                daily_map[key]["calls"] += int(cnt or 0)

    # 按调用类型分布
    by_category_rows = db.execute(
        select(
            ApiTokenUsage.category,
            func.coalesce(func.sum(ApiTokenUsage.total_tokens), 0),
            func.coalesce(func.sum(ApiTokenUsage.call_count), 0),
        )
        .where(*conditions)
        .group_by(ApiTokenUsage.category)
    ).all()

    # 按模型分布
    by_model_rows = db.execute(
        select(
            ApiTokenUsage.model,
            func.coalesce(func.sum(ApiTokenUsage.prompt_tokens), 0),
            func.coalesce(func.sum(ApiTokenUsage.completion_tokens), 0),
            func.coalesce(func.sum(ApiTokenUsage.total_tokens), 0),
            func.coalesce(func.sum(ApiTokenUsage.call_count), 0),
        )
        .where(*conditions)
        .group_by(ApiTokenUsage.model)
        .order_by(func.sum(ApiTokenUsage.total_tokens).desc())
    ).all()

    # 用户消耗排行 Top 10
    top_users_rows = db.execute(
        select(
            ApiTokenUsage.user_id,
            User.username,
            func.coalesce(func.sum(ApiTokenUsage.total_tokens), 0),
            func.coalesce(func.sum(ApiTokenUsage.call_count), 0),
        )
        .outerjoin(User, User.id == ApiTokenUsage.user_id)
        .where(*conditions, ApiTokenUsage.user_id.is_not(None))
        .group_by(ApiTokenUsage.user_id, User.username)
        .order_by(func.sum(ApiTokenUsage.total_tokens).desc())
        .limit(10)
    ).all()

    # 明细分页
    total_logs = db.scalar(select(func.count()).select_from(ApiTokenUsage).where(*conditions)) or 0
    log_rows = db.execute(
        select(ApiTokenUsage, User.username)
        .outerjoin(User, User.id == ApiTokenUsage.user_id)
        .where(*conditions)
        .order_by(ApiTokenUsage.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return {
        "summary": {
            "total_tokens": int(summary_row[0]),
            "prompt_tokens": int(summary_row[1]),
            "completion_tokens": int(summary_row[2]),
            "total_calls": int(summary_row[3]),
            "today_tokens": int(today_tokens),
        },
        "trend": list(daily_map.values()),
        "by_category": [
            {"category": r[0], "total_tokens": int(r[1]), "calls": int(r[2])} for r in by_category_rows
        ],
        "by_model": [
            {
                "model": r[0],
                "prompt_tokens": int(r[1]),
                "completion_tokens": int(r[2]),
                "total_tokens": int(r[3]),
                "calls": int(r[4]),
            }
            for r in by_model_rows
        ],
        "top_users": [
            {"user_id": r[0], "username": r[1] or f"User#{r[0]}", "total_tokens": int(r[2]), "calls": int(r[3])}
            for r in top_users_rows
        ],
        "logs": {
            "items": [
                {
                    "id": row.id,
                    "user_id": row.user_id,
                    "username": uname or ("系统任务" if row.user_id is None else f"User#{row.user_id}"),
                    "category": row.category,
                    "model": row.model,
                    "prompt_tokens": row.prompt_tokens,
                    "completion_tokens": row.completion_tokens,
                    "total_tokens": row.total_tokens,
                    "call_count": row.call_count,
                    "scene_id": row.scene_id,
                    "session_id": row.session_id,
                    "created_at": row.created_at,
                }
                for row, uname in log_rows
            ],
            "total": total_logs,
            "page": page,
            "page_size": page_size,
        },
    }


def batch_delete_sessions(db: Session, session_ids: list[str]) -> dict:
    """批量删除对话会话及其所有轮次。"""
    unique_ids = list(dict.fromkeys(session_ids))
    if not unique_ids:
        return {"deleted": 0}
    db.query(PracticeTurn).filter(PracticeTurn.session_id.in_(unique_ids)).delete(synchronize_session=False)
    deleted = db.query(PracticeSession).filter(PracticeSession.id.in_(unique_ids)).delete(synchronize_session=False)
    db.commit()
    return {"deleted": deleted}


def _preset_to_dict(preset: AvatarPreset, owner_username: str | None, usage_count: int = 0) -> dict:
    """序列化数字人角色预设。"""
    return {
        "id": preset.id,
        "owner_id": preset.owner_id,
        "owner_username": owner_username or (preset.author_name if not preset.is_builtin else "系统内置"),
        "is_builtin": bool(preset.is_builtin),
        "is_public": bool(preset.is_public),
        "author_name": preset.author_name,
        "source_avatar_id": preset.source_avatar_id,
        "display_name": preset.display_name,
        "kind": preset.kind,
        "theme": preset.theme,
        "tagline": preset.tagline,
        "description": preset.description,
        "greeting": preset.greeting,
        "default_voice": normalized_voice(preset.default_voice) or preset.default_voice,
        "appearance": preset.appearance,
        "usage_count": usage_count,
        "created_at": preset.created_at,
        "updated_at": preset.updated_at,
    }


def list_avatar_presets(
    db: Session,
    *,
    q: str | None = None,
    is_builtin: bool | None = None,
    is_public: bool | None = None,
    owner_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """分页查询创建的数字人角色列表（含内置与用户创作）。"""
    conditions = []
    if q and q.strip():
        kw = f"%{q.strip()}%"
        conditions.append(
            or_(
                AvatarPreset.id.ilike(kw),
                AvatarPreset.display_name.ilike(kw),
                AvatarPreset.description.ilike(kw),
                AvatarPreset.author_name.ilike(kw),
            )
        )
    if is_builtin is not None:
        conditions.append(AvatarPreset.is_builtin == (1 if is_builtin else 0))
    if is_public is not None:
        conditions.append(AvatarPreset.is_public == (1 if is_public else 0))
    if owner_id is not None:
        conditions.append(AvatarPreset.owner_id == owner_id)

    total = db.scalar(select(func.count()).select_from(AvatarPreset).where(*conditions)) or 0
    rows = db.execute(
        select(AvatarPreset, User.username)
        .outerjoin(User, User.id == AvatarPreset.owner_id)
        .where(*conditions)
        .order_by(AvatarPreset.is_builtin.asc(), AvatarPreset.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    preset_ids = [p.id for p, _ in rows]
    usage_counts: dict[str, int] = {}
    if preset_ids:
        usage_counts = dict(
            db.execute(
                select(AvatarPreference.avatar_id, func.count())
                .where(AvatarPreference.avatar_id.in_(preset_ids))
                .group_by(AvatarPreference.avatar_id)
            ).all()
        )

    items = [_preset_to_dict(p, uname, usage_counts.get(p.id, 0)) for p, uname in rows]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def update_avatar_preset(db: Session, avatar_id: str, data: dict) -> dict:
    """管理员更新创建的数字人角色信息或公开状态。"""
    preset = db.get(AvatarPreset, avatar_id)
    if preset is None:
        raise AppError("数字人角色不存在", code="AVATAR_NOT_FOUND", status_code=404)

    for field in ("display_name", "description", "tagline", "greeting", "theme", "appearance"):
        if field in data and data[field] is not None:
            setattr(preset, field, data[field])

    if "default_voice" in data and data["default_voice"] is not None:
        norm = normalized_voice(data["default_voice"])
        if norm is None:
            raise AppError("不支持的音色预设", code="AVATAR_VOICE_UNKNOWN", status_code=422)
        preset.default_voice = norm

    if "is_public" in data and data["is_public"] is not None:
        if preset.is_builtin and not data["is_public"]:
            raise AppError("系统内置数字人不可设为私有", code="BUILTIN_PROTECTED", status_code=400)
        preset.is_public = 1 if data["is_public"] else 0

    db.commit()
    db.refresh(preset)
    owner_username = db.scalar(select(User.username).where(User.id == preset.owner_id)) if preset.owner_id else None
    usage_count = db.scalar(
        select(func.count()).select_from(AvatarPreference).where(AvatarPreference.avatar_id == preset.id)
    ) or 0
    return _preset_to_dict(preset, owner_username, usage_count)


def delete_avatar_preset(db: Session, avatar_id: str) -> None:
    """管理员删除非内置数字人角色。"""
    preset = db.get(AvatarPreset, avatar_id)
    if preset is None:
        raise AppError("数字人角色不存在", code="AVATAR_NOT_FOUND", status_code=404)
    if preset.is_builtin:
        raise AppError("系统内置数字人受保护，不允许删除", code="BUILTIN_PROTECTED", status_code=400)
    db.delete(preset)
    db.commit()


def batch_update_avatar_presets_public(db: Session, avatar_ids: list[str], is_public: bool) -> dict:
    """批量设置数字人公开/私有状态（内置角色不可设为私有）。"""
    unique_ids = list(dict.fromkeys(avatar_ids))
    presets = db.scalars(select(AvatarPreset).where(AvatarPreset.id.in_(unique_ids))).all()
    updated = 0
    skipped_builtin = 0
    for preset in presets:
        if preset.is_builtin and not is_public:
            skipped_builtin += 1
            continue
        preset.is_public = 1 if is_public else 0
        updated += 1
    db.commit()
    return {"updated": updated, "skipped_builtin": skipped_builtin}


def batch_delete_avatar_presets(db: Session, avatar_ids: list[str]) -> dict:
    """批量删除非内置数字人角色（自动跳过内置角色）。"""
    unique_ids = list(dict.fromkeys(avatar_ids))
    presets = db.scalars(select(AvatarPreset).where(AvatarPreset.id.in_(unique_ids))).all()
    deleted = 0
    skipped_builtin = 0
    for preset in presets:
        if preset.is_builtin:
            skipped_builtin += 1
            continue
        db.delete(preset)
        deleted += 1
    db.commit()
    return {"deleted": deleted, "skipped_builtin": skipped_builtin}


def get_token_stats(
    db: Session,
    *,
    days: int = 7,
    category: str | None = None,
    model: str | None = None,
    user_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """汇总全平台 API Token 消耗统计、趋势、模型/用户分布及明细流水。"""
    now = utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_day = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)

    conditions = []
    if category:
        conditions.append(ApiTokenUsage.category == category)
    if model:
        conditions.append(ApiTokenUsage.model == model)
    if user_id is not None:
        conditions.append(ApiTokenUsage.user_id == user_id)

    summary_row = db.execute(
        select(
            func.coalesce(func.sum(ApiTokenUsage.total_tokens), 0),
            func.coalesce(func.sum(ApiTokenUsage.prompt_tokens), 0),
            func.coalesce(func.sum(ApiTokenUsage.completion_tokens), 0),
            func.coalesce(func.sum(ApiTokenUsage.call_count), 0),
        ).where(*conditions)
    ).one()

    today_tokens = (
        db.scalar(
            select(func.coalesce(func.sum(ApiTokenUsage.total_tokens), 0)).where(
                *conditions, ApiTokenUsage.created_at >= today_start
            )
        )
        or 0
    )

    # 近 N 天每日趋势
    daily_map: dict[str, dict] = {}
    for offset in range(days):
        d = (start_day + timedelta(days=offset)).strftime("%m-%d")
        daily_map[d] = {"date": d, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0}

    trend_rows = db.execute(
        select(
            ApiTokenUsage.created_at,
            ApiTokenUsage.prompt_tokens,
            ApiTokenUsage.completion_tokens,
            ApiTokenUsage.total_tokens,
            ApiTokenUsage.call_count,
        ).where(*conditions, ApiTokenUsage.created_at >= start_day)
    ).all()
    for dt, p, c, t, cnt in trend_rows:
        if dt is not None:
            key = dt.strftime("%m-%d")
            if key in daily_map:
                daily_map[key]["prompt_tokens"] += int(p or 0)
                daily_map[key]["completion_tokens"] += int(c or 0)
                daily_map[key]["total_tokens"] += int(t or 0)
                daily_map[key]["calls"] += int(cnt or 0)

    # 按调用类型分布
    by_category_rows = db.execute(
        select(
            ApiTokenUsage.category,
            func.coalesce(func.sum(ApiTokenUsage.total_tokens), 0),
            func.coalesce(func.sum(ApiTokenUsage.call_count), 0),
        )
        .where(*conditions)
        .group_by(ApiTokenUsage.category)
    ).all()

    # 按模型分布
    by_model_rows = db.execute(
        select(
            ApiTokenUsage.model,
            func.coalesce(func.sum(ApiTokenUsage.prompt_tokens), 0),
            func.coalesce(func.sum(ApiTokenUsage.completion_tokens), 0),
            func.coalesce(func.sum(ApiTokenUsage.total_tokens), 0),
            func.coalesce(func.sum(ApiTokenUsage.call_count), 0),
        )
        .where(*conditions)
        .group_by(ApiTokenUsage.model)
        .order_by(func.sum(ApiTokenUsage.total_tokens).desc())
    ).all()

    # 用户消耗排行 Top 10
    top_users_rows = db.execute(
        select(
            ApiTokenUsage.user_id,
            User.username,
            func.coalesce(func.sum(ApiTokenUsage.total_tokens), 0),
            func.coalesce(func.sum(ApiTokenUsage.call_count), 0),
        )
        .outerjoin(User, User.id == ApiTokenUsage.user_id)
        .where(*conditions, ApiTokenUsage.user_id.is_not(None))
        .group_by(ApiTokenUsage.user_id, User.username)
        .order_by(func.sum(ApiTokenUsage.total_tokens).desc())
        .limit(10)
    ).all()

    # 明细分页
    total_logs = db.scalar(select(func.count()).select_from(ApiTokenUsage).where(*conditions)) or 0
    log_rows = db.execute(
        select(ApiTokenUsage, User.username)
        .outerjoin(User, User.id == ApiTokenUsage.user_id)
        .where(*conditions)
        .order_by(ApiTokenUsage.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return {
        "summary": {
            "total_tokens": int(summary_row[0]),
            "prompt_tokens": int(summary_row[1]),
            "completion_tokens": int(summary_row[2]),
            "total_calls": int(summary_row[3]),
            "today_tokens": int(today_tokens),
        },
        "trend": list(daily_map.values()),
        "by_category": [
            {"category": r[0], "total_tokens": int(r[1]), "calls": int(r[2])} for r in by_category_rows
        ],
        "by_model": [
            {
                "model": r[0],
                "prompt_tokens": int(r[1]),
                "completion_tokens": int(r[2]),
                "total_tokens": int(r[3]),
                "calls": int(r[4]),
            }
            for r in by_model_rows
        ],
        "top_users": [
            {"user_id": r[0], "username": r[1] or f"User#{r[0]}", "total_tokens": int(r[2]), "calls": int(r[3])}
            for r in top_users_rows
        ],
        "logs": {
            "items": [
                {
                    "id": row.id,
                    "user_id": row.user_id,
                    "username": uname or ("系统任务" if row.user_id is None else f"User#{row.user_id}"),
                    "category": row.category,
                    "model": row.model,
                    "prompt_tokens": row.prompt_tokens,
                    "completion_tokens": row.completion_tokens,
                    "total_tokens": row.total_tokens,
                    "call_count": row.call_count,
                    "scene_id": row.scene_id,
                    "session_id": row.session_id,
                    "created_at": row.created_at,
                }
                for row, uname in log_rows
            ],
            "total": total_logs,
            "page": page,
            "page_size": page_size,
        },
    }

"""管理端数字人形象、音色清单与偏好/角色预设管理。"""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import AvatarPreference, AvatarPreset, Scene, User
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
    {
        "id": "claire_2d",
        "display_name": "Claire · 克莱尔",
        "kind": "2d",
        "theme": "indigo",
        "description": "高马尾 · 铁路制服 · 车站售票员",
        "tagline": "耐心干练的车站售票员，在佩恩车站为你安排最佳车次。",
        "default_voice": "jenny",
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

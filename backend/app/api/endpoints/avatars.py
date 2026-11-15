"""数字人偏好接口（控制器层）：GET / PUT / DELETE /api/preferences/avatar。

偏好按「用户 × 场景档」存储：scene_id 查询/载荷参数定位档位，
空值表示「跟随场景推荐」档；未保存过时返回全 null 字段而非 404。
"""
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import inspect, or_, text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_optional_user
from app.core.database import get_db
from app.models import AvatarPreset, User
from app.schemas.avatar import (
    AvatarPreferenceResponse,
    AvatarPreferenceUpdate,
    AvatarPresetCreate,
    AvatarPresetResponse,
    AvatarPresetUpdate,
)
from app.services import avatar_service

router = APIRouter(prefix="/preferences/avatar", tags=["数字人"])
catalog_router = APIRouter(prefix="/avatars", tags=["数字人"])

BUILTIN_AVATAR_SEEDS = [
    {
        "id": "leo_2d",
        "display_name": "Leo · 利奥",
        "theme": "amber",
        "tagline": "热情忙碌但亲切，在纽约街头咖啡馆等你点单。",
        "description": "浓眉短发 · 紫色围裙 · 咖啡师",
        "greeting": "Hi there! What can I get started for you today?",
        "default_voice": "andrew",
        "appearance": {"base": "male", "skinTone": "warm", "hairStyle": "undercut", "hairColor": "#47302a", "eyeStyle": "bright", "eyeColor": "#3b2738", "glasses": "none", "outfit": "apron_violet", "accessory": "none", "backdrop": "cafe"},
    },
    {
        "id": "emily_2d",
        "display_name": "Emily · 艾米丽",
        "theme": "teal",
        "tagline": "冷静从容、乐于助人，帮你妥善安排改签行程。",
        "description": "低发髻 · 薄荷丝巾 · 机场地勤",
        "greeting": "Good evening, how can I help with your flight?",
        "default_voice": "aria",
        "appearance": {"base": "female", "skinTone": "fair", "hairStyle": "low_bun", "hairColor": "#46335e", "eyeStyle": "gentle", "eyeColor": "#35264a", "glasses": "none", "outfit": "airline_blazer", "accessory": "headset_single", "backdrop": "airport"},
    },
    {
        "id": "david_2d",
        "display_name": "David · 大卫",
        "theme": "blue",
        "tagline": "结果导向且注重协作，推进跨国项目发布节奏。",
        "description": "偏分短发 · 方框眼镜 · 产品经理",
        "greeting": "Hi team, let’s align on the Q3 launch.",
        "default_voice": "guy",
        "appearance": {"base": "male", "skinTone": "medium", "hairStyle": "side_part", "hairColor": "#2c263f", "eyeStyle": "calm", "eyeColor": "#2d294b", "glasses": "rect_dark", "outfit": "pm_suit", "accessory": "none", "backdrop": "meeting"},
    },
    {
        "id": "sarah_2d",
        "display_name": "Sarah · 莎拉",
        "theme": "violet",
        "tagline": "专业且略带严格，深入考察你的工程实践与表达。",
        "description": "及肩偏分 · 细框圆镜 · 技术面试官",
        "greeting": "Hi, I’m Sarah. Whenever you’re ready.",
        "default_voice": "emma",
        "appearance": {"base": "female", "skinTone": "fair", "hairStyle": "shoulder_sleek", "hairColor": "#3d2b52", "eyeStyle": "calm", "eyeColor": "#2d2040", "glasses": "round_violet", "outfit": "tech_cardigan", "accessory": "earring_pearl", "backdrop": "interview"},
    },
    {
        "id": "claire_2d",
        "display_name": "Claire · 克莱尔",
        "theme": "indigo",
        "tagline": "耐心干练的车站售票员，在佩恩车站为你安排最佳车次。",
        "description": "高马尾 · 铁路制服 · 车站售票员",
        "greeting": "Good morning, welcome to the ticket counter!",
        "default_voice": "jenny",
        "appearance": {"base": "female", "skinTone": "warm", "hairStyle": "high_ponytail", "hairColor": "#3b2b4a", "eyeStyle": "bright", "eyeColor": "#35264a", "glasses": "none", "outfit": "station_uniform", "accessory": "headset_single", "backdrop": "station"},
    },
]


def sync_builtin_avatars(db: Session) -> int:
    """确保 4 个内置角色存在于 avatars 表（幂等 upsert），并按需补齐发布字段。"""
    from app.core.migrations import ensure_avatar_columns

    ensure_avatar_columns(db.get_bind())

    added = 0
    for seed in BUILTIN_AVATAR_SEEDS:
        existing = db.get(AvatarPreset, seed["id"])
        if existing is None:
            db.add(AvatarPreset(is_builtin=1, is_public=1, author_name="EchoTalk", kind="2d", **seed))
            added += 1
    if added:
        db.commit()
    return added


def _preset_to_response(row: AvatarPreset, user: User | None = None, is_acquired: bool = False) -> AvatarPresetResponse:
    return AvatarPresetResponse(
        id=row.id,
        is_builtin=bool(row.is_builtin),
        is_public=bool(getattr(row, "is_public", 0)),
        is_owner=bool(user and row.owner_id == user.id),
        is_acquired=is_acquired,
        source_avatar_id=getattr(row, "source_avatar_id", None),
        author_name=getattr(row, "author_name", "") or "",
        display_name=row.display_name,
        kind=row.kind,
        theme=row.theme,
        tagline=row.tagline,
        description=row.description,
        greeting=row.greeting,
        default_voice=row.default_voice,
        appearance=row.appearance,
    )


def _to_response(pref) -> AvatarPreferenceResponse:
    """模型行 → 响应体；库内空串场景键归一为 null（跟随推荐的对外语义）。"""
    return AvatarPreferenceResponse(
        avatar_id=pref.avatar_id,
        role_id=pref.role_id,
        voice_style=avatar_service.normalized_voice(pref.voice_style),  # 存量历史枚举归一后返回
        scene_id=pref.scene_id or None,
        speech_rate=pref.speech_rate,
        lip_sync_enabled=bool(pref.lip_sync_enabled),
        updated_at=pref.updated_at,
    )


@router.get("", response_model=AvatarPreferenceResponse)
def read_preference(
    scene_id: str | None = Query(default=None, description="场景 id；空为「跟随场景推荐」档"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """读取当前场景档的偏好；未保存过时返回全 null 字段（前端按跟随缺省处理）。"""
    pref = avatar_service.get_preference(db, user, scene_id)
    if pref is None:
        return AvatarPreferenceResponse()  # 全 null：该场景档从未自定义
    return _to_response(pref)


@router.put("", response_model=AvatarPreferenceResponse)
def save_preference(
    payload: AvatarPreferenceUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """整体覆盖保存当前场景档的偏好（形象 × 音色 × 节奏的任意组合）。"""
    pref = avatar_service.save_preference(db, user, payload)
    return _to_response(pref)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def reset_preference(
    scene_id: str | None = Query(default=None, description="场景 id；空为「跟随场景推荐」档"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """重置当前场景档的偏好：删除该行，回到跟随缺省。"""
    avatar_service.reset_preference(db, user, scene_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@catalog_router.get("", response_model=list[AvatarPresetResponse])
def list_avatars(
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """获取当前用户可用的数字人角色清单（4 个内置预设 + 本人创作或获取的角色）。"""
    sync_builtin_avatars(db)
    query = db.query(AvatarPreset)
    if user is None:
        query = query.filter(AvatarPreset.is_builtin == 1)
    else:
        query = query.filter(or_(AvatarPreset.is_builtin == 1, AvatarPreset.owner_id == user.id))
    rows = query.order_by(AvatarPreset.is_builtin.desc(), AvatarPreset.created_at.asc()).all()
    return [_preset_to_response(r, user) for r in rows]


@catalog_router.get("/market", response_model=list[AvatarPresetResponse])
def list_market_avatars(
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """角色市场：返回所有公开发布的社区数字人角色（不含内置 4 个预设，优先展示最新）。"""
    sync_builtin_avatars(db)
    acquired_ids: set[str] = set()
    legacy_keys: set[tuple[str, str]] = set()
    if user is not None:
        owned_rows = (
            db.query(AvatarPreset)
            .filter(AvatarPreset.owner_id == user.id, AvatarPreset.is_builtin == 0)
            .all()
        )
        for owned in owned_rows:
            if owned.source_avatar_id:
                acquired_ids.add(owned.source_avatar_id)
            elif not owned.is_public:
                legacy_keys.add((owned.display_name, owned.author_name or ""))
    rows = (
        db.query(AvatarPreset)
        .filter(AvatarPreset.is_public == 1, AvatarPreset.is_builtin == 0)
        .order_by(AvatarPreset.created_at.desc())
        .all()
    )
    return [
        _preset_to_response(
            r,
            user,
            is_acquired=(
                r.id in acquired_ids
                or (
                    user is not None
                    and r.owner_id != user.id
                    and (r.display_name, r.author_name or "") in legacy_keys
                )
            ),
        )
        for r in rows
    ]


@catalog_router.post("/{avatar_id}/clone", response_model=AvatarPresetResponse, status_code=status.HTTP_201_CREATED)
def clone_market_avatar(
    avatar_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """从角色市场获取他人的公开角色到自己的角色库。"""
    source = db.get(AvatarPreset, avatar_id)
    if source is None or (not source.is_public and source.owner_id != user.id):
        raise HTTPException(status_code=404, detail="该角色不存在或未公开")
    existing = (
        db.query(AvatarPreset)
        .filter(AvatarPreset.owner_id == user.id, AvatarPreset.source_avatar_id == source.id)
        .first()
    )
    if existing is not None:
        return _preset_to_response(existing, user, is_acquired=True)
    cloned = AvatarPreset(
        id=f"custom_{uuid4().hex[:12]}",
        owner_id=user.id,
        is_builtin=0,
        is_public=0,
        author_name=source.author_name or "",
        source_avatar_id=source.id,
        display_name=source.display_name,
        kind=source.kind,
        theme=source.theme,
        tagline=source.tagline,
        description=source.description,
        greeting=source.greeting,
        default_voice=source.default_voice,
        appearance=source.appearance,
    )
    db.add(cloned)
    db.commit()
    db.refresh(cloned)
    return _preset_to_response(cloned, user, is_acquired=True)


@catalog_router.delete("/{avatar_id}/clone", status_code=status.HTTP_204_NO_CONTENT)
def unclone_market_avatar(
    avatar_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """取消获取从角色市场克隆到自己角色库的角色（含早期未记录来源 ID 的重复副本）。"""
    source = db.get(AvatarPreset, avatar_id)
    conds = [AvatarPreset.source_avatar_id == avatar_id]
    if source is not None and source.owner_id != user.id:
        conds.append(
            (AvatarPreset.source_avatar_id.is_(None))
            & (AvatarPreset.is_builtin == 0)
            & (AvatarPreset.is_public == 0)
            & (AvatarPreset.display_name == source.display_name)
            & (AvatarPreset.author_name == (source.author_name or ""))
        )
    rows = (
        db.query(AvatarPreset)
        .filter(AvatarPreset.owner_id == user.id, or_(*conds))
        .all()
    )
    for row in rows:
        db.delete(row)
    if rows:
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@catalog_router.post("", response_model=AvatarPresetResponse, status_code=status.HTTP_201_CREATED)
def create_avatar(
    payload: AvatarPresetCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建当前用户的自定义数字人角色。"""
    row = AvatarPreset(
        id=f"custom_{uuid4().hex[:12]}",
        owner_id=user.id,
        is_builtin=0,
        is_public=1 if payload.is_public else 0,
        author_name=getattr(user, "username", "") or "",
        display_name=payload.display_name,
        kind="2d",
        theme=payload.theme,
        tagline=payload.tagline,
        description=payload.description,
        greeting=payload.greeting,
        default_voice=payload.default_voice,
        appearance=payload.appearance,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _preset_to_response(row, user)


@catalog_router.put("/{avatar_id}", response_model=AvatarPresetResponse)
def update_avatar(
    avatar_id: str,
    payload: AvatarPresetUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新用户自己创建的自定义数字人角色。"""
    row = db.get(AvatarPreset, avatar_id)
    if row is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    if row.is_builtin or row.owner_id != user.id:
        raise HTTPException(status_code=403, detail="无权修改内置或其他用户的角色")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "is_public" and value is not None:
            setattr(row, field, 1 if value else 0)
        else:
            setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return _preset_to_response(row, user)


@catalog_router.post("/{avatar_id}/publish", response_model=AvatarPresetResponse)
def publish_avatar(
    avatar_id: str,
    is_public: bool = Query(default=True, description="是否公开发布"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """发布或取消发布用户自己的自定义数字人角色。"""
    row = db.get(AvatarPreset, avatar_id)
    if row is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    if row.is_builtin or row.owner_id != user.id:
        raise HTTPException(status_code=403, detail="无权发布内置或其他用户的角色")
    row.is_public = 1 if is_public else 0
    if not row.author_name:
        row.author_name = getattr(user, "username", "") or ""
    db.commit()
    db.refresh(row)
    return _preset_to_response(row, user)


@catalog_router.delete("/{avatar_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_avatar(
    avatar_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除用户自己创建的自定义数字人角色。"""
    row = db.get(AvatarPreset, avatar_id)
    if row is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    if row.is_builtin or row.owner_id != user.id:
        raise HTTPException(status_code=403, detail="内置角色不可删除")
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

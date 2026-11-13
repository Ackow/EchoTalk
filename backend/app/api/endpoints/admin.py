"""管理端接口：概览、用户管理、数字人配置、场景管理、对话记录管理。"""
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user, get_db
from app.core.errors import AppError
from app.models import User
from app.schemas.admin import (
    AdminAvatarPreferenceUpsert,
    AdminAvatarPresetUpdate,
    AdminSceneUpdate,
    AdminUserCreate,
    AdminUserUpdate,
    BatchAvatarPrefDelete,
    BatchAvatarPresetPublic,
    BatchIntIds,
    BatchSceneStatus,
    BatchStrIds,
)
from app.schemas.auth import AuthResponse, Credentials
from app.services import admin_service, auth_service

router = APIRouter(prefix="/admin", tags=["管理端"])


@router.post("/login", response_model=AuthResponse)
def admin_login(payload: Credentials, db: Session = Depends(get_db)):
    """管理端登录：校验凭据且必须具备管理员权限。"""
    user, token = auth_service.login(db, payload.username, payload.password)
    if not user.is_admin:
        raise AppError("该账号无管理员权限", code="FORBIDDEN", status_code=403)
    return AuthResponse(access_token=token, user=user)


@router.get("/dashboard")
def dashboard(
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """获取管理端仪表盘汇总统计与趋势数据。"""
    return admin_service.get_dashboard(db)


# ---- 用户管理 ----
@router.get("/users")
def list_users(
    q: str | None = Query(default=None),
    is_admin: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_service.list_users(db, q=q, is_admin=is_admin, page=page, page_size=page_size)


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminUserCreate,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_service.create_user(db, payload.username, payload.password, payload.is_admin)


@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    current_admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_service.update_user(
        db, current_admin, user_id, is_admin=payload.is_admin, password=payload.password
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    admin_service.delete_user(db, current_admin, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/users/batch-delete")
def batch_delete_users(
    payload: BatchIntIds,
    current_admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_service.batch_delete_users(db, current_admin, payload.ids)


# ---- 数字人管理 ----
@router.get("/avatars/catalog")
def avatar_catalog(
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_service.get_avatar_catalog(db)


@router.get("/avatars/preferences")
def list_avatar_preferences(
    user_id: int | None = Query(default=None),
    scene_id: str | None = Query(default=None),
    avatar_id: str | None = Query(default=None),
    voice_style: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_service.list_avatar_preferences(
        db,
        user_id=user_id,
        scene_id=scene_id,
        avatar_id=avatar_id,
        voice_style=voice_style,
        page=page,
        page_size=page_size,
    )


@router.put("/avatars/preferences")
def upsert_avatar_preference(
    payload: AdminAvatarPreferenceUpsert,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_service.upsert_avatar_preference(
        db,
        user_id=payload.user_id,
        scene_id=payload.scene_id,
        avatar_id=payload.avatar_id,
        voice_style=payload.voice_style,
        speech_rate=payload.speech_rate,
        lip_sync_enabled=payload.lip_sync_enabled,
    )


@router.delete("/avatars/preferences", status_code=status.HTTP_204_NO_CONTENT)
def delete_avatar_preference(
    user_id: int = Query(...),
    scene_id: str | None = Query(default=""),
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    admin_service.delete_avatar_preference(db, user_id, scene_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/avatars/preferences/batch-delete")
def batch_delete_avatar_preferences(
    payload: BatchAvatarPrefDelete,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_service.batch_delete_avatar_preferences(db, [(i.user_id, i.scene_id) for i in payload.items])


@router.get("/avatars/presets")
def list_avatar_presets(
    q: str | None = Query(default=None),
    is_builtin: bool | None = Query(default=None),
    is_public: bool | None = Query(default=None),
    owner_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_service.list_avatar_presets(
        db, q=q, is_builtin=is_builtin, is_public=is_public, owner_id=owner_id, page=page, page_size=page_size
    )


@router.patch("/avatars/presets/{avatar_id}")
def update_avatar_preset(
    avatar_id: str,
    payload: AdminAvatarPresetUpdate,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_service.update_avatar_preset(db, avatar_id, payload.model_dump(exclude_unset=True))


@router.delete("/avatars/presets/{avatar_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_avatar_preset(
    avatar_id: str,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    admin_service.delete_avatar_preset(db, avatar_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/avatars/presets/batch-public")
def batch_update_avatar_presets_public(
    payload: BatchAvatarPresetPublic,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_service.batch_update_avatar_presets_public(db, payload.ids, payload.is_public)


@router.post("/avatars/presets/batch-delete")
def batch_delete_avatar_presets(
    payload: BatchStrIds,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_service.batch_delete_avatar_presets(db, payload.ids)


# ---- 场景管理 ----
@router.get("/scenes")
def list_scenes(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    mode: str | None = Query(default=None),
    source: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_service.list_scenes(
        db, q=q, category=category, mode=mode, source=source, status=status_filter, page=page, page_size=page_size
    )


@router.get("/scenes/{scene_id}")
def get_scene(
    scene_id: str,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_service.get_scene_detail(db, scene_id)


@router.patch("/scenes/{scene_id}")
def update_scene(
    scene_id: str,
    payload: AdminSceneUpdate,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_service.update_scene(db, scene_id, payload.model_dump(exclude_unset=True))


@router.delete("/scenes/{scene_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scene(
    scene_id: str,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    admin_service.delete_scene(db, scene_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/scenes/batch-status")
def batch_update_scenes_status(
    payload: BatchSceneStatus,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_service.batch_update_scenes_status(db, payload.ids, payload.status)


@router.post("/scenes/batch-delete")
def batch_delete_scenes(
    payload: BatchStrIds,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_service.batch_delete_scenes(db, payload.ids)


# ---- 对话记录管理 ----
@router.get("/sessions")
def list_sessions(
    user_id: int | None = Query(default=None),
    scene_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_service.list_sessions(
        db, user_id=user_id, scene_id=scene_id, status=status_filter, q=q, page=page, page_size=page_size
    )


@router.get("/sessions/{session_id}")
def get_session(
    session_id: str,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_service.get_session_detail(db, session_id)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    admin_service.delete_session(db, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/sessions/batch-delete")
def batch_delete_sessions(
    payload: BatchStrIds,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_service.batch_delete_sessions(db, payload.ids)

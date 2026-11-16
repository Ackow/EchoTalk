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
from app.schemas.saas import (
    AdminCampaignCreate,
    AdminCampaignUpdate,
    AdminPlanUpdate,
    AdminRedeemGenerateRequest,
    AdminTaskUpdate,
    AdminUserGrantRequest,
)
from app.services import admin_service, auth_service, saas_service
from app.services.admin import saas_and_modules as admin_ext

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


@router.get("/settings/registration")
def get_registration_setting(
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    from app.models.user import SystemConfig

    SystemConfig.__table__.create(bind=db.get_bind(), checkfirst=True)
    row = db.get(SystemConfig, "registration_restricted")
    return {"registration_restricted": bool(row and row.value == "true")}


@router.put("/settings/registration")
def update_registration_setting(
    payload: dict,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    from app.models.user import SystemConfig

    SystemConfig.__table__.create(bind=db.get_bind(), checkfirst=True)
    restricted = bool(payload.get("registration_restricted"))
    row = db.get(SystemConfig, "registration_restricted")
    if row is None:
        row = SystemConfig(key="registration_restricted", value="true" if restricted else "false")
        db.add(row)
    else:
        row.value = "true" if restricted else "false"
    db.commit()
    return {"registration_restricted": restricted}


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


# ---- API Token 统计 ----
@router.get("/token-stats")
def token_stats(
    days: int = Query(default=7, ge=1, le=90),
    category: str | None = Query(default=None),
    model: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_service.get_token_stats(
        db,
        days=days,
        category=category,
        model=model,
        user_id=user_id,
        page=page,
        page_size=page_size,
    )


# ---- 用户会员与积分调账 ----
@router.post("/users/{user_id}/grant")
def grant_user_saas(
    user_id: int,
    payload: AdminUserGrantRequest,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_ext.grant_user_saas(
        db,
        user_id,
        plan_tier=payload.plan_tier,
        plan_days=payload.plan_days,
        credits_delta=payload.credits_delta,
        remark=payload.remark,
    )


# ---- 多角色场景管理 ----
@router.get("/debates")
def list_admin_debates(
    q: str | None = Query(default=None),
    scene_type: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_ext.list_admin_debates(db, q=q, scene_type=scene_type, status=status_filter, page=page, page_size=page_size)


@router.patch("/debates/{topic_id}")
def update_admin_debate(
    topic_id: str,
    payload: dict,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_ext.update_admin_debate(db, topic_id, payload)


@router.delete("/debates/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_debate(
    topic_id: str,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    admin_ext.delete_admin_debate(db, topic_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- 多角色会话记录 ----
@router.get("/debate-sessions")
def list_admin_debate_sessions(
    q: str | None = Query(default=None),
    scene_type: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_ext.list_admin_debate_sessions(db, q=q, scene_type=scene_type, status=status_filter, page=page, page_size=page_size)


@router.get("/debate-sessions/{session_id}")
def get_admin_debate_session(
    session_id: str,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_ext.get_admin_debate_session_detail(db, session_id)


@router.delete("/debate-sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_debate_session(
    session_id: str,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    admin_ext.delete_admin_debate_session(db, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- 知识库文档管理 ----
@router.get("/knowledge")
def list_admin_knowledge(
    scope: str = Query(default="scene"),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_ext.list_admin_knowledge(db, scope=scope, q=q, page=page, page_size=page_size)


@router.delete("/knowledge/{scope}/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_knowledge(
    scope: str,
    doc_id: int,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    admin_ext.delete_admin_knowledge(db, scope, doc_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/knowledge/lightrag-config")
def get_lightrag_config(_: User = Depends(get_admin_user)):
    from app.core import config
    from app.scenes import lightrag_service

    return {
        "enabled": bool(config.LIGHTRAG_ENABLED),
        "available": bool(lightrag_service.available()),
        "has_llm_key": bool(config.LIGHTRAG_LLM_API_KEY),
        "has_embedding_key": bool(config.EMBEDDING_API_KEY),
    }


@router.put("/knowledge/lightrag-config")
def update_lightrag_config(
    payload: dict,
    _: User = Depends(get_admin_user),
):
    from app.core import config
    from app.scenes import lightrag_service

    if "enabled" in payload:
        config.LIGHTRAG_ENABLED = bool(payload["enabled"])
    return {
        "enabled": bool(config.LIGHTRAG_ENABLED),
        "available": bool(lightrag_service.available()),
        "has_llm_key": bool(config.LIGHTRAG_LLM_API_KEY),
        "has_embedding_key": bool(config.EMBEDDING_API_KEY),
    }


# ---- 复习计划与听力记录 ----
@router.get("/reviews")
def list_admin_reviews(
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_ext.list_admin_reviews(db, page=page, page_size=page_size, q=q)


@router.delete("/reviews/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_review(
    item_id: int,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    admin_ext.delete_admin_review(db, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/listening/attempts")
def list_admin_listening_attempts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_ext.list_admin_listening_attempts(db, page=page, page_size=page_size)


# ---- SaaS 套餐、任务、活动、订单与兑换码 ----
@router.get("/saas/plans")
def get_admin_saas_plans(
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return {"plans": saas_service.list_plans(db), "action_meta": saas_service.ACTION_META}


@router.put("/saas/plans/{tier}")
def update_admin_saas_plan(
    tier: str,
    payload: AdminPlanUpdate,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return {"plans": admin_ext.update_admin_plan(db, tier, payload.model_dump(exclude_unset=True))}


@router.get("/saas/tasks")
def list_admin_tasks(
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return {"items": admin_ext.list_admin_tasks(db)}


@router.put("/saas/tasks/{task_code}")
def update_admin_task(
    task_code: str,
    payload: AdminTaskUpdate,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_ext.update_admin_task(db, task_code, payload.model_dump(exclude_unset=True))


@router.get("/saas/campaigns")
def list_admin_campaigns(
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return {"items": admin_ext.list_admin_campaigns(db)}


@router.post("/saas/campaigns", status_code=status.HTTP_201_CREATED)
def create_admin_campaign(
    payload: AdminCampaignCreate,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_ext.create_admin_campaign(db, payload.model_dump())


@router.patch("/saas/campaigns/{campaign_id}")
def update_admin_campaign(
    campaign_id: int,
    payload: AdminCampaignUpdate,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_ext.update_admin_campaign(db, campaign_id, payload.model_dump(exclude_unset=True))


@router.delete("/saas/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_campaign(
    campaign_id: int,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    admin_ext.delete_admin_campaign(db, campaign_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/saas/orders")
def list_admin_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_ext.list_admin_orders(db, page=page, page_size=page_size)


@router.get("/saas/ledger")
def list_admin_ledger(
    user_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_ext.list_admin_ledger(db, user_id=user_id, page=page, page_size=page_size)


@router.get("/saas/redeem-codes")
def list_admin_redeem_codes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return admin_ext.list_admin_redeem_codes(db, page=page, page_size=page_size)


@router.post("/saas/redeem-codes", status_code=status.HTTP_201_CREATED)
def generate_admin_redeem_codes(
    payload: AdminRedeemGenerateRequest,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return {"codes": admin_ext.generate_admin_redeem_codes(db, payload.model_dump())}


@router.get("/saas/billing-config")
def get_admin_billing_config(
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    cfg = saas_service.get_billing_config(db)
    return {
        "tokens_per_credit": cfg.tokens_per_credit,
        "prompt_price_per_million": cfg.prompt_price_per_million,
        "completion_price_per_million": cfg.completion_price_per_million,
    }


@router.put("/saas/billing-config")
def update_admin_billing_config(
    payload: dict,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    cfg = saas_service.get_billing_config(db)
    if "tokens_per_credit" in payload:
        cfg.tokens_per_credit = max(1, int(payload["tokens_per_credit"]))
    if "prompt_price_per_million" in payload:
        cfg.prompt_price_per_million = max(0.0, float(payload["prompt_price_per_million"]))
    if "completion_price_per_million" in payload:
        cfg.completion_price_per_million = max(0.0, float(payload["completion_price_per_million"]))
    db.add(cfg)
    db.commit()
    return {
        "tokens_per_credit": cfg.tokens_per_credit,
        "prompt_price_per_million": cfg.prompt_price_per_million,
        "completion_price_per_million": cfg.completion_price_per_million,
    }

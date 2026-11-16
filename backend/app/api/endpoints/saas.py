"""用户端 SaaS 订阅、配额开关、签到、积分任务、模拟支付与兑换码接口。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.saas import MockCheckoutRequest, RedeemCodeRequest, SaasSettingsUpdate
from app.services import saas_service

router = APIRouter(prefix="/saas", tags=["SaaS 订阅与积分"])


@router.get("/me")
def get_my_saas_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户会员等级、积分余额、超额抵扣开关与今日免费额度使用情况。"""
    return saas_service.get_saas_profile(db, user)


@router.patch("/me/settings")
def update_my_saas_settings(
    payload: SaasSettingsUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """切换用户个人「免费额度用尽后自动消耗积分」开关。"""
    user.auto_use_credits = 1 if payload.auto_use_credits else 0
    db.add(user)
    db.commit()
    return {"auto_use_credits": bool(user.auto_use_credits)}


@router.get("/plans")
def get_saas_plans(db: Session = Depends(get_db)):
    """获取三档 SaaS 套餐对比、积分加油包目录与当前生效的限时活动（游客也可浏览）。"""
    saas_service.ensure_saas_defaults(db)
    campaigns = saas_service.get_active_campaigns(db)
    return {
        "plans": saas_service.list_plans(db),
        "credit_packs": list(saas_service.CREDIT_PACKS.values()),
        "action_meta": saas_service.ACTION_META,
        "active_campaigns": [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "bonus_multiplier": c.bonus_multiplier,
                "free_actions_json": c.free_actions_json or [],
                "ends_at": c.ends_at.isoformat(),
            }
            for c in campaigns
        ],
    }


@router.post("/checkin")
def daily_checkin(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """每日签到领取积分与连签里程碑奖励。"""
    return saas_service.daily_checkin(db, user)


@router.get("/tasks")
def list_tasks(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取今日训练任务与新手成长任务进度。"""
    return {"items": saas_service.get_tasks_with_progress(db, user)}


@router.post("/tasks/{task_code}/claim")
def claim_task(
    task_code: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """领取已完成任务的积分奖励。"""
    return saas_service.claim_task_reward(db, user, task_code)


@router.post("/checkout/mock")
def mock_checkout(
    payload: MockCheckoutRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """模拟收银台支付成功（免真实支付网关），升级套餐或购买积分加油包。"""
    return saas_service.mock_checkout(
        db,
        user,
        order_type=payload.order_type,
        target_tier=payload.target_tier,
        billing_cycle=payload.billing_cycle,
        credit_pack_code=payload.credit_pack_code,
    )


@router.post("/redeem")
def redeem_code(
    payload: RedeemCodeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """核销兑换码，领取积分或体验会员。"""
    return saas_service.redeem_code(db, user, payload.code)


@router.get("/ledger")
def list_ledger(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """分页查询个人积分收支流水。"""
    return saas_service.list_user_ledger(db, user.id, page=page, page_size=page_size)

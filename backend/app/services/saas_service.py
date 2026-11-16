"""SaaS 订阅、每日免费额度、超额积分抵扣、任务签到与模拟订单核心服务。"""
from __future__ import annotations

import logging
import secrets
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.timeutil import utcnow
from app.models import User, UserXpState
from app.models.saas import (
    CreditLedger,
    CreditTaskDef,
    RedeemCode,
    SaasBillingConfig,
    SaasCampaign,
    SaasPlanConfig,
    SubscriptionOrder,
    UserDailyUsage,
    UserTaskProgress,
)

logger = logging.getLogger("echotalk.saas")

TIER_RANK: dict[str, int] = {"free": 0, "pro": 1, "enterprise": 2}
TOKENS_PER_CREDIT: int = 1000  # 基准换算：1 回声积分 ≈ 1,000 LLM Tokens
POOL_CAPACITIES: dict[str, int] = {"free": 40, "pro": 400, "enterprise": -1}
CHECKIN_XP_REWARDS: list[int] = [5, 8, 10, 12, 15, 18, 25]
TASK_XP_MAP: dict[str, int] = {
    "daily_practice_1": 15,
    "daily_listening_1": 25,
    "daily_review_10": 15,
    "daily_debate_1": 20,
    "onboard_avatar": 20,
    "onboard_scene": 30,
}

ACTION_META: dict[str, dict[str, str]] = {
    "practice_turn": {"label": "1v1 语音对话轮次", "module": "语音对话"},
    "practice_coach_hint": {"label": "实时 Coach 话术提示", "module": "语音对话"},
    "practice_report_deep": {"label": "1v1 深度复盘报告", "module": "语音对话"},
    "debate_turn": {"label": "1vN 多角色辩论/群面轮次", "module": "多角色对话"},
    "debate_verdict_report": {"label": "1vN 赛后裁决与录用评估", "module": "多角色对话"},
    "listening_explain": {"label": "听力划词解释 / AI 助教", "module": "听力工作室"},
    "scene_ai_draft": {"label": "AI 一键生成场景/多角色草稿", "module": "场景编辑器"},
    "knowledge_embed": {"label": "知识库文档解析与向量化", "module": "知识工作区"},
}

CREDIT_PACKS: dict[str, dict[str, Any]] = {
    "pack_300": {"code": "pack_300", "name": "轻量体验包", "credits": 300, "price_yuan": 6},
    "pack_1000": {"code": "pack_1000", "name": "高频冲刺包", "credits": 1000, "price_yuan": 18},
    "pack_3000": {"code": "pack_3000", "name": "年度备考大容量包", "credits": 3000, "price_yuan": 48},
}

DEFAULT_PLANS: list[dict[str, Any]] = [
    {
        "tier": "free",
        "name": "Free 免费体验版",
        "description": "每日赠送基础对话与听力额度，超出可通过签到/任务积分抵扣",
        "monthly_price_yuan": 0,
        "yearly_price_yuan": 0,
        "monthly_grant_credits": 0,
        "daily_free_credits": 40,
        "max_custom_scenes": 2,
        "max_custom_debates": 1,
        "max_knowledge_docs": 0,
        "allow_zip_import": 0,
        "allow_zip_export": 0,
        "checkin_multiplier": 1,
        "credit_discount_rate": 1.0,
        "quotas_json": {
            "practice_turn": {"daily_free": 15, "credit_cost": 2, "allow_overage_credits": True},
            "practice_coach_hint": {"daily_free": 3, "credit_cost": 1, "allow_overage_credits": True},
            "practice_report_deep": {"daily_free": 1, "credit_cost": 3, "allow_overage_credits": True},
            "debate_turn": {"daily_free": 6, "credit_cost": 4, "allow_overage_credits": True},
            "debate_verdict_report": {"daily_free": 1, "credit_cost": 5, "allow_overage_credits": True},
            "listening_explain": {"daily_free": 10, "credit_cost": 1, "allow_overage_credits": True},
            "scene_ai_draft": {"daily_free": 0, "credit_cost": 5, "allow_overage_credits": True},
            "knowledge_embed": {"daily_free": 0, "credit_cost": 10, "allow_overage_credits": False},
        },
    },
    {
        "tier": "pro",
        "name": "Pro 个人专业版",
        "description": "开放场景包 ZIP 导入、AI 草稿生成、私有简历知识库与 8 折积分消耗",
        "monthly_price_yuan": 29,
        "yearly_price_yuan": 268,
        "monthly_grant_credits": 1200,
        "daily_free_credits": 400,
        "max_custom_scenes": 30,
        "max_custom_debates": 20,
        "max_knowledge_docs": 15,
        "allow_zip_import": 1,
        "allow_zip_export": 0,
        "checkin_multiplier": 2,
        "credit_discount_rate": 0.8,
        "quotas_json": {
            "practice_turn": {"daily_free": 150, "credit_cost": 2, "allow_overage_credits": True},
            "practice_coach_hint": {"daily_free": 50, "credit_cost": 1, "allow_overage_credits": True},
            "practice_report_deep": {"daily_free": 20, "credit_cost": 3, "allow_overage_credits": True},
            "debate_turn": {"daily_free": 80, "credit_cost": 4, "allow_overage_credits": True},
            "debate_verdict_report": {"daily_free": 20, "credit_cost": 5, "allow_overage_credits": True},
            "listening_explain": {"daily_free": -1, "credit_cost": 0, "allow_overage_credits": True},
            "scene_ai_draft": {"daily_free": 10, "credit_cost": 5, "allow_overage_credits": True},
            "knowledge_embed": {"daily_free": 5, "credit_cost": 10, "allow_overage_credits": True},
        },
    },
    {
        "tier": "enterprise",
        "name": "Enterprise 机构/企业版",
        "description": "开放场景包 ZIP 打包导出分发、无限场景创建与大容量企业知识库",
        "monthly_price_yuan": 199,
        "yearly_price_yuan": 1880,
        "monthly_grant_credits": 10000,
        "daily_free_credits": -1,
        "max_custom_scenes": -1,
        "max_custom_debates": -1,
        "max_knowledge_docs": 200,
        "allow_zip_import": 1,
        "allow_zip_export": 1,
        "checkin_multiplier": 3,
        "credit_discount_rate": 0.5,
        "quotas_json": {
            "practice_turn": {"daily_free": -1, "credit_cost": 0, "allow_overage_credits": True},
            "practice_coach_hint": {"daily_free": -1, "credit_cost": 0, "allow_overage_credits": True},
            "practice_report_deep": {"daily_free": -1, "credit_cost": 0, "allow_overage_credits": True},
            "debate_turn": {"daily_free": -1, "credit_cost": 0, "allow_overage_credits": True},
            "debate_verdict_report": {"daily_free": -1, "credit_cost": 0, "allow_overage_credits": True},
            "listening_explain": {"daily_free": -1, "credit_cost": 0, "allow_overage_credits": True},
            "scene_ai_draft": {"daily_free": 50, "credit_cost": 3, "allow_overage_credits": True},
            "knowledge_embed": {"daily_free": 50, "credit_cost": 5, "allow_overage_credits": True},
        },
    },
]

DEFAULT_TASKS: list[dict[str, Any]] = [
    {
        "task_code": "daily_practice_1",
        "title": "开口破冰",
        "description": "完成 1 场 1v1 语音对话练习",
        "category": "daily",
        "target_count": 1,
        "reward_credits": 15,
        "daily_limit": 1,
        "route_path": "/practice",
        "sort_order": 10,
    },
    {
        "task_code": "daily_listening_1",
        "title": "磨耳朵训练",
        "description": "在听力工作室提交 1 次听力练习",
        "category": "daily",
        "target_count": 1,
        "reward_credits": 10,
        "daily_limit": 2,
        "route_path": "/listening",
        "sort_order": 20,
    },
    {
        "task_code": "daily_review_10",
        "title": "记忆加固",
        "description": "在复习计划中完成 3 次复习或添加复习表达",
        "category": "daily",
        "target_count": 3,
        "reward_credits": 15,
        "daily_limit": 1,
        "route_path": "/review",
        "sort_order": 30,
    },
    {
        "task_code": "daily_debate_1",
        "title": "思维交锋",
        "description": "参与并完成 1 场多角色辩论或群面圆桌",
        "category": "daily",
        "target_count": 1,
        "reward_credits": 20,
        "daily_limit": 1,
        "route_path": "/debate",
        "sort_order": 40,
    },
    {
        "task_code": "onboard_avatar",
        "title": "定制专属数字人",
        "description": "保存一次个人偏好的数字人形象或音色",
        "category": "onboarding",
        "target_count": 1,
        "reward_credits": 20,
        "daily_limit": 1,
        "route_path": "/avatar",
        "sort_order": 50,
    },
    {
        "task_code": "onboard_scene",
        "title": "创建首个自定义场景",
        "description": "亲手创建一个 1v1 场景或 1vN 多角色场景",
        "category": "onboarding",
        "target_count": 1,
        "reward_credits": 30,
        "daily_limit": 1,
        "route_path": "/scenes/create",
        "sort_order": 60,
    },
]


def _today_str() -> str:
    return date.today().isoformat()


def ensure_saas_defaults(db: Session) -> None:
    """幂等初始化默认套餐配置与积分任务定义。"""
    changed = False
    for p in DEFAULT_PLANS:
        if not db.get(SaasPlanConfig, p["tier"]):
            db.add(SaasPlanConfig(**p))
            changed = True
    for t in DEFAULT_TASKS:
        existing = db.get(CreditTaskDef, t["task_code"])
        if not existing:
            db.add(CreditTaskDef(**t))
            changed = True
        elif t["task_code"] == "daily_review_10" and existing.target_count == 10:
            existing.target_count = t["target_count"]
            existing.description = t["description"]
            db.add(existing)
            changed = True
    if db.query(SaasCampaign).count() == 0:
        now = utcnow()
        db.add(
            SaasCampaign(
                name="英语口语冲刺季 · 听力 AI 助教限时免额度",
                description="活动期间听力工作室划词解释与 AI 助教不占用今日免费额度，完成任务可更快累积段位 XP 与回声积分。",
                bonus_multiplier=1.0,
                free_actions_json=["listening_explain"],
                starts_at=now - timedelta(days=2),
                ends_at=now + timedelta(days=30),
                enabled=1,
            )
        )
        changed = True
    if not db.get(SaasBillingConfig, 1):
        db.add(SaasBillingConfig(id=1, tokens_per_credit=1000, prompt_price_per_million=2.0, completion_price_per_million=8.0))
        changed = True
    if changed:
        db.commit()


def get_billing_config(db: Session) -> SaasBillingConfig:
    ensure_saas_defaults(db)
    cfg = db.get(SaasBillingConfig, 1)
    assert cfg is not None
    return cfg


def _grant_user_xp(db: Session, user_id: int, xp_delta: int) -> int:
    if xp_delta <= 0:
        return 0
    today = _today_str()
    state = db.get(UserXpState, user_id)
    if not state:
        state = UserXpState(user_id=user_id, total_xp=0, today_xp=0, today_date=today, streak_days=1)
        db.add(state)
    if state.today_date != today:
        state.today_date = today
        state.today_xp = 0
    state.total_xp = int(state.total_xp or 0) + int(xp_delta)
    state.today_xp = int(state.today_xp or 0) + int(xp_delta)
    db.add(state)
    return state.total_xp


def get_effective_tier(db: Session, user: User) -> str:
    """返回用户当前有效等级；如会员过期则自动回退为 free。"""
    tier = (user.plan_tier or "free").lower()
    if tier not in TIER_RANK:
        tier = "free"
    if tier != "free" and user.plan_expires_at and user.plan_expires_at < utcnow():
        user.plan_tier = "free"
        user.plan_expires_at = None
        db.add(user)
        db.commit()
        return "free"
    return tier


def get_plan_config(db: Session, tier: str) -> SaasPlanConfig:
    ensure_saas_defaults(db)
    plan = db.get(SaasPlanConfig, tier) or db.get(SaasPlanConfig, "free")
    assert plan is not None
    return plan


def get_active_campaigns(db: Session) -> list[SaasCampaign]:
    now = utcnow()
    return (
        db.query(SaasCampaign)
        .filter(SaasCampaign.enabled == 1, SaasCampaign.starts_at <= now, SaasCampaign.ends_at >= now)
        .all()
    )


def _append_ledger(
    db: Session,
    user: User,
    delta: int,
    source_type: str,
    remark: str,
    action_key: str | None = None,
    ref_id: str | None = None,
) -> CreditLedger:
    user.credits_balance = max(0, int(user.credits_balance or 0) + int(delta))
    entry = CreditLedger(
        user_id=user.id,
        delta=int(delta),
        balance_after=user.credits_balance,
        source_type=source_type,
        action_key=action_key,
        ref_id=ref_id,
        remark=remark,
    )
    db.add(user)
    db.add(entry)
    return entry


def check_tier_permission(db: Session, user: User, min_tier: str, feature_name: str = "该功能") -> None:
    eff = get_effective_tier(db, user)
    if TIER_RANK.get(eff, 0) < TIER_RANK.get(min_tier, 0):
        label = {"pro": "Pro 专业版", "enterprise": "Enterprise 企业版"}.get(min_tier, min_tier)
        raise AppError(f"{feature_name}需升级至「{label}」后使用", code="PLAN_REQUIRED", status_code=403)


def check_zip_permission(db: Session, user: User, mode: str) -> None:
    eff = get_effective_tier(db, user)
    plan = get_plan_config(db, eff)
    if mode == "import" and not plan.allow_zip_import:
        raise AppError("导入外部 ZIP 场景包需升级至「Pro 专业版」或以上", code="PLAN_REQUIRED", status_code=403)
    if mode == "export" and not plan.allow_zip_export:
        raise AppError("打包导出 ZIP 场景包需升级至「Enterprise 企业/机构版」", code="PLAN_REQUIRED", status_code=403)


def check_creation_limit(db: Session, user: User, resource: str, current_count: int) -> None:
    eff = get_effective_tier(db, user)
    plan = get_plan_config(db, eff)
    limit_map = {
        "scene": (plan.max_custom_scenes, "1v1 自定义场景"),
        "debate": (plan.max_custom_debates, "多角色场景"),
        "knowledge": (plan.max_knowledge_docs, "私有知识库文档"),
    }
    limit, label = limit_map.get(resource, (-1, "资源"))
    if limit >= 0 and current_count >= limit:
        raise AppError(
            f"当前套餐最多支持 {limit} 个{label}（已达上限），请升级会员解锁更多配额",
            code="PLAN_LIMIT_REACHED",
            status_code=403,
        )


def check_and_consume_quota(
    db: Session,
    user: User,
    action_key: str,
    ref_id: str | None = None,
) -> dict[str, Any]:
    """三步走判定链路：活动限免 -> 每日免费额度 -> 超额使用积分抵扣开关。"""
    ensure_saas_defaults(db)
    eff = get_effective_tier(db, user)
    plan = get_plan_config(db, eff)
    today = _today_str()

    usage = (
        db.query(UserDailyUsage)
        .filter(UserDailyUsage.user_id == user.id, UserDailyUsage.date_str == today, UserDailyUsage.action_key == action_key)
        .first()
    )
    if not usage:
        usage = UserDailyUsage(user_id=user.id, date_str=today, action_key=action_key, free_used_count=0, paid_used_count=0, credits_spent=0)
        db.add(usage)

    # 1. 限时活动限免判定
    for camp in get_active_campaigns(db):
        if action_key in (camp.free_actions_json or []):
            usage.free_used_count += 1
            db.commit()
            return {"allowed": True, "mode": "campaign_free", "credits_spent": 0, "credits_balance": user.credits_balance}

    quota_cfg = (plan.quotas_json or {}).get(action_key) or {"credit_cost": 1, "allow_overage_credits": True}
    base_cost = max(0, int(quota_cfg.get("credit_cost", 1)))
    allow_overage = bool(quota_cfg.get("allow_overage_credits", True))

    # 2. 统一每日免费积分额度池判定（daily_free_credits == -1 表示无限）
    pool_cap = int(getattr(plan, "daily_free_credits", 40) if getattr(plan, "daily_free_credits", None) is not None else 40)
    today_rows = db.query(UserDailyUsage).filter(UserDailyUsage.user_id == user.id, UserDailyUsage.date_str == today).all()
    pool_used = sum(int(r.free_used_count or 0) for r in today_rows)

    if pool_cap == -1 or (pool_used + base_cost <= pool_cap):
        usage.free_used_count += base_cost
        db.commit()
        new_used = pool_used + base_cost
        remaining = -1 if pool_cap == -1 else max(0, pool_cap - new_used)
        return {
            "allowed": True,
            "mode": "free_quota",
            "credits_spent": 0,
            "pool_cost": base_cost,
            "remaining_free": remaining,
            "credits_balance": user.credits_balance,
        }

    # 3. 免费额度池已满 -> 校验后台全局开关 & 用户个人开关
    if not allow_overage:
        raise AppError(
            f"今日免费额度池已用满，「{ACTION_META.get(action_key, {}).get('label', action_key)}」需升级会员后使用",
            code="PLAN_REQUIRED",
            status_code=403,
        )

    if not bool(user.auto_use_credits):
        raise AppError(
            "今日免费额度池已用满（100%），请在任务中心开启「超额自动消耗回声积分」或升级会员",
            code="QUOTA_EXCEEDED",
            status_code=403,
        )

    cost = 0 if base_cost <= 0 else max(1, round(base_cost * float(plan.credit_discount_rate or 1.0)))
    if int(user.credits_balance or 0) < cost:
        raise AppError(
            f"今日免费额度池已用满，继续使用需 {cost} 回声积分（当前余额 {user.credits_balance} 点），请签到/完成任务或升级会员",
            code="INSUFFICIENT_CREDITS",
            status_code=403,
        )

    if cost > 0:
        label = ACTION_META.get(action_key, {}).get("label", action_key)
        _append_ledger(db, user, -cost, "overage_consume", f"超额使用：{label}", action_key=action_key, ref_id=ref_id)

    usage.paid_used_count += 1
    usage.credits_spent += cost
    db.commit()
    return {
        "allowed": True,
        "mode": "credits",
        "credits_spent": cost,
        "remaining_free": 0,
        "credits_balance": user.credits_balance,
    }


def get_saas_profile(db: Session, user: User) -> dict[str, Any]:
    ensure_saas_defaults(db)
    eff = get_effective_tier(db, user)
    plan = get_plan_config(db, eff)
    today = _today_str()
    usages = {
        u.action_key: u
        for u in db.query(UserDailyUsage).filter(UserDailyUsage.user_id == user.id, UserDailyUsage.date_str == today).all()
    }
    active_campaigns = get_active_campaigns(db)
    free_override_actions = {a for c in active_campaigns for a in (c.free_actions_json or [])}

    quotas = []
    pool_used = 0
    for key, meta in ACTION_META.items():
        cfg = (plan.quotas_json or {}).get(key) or {"credit_cost": 1, "allow_overage_credits": True}
        u = usages.get(key)
        used_pool_points = int(u.free_used_count) if u else 0
        pool_used += used_pool_points
        base_cost = int(cfg.get("credit_cost", 1))
        discounted_cost = 0 if base_cost <= 0 else max(1, round(base_cost * float(plan.credit_discount_rate or 1.0)))
        quotas.append(
            {
                "action_key": key,
                "label": meta["label"],
                "module": meta["module"],
                "pool_points_used": used_pool_points,
                "paid_used": int(u.paid_used_count) if u else 0,
                "credits_spent": int(u.credits_spent) if u else 0,
                "credit_cost": discounted_cost,
                "allow_overage_credits": bool(cfg.get("allow_overage_credits", True)),
                "campaign_free": key in free_override_actions,
            }
        )

    pool_cap = int(getattr(plan, "daily_free_credits", 40) if getattr(plan, "daily_free_credits", None) is not None else 40)
    pool_pct = 0 if pool_cap == -1 else min(100, round((pool_used / max(1, pool_cap)) * 100))

    from app.models import DebateTopic, PersonalDocument, Scene

    custom_scenes_count = db.query(Scene).filter(Scene.author_id == user.id, Scene.source != "builtin").count()
    custom_debates_count = db.query(DebateTopic).filter(DebateTopic.owner_id == user.id, DebateTopic.is_builtin == False).count()
    knowledge_docs_count = db.query(PersonalDocument).filter(PersonalDocument.owner_id == user.id).count()

    return {
        "user_id": user.id,
        "username": user.username,
        "plan_tier": eff,
        "plan_name": plan.name,
        "plan_expires_at": user.plan_expires_at.isoformat() if user.plan_expires_at else None,
        "credits_balance": int(user.credits_balance or 0),
        "auto_use_credits": bool(user.auto_use_credits),
        "checkin_streak": int(user.checkin_streak or 0),
        "checked_in_today": user.last_checkin_date == today,
        "daily_pool_capacity": pool_cap,
        "daily_pool_used": pool_used,
        "daily_pool_pct": pool_pct,
        "tokens_per_credit": get_billing_config(db).tokens_per_credit,
        "checkin_xp_rewards": CHECKIN_XP_REWARDS,
        "allow_zip_import": bool(plan.allow_zip_import),
        "allow_zip_export": bool(plan.allow_zip_export),
        "max_custom_scenes": plan.max_custom_scenes,
        "max_custom_debates": plan.max_custom_debates,
        "max_knowledge_docs": plan.max_knowledge_docs,
        "custom_scenes_count": custom_scenes_count,
        "custom_debates_count": custom_debates_count,
        "knowledge_docs_count": knowledge_docs_count,
        "quotas": quotas,
        "active_campaigns": [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "bonus_multiplier": c.bonus_multiplier,
                "free_actions_json": c.free_actions_json or [],
                "ends_at": c.ends_at.isoformat(),
            }
            for c in active_campaigns
        ],
    }


def list_plans(db: Session) -> list[dict[str, Any]]:
    ensure_saas_defaults(db)
    plans = db.query(SaasPlanConfig).all()
    plans.sort(key=lambda p: TIER_RANK.get(p.tier, 99))
    return [
        {
            "tier": p.tier,
            "name": p.name,
            "description": p.description,
            "monthly_price_yuan": p.monthly_price_yuan,
            "yearly_price_yuan": p.yearly_price_yuan,
            "monthly_grant_credits": p.monthly_grant_credits,
            "daily_free_credits": int(getattr(p, "daily_free_credits", 40) if getattr(p, "daily_free_credits", None) is not None else 40),
            "max_custom_scenes": p.max_custom_scenes,
            "max_custom_debates": p.max_custom_debates,
            "max_knowledge_docs": p.max_knowledge_docs,
            "allow_zip_import": bool(p.allow_zip_import),
            "allow_zip_export": bool(p.allow_zip_export),
            "checkin_multiplier": p.checkin_multiplier,
            "credit_discount_rate": p.credit_discount_rate,
            "quotas_json": p.quotas_json or {},
        }
        for p in plans
    ]


def daily_checkin(db: Session, user: User) -> dict[str, Any]:
    ensure_saas_defaults(db)
    today = _today_str()
    if user.last_checkin_date == today:
        raise AppError("今日已完成签到，请明天再来", code="ALREADY_CHECKED_IN", status_code=400)

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    streak = int(user.checkin_streak or 0) + 1 if user.last_checkin_date == yesterday else 1
    user.checkin_streak = streak
    user.last_checkin_date = today

    eff = get_effective_tier(db, user)
    plan = get_plan_config(db, eff)
    camp_mult = max([float(c.bonus_multiplier or 1.0) for c in get_active_campaigns(db)] or [1.0])

    base = round(10 * int(plan.checkin_multiplier or 1) * camp_mult)
    milestone_bonus = 0
    if streak % 30 == 0:
        milestone_bonus = 150
    elif streak % 7 == 0:
        milestone_bonus = 40
    elif streak % 3 == 0:
        milestone_bonus = 15

    total = base + milestone_bonus
    xp_earned = CHECKIN_XP_REWARDS[(streak - 1) % len(CHECKIN_XP_REWARDS)]
    _grant_user_xp(db, user.id, xp_earned)
    remark = f"每日签到（第 {streak} 天，+{xp_earned} XP）" + (f" + 连签奖励 {milestone_bonus}" if milestone_bonus else "")
    _append_ledger(db, user, total, "daily_checkin", remark)
    db.commit()
    return {
        "credits_earned": total,
        "xp_earned": xp_earned,
        "base_credits": base,
        "milestone_bonus": milestone_bonus,
        "checkin_streak": streak,
        "credits_balance": user.credits_balance,
    }


def record_task_progress(db: Session, user_id: int | None, task_code: str, increment: int = 1) -> None:
    """业务动作触发任务进度累积（静默容错，不影响主业务）。"""
    if not user_id:
        return
    try:
        ensure_saas_defaults(db)
        task = db.get(CreditTaskDef, task_code)
        if not task or not task.enabled:
            return
        period = "LIFETIME" if task.category == "onboarding" else _today_str()
        prog = (
            db.query(UserTaskProgress)
            .filter(UserTaskProgress.user_id == user_id, UserTaskProgress.task_code == task_code, UserTaskProgress.period_key == period)
            .first()
        )
        if not prog:
            prog = UserTaskProgress(user_id=user_id, task_code=task_code, period_key=period, progress_count=0, claimed_count=0)
            db.add(prog)
        max_progress = task.target_count * task.daily_limit
        prog.progress_count = min(max_progress, int(prog.progress_count or 0) + increment)
        db.commit()
    except Exception:
        logger.warning("任务进度记录失败: user=%s task=%s", user_id, task_code, exc_info=True)


def get_tasks_with_progress(db: Session, user: User) -> list[dict[str, Any]]:
    ensure_saas_defaults(db)
    tasks = db.query(CreditTaskDef).filter(CreditTaskDef.enabled == 1).order_by(CreditTaskDef.sort_order.asc()).all()
    today = _today_str()
    rows = (
        db.query(UserTaskProgress)
        .filter(UserTaskProgress.user_id == user.id, UserTaskProgress.period_key.in_([today, "LIFETIME"]))
        .all()
    )
    prog_map = {(r.task_code, r.period_key): r for r in rows}

    result = []
    for t in tasks:
        period = "LIFETIME" if t.category == "onboarding" else today
        p = prog_map.get((t.task_code, period))
        progress_count = int(p.progress_count) if p else 0
        claimed_count = int(p.claimed_count) if p else 0
        completed_units = progress_count // max(1, t.target_count)
        claimable = completed_units > claimed_count and claimed_count < t.daily_limit
        result.append(
            {
                "task_code": t.task_code,
                "title": t.title,
                "description": t.description,
                "category": t.category,
                "target_count": t.target_count,
                "reward_credits": t.reward_credits,
                "reward_xp": TASK_XP_MAP.get(t.task_code, 15),
                "daily_limit": t.daily_limit,
                "route_path": t.route_path,
                "progress_count": progress_count,
                "claimed_count": claimed_count,
                "claimable": claimable,
                "finished": claimed_count >= t.daily_limit,
            }
        )
    return result


def claim_task_reward(db: Session, user: User, task_code: str) -> dict[str, Any]:
    ensure_saas_defaults(db)
    task = db.get(CreditTaskDef, task_code)
    if not task or not task.enabled:
        raise AppError("任务不存在或已下线", code="NOT_FOUND", status_code=404)
    period = "LIFETIME" if task.category == "onboarding" else _today_str()
    prog = (
        db.query(UserTaskProgress)
        .filter(UserTaskProgress.user_id == user.id, UserTaskProgress.task_code == task_code, UserTaskProgress.period_key == period)
        .first()
    )
    if not prog:
        raise AppError("任务尚未完成", code="TASK_NOT_COMPLETED", status_code=400)
    if prog.claimed_count >= task.daily_limit:
        raise AppError("该任务奖励已全部领取", code="TASK_ALREADY_CLAIMED", status_code=400)
    completed_units = prog.progress_count // max(1, task.target_count)
    if completed_units <= prog.claimed_count:
        raise AppError("当前进度不足，请继续完成任务", code="TASK_NOT_COMPLETED", status_code=400)

    camp_mult = max([float(c.bonus_multiplier or 1.0) for c in get_active_campaigns(db)] or [1.0])
    reward = round(task.reward_credits * camp_mult)
    xp_earned = TASK_XP_MAP.get(task.task_code, 15)
    prog.claimed_count += 1
    _grant_user_xp(db, user.id, xp_earned)
    _append_ledger(db, user, reward, "task_reward", f"完成任务：{task.title}（+{xp_earned} XP）", action_key=task_code)
    db.commit()
    return {"credits_earned": reward, "xp_earned": xp_earned, "credits_balance": user.credits_balance}


def mock_checkout(
    db: Session,
    user: User,
    order_type: str,
    target_tier: str | None = None,
    billing_cycle: str = "monthly",
    credit_pack_code: str | None = None,
) -> dict[str, Any]:
    ensure_saas_defaults(db)
    order_no = f"MOCK{datetime.now().strftime('%Y%m%d%H%M%S')}{secrets.token_hex(3).upper()}"

    if order_type == "plan_upgrade":
        if target_tier not in ("pro", "enterprise"):
            raise AppError("请选择有效的目标订阅套餐", code="INVALID_TIER", status_code=400)
        plan = get_plan_config(db, target_tier)
        days = 365 if billing_cycle == "yearly" else 30
        price = plan.yearly_price_yuan if billing_cycle == "yearly" else plan.monthly_price_yuan
        grant_credits = plan.monthly_grant_credits * (12 if billing_cycle == "yearly" else 1)

        now = utcnow()
        base_time = user.plan_expires_at if (user.plan_tier == target_tier and user.plan_expires_at and user.plan_expires_at > now) else now
        user.plan_tier = target_tier
        user.plan_expires_at = base_time + timedelta(days=days)

        order = SubscriptionOrder(
            order_no=order_no,
            user_id=user.id,
            order_type="plan_upgrade",
            target_tier=target_tier,
            billing_cycle=billing_cycle,
            credits_granted=grant_credits,
            amount_yuan=price,
            status="paid",
            payment_channel="mock_checkout",
        )
        db.add(order)
        if grant_credits > 0:
            _append_ledger(db, user, grant_credits, "plan_grant", f"开通 {plan.name}（{billing_cycle}）赠送积分", ref_id=order_no)
        db.commit()
        return {
            "order_no": order_no,
            "plan_tier": user.plan_tier,
            "plan_expires_at": user.plan_expires_at.isoformat(),
            "credits_granted": grant_credits,
            "credits_balance": user.credits_balance,
        }

    pack = CREDIT_PACKS.get(credit_pack_code or "")
    if not pack:
        raise AppError("积分加油包不存在", code="NOT_FOUND", status_code=404)
    order = SubscriptionOrder(
        order_no=order_no,
        user_id=user.id,
        order_type="credit_pack",
        credits_granted=pack["credits"],
        amount_yuan=pack["price_yuan"],
        status="paid",
        payment_channel="mock_checkout",
    )
    db.add(order)
    _append_ledger(db, user, pack["credits"], "credit_pack", f"购买积分加油包：{pack['name']}", ref_id=order_no)
    db.commit()
    return {
        "order_no": order_no,
        "credits_granted": pack["credits"],
        "credits_balance": user.credits_balance,
    }


def redeem_code(db: Session, user: User, code_str: str) -> dict[str, Any]:
    clean_code = code_str.strip().upper()
    rc = db.query(RedeemCode).filter(RedeemCode.code == clean_code).first()
    if not rc:
        raise AppError("兑换码不存在，请核对后重试", code="INVALID_CODE", status_code=404)
    if rc.is_used:
        raise AppError("该兑换码已被核销", code="CODE_USED", status_code=400)
    if rc.expires_at and rc.expires_at < utcnow():
        raise AppError("该兑换码已过期", code="CODE_EXPIRED", status_code=400)

    rc.is_used = 1
    rc.used_by_user_id = user.id
    rc.used_at = utcnow()
    db.add(rc)

    if rc.reward_tier in ("pro", "enterprise") and rc.reward_days > 0:
        now = utcnow()
        base_time = user.plan_expires_at if (user.plan_tier == rc.reward_tier and user.plan_expires_at and user.plan_expires_at > now) else now
        user.plan_tier = rc.reward_tier
        user.plan_expires_at = base_time + timedelta(days=rc.reward_days)

    if rc.reward_credits > 0:
        _append_ledger(db, user, rc.reward_credits, "redeem_code", f"兑换码核销：{clean_code}", ref_id=clean_code)

    db.commit()
    return {
        "code": clean_code,
        "reward_credits": rc.reward_credits,
        "reward_tier": rc.reward_tier,
        "reward_days": rc.reward_days,
        "plan_tier": user.plan_tier,
        "plan_expires_at": user.plan_expires_at.isoformat() if user.plan_expires_at else None,
        "credits_balance": user.credits_balance,
    }


def list_user_ledger(db: Session, user_id: int, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    q = db.query(CreditLedger).filter(CreditLedger.user_id == user_id)
    total = q.count()
    items = q.order_by(desc(CreditLedger.id)).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": item.id,
                "delta": item.delta,
                "balance_after": item.balance_after,
                "source_type": item.source_type,
                "action_key": item.action_key,
                "ref_id": item.ref_id,
                "remark": item.remark,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ],
    }

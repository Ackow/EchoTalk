"""管理端概览仪表盘与全平台 API Token 消耗统计。"""
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.timeutil import utcnow
from app.models import (
    ApiTokenUsage,
    AuthSession,
    AvatarPreference,
    AvatarPreset,
    Document,
    PracticeSession,
    PracticeTurn,
    Scene,
    User,
)
from app.services.admin.avatars import AVATAR_CATALOG, VOICE_CATALOG
from app.services.avatar_service import normalized_voice


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

    avatar_dist_rows = db.execute(
        select(AvatarPreference.avatar_id, func.count().label("cnt")).group_by(AvatarPreference.avatar_id)
    ).all()
    voice_dist_rows = db.execute(
        select(AvatarPreference.voice_style, func.count().label("cnt")).group_by(AvatarPreference.voice_style)
    ).all()

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

    from app.models import DebateSession, DebateTopic, ReviewItem
    from app.models.saas import CreditLedger, SubscriptionOrder

    debate_topic_total = db.scalar(select(func.count()).select_from(DebateTopic)) or 0
    debate_session_total = db.scalar(select(func.count()).select_from(DebateSession)) or 0
    review_total = db.scalar(select(func.count()).select_from(ReviewItem)) or 0
    pro_users = db.scalar(select(func.count()).select_from(User).where(User.plan_tier == "pro")) or 0
    ent_users = db.scalar(select(func.count()).select_from(User).where(User.plan_tier == "enterprise")) or 0
    credits_today_spent = (
        db.scalar(
            select(func.coalesce(func.sum(CreditLedger.delta), 0)).where(
                CreditLedger.delta < 0, CreditLedger.created_at >= today_start
            )
        )
        or 0
    )
    orders_total = db.scalar(select(func.count()).select_from(SubscriptionOrder)) or 0

    return {
        "users": {
            "total": user_total,
            "admins": admin_total,
            "active_tokens": active_auth_sessions,
            "pro": pro_users,
            "enterprise": ent_users,
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
        "debates": {
            "topics": debate_topic_total,
            "sessions": debate_session_total,
        },
        "reviews": {
            "total": review_total,
        },
        "saas": {
            "paid_users": pro_users + ent_users,
            "credits_today_spent": abs(int(credits_today_spent)),
            "orders_total": orders_total,
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

    by_category_rows = db.execute(
        select(
            ApiTokenUsage.category,
            func.coalesce(func.sum(ApiTokenUsage.total_tokens), 0),
            func.coalesce(func.sum(ApiTokenUsage.call_count), 0),
        )
        .where(*conditions)
        .group_by(ApiTokenUsage.category)
    ).all()

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

    total_logs = db.scalar(select(func.count()).select_from(ApiTokenUsage).where(*conditions)) or 0
    log_rows = db.execute(
        select(ApiTokenUsage, User.username)
        .outerjoin(User, User.id == ApiTokenUsage.user_id)
        .where(*conditions)
        .order_by(ApiTokenUsage.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    from app.models.saas import CreditLedger, SubscriptionOrder
    from app.services.saas_service import get_billing_config

    cfg = get_billing_config(db)
    tpc = int(cfg.tokens_per_credit or 1000)
    prompt_price = float(cfg.prompt_price_per_million or 2.0)
    completion_price = float(cfg.completion_price_per_million or 8.0)

    ledger_conds = [CreditLedger.delta < 0, CreditLedger.created_at >= start_day]
    if user_id is not None:
        ledger_conds.append(CreditLedger.user_id == user_id)
    credits_spent_raw = db.scalar(select(func.coalesce(func.sum(CreditLedger.delta), 0)).where(*ledger_conds)) or 0
    credits_spent = abs(int(credits_spent_raw))
    actual_tokens = int(summary_row[0])
    prompt_tok = int(summary_row[1])
    completion_tok = int(summary_row[2])

    order_conds = [SubscriptionOrder.status == "paid", SubscriptionOrder.created_at >= start_day]
    if user_id is not None:
        order_conds.append(SubscriptionOrder.user_id == user_id)
    revenue_yuan = float(db.scalar(select(func.coalesce(func.sum(SubscriptionOrder.amount_yuan), 0)).where(*order_conds)) or 0)
    order_count = int(db.scalar(select(func.count()).select_from(SubscriptionOrder).where(*order_conds)) or 0)
    api_cost_yuan = round((prompt_tok / 1_000_000) * prompt_price + (completion_tok / 1_000_000) * completion_price, 4)
    gross_profit_yuan = round(revenue_yuan - api_cost_yuan, 2)
    gross_margin_pct = round((gross_profit_yuan / revenue_yuan) * 100, 1) if revenue_yuan > 0 else 0.0

    return {
        "summary": {
            "total_tokens": actual_tokens,
            "prompt_tokens": prompt_tok,
            "completion_tokens": completion_tok,
            "total_calls": int(summary_row[3]),
            "today_tokens": int(today_tokens),
        },
        "billing_config": {
            "tokens_per_credit": tpc,
            "prompt_price_per_million": prompt_price,
            "completion_price_per_million": completion_price,
        },
        "credit_conversion": {
            "tokens_per_credit": tpc,
            "credits_spent": credits_spent,
            "equivalent_tokens": credits_spent * tpc,
            "actual_tokens": actual_tokens,
            "actual_tokens_per_credit": round(actual_tokens / credits_spent) if credits_spent > 0 else 0,
        },
        "profit_analysis": {
            "revenue_yuan": round(revenue_yuan, 2),
            "order_count": order_count,
            "api_cost_yuan": round(api_cost_yuan, 2),
            "gross_profit_yuan": gross_profit_yuan,
            "gross_margin_pct": gross_margin_pct,
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

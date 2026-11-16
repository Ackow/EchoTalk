"""SaaS 订阅套餐、每日配额、积分账本、任务活动与模拟订单数据模型。"""
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint

from app.core.database import Base
from app.core.timeutil import utcnow


class SaasPlanConfig(Base):
    """SaaS 套餐与配额规则表（支持管理端动态热更新）。"""

    __tablename__ = "saas_plan_configs"

    tier = Column(String(20), primary_key=True)  # free / pro / enterprise
    name = Column(String(50), nullable=False)
    description = Column(String(200), nullable=False, default="")
    monthly_price_yuan = Column(Integer, nullable=False, default=0)
    yearly_price_yuan = Column(Integer, nullable=False, default=0)
    monthly_grant_credits = Column(Integer, nullable=False, default=0)
    daily_free_credits = Column(Integer, nullable=False, default=40)  # 每日共享免费额度池点数（-1 表示无限）
    max_custom_scenes = Column(Integer, nullable=False, default=2)  # -1 表示无限制
    max_custom_debates = Column(Integer, nullable=False, default=1)  # -1 表示无限制
    max_knowledge_docs = Column(Integer, nullable=False, default=0)  # -1 表示无限制
    allow_zip_import = Column(Integer, nullable=False, default=0)  # 0/1：是否允许导入场景包 ZIP
    allow_zip_export = Column(Integer, nullable=False, default=0)  # 0/1：是否允许导出场景包 ZIP
    checkin_multiplier = Column(Integer, nullable=False, default=1)  # 签到积分倍率
    credit_discount_rate = Column(Float, nullable=False, default=1.0)  # 超额消耗积分折扣（如 0.8 表示 8 折）
    quotas_json = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class UserDailyUsage(Base):
    """用户每日免费配额与积分消耗统计表。"""

    __tablename__ = "user_daily_usage"
    __table_args__ = (UniqueConstraint("user_id", "date_str", "action_key", name="uq_user_daily_action"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date_str = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    action_key = Column(String(40), nullable=False, index=True)
    free_used_count = Column(Integer, nullable=False, default=0)
    paid_used_count = Column(Integer, nullable=False, default=0)
    credits_spent = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class CreditLedger(Base):
    """用户积分收支流水账本表。"""

    __tablename__ = "credit_ledger"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    delta = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    source_type = Column(String(40), nullable=False, index=True)
    # signup_bonus / daily_checkin / task_reward / campaign_bonus / redeem_code / plan_grant / credit_pack / admin_adjust / overage_consume
    action_key = Column(String(40), nullable=True)
    ref_id = Column(String(64), nullable=True)
    remark = Column(String(200), nullable=False, default="")
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)


class CreditTaskDef(Base):
    """积分任务定义表（管理端可配置）。"""

    __tablename__ = "credit_task_defs"

    task_code = Column(String(40), primary_key=True)
    title = Column(String(80), nullable=False)
    description = Column(String(200), nullable=False, default="")
    category = Column(String(20), nullable=False, default="daily")  # daily / onboarding
    target_count = Column(Integer, nullable=False, default=1)
    reward_credits = Column(Integer, nullable=False, default=10)
    daily_limit = Column(Integer, nullable=False, default=1)
    route_path = Column(String(64), nullable=False, default="/")  # 前端跳转路径
    enabled = Column(Integer, nullable=False, default=1)
    sort_order = Column(Integer, nullable=False, default=10)


class UserTaskProgress(Base):
    """用户任务完成与领奖记录表。"""

    __tablename__ = "user_task_progress"
    __table_args__ = (UniqueConstraint("user_id", "task_code", "period_key", name="uq_user_task_period"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    task_code = Column(String(40), nullable=False, index=True)
    period_key = Column(String(20), nullable=False)  # YYYY-MM-DD 或 LIFETIME
    progress_count = Column(Integer, nullable=False, default=0)
    claimed_count = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class SaasCampaign(Base):
    """限时运营活动表（积分翻倍或特定功能限免）。"""

    __tablename__ = "saas_campaigns"

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    description = Column(String(200), nullable=False, default="")
    bonus_multiplier = Column(Float, nullable=False, default=1.0)  # 任务/签到积分倍率
    free_actions_json = Column(JSON, nullable=False, default=list)  # 限免的 action_key 列表
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    enabled = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class SubscriptionOrder(Base):
    """模拟订阅与积分充值订单表（免真实支付接入）。"""

    __tablename__ = "subscription_orders"

    id = Column(Integer, primary_key=True)
    order_no = Column(String(40), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    order_type = Column(String(20), nullable=False)  # plan_upgrade / credit_pack
    target_tier = Column(String(20), nullable=True)  # pro / enterprise
    billing_cycle = Column(String(20), nullable=True)  # monthly / yearly
    credits_granted = Column(Integer, nullable=False, default=0)
    amount_yuan = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="paid")  # paid / refunded
    payment_channel = Column(String(30), nullable=False, default="mock_checkout")
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)


class RedeemCode(Base):
    """兑换码 / 激活码表。"""

    __tablename__ = "redeem_codes"

    id = Column(Integer, primary_key=True)
    code = Column(String(40), unique=True, nullable=False, index=True)
    reward_type = Column(String(20), nullable=False)  # credits / plan_days
    reward_credits = Column(Integer, nullable=False, default=0)
    reward_tier = Column(String(20), nullable=True)  # pro / enterprise
    reward_days = Column(Integer, nullable=False, default=0)
    is_used = Column(Integer, nullable=False, default=0)
    used_by_user_id = Column(Integer, nullable=True, index=True)
    used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    note = Column(String(120), nullable=False, default="")
    created_at = Column(DateTime, default=utcnow, nullable=False)


class SaasBillingConfig(Base):
    """全局算力换算与 API 成本单价配置表（用于后台盈利核算）。"""

    __tablename__ = "saas_billing_configs"

    id = Column(Integer, primary_key=True)  # 固定 id=1
    tokens_per_credit = Column(Integer, nullable=False, default=1000)  # 1 回声积分对应理论 Tokens
    prompt_price_per_million = Column(Float, nullable=False, default=2.0)  # 输入单价：元 / 1M Tokens
    completion_price_per_million = Column(Float, nullable=False, default=8.0)  # 输出单价：元 / 1M Tokens
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

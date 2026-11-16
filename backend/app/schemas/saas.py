"""SaaS 订阅、配额开关、积分任务与兑换码请求/响应结构。"""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class SaasSettingsUpdate(BaseModel):
    auto_use_credits: bool


class MockCheckoutRequest(BaseModel):
    order_type: Literal["plan_upgrade", "credit_pack"]
    target_tier: Literal["pro", "enterprise"] | None = None
    billing_cycle: Literal["monthly", "yearly"] = "monthly"
    credit_pack_code: str | None = None


class RedeemCodeRequest(BaseModel):
    code: str = Field(min_length=4, max_length=40)


class AdminPlanUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    monthly_price_yuan: int | None = Field(default=None, ge=0)
    yearly_price_yuan: int | None = Field(default=None, ge=0)
    monthly_grant_credits: int | None = Field(default=None, ge=0)
    daily_free_credits: int | None = Field(default=None, ge=-1)
    max_custom_scenes: int | None = Field(default=None, ge=-1)
    max_custom_debates: int | None = Field(default=None, ge=-1)
    max_knowledge_docs: int | None = Field(default=None, ge=-1)
    allow_zip_import: bool | None = None
    allow_zip_export: bool | None = None
    checkin_multiplier: int | None = Field(default=None, ge=1, le=10)
    credit_discount_rate: float | None = Field(default=None, ge=0.1, le=1.0)
    quotas_json: dict[str, Any] | None = None


class AdminTaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    target_count: int | None = Field(default=None, ge=1)
    reward_credits: int | None = Field(default=None, ge=0)
    daily_limit: int | None = Field(default=None, ge=1)
    enabled: bool | None = None
    sort_order: int | None = None


class AdminCampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = ""
    bonus_multiplier: float = Field(default=2.0, ge=1.0, le=10.0)
    free_actions_json: list[str] = Field(default_factory=list)
    starts_at: datetime
    ends_at: datetime
    enabled: bool = True


class AdminCampaignUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    bonus_multiplier: float | None = Field(default=None, ge=1.0, le=10.0)
    free_actions_json: list[str] | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    enabled: bool | None = None


class AdminUserGrantRequest(BaseModel):
    plan_tier: Literal["free", "pro", "enterprise"] | None = None
    plan_days: int | None = Field(default=None, ge=0, le=3650)
    credits_delta: int = Field(default=0, ge=-100000, le=100000)
    remark: str = Field(default="管理员手动调整", max_length=200)


class AdminRedeemGenerateRequest(BaseModel):
    count: int = Field(default=5, ge=1, le=50)
    reward_type: Literal["credits", "plan_days"] = "credits"
    reward_credits: int = Field(default=200, ge=0, le=100000)
    reward_tier: Literal["pro", "enterprise"] | None = None
    reward_days: int = Field(default=7, ge=0, le=365)
    prefix: str = Field(default="ECHO", min_length=2, max_length=10)
    note: str = Field(default="", max_length=120)

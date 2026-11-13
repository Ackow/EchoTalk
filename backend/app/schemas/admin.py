"""管理端 API 请求与响应结构。"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AdminUserCreate(BaseModel):
    """管理员创建用户请求体。"""

    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    is_admin: bool = False


class AdminUserUpdate(BaseModel):
    """管理员更新用户请求体。"""

    is_admin: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class AdminAvatarPreferenceUpsert(BaseModel):
    """管理员创建或更新用户的数字人偏好。"""

    user_id: int
    scene_id: str | None = Field(default=None, max_length=50)
    avatar_id: str = Field(min_length=1, max_length=50)
    voice_style: str = Field(min_length=1, max_length=50)
    speech_rate: float = Field(default=1.0, ge=0.75, le=1.25)
    lip_sync_enabled: bool = True


class AdminSceneUpdate(BaseModel):
    """管理员更新场景包或元数据。"""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    category: str | None = Field(default=None, max_length=30)
    mode: str | None = Field(default=None, max_length=20)
    difficulty: str | None = Field(default=None, max_length=20)
    status: str | None = Field(default=None, pattern="^(private|published)$")
    package_json: dict[str, Any] | None = None


class BatchIntIds(BaseModel):
    """批量整型 ID 请求体。"""

    ids: list[int] = Field(min_length=1, max_length=200)


class BatchStrIds(BaseModel):
    """批量字符串 ID 请求体。"""

    ids: list[str] = Field(min_length=1, max_length=200)


class BatchSceneStatus(BaseModel):
    """批量更新场景发布状态请求体。"""

    ids: list[str] = Field(min_length=1, max_length=200)
    status: str = Field(pattern="^(private|published)$")


class AvatarPrefKey(BaseModel):
    """数字人偏好复合主键。"""

    user_id: int
    scene_id: str = ""


class BatchAvatarPrefDelete(BaseModel):
    """批量删除数字人偏好请求体。"""

    items: list[AvatarPrefKey] = Field(min_length=1, max_length=200)


class AdminAvatarPresetUpdate(BaseModel):
    """管理员更新创建的数字人角色请求体。"""

    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=200)
    tagline: str | None = Field(default=None, max_length=200)
    greeting: str | None = Field(default=None, max_length=300)
    theme: str | None = Field(default=None, max_length=30)
    default_voice: str | None = Field(default=None, max_length=50)
    is_public: bool | None = None
    appearance: dict[str, Any] | None = None


class BatchAvatarPresetPublic(BaseModel):
    """批量设置数字人公开状态请求体。"""

    ids: list[str] = Field(min_length=1, max_length=200)
    is_public: bool

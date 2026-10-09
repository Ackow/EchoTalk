"""账户接口的数据校验与响应结构。"""
from datetime import datetime

from pydantic import BaseModel, Field


class Credentials(BaseModel):
    """注册/登录共用的请求体。"""

    username: str = Field(min_length=3, max_length=50)  # 用户名：3~50 字符
    password: str = Field(min_length=8, max_length=128)  # 密码：8~128 字符


class UserResponse(BaseModel):
    """用户信息响应：不包含密码摘要。"""

    id: int  # 用户 ID
    username: str  # 用户名
    created_at: datetime  # 注册时间（UTC）

    model_config = {"from_attributes": True}  # 允许直接从 ORM 对象读取同名字段


class AuthResponse(BaseModel):
    """注册/登录成功响应：令牌 + 用户信息。"""

    access_token: str  # 访问令牌：用于 Authorization: Bearer 头
    token_type: str = "bearer"  # 令牌类型：固定 bearer
    user: UserResponse  # 当前账户信息


class AvatarPreferenceUpdate(BaseModel):
    """数字人偏好保存请求：整体覆盖保存。

    avatar_id / voice_style 为前端固定清单内的 id，后端不持有清单、只校验非空；
    scene_id 由服务层校验场景存在且对当前用户可见。
    """

    avatar_id: str = Field(min_length=1, max_length=50)  # 数字人形象 ID
    role_id: str | None = Field(default=None, max_length=50)  # 交流身份 ID：空表示跟随缺省
    voice_style: str = Field(min_length=1, max_length=50)  # 音色风格
    scene_id: str | None = Field(default=None, max_length=50)  # 默认训练场景：空表示跟随场景推荐
    speech_rate: float = Field(default=1.0, ge=0.75, le=1.25)  # 语速倍率
    lip_sync_enabled: bool = True  # 口型演示开关


class AvatarPreferenceResponse(BaseModel):
    """数字人偏好响应：未保存过时各选择字段为 null（表示跟随缺省/场景推荐）。"""

    avatar_id: str | None = None  # 数字人形象 ID
    role_id: str | None = None  # 交流身份 ID
    voice_style: str | None = None  # 音色风格
    scene_id: str | None = None  # 默认训练场景
    speech_rate: float = 1.0  # 语速倍率
    lip_sync_enabled: bool = True  # 口型演示开关
    updated_at: datetime | None = None  # 最近保存时间（UTC）：从未保存为 null

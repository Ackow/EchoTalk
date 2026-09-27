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

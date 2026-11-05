"""session API 请求与响应结构。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

class CreateSession(BaseModel):
    """创建练习会话请求：指定一个当前用户可访问的场景。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    scene_id: str = Field(min_length=2, max_length=50)


class SubmitTurn(BaseModel):
    """提交文字轮次请求：request_id 用于安全重试与幂等去重。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    text: str = Field(min_length=1, max_length=4000)



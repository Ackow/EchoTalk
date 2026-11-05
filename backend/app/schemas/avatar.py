"""avatar API 请求与响应结构。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

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



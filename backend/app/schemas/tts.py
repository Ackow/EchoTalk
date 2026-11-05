"""语音合成与问候音频的参数校验。"""
from pydantic import BaseModel, Field, field_validator

from app.services import tts_service


class VoiceOptions(BaseModel):
    voice_style: str = "emma"
    speech_rate: float = Field(default=1.0, ge=0.75, le=1.25)

    @field_validator("voice_style")
    @classmethod
    def normalize_style(cls, value: str) -> str:
        """兼容历史声音名称，拒绝白名单之外的声音。"""
        style = tts_service.normalize_style(value)
        if style is None:
            raise ValueError("不支持的声音预设")
        return style


class TtsRequest(VoiceOptions):
    text: str = Field(min_length=1, max_length=tts_service.TEXT_MAX)

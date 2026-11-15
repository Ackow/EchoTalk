"""语音识别接口的公开响应，不包含云服务凭据。"""
from pydantic import BaseModel, Field


class SpeechStatus(BaseModel):
    configured: bool
    max_duration: int
    sample_rate: int


class TranscriptionResponse(BaseModel):
    text: str
    duration: float
    provider: str = "tencent"
    audio_token: str | None = None


class ExplainRequest(BaseModel):
    text: str = Field(min_length=1, max_length=240)
    context: str = Field(default="", max_length=600)


class ExplainResponse(BaseModel):
    text: str
    phonetic: str = ""
    translation: str
    tip: str = ""

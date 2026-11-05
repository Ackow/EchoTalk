"""语音识别接口的公开响应，不包含云服务凭据。"""
from pydantic import BaseModel


class SpeechStatus(BaseModel):
    configured: bool
    max_duration: int
    sample_rate: int


class TranscriptionResponse(BaseModel):
    text: str
    duration: float
    provider: str = "tencent"

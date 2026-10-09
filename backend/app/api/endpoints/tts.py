"""TTS 语音合成接口（控制器层）：GET /api/tts/voices、POST /api/tts/synthesize。

只负责解析请求、调用服务层、格式化响应，不含业务逻辑。
"""
from fastapi import APIRouter, Response
from pydantic import BaseModel, Field, field_validator

from app.services import tts_service

router = APIRouter(prefix="/tts", tags=["语音合成"])


class TtsRequest(BaseModel):
    """合成请求：文本 + 声音预设 + 语速（0.75~1.25，与偏好字段同界）。"""

    text: str = Field(min_length=1, max_length=tts_service.TEXT_MAX)
    voice_style: str
    speech_rate: float = Field(default=1.0, ge=0.75, le=1.25)

    @field_validator("voice_style")
    @classmethod
    def normalize_style(cls, value: str) -> str:
        """归一并校验 style（兼容历史枚举 us_female 等），非法值转 422。"""
        style = tts_service.normalize_style(value)
        if style is None:
            raise ValueError("不支持的声音预设")
        return style


@router.get("/voices")
async def list_tts_voices():
    """声音清单与渠道可用性（探测结果缓存 5 分钟）。"""
    available = await tts_service.probe_voices()
    return [
        {"style": style, "tts_voice": voice, "available": available.get(style, False)}
        for style, voice in tts_service.TTS_VOICES.items()
    ]


@router.post("/synthesize")
async def synthesize(payload: TtsRequest):
    """文本合成 MP3 音频流（audio/mpeg），供前端试听与播报。"""
    audio = await tts_service.synthesize(payload.text, payload.voice_style, payload.speech_rate)
    return Response(content=audio, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})

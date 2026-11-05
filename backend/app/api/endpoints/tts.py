"""TTS 语音合成接口（控制器层）：GET /api/tts/voices、POST /api/tts/synthesize。

只负责解析请求、调用服务层、格式化响应，不含业务逻辑。
"""
from fastapi import APIRouter, Response
from app.schemas.tts import TtsRequest

from app.services import tts_service

router = APIRouter(prefix="/tts", tags=["语音合成"])


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

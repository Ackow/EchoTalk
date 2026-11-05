"""腾讯云 Flash ASR：校验浏览器 WAV，签名后上传并提取英文转写。"""
import base64
import hashlib
import hmac
import io
import logging
import time
import wave

import httpx

from app.core import config
from app.core.errors import AppError

logger = logging.getLogger("echotalk")
MAX_DURATION = 60
SAMPLE_RATE = 16000
MAX_BYTES = 2_000_000


def configured() -> bool:
    """只报告识别服务是否已配置，不把密钥发送给客户端。"""
    return bool(config.ASR_APP_ID and config.ASR_SECRET_ID and config.ASR_SECRET_KEY)


def validate_audio(audio: bytes) -> float:
    """验证实际 WAV 内容、采样规格与时长，返回秒数。"""
    if not audio or len(audio) > MAX_BYTES:
        raise AppError("录音为空或超过大小限制", code="ASR_AUDIO_SIZE", status_code=422)
    try:
        with wave.open(io.BytesIO(audio), "rb") as wav:
            frames = wav.getnframes()
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getcomptype()) != (1, 2, SAMPLE_RATE, "NONE"):
                raise ValueError("unsupported WAV specification")
            duration = frames / SAMPLE_RATE
            if not 0.3 <= duration <= MAX_DURATION:
                raise ValueError("duration out of range")
            if len(wav.readframes(frames)) != frames * 2:
                raise ValueError("truncated WAV")
            return duration
    except (wave.Error, EOFError, ValueError, OSError) as exc:
        raise AppError("请上传 0.3–60 秒、16kHz 单声道 PCM16 WAV 录音", code="ASR_INVALID_AUDIO", status_code=422) from exc


def sign_request(app_id: str, secret_key: str, params: dict) -> str:
    """对排序后的完整请求参数计算腾讯 Flash API 的 HMAC-SHA1 签名。"""
    query = "&".join(f"{key}={value}" for key, value in sorted(params.items()))
    raw = f"POSTasr.cloud.tencent.com/asr/flash/v1/{app_id}?{query}"
    return base64.b64encode(hmac.new(secret_key.encode(), raw.encode(), hashlib.sha1).digest()).decode()


async def transcribe(audio: bytes) -> dict:
    """识别一段经过校验的英文录音；配置缺失或服务失败时显式报错。"""
    duration = validate_audio(audio)
    if not configured():
        raise AppError("语音识别服务尚未配置，请先使用文字输入", code="ASR_NOT_CONFIGURED", status_code=503)
    params = {
        "secretid": config.ASR_SECRET_ID, "timestamp": int(time.time()),
        "engine_type": "16k_en", "voice_format": "wav", "filter_punc": 0,
        "filter_modal": 0, "filter_dirty": 0, "convert_num_mode": 1,
        "word_info": 0, "first_channel_only": 1, "speaker_diarization": 0,
    }
    headers = {
        "Authorization": sign_request(config.ASR_APP_ID, config.ASR_SECRET_KEY, params),
        "Content-Type": "application/octet-stream",
    }
    try:
        # 不自动重试计费请求；日志不记录凭据、带签名 URL 或用户录音/原文。
        async with httpx.AsyncClient(timeout=35) as client:
            response = await client.post(
                f"https://asr.cloud.tencent.com/asr/flash/v1/{config.ASR_APP_ID}",
                params=params, headers=headers, content=audio,
            )
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict) or data.get("code") != 0:
            logger.warning("ASR 服务返回失败，code=%s", data.get("code") if isinstance(data, dict) else "invalid")
            raise AppError("语音识别失败，请稍后重试或使用文字输入", code="ASR_PROVIDER_FAILED", status_code=502)
        channels = data.get("flash_result", [])
        if not isinstance(channels, list):
            raise ValueError("invalid result")
        text = " ".join(item.get("text", "") for item in channels if isinstance(item, dict)).strip()
    except AppError:
        raise
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.warning("ASR 请求失败，type=%s", type(exc).__name__)
        raise AppError("语音识别暂不可用，请重试或使用文字输入", code="ASR_PROVIDER_FAILED", status_code=502) from exc
    if not text:
        raise AppError("没有识别到语音，请靠近麦克风重新录制", code="ASR_NO_SPEECH", status_code=422)
    if len(text) > 4000:
        raise AppError("识别内容过长，请缩短录音后重试", code="ASR_TEXT_TOO_LONG", status_code=422)
    return {"text": text, "duration": round(duration, 3), "provider": "tencent"}

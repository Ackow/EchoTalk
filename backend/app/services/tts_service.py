"""TTS 语音合成服务：基于 edge-tts 将文本合成为 MP3 音频。

声音清单与前端 FALLBACK_VOICES 保持一致（style 为约定枚举）；
合成结果为 audio/mpeg 字节流，语速按 speech_rate 百分比换算。
"""
import logging
import time

import edge_tts

from app.core.errors import AppError

logger = logging.getLogger("echotalk")

# 声音白名单：style（声音名小写）→ edge-tts 渠道 voice 名，覆盖美/英/澳口音
TTS_VOICES: dict[str, str] = {
    "emma": "en-US-EmmaNeural",
    "aria": "en-US-AriaNeural",
    "jenny": "en-US-JennyNeural",
    "andrew": "en-US-AndrewNeural",
    "brian": "en-US-BrianNeural",
    "guy": "en-US-GuyNeural",
    "sonia": "en-GB-SoniaNeural",
    "ryan": "en-GB-RyanNeural",
    "natasha": "en-AU-NatashaNeural",
    "william": "en-AU-WilliamNeural",
}

# 历史风格枚举归一：早期版本用口音_性别作 style，统一映射到声音名
STYLE_ALIASES: dict[str, str] = {
    "us_female": "emma",
    "uk_female": "sonia",
    "us_male": "andrew",
}


def normalize_style(style: str) -> str | None:
    """归一 style：兼容历史枚举（us_female 等），白名单外返回 None。"""
    style = (style or "").strip().lower()
    return STYLE_ALIASES.get(style, style if style in TTS_VOICES else None)

TEXT_MAX = 500  # 单次合成文本上限：试听与短句播报足够，防滥用

# 可用性探测缓存：渠道连通性短时间不会变化，5 分钟内复用结果
_probe_cache: dict = {"at": 0.0, "available": {}}
PROBE_TTL = 300


def resolve_voice(style: str) -> str:
    """按 style 取渠道 voice 名；先归一（兼容历史枚举），白名单外直接拒绝。"""
    voice = TTS_VOICES.get(normalize_style(style) or "")
    if voice is None:
        raise AppError("不支持的声音预设", code="TTS_VOICE_UNKNOWN", status_code=422)
    return voice


def rate_suffix(speech_rate: float) -> str:
    """语速 → edge-tts 增减百分比串（7.x 要求恒为字符串，标准语速用 "+0%"）。"""
    return f"{round((speech_rate - 1) * 100):+d}%"


async def synthesize(text: str, style: str, speech_rate: float = 1.0) -> bytes:
    """合成文本为 MP3 字节流；文本为空或超长抛业务错误。"""
    text = (text or "").strip()
    if not text:
        raise AppError("合成内容不能为空", code="TTS_TEXT_EMPTY", status_code=422)
    if len(text) > TEXT_MAX:
        raise AppError(f"合成内容不能超过 {TEXT_MAX} 字", code="TTS_TEXT_TOO_LONG", status_code=422)

    voice = resolve_voice(style)
    chunks: list[bytes] = []
    try:
        # 构造也纳入保护：参数问题在构造期即抛出，避免穿透为 500
        communicate = edge_tts.Communicate(text, voice, rate=rate_suffix(speech_rate))
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":  # 只收集音频块，忽略 WordBoundary 等元数据
                chunks.append(chunk["data"])
    except Exception as exc:
        logger.warning("TTS 合成失败（voice=%s）：%r", voice, exc)
        raise AppError("语音合成失败，请稍后重试", code="TTS_SYNTHESIZE_FAILED", status_code=502) from exc

    audio = b"".join(chunks)
    if not audio:
        raise AppError("语音合成失败，请稍后重试", code="TTS_SYNTHESIZE_FAILED", status_code=502)
    return audio


async def probe_voices() -> dict[str, bool]:
    """探测各声音是否可用（渠道声音清单能匹配到即视为可用）；结果缓存 5 分钟。"""
    now = time.monotonic()
    if now - _probe_cache["at"] < PROBE_TTL:
        return _probe_cache["available"]
    available: dict[str, bool] = {style: False for style in TTS_VOICES}
    try:
        remote = await edge_tts.list_voices()  # 拉取渠道全部声音（网络调用）
        names = {v["ShortName"] for v in remote}
        for style, voice in TTS_VOICES.items():
            available[style] = voice in names
    except Exception as exc:
        logger.warning("TTS 声音探测失败，全部按不可用处理：%r", exc)
    _probe_cache.update(at=now, available=available)
    return available

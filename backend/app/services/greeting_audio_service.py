"""开场音频磁盘缓存：相同文本、声音与语速跨会话复用。"""
import asyncio
import hashlib
import json
import os
from importlib.metadata import version
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.core.config import BACKEND_DIR
from app.core.errors import AppError
from app.services import tts_service

CACHE_ROOT = Path(os.getenv("ECHOTALK_STORAGE_ROOT", str(BACKEND_DIR / "storage"))) / "tts" / "greetings"
_pending: dict[tuple[asyncio.AbstractEventLoop, str], asyncio.Task] = {}


def audio_key(text: str, voice_style: str, speech_rate: float) -> str:
    """以实际合成参数寻址；场景、音色或语速改变时自然生成新缓存。"""
    params = ["greeting-v1", version("edge-tts"), text.strip(), tts_service.resolve_voice(voice_style), tts_service.rate_suffix(speech_rate)]
    return hashlib.sha256(json.dumps(params, ensure_ascii=False).encode()).hexdigest()


def _write_atomic(path: Path, audio: bytes) -> None:
    """原子替换完整 MP3，避免中断写入留下被误认为缓存的半文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as output:
            temporary = Path(output.name)
            output.write(audio)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


async def get_audio(text: str, voice_style: str, speech_rate: float) -> Path:
    """返回持久化音频路径；命中不调用 TTS，同进程首次并发请求合并。"""
    if not text.strip():
        raise AppError("该会话没有问候语", code="GREETING_EMPTY", status_code=404)
    key = audio_key(text, voice_style, speech_rate)
    path = CACHE_ROOT / f"{key}.mp3"
    if path.is_file() and path.stat().st_size > 0:
        return path

    async def generate() -> Path:
        audio = await tts_service.synthesize(text, voice_style, speech_rate)
        await asyncio.to_thread(_write_atomic, path, audio)
        return path

    pending_key = (asyncio.get_running_loop(), key)
    task = _pending.get(pending_key)
    if task is None:
        task = asyncio.create_task(generate())
        _pending[pending_key] = task

        def forget(completed):
            if _pending.get(pending_key) is completed:
                del _pending[pending_key]
            # 请求取消后任务仍可能失败；主动取出异常以免出现未处理任务告警。
            if not completed.cancelled():
                completed.exception()

        task.add_done_callback(forget)
    return await asyncio.shield(task)

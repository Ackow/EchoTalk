"""按用户、会话及轮次缓存生成的练习回复音频。"""
import asyncio
import hashlib
import json
import os
from importlib.metadata import version
from pathlib import Path

from app.core.config import BACKEND_DIR
from app.services import greeting_audio_service, tts_service

CACHE_ROOT = Path(os.getenv("ECHOTALK_STORAGE_ROOT", str(BACKEND_DIR / "storage"))) / "tts" / "practice"
_pending: dict[tuple[asyncio.AbstractEventLoop, str], asyncio.Task] = {}


async def get_audio(user_id: int, session_id: str, turn_id: str, text: str, voice_style: str, speech_rate: float) -> Path:
    params = ["practice-v1", user_id, session_id, turn_id, version("edge-tts"), text.strip(), tts_service.resolve_voice(voice_style), tts_service.rate_suffix(speech_rate)]
    key = hashlib.sha256(json.dumps(params, ensure_ascii=False).encode()).hexdigest()
    path = CACHE_ROOT / f"{key}.mp3"
    if path.is_file() and path.stat().st_size:
        return path

    async def generate():
        audio = await tts_service.synthesize(text, voice_style, speech_rate)
        await asyncio.to_thread(greeting_audio_service._write_atomic, path, audio)
        return path

    pending_key = (asyncio.get_running_loop(), key)
    task = _pending.get(pending_key)
    if task is None:
        task = asyncio.create_task(generate())
        _pending[pending_key] = task

        def forget(completed):
            if _pending.get(pending_key) is completed:
                del _pending[pending_key]
            if not completed.cancelled():
                completed.exception()

        task.add_done_callback(forget)
    return await asyncio.shield(task)

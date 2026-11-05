"""开场音频跨会话复用、参数失效和首次并发合并回归。"""
import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ.setdefault("ECHOTALK_DB_PASSWORD", "offline-test-only")

from app.core.errors import AppError
from app.services import greeting_audio_service as cache


class GreetingAudioTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.settings = patch.object(cache, "CACHE_ROOT", Path(self.directory.name))
        self.settings.start()

    async def asyncTearDown(self):
        self.settings.stop()
        self.directory.cleanup()

    async def test_reuses_persistent_audio_without_synthesis(self):
        synthesize = AsyncMock(return_value=b"cached-mp3")
        with patch.object(cache.tts_service, "synthesize", synthesize):
            first = await cache.get_audio("Hello", "emma", 1)
            second = await cache.get_audio("Hello", "emma", 1)
        self.assertEqual(first, second)
        self.assertEqual(second.read_bytes(), b"cached-mp3")
        synthesize.assert_awaited_once()
        # 没有进程内任务时，磁盘缓存仍能独立命中。
        with patch.object(cache.tts_service, "synthesize", AsyncMock(side_effect=AssertionError("must not synthesize"))):
            self.assertEqual(await cache.get_audio("Hello", "emma", 1), first)

    async def test_changed_text_voice_or_rate_has_separate_file(self):
        with patch.object(cache.tts_service, "synthesize", AsyncMock(return_value=b"mp3")) as synthesize:
            paths = [await cache.get_audio(*args) for args in [
                ("Hello", "emma", 1), ("Welcome", "emma", 1),
                ("Hello", "sonia", 1), ("Hello", "emma", .9),
            ]]
        self.assertEqual(len(set(paths)), 4)
        self.assertEqual(synthesize.await_count, 4)

    async def test_alias_and_whitespace_reuse_same_audio(self):
        with patch.object(cache.tts_service, "synthesize", AsyncMock(return_value=b"mp3")) as synthesize:
            first = await cache.get_audio(" Hello ", "emma", 1)
            second = await cache.get_audio("Hello", "us_female", 1)
        self.assertEqual(first, second)
        self.assertEqual(synthesize.await_count, 1)

    async def test_first_concurrent_requests_share_generation(self):
        with patch.object(cache.tts_service, "synthesize", AsyncMock(return_value=b"mp3")) as synthesize:
            paths = await asyncio.gather(*(cache.get_audio("Hello", "emma", 1) for _ in range(8)))
        self.assertEqual(len(set(paths)), 1)
        self.assertEqual(synthesize.await_count, 1)

    async def test_failure_does_not_poison_cache(self):
        with patch.object(cache.tts_service, "synthesize", AsyncMock(side_effect=AppError("offline"))):
            with self.assertRaises(AppError):
                await cache.get_audio("Hello", "emma", 1)
        self.assertEqual(list(Path(self.directory.name).glob("*.mp3")), [])
        with patch.object(cache.tts_service, "synthesize", AsyncMock(return_value=b"retry")):
            self.assertEqual((await cache.get_audio("Hello", "emma", 1)).read_bytes(), b"retry")


if __name__ == "__main__":
    unittest.main()

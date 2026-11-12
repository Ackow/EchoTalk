"""练习回复音频持久化与并发合成测试。"""
import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ.setdefault("ECHOTALK_DB_PASSWORD", "offline-test-only")
from app.services import practice_audio_service as cache


class PracticeAudioTests(unittest.IsolatedAsyncioTestCase):
    async def test_persistent_cache_and_owner_isolation(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(cache, "CACHE_ROOT", Path(directory)):
            with patch.object(cache.tts_service, "synthesize", AsyncMock(return_value=b"audio")) as synth:
                paths = await asyncio.gather(*(cache.get_audio(1, "session", "turn", "Hello", "emma", 1) for _ in range(4)))
                self.assertEqual(len(set(paths)), 1)
                synth.assert_awaited_once()
                other = await cache.get_audio(2, "session", "turn", "Hello", "emma", 1)
                self.assertNotEqual(paths[0], other)
                self.assertEqual(synth.await_count, 2)
            with patch.object(cache.tts_service, "synthesize", AsyncMock(side_effect=AssertionError("cache miss"))):
                self.assertEqual((await cache.get_audio(1, "session", "turn", "Hello", "emma", 1)).read_bytes(), b"audio")


if __name__ == "__main__":
    unittest.main()

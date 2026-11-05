"""语音合成的输出、上游拒绝与超时错误回归，不依赖外网。"""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("ECHOTALK_DB_PASSWORD", "offline-test-only")

from app.core.errors import AppError
from app.services import tts_service


class FakeCommunicate:
    async def stream(self):
        yield {"type": "WordBoundary", "text": "Hello"}
        yield {"type": "audio", "data": b"audio-1"}
        yield {"type": "audio", "data": b"audio-2"}


class TtsTests(unittest.IsolatedAsyncioTestCase):
    async def test_audio_and_voice_parameters(self):
        with patch.object(tts_service.edge_tts, "Communicate", return_value=FakeCommunicate()) as factory:
            audio = await tts_service.synthesize("Hello", "emma", .9)
        self.assertEqual(audio, b"audio-1audio-2")
        factory.assert_called_once_with("Hello", "en-US-EmmaNeural", rate="-10%", connect_timeout=8, receive_timeout=15)

    async def test_upstream_rejection_has_specific_error(self):
        class Forbidden(Exception):
            status = 403
        with patch.object(tts_service.edge_tts, "Communicate", side_effect=Forbidden("provider-url-token")):
            with self.assertRaises(AppError) as caught:
                await tts_service.synthesize("Hello", "emma")
        self.assertEqual(caught.exception.code, "TTS_PROVIDER_REJECTED")
        self.assertNotIn("provider-url-token", caught.exception.message)

    async def test_timeout_has_specific_error(self):
        with patch.object(tts_service.edge_tts, "Communicate", side_effect=TimeoutError()):
            with self.assertRaises(AppError) as caught:
                await tts_service.synthesize("Hello", "emma")
        self.assertEqual(caught.exception.status_code, 504)

    async def test_no_audio_is_not_silent_success(self):
        class Empty:
            async def stream(self):
                yield {"type": "WordBoundary", "text": "Hello"}
        with patch.object(tts_service.edge_tts, "Communicate", return_value=Empty()):
            with self.assertRaises(AppError) as caught:
                await tts_service.synthesize("Hello", "emma")
        self.assertEqual(caught.exception.code, "TTS_SYNTHESIZE_FAILED")


if __name__ == "__main__":
    unittest.main()

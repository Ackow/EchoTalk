"""离线校验 WAV 边界、识别失败与 API 鉴权，不调用真实计费服务。"""
import io
import os
import unittest
import wave
from unittest.mock import patch

os.environ.setdefault("ECHOTALK_DB_PASSWORD", "offline-test-only")

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.endpoints.speech import router
from app.core import config
from app.core.errors import AppError, register_exception_handlers
from app.services import asr_service


def audio(seconds=1, rate=16000, channels=1, width=2):
    """创建具有准确长度的 PCM WAV 测试录音。"""
    stream = io.BytesIO()
    with wave.open(stream, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(width)
        wav.setframerate(rate)
        wav.writeframes(b"\0" * int(rate * seconds) * channels * width)
    return stream.getvalue()


class AudioValidationTests(unittest.TestCase):
    def test_valid_wav_and_duration_limit(self):
        self.assertEqual(asr_service.validate_audio(audio()), 1)
        self.assertEqual(asr_service.validate_audio(audio(60)), 60)

    def test_reject_invalid_formats_and_truncated_audio(self):
        for data in [b"webm", audio(rate=48000), audio(channels=2), audio(width=1), audio(.1), audio(61), audio()[:-30]]:
            with self.subTest(length=len(data)):
                with self.assertRaises(AppError) as caught:
                    asr_service.validate_audio(data)
                self.assertEqual(caught.exception.status_code, 422)

    def test_size_limit(self):
        for data in [b"", b"x" * (asr_service.MAX_BYTES + 1)]:
            with self.assertRaises(AppError) as caught:
                asr_service.validate_audio(data)
            self.assertEqual(caught.exception.code, "ASR_AUDIO_SIZE")


class TranscriptionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.settings = patch.multiple(config, ASR_APP_ID="12345", ASR_SECRET_ID="offline-id", ASR_SECRET_KEY="offline-key")
        self.settings.start()
        self.addCleanup(self.settings.stop)

    async def invoke(self, handler):
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            with patch.object(asr_service.httpx, "AsyncClient", return_value=client):
                return await asr_service.transcribe(audio())
        finally:
            await client.aclose()

    async def test_success_and_signed_request(self):
        def handler(request):
            self.assertEqual(request.url.path, "/asr/flash/v1/12345")
            self.assertEqual(request.url.params["engine_type"], "16k_en")
            self.assertEqual(request.url.params["voice_format"], "wav")
            self.assertEqual(request.headers["Content-Type"], "application/octet-stream")
            self.assertTrue(request.headers["Authorization"])
            self.assertEqual(request.content, audio())
            return httpx.Response(200, json={"code": 0, "flash_result": [{"text": "Hello."}, {"text": "I would like a coffee."}]})
        result = await self.invoke(handler)
        self.assertEqual(result["text"], "Hello. I would like a coffee.")
        self.assertEqual(result["duration"], 1)

    async def test_missing_configuration(self):
        with patch.object(config, "ASR_SECRET_KEY", ""):
            with self.assertRaises(AppError) as caught:
                await asr_service.transcribe(audio())
            self.assertEqual(caught.exception.code, "ASR_NOT_CONFIGURED")

    async def test_no_speech(self):
        with self.assertRaises(AppError) as caught:
            await self.invoke(lambda r: httpx.Response(200, json={"code": 0, "flash_result": []}))
        self.assertEqual(caught.exception.code, "ASR_NO_SPEECH")

    async def test_provider_failure_does_not_return_fake_text(self):
        for response in [httpx.Response(200, json={"code": 4001, "message": "credential-detail"}), httpx.Response(500), httpx.Response(200, text="invalid")]:
            with self.subTest(status=response.status_code):
                with self.assertRaises(AppError) as caught:
                    await self.invoke(lambda r: response)
                self.assertEqual(caught.exception.code, "ASR_PROVIDER_FAILED")
                self.assertNotIn("credential-detail", caught.exception.message)

    async def test_timeout(self):
        def handler(request):
            raise httpx.ReadTimeout("offline timeout")
        with self.assertRaises(AppError) as caught:
            await self.invoke(handler)
        self.assertEqual(caught.exception.status_code, 502)


class SpeechApiTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        register_exception_handlers(self.app)
        self.app.include_router(router, prefix="/api")

    def test_upload_requires_login_and_status_hides_keys(self):
        with TestClient(self.app) as client:
            response = client.get("/api/speech/status")
            self.assertEqual(set(response.json()), {"configured", "max_duration", "sample_rate"})
            response = client.post("/api/speech/transcriptions", files={"file": ("recording.wav", audio(), "audio/wav")})
            self.assertEqual(response.status_code, 401)

    def test_upload_checks_actual_content(self):
        self.app.dependency_overrides[get_current_user] = lambda: object()
        with TestClient(self.app) as client:
            response = client.post("/api/speech/transcriptions", files={"file": ("recording.wav", b"not-wav", "audio/wav")})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "ASR_INVALID_AUDIO")


if __name__ == "__main__":
    unittest.main()

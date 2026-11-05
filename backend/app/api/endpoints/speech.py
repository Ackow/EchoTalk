"""录音识别控制器：提供能力状态与登录后的 WAV 上传入口。"""
from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.speech import SpeechStatus, TranscriptionResponse
from app.services import asr_service

router = APIRouter(prefix="/speech", tags=["语音识别"])


@router.get("/status", response_model=SpeechStatus)
def status():
    """返回录音限制和服务可用配置，供前端选择合适的输入方式。"""
    return {"configured": asr_service.configured(), "max_duration": asr_service.MAX_DURATION, "sample_rate": asr_service.SAMPLE_RATE}


@router.post("/transcriptions", response_model=TranscriptionResponse)
async def transcribe(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    """限制读取大小后交由服务验证真实文件内容，不信任扩展名和 MIME。"""
    try:
        audio = await file.read(asr_service.MAX_BYTES + 1)
    finally:
        await file.close()
    return await asr_service.transcribe(audio)

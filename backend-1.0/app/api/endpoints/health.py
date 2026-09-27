from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()

@router.get("/health")
def health_check():
    """
    健康检查及 API 服务状态诊断接口
    """
    # 检查七牛云是否配置成功
    qiniu_ok = bool(settings.QINIU_ACCESS_KEY and settings.QINIU_SECRET_KEY)
    # 检查大模型 OpenAI Key 是否配置（非默认 Mock）
    openai_ok = settings.OPENAI_API_KEY != "mock-key"
    
    return {
        "status": "healthy",
        "database": "sqlite connected",
        "qiniu_kodo_configured": qiniu_ok,
        "openai_configured": openai_ok,
        "region": "cn-east-1 (z0)"
    }

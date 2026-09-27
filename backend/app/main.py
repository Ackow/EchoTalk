"""EchoTalk 2.0 账户服务入口。

应用装配：中间件、CORS、全局异常处理、健康/就绪探针与路由注册。
"""
import logging
import time
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app import models  # noqa: F401 导入即注册 SQLAlchemy 表定义
from app.api.endpoints.auth import router as auth_router
from app.core.config import CORS_ORIGINS
from app.core.database import engine
from app.core.errors import register_exception_handlers

logger = logging.getLogger("echotalk")

app = FastAPI(title="EchoTalk 2.0 API", version="2.0.0")
register_exception_handlers(app)  # 全局异常处理器：规范化错误响应


@app.middleware("http")
async def request_context(request, call_next):
    """为每个请求分配追踪 ID 并记录结构化访问日志。"""
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info(
        '{"request_id":"%s","method":"%s","path":"%s","status":%d,"elapsed_ms":%.1f}',
        request_id, request.method, request.url.path, response.status_code, elapsed_ms,
    )
    response.headers["X-Request-ID"] = request_id  # 响应头回传，便于问题排查
    return response


# 桌面端 file:// 来源需要将 null 加入配置；正式部署只允许实际客户端来源。
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
app.include_router(auth_router, prefix="/api")  # 账户路由统一挂 /api 前缀


@app.get("/api/health", tags=["服务"])
def health():
    """存活探针：进程正常即返回 ok，不检查外部依赖。"""
    return {"status": "ok"}


@app.get("/api/ready", tags=["服务"])
def ready():
    """就绪探针：验证数据库连接可用；失败返回 503，供部署编排判断。"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        logger.exception("就绪检查失败：数据库不可用")
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "error": {"code": "db_unavailable", "message": "数据库暂不可用"}},
        )

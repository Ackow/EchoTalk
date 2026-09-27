"""统一业务错误体系与响应结构。

业务代码只抛出 AppError 子类；全局异常处理器将其转换为
``{"error": {"code": ..., "message": ...}}`` 的规范化 JSON，
客户端永远不会看到堆栈或内部细节。
"""
from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """业务错误基类：所有可预期错误都应使用它的子类。"""

    status_code = 400  # 默认 HTTP 状态码
    code = "bad_request"  # 机器可读的错误码，供前端程序化判断

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: list | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.details = details  # 可选字段级详情（如场景包校验错误列表）
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code

    def to_response(self) -> JSONResponse:
        """转换为规范化错误响应体。"""
        error: dict = {"code": self.code, "message": self.message}
        if self.details:
            error["details"] = self.details  # 字段级详情：供表单逐项标注
        return JSONResponse(status_code=self.status_code, content={"error": error})


class ConflictError(AppError):
    """资源冲突：如用户名已被注册（HTTP 409）。"""

    status_code = 409
    code = "conflict"


class AuthError(AppError):
    """身份验证失败：凭据错误或会话失效（HTTP 401）。"""

    status_code = 401
    code = "unauthorized"


def register_exception_handlers(app) -> None:
    """在 FastAPI 应用上注册全局异常处理器。"""

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return exc.to_response()  # 可预期业务错误：返回规范化结构

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        # 未预期异常：记录服务端日志，但对外只暴露统一提示，绝不返回堆栈。
        import logging

        logging.getLogger("echotalk").exception("未处理异常：%s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "服务内部错误，请稍后重试"}},
        )

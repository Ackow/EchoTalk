"""场景模块专用错误（设计稿场景包方案 附录 B 错误码约定）。"""
from app.core.errors import AppError


class SceneNotFoundError(AppError):
    """场景 ID 不存在（404）。"""

    status_code = 404
    code = "SCENE_NOT_FOUND"

    def __init__(self, scene_id: str):
        super().__init__(f"场景 '{scene_id}' 不存在")


class SceneIdConflictError(AppError):
    """创建/导入时场景 ID 冲突（409）；导入可用 resolve=overwrite|rename 解决。"""

    status_code = 409
    code = "SCENE_ID_CONFLICT"

    def __init__(self, scene_id: str, source: str):
        hint = "内置场景 ID 不可覆盖，请改名导入" if source == "builtin" else "可选择覆盖现有场景或改名导入"
        super().__init__(f"场景 ID '{scene_id}' 已存在（{hint}）")


class SceneBuiltinReadonlyError(AppError):
    """内置场景只读：不可编辑/删除（409）。"""

    status_code = 409
    code = "SCENE_BUILTIN_READONLY"

    def __init__(self, scene_id: str):
        super().__init__(f"内置场景 '{scene_id}' 只读，可复制为自定义场景后修改")


class SceneInvalidPackageError(AppError):
    """场景包校验失败（422）：details 为字段级错误列表。"""

    status_code = 422
    code = "SCENE_INVALID_PACKAGE"

    def __init__(self, message: str, details: list[dict] | None = None):
        super().__init__(message, details=details or [])


class SceneInvalidExpressionError(AppError):
    """表达式解析失败（422）：含位置信息。"""

    status_code = 422
    code = "SCENE_INVALID_EXPRESSION"


class SceneUnsupportedFileError(AppError):
    """资料类型不支持（400）。"""

    status_code = 400
    code = "SCENE_UNSUPPORTED_FILE"


class ScenePackageIncompatibleError(AppError):
    """包的 min_app 高于当前应用版本（422）。"""

    status_code = 422
    code = "SCENE_PACKAGE_INCOMPATIBLE"

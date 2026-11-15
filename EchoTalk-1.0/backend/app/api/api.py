from fastapi import APIRouter
from app.api.endpoints import health, scenes, dialogues, users, settings

# 创建顶级路由聚合器
api_router = APIRouter()

# 挂载各业务子模块路由
api_router.include_router(health.router, tags=["健康状况"])
api_router.include_router(scenes.router, prefix="/scenes", tags=["练习场景"])
api_router.include_router(dialogues.router, prefix="/dialogues", tags=["口语会话"])
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])
api_router.include_router(settings.router, prefix="/settings", tags=["系统设置"])

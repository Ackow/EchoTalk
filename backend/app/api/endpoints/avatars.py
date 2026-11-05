"""数字人偏好接口（控制器层）：GET / PUT / DELETE /api/preferences/avatar。

偏好按「用户 × 场景档」存储：scene_id 查询/载荷参数定位档位，
空值表示「跟随场景推荐」档；未保存过时返回全 null 字段而非 404。
"""
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.avatar import AvatarPreferenceResponse, AvatarPreferenceUpdate
from app.services import avatar_service

router = APIRouter(prefix="/preferences/avatar", tags=["数字人"])


def _to_response(pref) -> AvatarPreferenceResponse:
    """模型行 → 响应体；库内空串场景键归一为 null（跟随推荐的对外语义）。"""
    return AvatarPreferenceResponse(
        avatar_id=pref.avatar_id,
        role_id=pref.role_id,
        voice_style=avatar_service.normalized_voice(pref.voice_style),  # 存量历史枚举归一后返回
        scene_id=pref.scene_id or None,
        speech_rate=pref.speech_rate,
        lip_sync_enabled=bool(pref.lip_sync_enabled),
        updated_at=pref.updated_at,
    )


@router.get("", response_model=AvatarPreferenceResponse)
def read_preference(
    scene_id: str | None = Query(default=None, description="场景 id；空为「跟随场景推荐」档"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """读取当前场景档的偏好；未保存过时返回全 null 字段（前端按跟随缺省处理）。"""
    pref = avatar_service.get_preference(db, user, scene_id)
    if pref is None:
        return AvatarPreferenceResponse()  # 全 null：该场景档从未自定义
    return _to_response(pref)


@router.put("", response_model=AvatarPreferenceResponse)
def save_preference(
    payload: AvatarPreferenceUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """整体覆盖保存当前场景档的偏好（形象 × 音色 × 节奏的任意组合）。"""
    pref = avatar_service.save_preference(db, user, payload)
    return _to_response(pref)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def reset_preference(
    scene_id: str | None = Query(default=None, description="场景 id；空为「跟随场景推荐」档"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """重置当前场景档的偏好：删除该行，回到跟随缺省。"""
    avatar_service.reset_preference(db, user, scene_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

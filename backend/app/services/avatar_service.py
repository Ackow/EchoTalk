"""数字人偏好业务逻辑：读取 / 保存 / 重置每用户的形象与声音组合。"""
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import AvatarPreference, Scene, User
from app.schemas.avatar import AvatarPreferenceUpdate
from app.services.tts_service import normalize_style

SPEECH_RATE_MIN = 0.75  # 语速下限：与前端滑杆范围一致
SPEECH_RATE_MAX = 1.25  # 语速上限


class SceneNotAllowedError(AppError):
    """偏好里绑定的默认场景不存在或当前用户不可见（400）。"""

    status_code = 400
    code = "AVATAR_SCENE_NOT_ALLOWED"


class VoiceStyleInvalidError(AppError):
    """声音预设不在白名单内（422）。"""

    status_code = 422
    code = "AVATAR_VOICE_UNKNOWN"


def normalized_voice(style: str | None) -> str | None:
    """偏好中的 voice_style 归一：兼容历史枚举；空值与脏数据一律归 None。"""
    if not style:
        return None
    return normalize_style(style)


def scene_key(scene_id: str | None) -> str:
    """场景键归一：空值归空串（「跟随场景推荐」档），其余原样作为存储键。"""
    return (scene_id or "").strip()


def get_preference(db: Session, user: User, scene_id: str | None = None) -> AvatarPreference | None:
    """读取某场景档的偏好；从未保存过时返回 None（控制器转成全 null 响应）。"""
    return db.get(AvatarPreference, (user.id, scene_key(scene_id)))


def save_preference(db: Session, user: User, payload: AvatarPreferenceUpdate) -> AvatarPreference:
    """保存（upsert）当前场景档的偏好；绑定的场景需存在且当前用户可见。"""
    if payload.scene_id is not None:
        scene = db.get(Scene, payload.scene_id)
        # 场景必须存在；非内置场景仅作者本人可选（与场景列表可见性规则一致）
        if scene is None or (scene.source != "builtin" and scene.author_id != user.id):
            raise SceneNotAllowedError("默认场景不存在或无权使用，请重新选择")

    key = scene_key(payload.scene_id)
    pref = db.get(AvatarPreference, (user.id, key))
    if pref is None:
        pref = AvatarPreference(user_id=user.id, scene_id=key)
        db.add(pref)
    # voice_style 入库前归一为声音名枚举；显式传入但不在白名单时拒绝，避免存进无法合成的值
    if payload.voice_style is not None and normalized_voice(payload.voice_style) is None:
        raise VoiceStyleInvalidError("不支持的声音预设")
    pref.avatar_id = payload.avatar_id
    pref.role_id = payload.role_id
    pref.voice_style = normalized_voice(payload.voice_style)
    pref.scene_id = key  # 主键列 NOT NULL：空键即空串（「跟随场景推荐」档）
    pref.speech_rate = min(SPEECH_RATE_MAX, max(SPEECH_RATE_MIN, payload.speech_rate))
    pref.lip_sync_enabled = 1 if payload.lip_sync_enabled else 0
    db.commit()
    db.refresh(pref)
    return pref


def reset_preference(db: Session, user: User, scene_id: str | None = None) -> None:
    """重置某场景档的偏好：删除该行，回到跟随缺省/场景推荐。"""
    pref = db.get(AvatarPreference, (user.id, scene_key(scene_id)))
    if pref is not None:
        db.delete(pref)
        db.commit()

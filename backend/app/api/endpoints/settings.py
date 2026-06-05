import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import DialogueHistory, DialogueTurn
from app.core.config import settings

router = APIRouter()

# 获取本地静态音频缓存路径
STATIC_AUDIO_DIR = settings.static_audio_dir

@router.get("/cache-info")
def get_cache_info():
    """
    扫描本地静态音频缓存，返回文件个数和累积占用的存储字节大小
    """
    if not os.path.exists(STATIC_AUDIO_DIR):
        return {"file_count": 0, "total_size_bytes": 0}
        
    file_count = 0
    total_size_bytes = 0
    
    try:
        for filename in os.listdir(STATIC_AUDIO_DIR):
            file_path = os.path.join(STATIC_AUDIO_DIR, filename)
            # 仅统计音频文件且不计入打招呼的声音种子文件
            if os.path.isfile(file_path) and (filename.endswith(".wav") or filename.endswith(".mp3")):
                if not filename.startswith("scene_greeting_"):
                    file_count += 1
                    total_size_bytes += os.path.getsize(file_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"读取音频缓存失败: {str(e)}"
        )
        
    return {
        "file_count": file_count,
        "total_size_bytes": total_size_bytes
    }

@router.post("/clear-cache")
def clear_audio_cache():
    """
    清除本地所有缓存的用户和AI练习音频，保留系统自带的场景打招呼引导音轨
    """
    if not os.path.exists(STATIC_AUDIO_DIR):
        return {"message": "缓存目录不存在，无需清理", "cleared_count": 0}
        
    cleared_count = 0
    freed_bytes = 0
    
    try:
        for filename in os.listdir(STATIC_AUDIO_DIR):
            file_path = os.path.join(STATIC_AUDIO_DIR, filename)
            if os.path.isfile(file_path) and (filename.endswith(".wav") or filename.endswith(".mp3")):
                # 系统内置场景引导音轨不予删除，保护开场白正常播放
                if not filename.startswith("scene_greeting_"):
                    size = os.path.getsize(file_path)
                    os.remove(file_path)
                    cleared_count += 1
                    freed_bytes += size
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清理音频缓存发生异常: {str(e)}"
        )
        
    return {
        "message": "音频缓存清理成功",
        "cleared_count": cleared_count,
        "freed_bytes": freed_bytes
    }

@router.post("/clear-db")
def clear_practice_history(db: Session = Depends(get_db)):
    """
    彻底清空数据库中的所有历史对话轮次和会话记录（危险操作）
    """
    try:
        # 级联删除，由于外键关联规则，清理 history 会级联删干净 turns
        deleted_history = db.query(DialogueHistory).delete()
        deleted_turns = db.query(DialogueTurn).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清空练习历史记录失败: {str(e)}"
        )
        
    return {
        "message": "练习历史数据库已成功置空",
        "deleted_histories": deleted_history,
        "deleted_turns": deleted_turns
    }

@router.get("/config-status")
def get_config_status():
    """
    获取后台主要 API 服务的秘钥配置状态，用于在前端设置页面进行展示
    """
    return {
        "deepseek_configured": bool(settings.DEEPSEEK_API_KEY),
        "openai_configured": bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "mock-key"),
        "xiaomi_configured": bool(settings.XIAOMI_API_KEY),
        "xunfei_configured": bool(settings.XFYUN_APP_ID and settings.XFYUN_APP_ID != "mock-appid"),
        "qiniu_configured": bool(settings.QINIU_ACCESS_KEY and settings.QINIU_SECRET_KEY)
    }


CONFIG_FIELDS = [
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_MODEL",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "XIAOMI_API_KEY",
    "XIAOMI_BASE_URL",
    "XIAOMI_MODEL",
    "XFYUN_APP_ID",
    "XFYUN_API_KEY",
    "XFYUN_API_SECRET",
    "BAIDU_API_KEY",
    "BAIDU_SECRET_KEY",
    "QINIU_ACCESS_KEY",
    "QINIU_SECRET_KEY",
    "QINIU_BUCKET_NAME",
    "QINIU_DOMAIN"
]

SENSITIVE_FIELDS = {
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
    "XIAOMI_API_KEY",
    "XFYUN_API_KEY",
    "XFYUN_API_SECRET",
    "BAIDU_API_KEY",
    "BAIDU_SECRET_KEY",
    "QINIU_ACCESS_KEY",
    "QINIU_SECRET_KEY"
}


@router.get("/config")
def get_config():
    """
    获取当前的所有配置参数（敏感 Key 进行脱敏掩码处理）
    """
    result = {}
    for field in CONFIG_FIELDS:
        val = getattr(settings, field, "")
        if field in SENSITIVE_FIELDS:
            # 如果配置了有效值且非占位的 mock-key，则返回掩码
            if val and val != "mock-key":
                result[field] = "●●●●●●●●"
            else:
                result[field] = ""
        else:
            result[field] = val or ""
    return result


@router.post("/config")
def update_config(new_config: dict):
    """
    保存配置到 settings.json，并实时更新内存中的 settings 实例
    """
    import json
    json_path = settings.settings_json_path
    
    # 尝试加载当前已保存的 settings.json
    current_json_data = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                current_json_data = json.load(f)
        except Exception:
            pass
            
    updated_data = {}
    for field in CONFIG_FIELDS:
        if field in new_config:
            val = new_config[field]
            if field in SENSITIVE_FIELDS:
                # 如果是掩码占位符，说明用户没有修改它，我们保持原来的值（优先取 settings.json 中的值，其次取内存值）
                if val == "●●●●●●●●":
                    if field in current_json_data and current_json_data[field] is not None:
                        updated_data[field] = current_json_data[field]
                    else:
                        orig_val = getattr(settings, field)
                        updated_data[field] = orig_val if orig_val != "mock-key" else None
                elif val == "":
                    updated_data[field] = None
                else:
                    updated_data[field] = val
            else:
                updated_data[field] = val if val != "" else None
        else:
            # 如果前端传参没有包含该字段，保持原值
            if field in current_json_data:
                updated_data[field] = current_json_data[field]
            else:
                updated_data[field] = getattr(settings, field)

    # 写入 JSON 文件
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(updated_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存配置文件 settings.json 失败: {str(e)}"
        )
        
    # 实时更新内存中的 settings 属性
    for key, val in updated_data.items():
        if hasattr(settings, key):
            setattr(settings, key, val)
            
    return {"message": "配置保存成功，并且已实时应用到系统后端！"}


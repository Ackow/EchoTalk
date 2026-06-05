import os
import shutil
from typing import Optional
from qiniu import Auth, put_file
import qiniu.config
from app.core.config import settings

# 设置本地静态存储文件夹路径
STATIC_AUDIO_DIR = settings.static_audio_dir

def upload_audio_to_kodo(local_file_path: str, filename: str) -> str:
    """
    将本地录制的音频文件上传至七牛云 Kodo 存储桶。
    如果未配置七牛云密钥，则会自动回退为本地静态文件夹存储，并返回 Localhost 的静态访问 URL。
    """
    # 检查是否配置了有效的七牛云凭证
    has_credentials = bool(settings.QINIU_ACCESS_KEY and settings.QINIU_SECRET_KEY)
    
    if not has_credentials:
        # 回退逻辑：直接拷贝文件到本地静态路由托管目录
        dest_path = os.path.join(STATIC_AUDIO_DIR, filename)
        if os.path.abspath(local_file_path) != os.path.abspath(dest_path):
            shutil.copy(local_file_path, dest_path)
        print(f"[存储回退] 未配置七牛云凭据，音频文件已保存至本地: {dest_path}")
        return f"/static/audio/{filename}"

    try:
        # 显式配置七牛云为 华东-浙江 区域 (zone_z0)
        qiniu.config.set_default_zone(qiniu.config.zone_z0())
        
        # 构建七牛认证对象
        q = Auth(settings.QINIU_ACCESS_KEY, settings.QINIU_SECRET_KEY)
        
        # 生成上传凭证（Token），有效期为1小时
        token = q.upload_token(settings.QINIU_BUCKET_NAME, filename, 3600)
        
        # 执行上传
        ret, info = put_file(token, filename, local_file_path)
        
        if info.status_code == 200:
            print(f"[七牛云 Kodo] 音频文件上传成功: {filename}")
            domain = settings.QINIU_DOMAIN.rstrip("/")
            if not domain.startswith("http"):
                domain = f"http://{domain}"
            return f"{domain}/{filename}"
        else:
            raise Exception(f"七牛云返回错误代码 {info.status_code}: {info.error}")
            
    except Exception as e:
        print(f"[七牛云上传异常] {e}。程序已自动回退到本地静态存储。")
        dest_path = os.path.join(STATIC_AUDIO_DIR, filename)
        if os.path.abspath(local_file_path) != os.path.abspath(dest_path):
            shutil.copy(local_file_path, dest_path)
        return f"/static/audio/{filename}"

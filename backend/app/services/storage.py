import os
import shutil
from typing import Optional
from qiniu import Auth, Region
from qiniu.services.storage.uploaders import FormUploader
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
        # 构建七牛认证对象
        q = Auth(settings.QINIU_ACCESS_KEY, settings.QINIU_SECRET_KEY)
        
        # 生成上传凭证（Token），有效期为1小时
        token = q.upload_token(settings.QINIU_BUCKET_NAME, filename, 3600)
        
        # 显式指定华东机房上传域名，避开 Windows 下 Qiniu SDK 自动查询区域缓存的 WinError 183 冲突 Bug
        region = Region(up_host='https://up.qiniup.com')
        uploader = FormUploader(settings.QINIU_BUCKET_NAME, regions=[region])
        
        # 执行上传
        ret, info = uploader.upload(filename, local_file_path, up_token=token)
        
        if info.status_code == 200:
            print(f"[七牛云 Kodo] 音频文件上传成功: {filename}")
            domain = settings.QINIU_DOMAIN or ""
            # 如果配置了安全的 HTTPS 自定义域名，可以直接返回外链
            if domain.startswith("https://"):
                domain_clean = domain.rstrip("/")
                return f"{domain_clean}/{filename}"
            else:
                # 否则返回后端的代理接口路由，避开浏览器的混合内容 (Mixed Content) 拦截和 CORS 限制
                return f"/api/dialogues/audio/qiniu/{filename}"
        else:
            raise Exception(f"七牛云返回错误代码 {info.status_code}: {info.error}")
            
    except Exception as e:
        print(f"[七牛云上传异常] {e}。程序已自动回退到本地静态存储。")
        dest_path = os.path.join(STATIC_AUDIO_DIR, filename)
        if os.path.abspath(local_file_path) != os.path.abspath(dest_path):
            shutil.copy(local_file_path, dest_path)
        return f"/static/audio/{filename}"

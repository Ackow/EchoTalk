import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # 七牛云存储配置
    QINIU_ACCESS_KEY: Optional[str] = None
    QINIU_SECRET_KEY: Optional[str] = None
    QINIU_BUCKET_NAME: str = "echotalk-bucket"
    QINIU_DOMAIN: str = "http://mock.qiniu.com"

    # 大语言模型配置
    OPENAI_API_KEY: str = "mock-key"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # 向量嵌入模型配置 (BAAI/bge-large-en-v1.5)
    EMBEDDING_API_KEY: Optional[str] = None
    EMBEDDING_BASE_URL: Optional[str] = None
    EMBEDDING_MODEL: str = None

    # 微软 Azure 语音配置 (用于发音评估)
    AZURE_SPEECH_KEY: str = "mock-key"
    AZURE_SPEECH_REGION: str = "eastus"

    # SQLite 本地数据库配置
    DATABASE_URL: str = "sqlite:///./echotalk.db"

    # 读取 backend 目录下的 .env 配置文件
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # 七牛云存储配置
    QINIU_ACCESS_KEY: Optional[str] = None
    QINIU_SECRET_KEY: Optional[str] = None
    QINIU_BUCKET_NAME: str = "echotalk-bucket"
    QINIU_DOMAIN: str = "http://mock.qiniu.com"

    # 大语言模型配置 (支持 DeepSeek, 小米 MiMo 或 OpenAI)
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    XIAOMI_API_KEY: Optional[str] = None
    XIAOMI_BASE_URL: str = "https://api.ai.mi.com/v1"
    XIAOMI_MODEL: str = "mimo-chat"

    # 原 OpenAI 配置（用作兼容性底座）
    OPENAI_API_KEY: str = "mock-key"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # 向量嵌入模型配置 (BAAI/bge-large-en-v1.5)
    EMBEDDING_API_KEY: Optional[str] = None # 如果不填，默认共用大模型 Key
    EMBEDDING_BASE_URL: Optional[str] = None # 如果不填，默认共用大模型 BaseURL
    EMBEDDING_MODEL: str = "BAAI/bge-large-en-v1.5"

    # 微软 Azure 语音配置 (用于发音评估)
    AZURE_SPEECH_KEY: str = "mock-key"
    AZURE_SPEECH_REGION: str = "eastus"

    # 科大讯飞语音评测配置 (用于发音评估)
    XFYUN_APP_ID: Optional[str] = None
    XFYUN_API_KEY: Optional[str] = None
    XFYUN_API_SECRET: Optional[str] = None

    # 百度智能云语音识别配置 (用于语音转文字 STT)
    BAIDU_API_KEY: Optional[str] = None
    BAIDU_SECRET_KEY: Optional[str] = None

    # SQLite 本地数据库配置
    DATABASE_URL: str = "sqlite:///./echotalk.db"

    # 读取 backend 目录下的 .env 配置文件
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

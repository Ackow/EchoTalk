import os
import sys
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

    # 科大讯飞语音评测配置 (用于发音评估)
    XFYUN_APP_ID: Optional[str] = None
    XFYUN_API_KEY: Optional[str] = None
    XFYUN_API_SECRET: Optional[str] = None

    # 腾讯云语音识别配置 (录音文件识别极速版 Flash ASR，用于语音转文字 STT)
    TENCENT_APPID: Optional[str] = None
    TENCENT_SECRET_ID: Optional[str] = None
    TENCENT_SECRET_KEY: Optional[str] = None
    USE_TENCENT_TTS: bool = False

    # 获取可写的基础运行目录
    @property
    def writeable_base_dir(self) -> str:
        import sys
        if getattr(sys, 'frozen', False):
            # 打包生产环境下，写入用户 AppData 目录，保证可写权限
            appdata = os.environ.get('APPDATA') or os.path.expanduser('~')
            base_dir = os.path.join(appdata, 'EchoTalk')
            os.makedirs(base_dir, exist_ok=True)
            return base_dir
        else:
            return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # SQLite 本地数据库配置
    @property
    def DATABASE_URL(self) -> str:
        return f"sqlite:///{os.path.join(self.writeable_base_dir, 'echotalk.db')}"

    # 读取 backend 目录下的 .env 配置文件
    @property
    def env_file_path(self) -> str:
        import sys
        if getattr(sys, 'frozen', False):
            return os.path.join(os.path.dirname(sys.executable), ".env")
        return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")

    # 获取 settings.json 路径
    @property
    def settings_json_path(self) -> str:
        return os.path.join(self.writeable_base_dir, 'settings.json')

    # 获取静态文件存储路径
    @property
    def static_dir(self) -> str:
        s_dir = os.path.join(self.writeable_base_dir, 'static')
        os.makedirs(s_dir, exist_ok=True)
        os.makedirs(os.path.join(s_dir, 'audio'), exist_ok=True)
        os.makedirs(os.path.join(s_dir, 'rag', 'indices'), exist_ok=True)
        os.makedirs(os.path.join(s_dir, 'rag', 'temp'), exist_ok=True)
        return s_dir

    # 获取音频存储路径
    @property
    def static_audio_dir(self) -> str:
        audio_dir = os.path.join(self.static_dir, 'audio')
        os.makedirs(audio_dir, exist_ok=True)
        return audio_dir

    @property
    def static_rag_dir(self) -> str:
        rag_dir = os.path.join(self.static_dir, 'rag')
        os.makedirs(rag_dir, exist_ok=True)
        return rag_dir

    @property
    def static_rag_indices_dir(self) -> str:
        indices_dir = os.path.join(self.static_rag_dir, 'indices')
        os.makedirs(indices_dir, exist_ok=True)
        return indices_dir

    @property
    def static_rag_temp_dir(self) -> str:
        temp_dir = os.path.join(self.static_rag_dir, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        return temp_dir

    @property
    def static_audio_temp_dir(self) -> str:
        temp_dir = os.path.join(self.static_audio_dir, 'temp_uploads')
        os.makedirs(temp_dir, exist_ok=True)
        return temp_dir

    def __init__(self, **values):
        super().__init__(**values)
        self.load_from_json()

    def load_from_json(self):
        import json
        path = self.settings_json_path
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for key, val in data.items():
                        if hasattr(self, key) and val is not None:
                            setattr(self, key, val)
            except Exception as e:
                print(f"Error loading settings.json: {e}")

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env") if not getattr(sys, 'frozen', False) else os.path.join(os.path.dirname(sys.executable), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )



settings = Settings()

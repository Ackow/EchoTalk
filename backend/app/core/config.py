"""数据库与运行配置：从 backend/.env 读取本地 MySQL 连接信息。

优先级：真实环境变量 > backend/.env > 默认值。
仅支持本地 MySQL：未配置密码（ECHOTALK_DB_PASSWORD 为空）时直接报错终止。
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL

BACKEND_DIR = Path(__file__).resolve().parents[2]  # backend 目录：本文件向上两级

# 无论从哪个工作目录启动，都加载 backend/.env；已存在的环境变量不会被覆盖。
load_dotenv(BACKEND_DIR / ".env", override=False)


# ---- 本地 MySQL 连接配置 ----
DB_HOST = os.getenv("ECHOTALK_DB_HOST", "127.0.0.1").strip()  # MySQL 主机
DB_PORT = int(os.getenv("ECHOTALK_DB_PORT", "3307"))  # MySQL 端口
DB_NAME = os.getenv("ECHOTALK_DB_NAME", "echotalk").strip()  # 库名
DB_USER = os.getenv("ECHOTALK_DB_USER", "echotalk_app").strip()  # 连接账号
DB_PASSWORD = os.getenv("ECHOTALK_DB_PASSWORD", "").strip()  # 连接密码

if not DB_PASSWORD:  # 密码缺失时尽快失败，给出可操作的提示而非连接期的晦涩报错
    raise RuntimeError(
        "未配置数据库密码：请在 backend/.env 中设置 ECHOTALK_DB_PASSWORD（仅支持本地 MySQL）。"
    )

DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,  # URL.create 自动处理特殊字符转义
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    query={"charset": "utf8mb4"},
)

# ---- API 服务配置 ----
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ECHOTALK_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
API_BIND_HOST = os.getenv("ECHOTALK_API_HOST", "127.0.0.1")  # 监听地址
API_BIND_PORT = int(os.getenv("ECHOTALK_API_PORT", "8000"))  # 监听端口

# ---- 嵌入（Hybrid RAG）配置：SiliconFlow OpenAI 兼容接口，BAAI/bge-m3 ----
# 未配置 key 时嵌入链路自动停用，检索退化为纯关键词（ngram 全文）模式。
EMBEDDING_API_KEY = os.getenv("ECHOTALK_SILICONFLOW_API_KEY", "").strip()
EMBEDDING_API_BASE = os.getenv("ECHOTALK_EMBEDDING_API_BASE", "https://api.siliconflow.cn/v1").strip().rstrip("/")
EMBEDDING_MODEL = os.getenv("ECHOTALK_EMBEDDING_MODEL", "BAAI/bge-m3").strip()  # 换模型需全量重建索引（reindex）
EMBEDDING_DIM = int(os.getenv("ECHOTALK_EMBEDDING_DIM", "1024"))  # bge-m3 输出维度
EMBEDDING_TIMEOUT = float(os.getenv("ECHOTALK_EMBEDDING_TIMEOUT", "15"))  # 单次请求超时（秒）
EMBEDDING_BATCH_SIZE = int(os.getenv("ECHOTALK_EMBEDDING_BATCH", "16"))  # 单请求文本条数上限

# ---- LightRAG（图谱 RAG）配置：实体抽取 LLM 独立配置（base_url + key + 模型名），与嵌入分开 ----
# 未配置 LLM key 或 ECHOTALK_LIGHTRAG_ENABLED=false 时整条链路停用
# （维护操作静默跳过，查询接口 400）。嵌入仍走上面的 SiliconFlow bge-m3。
# 抽取 LLM 官方建议 ≥32B 且非推理模型；默认 DeepSeek-V3（中文实体抽取强、性价比高）。
LIGHTRAG_ENABLED = os.getenv("ECHOTALK_LIGHTRAG_ENABLED", "true").strip().lower() not in ("0", "false", "no", "off")
LIGHTRAG_LLM_API_BASE = os.getenv("ECHOTALK_LIGHTRAG_LLM_API_BASE", "https://api.siliconflow.cn/v1").strip().rstrip("/")
LIGHTRAG_LLM_API_KEY = os.getenv("ECHOTALK_LIGHTRAG_LLM_API_KEY", "").strip()
LIGHTRAG_LLM_MODEL = os.getenv("ECHOTALK_LIGHTRAG_LLM_MODEL", "deepseek-ai/DeepSeek-V3").strip()
LIGHTRAG_LLM_TIMEOUT = int(os.getenv("ECHOTALK_LIGHTRAG_LLM_TIMEOUT", "120"))  # 单次抽取/查询超时（秒）
LIGHTRAG_ROOT = Path(os.getenv("ECHOTALK_LIGHTRAG_DIR", str(BACKEND_DIR / "storage" / "lightrag")))

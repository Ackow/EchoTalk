"""嵌入服务（Hybrid RAG）：SiliconFlow OpenAI 兼容 /v1/embeddings 客户端。

- 未配置 ECHOTALK_SILICONFLOW_API_KEY 时 available() 为 False，调用方退化为纯关键词检索；
- 向量以 float32 小端打包进 BLOB（chunk_embeddings.embedding），余弦在应用层计算——
  单场景语料量级为几十~几百块，无需向量数据库；
- 模型默认 BAAI/bge-m3（1024 维）。向量空间随模型变化，换模型必须全量 reindex。
"""
import logging
import math
import struct
import time

import httpx

from app.core import config

logger = logging.getLogger(__name__)

# 单文本截断：bge-m3 上下文 8K token，分块上限 1100 字符本就远小于此，截断只是防御
_MAX_TEXT_CHARS = 4000
# 429 / 5xx 的重试次数与退避基数（秒）
_RETRIES = 2
_RETRY_BACKOFF = 1.0


class EmbeddingUnavailableError(RuntimeError):
    """嵌入链路不可用：未配置 key 或上游持续失败。"""


def available() -> bool:
    """嵌入链路是否可用（仅需配置 key）。"""
    return bool(config.EMBEDDING_API_KEY)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量嵌入：按 EMBEDDING_BATCH_SIZE 切分请求，429/5xx 指数退避重试。

    返回与输入同序的向量列表；维度与 EMBEDDING_DIM 不符时视为配置错误直接抛出。
    """
    if not available():
        raise EmbeddingUnavailableError("未配置 ECHOTALK_SILICONFLOW_API_KEY，嵌入链路停用")
    if not texts:
        return []

    vectors: list[list[float]] = []
    headers = {"Authorization": f"Bearer {config.EMBEDDING_API_KEY}"}
    with httpx.Client(timeout=config.EMBEDDING_TIMEOUT) as client:
        for start in range(0, len(texts), config.EMBEDDING_BATCH_SIZE):
            batch = [t[:_MAX_TEXT_CHARS] for t in texts[start : start + config.EMBEDDING_BATCH_SIZE]]
            payload = {"model": config.EMBEDDING_MODEL, "input": batch, "encoding_format": "float"}
            data = None
            last_error: Exception | None = None
            for attempt in range(_RETRIES + 1):
                try:
                    resp = client.post(f"{config.EMBEDDING_API_BASE}/embeddings", json=payload, headers=headers)
                    if resp.status_code in (429, 500, 502, 503, 504) and attempt < _RETRIES:
                        time.sleep(_RETRY_BACKOFF * (attempt + 1))
                        continue
                    resp.raise_for_status()
                    data = resp.json()["data"]
                    break
                except (httpx.HTTPError, KeyError, ValueError) as exc:
                    last_error = exc
                    if attempt < _RETRIES:
                        time.sleep(_RETRY_BACKOFF * (attempt + 1))
            if data is None:
                raise EmbeddingUnavailableError(f"嵌入请求失败（已重试 {_RETRIES} 次）：{last_error}")
            data.sort(key=lambda item: item["index"])  # 恢复与输入的对应顺序
            vectors.extend(item["embedding"] for item in data)

    if vectors and len(vectors[0]) != config.EMBEDDING_DIM:
        raise EmbeddingUnavailableError(
            f"嵌入维度不符：模型返回 {len(vectors[0])} 维，配置为 {config.EMBEDDING_DIM} 维，请检查 ECHOTALK_EMBEDDING_DIM"
        )
    return vectors


def pack(vector: list[float]) -> bytes:
    """向量 → float32 小端二进制（BLOB 存储格式）。"""
    return struct.pack(f"<{len(vector)}f", *vector)


def unpack(blob: bytes) -> list[float]:
    """BLOB → 向量。"""
    count = len(blob) // 4
    return list(struct.unpack(f"<{count}f", blob))


def cosine(a: list[float], b: list[float]) -> float:
    """余弦相似度（纯 Python，1024 维 × 数百块量级足够快）。"""
    dot = norm_a = norm_b = 0.0
    for x, y in zip(a, b):
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    if norm_a <= 0 or norm_b <= 0:
        return 0.0
    return dot / math.sqrt(norm_a * norm_b)

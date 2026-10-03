"""LightRAG 图谱 RAG 服务：场景/个人知识库共用的实体关系索引与检索。

架构要点（为什么这样设计）：
- **单一后台事件循环线程独占所有 LightRAG 实例**：LightRAG 实例不是线程/循环安全的，
  本应用的端点既有 async 也有 sync（sync 跑在线程池），统一经
  run_coroutine_threadsafe 提交到专用循环，杜绝同一实例被两个事件循环并发触碰；
- **每个知识空间一个 working_dir**（storage/lightrag/scene/{id} 或 personal/{uid}）：
  默认文件存储（JsonKV + NanoVectorDB + NetworkX）对桌面级语料量级远够，免迁移；
- **文档 id 直接复用本应用的 "{scene|personal}-{document.id}"**：LightRAG 的
  ainsert(ids=...) 接受自定义 id，删除用 adelete_by_doc_id，无需额外映射表。
  同名资料更新会换 document.id（先删后建），调用方负责同时调度旧 id 删除；
- **实体抽取走独立配置的 OpenAI 兼容 LLM**（ECHOTALK_LIGHTRAG_LLM_API_BASE/API_KEY/MODEL，
  如 DeepSeek-V3）；嵌入复用 SiliconFlow bge-m3。抽取耗时数十秒，所有维护操作
  fire-and-forget，失败只记日志，绝不阻塞上传主流程；
- 未配置 key / ECHOTALK_LIGHTRAG_ENABLED=false 时 available()=False：
  维护静默跳过，查询接口报 400。
"""
import asyncio
import logging
import shutil
import threading
from pathlib import Path
from typing import Any

from app.core import config

logger = logging.getLogger(__name__)

# LightRAG 查询模式白名单（aquery 的 mode 参数）
QUERY_MODES = ("naive", "local", "global", "hybrid", "mix")
DEFAULT_QUERY_MODE = "mix"
# 查询含一次 LLM 关键词抽取调用，给足超时；rebuild 为 fire-and-forget 无需超时
QUERY_TIMEOUT = 90.0

_instances: dict[str, Any] = {}
_dir_locks: dict[str, asyncio.Lock] = {}
_bg_loop: asyncio.AbstractEventLoop | None = None
_bg_lock = threading.Lock()


def available() -> bool:
    """LightRAG 链路是否可用（开关 + 独立抽取 LLM key + 嵌入 key）。"""
    return bool(
        config.LIGHTRAG_ENABLED
        and config.LIGHTRAG_LLM_API_KEY
        and config.EMBEDDING_API_KEY
    )


def _ensure_bg_loop() -> asyncio.AbstractEventLoop:
    """懒启动专用事件循环线程（进程内单例）。"""
    global _bg_loop
    with _bg_lock:
        if _bg_loop is None or _bg_loop.is_closed():
            loop = asyncio.new_event_loop()
            thread = threading.Thread(target=loop.run_forever, name="lightrag-loop", daemon=True)
            thread.start()
            _bg_loop = loop
        return _bg_loop


def _submit(coro: Any, timeout: float | None = None) -> Any:
    """提交协程到后台循环；timeout  None 时 fire-and-forget（自带异常日志）。"""
    fut = asyncio.run_coroutine_threadsafe(coro, _ensure_bg_loop())
    if timeout is None:
        def _log(exc: BaseException) -> None:
            logger.warning("LightRAG 后台任务失败：%s", exc)
        fut.add_done_callback(lambda f: _log(f.exception()) if f.exception() else None)
        return None
    return fut.result(timeout=timeout)


def _working_dir(kind: str, owner_id: Any) -> Path:
    return config.LIGHTRAG_ROOT / kind / str(owner_id)


def _llm_model_func():
    """OpenAI 兼容 LLM 适配层：LightRAG 会透传 keyword_extraction 等参数。"""
    from lightrag.llm.openai import openai_complete_if_cache

    async def func(prompt: str, system_prompt: str | None = None, history_messages: list | None = None, **kwargs: Any) -> str:
        kwargs.pop("hashing_kv", None)  # LightRAG 内部注入，不透传给 openai binding
        return await openai_complete_if_cache(
            config.LIGHTRAG_LLM_MODEL,
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages or [],
            base_url=config.LIGHTRAG_LLM_API_BASE,
            api_key=config.LIGHTRAG_LLM_API_KEY,
            timeout=config.LIGHTRAG_LLM_TIMEOUT,
            **kwargs,
        )

    return func


def _embedding_func():
    """bge-m3 嵌入适配层：与 hybrid RAG 同模型同 key，向量空间一致。

    不用 LightRAG 的 openai_embed：它被 @wrap_embedding_func_with_attrs(1536)
    装饰，直接调用会用 OpenAI 默认维度 1536 校验 n×1024 的结果（count mismatch）；
    这里直接复用本应用自带的嵌入客户端（批量/重试/排序齐全，已在线上验证）。
    """
    import numpy as np

    from app.scenes import embedding as emb
    from lightrag.utils import EmbeddingFunc

    async def func(texts: list[str]):
        vectors = emb.embed_texts(list(texts))
        return np.array(vectors, dtype=np.float32)

    return EmbeddingFunc(
        embedding_dim=config.EMBEDDING_DIM,
        func=func,
        max_token_size=8192,  # bge-m3 上下文上限
        model_name=config.EMBEDDING_MODEL,
    )


async def _get_instance(key: str, kind: str, owner_id: Any):
    rag = _instances.get(key)
    if rag is not None:
        return rag
    from lightrag import LightRAG

    working_dir = _working_dir(kind, owner_id)
    working_dir.mkdir(parents=True, exist_ok=True)
    rag = LightRAG(
        working_dir=str(working_dir),
        llm_model_func=_llm_model_func(),
        llm_model_name=config.LIGHTRAG_LLM_MODEL,
        llm_model_max_async=2,  # 硅基流动免费档并发限制，保守
        embedding_func=_embedding_func(),
        max_parallel_insert=1,
        addon_params={"language": "Simplified Chinese"},  # 实体/关系抽取输出语言
    )
    await rag.initialize_storages()
    _instances[key] = rag
    _dir_locks.setdefault(key, asyncio.Lock())
    logger.info("LightRAG 实例就绪：%s（%s）", key, working_dir)
    return rag


def _lr_doc_id(kind: str, document_id: int) -> str:
    return f"{kind}-{document_id}"


# ---- 维护操作（后台执行，fire-and-forget） -----------------------------------

async def _upsert(kind: str, owner_id: Any, document_id: int, text: str) -> None:
    key = f"{kind}:{owner_id}"
    lock = _dir_locks.setdefault(key, asyncio.Lock())
    async with lock:
        rag = await _get_instance(key, kind, owner_id)
        lr_id = _lr_doc_id(kind, document_id)
        try:  # 更新场景：旧 id 残留会污染图谱，先删后插
            await rag.adelete_by_doc_id(lr_id)
        except Exception:
            pass  # id 不存在时忽略
        await rag.ainsert(text, ids=lr_id, file_paths=f"{kind}/{document_id}")
        logger.info("LightRAG 已索引 %s/%s（%d 字符）", key, lr_id, len(text))


async def _delete(kind: str, owner_id: Any, document_id: int) -> None:
    key = f"{kind}:{owner_id}"
    if key not in _instances and not _working_dir(kind, owner_id).exists():
        return  # 从未建过索引，无需清理
    lock = _dir_locks.setdefault(key, asyncio.Lock())
    async with lock:
        rag = await _get_instance(key, kind, owner_id)
        await rag.adelete_by_doc_id(_lr_doc_id(kind, document_id))
        logger.info("LightRAG 已移除 %s/%s", key, _lr_doc_id(kind, document_id))


async def _rebuild(kind: str, owner_id: Any, docs: list[tuple[int, str]]) -> int:
    """清空 working_dir 全量重建（换抽取 LLM / 索引损坏后的兜底入口）。"""
    key = f"{kind}:{owner_id}"
    lock = _dir_locks.setdefault(key, asyncio.Lock())
    async with lock:
        rag = _instances.pop(key, None)
        if rag is not None:
            try:
                await rag.finalize_storages()
            except Exception:
                pass
        shutil.rmtree(_working_dir(kind, owner_id), ignore_errors=True)
        if not docs:
            return 0
        rag = await _get_instance(key, kind, owner_id)
        ids = [_lr_doc_id(kind, doc_id) for doc_id, _text in docs]
        await rag.ainsert([text for _doc_id, text in docs], ids=ids)
        logger.info("LightRAG 重建完成：%s（%d 篇）", key, len(docs))
        return len(docs)


def schedule_upsert(kind: str, owner_id: Any, document_id: int, text: str) -> None:
    """插入/更新一篇资料的图谱索引（不阻塞调用方）。"""
    if not available():
        return
    _submit(_upsert(kind, owner_id, document_id, text))


def schedule_delete(kind: str, owner_id: Any, document_id: int) -> None:
    """从图谱索引移除一篇资料（不阻塞调用方）。"""
    if not available():
        return
    _submit(_delete(kind, owner_id, document_id))


def schedule_rebuild(kind: str, owner_id: Any, docs: list[tuple[int, str]]) -> None:
    """全量重建（不阻塞调用方）。docs 为 [(document_id, 源文本)]。"""
    if not available():
        return
    _submit(_rebuild(kind, owner_id, list(docs)))


# ---- 查询（阻塞调用线程直到返回；端点须为 sync def，跑在线程池） --------------

def query(kind: str, owner_id: Any, q: str, mode: str = DEFAULT_QUERY_MODE, top_k: int = 6) -> str:
    """图谱检索上下文（only_need_context：不生成答案，只返回实体/关系/分块）。"""
    if mode not in QUERY_MODES:
        raise ValueError(f"不支持的检索模式：{mode}")

    async def job() -> str:
        key = f"{kind}:{owner_id}"
        rag = await _get_instance(key, kind, owner_id)
        from lightrag import QueryParam

        param = QueryParam(mode=mode, only_need_context=True, top_k=max(1, min(top_k, 20)))
        return await rag.aquery(q, param)

    return _submit(job(), timeout=QUERY_TIMEOUT)

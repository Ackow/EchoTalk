"""混合检索（Hybrid RAG）：ngram 全文关键词 + 嵌入向量余弦，RRF 融合排序。

- 关键词路：MySQL FULLTEXT（ngram 分词，中文友好）MATCH...AGAINST 自然语言模式；
- 向量路：查询文本实时嵌入，与 chunk_embeddings 逐块余弦；
- 融合：Reciprocal Rank Fusion（score = Σ 1/(k+rank)，k=60），对两路分数量纲不敏感；
- 降级：未配置嵌入 key 时自动退为纯关键词模式（mode="keyword"）；
  全文索引缺失（首次调用时自动补建，失败）则 mode="none"。
"""
import logging
from collections import defaultdict
from typing import Any

from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.scenes import embedding as embedding_svc

logger = logging.getLogger(__name__)

RRF_K = 60  # RRF 平滑常数：排名越靠前贡献越大，同时压制单路异常值
CANDIDATE_FACTOR = 3  # 每路召回候选数 = top_k × 3，融合后截回 top_k
_MIN_QUERY_CHARS = 1  # 查询最短长度

# 进程内缓存：全文索引只需补建一次
_fulltext_ready = False


def _ensure_fulltext(db: Session) -> bool:
    """保证 chunks / personal_chunks 存在 ngram 全文索引（幂等；失败返回 False 且不缓存）。"""
    global _fulltext_ready
    if _fulltext_ready:
        return True
    try:
        for table, index in (("chunks", "ft_chunks_text"), ("personal_chunks", "ft_personal_chunks_text")):
            exists = db.execute(
                sql_text(
                    "SELECT 1 FROM information_schema.STATISTICS "
                    "WHERE table_schema = DATABASE() AND table_name = :tbl AND index_name = :idx"
                ),
                {"tbl": table, "idx": index},
            ).first()
            if not exists:
                db.execute(sql_text(f"ALTER TABLE `{table}` ADD FULLTEXT INDEX `{index}` (`text`) WITH PARSER ngram"))
        db.commit()
        _fulltext_ready = True
        return True
    except Exception as exc:
        logger.warning("ngram 全文索引补建失败：%s", exc)
        db.rollback()
        return False


def _keyword_rank(db: Session, table: str, owner_filter: dict[str, Any], query: str, limit: int) -> list[int]:
    """关键词召回：MATCH...AGAINST 自然语言模式，返回按得分降序的 chunk_id 列表。"""
    if table == "chunks":
        where = "c.scene_id = :sid"
    else:
        where = "c.document_id IN (SELECT id FROM personal_documents WHERE owner_id = :uid)"
    params = {**owner_filter, "q": query, "lim": limit}
    rows = db.execute(
        sql_text(
            f"SELECT c.id, MATCH(c.`text`) AGAINST (:q IN NATURAL LANGUAGE MODE) AS score "
            f"FROM `{table}` c WHERE {where} "
            f"AND MATCH(c.`text`) AGAINST (:q IN NATURAL LANGUAGE MODE) "
            f"ORDER BY score DESC LIMIT :lim"
        ),
        params,
    ).fetchall()
    return [row[0] for row in rows]


def _vector_rank(db: Session, table: str, owner_filter: dict[str, Any], query_vector: list[float], limit: int) -> list[int]:
    """向量召回：场景/个人分块的存量向量逐一余弦，返回降序 chunk_id 列表。"""
    from app.models import Chunk, ChunkEmbedding, PersonalChunk, PersonalChunkEmbedding, PersonalDocument

    if table == "chunks":
        rows = (
            db.query(Chunk, ChunkEmbedding)
            .outerjoin(ChunkEmbedding, ChunkEmbedding.chunk_id == Chunk.id)
            .filter(Chunk.scene_id == owner_filter["sid"])
            .all()
        )
    else:
        rows = (
            db.query(PersonalChunk, PersonalChunkEmbedding)
            .join(PersonalDocument, PersonalDocument.id == PersonalChunk.document_id)
            .outerjoin(PersonalChunkEmbedding, PersonalChunkEmbedding.chunk_id == PersonalChunk.id)
            .filter(PersonalDocument.owner_id == owner_filter["uid"])
            .all()
        )
    scored: list[tuple[float, int]] = []
    for chunk, emb in rows:
        if emb is None:
            continue  # 缺向量（上传时嵌入失败）→ 关键词路兜底
        score = embedding_svc.cosine(query_vector, embedding_svc.unpack(emb.embedding))
        if score > 0:
            scored.append((score, chunk.id))
    scored.sort(reverse=True)
    return [chunk_id for _score, chunk_id in scored[:limit]]


def _rrf_fuse(rank_lists: list[list[int]], top_k: int) -> list[int]:
    """Reciprocal Rank Fusion：各路排名倒数求和，返回融合后降序 chunk_id 列表。"""
    scores: dict[int, float] = defaultdict(float)
    for ranks in rank_lists:
        for position, chunk_id in enumerate(ranks):
            scores[chunk_id] += 1.0 / (RRF_K + position + 1)
    return [chunk_id for chunk_id, _score in sorted(scores.items(), key=lambda kv: -kv[1])[:top_k]]


def _assemble(db: Session, table: str, chunk_ids: list[int], used_vector: bool) -> dict[str, Any]:
    """组装检索结果：分块正文 + 文件名 + 可见性 + 模式标记。"""
    from app.models import Chunk, Document, PersonalChunk, PersonalDocument

    if not chunk_ids:
        return {"mode": "hybrid" if used_vector else "keyword", "items": []}
    if table == "chunks":
        rows = db.query(Chunk, Document.filename).join(Document, Document.id == Chunk.document_id).filter(Chunk.id.in_(chunk_ids)).all()
    else:
        rows = (
            db.query(PersonalChunk, PersonalDocument.filename)
            .join(PersonalDocument, PersonalDocument.id == PersonalChunk.document_id)
            .filter(PersonalChunk.id.in_(chunk_ids))
            .all()
        )
    by_id = {row[0].id: (row[0], row[1]) for row in rows}
    items = []
    for rank, chunk_id in enumerate(chunk_ids):
        match = by_id.get(chunk_id)
        if match is None:
            continue
        chunk, filename = match
        items.append({
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "filename": filename,
            "section": chunk.section or "_",
            "ordinal": chunk.ordinal,
            "visibility": chunk.visibility,
            "text": chunk.text,
            "rank": rank,
        })
    return {"mode": "hybrid" if used_vector else "keyword", "items": items}


def search_scene(db: Session, scene_id: str, query: str, top_k: int = 4) -> dict[str, Any]:
    """场景知识混合检索：知识工作区搜索框与对话侧 RAG 注入共用的数据源。"""
    query = (query or "").strip()
    if len(query) < _MIN_QUERY_CHARS:
        return {"query": query, "mode": "none", "items": []}

    fulltext_ok = _ensure_fulltext(db)
    owner_filter = {"sid": scene_id}
    limit = max(top_k * CANDIDATE_FACTOR, 12)

    keyword_ids = _keyword_rank(db, "chunks", owner_filter, query, limit) if fulltext_ok else []

    used_vector = False
    vector_ids: list[int] = []
    if embedding_svc.available():
        try:
            query_vector = embedding_svc.embed_texts([query])[0]
            vector_ids = _vector_rank(db, "chunks", owner_filter, query_vector, limit)
            used_vector = True
        except Exception as exc:
            logger.warning("查询嵌入失败，本次退为关键词检索：%s", exc)

    if not keyword_ids and not vector_ids:
        return {"query": query, "mode": "hybrid" if used_vector else "keyword", "items": []}

    fused = _rrf_fuse([vector_ids, keyword_ids], top_k)
    result = _assemble(db, "chunks", fused, used_vector)
    return {"query": query, **result}


def search_personal(db: Session, user_id: int, query: str, top_k: int = 4) -> dict[str, Any]:
    """个人资料混合检索：与场景检索同一套融合逻辑，数据源为本人全部个人资料。"""
    query = (query or "").strip()
    if len(query) < _MIN_QUERY_CHARS:
        return {"query": query, "mode": "none", "items": []}

    fulltext_ok = _ensure_fulltext(db)
    owner_filter = {"uid": user_id}
    limit = max(top_k * CANDIDATE_FACTOR, 12)

    keyword_ids = _keyword_rank(db, "personal_chunks", owner_filter, query, limit) if fulltext_ok else []

    used_vector = False
    vector_ids: list[int] = []
    if embedding_svc.available():
        try:
            query_vector = embedding_svc.embed_texts([query])[0]
            vector_ids = _vector_rank(db, "personal_chunks", owner_filter, query_vector, limit)
            used_vector = True
        except Exception as exc:
            logger.warning("查询嵌入失败，本次退为关键词检索：%s", exc)

    if not keyword_ids and not vector_ids:
        return {"query": query, "mode": "hybrid" if used_vector else "keyword", "items": []}

    fused = _rrf_fuse([vector_ids, keyword_ids], top_k)
    result = _assemble(db, "personal_chunks", fused, used_vector)
    return {"query": query, **result}

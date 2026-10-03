"""实体关系图谱（阶段三）：LightRAG 真实图谱优先 + 规则化抽取兜底。

数据源选择（scene_graph / personal_graph 统一入口）：
- LightRAG 链路可用且该知识空间已建索引 → 读取 LightRAG 的 graphml
  （LLM 抽取的实体/关系，含类型、描述、权重），engine='lightrag'；
- 否则回退规则版抽取（下方规则描述），engine='rule'。

规则版抽取策略（纯规则、确定可解释；接口与 LLM 抽取对齐，可整体替换）：
- 实体节点：
  - 资料文件（kind=file）
  - 分节（kind=section）：跨文件同名合并为同一节点，天然构成文件间的桥接实体
- 关系边：
  - contains：文件 → 其包含的分节
  - related：跨文件分节两两计算词集重叠系数（|∩|/min），达标则连边（阈值 0.18，取 Top N）
- 可见性：分节节点汇总其分块可见性（user / ai_only / mixed）；个人资料统一 user。

场景图谱与个人资料图谱共用 _build_graph，仅数据源查询不同。
"""
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.scenes import knowledge
from app.scenes.errors import SceneNotFoundError

logger = logging.getLogger(__name__)

# 关键词抽取：英文词（≥3 字符，含内部连接符/数字）或 2~6 字中文词组
_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_+-]{2,}|[\u4e00-\u9fff]{2,6}")

# 高频虚词停用：不参与相关度计算（最小集合，命中常见文档套话即可）
_STOPWORDS = frozenset(
    """the a an and or for with this that these those are was were be been is of to in on
    at by from as it its will can may should would must have has had not you your we our
    they their their them he she his her but if then than when what which who whom how why
    all any each few more most other some such no nor only own same so too very s t just
    don now about into over under between within during before after above below up down
    out off again further once here there where both each why also very using use used
    will shall may might must do does did doing done have having
    一个 我们 你们 他们 这个 那个 以及 但是 如果 那么 因为 所以 或者 并且 可以 需要 应该
    通过 对于 关于 进行 使用 可以 这些 那些 没有 已经""".split()
)

RELATED_THRESHOLD = 0.18  # 相关边重叠系数阈值（|∩| / min(|A|,|B|)）
RELATED_MIN_INTERSECTION = 2  # 相关边最少共同词数：避免单词巧合连边
RELATED_MAX = 14  # 相关边数量上限：只保留重叠分数最高的前 N 条
TOKENS_PER_SECTION = 200  # 每个分节最多参与计算的词数

LR_DESC_MAX = 160  # 实体描述下发截断长度（前端 tooltip 展示足够）
LR_EDGE_DESC_MAX = 100  # 关系描述/关键词下发截断长度

# graphml 解析结果按 (路径, mtime) 缓存：索引未变时避免重复解析文件
_graphml_cache: dict[tuple[str, float], dict[str, Any]] = {}


def _lightrag_graph(kind: str, owner_id: Any, meta: dict[str, Any]) -> dict[str, Any] | None:
    """读取 LightRAG 图存储（graphml）组装实体关系图谱。

    该知识空间从未建过索引（目录/文件不存在或空图）时返回 None，
    调用方回退规则版；解析失败只记日志并回退，不让图谱接口报错。
    """
    import networkx as nx

    from app.core import config

    graphml = Path(config.LIGHTRAG_ROOT) / kind / str(owner_id) / "graph_chunk_entity_relation.graphml"
    if not graphml.exists():
        return None
    try:
        mtime = graphml.stat().st_mtime
        cached = _graphml_cache.get((str(graphml), mtime))
        if cached is not None:
            return {**cached, **meta}
        g = nx.read_graphml(graphml)
        if g.number_of_nodes() == 0:
            return None
        nodes = []
        for name, attrs in g.nodes(data=True):
            description = str(attrs.get("description") or "").replace("<SEP>", "；")
            files = sorted({p.strip() for p in str(attrs.get("file_path") or "").split(",") if p.strip()})
            nodes.append({
                "id": f"ent:{name}",
                "label": name,
                "kind": "entity",
                "entity_type": (str(attrs.get("entity_type") or "").strip() or "other").lower(),
                "description": description[:LR_DESC_MAX],
                "files": files,  # 来源 document.id 列表（LightRAG file_paths 记录）
            })
        edges = []
        for s, t, attrs in g.edges(data=True):
            try:
                weight = float(attrs.get("weight") or 1.0)
            except (TypeError, ValueError):
                weight = 1.0
            edges.append({
                "source": f"ent:{s}",
                "target": f"ent:{t}",
                "kind": "lr_related",
                "weight": round(weight, 2),
                "keywords": str(attrs.get("keywords") or "")[:LR_EDGE_DESC_MAX],
                "description": str(attrs.get("description") or "").replace("<SEP>", "；")[:LR_EDGE_DESC_MAX],
            })
        payload = {
            **meta,
            "engine": "lightrag",
            "nodes": nodes,
            "edges": edges,
            "totals": {"entities": len(nodes), "relations": len(edges)},
            "truncated": False,
        }
        from app.scenes import lightrag_service

        payload["index"] = lightrag_service.index_status(kind, owner_id)  # 透传构建进度（缓存命中时随 payload 一起复用）
        _graphml_cache[(str(graphml), mtime)] = payload
        return {**payload, **meta}
    except Exception as exc:
        logger.warning("LightRAG 图谱读取失败，回退规则版：%s", exc)
        return None


def _tokenize(text: str) -> list[str]:
    """切词并过滤停用词：小写化，保留英文词与中文 2~6 字词组。"""
    words = []
    for raw in _TOKEN_RE.findall(text or ""):
        word = raw.lower()
        if len(word) < 2 or word in _STOPWORDS:
            continue
        words.append(word)
    return words


def _section_visibility(visibilities: set[str]) -> str:
    """汇总分节可见性：全部 user → user；全部 ai_only → ai_only；混合 → mixed。"""
    if len(visibilities) == 1:
        return next(iter(visibilities))
    return "mixed"


def _build_graph(documents: list[Any], chunks_by_doc: dict[int, list[Any]], meta: dict[str, Any]) -> dict[str, Any]:
    """通用图谱组装：文件节点 + 分节实体（跨文件同名合并）+ 从属/相关边。

    documents / chunks_by_doc 由场景与个人资料两个入口各自查询后传入，
    抽取与布局逻辑完全共用，保证两处图谱行为一致。
    """
    if not documents:
        return {**meta, "nodes": [], "edges": [], "truncated": False}

    # ---- 分节实体：跨文件按分节名合并 ----
    sections: dict[str, dict[str, Any]] = {}  # section 名 → 节点数据
    for doc in documents:
        for chunk in chunks_by_doc.get(doc.id, []):
            name = chunk.section or "_"
            node = sections.setdefault(
                name,
                {"id": f"sec:{name}", "label": name, "kind": "section", "files": [], "chunk_count": 0,
                 "visibility": set(), "tokens": []},
            )
            node["files"].append(doc.id)
            node["chunk_count"] += 1
            node["visibility"].add(chunk.visibility)
            if not node["tokens"]:
                node["tokens"].extend(_tokenize(node["label"]) * 2)  # 标题词加权：主题词是关联的核心信号
            node["tokens"].extend(_tokenize(chunk.text)[:TOKENS_PER_SECTION])

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    for doc in documents:
        nodes.append({
            "id": f"file:{doc.id}",
            "label": doc.filename,
            "kind": "file",
            "sections_count": len({c.section or "_" for c in chunks_by_doc.get(doc.id, [])}),
        })
    for node in sections.values():
        nodes.append({
            "id": node["id"],
            "label": node["label"],
            "kind": "section",
            "files": node["files"],
            "chunk_count": node["chunk_count"],
            "visibility": _section_visibility(node["visibility"]),
        })
        for file_id in node["files"]:  # 从属边：文件 → 分节
            edges.append({"source": f"file:{file_id}", "target": node["id"], "kind": "contains"})

    # ---- 相关边：跨文件分节两两重叠系数（|∩| / min(|A|,|B|)） ----
    keys = list(sections)
    scored: list[tuple[float, str, str]] = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = sections[keys[i]], sections[keys[j]]
            if set(a["files"]) & set(b["files"]):
                continue  # 只连跨文件分节：同文件的从属关系已由 contains 表达
            sa, sb = set(a["tokens"]), set(b["tokens"])
            if not sa or not sb:
                continue
            inter = len(sa & sb)
            coef = inter / min(len(sa), len(sb))
            if inter >= RELATED_MIN_INTERSECTION and coef >= RELATED_THRESHOLD:
                scored.append((coef, inter, keys[i], keys[j]))
    scored.sort(reverse=True)
    for _coef, _inter, key_a, key_b in scored[:RELATED_MAX]:
        edges.append({
            "source": f"sec:{key_a}",
            "target": f"sec:{key_b}",
            "kind": "related",
            "score": round(_coef, 2),
        })

    for node in sections.values():
        node.pop("tokens", None)  # 内部计算字段不下发
    return {**meta, "engine": "rule", "nodes": nodes, "edges": edges, "truncated": len(scored) > RELATED_MAX}


def scene_graph(db: Session, scene_id: str) -> dict[str, Any]:
    """场景知识图谱：LightRAG 已建索引时返回真实实体关系图，否则规则抽取版。

    无论走哪个引擎，都带 index 字段（索引构建进度/失败原因），前端据此
    展示"构建中 X/N"或失败提示——避免后台索引对用户完全不可见。
    """
    from app.scenes import lightrag_service

    if lightrag_service.available():
        lr = _lightrag_graph("scene", scene_id, {"scene_id": scene_id})
        if lr is not None:
            return lr
        index_meta = lightrag_service.index_status("scene", scene_id)
    else:
        index_meta = {"status": "disabled", "done": 0, "total": 0, "failed": 0, "error": None}
    documents = knowledge.list_documents(db, scene_id)
    chunks_by_doc: dict[int, list[Any]] = defaultdict(list)
    if documents:
        doc_ids = {doc.id for doc in documents}
        for row in db.query(knowledge.Chunk).filter(
            knowledge.Chunk.scene_id == scene_id, knowledge.Chunk.document_id.in_(doc_ids)
        ).order_by(knowledge.Chunk.id):
            chunks_by_doc[row.document_id].append(row)
    return {**_build_graph(documents, chunks_by_doc, {"scene_id": scene_id}), "index": index_meta}


def personal_graph(db: Session, user_id: int) -> dict[str, Any]:
    """个人资料图谱：与场景图谱同一套数据源选择，规则版共用抽取逻辑。"""
    from app.models import PersonalChunk, PersonalDocument
    from app.scenes import lightrag_service

    if lightrag_service.available():
        lr = _lightrag_graph("personal", user_id, {"scope": "personal", "owner_id": user_id})
        if lr is not None:
            return lr
        index_meta = lightrag_service.index_status("personal", user_id)
    else:
        index_meta = {"status": "disabled", "done": 0, "total": 0, "failed": 0, "error": None}

    documents = (
        db.query(PersonalDocument)
        .filter(PersonalDocument.owner_id == user_id)
        .order_by(PersonalDocument.id)
        .all()
    )
    chunks_by_doc: dict[int, list[Any]] = defaultdict(list)
    if documents:
        doc_ids = {doc.id for doc in documents}
        for row in db.query(PersonalChunk).filter(
            PersonalChunk.document_id.in_(doc_ids)
        ).order_by(PersonalChunk.id):
            chunks_by_doc[row.document_id].append(row)
    return {**_build_graph(documents, chunks_by_doc, {"scope": "personal", "owner_id": user_id}), "index": index_meta}

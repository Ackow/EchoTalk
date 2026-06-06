import os
import json
import re
import hashlib
import numpy as np
import faiss
from typing import List, Dict, Any, Tuple, Optional, Union
from openai import OpenAI
from app.core.config import settings
from app.core.logger import log_api_call

# 向量特征维度（对应 BAAI/bge-large-en-v1.5 默认维度 1024）
DIMENSION = 1024

# ──────────────────────────────────────────────
# 结构化分块类型定义
# ──────────────────────────────────────────────
# 新格式：每个分块是一个 dict，包含 section/content/visibility
# 旧格式：每个分块是一个纯文本 str（向后兼容）

ChunkDict = Dict[str, Any]
# 典型结构：
# {
#   "section": "menu",           # 分节名称（如 "menu", "barista_workflow", "vocabulary"）
#   "content": "...",           # 分块文本内容
#   "visibility": "user",        # "user" = 用户可见，"ai_only" = 仅 AI 使用
# }

RawChunk = Union[str, ChunkDict]


def hash_text_to_vector(text: str, dimensions: int = DIMENSION) -> np.ndarray:
    """
    无 Key 离线兜底算法：基于 MD5 特征哈希（Feature Hashing）生成 1024 维局部敏感向量。
    该算法对英文/中文词汇在机器重启、进程复位后均能产生 100% 确定且不变的向量值，且特征重合度计算符合余弦相似度。
    """
    words = re.findall(r'\w+', text.lower()) if text else []
    vector = np.zeros(dimensions, dtype=np.float32)
    for w in words:
        # 使用 MD5 保证在不同进程生命周期内哈希值的一致性
        h_str = hashlib.md5(w.encode('utf-8')).hexdigest()
        h = int(h_str, 16)

        # 索引与正负符号双重哈希，减少冲突偏置
        idx = h % dimensions
        sign = 1 if (h // dimensions) % 2 == 0 else -1
        vector[idx] += sign

    # 执行 L2 归一化，使其在 L2 空间的比对等价于余弦相似度
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm
    else:
        vector[0] = 1.0  # 纯空文本降级占位符
    return vector


def get_embedding(text: str) -> List[float]:
    """
    为指定文本生成 1024 维特征向量。
    如果配置了有效 API Key 则调用 Siliconflow 兼容接口进行 HTTP POST 提取，
    否则自动降级为本地 MD5 哈希特征生成器。
    """
    import requests
    # 提取 Embedding 相关配置，允许独立设置，默认共用大模型 Key 和 BaseURL
    api_key = settings.EMBEDDING_API_KEY or settings.OPENAI_API_KEY
    base_url = settings.EMBEDDING_BASE_URL or settings.OPENAI_BASE_URL
    model_name = settings.EMBEDDING_MODEL

    has_credentials = (
        api_key
        and api_key != "mock-key"
        and api_key != "your_openai_api_key"
    )

    if not has_credentials:
        # 无需联网的本地哈希生成
        log_api_call(
            api_type="向量嵌入 (Embedding)",
            provider="本地离线引擎",
            url="None (Offline)",
            model=model_name,
            action="RAG 知识库向量化 (get_embedding)",
            status="success",
            extra_info=f"未配置有效密钥，已安全降级为本地哈希向量生成器（输入文本前40字: '{text[:40]}...'）。"
        )
        return hash_text_to_vector(text).tolist()

    try:
        # 构建标准的 /embeddings 完整端点 URL
        url = base_url.rstrip("/")
        if not url.endswith("/embeddings"):
            url = f"{url}/embeddings"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "input": text,
            "model": model_name
        }

        log_api_call(
            api_type="向量嵌入 (Embedding)",
            provider="Siliconflow / OpenAI 兼容端点",
            url=url,
            model=model_name,
            action="RAG 知识库向量化 (get_embedding)",
            status="pending"
        )

        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        res_data = response.json()
        log_api_call(
            api_type="向量嵌入 (Embedding)",
            provider="Siliconflow / OpenAI 兼容端点",
            url=url,
            model=model_name,
            action="RAG 知识库向量化 (get_embedding)",
            status="success",
            extra_info=f"生成向量成功，输入文本前 40 字: {text[:40]}..."
        )
        return res_data["data"][0]["embedding"]
    except Exception as e:
        log_api_call(
            api_type="向量嵌入 (Embedding)",
            provider="Siliconflow / OpenAI 兼容端点",
            url=url,
            model=model_name,
            action="RAG 知识库向量化 (get_embedding)",
            status="failed",
            extra_info=str(e)
        )
        return hash_text_to_vector(text).tolist()


def get_index_paths(scene_id: str) -> Tuple[str, str]:
    """
    获取指定场景 RAG 索引文件与文本块 JSON 文件的存储路径。
    """
    indices_dir = settings.static_rag_indices_dir
    index_file = os.path.join(indices_dir, f"{scene_id}.index")
    json_file = os.path.join(indices_dir, f"{scene_id}.json")
    return index_file, json_file


# ──────────────────────────────────────────────
# 分块格式标准化工具函数
# ──────────────────────────────────────────────

def _normalize_chunk(chunk: RawChunk) -> ChunkDict:
    """
    将任意格式的分块统一为 ChunkDict 格式。

    - 如果是 str（旧格式），自动检测节标题并赋予默认 visibility="ai_only"
    - 如果是 dict（新格式），补充缺失字段
    """
    if isinstance(chunk, str):
        # 旧格式兼容：自动检测节标题
        section = _detect_section_from_text(chunk)
        return {
            "section": section,
            "content": chunk,
            "visibility": "ai_only",  # 旧格式默认仅 AI 使用，安全保守
            "_has_vis": False
        }
    if isinstance(chunk, dict):
        # 新格式：确保必要字段存在，记录是否原本就有 visibility
        has_vis = "visibility" in chunk
        return {
            "section": chunk.get("section", "general"),
            "content": chunk.get("content", chunk.get("text", "")),
            "visibility": chunk.get("visibility", "ai_only"),
            "title": chunk.get("title"),
            "_has_vis": has_vis
        }
    # 兜底：无法识别的格式，转为字符串
    text = str(chunk)
    return {
        "section": _detect_section_from_text(text),
        "content": text,
        "visibility": "ai_only",
        "_has_vis": False
    }


def _extract_content(chunk: RawChunk) -> str:
    """
    从分块中提取纯文本内容（用于向量化和 LLM 上下文拼接）。
    """
    if isinstance(chunk, str):
        return chunk
    if isinstance(chunk, dict):
        return chunk.get("content", chunk.get("text", ""))
    return str(chunk)


def _detect_section_from_text(text: str) -> str:
    """
    启发式检测文本所属的分节类别。
    根据文本内容中的关键词判断它属于哪个场景节。
    """
    text_lower = text.lower()

    # 菜单/价格相关
    if any(kw in text_lower for kw in ["$", "price", "menu", "espresso", "latte", "cappuccino",
                                         "americano", "cold brew", "matcha", "chai latte",
                                         "hot chocolate", "breakfast", "bakery", "muffin",
                                         "bagel", "avocado toast", "surcharge"]):
        return "menu"

    # 定制选项相关
    if any(kw in text_lower for kw in ["tall", "grande", "venti", "size", "milk options",
                                         "oat milk", "almond milk", "soy milk", "sweetener",
                                         "syrup", "half-sweet", "ice levels", "temperature"]):
        return "customization"

    # 服务员工作流程相关
    if any(kw in text_lower for kw in ["barista", "workflow", "greeting", "upsell",
                                         "dine-in", "to-go", "payment", "queue",
                                         "inventory", "out of stock", "suggest"]):
        return "barista_workflow"

    # 常用口语表达/词汇相关
    if any(kw in text_lower for kw in ["how to ask", "how to order", "vocabulary",
                                         "can i get", "i'd like", "could i have",
                                         "terminology", "slang"]):
        return "vocabulary"

    # 面试相关
    if any(kw in text_lower for kw in ["interview", "candidate", "behavioral", "technical",
                                         "frontend", "react", "vue", "javascript",
                                         "star method", "tell me about yourself"]):
        return "interview"

    # 会议相关
    if any(kw in text_lower for kw in ["meeting", "agenda", "deadline", "milestone",
                                         "sprint", "retrospective", "blocker"]):
        return "meeting"

    return "general"


def _get_default_visibility_for_section(section: str) -> str:
    """
    根据分节名称返回默认的可见性设置。
    管理员上传文档后可手动调整，此函数提供合理默认值。
    """
    # 默认对用户可见的节
    user_visible_sections = {"menu", "customization", "vocabulary", "interview_questions"}
    if section in user_visible_sections:
        return "user"
    # 默认仅 AI 使用的节（内部流程、规则、库存等）
    return "ai_only"


def normalize_chunks(chunks: List[RawChunk]) -> List[ChunkDict]:
    """
    将一批分块统一标准化为 List[ChunkDict]。
    自动处理旧格式的 List[str] 兼容。
    """
    normalized = []
    for chunk in chunks:
        nd = _normalize_chunk(chunk)
        # 如果 visibility 还是默认 "ai_only"，且非用户手动配置，则根据节名再判断一次
        if not nd.get("_has_vis") and nd["visibility"] == "ai_only":
            nd["visibility"] = _get_default_visibility_for_section(nd["section"])
        
        # 清除临时状态变量
        if "_has_vis" in nd:
            del nd["_has_vis"]
            
        normalized.append(nd)
    return normalized


def chunks_to_rag_text(chunks: List[RawChunk]) -> str:
    """
    将分块列表拼接为纯文本（用于 LLM 上下文）。
    无论新旧格式，都只提取 content/文本部分。
    """
    texts = []
    for chunk in chunks:
        texts.append(_extract_content(chunk))
    return "\n".join(texts) if texts else ""


# ──────────────────────────────────────────────
# 核心 RAG 函数
# ──────────────────────────────────────────────

def save_index(scene_id: str, index: faiss.Index, chunks: List[RawChunk]):
    """
    将 FAISS 向量索引与文本内容映射持久化至本地硬盘。
    分块会先标准化为 ChunkDict 再保存。
    """
    index_file, json_file = get_index_paths(scene_id)
    # 写入 FAISS 物理索引文件
    faiss.write_index(index, index_file)
    # 标准化并写入映射的文本块
    normalized = normalize_chunks(chunks)
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)


def load_index(scene_id: str) -> Tuple[Optional[faiss.Index], List[ChunkDict]]:
    """
    从硬盘加载指定场景的向量索引和文本分块。
    返回值中的 chunks 始终为 List[ChunkDict]（旧格式自动升级）。
    如果不存在则返回 (None, [])。
    """
    index_file, json_file = get_index_paths(scene_id)
    if not os.path.exists(index_file) or not os.path.exists(json_file):
        return None, []

    try:
        index = faiss.read_index(index_file)
        with open(json_file, "r", encoding="utf-8") as f:
            raw_chunks = json.load(f)
        # 统一标准化（自动处理旧格式 List[str] 升级）
        chunks = normalize_chunks(raw_chunks)
        return index, chunks
    except Exception as e:
        print(f"[RAG 索引加载失败] 场景 {scene_id} 索引损坏: {e}")
        return None, []


def add_documents_to_scene(scene_id: str, new_chunks: List[RawChunk]):
    """
    将提取出来的文本分块向量化，并追加写入到场景对应的 RAG 本地索引中。
    支持 List[str]（旧格式）和 List[Dict]（新格式）。
    """
    if not new_chunks:
        return

    # 1. 尝试加载已有的索引
    index, chunks = load_index(scene_id)

    if index is None:
        # 如果是首次上传，则创建一个常规的 L2 扁平索引
        index = faiss.IndexFlatL2(DIMENSION)
        chunks = []

    # 2. 标准化新分块，并为所有文本块生成特征向量
    normalized_new = normalize_chunks(new_chunks)
    vectors = []
    for chunk in normalized_new:
        emb = get_embedding(chunk["content"])
        vectors.append(emb)

    vectors_np = np.array(vectors, dtype=np.float32)

    # 3. 将新向量添加进索引，并扩充文本列表
    index.add(vectors_np)
    chunks.extend(normalized_new)

    # 4. 持久化保存
    save_index(scene_id, index, chunks)
    print(f"[RAG 知识库更新] 成功向场景 {scene_id} 添加 {len(normalized_new)} 个分块，当前累积分块数: {len(chunks)}")


def query_scene_knowledge(scene_id: str, query: str, top_k: int = 3) -> List[str]:
    """
    根据用户提问，在指定场景知识库中检索出最相关的 Top-K 个文本分块。
    返回值始终为纯文本 List[str]（兼容旧调用方）。
    """
    index, chunks = load_index(scene_id)
    # 如果该场景尚未建立知识库或内容为空，直接返回空列表
    if index is None or not chunks:
        return []

    # 1. 生成提问的特征向量并转换为 NumPy 格式
    query_emb = get_embedding(query)
    query_vector = np.array([query_emb], dtype=np.float32)

    # 2. 执行向量相似度检索 (Top-K)
    # D: 距离数组, I: 匹配到的文本分块索引数组
    D, I = index.search(query_vector, min(top_k, len(chunks)))

    # 3. 提取对应的文本内容（过滤掉 -1 的空值）
    matched_chunks = []
    for idx in I[0]:
        if idx != -1 and idx < len(chunks):
            matched_chunks.append(_extract_content(chunks[idx]))

    return matched_chunks


def get_user_visible_chunks(scene_id: str) -> List[ChunkDict]:
    """
    获取场景中对用户可见的知识库分块（visibility == "user"）。
    按照分节名称聚合，便于前端展示。
    """
    _, chunks = load_index(scene_id)
    if not chunks:
        return []

    # 筛选用户可见的分块
    user_chunks = [c for c in chunks if c.get("visibility") == "user"]

    # 按 section 分组并合并内容，形成完整的分节
    sections: Dict[str, List[str]] = {}
    section_titles: Dict[str, str] = {}
    for chunk in user_chunks:
        sec = chunk.get("section", "general")
        if sec not in sections:
            sections[sec] = []
        sections[sec].append(chunk["content"])
        if chunk.get("title") and sec not in section_titles:
            section_titles[sec] = chunk["title"]

    # 合并为结构化列表
    result = []
    for sec_name, contents in sections.items():
        result.append({
            "section": sec_name,
            "content": "\n\n".join(contents),
            "title": section_titles.get(sec_name)
        })

    return result


def get_scene_section_overview(scene_id: str) -> List[Dict[str, Any]]:
    """
    获取场景知识库的所有分节概览（包含 visibility 信息），供管理界面使用。
    """
    _, chunks = load_index(scene_id)
    if not chunks:
        return []

    seen = set()
    overview = []
    for chunk in chunks:
        sec = chunk.get("section", "general")
        vis = chunk.get("visibility", "ai_only")
        key = f"{sec}:{vis}"
        if key not in seen:
            seen.add(key)
            count = sum(1 for c in chunks if c.get("section") == sec and c.get("visibility") == vis)
            title = None
            for c in chunks:
                if c.get("section") == sec and c.get("title"):
                    title = c["title"]
                    break
            overview.append({
                "section": sec,
                "visibility": vis,
                "chunk_count": count,
                "title": title
            })

    return overview


def clear_scene_knowledge(scene_id: str):
    """
    彻底清空并删除指定场景的本地 RAG 向量索引和文档库。
    """
    index_file, json_file = get_index_paths(scene_id)
    for path in [index_file, json_file]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                print(f"[RAG 清理错误] 无法删除文件 {path}: {e}")
    print(f"[RAG 知识库清空] 场景 {scene_id} 的本地知识库已全部销毁。")

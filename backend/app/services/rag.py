import os
import json
import re
import hashlib
import numpy as np
import faiss
from typing import List, Dict, Any, Tuple, Optional
from openai import OpenAI
from app.core.config import settings
from app.core.logger import log_api_call

# 向量特征维度（对应 BAAI/bge-large-en-v1.5 默认维度 1024）
DIMENSION = 1024

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
        vector[0] = 1.0 # 纯空文本降级占位符
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

        # 调用 requests.post 提取嵌入向量
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


def save_index(scene_id: str, index: faiss.Index, chunks: List[str]):
    """
    将 FAISS 向量索引与文本内容映射持久化至本地硬盘。
    """
    index_file, json_file = get_index_paths(scene_id)
    # 写入 FAISS 物理索引文件
    faiss.write_index(index, index_file)
    # 写入映射的文本块
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)


def load_index(scene_id: str) -> Tuple[Optional[faiss.Index], List[str]]:
    """
    从硬盘加载指定场景的向量索引和文本分块。如果不存在则返回 (None, [])。
    """
    index_file, json_file = get_index_paths(scene_id)
    if not os.path.exists(index_file) or not os.path.exists(json_file):
        return None, []
    
    try:
        index = faiss.read_index(index_file)
        with open(json_file, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        return index, chunks
    except Exception as e:
        print(f"[RAG 索引加载失败] 场景 {scene_id} 索引损坏: {e}")
        return None, []


def add_documents_to_scene(scene_id: str, new_chunks: List[str]):
    """
    将提取出来的文本分块向量化，并追加写入到场景对应的 RAG 本地索引中。
    """
    if not new_chunks:
        return

    # 1. 尝试加载已有的索引
    index, chunks = load_index(scene_id)
    
    if index is None:
        # 如果是首次上传，则创建一个常规的 L2 扁平索引
        index = faiss.IndexFlatL2(DIMENSION)
        chunks = []

    # 2. 为所有文本块生成特征向量并组合成 NumPy 矩阵
    vectors = []
    for chunk in new_chunks:
        emb = get_embedding(chunk)
        vectors.append(emb)
    
    vectors_np = np.array(vectors, dtype=np.float32)

    # 3. 将新向量添加进索引，并扩充文本列表
    index.add(vectors_np)
    chunks.extend(new_chunks)

    # 4. 持久化保存
    save_index(scene_id, index, chunks)
    print(f"[RAG 知识库更新] 成功向场景 {scene_id} 添加 {len(new_chunks)} 个分块，当前累积分块数: {len(chunks)}")


def query_scene_knowledge(scene_id: str, query: str, top_k: int = 3) -> List[str]:
    """
    根据用户提问，在指定场景知识库中检索出最相关的 Top-K 个文本分块。
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
            matched_chunks.append(chunks[idx])
            
    return matched_chunks


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

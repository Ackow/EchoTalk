import os
import sys

# 将 backend 目录添加到 Python 路径中，以便能够导入 app 包
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.document import get_document_chunks
from app.services.rag import add_documents_to_scene, query_scene_knowledge, clear_scene_knowledge

# 测试数据及临时场景设置
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "data", "rag_seeds")
TEST_SCENE = "test_scene_rag"

def test_rag_flow():
    """
    测试本地 RAG 完整检索闭环：切片录入 -> 本地向量哈希/Embedding -> 邻近向量查询 -> 检索召回
    """
    print("\n--- [RAG 检索连通性测试开始] ---")
    
    # 清理历史可能残留的临时测试索引
    clear_scene_knowledge(TEST_SCENE)
    
    # 1. 载入面试指南并进行分块
    interview_file = os.path.join(DATA_DIR, "interview_prep.txt")
    assert os.path.exists(interview_file)
    chunks = get_document_chunks(
        interview_file, 
        chunk_size=300, 
        chunk_overlap=50, 
        keep_user_sections_whole=False
    )
    print(f"解析 interview_prep.txt 得到 {len(chunks)} 个分块。")
    
    # 2. 将分块录入到 RAG 向量数据库
    add_documents_to_scene(TEST_SCENE, chunks)
    
    # 3. 语义查询验证一：测试关于 React Virtual DOM 的检索
    query_1 = "What is the Virtual DOM and React reconciliation?"
    print(f"\n[提问 1] '{query_1}'")
    results_1 = query_scene_knowledge(TEST_SCENE, query_1, top_k=2)
    
    print(f"召回结果数量: {len(results_1)} 个分块")
    for i, r in enumerate(results_1):
        print(f"  分块 {i+1} 内容 (前80字): {r[:80]}...")
        
    assert len(results_1) > 0, "提问 1 未召回任何分块内容！"
    # 验证召回的第一块确实包含 Virtual DOM 相关关键词
    assert "virtual dom" in results_1[0].lower() or "fiber" in results_1[0].lower(), "未检索到最相关的 Virtual DOM 知识块！"
    
    # 4. 语义查询验证二：测试关于 Critical Rendering Path 的检索
    query_2 = "Explain the Critical Rendering Path and reflow"
    print(f"\n[提问 2] '{query_2}'")
    results_2 = query_scene_knowledge(TEST_SCENE, query_2, top_k=1)
    
    print(f"召回结果数量: {len(results_2)} 个分块")
    if results_2:
        print(f"  分块 1 内容 (前120字): {results_2[0][:120]}...")
        
    assert len(results_2) > 0, "提问 2 未召回任何分块内容！"
    assert "rendering path" in results_2[0].lower() or "reflow" in results_2[0].lower(), "未检索到最相关的浏览器渲染路径知识块！"

    # 5. 清理现场
    clear_scene_knowledge(TEST_SCENE)
    print("\n[SUCCESS] RAG 向量特征提取、FAISS 写入与语义匹配全部通过测试！")

if __name__ == "__main__":
    try:
        test_rag_flow()
    except AssertionError as e:
        print(f"\n[FAIL] RAG 检索测试失败: {e}")
        sys.exit(1)
    except Exception as ex:
        print(f"\n[FAIL] 运行过程发生非预期异常: {ex}")
        sys.exit(1)

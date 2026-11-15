import os
import sys
from fastapi.testclient import TestClient

# 将 backend 目录添加到 Python 路径中
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app, seed_default_scenes
from app.core.database import get_db, engine, Base
from app.models import Scene

client = TestClient(app)
Base.metadata.create_all(bind=engine)

def test_scene_rag_endpoints_flow():
    print("\n--- [场景 RAG 接口端到端测试开始] ---")
    scene_id = "interview"
    
    # 0. 确保数据库中存在 interview 场景
    db = next(get_db())
    seed_default_scenes(db)
    existing = db.query(Scene).filter(Scene.id == scene_id).first()
    assert existing is not None, f"数据库中未找到场景 {scene_id}"
    db.close()

    # 1. 确保先清空该场景的历史文档，保持测试环境干净
    print("\n[步骤 1] 清空该场景的 RAG 知识库...")
    del_resp = client.delete(f"/api/scenes/{scene_id}/documents")
    assert del_resp.status_code == 200
    data = del_resp.json()
    assert data["rag_metadata"] == []
    print("清空成功！")

    # 2. 准备一份临时测试文档
    print("\n[步骤 2] 准备临时测试文档...")
    temp_filename = "temp_interview_docs.txt"
    temp_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), temp_filename)
    
    # 写入一些关于 React Native JSI 架构的特色文本
    test_content = (
        "React Native uses a JavaScript bridge to communicate with native platform modules. "
        "The bridge processes serialized messages asynchronously. "
        "However, complex UI animations might suffer from performance bottlenecks. "
        "To address this, the new React Native architecture introduces JSI (JavaScript Interface), "
        "allowing JS to call native methods directly in a synchronous manner without serialization."
    )
    with open(temp_filepath, "w", encoding="utf-8") as f:
        f.write(test_content)
    print(f"临时文件创建成功: {temp_filepath}")

    try:
        # 3. 测试文件上传接口
        print("\n[步骤 3] 上传文档至场景 RAG 库...")
        with open(temp_filepath, "rb") as f:
            upload_resp = client.post(
                f"/api/scenes/{scene_id}/upload",
                files={"file": (temp_filename, f, "text/plain")}
            )
        
        assert upload_resp.status_code == 200
        upload_data = upload_resp.json()
        print(f"上传成功！当前 RAG 元数据: {upload_data['rag_metadata']}")
        assert len(upload_data["rag_metadata"]) == 1
        assert upload_data["rag_metadata"][0]["filename"] == temp_filename
        assert upload_data["rag_metadata"][0]["chunk_count"] > 0

        # 4. 测试语义检索端点
        print("\n[步骤 4] 语义检索测试...")
        query_payload = {
            "query": "What is JSI and how does it improve React Native performance?",
            "top_k": 1
        }
        query_resp = client.post(f"/api/scenes/{scene_id}/query", json=query_payload)
        assert query_resp.status_code == 200
        query_data = query_resp.json()
        print(f"检索到 {len(query_data['results'])} 条匹配分块:")
        for r in query_data["results"]:
            print(f"  - {r[:100]}...")
            
        assert len(query_data["results"]) > 0
        assert "jsi" in query_data["results"][0].lower() or "bridge" in query_data["results"][0].lower()

        # 5. 清理场景文档库并验证
        print("\n[步骤 5] 再次调用删除路由清空库...")
        del_resp_2 = client.delete(f"/api/scenes/{scene_id}/documents")
        assert del_resp_2.status_code == 200
        data_2 = del_resp_2.json()
        assert data_2["rag_metadata"] == []
        print("二次清空成功！")

    finally:
        # 清理物理临时测试文件
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
            print(f"清理临时文件完成: {temp_filepath}")

    print("\n[SUCCESS] 场景 RAG API 端点端到端连通性测试全部通过！")


def test_scene_crud_with_delete():
    print("\n--- [场景 CRUD 与删除接口测试开始] ---")
    temp_scene_id = "temp-delete-scene-test"
    
    # 1. 确保先删除该场景（防止上次残留）
    client.delete(f"/api/scenes/{temp_scene_id}")
    
    # 2. 创建临时测试场景
    create_payload = {
        "id": temp_scene_id,
        "name": "临时测试场景",
        "description": "用于验证删除场景接口",
        "category": "custom",
        "default_params": {},
        "system_prompt": "You are a test assistant.",
        "greeting_text": "Hi test"
    }
    create_resp = client.post("/api/scenes/", json=create_payload)
    assert create_resp.status_code == 201
    
    # 3. 验证场景已被成功创建且可查询
    get_resp = client.get(f"/api/scenes/{temp_scene_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "临时测试场景"
    
    # 4. 删除场景
    delete_resp = client.delete(f"/api/scenes/{temp_scene_id}")
    assert delete_resp.status_code == 200
    assert "已成功彻底清除" in delete_resp.json()["message"]
    
    # 5. 验证删除后查询返回 404
    get_resp_after = client.get(f"/api/scenes/{temp_scene_id}")
    assert get_resp_after.status_code == 404
    print("[SUCCESS] 场景 CRUD 与删除接口测试通过！")


if __name__ == "__main__":
    try:
        test_scene_rag_endpoints_flow()
        test_scene_crud_with_delete()
    except AssertionError as e:
        print(f"\n[FAIL] 接口测试断言失败: {e}")
        sys.exit(1)
    except Exception as ex:
        print(f"\n[FAIL] 运行过程发生异常: {ex}")
        sys.exit(1)


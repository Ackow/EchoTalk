import os
import sys
import json
import asyncio
from fastapi.testclient import TestClient

# 将 backend 目录添加到 Python 路径中
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app, seed_default_scenes
from app.core.database import get_db, engine, Base
from app.models import User, Scene, DialogueHistory, DialogueTurn

client = TestClient(app)
Base.metadata.create_all(bind=engine)

def test_dialogue_pipeline_and_endpoints():
    print("\n--- [对话交互管道 & API 端点整合测试开始] ---")
    
    db = next(get_db())
    seed_default_scenes(db)
    
    # 1. 确保存在测试用户和练习场景
    test_username = "pipeline_test_user"
    user = db.query(User).filter(User.username == test_username).first()
    if not user:
        user = User(username=test_username)
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"创建测试用户成功, ID: {user.id}")
    else:
        print(f"找到现有测试用户, ID: {user.id}")

    scene_id = "interview"
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    assert scene is not None, f"数据库中必须存在场景: {scene_id}"
    print(f"确认场景存在: {scene.name}")

    # 2. 调用 /api/dialogues/start 启动练习会话
    print("\n[步骤 1] 调用 /api/dialogues/start 创建会话历史记录...")
    start_payload = {
        "user_id": user.id,
        "scene_id": scene_id
    }
    start_resp = client.post("/api/dialogues/start", json=start_payload)
    assert start_resp.status_code == 201, f"启动会话失败: {start_resp.text}"
    history_data = start_resp.json()
    history_id = history_data["id"]
    print(f"会话创建成功! 会话 ID: {history_id}")
    
    # 3. 准备待测试的 16k WAV 真实音频文件
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    audio_path = os.path.join(tests_dir, "data", "hello.wav")
    assert os.path.exists(audio_path), f"测试音频 hello.wav 未找到: {audio_path}"
    print(f"测试音频文件就绪: {audio_path}，大小: {os.path.getsize(audio_path)} 字节")

    # 4. 调用 /api/dialogues/{history_id}/turn?stream=true 上传音频并运行流式 Pipeline
    print(f"\n[步骤 2] 调用 /api/dialogues/{history_id}/turn?stream=true 发送音频并执行流式 Pipeline...")
    with open(audio_path, "rb") as f:
        turn_resp = client.post(
            f"/api/dialogues/{history_id}/turn?stream=true",
            files={"file": ("hello.wav", f, "audio/wav")}
        )
        
    assert turn_resp.status_code == 200, f"流式交互 Turn 运行失败: {turn_resp.text}"
    
    # 解析 SSE 事件
    events = []
    for line in turn_resp.iter_lines():
        if not line:
            continue
        line_str = line.decode("utf-8") if isinstance(line, bytes) else line
        if line_str.startswith("data: "):
            event_data = json.loads(line_str[6:])
            events.append(event_data)
            print(f"  [SSE Event] status: {event_data.get('status')}, message/text: {event_data.get('message') or event_data.get('text') or '...'}")

    # 校验流式事件状态
    statuses = [e.get("status") for e in events]
    print(f"接收到的流式状态序列: {statuses}")
    assert "asr" in statuses
    assert "asr_done" in statuses
    assert "ise" in statuses
    assert "pii" in statuses
    assert "llm" in statuses
    assert "done" in statuses

    # 获取最终结果
    done_event = [e for e in events if e.get("status") == "done"][0]
    turns_data = done_event["result"]
    assert len(turns_data) == 2, f"应当在 done 状态中返回2个轮次信息 (User & Assistant), 实际返回: {len(turns_data)}"
    
    user_turn = turns_data[0]
    assistant_turn = turns_data[1]
    
    print("\n[交互轮次 1 (User Turn) 校验]")
    print(f"  * 角色 (role)               : {user_turn['role']}")
    print(f"  * 转译文本 (text)           : '{user_turn['text']}'")
    print(f"  * 托管音频 URL (audio_url)  : {user_turn['audio_url']}")
    print(f"  * 发音得分 (pronun_score)  : {user_turn['pronunciation_score']}")
    print(f"  * 语法纠错 (grammar_correct): {user_turn['grammar_correction']}")
    
    assert user_turn["role"] == "user"
    assert len(user_turn["text"]) > 0
    assert user_turn["audio_url"] is not None
    assert user_turn["pronunciation_score"] is not None
    assert "total_score" in user_turn["pronunciation_score"]
    assert user_turn["grammar_correction"] is not None
    
    print("\n[交互轮次 2 (Assistant Turn) 校验]")
    print(f"  * 角色 (role)               : {assistant_turn['role']}")
    print(f"  * 回复文本 (text)           : '{assistant_turn['text']}'")
    print(f"  * 托管音频 URL (audio_url)  : {assistant_turn['audio_url']}")
    
    assert assistant_turn["role"] == "assistant"
    assert len(assistant_turn["text"]) > 0
    assert assistant_turn["audio_url"] is not None

    # 5. 调用 /api/dialogues/{history_id}/settle 进行会话结算
    print(f"\n[步骤 3] 调用 /api/dialogues/{history_id}/settle 执行结算逻辑...")
    settle_resp = client.post(f"/api/dialogues/{history_id}/settle")
    assert settle_resp.status_code == 200, f"结算失败: {settle_resp.text}"
    settle_data = settle_resp.json()
    
    print(f"  * 综合评分 (overall_score): {settle_data['overall_score']}")
    print(f"  * 结束时间 (end_time)     : {settle_data['end_time']}")
    
    assert settle_data["overall_score"] is not None
    assert float(settle_data["overall_score"]) > 0
    assert settle_data["end_time"] is not None

    # 6. 清理生成的测试数据以防止污染数据库
    print("\n[清理步骤] 删除测试生成的 dialogue turn 和 history 记录...")
    db.query(DialogueTurn).filter(DialogueTurn.dialogue_history_id == history_id).delete()
    db.query(DialogueHistory).filter(DialogueHistory.id == history_id).delete()
    db.commit()
    db.close()
    
    print("\n[SUCCESS] 对话管道与 API 接口端到端整合测试全部通过！")

if __name__ == "__main__":
    try:
        test_dialogue_pipeline_and_endpoints()
    except AssertionError as e:
        print(f"\n[FAIL] 断言校验失败: {e}")
        sys.exit(1)
    except Exception as ex:
        print(f"\n[FAIL] 运行发生异常: {ex}")
        sys.exit(1)

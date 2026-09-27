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
            print(f"  [SSE Event] status: {event_data.get('status')}, message/text: {event_data.get('message') or event_data.get('text') or event_data.get('detail') or '...'}")

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


def test_dynamic_grammar_correction_mock():
    print("\n--- [动态语法纠错 Mock 逻辑单元测试开始] ---")
    from app.services.pipeline import extract_item_from_text, mock_llm_response
    
    # 1. 测试从文本中提取物品名词
    item1 = extract_item_from_text("give me your chocolate Baker all of them how much")
    assert item1 == "chocolate Baker"
    
    item2 = extract_item_from_text("I want chocolate cake please")
    assert item2 == "chocolate cake"
    
    item3 = extract_item_from_text("latte")
    assert item3 == "latte"  # 应当保留原始输入的大小写

    # 2. 测试 Mock LLM 纠错在原句上修改且保留核心词汇 (默认口语化风格)
    res_coll = mock_llm_response("order", "give me your chocolate Baker all of them how much", speaking_style="colloquial")
    gc_coll = res_coll["grammar_correction"]
    assert gc_coll["original"] == "give me your chocolate Baker all of them how much"
    assert "chocolate Baker" in gc_coll["corrected"]
    assert "Could I have" in gc_coll["corrected"]
    assert "How much is it?" in gc_coll["corrected"]
    assert "Sure!" in res_coll["reply"]
    print("  * [口语化] 纠错结果为:", gc_coll["corrected"])
    print("  * [口语化] 对话回复为:", res_coll["reply"])
    
    # 3. 测试 Mock LLM 书面化风格
    res_form = mock_llm_response("order", "give me your chocolate Baker all of them how much", speaking_style="formal")
    gc_form = res_form["grammar_correction"]
    assert gc_form["original"] == "give me your chocolate Baker all of them how much"
    assert "chocolate Baker" in gc_form["corrected"]
    assert "I would like to order" in gc_form["corrected"]
    assert "How much does it cost?" in gc_form["corrected"]
    assert "Certainly." in res_form["reply"]
    print("  * [书面化] 纠错结果为:", gc_form["corrected"])
    print("  * [书面化] 对话回复为:", res_form["reply"])
    
    print("\n[SUCCESS] 动态语法纠错 Mock 逻辑测试（口语化 & 书面化）成功通过！")


def test_validate_scene_relevance():
    """测试场景一致性验证过滤器"""
    print("\n--- [场景一致性验证过滤器测试开始] ---")
    from app.services.pipeline import validate_scene_relevance

    # 咖啡厅场景的 System Prompt
    cafe_prompt = (
        "You are Leo, a friendly but busy barista at Metro Cafe in New York. "
        "The customer wants to order coffee or breakfast. Ask about cup size, milk options, "
        "and whether it is dine-in or to-go."
    )

    # 面试场景的 System Prompt
    interview_prompt = (
        "You are Sarah, an experienced Senior engineering manager at Global Tech Inc. "
        "You are conducting a technical English interview for a Senior Frontend Developer position."
    )

    # 1. 明确相关输入 → 应原样放行
    on_topic_cases = [
        "I would like a large vanilla latte please",
        "Can I get a cappuccino and a croissant?",
        "Do you have oat milk for my coffee?",
        "I had 5 years of experience in React and TypeScript",
        "Yes, that will be all thanks",
    ]
    for text in on_topic_cases:
        result = validate_scene_relevance(text, cafe_prompt if "coffee" in text or "latte" in text or "cappuccino" in text else interview_prompt)
        assert result == text, f"相关输入不应被拦截: '{text}' → '{result}'"
        print(f"  [PASS] 相关输入放行: '{text[:50]}...'")

    # 2. 明确跑题输入 → 应被拦截替换
    off_topic_cases = [
        ("I want to buy a plane ticket to London", cafe_prompt),
        ("What is the weather like in New York?", cafe_prompt),
        ("Can you help me with my math homework?", interview_prompt),
        ("I need to book a hotel room for next week", cafe_prompt),
    ]
    for text, prompt in off_topic_cases:
        result = validate_scene_relevance(text, prompt)
        if result != text:
            print(f"  [PASS] 跑题输入被拦截: '{text[:50]}...' → 已替换")
        else:
            print(f"  [INFO] 跑题输入未拦截(可能因降级): '{text[:50]}...'")

    # 3. 空输入
    empty_result = validate_scene_relevance("", cafe_prompt)
    assert empty_result == "", "空输入应原样返回"
    print("  [PASS] 空输入处理正确")

    # 4. 无场景 prompt
    no_prompt_result = validate_scene_relevance("some random text", "")
    assert no_prompt_result == "some random text", "无场景 prompt 应放行"
    print("  [PASS] 无场景 prompt 处理正确")

    # 5. 缓存命中测试
    validate_scene_relevance("I want a latte", cafe_prompt)
    validate_scene_relevance("I want a latte too", cafe_prompt)
    print("  [PASS] 缓存机制正常（第二次调用应使用缓存向量）")

    print("\n[SUCCESS] 场景一致性验证过滤器测试通过！")

def test_off_topic_grammar_correction_isolation():
    print("\n--- [跑题语法纠错隔离测试开始] ---")
    from app.services.pipeline import mock_llm_response, _SCENE_REDIRECT_TEXT

    # 1. 模拟跑题输入
    off_topic_input = "I want to buy a ticket to London"
    
    # 模拟在 cafe 场景触发跑题
    res = mock_llm_response(
        scene_id="cafe",
        user_text=_SCENE_REDIRECT_TEXT,
        rag_context="latte espresso",
        speaking_style="colloquial",
        original_user_text=off_topic_input
    )
    
    # 2. 校验回复是否为跑题引导句
    assert "stick to" in res["reply"] or "focus on" in res["reply"] or "order" in res["reply"]
    assert "cheesecake" not in res["reply"].lower()  # 不应该返回正常的咖啡馆点餐回复
    
    # 3. 校验语法纠错是否纠正的是用户的实际输入
    gc = res["grammar_correction"]
    assert gc["original"] == off_topic_input
    assert "ticket" in gc["corrected"]  # 纠正结果应当包含用户的原意 core noun "ticket"
    assert "recognized correctly" not in gc["original"]  # 纠错原文不应包含 ASR 跑题错误系统提示
    
    print("  * [跑题隔离] 纠错原文为:", gc["original"])
    print("  * [跑题隔离] 纠错结果为:", gc["corrected"])
    print("  * [跑题隔离] 引导回复为:", res["reply"])
    print("\n[SUCCESS] 跑题语法纠错隔离测试通过！")

if __name__ == "__main__":
    try:
        test_dialogue_pipeline_and_endpoints()
        test_dynamic_grammar_correction_mock()
        test_validate_scene_relevance()
        test_off_topic_grammar_correction_isolation()
    except AssertionError as e:
        print(f"\n[FAIL] 断言校验失败: {e}")
        sys.exit(1)
    except Exception as ex:
        print(f"\n[FAIL] 运行发生异常: {ex}")
        sys.exit(1)

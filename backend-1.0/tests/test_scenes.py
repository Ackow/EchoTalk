import os
import sys

# 将 backend 目录添加到 Python 路径中
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scenes.loader import load_scenes, get_scene, CustomScene

def test_default_scenes_loading():
    """
    测试 1：验证是否能正确加载出系统内置的 3 个默认场景
    """
    scenes = load_scenes()
    print("\n--- [测试 1: 场景加载] ---")
    print(f"当前已加载场景列表: {list(scenes.keys())}")
    assert "interview" in scenes
    assert "ordering" in scenes
    assert "meeting" in scenes
    print("测试 1 通关：内置场景全部加载成功！\n")

def test_prompt_rendering():
    """
    测试 2：验证系统提示词模板是否能够根据自定义参数正确渲染
    """
    print("\n--- [测试 2: 提示词渲染] ---")
    interview = get_scene("interview")
    
    # 默认渲染
    default_prompt = interview.get_system_prompt()
    print(f"Sarah 默认 Prompt (前80字): {default_prompt[:80]}...")
    assert "Sarah" in default_prompt
    assert "Senior Frontend Developer" in default_prompt

    # 传入自定义参数渲染
    custom_params = {
        "interviewer_name": "Tony",
        "job_title": "Python Architect"
    }
    custom_prompt = interview.get_system_prompt(custom_params)
    print(f"Tony 渲染后的 Prompt (前80字): {custom_prompt[:80]}...")
    assert "Tony" in custom_prompt
    assert "Python Architect" in custom_prompt
    print("测试 2 通关：自定义参数动态格式化成功！\n")

def test_greetings():
    """
    测试 3：验证欢迎语（Greeting）生成
    """
    print("\n--- [测试 3: 欢迎语测试] ---")
    ordering = get_scene("ordering")
    greeting = ordering.get_greeting()
    print(f"咖啡点单欢迎语: {greeting}")
    assert "Metro Cafe" in greeting
    
    custom_greeting = ordering.get_greeting({"store_name": "Starbucks"})
    print(f"星巴克点单欢迎语: {custom_greeting}")
    assert "Starbucks" in custom_greeting
    print("测试 3 通关：开场欢迎语渲染成功！\n")

def test_validation_hooks():
    """
    测试 4：验证对话拦截校验逻辑（validate_turn）
    """
    print("\n--- [测试 4: 拦截校验测试] ---")
    interview = get_scene("interview")
    
    # 正常英文输入测试
    res_ok = interview.validate_turn("I have five years of experience in JavaScript development.")
    assert res_ok["is_valid"] is True
    assert res_ok["warning"] == ""
    
    # 中文汉字敏感测试
    res_zh = interview.validate_turn("你好，我是来面试前端工程师的。")
    print(f"输入中文校验反馈: {res_zh['warning']}")
    assert "Sarah 仅支持英文交流" in res_zh["warning"]
    
    # 输入过短测试
    res_short = interview.validate_turn("hi")
    print(f"输入过短校验反馈: {res_short['warning']}")
    assert "您的回答非常简短" in res_short["warning"]
    print("测试 4 通关：中文字符检测与过短保护逻辑运行正常！\n")

def test_custom_database_scene():
    """
    测试 5：验证自定义场景的实例化与合并
    """
    print("\n--- [测试 5: 自定义数据库场景实例化] ---")
    # 模拟用户创建的口语场景
    custom = CustomScene(
        scene_id="hotel_checkin",
        name="酒店办理入住",
        description="模拟前台办理登记入住和房间咨询",
        category="daily",
        default_params={
            "character_name": "Emily",
            "hotel_name": "Hilton Hotel",
            "greeting_template": "Welcome to {hotel_name}! I am {character_name}. How can I assist you with your booking?"
        },
        system_prompt="You are {character_name} at the reception of {hotel_name}..."
    )
    
    greeting = custom.get_greeting()
    print(f"自定义场景首句欢迎语: {greeting}")
    assert "Hilton Hotel" in greeting
    assert "Emily" in greeting
    print("测试 5 通关：自定义数据库场景类工作符合预期！\n")

if __name__ == "__main__":
    # 执行测试套件
    try:
        test_default_scenes_loading()
        test_prompt_rendering()
        test_greetings()
        test_validation_hooks()
        test_custom_database_scene()
        print("[SUCCESS] 所有场景插件和加载器功能测试全部通过 (5/5)！")
    except AssertionError as e:
        print(f"[FAIL] 测试失败: {e}")
        sys.exit(1)

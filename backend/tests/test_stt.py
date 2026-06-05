import os
import sys

# 将 backend 目录添加到 Python 路径中
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.stt import speech_to_text
import app.services.stt as stt

def test_stt_fallback_flow():
    print("\n--- [百度 ASR (STT) 本地 Mock 与降级测试] ---")
    
    # 1. 模拟一个非存在的音频路径，验证报错与文件名匹配 Mock 逻辑
    fake_audio_interview = "tests/data/interview_mock.wav"
    res_interview = speech_to_text(fake_audio_interview)
    print(f"  * 文件名带有 'interview' 的降级结果: '{res_interview}'")
    assert "developer job interview" in res_interview

    # 2. 模拟点餐场景文件名 Mock 逻辑
    fake_audio_order = "tests/data/cafe_order.wav"
    res_order = speech_to_text(fake_audio_order)
    print(f"  * 文件名带有 'cafe' 的降级结果     : '{res_order}'")
    assert "vanilla latte" in res_order

    # 3. 验证通过全局变量 _mock_override_text 进行强行指定的逻辑 (用于管道联合测试)
    expected_text = "Override ASR transcription result successfully."
    stt._mock_override_text = expected_text
    
    res_override = speech_to_text(fake_audio_interview)
    print(f"  * 手动设定 Override 后的识别结果    : '{res_override}'")
    assert res_override == expected_text
    
    # 重置测试状态，防止干扰其他用例
    stt._mock_override_text = None
    
    print("\n[SUCCESS] 百度 ASR 服务本地降级与控制测试全部通过！")


def test_user_hello_audio():
    paths_to_check = [
        "tests/data/hello.wav",
    ]
    user_audio = None
    for p in paths_to_check:
        if os.path.exists(p):
            user_audio = p
            break

    if user_audio:
        print(f"\n--- [用户真实录音 {user_audio} 识别测试开始 >>>] ---")
        result = speech_to_text(user_audio)
        print(f"  * 百度 ASR 真实转译文字: '{result}'")
        print(f"---------------------------------------------\n")
    else:
        print("\n(提示 💡: 如果你想直接在测试中识别你录制的音频，可以将录音文件命名为 'hello.wav' 并放入 backend/data 目录下，脚本会自动检测并执行真实转译。)\n")


if __name__ == "__main__":
    try:
        test_stt_fallback_flow()
        test_user_hello_audio()
    except AssertionError as e:
        print(f"\n[FAIL] 断言失败: {e}")
        sys.exit(1)
    except Exception as ex:
        print(f"\n[FAIL] 发生异常: {ex}")
        sys.exit(1)

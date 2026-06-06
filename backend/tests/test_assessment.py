import os
import sys

# 将 backend 目录添加到 Python 路径中
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from app.core.config import settings
from app.services.assessment import (
    assess_pronunciation, 
    assess_pronunciation_sync,
    _parse_xfyun_xml
)

def test_xml_parsing_and_normalization():
    print("\n--- [1. 科大讯飞 XML 结果解析与归一化测试] ---")
    
    # 模拟 5 分制返回的 XML 文本，属性可能存在于 read_sentence 节点下
    five_point_xml = (
        '<xml_report>'
        '  <read_sentence total_score="4.1" accuracy_score="4.5" fluency_score="3.8" integrity_score="4.0" />'
        '</xml_report>'
    )
    
    # 解析并验证 5 分制自动放大 20 倍
    scores_5 = _parse_xfyun_xml(five_point_xml)
    print(f"  * 5 分制输入解析归一化结果: {scores_5}")
    assert scores_5["total_score"] == 82.0
    assert scores_5["accuracy_score"] == 90.0
    assert scores_5["fluency_score"] == 76.0
    assert scores_5["integrity_score"] == 80.0
    print("  * [OK] 5 分制缩放验证通过！")
    
    # 模拟百分制返回的 XML 文本
    hundred_point_xml = (
        '<xml_report>'
        '  <read_sentence total_score="87.5" accuracy_score="92.0" fluency_score="84.0" integrity_score="90.0" />'
        '</xml_report>'
    )
    
    # 解析并验证百分制保持不变
    scores_100 = _parse_xfyun_xml(hundred_point_xml)
    print(f"  * 百分制输入解析归一化结果: {scores_100}")
    assert scores_100["total_score"] == 87.5
    assert scores_100["accuracy_score"] == 92.0
    assert scores_100["fluency_score"] == 84.0
    assert scores_100["integrity_score"] == 90.0
    print("  * [OK] 百分制直通验证通过！")


def test_mock_fallback_scoring():
    print("\n--- [2. 本地离线 Mock 打分机制与自适应检验测试] ---")
    
    ref_text_1 = "This is a simple english sentence for oral testing."
    # 异步接口调用（因为未配置科大讯飞凭证，应该无缝安全降级至本地 Mock 打分器）
    scores_1 = asyncio.run(assess_pronunciation("tests/data/not_exist.wav", ref_text_1))
    print(f"  * 文本 1 评估分值结果: {scores_1}")
    
    # 验证各项分值均合法落在百分制 60~100 区间内
    for k in ["total_score", "accuracy_score", "fluency_score", "integrity_score"]:
        v = scores_1[k]
        assert 60.0 <= v <= 100.0
        
    # 测试“输入确定、分值确定”的幂等性（由于 hash 打分逻辑，确保单元测试是确定可重复的）
    scores_1_dup = asyncio.run(assess_pronunciation("tests/data/not_exist.wav", ref_text_1))
    assert scores_1["total_score"] == scores_1_dup["total_score"]
    assert scores_1["accuracy_score"] == scores_1_dup["accuracy_score"]
    print("  * [OK] 评估分值合法区间与计算幂等性验证通过！")

    # 输入不同的文本，应该产生不同的分数
    ref_text_2 = "A completely different reference sentence to verify hash variation."
    scores_2 = asyncio.run(assess_pronunciation("tests/data/not_exist.wav", ref_text_2))
    print(f"  * 文本 2 评估分值结果: {scores_2}")
    assert scores_1["total_score"] != scores_2["total_score"]
    print("  * [OK] 文本差异分值浮动验证通过！")


def test_real_audio_assessment():
    print("\n--- [3. 真实音频发音评估兼容测试 >>>] ---")
    
    # 确定 tests 文件夹物理路径并定位默认音频
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    audio_path = os.path.join(tests_dir, "data", "hello.wav")
    reference_text = "hello, my name is icecola"
    
    # 再次检查音频文件是否存在。如果不存在，跳过
    if not os.path.exists(audio_path):
        print(f"  * [SKIP] 音频文件不存在，跳过该项真实评估测试: '{audio_path}'")
        return
        
    print(f"  * 评估目标音频  : '{audio_path}'")
    print(f"  * 评测参考文本  : '{reference_text}'")

    # 执行发音评估
    try:
        # 即使无 Key，也会安全激活本地 Mock 降级并成功返回分值，这应该能全链路跑通
        scores = assess_pronunciation_sync(audio_path, reference_text)
        print(f"  * 评估得分结果  : {scores}")
        assert "total_score" in scores
        assert scores["total_score"] > 0
        print("  * [OK] 真实音频发音评估通过！")
    except Exception as e:
        print(f"  * [FAIL] 评估运行异常: {e}")
        assert False, f"发音评估运行异常: {e}"


if __name__ == "__main__":
    try:
        test_xml_parsing_and_normalization()
        test_mock_fallback_scoring()
        test_real_audio_assessment()
        print("\n=============================================")
        print(" [SUCCESS] 科大讯飞发音评测组件单元测试全部通过！ ")
        print("=============================================\n")
    except AssertionError as e:
        print(f"\n[FAIL] 断言失败: {e}")
        sys.exit(1)
    except Exception as ex:
        print(f"\n[FAIL] 发生异常: {ex}")
        sys.exit(1)

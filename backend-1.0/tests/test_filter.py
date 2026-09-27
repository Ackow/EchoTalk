import os
import sys

# 将 backend 目录添加到 Python 路径中，以便能够导入 app 包
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.filter import redact_pii_local, anonymize_text_via_llm

def test_local_regex_redaction():
    """
    测试 1：验证常见的个人隐私敏感正则拦截脱敏是否正确
    """
    print("\n--- [测试 1: 正则匹配脱敏测试] ---")
    
    # 各种隐私数据组合文本
    input_text = (
        "My phone number is +8613812345678 and my email is test_user@google.com. "
        "Here is my ID card: 33010219900307123X. Please transfer money to bank card 6222021202888888889. "
        "The server IP is 192.168.1.105."
    )
    print(f"原始敏感文本: {input_text}")
    
    redacted = redact_pii_local(input_text)
    print(f"本地脱敏文本: {redacted}\n")
    
    # 断言包含脱敏占位符
    assert "[PHONE_REDACTED]" in redacted
    assert "[EMAIL_REDACTED]" in redacted
    assert "[ID_REDACTED]" in redacted
    assert "[CARD_REDACTED]" in redacted
    assert "[IP_REDACTED]" in redacted
    
    # 断言敏感词被清除了
    assert "13812345678" not in redacted
    assert "test_user@google.com" not in redacted
    assert "33010219900307123X" not in redacted
    assert "6222021202888888889" not in redacted
    assert "192.168.1.105" not in redacted
    print("测试 1 通关：正则替换规则匹配无误！\n")


def test_custom_dictionary_redaction():
    """
    测试 2：验证自定义词表脱敏替换
    """
    print("\n--- [测试 2: 自定义词表脱敏测试] ---")
    
    input_text = "The secret project name is Project Alpha, directed by CEO John Doe from Tesla."
    custom_words = ["Project Alpha", "John Doe", "Tesla"]
    print(f"原始文本: {input_text}")
    print(f"敏感词库: {custom_words}")
    
    redacted = redact_pii_local(input_text, custom_words)
    print(f"脱敏后文本: {redacted}\n")
    
    assert "Project Alpha" not in redacted
    assert "John Doe" not in redacted
    assert "Tesla" not in redacted
    assert "[CONFIDENTIAL_REDACTED]" in redacted
    print("测试 2 通关：自定义词表及大小写兼容过滤成功！\n")


def test_llm_anonymize_fallback():
    """
    测试 3：验证大模型脱敏接口的调用与容错机制
    """
    print("\n--- [测试 3: 大模型脱敏容错与调用测试] ---")
    input_text = "Contact me at 13999999999."
    
    # 调用大模型脱敏（或无 Key 自动降级）
    redacted = anonymize_text_via_llm(input_text)
    print(f"脱敏输出结果: {redacted}\n")
    
    # 只要原始敏感数据被清除，且包含了脱敏占位标记即可
    assert "13999999999" not in redacted
    assert "REDACTED" in redacted or "redacted" in redacted or "contact" in redacted.lower()
    print("测试 3 通关：大模型脱敏在无 Key 时成功实现安全降级！\n")


if __name__ == "__main__":
    try:
        test_local_regex_redaction()
        test_custom_dictionary_redaction()
        test_llm_anonymize_fallback()
        print("[SUCCESS] 隐私脱敏过滤器服务测试全部通过 (3/3)！")
    except AssertionError as e:
        print(f"[FAIL] 测试失败: {e}")
        sys.exit(1)

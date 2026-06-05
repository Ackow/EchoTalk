import re
from typing import List, Optional
from openai import OpenAI
from app.core.config import settings
from app.core.logger import log_api_call

# --- 常用个人隐私信息 (PII) 正则表达式定义 ---
# 1. 手机号码 (中国大陆11位手机号及国际标准格式格式化)
PHONE_PATTERN = r'\b(?:\+?86)?1[3-9]\d{9}\b|\b\d{3}-\d{8}\b|\b\d{4}-\d{7}\b'

# 2. 电子邮箱
EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

# 3. 身份证号 (18位大陆身份证，包含尾部校验位 X/x)
ID_CARD_PATTERN = r'\b\d{15}\b|\b\d{17}[\dXx]\b'

# 4. 银行卡/信用卡号 (16 至 19 位连续数字)
CARD_PATTERN = r'\b\d{16,19}\b'

# 5. IPv4 地址
IP_PATTERN = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'


def redact_pii_local(text: str, custom_words: Optional[List[str]] = None) -> str:
    """
    使用高效的本地规则匹配，对文本中的敏感隐私数据进行秒级过滤脱敏。
    支持屏蔽：手机号、邮箱、身份证、银行卡、IP 地址，以及传入的自定义词表（如人名、公司机密项目名等）。
    """
    if not text:
        return text

    # 1. 执行正则替换
    text = re.sub(PHONE_PATTERN, "[PHONE_REDACTED]", text)
    text = re.sub(EMAIL_PATTERN, "[EMAIL_REDACTED]", text)
    text = re.sub(ID_CARD_PATTERN, "[ID_REDACTED]", text)
    text = re.sub(CARD_PATTERN, "[CARD_REDACTED]", text)
    text = re.sub(IP_PATTERN, "[IP_REDACTED]", text)

    # 2. 自定义敏感词表匹配（不区分大小写）
    if custom_words:
        for word in custom_words:
            if not word.strip():
                continue
            # 构建不区分大小写的正则，对敏感词进行精准脱敏
            escaped_word = re.escape(word.strip())
            pattern = re.compile(rf'\b{escaped_word}\b', re.IGNORECASE)
            text = pattern.sub("[CONFIDENTIAL_REDACTED]", text)
            
            # 兼容中文或非英文字符边界
            if not re.match(r'^[A-Za-z0-9_]+$', word):
                text = text.replace(word, "[CONFIDENTIAL_REDACTED]")

    return text


def anonymize_text_via_llm(text: str) -> str:
    """
    调用大语言模型（LLM）进行智能语义级别的脱敏拦截。
    自适应支持 DeepSeek (deepseek-chat)、小米 MiMo 或 OpenAI。
    如果未配置任何大模型 API Key，程序将自动安全降级，仅执行本地规则脱敏。
    """
    if not text:
        return text

    # 按照优先级动态匹配用户配置的密钥，支持热插拔切换
    api_key = None
    base_url = None
    model_name = None
    provider_name = ""
    
    if settings.DEEPSEEK_API_KEY:
        api_key = settings.DEEPSEEK_API_KEY
        base_url = settings.DEEPSEEK_BASE_URL
        model_name = settings.DEEPSEEK_MODEL
        provider_name = "DeepSeek"
    elif settings.XIAOMI_API_KEY:
        api_key = settings.XIAOMI_API_KEY
        base_url = settings.XIAOMI_BASE_URL
        model_name = settings.XIAOMI_MODEL
        provider_name = "Xiaomi MiMo"
    elif settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "mock-key":
        api_key = settings.OPENAI_API_KEY
        base_url = settings.OPENAI_BASE_URL
        model_name = settings.OPENAI_MODEL
        provider_name = "OpenAI"

    has_credentials = bool(api_key)

    if not has_credentials:
        log_api_call(
            api_type="大语言模型 (LLM)",
            provider="本地离线引擎",
            url="None (Offline)",
            model="None",
            action="智能脱敏过滤 (anonymize_text_via_llm)",
            status="success",
            extra_info="未配置有效大模型密钥，已安全降级为本地规则脱敏（正则/自定义词表）。"
        )
        return redact_pii_local(text)

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        log_api_call(
            api_type="大语言模型 (LLM)",
            provider=provider_name,
            url=base_url,
            model=model_name,
            action="智能脱敏过滤 (anonymize_text_via_llm)",
            status="pending"
        )
        
        system_prompt = (
            "You are a data privacy protection assistant. Your job is to anonymize and redact "
            "any personally identifiable information (PII) or confidential corporate secrets "
            "from the input text. Replace names with [NAME_REDACTED], company names with [COMPANY_REDACTED], "
            "specific project names with [PROJECT_REDACTED], and financial data with [FINANCIAL_REDACTED]. "
            "Keep the rest of the text unchanged and preserve the original language. Do not output anything other than the sanitized text."
        )

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.0, # 保证输出的确定性
            max_tokens=1000
        )
        
        sanitized_text = response.choices[0].message.content.strip()
        log_api_call(
            api_type="大语言模型 (LLM)",
            provider=provider_name,
            url=base_url,
            model=model_name,
            action="智能脱敏过滤 (anonymize_text_via_llm)",
            status="success",
            extra_info=f"脱敏后文本前 40 字: {sanitized_text[:40]}..."
        )
        return sanitized_text

    except Exception as e:
        log_api_call(
            api_type="大语言模型 (LLM)",
            provider=provider_name,
            url=base_url,
            model=model_name,
            action="智能脱敏过滤 (anonymize_text_via_llm)",
            status="failed",
            extra_info=str(e)
        )
        return redact_pii_local(text)

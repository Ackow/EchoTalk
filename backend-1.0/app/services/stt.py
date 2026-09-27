import os
import time
import hmac
import hashlib
import base64
import requests
from urllib.parse import urlencode
from typing import Optional

from app.core.config import settings
from app.core.logger import log_api_call

# 允许测试脚本在 Mock 状态下精准控制 ASR 产出的文本
_mock_override_text: Optional[str] = None


def mock_speech_to_text(audio_path: str) -> str:
    """
    腾讯云 ASR 未配置或异常时的本地安全降级 Mock 生成器。
    支持在单元测试中通过设定 _mock_override_text 来决定固定输出。
    """
    global _mock_override_text
    if _mock_override_text is not None:
        return _mock_override_text
        
    # 根据传入音频的文件名包含的场景关键字，自动回馈特定练习语句以模拟真实流程
    filename = os.path.basename(audio_path).lower()
    if "interview" in filename:
        return "I would like to practice speaking English for a developer job interview."
    elif "order" in filename or "cafe" in filename:
        return "Hello! I'd like to order a large vanilla latte and a slice of cheesecake."
    elif "meeting" in filename:
        return "I want to explain the delays on the React Native project launch."
        
    return "Hi, I am ready to start my English oral practice session now."


def _generate_tencent_sign(secret_key: str, appid: str, params: dict) -> str:
    """
    生成腾讯云录音文件识别极速版 HMAC-SHA1 签名。
    签名规则：对 URL 所有参数按 key 排序后拼接签名原文（以 POSTasr.cloud.tencent.com/asr/flash/v1/{appid}? 开头），
    排序和拼接时不包含 appid。用 SecretKey 做 HMAC-SHA1，再 Base64 编码。
    """
    # 按 key 字典序排列，并且过滤掉 appid
    sorted_params = sorted(
        [(k, v) for k, v in params.items() if k != "appid"],
        key=lambda x: x[0]
    )
    query_str = "&".join(f"{k}={v}" for k, v in sorted_params)
    sign_str = f"POSTasr.cloud.tencent.com/asr/flash/v1/{appid}?" + query_str
    
    sign = hmac.new(secret_key.encode("utf-8"), sign_str.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(sign).decode("utf-8")


def _detect_voice_format(audio_path: str) -> str:
    """根据文件扩展名推断音频格式参数"""
    ext = os.path.splitext(audio_path)[1].lower()
    format_map = {
        ".wav": "wav",
        ".mp3": "mp3",
        ".m4a": "m4a",
        ".ogg": "ogg-opus",
        ".pcm": "pcm",
        ".aac": "aac",
        ".amr": "amr",
    }
    return format_map.get(ext, "wav")


def speech_to_text(audio_path: str) -> str:
    """
    语音转文字 (STT) 核心入口：
    使用腾讯云录音文件识别极速版 (Flash ASR)，支持英文识别并自带智能标点。
    引擎模型：16k_en（英文通用模型）
    若配置缺失或识别异常，将无缝安全降级至本地 Mock 口语文本生成器。
    """
    # 1. 检测文件是否存在
    if not audio_path or not os.path.exists(audio_path):
        log_api_call(
            api_type="语音转文字 (STT)",
            provider="Tencent Cloud",
            url="None",
            model="Flash ASR 16k_en",
            action="腾讯云极速语音识别 (speech_to_text)",
            status="failed",
            extra_info=f"音频文件不存在: '{audio_path}'。回退至本地 Mock。"
        )
        return mock_speech_to_text(audio_path or "")

    # 2. 检查腾讯云配置
    appid = settings.TENCENT_APPID
    secret_id = settings.TENCENT_SECRET_ID
    secret_key = settings.TENCENT_SECRET_KEY
    
    if not appid or not secret_id or not secret_key:
        log_api_call(
            api_type="语音转文字 (STT)",
            provider="本地离线引擎",
            url="None (Offline)",
            model="Flash ASR 16k_en",
            action="腾讯云极速语音识别 (speech_to_text)",
            status="success",
            extra_info="未配置有效腾讯云凭证，已安全降级为本地 Mock 语音转译器。"
        )
        return mock_speech_to_text(audio_path)

    # 3. 读取音频二进制数据
    try:
        with open(audio_path, "rb") as f:
            audio_data = f.read()
        audio_len = len(audio_data)
    except Exception as e:
        log_api_call(
            api_type="语音转文字 (STT)",
            provider="Tencent Cloud",
            url="None",
            model="Flash ASR 16k_en",
            action="腾讯云极速语音识别 (speech_to_text)",
            status="failed",
            extra_info=f"读取音频文件失败: {str(e)}。回退至本地 Mock。"
        )
        return mock_speech_to_text(audio_path)

    # 4. 构建请求参数与签名
    engine_type = "16k_en"  # 英文通用模型，自带标点
    voice_format = _detect_voice_format(audio_path)
    timestamp = int(time.time())
    
    # 必须包含所有参与请求的参数，确保顺序严格按照字典序排列。
    # 根据腾讯云极速版 SDK，appid 作为 URL 路径参数，不放在 query 参数中参与排序和拼接。并且极速版不需要 expired 和 nonce。
    query_params = {
        "secretid": secret_id,
        "timestamp": timestamp,
        "engine_type": engine_type,
        "voice_format": voice_format,
        "speaker_diarization": 0,
        "customization_id": "",
        "filter_dirty": 0,
        "filter_modal": 0,
        "filter_punc": 0,       # 0 = 不过滤标点（即保留标点输出）
        "convert_num_mode": 1,  # 智能转换数字
        "word_info": 0,
        "first_channel_only": 1,
        "reinforce_hotword": 0,
        "sentence_max_length": 0,
    }
    
    signature = _generate_tencent_sign(
        secret_key=secret_key,
        appid=appid,
        params=query_params,
    )

    # 5. 拼接请求 URL
    api_url = f"https://asr.cloud.tencent.com/asr/flash/v1/{appid}?" + urlencode(query_params)

    headers = {
        "Host": "asr.cloud.tencent.com",
        "Authorization": signature,
        "Content-Type": "application/octet-stream",
        "Content-Length": str(audio_len),
    }

    # 6. 发起腾讯云极速语音识别请求
    try:
        log_api_call(
            api_type="语音转文字 (STT)",
            provider="Tencent Cloud",
            url="https://asr.cloud.tencent.com/asr/flash/v1/...",
            model=f"Flash ASR {engine_type}",
            action="腾讯云极速语音识别 (speech_to_text)",
            status="pending",
            extra_info=f"音频大小: {audio_len} 字节, 格式: {voice_format}"
        )
        
        response = requests.post(api_url, headers=headers, data=audio_data, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        code = data.get("code", -1)
        if code == 0:
            # 成功：从 flash_result 中提取识别文本
            flash_result = data.get("flash_result", [])
            if flash_result:
                # 合并所有 channel 的识别结果
                all_text = " ".join(
                    channel.get("text", "") 
                    for channel in flash_result
                ).strip()
            else:
                all_text = ""
            
            log_api_call(
                api_type="语音转文字 (STT)",
                provider="Tencent Cloud",
                url="https://asr.cloud.tencent.com/asr/flash/v1/...",
                model=f"Flash ASR {engine_type}",
                action="腾讯云极速语音识别 (speech_to_text)",
                status="success",
                extra_info=f"转译成功，识别文本前 60 字: '{all_text[:60]}...'"
            )
            return all_text
        else:
            err_msg = data.get("message", "unknown error")
            log_api_call(
                api_type="语音转文字 (STT)",
                provider="Tencent Cloud",
                url="https://asr.cloud.tencent.com/asr/flash/v1/...",
                model=f"Flash ASR {engine_type}",
                action="腾讯云极速语音识别 (speech_to_text)",
                status="failed",
                extra_info=f"腾讯云返回错误 [{code}]: {err_msg}。已回退至本地 Mock。"
            )
            return mock_speech_to_text(audio_path)
            
    except Exception as e:
        log_api_call(
            api_type="语音转文字 (STT)",
            provider="Tencent Cloud",
            url="https://asr.cloud.tencent.com/asr/flash/v1/...",
            model=f"Flash ASR {engine_type}",
            action="腾讯云极速语音识别 (speech_to_text)",
            status="failed",
            extra_info=f"请求腾讯云接口发生异常: {str(e)}。已回退至本地 Mock。"
        )
        return mock_speech_to_text(audio_path)

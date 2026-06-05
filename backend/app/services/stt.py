import os
import time
import base64
import requests
from typing import Optional

from app.core.config import settings
from app.core.logger import log_api_call

# 用于缓存百度的 Access Token，避免频繁请求 OAuth 接口（Token 有效期为 30 天）
_token_cache = {
    "token": None,
    "expires_at": 0
}

# 允许测试脚本在 Mock 状态下精准控制 ASR 产出的文本
_mock_override_text: Optional[str] = None


def get_baidu_token() -> Optional[str]:
    """
    使用 API Key (Client ID) 与 Secret Key (Client Secret) 向百度智能云请求获取 Access Token，并进行内存缓存。
    """
    global _token_cache
    now = time.time()
    
    # 如果缓存的 Token 依然有效，则直接返回
    if _token_cache["token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["token"]

    api_key = settings.BAIDU_API_KEY
    secret_key = settings.BAIDU_SECRET_KEY
    
    # 未配置 Key 时直接返回 None，触发离线降级
    if not api_key or not secret_key:
        return None

    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": api_key,
        "client_secret": secret_key
    }

    try:
        log_api_call(
            api_type="百度授权认证 (OAuth2.0)",
            provider="Baidu Cloud",
            url=url,
            model="None",
            action="获取百度智能云接口调用凭证 (get_baidu_token)",
            status="pending"
        )
        
        response = requests.post(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if "access_token" in data:
            token = data["access_token"]
            expires_in = data.get("expires_in", 2592000) # 默认 30 天
            _token_cache["token"] = token
            _token_cache["expires_at"] = now + expires_in
            
            log_api_call(
                api_type="百度授权认证 (OAuth2.0)",
                provider="Baidu Cloud",
                url=url,
                model="None",
                action="获取百度智能云接口调用凭证 (get_baidu_token)",
                status="success",
                extra_info="成功换取并缓存百度语音 Access Token。"
            )
            return token
        else:
            log_api_call(
                api_type="百度授权认证 (OAuth2.0)",
                provider="Baidu Cloud",
                url=url,
                model="None",
                action="获取百度智能云接口调用凭证 (get_baidu_token)",
                status="failed",
                extra_info=f"返回的响应中不含 access_token: {data}"
            )
            return None
            
    except Exception as e:
        log_api_call(
            api_type="百度授权认证 (OAuth2.0)",
            provider="Baidu Cloud",
            url=url,
            model="None",
            action="获取百度智能云接口调用凭证 (get_baidu_token)",
            status="failed",
            extra_info=f"网络请求错误: {str(e)}"
        )
        return None


def mock_speech_to_text(audio_path: str) -> str:
    """
    百度 ASR 未配置或异常时的本地安全降级 Mock 生成器。
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


def speech_to_text(audio_path: str) -> str:
    """
    语音转文字 (STT) 核心入口：
    接收本地 WAV 音频路径，上传至百度短语音识别标准版服务（dev_pid=1737 纯英文识别模型）。
    若配置缺失或识别异常，将无缝安全降级至本地 Mock 口语文本生成器。
    """
    # 1. 检测文件是否存在
    if not audio_path or not os.path.exists(audio_path):
        log_api_call(
            api_type="语音转文字 (STT)",
            provider="Baidu Cloud",
            url="None",
            model="Baidu ASR English (1737)",
            action="百度英文短语音识别 (speech_to_text)",
            status="failed",
            extra_info=f"音频文件不存在: '{audio_path}'。回退至本地 Mock。"
        )
        return mock_speech_to_text(audio_path or "")

    # 2. 获取百度 Token
    token = get_baidu_token()
    if not token:
        # 无 Token，说明未配置 API Key 或认证请求失败，降级
        log_api_call(
            api_type="语音转文字 (STT)",
            provider="本地离线引擎",
            url="None (Offline)",
            model="Baidu ASR English (1737)",
            action="百度英文短语音识别 (speech_to_text)",
            status="success",
            extra_info="未配置有效百度云凭证，已安全降级为本地 Mock 语音转译器。"
        )
        return mock_speech_to_text(audio_path)

    # 3. 读取音频并 Base64 编码
    try:
        with open(audio_path, "rb") as f:
            audio_data = f.read()
        audio_len = len(audio_data)
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")
    except Exception as e:
        log_api_call(
            api_type="语音转文字 (STT)",
            provider="Baidu Cloud",
            url="None",
            model="Baidu ASR English (1737)",
            action="百度英文短语音识别 (speech_to_text)",
            status="failed",
            extra_info=f"读取音频文件失败: {str(e)}。回退至本地 Mock。"
        )
        return mock_speech_to_text(audio_path)

    # 4. 发起百度短语音识别标准版（英文模型）请求
    api_url = "https://vop.baidu.com/server_api"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "format": "wav",
        "rate": 16000,
        "channel": 1,
        "cuid": "echotalk-desktop-client",
        "token": token,
        "speech": audio_base64,
        "len": audio_len,
        "dev_pid": 1737  # 1737 对应纯英文输入识别模型
    }

    try:
        log_api_call(
            api_type="语音转文字 (STT)",
            provider="Baidu Cloud",
            url=api_url,
            model="Baidu ASR English (1737)",
            action="百度英文短语音识别 (speech_to_text)",
            status="pending",
            extra_info=f"音频大小: {audio_len} 字节"
        )
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        err_no = data.get("err_no", -1)
        if err_no == 0:
            result_list = data.get("result", [])
            transcript = result_list[0] if result_list else ""
            log_api_call(
                api_type="语音转文字 (STT)",
                provider="Baidu Cloud",
                url=api_url,
                model="Baidu ASR English (1737)",
                action="百度英文短语音识别 (speech_to_text)",
                status="success",
                extra_info=f"转译成功，识别文本前 40 字: '{transcript[:40]}...'"
            )
            return transcript
        else:
            err_msg = data.get("err_msg", "unknown error")
            log_api_call(
                api_type="语音转文字 (STT)",
                provider="Baidu Cloud",
                url=api_url,
                model="Baidu ASR English (1737)",
                action="百度英文短语音识别 (speech_to_text)",
                status="failed",
                extra_info=f"百度返回识别错误 [{err_no}]: {err_msg}。已回退至本地 Mock。"
            )
            return mock_speech_to_text(audio_path)
            
    except Exception as e:
        log_api_call(
            api_type="语音转文字 (STT)",
            provider="Baidu Cloud",
            url=api_url,
            model="Baidu ASR English (1737)",
            action="百度英文短语音识别 (speech_to_text)",
            status="failed",
            extra_info=f"请求百度接口发生异常: {str(e)}。已回退至本地 Mock。"
        )
        return mock_speech_to_text(audio_path)

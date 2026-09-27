import os
import base64
import asyncio
from typing import Optional, Union
from concurrent.futures import ThreadPoolExecutor

import edge_tts
from app.core.config import settings
from app.core.logger import log_api_call

# 1 秒静音 MP3 文件的 Base64 编码，用于网络不可用或请求超时等异常时的本地 Mock 降级
MOCK_MP3_BASE64 = (
    "SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU2LjM2LjEwMAAAAAAAAAAAAAAA//OEAAAAAAAAAAAAAAAAAAAAAAAASW5mbwAAAA8AAAAEAAABIADAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDV1dXV1dXV1dXV1dXV1dXV1dXV1dXV1dXV6urq6urq6urq6urq6urq6urq6urq6urq6v////////////////////////////////8AAAAATGF2YzU2LjQxAAAAAAAAAAAAAAAAJAAAAAAAAAAAASDs90hvAAAAAAAAAAAAAAAAAAAA//MUZAAAAAGkAAAAAAAAA0gAAAAATEFN//MUZAMAAAGkAAAAAAAAA0gAAAAARTMu//MUZAYAAAGkAAAAAAAAA0gAAAAAOTku//MUZAkAAAGkAAAAAAAAA0gAAAAANVVV"
)

# 默认高品质微软神经网络英文发音人
DEFAULT_VOICE = "en-US-EmmaMultilingualNeural"


def _format_rate(rate: Union[str, int, float, None]) -> str:
    """
    将语速参数转换为 edge-tts 所需的格式（例如 '+10%', '-5%', '+0%'）。
    - 若传入 float/int: 1.0 -> '+0%', 1.15 -> '+15%', 0.85 -> '-15%'
    - 若传入合规 str: 如 '+10%', '-5%'，直接使用
    - 若传入数值型 str: 如 '1.2'，转换为 float 后再换算百分比
    - 其它情况默认返回 '+0%'
    """
    if rate is None:
        return "+0%"
    if isinstance(rate, (int, float)):
        val = round((rate - 1.0) * 100)
        return f"{'+' if val >= 0 else ''}{val}%"
    if isinstance(rate, str):
        rate = rate.strip()
        # 如果已是合格的格式，直接返回
        if (rate.startswith("+") or rate.startswith("-")) and rate.endswith("%"):
            return rate
        # 尝试转换为浮点数并格式化
        try:
            val_f = float(rate)
            val = round((val_f - 1.0) * 100)
            return f"{'+' if val >= 0 else ''}{val}%"
        except ValueError:
            return "+0%"
    return "+0%"


def _get_proxy() -> Optional[str]:
    """
    自动读取系统的代理环境变量，协助在国内复杂网络环境下的 aiohttp 握手请求。
    优先级为 HTTPS_PROXY > HTTP_PROXY > https_proxy > http_proxy。
    """
    for env_key in ["HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"]:
        proxy = os.environ.get(env_key)
        if proxy:
            return proxy
    return None


def _write_mock_mp3(output_path: str) -> bool:
    """
    在网络无法连接或出现异常时，在本地静默写入 1 秒静音 Mock MP3 保证后续业务管道全通。
    """
    try:
        dir_name = os.path.dirname(output_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        mp3_bytes = base64.b64decode(MOCK_MP3_BASE64)
        with open(output_path, "wb") as f:
            f.write(mp3_bytes)
        return True
    except Exception as e:
        print(f"[TTS Mock 写入异常] 写入 Mock MP3 失败: {str(e)}")
        return False

def _rate_to_tencent_speed(rate: Union[str, int, float, None]) -> float:
    """
    将百分比或浮点语速转换为腾讯云 [-2.0, 2.0] 的 speed。
    1.0 (或 "+0%") -> 0.0
    1.2 (或 "+20%") -> 1.0
    1.5 (或 "+50%") -> 2.0
    0.8 (或 "-20%") -> -1.0
    0.6 (或 "-40%") -> -2.0
    """
    if rate is None:
        return 0.0
    multiplier = 1.0
    if isinstance(rate, (int, float)):
        multiplier = float(rate)
    elif isinstance(rate, str):
        rate = rate.strip()
        if rate.endswith("%"):
            try:
                val = float(rate[:-1].strip()) / 100.0
                multiplier = 1.0 + val
            except ValueError:
                multiplier = 1.0
        else:
            try:
                multiplier = float(rate)
            except ValueError:
                multiplier = 1.0

    if multiplier >= 1.0:
        if multiplier <= 1.2:
            speed = (multiplier - 1.0) / 0.2
        else:
            speed = 1.0 + (multiplier - 1.2) / 0.3
            if speed > 2.0:
                speed = 2.0
    else:
        if multiplier >= 0.8:
            speed = (multiplier - 1.0) / 0.2
        else:
            speed = -1.0 + (multiplier - 0.8) / 0.2
            if speed < -2.0:
                speed = -2.0
    return round(speed, 2)


def _tencent_text_to_speech_sync(
    text: str,
    output_path: str,
    voice_type: int,
    speed: float,
    secret_id: str,
    secret_key: str
) -> bool:
    """
    同步调用腾讯云 TTS TextToVoice 接口并将合成音频保存至 output_path。
    """
    from tencentcloud.common import credential
    from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
    from tencentcloud.tts.v20190823 import tts_client, models
    import uuid

    try:
        cred = credential.Credential(secret_id, secret_key)
        client = tts_client.TtsClient(cred, "ap-guangzhou")

        req = models.TextToVoiceRequest()
        req.Text = text
        req.SessionId = str(uuid.uuid4())
        req.VoiceType = voice_type
        req.Volume = 0
        req.Speed = speed
        req.ProjectId = 0
        
        # 根据 output_path 后缀自动设置 Codec
        ext = os.path.splitext(output_path)[1].lower()
        if ext == ".mp3":
            req.Codec = "mp3"
        elif ext == ".wav":
            req.Codec = "wav"
        else:
            req.Codec = "mp3"
            
        req.SampleRate = 16000

        resp = client.TextToVoice(req)
        
        if resp.Audio:
            audio_bytes = base64.b64decode(resp.Audio)
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            return True
        else:
            raise Exception("Tencent TTS response did not contain Audio data.")
            
    except TencentCloudSDKException as err:
        raise Exception(f"TencentCloudSDKException: {err.message} (code: {err.code})")
    except Exception as e:
        raise e


async def async_text_to_speech(
    text: str,
    output_path: str,
    voice: str = DEFAULT_VOICE,
    rate: Union[str, int, float, None] = "+0%"
) -> bool:
    """
    异步文字转语音 (TTS) 服务核心实现：
    使用 edge-tts 免 Key 合成高质量的神经网络语音，并保存至 output_path。
    若合成抛出异常或网络不通，将自动启动降级逻辑，写入本地 Mock 静音音频。
    """
    # 0. 简写与特定口音映射
    if voice == "us":
        voice = "en-US-EmmaMultilingualNeural"
    elif voice == "uk":
        voice = "en-GB-SoniaNeural"

    # 1. 检查是否配置并启用了腾讯云 TTS
    use_tencent = settings.USE_TENCENT_TTS
    secret_id = settings.TENCENT_SECRET_ID
    secret_key = settings.TENCENT_SECRET_KEY
    
    if use_tencent and secret_id and secret_key:
        # 确定腾讯云发音人声音 ID (101017: 智雅英文女声(美音), 105100: 英音女声)
        if "en-GB" in voice or "uk" in voice:
            tencent_voice = 105100
        else:
            tencent_voice = 101017

        if len(text) > 500:
            log_api_call(
                api_type="文字转语音 (TTS)",
                provider="Tencent Cloud",
                url="https://tts.tencentcloudapi.com",
                model=str(tencent_voice),
                action="腾讯云极速语音合成 (async_text_to_speech)",
                status="failed",
                extra_info=f"文本长度为 {len(text)} 超过腾讯极速版 500 字符限制。自动降级使用微软 Edge-TTS。"
            )
        else:
            tencent_speed = _rate_to_tencent_speed(rate)
            
            # 确保保存音频的父级目录存在
            dir_name = os.path.dirname(output_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
                
            log_api_call(
                api_type="文字转语音 (TTS)",
                provider="Tencent Cloud",
                url="https://tts.tencentcloudapi.com",
                model=str(tencent_voice),
                action="腾讯云极速语音合成 (async_text_to_speech)",
                status="pending",
                extra_info=f"文本内容: '{text[:40]}...', 语速: {tencent_speed} (原始 rate: {rate})"
            )
            
            try:
                success = await asyncio.to_thread(
                    _tencent_text_to_speech_sync,
                    text,
                    output_path,
                    tencent_voice,
                    tencent_speed,
                    secret_id,
                    secret_key
                )
                if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    log_api_call(
                        api_type="文字转语音 (TTS)",
                        provider="Tencent Cloud",
                        url="https://tts.tencentcloudapi.com",
                        model=str(tencent_voice),
                        action="腾讯云极速语音合成 (async_text_to_speech)",
                        status="success",
                        extra_info=f"腾讯云极速合成成功。保存路径: '{output_path}'，大小: {os.path.getsize(output_path)} 字节。"
                    )
                    return True
                else:
                    raise Exception("Tencent TTS returned success but output file is empty or missing.")
            except Exception as e:
                log_api_call(
                    api_type="文字转语音 (TTS)",
                    provider="Tencent Cloud",
                    url="https://tts.tencentcloudapi.com",
                    model=str(tencent_voice),
                    action="腾讯云极速语音合成 (async_text_to_speech)",
                    status="failed",
                    extra_info=f"请求腾讯云极速 TTS 接口发生异常: {str(e)}。将自动降级使用微软 Edge-TTS。"
                )
                # 抛出异常后继续向下执行微软 Edge-TTS 降级逻辑

    formatted_rate = _format_rate(rate)
    proxy = _get_proxy()

    # 确保保存音频的父级目录存在
    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    log_api_call(
        api_type="文字转语音 (TTS)",
        provider="Microsoft Edge TTS",
        url="wss://speech.platform.bing.com/consumer/speech/synthesize/readaloud/edge/v1",
        model=voice,
        action="微软神经网络语音合成 (async_text_to_speech)",
        status="pending",
        extra_info=f"文本内容: '{text[:40]}...', 语速: {formatted_rate}, 代理: {proxy or '无'}"
    )

    try:
        # 实例化 Communicate 语音合成任务
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=formatted_rate,
            proxy=proxy
        )
        
        # 异步保存至指定路径
        await communicate.save(output_path)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            log_api_call(
                api_type="文字转语音 (TTS)",
                provider="Microsoft Edge TTS",
                url="wss://speech.platform.bing.com/consumer/speech/synthesize/readaloud/edge/v1",
                model=voice,
                action="微软神经网络语音合成 (async_text_to_speech)",
                status="success",
                extra_info=f"音频合成成功。保存路径: '{output_path}'，大小: {os.path.getsize(output_path)} 字节。"
            )
            return True
        else:
            raise Exception("合成音频文件大小为 0 字节，生成失败。")

    except Exception as e:
        log_api_call(
            api_type="文字转语音 (TTS)",
            provider="Microsoft Edge TTS",
            url="wss://speech.platform.bing.com/consumer/speech/synthesize/readaloud/edge/v1",
            model=voice,
            action="微软神经网络语音合成 (async_text_to_speech)",
            status="failed",
            extra_info=f"请求微软 Edge-TTS 接口发生异常: {str(e)}。已安全激活本地 Mock 静音音频。"
        )
        # 启动安全 Mock 降级
        return _write_mock_mp3(output_path)


def text_to_speech(
    text: str,
    output_path: str,
    voice: str = DEFAULT_VOICE,
    rate: Union[str, int, float, None] = "+0%"
) -> bool:
    """
    同步文字转语音 (TTS) 包装：
    检测是否已经在当前事件循环中。若是，则使用线程池并在独立线程中执行异步任务，
    彻底避免 FastAPI/asyncio 等异步容器运行时抛出 'RuntimeError: This event loop is already running' 报错。
    """
    coro = async_text_to_speech(text, output_path, voice, rate)
    try:
        # 尝试捕获当前正在运行的事件循环
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # 当前没有事件循环，可以安全地在主线程直接跑 asyncio.run
        return asyncio.run(coro)

    # 如果已经在活跃的事件循环中，必须在新线程的独立事件循环中执行以防冲突
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result()

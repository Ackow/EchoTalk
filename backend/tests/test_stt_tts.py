import os
import sys
import asyncio

# 将 backend 目录添加到 Python 路径中
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.tts import text_to_speech, async_text_to_speech, _format_rate
from app.services.storage import upload_audio_to_kodo

def test_rate_formatting():
    print("\n--- [1. 语速参数格式化测试] ---")
    assert _format_rate(None) == "+0%"
    assert _format_rate(1.0) == "+0%"
    assert _format_rate(1.15) == "+15%"
    assert _format_rate(0.8) == "-20%"
    assert _format_rate("+10%") == "+10%"
    assert _format_rate("0.9") == "-10%"
    assert _format_rate("invalid") == "+0%"
    print("[OK] 语速参数格式化通过！")

def test_tts_sync_and_async():
    print("\n--- [2. 神经网络 TTS 同步与异步合成测试] ---")
    out_dir = "tests/data/output"
    os.makedirs(out_dir, exist_ok=True)
    
    # 异步合成测试
    async_out_path = os.path.join(out_dir, "test_async.mp3")
    if os.path.exists(async_out_path):
        os.remove(async_out_path)
        
    print("  * 发起异步合成...")
    success_async = asyncio.run(async_text_to_speech(
        text="This is a test of edge-tts asynchronous speech synthesis.",
        output_path=async_out_path,
        rate=1.1
    ))
    assert success_async is True
    assert os.path.exists(async_out_path)
    assert os.path.getsize(async_out_path) > 0
    print(f"  * [OK] 异步合成文件成功，大小: {os.path.getsize(async_out_path)} 字节")
    
    # 同步合成测试
    sync_out_path = os.path.join(out_dir, "test_sync.mp3")
    if os.path.exists(sync_out_path):
        os.remove(sync_out_path)
        
    print("  * 发起同步合成...")
    success_sync = text_to_speech(
        text="This is a test of edge-tts synchronous speech synthesis wrapper.",
        output_path=sync_out_path,
        rate="+5%"
    )
    assert success_sync is True
    assert os.path.exists(sync_out_path)
    assert os.path.getsize(sync_out_path) > 0
    print(f"  * [OK] 同步合成文件成功，大小: {os.path.getsize(sync_out_path)} 字节")
    
    # 清理测试生成的文件
    os.remove(async_out_path)
    os.remove(sync_out_path)

def test_tts_fallback_mock():
    print("\n--- [3. 神经网络 TTS 异常降级兜底测试] ---")
    out_dir = "tests/data/output"
    os.makedirs(out_dir, exist_ok=True)
    
    fallback_path = os.path.join(out_dir, "test_fallback.mp3")
    if os.path.exists(fallback_path):
        os.remove(fallback_path)
        
    # 我们用一个不存在的/非法的 voice 名称来故意触发异常，看是否会触发本地 Mock MP3 降级
    print("  * 故意传入非法 voice 触发降级...")
    success = text_to_speech(
        text="Fallback test.",
        output_path=fallback_path,
        voice="non-existent-voice-name"
    )
    assert success is True
    assert os.path.exists(fallback_path)
    # 合理大小：因为 Mock 静音音频 base64 解码后大概只有 300 多个字节
    file_size = os.path.getsize(fallback_path)
    assert file_size > 0 and file_size < 1000
    print(f"  * [OK] 触发降级成功。写入的 Mock 哑音频大小: {file_size} 字节")
    
    os.remove(fallback_path)

def test_tts_storage_upload():
    print("\n--- [4. TTS 产物七牛云存储上传测试] ---")
    out_dir = "tests/data/output"
    os.makedirs(out_dir, exist_ok=True)
    
    local_path = os.path.join(out_dir, "test_upload_source.mp3")
    if os.path.exists(local_path):
        os.remove(local_path)
        
    # 首先生成一个 TTS 音频
    text_to_speech("Hi, let's test if uploading to qiniu kodo works correctly.", local_path)
    
    # 上传到存储
    filename = "test_tts_upload.mp3"
    print("  * 正在上传/托管合成的音频文件...")
    url = upload_audio_to_kodo(local_path, filename)
    print(f"  * [OK] 音频托管返回的访问 URL: {url}")
    assert url.startswith("http://") or url.startswith("https://") or url.startswith("/static/audio")
    
    # 清理
    os.remove(local_path)
    # 如果是本地降级拷贝，还需要把托管目录的也清掉
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_dest = os.path.join(backend_dir, "static", "audio", filename)
    if os.path.exists(static_dest):
        os.remove(static_dest)

def test_tencent_tts_integration():
    print("\n--- [5. 腾讯云语音合成 (TTS) 集成与自适应降级测试] ---")
    out_dir = "tests/data/output"
    os.makedirs(out_dir, exist_ok=True)
    
    test_out_path = os.path.join(out_dir, "test_tencent_fallback.mp3")
    if os.path.exists(test_out_path):
        os.remove(test_out_path)
        
    # 模拟开启了腾讯云极速合成，但故意设置了错误的 SecretId/Key
    from app.core.config import settings as app_settings
    orig_use = app_settings.USE_TENCENT_TTS
    orig_id = app_settings.TENCENT_SECRET_ID
    orig_key = app_settings.TENCENT_SECRET_KEY
    
    try:
        app_settings.USE_TENCENT_TTS = True
        app_settings.TENCENT_SECRET_ID = "invalid-secret-id"
        app_settings.TENCENT_SECRET_KEY = "invalid-secret-key"
        
        print("  * 开启腾讯云合成并设置无效密钥，测试是否降级到 Edge-TTS...")
        success = text_to_speech(
            text="Testing Tencent TTS fallback to Edge TTS with invalid keys.",
            output_path=test_out_path
        )
        assert success is True
        assert os.path.exists(test_out_path)
        assert os.path.getsize(test_out_path) > 0
        print(f"  * [OK] 降级合成成功，生成音频大小: {os.path.getsize(test_out_path)} 字节")
        
    finally:
        # 恢复原始配置
        app_settings.USE_TENCENT_TTS = orig_use
        app_settings.TENCENT_SECRET_ID = orig_id
        app_settings.TENCENT_SECRET_KEY = orig_key
        if os.path.exists(test_out_path):
            os.remove(test_out_path)


def test_tencent_tts_success():
    print("\n--- [6. 腾讯云语音合成 (TTS) 模拟成功通路测试] ---")
    out_dir = "tests/data/output"
    os.makedirs(out_dir, exist_ok=True)
    
    test_out_path = os.path.join(out_dir, "test_tencent_success.mp3")
    if os.path.exists(test_out_path):
        os.remove(test_out_path)
        
    from unittest.mock import patch, MagicMock
    from app.core.config import settings as app_settings
    
    orig_use = app_settings.USE_TENCENT_TTS
    orig_id = app_settings.TENCENT_SECRET_ID
    orig_key = app_settings.TENCENT_SECRET_KEY
    
    # 模拟成功的响应
    mock_resp = MagicMock()
    from app.services.tts import MOCK_MP3_BASE64
    mock_resp.Audio = MOCK_MP3_BASE64
    
    try:
        app_settings.USE_TENCENT_TTS = True
        app_settings.TENCENT_SECRET_ID = "mock-secret-id"
        app_settings.TENCENT_SECRET_KEY = "mock-secret-key"
        
        # Mock TextToVoice 接口调用返回 mock_resp
        with patch("tencentcloud.tts.v20190823.tts_client.TtsClient.TextToVoice", return_value=mock_resp) as mock_api:
            print("  * 模拟开启腾讯云合成并配置 Mock 成功接口响应...")
            success = text_to_speech(
                text="Testing Tencent TTS successful path.",
                output_path=test_out_path
            )
            assert success is True
            assert mock_api.called is True
            assert os.path.exists(test_out_path)
            assert os.path.getsize(test_out_path) > 0
            print(f"  * [OK] 腾讯云 TTS 模拟成功通路测试通过！音频大小: {os.path.getsize(test_out_path)} 字节")
            
    finally:
        app_settings.USE_TENCENT_TTS = orig_use
        app_settings.TENCENT_SECRET_ID = orig_id
        app_settings.TENCENT_SECRET_KEY = orig_key
        if os.path.exists(test_out_path):
            os.remove(test_out_path)


if __name__ == "__main__":
    try:
        test_rate_formatting()
        test_tts_sync_and_async()
        test_tts_fallback_mock()
        test_tts_storage_upload()
        test_tencent_tts_integration()
        test_tencent_tts_success()
        print("\n=============================================")
        print(" [SUCCESS] 微软与腾讯云 TTS 服务单元测试全部通过！ ")
        print("=============================================\n")
    except AssertionError as e:
        print(f"\n[FAIL] 断言失败: {e}")
        sys.exit(1)
    except Exception as ex:
        print(f"\n[FAIL] 发生异常: {ex}")
        sys.exit(1)

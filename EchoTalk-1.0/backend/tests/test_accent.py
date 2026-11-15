import os
import sys
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# 将 backend 目录添加到 Python 路径中
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app, seed_default_scenes
from app.core.database import get_db, engine, Base
from app.models import User, DialogueHistory
from app.services.tts import async_text_to_speech

client = TestClient(app)
Base.metadata.create_all(bind=engine)

def test_dialogue_accent_endpoints():
    print("\n--- [对话口音接口测试开始] ---")
    db = next(get_db())
    seed_default_scenes(db)
    
    # 确保存在测试用户
    test_username = "accent_test_user"
    user = db.query(User).filter(User.username == test_username).first()
    if not user:
        user = User(username=test_username)
        db.add(user)
        db.commit()
        db.refresh(user)

    # 1. 启动会话时传入英式发音 (uk)
    start_payload = {
        "user_id": user.id,
        "scene_id": "ordering",
        "accent": "uk"
    }
    start_resp = client.post("/api/dialogues/start", json=start_payload)
    assert start_resp.status_code == 201, start_resp.text
    history_data = start_resp.json()
    history_id = history_data["id"]
    assert history_data["accent"] == "uk"
    
    # 验证数据库中也是 uk
    history_db = db.query(DialogueHistory).filter(DialogueHistory.id == history_id).first()
    assert history_db.accent == "uk"
    
    # 2. 修改口音为美式发音 (us)
    put_resp = client.put(f"/api/dialogues/{history_id}/accent?accent=us")
    assert put_resp.status_code == 200
    assert put_resp.json()["accent"] == "us"
    
    db.refresh(history_db)
    assert history_db.accent == "us"
    
    # 3. 传入非法口音校验
    put_resp_invalid = client.put(f"/api/dialogues/{history_id}/accent?accent=invalid")
    assert put_resp_invalid.status_code == 400
    
    # 清理数据
    db.delete(history_db)
    db.commit()
    db.close()
    print("[SUCCESS] 对话口音切换接口测试通过！")


@patch("app.services.tts.edge_tts.Communicate")
@patch("app.services.tts.settings")
def test_tts_voice_mapping_edge_tts(mock_settings, mock_communicate):
    print("\n--- [Edge-TTS 口音映射与调用测试开始] ---")
    mock_settings.USE_TENCENT_TTS = False
    mock_settings.TENCENT_SECRET_ID = None
    mock_settings.TENCENT_SECRET_KEY = None
    
    # 模拟 edge-tts 保存
    mock_comm_instance = mock_communicate.return_value
    mock_comm_instance.save = MagicMock()
    
    # 测试美音
    asyncio.run(async_text_to_speech("hello", "dummy.mp3", voice="us"))
    mock_communicate.assert_called_with(
        text="hello",
        voice="en-US-EmmaMultilingualNeural",
        rate="+0%",
        proxy=None
    )
    
    # 测试英音
    asyncio.run(async_text_to_speech("hello", "dummy.mp3", voice="uk"))
    mock_communicate.assert_called_with(
        text="hello",
        voice="en-GB-SoniaNeural",
        rate="+0%",
        proxy=None
    )
    print("[SUCCESS] Edge-TTS 口音映射测试通过！")


@patch("app.services.tts._tencent_text_to_speech_sync")
@patch("app.services.tts.settings")
def test_tts_voice_mapping_tencent(mock_settings, mock_tencent_sync):
    print("\n--- [Tencent TTS 口音映射与调用测试开始] ---")
    mock_settings.USE_TENCENT_TTS = True
    mock_settings.TENCENT_SECRET_ID = "test-id"
    mock_settings.TENCENT_SECRET_KEY = "test-key"
    
    mock_tencent_sync.return_value = True
    
    # 测试美音
    asyncio.run(async_text_to_speech("hello", "dummy.mp3", voice="us"))
    mock_tencent_sync.assert_called_with(
        "hello",
        "dummy.mp3",
        101017,  # 美音女声
        0.0,
        "test-id",
        "test-key"
    )
    
    # 测试英音
    asyncio.run(async_text_to_speech("hello", "dummy.mp3", voice="uk"))
    mock_tencent_sync.assert_called_with(
        "hello",
        "dummy.mp3",
        105100,  # 英音女声
        0.0,
        "test-id",
        "test-key"
    )
    print("[SUCCESS] Tencent TTS 口音映射测试通过！")


def test_on_demand_accent_synthesis():
    print("\n--- [在线按需口音合成接口测试开始] ---")
    db = next(get_db())
    
    # 建立一条临时轮次记录
    from app.models import DialogueTurn
    turn = DialogueTurn(
        dialogue_history_id=1,
        role="assistant",
        text="Hello world test",
        audio_url="original_url.mp3",
        audio_url_us="us_url.mp3"
    )
    db.add(turn)
    db.commit()
    db.refresh(turn)
    
    try:
        # 1. 尝试获取已有缓存的美音，应直接返回已有值而不调用 tts 引擎
        resp_us = client.post(f"/api/dialogues/turns/{turn.id}/synthesize?accent=us")
        assert resp_us.status_code == 200
        assert resp_us.json()["audio_url"] == "us_url.mp3"
        
        # 2. 尝试获取未缓存的英音，应触发 TTS 异步合成并存盘
        with patch("app.api.endpoints.dialogues.async_text_to_speech") as mock_tts, \
             patch("app.api.endpoints.dialogues.upload_audio_to_kodo") as mock_upload:
            
            # 定义 side_effect 模拟写入音频文件
            def mock_tts_side_effect(text, path, voice):
                with open(path, "w") as f:
                    f.write("dummy-mp3-bytes")
                return True
                
            mock_tts.side_effect = mock_tts_side_effect
            mock_upload.return_value = "new_uk_url.mp3"
            
            resp_uk = client.post(f"/api/dialogues/turns/{turn.id}/synthesize?accent=uk")
            assert resp_uk.status_code == 200
            assert resp_uk.json()["audio_url"] == "new_uk_url.mp3"
            
            # 确认合成参数正确
            mock_tts.assert_called_once()
            args, kwargs = mock_tts.call_args
            assert args[0] == "Hello world test"
            assert kwargs["voice"] == "en-GB-SoniaNeural"
            
            # 确认数据库已更新
            db.refresh(turn)
            assert turn.audio_url_uk == "new_uk_url.mp3"
            
    finally:
        db.delete(turn)
        db.commit()
        db.close()
    print("[SUCCESS] 在线按需口音合成接口测试通过！")

if __name__ == "__main__":
    test_dialogue_accent_endpoints()
    test_tts_voice_mapping_edge_tts()
    test_tts_voice_mapping_tencent()
    test_on_demand_accent_synthesis()

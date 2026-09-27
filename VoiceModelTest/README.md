# LFM2.5-Audio 本地测试

模型目录：`LFM2.5-Audio-1.5B-4bit/`（约 1.8 GB，已下载到本目录）。

在 Apple Silicon macOS 且可用 Metal GPU 的环境中运行：

```bash
cd /path/to/EchoTalk
source .venv/bin/activate

# 默认用项目根目录的 dummy.mp3 做语音转文字
python VoiceModelTest/test_lfm_audio.py --mode stt --audio dummy.mp3

# 文本转语音，输出 VoiceModelTest/output.wav
python VoiceModelTest/test_lfm_audio.py --mode tts --text "Hello from EchoTalk."

# 语音到语音
python VoiceModelTest/test_lfm_audio.py --mode sts --audio dummy.mp3
```

如果需要重新下载模型：

```bash
python VoiceModelTest/download_model.py
```

依赖安装：

```bash
python -m pip install -r VoiceModelTest/requirements.txt
```

# 对话练习：录音与 ASR 转写

流程为：点击麦克风 → 浏览器采集 PCM → 停止录音 → 本地重采样为 WAV → 后端腾讯云 Flash ASR → 填入草稿 → 用户确认发送 → 对话 Agent。

## 配置

在腾讯云开通语音识别服务，在 `backend/.env` 配置以下服务端凭据，然后重启后端：

```dotenv
ECHOTALK_ASR_APP_ID=你的AppID
ECHOTALK_ASR_SECRET_ID=你的SecretID
ECHOTALK_ASR_SECRET_KEY=你的SecretKey
```

部署先运行 `cd backend`、`uv sync --locked`。新增语音模块不涉及数据库表，无需数据库迁移。密钥不下发前端，不通过浏览器原生 SpeechRecognition 识别。

实现遵循腾讯云 [Flash ASR 官方接口与签名说明](https://cloud.tencent.com/document/product/1093/52097)，使用 `16k_en` 引擎、HTTPS 上传和 HMAC-SHA1 签名。

## 接口

| 接口 | 用途 |
|---|---|
| `GET /api/speech/status` | 公开能力查询，返回 configured / max_duration / sample_rate |
| `POST /api/speech/transcriptions` | 登录后上传 multipart `file`，返回 text / duration / provider |

后端检查实际 WAV 数据：16kHz、单声道、PCM16、0.3–60 秒、最大 2MB。损坏/截断录音被拒绝，扩展名和 MIME 不作为格式依据。云服务未配置返回 503，空识别结果返回 422，服务错误返回 502，不回退模拟文本。

## 前端职责

- `src/composables/useVoiceInput.js`：麦克风权限、计时、状态、取消、停止及资源释放。
- `public/audio/pcm-recorder.worklet.js`：音频线程采样并确认停止前的尾段已发送。
- `src/audio/wav.js`：通过 OfflineAudioContext 重采样并编码 WAV。
- `src/api/speech.js`：携带现有登录令牌上传，不自动重试计费请求。
- `views/Practice.vue`：音量指示、停止/取消按钮、草稿确认与输入状态。

浏览器须允许麦克风，并运行在 localhost、HTTPS 或允许音频录制的桌面环境。标准 WAV 直接供识别，无需本机 FFmpeg。音频只在本轮浏览器内存和上传处理过程中使用，本模块不保存用户录音文件；识别请求会上传至配置的腾讯云服务。

用户停止录音后即释放音轨，再执行编码与上传；取消、页面卸载或设备断开也会清理资源。取消后迟到的权限/识别结果不会覆盖草稿。原有草稿与录音失败时的文字均保留。TTS 在录音开始时停止，录音或转写期间不会播放回复。

当前为停止后批量转写，不提供边说边出的字幕，也没有接入发音评分。ASR 只负责转写，不直接决定训练得分。

## 问候语与回复播报

创建会话时优先使用场景的问候语；未填写时提供基于角色的默认开场。前端默认自动播放问候与后续回复，可通过右侧「自动播放问候与回复」关闭，偏好保存在本机。浏览器阻止自动播放时显示提示，仍可点击「听语音」。

问候文本保存在会话数据库记录中，音频通过登录后的 `GET /api/sessions/{id}/greeting-audio` 获取。首次播放合成后持久化到 `backend/storage/tts/greetings/`（可由 `ECHOTALK_STORAGE_ROOT` 调整根目录）；后续会话命中相同文本、实际声音、语速与合成组件版本时直接读取 MP3，不重复调用 TTS。后端重启仍可复用。场景问候或声音参数变化时生成新的缓存文件，旧会话继续使用其文本快照。同进程首次并发请求合并，文件以原子替换写入；音频入口仍验证会话归属，不公开缓存目录。普通对话回复继续通过 TTS 接口按需生成。

TTS 独立使用 Edge 渠道，不使用腾讯云 ASR 凭据。依赖要求 `edge-tts>=7.3.0,<8`，当前锁定版本为 7.3.1；旧版 7.2.8 的上游 WebSocket 握手可能返回 403，进而表现为后端 502。升级包含 [上游 Sec-MS-GEC v2 修复](https://github.com/rany2/edge-tts/releases/tag/7.3.0)。音频接口失败时，前端会解包 Blob 中的 JSON 错误，显示具体原因。

## 验证边界

后端离线测试覆盖格式、时长、截断、配置缺失、服务错误、超时、空结果和鉴权；浏览器用合成音轨验证采样/编码/上传流程、取消保留草稿、音轨释放与拒绝权限提示。真实麦克风效果和腾讯云识别准确率仍需配置凭据后联调，不使用模拟测试结果作为识别质量证明。

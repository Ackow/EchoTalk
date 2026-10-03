# EchoTalk 2.0：数字人与声音模块设计

> 版本：v1.0 ｜ 状态：待实现 ｜ 对应总设计稿：§13 数字人与声音、§14.2/§14.4 前端、§20 阶段 7
> 上游依赖：场景包 v2（§4.7 数字人与场景包的边界）、TTS 服务、播放器状态机
> 定位：**呈现层模块**。决定"谁在说话、长什么样、什么声音"，不决定"练什么"。

---

## 阅读导航

| 章节 | 内容 |
|---|---|
| 1 | 模块定位与职责边界 |
| 2 | 三层形态与产品状态 |
| 3 | 资产规范（2D 分层与目录） |
| 4 | 数据模型 |
| 5 | 优先级与解析规则 |
| 6 | 口型驱动（三级降级） |
| 7 | 前端设计（组件与状态机） |
| 8 | 接口设计 |
| 9 | 后端实现要点 |
| 10 | 与既有模块的衔接 |
| 11 | 分阶段任务与完成标准 |
| 12 | 取舍、风险与不做的事 |

---

## 1. 模块定位与职责边界

数字人是**对话呈现层**，与场景包严格分离（场景包设计稿 §4.7 已定结论，本模块沿用并细化）：

| 关注点 | 归属 | 说明 |
|---|---|---|
| 角色 → 形象 / 声音的**推荐值** | 场景包 | `roles[].avatar / voice`、`avatar.preferred / rate`，全部可选、缺失无副作用 |
| 形象资产、声音、语速、呈现模式的**实际配置** | 数字人模块（用户级） | 角色页 / 设置页管理；资产存本地，不入场景包 ZIP |
| 实际渲染 | 前端 `AvatarStage` | 优先级：用户偏好 > 场景包推荐 > 应用缺省 |

**为什么必须分离：**

1. **职责分离** —— 场景包声明训练任务（教学内容），数字人是呈现层。同一场景换形象不应改动训练内容，导出的场景包也不应因为用户选了哪张脸而变化。
2. **可移植性** —— 2D/3D 模型与音频资产体积大、许可复杂，入包会让 ZIP 膨胀并限制分发。`voice` 只是风格描述（如 `en-US-YoungMale`），运行时映射到当前可用的 TTS 渠道。
3. **用户优先** —— 包推荐只是作者建议，用户在角色页的选择始终覆盖它，避免不同场景包互相改写用户配置。
4. **阶段匹配** —— 场景包在阶段 2–3 落地，数字人在阶段 7；`assets/` 目录 v1 只保留位置与透传。

**模块包含三个子能力：**

```
数字人模块
├── 形象（avatar_asset）  角色 → 形象资产的映射，含 2D 分层参数
├── 声音（voice）        TTS 声音风格 → 当前渠道可用 voice 的运行时映射
└── 呈现（presentation）  呈现模式（头像 / 2D / 3D 占位）+ 口型 + 状态
```

---

## 2. 三层形态与产品状态

| 层 | 实现 | 产品状态 | 本期交付 |
|---|---|---|---|
| 头像 | 角色首字母 / 静态图 + 说话·倾听状态点 | 轻量默认可用 | ✅ 阶段 7 交付（缺省回退层，必须永远可用） |
| 2D | 分层角色图 + 基础口型 + 待机动作 | **首批数字人目标** | ✅ 阶段 7 交付 |
| 3D | Three.js / VRM、动作与细口型 | 界面保留资源与模式位置 | ⏸ 仅保留数据结构与 UI 占位，不做渲染器 |

**关键原则：**

- **优先级是"角色一致性 + 音画同步"，不是写实面部。** 首版不做写实面部捕捉、不做 ARKit  blendshape。
- **摄像头不是前置条件。** 面部动捕（MediaPipe /摄像头方案）不在本期范围，后续按需要再加。
- **3D 不承诺时间盒。** 只在数据结构（`presentation_mode = "3d"`、`asset_id` 指向 `.vrm/.glb`）与 UI 位置上留好扩展点，避免主线周数被拖累。

---

## 3. 资产规范（2D 分层与目录）

### 3.1 资产形态选择

| 方案 | 优点 | 代价 | 决策 |
|---|---|---|---|
| **CSS/SVG 分层图形**（参考稿方案） | 零素材成本、任意分辨率清晰、包体近零、状态切换纯代码 | 视觉表现力有限，风格化 | ✅ **首版采用** |
| Live2D / Spine 动画 | 表现力强 industry-standard，参数化口型 | 需要授权素材与运行时，编辑器门槛高 | 后续 spike |
| 序列帧精灵图 | 实现简单 | 体积大、多分辨率适配差、多状态组合爆炸 | 不采用 |
| 3D / VRM | 表现力上限最高 | Three.js 运行时 + 模型资产 + 动作制作，成本最高 | 阶段 7 只留位 |

### 3.2 2D 资产分层契约

一个角色形象由**固定图层**组成，图层顺序即 z 序，缺省用占位样式补齐（不因缺图层报错）：

| z | 图层 key | 说明 | 必需 |
|---|---|---|---|
| 0 | `backdrop` | 舞台背景（渐变 / 圆形光环） | 否 |
| 1 | `body` | 躯干 + 服装 | 是 |
| 2 | `hair_back` | 后层头发 | 否 |
| 3 | `head` | 头部底色 | 是 |
| 4 | `face` | 眉 / 眼 / 鼻 | 否 |
| 5 | `mouth` | **口型层，受状态驱动** | 是 |
| 6 | `hair_front` | 刘海 / 前层头发 | 否 |
| 7 | `accessory` | 眼镜 / 耳机 / 帽子 | 否 |

每个形象资产（`avatar_asset`）的声明字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | str | 形象 ID，如 `leo_2d`、`sarah_2d`，小写下划线 |
| `display_name` | str | 展示名，如 "Leo · 2D" |
| `kind` | `head` \| `2d` \| `3d` | 形态；`3d` 仅登记不渲染 |
| `theme` | str | 主题 token 名（配色），复用 styles.css 变量 |
| `layers` | dict | 上表的 key → 素材路径或内置占位样式名 |
| `mouth_shapes` | list | 支持的口型集合，首版 `["closed", "open", "wide", "round"]` |
| `voice_hint` | str? | 声音风格倾向，如 `female_young`、`male_young`；**仅推荐**，可被用户覆盖 |
| `fallback_avatar` | str? | 加载失败时回退到哪个形象 ID，默认 `default` |

### 3.3 资产目录

```
backend/storage/avatars/
├── manifest.json              # 全部形象清单（内置，随应用分发）
├── default/                   # 缺省形象：纯 CSS 占位，不依赖任何文件
│   └── manifest.json
└── {avatar_id}/
    ├── manifest.json          # 该形象的图层声明
    ├── body.svg               # 可选，缺失则用占位样式
    ├── head.svg
    ├── face.svg
    ├── hair_back.svg
    ├── hair_front.svg
    ├── mouth.svg
    └── accessory.svg
```

约束：

- **资产永远不进场景包 ZIP**，也不入库。库中只存 `avatar_id` 字符串（与场景包 `roles[].avatar` 同一命名空间）。
- `manifest.json` 缺失或解析失败 → 该形象视为不可用，回退 `default`，**不得让对话流程失败**。
- 3D 资产目录预留 `backend/storage/avatars/{avatar_id}/model.{vrm,glb}`，本期不上传、不校验体积。

---

## 4. 数据模型

### 4.1 新增表：`user_preferences`（用户级偏好，1 用户 1 行）

| 列 | 类型 | 说明 |
|---|---|---|
| `user_id` | FK users.id | 主键兼外键 |
| `avatar_id` | String(50) | 用户选择的形象；NULL 表示跟随场景推荐 |
| `voice_style` | String(50) | 声音风格，如 `us_female` / `uk_female`；NULL 跟随推荐 |
| `tts_voice` | String(100) | 映射后的渠道 voice id，如 `en-US-EmmaNeural`；NULL 用渠道缺省 |
| `speech_rate` | Float | 语速倍率 0.75–1.25，缺省 1.0 |
| `presentation_mode` | String(10) | `auto` / `head` / `2d` / `3d`；缺省 `auto`（自动降级） |
| `lip_sync_enabled` | Bool | 是否显示口型，缺省 True |
| `subtitle_enabled` | Bool | 字幕开关（与口型共用同一播放器时间轴） |
| `created_at / updated_at` | DateTime | UTC |

**为什么单表而不是散落在 settings：** 偏好是"读多写极少、整体覆盖"的语义，一行 JSON 覆盖会让"部分更新"和"字段级校验"都变复杂；显式列可以直接用 SQL 查询与迁移，代价仅是可读性略差。后续偏好类型增多（目标、每日时长、纠错时机）时按前缀拆表。

### 4.2 资产清单：不入库

`avatar_asset` 清单来自 `backend/storage/avatars/manifest.json`，由后端启动时读取并缓存到进程内（`AvatarRegistry`，与 `SceneRegistry` 同构）。不建表，因为：

- 资产随应用分发，不随用户变化；
- 建表后需要处理"文件存在但库里没有 / 库里有但文件没了"的双向一致性；
- 清单本身只有几十行，进程内缓存足够。

`AvatarRegistry` 对外暴露：

| 方法 | 用途 |
|---|---|
| `list(kind=None)` | 列出可用形象（不含不可用项） |
| `get(avatar_id)` | 取单个形象声明；不存在返回 None（调用方负责回退） |
| `resolve(avatar_id)` | 取形象声明，失败自动回退 `default`，**永不抛异常** |

### 4.3 场景包侧（不改，仅消费）

场景包 v2 已有字段，本模块只读取：

```yaml
# scene.yaml
roles:
  - id: barista
    display_name: Leo
    voice: en-US-YoungMale      # 风格描述，运行时映射
    avatar: leo_2d             # 形象推荐

avatar:                        # 整包级推荐（可选）
  preferred: leo_2d
  rate: 1.0
```

`backend/app/scenes/schema.py` 中 `SceneRole.avatar` 与 `SceneAvatar(preferred, rate)` 已就位，**无需改动**。Pydantic 校验只检查引用格式，不要求资产存在——保持这一约束，资产缺失走运行期回退。

---

## 5. 优先级与解析规则

形象与声音的最终取值用一条**单向解析链**，禁止反向写入用户偏好：

```
resolve(scene_role, preferences, registry) ->
    1. preferences.avatar_id   有效且资产可用   → 用户显式选择
    2. scene_role.avatar       资产可用         → 场景包角色推荐
    3. scene_pkg.avatar.preferred 资产可用     → 整包推荐
    4. registry.default                      → 应用缺省
    （四级都不可用 → default 占位图形，仍不可用 → 头像层）
```

声音同理，链尾再退到 `asset.voice_hint` 与渠道缺省 voice：

```
resolve_voice(scene_role, preferences, channel_available) ->
    1. preferences.tts_voice    在渠道可用列表中
    2. preferences.voice_style  → 渠道映射表
    3. scene_role.voice         → 渠道映射表（风格串如 en-US-YoungMale）
    4. channel.default_voice
```

语速：

```
effective_rate = clamp(preferences.speech_rate ?? scene_pkg.avatar.rate ?? 1.0, 0.5, 2.0)
```

呈现模式同理，`auto` 依次尝试 `2d → head`，即**资产不支持 2D 时自动落到头像层**，设置页显示实际生效的模式而不是 `auto` 字面值。

**写入方向的单向性**是关键约束：解析结果**永不回写** `user_preferences`。否则用一个场景会静默改掉用户的全局形象选择。

---

## 6. 口型驱动

设计稿要求："TTS 有 timing / viseme 时按播放进度驱动口型；否则用音量或播放状态做简化开合。" 落地为**三级降级阶梯**，每级都能独立工作，运行时按可用性自上而下选：

| 级别 | 驱动源 | 表现 | 依赖 | 成本 |
|---|---|---|---|---|
| **L1 时间轴驱动** | 合成时返回的 `viseme_timeline` | 口型按当前播放时间查表切换，与语音严格对齐 | TTS 需返回词/音节边界时间戳 | 中 |
| **L2 音量包络驱动** | Web Audio `AnalyserNode` RMS | 嘴部开合幅度随实时音量变化，闭嘴时机准确 | 需 `createMediaElementSource` 接入播放链 | 低 |
| **L3 播放状态驱动** | `playing` 布尔 | 说话时固定开合 + 轻微摆动，停止即回待机 | 无 | 极低 |

### 6.1 L1：时间轴

后端合成语音时同时产出一份与音频同名的元数据：

```json
{
  "audio_path": "storage/audio/turn_003.mp3",
  "duration_ms": 2140,
  "provider": "edge_tts",
  "rate": "+0%",
  "words": [
    { "text": "Would", "start_ms": 0,   "end_ms": 380, "viseme": "wide" },
    { "text": "you",  "start_ms": 380, "end_ms": 620, "viseme": "round" }
  ]
}
```

- Edge-TTS 走 `Communicate.stream()` 捕获 `WordBoundary`（含 offset/duration）；腾讯云 TTS 走 `WordBoundary` / `SentenceBoundary` 响应。两者都能给出词级时间戳。
- 词 → viseme 的映射用一张静态表（按元音开头归类到 `wide / round / open / closed`），**首版不做音素级精细转换**。
- 存为 `xxx.mp3` + `xxx.timeline.json` 同目录，SSE 的 `audio_ready` 事件里带 `timeline_url`。

### 6.2 L2：音量包络

播放器已用 `<audio>` 时，接 `AnalyserNode` 需要注意：同一媒体元素只能建一次 `MediaElementAudioSourceNode`，重复创建会抛错。因此该节点由**播放器单例**创建一次，口型只订阅它输出的 RMS 数值，不自己碰音频链。

```js
// 每个渲染帧读取一次，得到 0~1 的开合目标值
const level = clamp((rms - NOISE_FLOOR) / (PEAK - NOISE_FLOOR), 0, 1)
mouth.style.setProperty('--mouth-open', level.toFixed(3))
```

阈值（`NOISE_FLOOR` / `PEAK`）需按实际音频标定；初版用固定保守值并留成配置项，不做自动校准。

### 6.3 状态与口型关系

| 阶段状态 | 眼睛 | 嘴 | 身体 |
|---|---|---|---|
| `idle` | 正常 | 闭合 | 呼吸式轻微起伏 |
| `listening`（用户在说） | 眨眼频率降低（"专注"） | 闭合 | 静止 |
| `thinking` | 上移（示意"看向别处"） | 闭合 | 静止 |
| `speaking` | 正常眨眼 | **由 L1/L2/L3 驱动** | 轻微摆动 |
| `interrupted` | — | 立即闭合 | — |

**中断必须立刻回待机。** 用户点击停止或插话时，先 `audio.pause()` 并把状态置为 `idle`，再更新 UI；不允许出现"音频已停但嘴还在动"。

---

## 7. 前端设计

### 7.1 组件拆分

对齐设计稿 §14.4 的 `components/avatar/`：

```
src/components/avatar/
├── AvatarStage.vue      # 舞台：承载形象、渲染状态与口型；对话页与面试页共用
├── RolePicker.vue       # 角色选择：场景包角色 → 形象的映射选择器
├── VoiceSettings.vue    # 声音设置：voice / 语速 / 口型开关
└── useLipsync.js        # 口型驱动 composable（L1/L2/L3 降级封装）
```

页面与复用关系：

| 组件 | 数字人角色页 | 语音对话页 | 模拟面试页 |
|---|---|---|---|
| `AvatarStage` | 大尺寸预览（scale 1.25） | 侧栏小尺寸 | 主舞台 + 角色切换 |
| `RolePicker` | ✅ 完整（选场景角色 → 选形象） | ➖ 只读 + "更换"入口跳转 | ➖ 面试官角色 pill 联动 |
| `VoiceSettings` | ✅ 完整 | ➖ 抽屉（从设置页进入） | ➖ 同左 |

**共享原则**：`AvatarStage` 只接收 `avatarId` / `size` / `state` / `lipSync` 四个输入，不自己拉数据。这样对话页、面试页、角色页三处用同一个组件，形象解析逻辑只写一遍。

### 7.2 状态机

设计稿 §14.4 的会话状态机 `idle / recording / transcribing / thinking / speaking / finished / error` 已覆盖本模块需求，本模块**复用同一套状态**，不另立一套。映射关系：

| 会话状态 | AvatarStage `state` | 口型 |
|---|---|---|
| `idle` / `finished` | `idle` | 闭合 |
| `recording` / `transcribing` | `listening` | 闭合 |
| `thinking` | `thinking` | 闭合 |
| `speaking` | `speaking` | **驱动** |
| `error` | `idle` | 闭合 + 错误提示 |

`AvatarStage` 自身不持有业务状态，只接收 prop；`finished` 与 `error` 的区别体现在外层文案，不体现在形象上。

### 7.3 路由与占位页

设计稿把"数字人角色"列为 14 个页面之一，本期从 `ModulePlaceholder` 升级为真实页面：

```js
// src/router/index.js 替换占位
{ path: 'avatar', name: 'avatar', component: () => import('../views/AvatarSettings.vue'), meta: { title: '数字人角色' } }
```

页面布局对齐参考稿（截图 `echotalk-2.0-avatar.png`）：左列形象预览舞台 + 状态演示按钮，右列"角色与声音设置"表单（交流角色 / 呈现方式 / 声音 / 语速滑块 / 口型开关 / 3D 资源占位）。

新增状态：`preferencesStore`（或沿用现有轻量模式——项目当前**没有** Pinia，`frontend/src` 下无 `stores/`，偏好暂放模块级 `reactive` 单例即可，等阶段 1 迁 Pinia 时再对齐）。保存走 `PUT /preferences/avatar`。

---

## 8. 接口设计

统一挂在 `/api` 前缀下，与现有 `auth_router / scenes_router / knowledge_router` 装配方式一致。全部接口**登录可选**：游客可读取与试用，保存需登录（与当前"游客可浏览"策略一致）。

| 方法 | 路径 | 用途 | 登录 |
|---|---|---|---|
| GET | `/api/avatars` | 列出可用形象（含 `default`），返回精简字段 | 否 |
| GET | `/api/avatars/{avatar_id}` | 形象详情（完整图层声明） | 否 |
| GET | `/api/avatars/resolve?scene_id=&role_id=` | 按优先级解析出实际生效的形象 + 声音 + 语速 + 模式 | 否 |
| GET | `/api/voices` | 当前 TTS 渠道可用声音列表（`voice_style` → `tts_voice` 映射表） | 否 |
| GET | `/api/preferences/avatar` | 读取用户数字人偏好；未设置返回 `null` 字段而非 404 | 否 |
| PUT | `/api/preferences/avatar` | 整体覆盖保存（部分字段缺省视为不改动） | 是 |
| DELETE | `/api/preferences/avatar` | 恢复默认（回到"跟随场景推荐"） | 是 |

响应示例（`/api/avatars/resolve`）：

```json
{
  "avatar": { "id": "leo_2d", "display_name": "Leo · 2D", "kind": "2d", "theme": "violet" },
  "source": "scene_role",
  "voice": { "style": "en-US-YoungMale", "tts_voice": "en-US-AndrewNeural", "available": true },
  "speech_rate": 1.0,
  "presentation_mode": "2d",
  "lip_sync": "timeline",
  "fallback_used": false
}
```

`source` 取值 `user | scene_role | scene_package | default`，前端据此显示"当前使用场景推荐形象 / 你的选择"，避免用户困惑。`lip_sync` 取 `timeline | envelope | state | off`，让前端与日志能明确当前口型实际跑在哪一级，不谎称 L1。

**SSE 事件扩展**（`/api/sessions/{id}/stream`）：`audio_ready` 事件 data 增加两个可选字段。

```json
{
  "type": "audio_ready",
  "data": {
    "url": "/audio/reply_003.mp3",
    "text": "Sure!",
    "timeline_url": "/audio/reply_003.timeline.json",
    "lip_sync": "timeline"
  }
}
```

字段可选 ⇒ 旧前端不受影响，缺失时前端自动降级到 L2/L3。

---

## 9. 后端实现要点

新增文件：

```
backend/app/
├── models.py                # 追加 UserPreference 表（沿用现有风格：中文行内注释）
├── schemas.py               # 追加 AvatarOut / AvatarResolveOut / AvatarPreferenceIn
├── services/
│   ├── avatar_service.py    # AvatarRegistry + resolve 链 + 清单加载
│   └── voice_service.py     # 渠道可用声音查询 + voice_style 映射
└── api/endpoints/
    ├── avatars.py           # /avatars、/avatars/resolve
    └── preferences.py       # /preferences/avatar
```

在 `app/main.py` 注册两枚路由（与现有三枚同风格），并在 `import models` 处自动建表（沿用现有 `init_db.py` + 启动同步模式，不引入迁移框架）。

实现要点：

| 要点 | 做法 |
|---|---|
| 清单加载 | 启动时读 `storage/avatars/manifest.json`，进程内缓存；文件缺失则只有 `default` |
| 永不抛异常 | `resolve()` 任何异常都回退 `default` 并在响应里带 `fallback_used: true` |
| 渠道探测 | `/api/voices` 从 TTS 服务读取可用 voice；不可用时返回本地静态表 + `available: false` |
| 游客策略 | GET 类接口不校验令牌；PUT/DELETE 走现有 `deps.py` 鉴权 |
| 时间轴产出 | 在 TTS 服务内统一封装 `synthesize() -> (audio_path, timeline|None)`，调用方无需关心供应商 |
| 写操作审计 | 沿用现有结构化日志，记录 `user_id` 与 `avatar_id` 变更前后值 |

---

## 10. 与既有模块的衔接

| 上游模块 | 衔接点 | 本期是否改动 |
|---|---|---|
| 场景包 v2 | 读 `roles[].avatar/voice`、`avatar.preferred/rate` | **不改**（`schema.py` 已就位） |
| TTS 服务 | 统一 `synthesize()` 返回音频 + 时间轴；`speech_rate` 下传 | 需扩展返回结构（向后兼容） |
| 播放器 | 提供 `currentTime` / `playing` / 可打断能力；`AnalyserNode` 单例 | 需提供 RMS 订阅接口 |
| 会话状态机 | 复用 `idle/recording/thinking/speaking/finished/error` | 不另立状态 |
| 设置页 | "语音与形象" tab 增加"管理数字人"入口跳角色页 | 小改 |
| 知识工作区 / 场景页 | 不涉及 | — |

**朗读顺序保证**：形象先于声音解析。TTS 请求发出前必须拿到 `voice` 与 `rate`，因此 `resolve` 走同步路径，不引入额外异步等待。

---

## 11. 分阶段任务与完成标准

对应总设计稿 §20 阶段 7（第 11–14 周）的数字人部分，拆成四个可独立验收的任务块：

### 任务 A：资产与解析（后端）

1. 建立 `storage/avatars/` 目录结构与 `manifest.json`；内置 3 个形象（Leo / Sarah / David）+ `default` 占位。
2. 实现 `AvatarRegistry`（启动加载、缓存、损坏回退）。
3. `models.py` 加 `UserPreference` 表，`schemas.py` 加请求/响应模型。
4. 实现 `resolve` 链 + `/api/avatars`、`/api/avatars/{id}`、`/api/avatars/resolve`。

**完成标准**：给定 `scene_id` + `role_id` + 不同偏好组合，解析结果与 §5 表格逐行一致；删除任意资产文件后接口仍返回可用形象且 `fallback_used: true`；pytest 覆盖四级优先级与两种回退。

### 任务 B：声音与语速

1. `voice_service` 暴露渠道可用声音；不可用时回退静态表。
2. `PUT/GET/DELETE /api/preferences/avatar` 三个接口 + 游客策略。
3. TTS 侧确认 `speech_rate` 生效（Edge 走 `rate="+10%"`，腾讯云走 `speed`，沿用 1.0 的 `_rate_to_tencent_speed` 换算）。

**完成标准**：改语速后同一句话实际时长可测出差异；未登录保存返回 401，登录后可往返保存/读取/清除。

### 任务 C：前端角色页与 AvatarStage

1. 新建 `views/AvatarSettings.vue`，替换 `router` 里的 `module('avatar', ...)` 占位。
2. 实现 `AvatarStage.vue`（props 驱动、无业务状态）、`RolePicker.vue`、`VoiceSettings.vue`。
3. 预览舞台提供"演示说话 / 恢复待机 / 在对话中预览"三个动作，行为与参考稿一致。

**完成标准**：角色页形象预览、呈现方式切换、语速滑块、开关全部生效并可持久化（刷新后保持）；呈现方式切到"轻量头像"时 2D 形象隐藏、头像出现；切到"3D"时显示资源占位说明而非空白。

### 任务 D：口型接入对话页

1. `useLipsync.js` 实现 L1/L2/L3 降级，按 `lip_sync` 字段选择。
2. 对话页与面试页把会话状态映射为 `AvatarStage` 的 `state`。
3. 打断路径：停止/插话时先置 `idle` 再更新 UI。

**完成标准**：AI 说话时嘴部有开合、停止后立刻闭合不残留；拔掉 `timeline_url` 时自动退到 L2 仍能动；连音频都不存在时退到 L3；三级都不满足时形象完全静止但不报错。

**阶段 7 整体完成标志**（对齐总设计稿）：2D 数字人真实参与对话，形象与声音按优先级正确落位，口型在三种降级下都可用，角色页保存的偏好在对话页生效。

---

## 12. 取舍、风险与不做的事

### 12.1 关键取舍

| 决策 | 选择 | 理由 | 放弃的收益 |
|---|---|---|---|
| 形象资产形态 | CSS/SVG 分层图形 | 零素材成本、分辨率无关、包体近零 | 视觉表现力上限 |
| 口型主路径 | L1 时间轴为主，L2/L3 保底 | 音画同步是核心体验，但不赌供应商时间戳质量 | 供应商不支持时表现降级 |
| 资产存储 | 文件 + 进程内清单，不入库 | 与"资产随应用分发"的事实一致，避免双向一致性 | 无法按用户定制上传（本期不需要） |
| 偏好存储 | 单表显式列 | 字段级校验与迁移简单 | 扩展新偏好需加列 |
| 状态来源 | 复用会话状态机 | 不引入第二套状态，避免不一致 | 数字人无法独立于会话演示范演 |
| 3D | 只留数据结构与 UI 位 | 3D 完整实现成本高，不绑主线周数 | 首版视觉上限 |

### 12.2 风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| TTS 渠道不返回时间戳 | L1 不可用 | 三级降级；`lip_sync` 字段如实上报实际级别 |
| 资产文件缺失/损坏 | 形象无法渲染 | `resolve` 永不抛异常，回退 `default` 占位 |
| `MediaElementSource` 重复创建抛错 | 音量驱动崩溃 | 播放器单例创建一次，口型只订阅数值 |
| 场景包作者填了不存在的 `avatar` | 形象解析失败 | 只校验格式，运行期回退，不阻断导入 |
| 语速上下限不一致导致 TTS 报错 | 合成失败 | 服务端统一 `clamp(0.5, 2.0)`，前端滑块限制 0.75–1.25 |
| 3D 素材许可与体积 | 无法分发 | 本期不引入 3D 资产，仅留目录约定 |

### 12.3 本期明确不做

- ❌ 摄像头面部动捕、真实 ARKit blendshape
- ❌ 音素级 viseme 精确转换（首版词级近似）
- ❌ 用户上传自定义形象资产
- ❌ 3D 渲染器（Three.js / VRM 运行时）、3D 动作与模型下载
- ❌ 数字人形象的场景内覆盖（同一场景不同角色用不同形象可以，但"按场景临时换脸"不做）
- ❌ 表情情绪识别驱动的面部情绪
- ❌ 形象资源包（bundle）打包分发机制

---

## 参考

- 总设计稿：`EchoTalk-2.0-Design.md` §13 / §14.2 / §14.4 / §20 阶段 7 / §20.1
- 场景包设计稿：`EchoTalk-2.0-Scene-Package-Design.md` §4.7（数字人与场景包的边界）
- 参考交互稿：`echotalk-2.0-frontend.html` 第 59 行 `section#avatar`；截图 `echotalk-2.0-avatar.png`
- 现有实现：`backend/app/scenes/schema.py`（`SceneRole.avatar` / `SceneAvatar`）、`backend/app/content/scenes/cafe_ordering.yaml`（推荐值用法）
- TTS 语速换算沿用 1.0 `backend-1.0/app/services/tts.py`（`_format_rate` / `_rate_to_tencent_speed`）
- [Three.js 官方文档](https://threejs.org/docs/)（3D 阶段参考，本期不使用）

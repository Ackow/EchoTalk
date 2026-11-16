// API 清单与后端路由逐条对应（backend/app/api/endpoints/*.py + app/main.py）。
// 行：[方法, 路径, 鉴权(public|optional|user|admin), 说明, 参数/备注]
export const apiGroups = [
 {
  "id": "auth",
  "title": "账户与认证",
  "intro": "前缀 /api/auth。令牌为不透明随机串，服务端仅存 SHA-256 摘要，有效期 30 天；请求头携带 Authorization: Bearer <token>。",
  "rows": [
   [
    "GET",
    "/api/auth/config",
    "public",
    "读取注册开关（是否限制注册）",
    "—"
   ],
   [
    "POST",
    "/api/auth/register",
    "public",
    "注册并直接登录，返回 {access_token, token_type, user}（201）",
    "body: username(3–50) · password(8–128)；受「限制注册」开关影响；用户名冲突 409"
   ],
   [
    "POST",
    "/api/auth/login",
    "public",
    "登录，返回 {access_token, token_type, user}",
    "body: username · password；凭据错误 401"
   ],
   [
    "POST",
    "/api/auth/logout",
    "user",
    "撤销当前令牌（写入 revoked_at），204",
    "—"
   ],
   [
    "GET",
    "/api/auth/me",
    "user",
    "当前用户信息：会员等级、到期时间、积分余额、auto_use_credits、连续签到",
    "—"
   ],
   [
    "PUT",
    "/api/auth/password",
    "user",
    "修改密码，204",
    "body: current_password · new_password(8–128)"
   ],
   [
    "POST",
    "/api/auth/avatar",
    "user",
    "上传头像（201）",
    "multipart: file（图片）"
   ],
   [
    "GET",
    "/api/auth/avatar/{user_id}",
    "public",
    "读取用户头像文件",
    "—"
   ],
   [
    "DELETE",
    "/api/auth/avatar",
    "user",
    "删除头像，回退为用户名首字母",
    "—"
   ]
  ]
 },
 {
  "id": "scenes",
  "title": "1v1 场景包（ScenePackage v2）",
  "intro": "前缀 /api/scenes。可见性规则：内置场景全员可见；自建/导入场景仅作者可见，发布后（status=published）社区可见。创建/导入/导出受套餐上限与 ZIP 权限控制。",
  "rows": [
   [
    "GET",
    "/api/scenes",
    "optional",
    "场景列表（内置 + 本人自建 + 已发布），含 required_tier、点赞/收藏状态",
    "—"
   ],
   [
    "GET",
    "/api/scenes/templates",
    "public",
    "可用于「从模板创建」的内置模板列表",
    "—"
   ],
   [
    "POST",
    "/api/scenes/validate",
    "public",
    "干跑校验不落库（编辑器实时反馈），成功返回 {valid:true}；失败 422 SCENE_INVALID_PACKAGE + 字段级 details",
    "body: 场景包 JSON（顶层 meta / roles / prompt / … 全部区块）"
   ],
   [
    "POST",
    "/api/scenes/generate-draft",
    "user",
    "AI 一键生成场景草稿（消耗 scene_ai_draft 额度）",
    "body: idea · difficulty（默认 normal）；返回 {draft}"
   ],
   [
    "POST",
    "/api/scenes/import",
    "user",
    "导入 v2 场景包 ZIP（需 allow_zip_import）；ID 冲突需显式选择",
    "multipart: file(.zip)；query: resolve=overwrite|rename；返回 {scene, action}"
   ],
   [
    "POST",
    "/api/scenes/from-template",
    "user",
    "基于内置模板创建自己的场景（201，校验数量上限）",
    "body: template_id · new_id（新场景 ID，需符合 ID 规则）"
   ],
   [
    "POST",
    "/api/scenes",
    "user",
    "创建场景（201）；包体先经 ScenePackage 全量校验，成功触发 onboard_scene 任务进度",
    "body: 场景包 JSON；超出 max_custom_scenes 返回 403"
   ],
   [
    "GET",
    "/api/scenes/{scene_id}",
    "optional",
    "场景完整包详情（私有场景仅作者可读）",
    "—"
   ],
   [
    "PUT",
    "/api/scenes/{scene_id}",
    "user",
    "整体更新自建场景（仅作者）",
    "body: 场景包"
   ],
   [
    "POST",
    "/api/scenes/{scene_id}/duplicate",
    "user",
    "复制为自己的新场景（201，校验数量上限）",
    "—"
   ],
   [
    "DELETE",
    "/api/scenes/{scene_id}",
    "user",
    "删除自建场景（内置不可删）",
    "—"
   ],
   [
    "GET",
    "/api/scenes/{scene_id}/export",
    "user",
    "导出标准 v2 ZIP（manifest.json + scene.yaml + knowledge/ + cover.*）；需 allow_zip_export（Enterprise），并累计下载数",
    "返回 application/zip"
   ],
   [
    "POST",
    "/api/scenes/{scene_id}/cover",
    "user",
    "上传封面（201）",
    "multipart: file"
   ],
   [
    "GET",
    "/api/scenes/{scene_id}/cover",
    "public",
    "读取封面（自建封面优先，内置回退到内置封面）",
    "—"
   ],
   [
    "DELETE",
    "/api/scenes/{scene_id}/cover",
    "user",
    "删除自定义封面",
    "—"
   ],
   [
    "POST",
    "/api/scenes/{scene_id}/publish",
    "user",
    "发布到社区（status=published）",
    "—"
   ],
   [
    "POST",
    "/api/scenes/{scene_id}/unpublish",
    "user",
    "撤回为私有",
    "—"
   ],
   [
    "POST",
    "/api/scenes/{scene_id}/like",
    "user",
    "点赞 / 取消点赞（切换）",
    "—"
   ],
   [
    "POST",
    "/api/scenes/{scene_id}/favorite",
    "user",
    "收藏 / 取消收藏（切换）",
    "—"
   ]
  ]
 },
 {
  "id": "scene-knowledge",
  "title": "场景知识库",
  "intro": "前缀 /api/scenes/{scene_id}/knowledge。分节可见性：user（学习者可读）/ ai_only（仅 AI 检索）；检索为 Hybrid RRF，LightRAG 为图谱增强。",
  "rows": [
   [
    "POST",
    "/api/scenes/{scene_id}/knowledge",
    "user",
    "上传资料文件并分块（201），支持 md/txt 等；同名覆盖",
    "multipart: file；form: visibility=user|ai_only"
   ],
   [
    "GET",
    "/api/scenes/{scene_id}/knowledge",
    "optional",
    "对当前身份可见的资料内容",
    "—"
   ],
   [
    "GET",
    "/api/scenes/{scene_id}/knowledge/sections",
    "optional",
    "分节概览（名称、可见性、块数）",
    "—"
   ],
   [
    "GET",
    "/api/scenes/{scene_id}/knowledge/content",
    "optional",
    "练习页展示用的资料正文（已按可见性过滤）",
    "—"
   ],
   [
    "GET",
    "/api/scenes/{scene_id}/knowledge/documents",
    "optional",
    "资料文档列表",
    "—"
   ],
   [
    "GET",
    "/api/scenes/{scene_id}/knowledge/documents/{document_id}/chunks",
    "optional",
    "某文档的分块明细",
    "—"
   ],
   [
    "GET",
    "/api/scenes/{scene_id}/knowledge/documents/{document_id}/source",
    "optional",
    "读取资料源文本",
    "—"
   ],
   [
    "PUT",
    "/api/scenes/{scene_id}/knowledge/documents/{document_id}/source",
    "user",
    "在线编辑资料源文本并重建分块与向量（仅作者）",
    "body: {text}（非空）"
   ],
   [
    "GET",
    "/api/scenes/{scene_id}/knowledge/graph",
    "optional",
    "LightRAG 实体关系图谱（节点/边）",
    "—"
   ],
   [
    "GET",
    "/api/scenes/{scene_id}/knowledge/search",
    "user",
    "Hybrid RRF 检索，返回命中块与 mode（hybrid/keyword/none）",
    "query: q · top_k"
   ],
   [
    "POST",
    "/api/scenes/{scene_id}/knowledge/reindex",
    "user",
    "全量重建分块向量（换嵌入模型后使用）",
    "—"
   ],
   [
    "GET",
    "/api/scenes/{scene_id}/knowledge/lightrag",
    "user",
    "LightRAG 图谱问答检索",
    "query: q · mode · top_k；未配置 LLM key 返回 400"
   ],
   [
    "POST",
    "/api/scenes/{scene_id}/knowledge/lightrag/rebuild",
    "user",
    "重建 LightRAG 图谱（后台线程异步）",
    "—"
   ],
   [
    "PATCH",
    "/api/scenes/{scene_id}/knowledge/sections/{section_name}",
    "user",
    "修改某分节可见性",
    "body: visibility=user|ai_only"
   ],
   [
    "DELETE",
    "/api/scenes/{scene_id}/knowledge/{document_id}",
    "user",
    "删除资料文件及其分块、向量",
    "—"
   ]
  ]
 },
 {
  "id": "personal",
  "title": "个人知识库",
  "intro": "前缀 /api/knowledge/personal。用户私有工作区（简历、JD、项目文档），可被多角色场景通过 knowledgeDocIds 引用。上传校验 max_knowledge_docs 并消耗 knowledge_embed 额度。",
  "rows": [
   [
    "GET",
    "/api/knowledge/personal",
    "user",
    "个人资料列表",
    "—"
   ],
   [
    "POST",
    "/api/knowledge/personal",
    "user",
    "上传个人资料（201）；同名即覆盖",
    "multipart: file；先校验文档上限再扣 knowledge_embed 额度"
   ],
   [
    "GET",
    "/api/knowledge/personal/search",
    "user",
    "个人库 Hybrid 检索",
    "query: q · top_k"
   ],
   [
    "POST",
    "/api/knowledge/personal/reindex",
    "user",
    "重建个人库向量",
    "—"
   ],
   [
    "GET",
    "/api/knowledge/personal/lightrag",
    "user",
    "个人库图谱问答",
    "query: q · mode · top_k"
   ],
   [
    "POST",
    "/api/knowledge/personal/lightrag/rebuild",
    "user",
    "重建个人库图谱",
    "—"
   ],
   [
    "GET",
    "/api/knowledge/personal/graph",
    "user",
    "个人库实体关系图谱",
    "—"
   ],
   [
    "GET",
    "/api/knowledge/personal/documents/{document_id}/chunks",
    "user",
    "文档分块明细",
    "—"
   ],
   [
    "GET",
    "/api/knowledge/personal/documents/{document_id}/source",
    "user",
    "读取文档源文本",
    "—"
   ],
   [
    "PUT",
    "/api/knowledge/personal/documents/{document_id}/source",
    "user",
    "在线编辑并重建索引",
    "body: {text}（非空）"
   ],
   [
    "DELETE",
    "/api/knowledge/personal/documents/{document_id}",
    "user",
    "删除文档",
    "—"
   ]
  ]
 },
 {
  "id": "sessions",
  "title": "1v1 对话会话（Practice）",
  "intro": "前缀 /api/sessions。每轮由 LangGraph（agent → tools → finalize）驱动，单轮最多 4 次模型调用、6 次工具执行；request_id 幂等，重复提交返回缓存结果。",
  "rows": [
   [
    "POST",
    "/api/sessions",
    "user",
    "创建会话（201）：校验场景可见性与 required_tier，快照场景包并生成问候语",
    "body: scene_id"
   ],
   [
    "GET",
    "/api/sessions",
    "user",
    "本人会话列表（分页）",
    "query: scene_id · status · mode · page · page_size"
   ],
   [
    "GET",
    "/api/sessions/latest",
    "user",
    "某场景最近一次会话（用于续练）",
    "query: scene_id"
   ],
   [
    "GET",
    "/api/sessions/analytics",
    "user",
    "学习分析：练习次数、时长、发音/语法趋势",
    "query: days"
   ],
   [
    "GET",
    "/api/sessions/{session_id}",
    "user",
    "会话详情：状态、目标进度、阶段与全部轮次",
    "—"
   ],
   [
    "GET",
    "/api/sessions/{session_id}/report",
    "user",
    "多维复盘报告：目标完成度、发音五维、语法纠错、强弱词",
    "—"
   ],
   [
    "POST",
    "/api/sessions/{session_id}/turns",
    "user",
    "非流式提交一轮（消耗 practice_turn）",
    "body: request_id · text(≤4000)"
   ],
   [
    "POST",
    "/api/sessions/{session_id}/turns/stream",
    "user",
    "SSE 流式提交一轮（消耗 practice_turn，触发 daily_practice_1 任务）",
    "body: request_id · text · voice_style · include_audio · audio_token；事件见「SSE 事件」"
   ],
   [
    "POST",
    "/api/sessions/{session_id}/suggest-reply",
    "user",
    "AI 参考回复建议（Coach，消耗 practice_coach_hint）",
    "—"
   ],
   [
    "POST",
    "/api/sessions/{session_id}/action",
    "user",
    "场景交互动作（如咖啡厅结账、确认结束卡片）",
    "body: action · payload"
   ],
   [
    "GET",
    "/api/sessions/{session_id}/greeting-audio",
    "user",
    "问候语 MP3（带文件缓存）",
    "query: voice_style · speech_rate(0.75–1.25)"
   ],
   [
    "GET",
    "/api/sessions/{session_id}/turns/{turn_id}/audio",
    "user",
    "某轮 AI 回复 MP3",
    "query: voice_style · speech_rate"
   ],
   [
    "GET",
    "/api/sessions/{session_id}/turns/{turn_id}/user-audio",
    "user",
    "用户当轮录音 WAV（仅本人）",
    "—"
   ]
  ]
 },
 {
  "id": "debate",
  "title": "1vN 多角色（辩论 / 群面圆桌）",
  "intro": "前缀 /api/debate。scene_type=debate（正反辩论）或 panel（多面试官圆桌），均由 roles_config（2–4 位 AI 角色）、stages_config（≤6 阶段）、tools_config 编排。",
  "rows": [
   [
    "GET",
    "/api/debate/topics",
    "optional",
    "多角色场景列表（内置 + 本人自建 + 已发布），含 roles / stages / tools / maxTurns",
    "—"
   ],
   [
    "POST",
    "/api/debate/topics/generate",
    "user",
    "AI 生成多角色场景草稿",
    "body: idea(2–300) · sceneType=debate|panel"
   ],
   [
    "POST",
    "/api/debate/topics",
    "user",
    "创建多角色场景（201，校验 max_custom_debates）",
    "body: DebateTopicIn（见多角色开发章节）"
   ],
   [
    "PUT",
    "/api/debate/topics/{topic_id}",
    "user",
    "更新自建场景（仅作者）",
    "body: DebateTopicIn"
   ],
   [
    "DELETE",
    "/api/debate/topics/{topic_id}",
    "user",
    "删除自建场景（内置不可删）",
    "—"
   ],
   [
    "POST",
    "/api/debate/topics/{topic_id}/cover",
    "user",
    "上传封面（201）",
    "multipart: file"
   ],
   [
    "GET",
    "/api/debate/topics/{topic_id}/cover",
    "public",
    "读取封面（内置封面直读 content/debates/covers）",
    "—"
   ],
   [
    "DELETE",
    "/api/debate/topics/{topic_id}/cover",
    "user",
    "删除封面",
    "—"
   ],
   [
    "POST",
    "/api/debate/topics/{topic_id}/like",
    "user",
    "点赞切换",
    "—"
   ],
   [
    "POST",
    "/api/debate/topics/{topic_id}/favorite",
    "user",
    "收藏切换",
    "—"
   ],
   [
    "POST",
    "/api/debate/topics/{topic_id}/publish",
    "user",
    "发布到社区",
    "—"
   ],
   [
    "POST",
    "/api/debate/topics/{topic_id}/unpublish",
    "user",
    "撤回为私有",
    "—"
   ],
   [
    "POST",
    "/api/debate/topics/import",
    "user",
    "导入多角色场景 ZIP（201，需 allow_zip_import）",
    "multipart: file"
   ],
   [
    "GET",
    "/api/debate/topics/{topic_id}/export",
    "user",
    "导出 ZIP（manifest.json + debate.json + cover.*，需 allow_zip_export）",
    "—"
   ],
   [
    "POST",
    "/api/debate/topics/{topic_id}/duplicate",
    "user",
    "复制为自己的场景（201）",
    "—"
   ],
   [
    "POST",
    "/api/debate/sessions",
    "user",
    "创建会话（201）：校验 required_tier，生成开场发言",
    "body: topic_id · user_side=pro|con · difficulty_level=supportive|balanced|sharp"
   ],
   [
    "GET",
    "/api/debate/sessions/latest",
    "user",
    "某场景最近会话",
    "query: topic_id"
   ],
   [
    "GET",
    "/api/debate/sessions/{session_id}",
    "user",
    "会话详情与全部发言",
    "—"
   ],
   [
    "POST",
    "/api/debate/sessions/{session_id}/turns",
    "user",
    "提交用户发言并获取 AI 角色回应（消耗 debate_turn，触发 daily_debate_1）",
    "body: text(≤2000) · is_voice · duration(1–300)；返回 {session, new_messages}"
   ],
   [
    "POST",
    "/api/debate/sessions/{session_id}/suggest-reply",
    "user",
    "生成用户可参考的回应建议",
    "—"
   ],
   [
    "POST",
    "/api/debate/sessions/{session_id}/finish",
    "user",
    "结束并生成裁决书，首次结算 40 XP",
    "返回 {session, verdict, xp_awarded}"
   ]
  ]
 },
 {
  "id": "review",
  "title": "复习计划（SM-2）",
  "intro": "前缀 /api/review。对话纠错、发音弱点、多角色推荐表达与听力错题会自动入库；评级采用 again / hard / good / easy。",
  "rows": [
   [
    "GET",
    "/api/review",
    "user",
    "到期与全部卡片列表",
    "query: sync（是否先同步来源）"
   ],
   [
    "POST",
    "/api/review/sync",
    "user",
    "从练习会话、发音与语法纠错同步生成卡片（source_key 幂等）",
    "—"
   ],
   [
    "POST",
    "/api/review",
    "user",
    "手动新增卡片，触发 daily_review_10 进度",
    "body: kind · prompt · answer · phonetic · note · context_text · scene_name"
   ],
   [
    "PATCH",
    "/api/review/{item_id}",
    "user",
    "编辑卡片或标记 mastered",
    "body: 上述字段 · status · mastery"
   ],
   [
    "DELETE",
    "/api/review/{item_id}",
    "user",
    "删除卡片",
    "—"
   ],
   [
    "POST",
    "/api/review/{item_id}/submit",
    "user",
    "提交一次复习评级，更新 ease_factor / interval_days / due_at",
    "body: rating=again|hard|good|easy"
   ]
  ]
 },
 {
  "id": "listening",
  "title": "听力工作室与 XP",
  "intro": "日常 / 四六级 / 电台 / 演讲四频道；练习单题奖励 5 XP，完成单元奖励单元 xp，每日目标 60 XP。",
  "rows": [
   [
    "GET",
    "/api/listening/units",
    "optional",
    "听力单元列表（含当前用户进度统计）",
    "—"
   ],
   [
    "POST",
    "/api/listening/attempts",
    "user",
    "提交单题作答，答对 +5 XP，触发 daily_listening_1",
    "body: unitId · exerciseId · exerciseType · isCorrect · isIndependent · hintsUsed[] · errorTag · stepIndex · totalSteps"
   ],
   [
    "POST",
    "/api/listening/units/{unit_id}/complete",
    "user",
    "标记单元完成并结算单元 XP",
    "—"
   ],
   [
    "POST",
    "/api/listening/review-add",
    "user",
    "将听力错题加入复习计划",
    "body: unitId · exerciseId · prompt · answer · note · contextText"
   ],
   [
    "GET",
    "/api/listening/profile",
    "user",
    "XP 档案：总 XP、今日 XP、连续天数、签到奖励",
    "—"
   ],
   [
    "POST",
    "/api/listening/checkin",
    "user",
    "听力模块每日签到（XP）",
    "—"
   ],
   [
    "GET",
    "/api/listening/audio",
    "public",
    "按文本流式合成听力音频",
    "query: text · rate · style"
   ]
  ]
 },
 {
  "id": "speech",
  "title": "语音识别、解释与合成",
  "intro": "ASR 使用腾讯云 Flash ASR（服务端持有凭据）；TTS 使用 edge-tts，声音白名单见「TTS 声音」。",
  "rows": [
   [
    "GET",
    "/api/speech/status",
    "public",
    "ASR 是否已配置、录音上限与采样率",
    "返回 {configured, max_duration, sample_rate}"
   ],
   [
    "POST",
    "/api/speech/transcriptions",
    "user",
    "英文语音转写",
    "multipart: file（0.3–60 秒、16kHz 单声道 PCM16 WAV）；未配置返回 503 ASR_NOT_CONFIGURED"
   ],
   [
    "POST",
    "/api/speech/explain",
    "user",
    "划词/划句解释：音标、语境释义、口语提示",
    "body: text(≤240) · context(≤600)"
   ],
   [
    "GET",
    "/api/tts/voices",
    "public",
    "声音清单及当前可用性探测",
    "—"
   ],
   [
    "POST",
    "/api/tts/synthesize",
    "public",
    "文本转语音（返回 audio/mpeg）",
    "body: text(≤500) · voice_style · speech_rate(0.75–1.25)"
   ]
  ]
 },
 {
  "id": "avatars",
  "title": "数字人",
  "intro": "偏好按「用户 × 场景」存储（scene_id 空串=跟随推荐）；目录含内置角色与用户自建角色，可公开、克隆。",
  "rows": [
   [
    "GET",
    "/api/preferences/avatar",
    "user",
    "读取偏好",
    "query: scene_id"
   ],
   [
    "PUT",
    "/api/preferences/avatar",
    "user",
    "整体覆盖保存偏好，触发 onboard_avatar",
    "body: avatar_id · voice_style · scene_id · speech_rate(0.75–1.25) · lip_sync_enabled"
   ],
   [
    "DELETE",
    "/api/preferences/avatar",
    "user",
    "重置为跟随推荐",
    "query: scene_id"
   ],
   [
    "GET",
    "/api/avatars",
    "optional",
    "角色目录（内置 + 自建 + 已克隆）",
    "—"
   ],
   [
    "GET",
    "/api/avatars/market",
    "optional",
    "数字人市场（公开角色）",
    "—"
   ],
   [
    "POST",
    "/api/avatars/{avatar_id}/clone",
    "user",
    "克隆市场角色到自己的目录",
    "—"
   ],
   [
    "DELETE",
    "/api/avatars/{avatar_id}/clone",
    "user",
    "取消克隆",
    "—"
   ],
   [
    "POST",
    "/api/avatars",
    "user",
    "创建自定义角色",
    "body: display_name · theme · tagline · description · greeting · default_voice · appearance"
   ],
   [
    "PUT",
    "/api/avatars/{avatar_id}",
    "user",
    "更新自建角色",
    "body: 同上"
   ],
   [
    "POST",
    "/api/avatars/{avatar_id}/publish",
    "user",
    "发布/取消发布到市场",
    "query: is_public（默认 true；false 为取消发布）"
   ],
   [
    "DELETE",
    "/api/avatars/{avatar_id}",
    "user",
    "删除自建角色",
    "—"
   ]
  ]
 },
 {
  "id": "saas",
  "title": "会员、积分与任务",
  "intro": "前缀 /api/saas。共享额度池 + 超额积分扣减，详见「SaaS 计量」。会员与积分目前通过兑换码或管理员发放获得，模拟收银台已关闭。",
  "rows": [
   [
    "GET",
    "/api/saas/me",
    "user",
    "会员概览：等级、积分、共享池进度百分比、auto_use_credits",
    "—"
   ],
   [
    "PATCH",
    "/api/saas/me/settings",
    "user",
    "修改「额度用尽后自动消耗积分」开关",
    "body: auto_use_credits"
   ],
   [
    "GET",
    "/api/saas/plans",
    "public",
    "三档套餐对比、加油包目录、生效中的限时活动与 action_meta",
    "—"
   ],
   [
    "POST",
    "/api/saas/checkin",
    "user",
    "每日签到，发放积分（乘套餐 checkin_multiplier 与活动倍率）",
    "—"
   ],
   [
    "GET",
    "/api/saas/tasks",
    "user",
    "任务列表与当期进度",
    "—"
   ],
   [
    "POST",
    "/api/saas/tasks/{task_code}/claim",
    "user",
    "领取任务奖励（回声积分 + 段位 XP）",
    "—"
   ],
   [
    "POST",
    "/api/saas/checkout/mock",
    "user",
    "【已关闭】直接模拟订阅/购买，恒返回 403 MOCK_CHECKOUT_DISABLED；请改用兑换码或管理员发放",
    "body（保留结构）: order_type=plan_upgrade|credit_pack · target_tier · billing_cycle · credit_pack_code"
   ],
   [
    "POST",
    "/api/saas/redeem",
    "user",
    "核销兑换码",
    "body: code(4–40)"
   ],
   [
    "GET",
    "/api/saas/ledger",
    "user",
    "本人积分账本",
    "query: page · page_size"
   ]
  ]
 },
 {
  "id": "admin-core",
  "title": "管理端：登录与用户",
  "intro": "前缀 /api/admin。除 /admin/login 外所有接口都要求 is_admin=1，否则 403 FORBIDDEN。",
  "rows": [
   [
    "POST",
    "/api/admin/login",
    "public",
    "管理员登录（非管理员账号被拒绝）",
    "body: username · password"
   ],
   [
    "GET",
    "/api/admin/dashboard",
    "admin",
    "运营看板：用户、会话、场景、Token 概览",
    "—"
   ],
   [
    "GET",
    "/api/admin/users",
    "admin",
    "用户列表",
    "query: q · is_admin · page · page_size"
   ],
   [
    "POST",
    "/api/admin/users",
    "admin",
    "创建用户",
    "body: username(3–50) · password(8–128) · is_admin"
   ],
   [
    "PATCH",
    "/api/admin/users/{user_id}",
    "admin",
    "修改用户（不能降级/删除自己）",
    "body: is_admin · password(8–128)（均可选）"
   ],
   [
    "DELETE",
    "/api/admin/users/{user_id}",
    "admin",
    "删除用户",
    "—"
   ],
   [
    "POST",
    "/api/admin/users/batch-delete",
    "admin",
    "批量删除用户",
    "body: {ids[]}（1–200 项）"
   ],
   [
    "POST",
    "/api/admin/users/{user_id}/grant",
    "admin",
    "手动调整会员等级/天数与积分",
    "body: plan_tier · plan_days(0–3650) · credits_delta(±100000) · remark"
   ],
   [
    "GET",
    "/api/admin/settings/registration",
    "admin",
    "读取「限制注册」开关",
    "—"
   ],
   [
    "PUT",
    "/api/admin/settings/registration",
    "admin",
    "更新「限制注册」开关",
    "body: {registration_restricted: bool}"
   ]
  ]
 },
 {
  "id": "admin-content",
  "title": "管理端：场景、多角色、数字人与学习数据",
  "intro": "",
  "rows": [
   [
    "GET",
    "/api/admin/scenes",
    "admin",
    "1v1 场景列表",
    "query: q · category · mode · source · status_filter · page · page_size"
   ],
   [
    "GET",
    "/api/admin/scenes/{scene_id}",
    "admin",
    "场景详情",
    "—"
   ],
   [
    "PATCH",
    "/api/admin/scenes/{scene_id}",
    "admin",
    "修改场景元数据或整包",
    "body: name · description · category · mode · difficulty · status(private|published) · package_json（均可选）"
   ],
   [
    "DELETE",
    "/api/admin/scenes/{scene_id}",
    "admin",
    "删除场景",
    "—"
   ],
   [
    "POST",
    "/api/admin/scenes/batch-status",
    "admin",
    "批量发布/下架",
    "body: ids[]（≤200）· status=private|published"
   ],
   [
    "POST",
    "/api/admin/scenes/batch-delete",
    "admin",
    "批量删除",
    "body: {ids[]}（1–200 项）"
   ],
   [
    "GET",
    "/api/admin/sessions",
    "admin",
    "1v1 会话列表",
    "query: user_id · scene_id · status_filter · q · page · page_size"
   ],
   [
    "GET",
    "/api/admin/sessions/{session_id}",
    "admin",
    "会话详情",
    "—"
   ],
   [
    "DELETE",
    "/api/admin/sessions/{session_id}",
    "admin",
    "删除会话",
    "—"
   ],
   [
    "POST",
    "/api/admin/sessions/batch-delete",
    "admin",
    "批量删除会话",
    "body: {ids[]}（1–200 项）"
   ],
   [
    "GET",
    "/api/admin/debates",
    "admin",
    "多角色场景列表",
    "query: q · scene_type · status_filter · page · page_size"
   ],
   [
    "PATCH",
    "/api/admin/debates/{topic_id}",
    "admin",
    "仅允许修改 status / required_tier / title_zh / difficulty_label",
    "body: 上述字段（均可选）"
   ],
   [
    "DELETE",
    "/api/admin/debates/{topic_id}",
    "admin",
    "删除多角色场景",
    "—"
   ],
   [
    "GET",
    "/api/admin/debate-sessions",
    "admin",
    "多角色会话列表",
    "query: q · scene_type · status_filter · page · page_size"
   ],
   [
    "GET",
    "/api/admin/debate-sessions/{session_id}",
    "admin",
    "多角色会话详情",
    "—"
   ],
   [
    "DELETE",
    "/api/admin/debate-sessions/{session_id}",
    "admin",
    "删除多角色会话",
    "—"
   ],
   [
    "GET",
    "/api/admin/avatars/catalog",
    "admin",
    "数字人目录",
    "—"
   ],
   [
    "GET",
    "/api/admin/avatars/preferences",
    "admin",
    "用户偏好列表",
    "query: user_id · scene_id · avatar_id · voice_style · page · page_size"
   ],
   [
    "PUT",
    "/api/admin/avatars/preferences",
    "admin",
    "代为设置用户偏好",
    "body: user_id · scene_id · avatar_id · voice_style · speech_rate · lip_sync_enabled"
   ],
   [
    "DELETE",
    "/api/admin/avatars/preferences",
    "admin",
    "删除某用户某场景偏好",
    "query: user_id · scene_id"
   ],
   [
    "POST",
    "/api/admin/avatars/preferences/batch-delete",
    "admin",
    "批量删除偏好",
    "body: items[{user_id, scene_id}]（≤200）"
   ],
   [
    "GET",
    "/api/admin/avatars/presets",
    "admin",
    "角色预设列表",
    "query: q · is_builtin · is_public · owner_id · page · page_size"
   ],
   [
    "PATCH",
    "/api/admin/avatars/presets/{avatar_id}",
    "admin",
    "修改角色预设",
    "body: display_name · description · tagline · greeting · theme · default_voice · is_public · appearance"
   ],
   [
    "DELETE",
    "/api/admin/avatars/presets/{avatar_id}",
    "admin",
    "删除角色预设",
    "—"
   ],
   [
    "POST",
    "/api/admin/avatars/presets/batch-public",
    "admin",
    "批量公开/取消公开",
    "body: ids[]（≤200）· is_public"
   ],
   [
    "POST",
    "/api/admin/avatars/presets/batch-delete",
    "admin",
    "批量删除",
    "body: {ids[]}（1–200 项）"
   ],
   [
    "GET",
    "/api/admin/knowledge",
    "admin",
    "知识库文档列表（scene / personal）",
    "query: scope · q · page · page_size"
   ],
   [
    "DELETE",
    "/api/admin/knowledge/{scope}/{doc_id}",
    "admin",
    "删除文档",
    "—"
   ],
   [
    "GET",
    "/api/admin/knowledge/lightrag-config",
    "admin",
    "读取 LightRAG 后台执行开关",
    "—"
   ],
   [
    "PUT",
    "/api/admin/knowledge/lightrag-config",
    "admin",
    "动态启停 LightRAG 后台执行",
    "body: {enabled: bool}"
   ],
   [
    "GET",
    "/api/admin/reviews",
    "admin",
    "复习卡片列表",
    "query: q · page · page_size"
   ],
   [
    "DELETE",
    "/api/admin/reviews/{item_id}",
    "admin",
    "删除卡片",
    "—"
   ],
   [
    "GET",
    "/api/admin/listening/attempts",
    "admin",
    "听力作答记录",
    "query: page · page_size"
   ],
   [
    "GET",
    "/api/admin/listening/units",
    "admin",
    "听力单元列表",
    "—"
   ],
   [
    "POST",
    "/api/admin/listening/import",
    "admin",
    "导入/更新听力单元",
    "body: id · channel · cetLevel · cetSection · channelLabel · level · title · subtitle · duration · xp · accent · exercises…"
   ],
   [
    "DELETE",
    "/api/admin/listening/units/{unit_id}",
    "admin",
    "删除听力单元",
    "—"
   ]
  ]
 },
 {
  "id": "admin-saas",
  "title": "管理端：SaaS 与成本核算",
  "intro": "热配置，立即生效，无需重启。",
  "rows": [
   [
    "GET",
    "/api/admin/saas/plans",
    "admin",
    "套餐配置与 action_meta",
    "—"
   ],
   [
    "PUT",
    "/api/admin/saas/plans/{tier}",
    "admin",
    "更新套餐（价格、额度池、上限、ZIP 权限、quotas_json）",
    "body: AdminPlanUpdate"
   ],
   [
    "GET",
    "/api/admin/saas/tasks",
    "admin",
    "任务定义",
    "—"
   ],
   [
    "PUT",
    "/api/admin/saas/tasks/{task_code}",
    "admin",
    "更新任务奖励/启停",
    "body: AdminTaskUpdate"
   ],
   [
    "GET",
    "/api/admin/saas/campaigns",
    "admin",
    "限时活动列表",
    "—"
   ],
   [
    "POST",
    "/api/admin/saas/campaigns",
    "admin",
    "创建活动（倍率 1–10、限免 action 列表、起止时间）",
    "body: AdminCampaignCreate"
   ],
   [
    "PATCH",
    "/api/admin/saas/campaigns/{campaign_id}",
    "admin",
    "修改活动",
    "body: AdminCampaignUpdate"
   ],
   [
    "DELETE",
    "/api/admin/saas/campaigns/{campaign_id}",
    "admin",
    "删除活动",
    "—"
   ],
   [
    "GET",
    "/api/admin/saas/orders",
    "admin",
    "订单列表",
    "query: page · page_size"
   ],
   [
    "GET",
    "/api/admin/saas/ledger",
    "admin",
    "全站积分账本",
    "query: user_id · page · page_size"
   ],
   [
    "GET",
    "/api/admin/saas/redeem-codes",
    "admin",
    "兑换码列表",
    "query: page · page_size"
   ],
   [
    "POST",
    "/api/admin/saas/redeem-codes",
    "admin",
    "批量生成兑换码",
    "body: count(1–50) · reward_type=credits|plan_days · reward_credits · reward_tier · reward_days · prefix · note"
   ],
   [
    "GET",
    "/api/admin/saas/billing-config",
    "admin",
    "读取计费换算与 Token 单价",
    "—"
   ],
   [
    "PUT",
    "/api/admin/saas/billing-config",
    "admin",
    "更新计费换算与 Token 单价",
    "body: tokens_per_credit · prompt_price_per_million · completion_price_per_million"
   ],
   [
    "GET",
    "/api/admin/token-stats",
    "admin",
    "Token 消耗聚合 + 周期订阅收入 / API 成本 / 净毛利",
    "query: days · category · model · user_id · page · page_size"
   ]
  ]
 },
 {
  "id": "service",
  "title": "服务探针",
  "intro": "无需鉴权，供部署编排使用。",
  "rows": [
   [
    "GET",
    "/api/health",
    "public",
    "存活探针：进程正常即返回 {status:\"ok\"}",
    "—"
   ],
   [
    "GET",
    "/api/ready",
    "public",
    "就绪探针：执行 SELECT 1；数据库不可用返回 503 {status:\"unavailable\"}",
    "—"
   ]
  ]
 }
]

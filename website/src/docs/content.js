// 产品文档静态内容：环境变量、错误码、场景包规范、多角色数据模型、SaaS 默认配置与代码示例。
// 数值与枚举均来自 backend/app 源码；修改后端默认值时请同步更新。

export const envVars = [
  ['ECHOTALK_DB_HOST / PORT / NAME / USER', '127.0.0.1 / 3307 / echotalk / echotalk_app', 'MySQL 连接；生产同机部署通常用 3306'],
  ['ECHOTALK_DB_PASSWORD', '（必填）', '数据库密码，缺失时启动即报错'],
  ['ECHOTALK_API_HOST / PORT', '127.0.0.1 / 8000', 'API 监听地址与端口；对外统一经 Nginx HTTPS'],
  ['ECHOTALK_CORS_ORIGINS', 'localhost:5173/5174 …', '逗号分隔的允许来源；Electron file:// 需包含 null'],
  ['ECHOTALK_CHAT_API_KEY / MODEL / API_BASE', '— / — / https://api.openai.com/v1', '对话 Agent 模型（须支持 Chat Completions 工具调用）；未配置时对话与多角色返回 503 CHAT_NOT_CONFIGURED'],
  ['ECHOTALK_ASR_APP_ID / SECRET_ID / SECRET_KEY', '—', '腾讯云 Flash ASR 凭据，仅后端持有'],
  ['ECHOTALK_XFYUN_APP_ID / API_KEY / API_SECRET', '—', '讯飞 ISE 口语评测；未配置时降级为模拟评分'],
  ['ECHOTALK_SILICONFLOW_API_KEY', '—', '嵌入服务 key；未配置时检索退化为纯关键词'],
  ['ECHOTALK_EMBEDDING_API_BASE / MODEL / DIM', 'https://api.siliconflow.cn/v1 / BAAI/bge-m3 / 1024', '嵌入模型；更换后必须全量 reindex'],
  ['ECHOTALK_EMBEDDING_TIMEOUT / BATCH', '15 / 16', '单次请求超时（秒）/ 单请求文本条数'],
  ['ECHOTALK_LIGHTRAG_ENABLED', 'true', 'LightRAG 总开关，管理端可运行时启停'],
  ['ECHOTALK_LIGHTRAG_LLM_API_BASE / API_KEY / MODEL', 'https://api.siliconflow.cn/v1 / — / deepseek-ai/DeepSeek-V3', '图谱实体抽取 LLM（建议 ≥32B 非推理模型），与嵌入 key 独立'],
  ['ECHOTALK_LIGHTRAG_LLM_TIMEOUT / ECHOTALK_LIGHTRAG_DIR', '120 / backend/storage/lightrag', '抽取超时（秒）/ 图谱存储目录'],
  ['ECHOTALK_ADMIN_USERNAME / PASSWORD', 'admin / admin123456', '仅 init_db.py 在库中无管理员时使用，上线前必须修改'],
]

export const errorCodes = [
  ['400', 'bad_request', '默认业务错误（参数不合法、场景包不是 .zip 等）'],
  ['401', 'unauthorized', '未携带令牌 / 令牌失效 / 凭据错误'],
  ['403', 'FORBIDDEN', '需要管理员权限，或无权操作他人资源'],
  ['403', 'PLAN_REQUIRED', '套餐不足（场景 required_tier、ZIP 导入导出、池满且该功能不允许超额）'],
  ['403', 'PLAN_LIMIT_REACHED', '自建场景 / 多角色 / 知识库文档数量达到套餐上限'],
  ['403', 'QUOTA_EXCEEDED', '免费额度池用满且用户关闭了「自动消耗积分」'],
  ['403', 'INSUFFICIENT_CREDITS', '免费额度池用满且积分不足以抵扣'],
  ['403', 'REGISTRATION_DISABLED', '管理端开启了「限制注册」'],
  ['403', 'MOCK_CHECKOUT_DISABLED', '直接模拟订阅 / 购买已关闭，请使用兑换码'],
  ['403', 'DEBATE_BUILTIN_READONLY / SCENE_FORBIDDEN', '内置多角色场景只读；仅作者可修改自建场景'],
  ['404', 'SCENE_NOT_FOUND / DEBATE_TOPIC_NOT_FOUND / DEBATE_NOT_FOUND / SESSION_NOT_FOUND', '资源不存在或不属于当前用户'],
  ['409', 'conflict / SCENE_ID_CONFLICT', '用户名已被注册；导入场景 ID 冲突（需 resolve=overwrite|rename）'],
  ['409', 'SCENE_BUILTIN_READONLY', '内置 1v1 场景只读，可从模板创建或复制'],
  ['409', 'SESSION_VERSION_CONFLICT / SESSION_FINISHED / TURN_ID_CONFLICT', '会话被并发更新 / 会话已结束 / 同一 request_id 提交了不同输入'],
  ['422', 'SCENE_INVALID_PACKAGE', '场景包校验失败，details 为字段级错误列表'],
  ['422', 'SCENE_INVALID_EXPRESSION / SCENE_PACKAGE_INCOMPATIBLE', '表达式非法 / 包要求的 min_app 高于当前版本'],
  ['422', 'ASR_INVALID_AUDIO / ASR_AUDIO_SIZE / TTS_VOICE_UNKNOWN', '录音格式或大小不符 / 声音预设不在白名单'],
  ['502', 'CHAT_MODEL_FAILED / CHAT_INVALID_RESPONSE / CHAT_TOOL_LIMIT / ASR_PROVIDER_FAILED', '上游模型 / ASR 失败、返回非法工具调用、超出工具预算'],
  ['503', 'CHAT_NOT_CONFIGURED / ASR_NOT_CONFIGURED / db_unavailable', '对话模型 / ASR 未配置；就绪探针数据库不可用'],
  ['504', 'TTS_TIMEOUT', '语音合成超时'],
]

export const sceneBlocks = [
  ['meta', '是', 'id（^[a-z][a-z0-9_]{1,49}$，一经创建不可变 SCENE_ID_IMMUTABLE）· name(1–100) · description · category(daily|business|career|academic|custom) · difficulty(entry|easy|normal|hard|expert) · mode(conversation|interview|debate) · version(默认 2) · compat.min_app(默认 2.0.0) · author · tags(≤8)。历史难度（CEFR / 简单普通困难）导入时自动归一为五级枚举。'],
  ['roles', '是', '1–4 个角色：id(^[a-z][a-z0-9_]{0,29}$，唯一) · display_name(1–50) · title · personality · voice（TTS 推荐）· avatar（形象推荐）· backstage（true 表示不参与对话的评估角色）。'],
  ['prompt', '是', 'system（必填，System Prompt 模板）· greeting（问候语）· params（≤16）：key · type(string|number|boolean) · default · editable · tip。占位符只允许 {param} 与 {roles.<id>.<field>}。'],
  ['objectives', '否', '≤8 个训练目标：id · label(1–60) · skill（关联技能图，如 speaking.politeness）· check（白名单表达式，程序判定达成，达成后保持）。'],
  ['state', '否', '场景状态初值（任意 JSON 键值）。写状态的工具只能修改此处声明的根键，且类型必须一致；stage / stage_turns / turn_count 为保留键。'],
  ['tools', '否', 'allowed（工具白名单，⊆ 注册表）· config（按工具名的静态配置，键 ⊆ allowed）。'],
  ['coordination', '否', '多角色协调：order 为角色 id 顺序数组，引用必须存在于 roles。'],
  ['stages', '否', '≤8 个阶段：id · name(1–60) · guidance（软引导，注入提示词）· exit_when（声明式推进条件）。'],
  ['finish', '是', 'when（必填表达式）· max_turns(2–200，默认 30，兜底) · on_finish（目前仅 request_feedback）。'],
  ['knowledge', '否', 'files（≤20）：path（相对 knowledge/）· visibility(user|ai_only) · sections[]；retrieval.default_top_k（默认 4）。'],
  ['evaluation', '否', 'dimensions（≤6）：id · label · weight(0,1] · source(state|llm) · hints[]；notes（评估备注）。'],
  ['guardrails', '否', 'language · min_words(1–100) · keyword_tips[{match,tip}] · off_topic{domain_keywords[],action:warn} · max_warnings_per_turn(1–5，默认 1)。'],
  ['avatar', '否', 'preferred（推荐形象 id）· rate(0.5–2.0 推荐语速)；仅推荐，无副作用。'],
]

export const sceneTools = [
  ['search_knowledge', 'query(1–500) · top_k(1–8，默认 4)', '检索本场景资料（Hybrid RRF），范围由当前场景闭包决定，不可跨场景。'],
  ['update_scene_state', 'key · value · evidence', '写入已声明的<标量>状态；类型需与声明一致，dict / list 被拒绝。'],
  ['append_state_item', 'key · item(string|object) · evidence', '向已声明的列表状态追加（上限 50 项），目标必须是 list。'],
  ['remove_state_item', 'key · match · evidence', '按关键词移除列表中第一个匹配项。'],
  ['adjust_state_number', 'key · delta · evidence', '增减已声明的数值状态（int 保持整型，保留 2 位小数）。'],
  ['calculate_expression', 'expression(≤200)', 'AST 白名单四则运算与 round / min / max / abs，禁止变量与属性访问。'],
  ['lookup_word', 'word(≤80)', '在场景资料中检索词语释义（取前 2 条命中）。'],
  ['get_hint', 'focus(≤200)', '返回当前目标（前 4 个）与 keyword_tips（前 3 条），供给学习者一句话提示。'],
  ['next_interview_stage', 'reason(≤200)', '请求进入下一阶段，实际切换由 advance() 在轮末统一执行。'],
  ['add_review_task', 'topic(≤160) · note(≤300)', '记录待复习表达（会话内最多 20 条），随报告 / 复习计划同步。'],
]

export const topicFields = [
  ['sceneType', 'debate | panel', '场景形态，默认 debate'],
  ['titleZh', '2–180 字', '中文标题（必填）'],
  ['motionEn', '4–1000 字', '英文议题 / 场景任务描述（必填），开场与提示词引用'],
  ['category', 'tech | workplace | education | society', '分类，对应中文名：科技伦理 / 职场文化 / 教育成长 / 社会生活'],
  ['difficulty', 'beginner | intermediate | advanced', '难度，对应：入门 / 进阶 / 挑战'],
  ['duration', '≤32 字，如「8 分钟」', '决定最大用户轮数（≤6 分钟 4 轮 / ≤9 分钟 6 轮 / 其余 8 轮）'],
  ['userRoleLabel', '≤64 字', '用户身份文案，panel 开场与记录里展示（默认「候选人 / 主讲人」）'],
  ['proSummary / conSummary', '各 ≤500 字', 'debate 的正反方要点；panel 可写「亮点 / 风险」'],
  ['backgroundContext', '≤1500 字', '背景资料，每轮注入提示词'],
  ['keyExpressions', 'string[]', '目标英文表达，前 6 条注入提示词'],
  ['defaultStyle', 'supportive | balanced | sharp', '默认对手强度（创建会话时可覆盖）'],
  ['roles', 'DebateRoleIn[≤4]', '角色编排，见下表；为空则回退旧 opponent* 字段'],
  ['stages', 'DebateStageIn[≤6]', '阶段编排；为空则使用默认四阶段'],
  ['tools', 'string[]', '启用的工具 ID；API 默认 [search_knowledge, rebuttal_hint, judge_score]'],
  ['knowledgeDocIds', 'int[]', '绑定的个人资料文档 ID（需 search_knowledge）'],
  ['opponentName / Title / Persona / Voice / AvatarId', '兼容旧字段', '由 roles 自动派生；仅在未提供 roles 时作为主对手来源'],
  ['status / required_tier', 'private|published / free|pro|enterprise', '不在创建体内：发布走 /publish，required_tier 仅管理端可改（默认 free）'],
]

export const actionKeys = [
  ['practice_turn', '1v1 语音对话轮次', '语音对话', 'POST /api/sessions/{id}/turns 与 /turns/stream'],
  ['practice_coach_hint', '实时 Coach 话术提示', '语音对话', 'POST /api/sessions/{id}/suggest-reply'],
  ['practice_report_deep', '1v1 深度复盘报告', '语音对话', '已在套餐中配置额度，当前接口未接入计量'],
  ['debate_turn', '1vN 多角色辩论 / 群面轮次', '多角色对话', 'POST /api/debate/sessions/{id}/turns'],
  ['debate_verdict_report', '1vN 赛后裁决与录用评估', '多角色对话', '已在套餐中配置额度，当前 finish 接口未接入计量'],
  ['listening_explain', '听力划词解释 / AI 助教', '听力工作室', '已在套餐中配置额度，当前 /speech/explain 未接入计量'],
  ['scene_ai_draft', 'AI 一键生成场景 / 多角色草稿', '场景编辑器', 'POST /api/scenes/generate-draft（多角色草稿接口 /debate/topics/generate 当前未计量）'],
  ['knowledge_embed', '知识库文档解析与向量化', '知识工作区', 'POST /api/knowledge/personal'],
]

export const planRows = [
  ['月 / 年价格（元）', '0 / 0', '29 / 268', '199 / 1880'],
  ['每月赠送积分', '0', '1200', '10000'],
  ['每日共享免费池（点）', '40', '400', '无限（-1）'],
  ['自建 1v1 场景上限', '2', '30', '无限'],
  ['自建多角色场景上限', '1', '20', '无限'],
  ['个人知识库文档上限', '0', '15', '200'],
  ['ZIP 导入 / 导出', '否 / 否', '是 / 否', '是 / 是'],
  ['签到积分倍率', '×1', '×2', '×3'],
  ['超额积分折扣', '1.0（无折扣）', '0.8（8 折）', '0.5（5 折）'],
  ['practice_turn：池点数 / 超额基准积分', '2', '2', '0（免费）'],
  ['debate_turn：基准积分', '4', '4', '0（免费）'],
  ['practice_coach_hint：基准积分', '1', '1', '0（免费）'],
  ['scene_ai_draft：基准积分', '5', '5', '3'],
  ['knowledge_embed：基准积分', '10（不允许超额）', '10', '5'],
]

export const taskRows = [
  ['daily_practice_1', '开口破冰', '1 场 1v1 对话', '15 积分', '日常 · 提交 1v1 轮次（/turns、/turns/stream）'],
  ['daily_listening_1', '磨耳朵训练', '1 次听力练习', '10 积分（每日最多 2 次）', '日常 · 提交听力作答 / 完成单元'],
  ['daily_review_10', '记忆加固', '3 次复习或添加', '15 积分', '日常 · 新增卡片 / 提交评级'],
  ['daily_debate_1', '思维交锋', '1 场多角色', '20 积分', '日常 · 多角色发言 / 结束'],
  ['onboard_avatar', '定制专属数字人', '保存 1 次偏好', '20 积分', '新手 · PUT /api/preferences/avatar'],
  ['onboard_scene', '创建首个自定义场景', '创建 1 个场景', '30 积分', '新手 · POST /api/scenes'],
]

export const voices = [
  ['emma', 'en-US-EmmaNeural', '美式 · 女'],
  ['aria', 'en-US-AriaNeural', '美式 · 女'],
  ['jenny', 'en-US-JennyNeural', '美式 · 女'],
  ['andrew', 'en-US-AndrewNeural', '美式 · 男'],
  ['brian', 'en-US-BrianNeural', '美式 · 男'],
  ['guy', 'en-US-GuyNeural', '美式 · 男'],
  ['sonia', 'en-GB-SoniaNeural', '英式 · 女'],
  ['ryan', 'en-GB-RyanNeural', '英式 · 男'],
  ['natasha', 'en-AU-NatashaNeural', '澳式 · 女'],
  ['william', 'en-AU-WilliamNeural', '澳式 · 男'],
]

export const faqs = [
  ['启动后内置场景为空', '先运行 python init_db.py 建表；lifespan 中的种子同步失败只会记 warning，查看后端日志即可定位。'],
  ['提交对话返回 503 CHAT_NOT_CONFIGURED', '配置 ECHOTALK_CHAT_API_KEY 与 ECHOTALK_CHAT_MODEL（模型需支持工具调用）并重启后端。'],
  ['录音按钮不可用 / ASR_NOT_CONFIGURED', 'GET /api/speech/status 返回 configured=false 时前端回退文字输入；填写 ECHOTALK_ASR_* 后恢复。'],
  ['检索结果 mode=keyword', '未配置嵌入 key，向量路停用；填写 ECHOTALK_SILICONFLOW_API_KEY 后调用 reindex 回填向量。'],
  ['检索结果 mode=none', 'FULLTEXT 索引未建成（MySQL 权限或 ngram 解析器问题），检查数据库账号是否有 ALTER 权限。'],
  ['LightRAG 接口返回 400', '未配置 ECHOTALK_LIGHTRAG_LLM_API_KEY，或管理端关闭了后台执行。图谱 building 状态长时间不变时调用 rebuild，僵尸状态会自愈。'],
  ['SSE 卡住、前端一次性收到全部文本', '反向代理开启了缓冲；Nginx 为 /api/ 关闭 proxy_buffering（后端已发送 X-Accel-Buffering: no）。'],
  ['403 QUOTA_EXCEEDED / INSUFFICIENT_CREDITS', '今日免费额度池已用满：开启「超额自动消耗积分」、签到 / 做任务获取积分，或通过兑换码升级。'],
  ['导入场景 409 SCENE_ID_CONFLICT', '用 ?resolve=overwrite 覆盖或 ?resolve=rename 改名导入。'],
  ['422 SCENE_INVALID_PACKAGE', '读取 error.details 的字段路径逐项修复；常见：占位符无法解析、工具未注册、表达式引用了未声明的 state 键。'],
  ['多角色场景发言 500', '检查是否绑定了 knowledgeDocIds（见多角色章节「已知问题」）；其余情况查看带 X-Request-ID 的日志。'],
  ['管理端接口 403 FORBIDDEN', '账号 is_admin 不是 1；用 init_db.py 创建 / 提升管理员，或由现有管理员在用户管理中授权。'],
]

export const code = {
  arch: `┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ frontend 5173 │  │ admin 5174    │  │ website 5200  │
│ Vue3 / Electron│  │ Vue3+Element  │  │ 官网 / 文档    │
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        └──────────────────┼──────────────────┘
                 HTTPS /api (Bearer Token, SSE)
                           │
                 ┌─────────▼──────────┐
                 │  Nginx 反向代理     │
                 └─────────┬──────────┘
                           │ 127.0.0.1:8000
        ┌──────────────────▼───────────────────┐
        │ FastAPI · app/main.py                │
        │  api/endpoints  → services           │
        │  agents (LangGraph) · scenes (RAG)   │
        └───┬───────────┬───────────┬──────────┘
            │           │           │
   MySQL 8 (35 表)   对话 / 嵌入 /     edge-tts · 腾讯 ASR
   FULLTEXT ngram    LightRAG LLM      讯飞 ISE
                     storage/ (封面、资料、音频缓存、图谱)`,

  quickstart: `# 1. 后端（FastAPI :8000）
cd backend
cp .env.example .env          # 填写 DB 密码、对话模型等
uv sync                       # 或 python -m venv .venv && pip install -r requirements.txt
.venv/bin/python init_db.py   # 建表 + 种子 + 默认管理员
.venv/bin/python main.py      # uvicorn，reload=True

# 2. 用户客户端（:5173）
cd frontend && npm install && npm run dev

# 3. 运营后台（:5174）
cd admin && npm install && npm run dev

# 4. 产品官网与文档（:5200，/api 代理到 :8000）
cd website && npm install && npm run dev`,

  error: `HTTP/1.1 403
{
  "error": {
    "code": "INSUFFICIENT_CREDITS",
    "message": "今日免费额度池已用满，继续使用需 3 回声积分（当前余额 1 点）…",
    "details": []        // 可选：字段级错误（如场景包校验）
  }
}`,

  er: `users ─┬─< auth_sessions
       ├─< practice_sessions ─< practice_turns          (scene_snapshot 冗余，不外联 scenes)
       ├─< debate_sessions   ─< debate_turns            (topic_id → debate_topics)
       ├─< review_items / listening_attempts / listening_progress
       ├─1 user_xp_states
       ├─< avatar_preferences (user_id, scene_id) ; avatars.owner_id
       ├─< personal_documents ─< personal_chunks ─1 personal_chunk_embeddings
       ├─< scenes.author_id ─┬─< documents ─< chunks ─1 chunk_embeddings
       │                     ├─1 scene_stats
       │                     └─< scene_user_stats (scene_id, user_id)
       ├─< debate_topics.owner_id ─< debate_topic_reactions
       ├─< listening_units.owner_id ─< listening_progress
       └─ SaaS: credit_ledger · user_daily_usage · user_task_progress
                subscription_orders · redeem_codes(used_by_user_id)
配置表（无外键）: saas_plan_configs · saas_billing_configs · saas_campaigns
                  credit_task_defs · system_configs · api_token_usage(流水)`,

  curl: `# 1) 注册并拿到令牌
curl -X POST http://127.0.0.1:8000/api/auth/register \\
  -H 'Content-Type: application/json' \\
  -d '{"username":"alice","password":"s3cret-pass"}'
# => {"access_token":"...","token_type":"bearer","user":{...}}

TOKEN=<access_token>

# 2) 创建 1v1 会话
curl -X POST http://127.0.0.1:8000/api/sessions \\
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \\
  -d '{"scene_id":"cafe_ordering"}'

# 3) 流式提交一轮（-N 关闭 curl 缓冲）
curl -N -X POST http://127.0.0.1:8000/api/sessions/<session_id>/turns/stream \\
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \\
  -d '{"request_id":"turn-001","text":"Hi, could I get a large latte please?","include_audio":false}'

# 4) 多角色：创建会话并发言
curl -X POST http://127.0.0.1:8000/api/debate/sessions \\
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \\
  -d '{"topic_id":"panel-final-interview","difficulty_level":"balanced"}'
curl -X POST http://127.0.0.1:8000/api/debate/sessions/<session_id>/turns \\
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \\
  -d '{"text":"I led the migration to an event-driven design...","is_voice":false}'
curl -X POST http://127.0.0.1:8000/api/debate/sessions/<session_id>/finish \\
  -H "Authorization: Bearer $TOKEN"`,

  zip: `echotalk_scene_demo.zip
├── manifest.json     # {format:"echotalk-scene", version:2, scene_id, min_app, files[], checksums{sha256}}
├── scene.yaml        # 13 个顶层区块：meta / roles / prompt / objectives / state / tools /
│                     #   coordination / stages / finish / knowledge / evaluation / guardrails / avatar
├── cover.png         # 可选，封面（png/jpg/jpeg/webp）
└── knowledge/        # 可选，资料源文件（md/txt…），可见性在 scene.yaml 的 knowledge.files 与分节标题里声明
    ├── menu.md
    └── staff_notes.md`,

  expr: `# objectives[].check
state.polite_request == true
tool_called('append_state_item')
state.paid == true and state_changed('order')

# stages[].exit_when
turn_count >= 1
stage == 'ordering' and stage_turns >= 2

# finish.when
state.confirmed == true and state.paid == true
goals_done() or turn_count >= 20`,

  sceneYaml: `meta:
  id: cafe_ordering
  name: 繁忙咖啡厅点餐 (Cafe Ordering)
  category: daily
  difficulty: easy
  mode: conversation
  compat: { min_app: 2.0.0 }
  tags: [礼貌表达, 订单工具]

roles:
  - id: barista
    display_name: Leo
    title: Barista
    personality: friendly but busy
    voice: andrew
    avatar: leo_2d

prompt:
  system: |
    You are {roles.barista.display_name}, a {roles.barista.personality} barista at {store_name}.
    When the customer orders politely, call update_scene_state for "polite_request"=true;
    when they order an item, call append_state_item (key "order");
    when they confirm or pay, call update_scene_state for "confirmed" / "paid".
    Use search_knowledge("prices") for exact prices. Never invent prices. Keep replies under 28 words.
  greeting: >
    Hi there! Welcome to {store_name}. What can I get started for you today?
  params:
    - { key: store_name, type: string, default: Metro Cafe, editable: true }

objectives:
  - { id: polite_request, label: 礼貌提出请求, check: "state.polite_request == true" }
  - { id: quantity_preference, label: 表达数量与规格, check: "tool_called('append_state_item')" }
  - { id: confirmation, label: 复述并确认订单, check: "state.confirmed == true" }

state:
  polite_request: false
  order: []
  confirmed: false
  paid: false

tools:
  allowed: [search_knowledge, update_scene_state, append_state_item, remove_state_item, calculate_expression, next_interview_stage]

stages:
  - { id: greeting, name: 进店问候, exit_when: "turn_count >= 1" }
  - { id: ordering, name: 点单与定制, guidance: 依次确认饮品、规格、奶类与堂食/带走 }
  - { id: checkout, name: 确认与支付, exit_when: "state.confirmed == true" }

finish:
  when: state.confirmed == true and state.paid == true
  max_turns: 30
  on_finish: request_feedback

knowledge:
  files:
    - { path: menu.md, visibility: user }
    - { path: staff_notes.md, visibility: ai_only }
  retrieval: { default_top_k: 4 }

evaluation:
  dimensions:
    - { id: task_completion, label: 任务完成度, weight: 0.4, source: state }
    - { id: politeness, label: 礼貌与得体, weight: 0.2, source: llm }
    - { id: accuracy, label: 语法与用词, weight: 0.4, source: llm }

guardrails:
  language: en
  min_words: 3
  off_topic: { domain_keywords: [coffee, latte, muffin, order, pay], action: warn }
  max_warnings_per_turn: 1

avatar: { preferred: leo_2d, rate: 1.0 }`,

  roleFlow: `POST /api/debate/sessions/{id}/turns  { text, is_voice, duration }
 │
 ├─ 1. 配额：check_and_consume_quota(debate_turn)；会话须 active（finished → DEBATE_ALREADY_FINISHED）
 ├─ 2. 写入用户发言 DebateTurn(role=user, turn_number=第 N 个用户发言)
 ├─ 3. 阶段推进：progress = N / maxTurns；next_stage = floor(progress × (阶段数-1))
 ├─ 4. 选择发言角色
 │      debate : 固定 opponent（无则 roles[0]）；评委 = 首个 judge
 │      panel  : 非 judge 角色池按 (N % 池大小) 轮换，且不与上一位 AI 相同；评委 = 另一位 judge
 ├─ 5. 评委是否发言：judge_score 启用 且 有评委 且 (阶段发生变化 或 N ≥ maxTurns)
 ├─ 6. LLM 一次生成 JSON：opponent_en/zh · judge_en/zh · score_deltas · win_rate_delta · review_expression
 │      提示词含：场景背景 / 目标表达 / 绑定资料 / 角色 persona / 对手强度 / 最近对话
 │      LLM 失败时走本地兜底发言（_fallback_ai_turn），不会 500
 ├─ 7. 回写：scores_json(逐项夹取) · win_rate · combo_count · stage_index · turn_count
 ├─ 8. 落库 AI 发言（+ 评委发言），add_review_task 启用时写入 review_items（幂等）
 └─ 9. 返回 { session, new_messages:[用户, AI(, 评委)] }

POST .../finish → status=finished，生成 verdict，首次发放 40 XP`,

  panelYaml: `id: panel-final-interview
sceneType: panel
category: workplace
categoryLabel: 职场文化
difficulty: advanced
difficultyLabel: 挑战
duration: 10 分钟            # → maxTurns = 8
userRoleLabel: 高级工程师候选人
titleZh: 终面多面试官群面（Tech Lead + HRBP）
motionEn: "Senior Backend Engineer Final Panel: Defend a high-stakes production architecture trade-off ..."
proSummary: 清晰阐述系统架构取舍逻辑与可量化线上收益
conSummary: 坦诚复盘跨团队分歧处理与降级保障预案
backgroundContext: 本场模拟外企资深研发岗位终面圆桌 ...
keyExpressions:
  - high-stakes architectural trade-off
  - blameless post-mortem
roles:
  - id: tech_lead
    roleType: interviewer
    name: Claire
    title: 技术总监 Tech Lead
    voice: emma
    avatarId: claire_2d
    persona: 专注高并发架构权衡、稳定性指标与工程落地成本的技术总监，追问具体且直接。
  - id: hrbp
    roleType: interviewer
    name: Emily
    title: 资深 HRBP
    voice: aria
    avatarId: emily_2d
    persona: 关注跨团队意见冲突、推进阻力与失败复盘透明度的资深 HRBP。
  - id: vp
    roleType: judge
    name: Leo
    title: 研发副总裁 VP
    voice: brian
    avatarId: leo_2d
    persona: 站在业务全局收益与组织长期发展视角追问关键取舍并给出终审评估。
# stages 省略 → panel 默认：自我陈述 / 深度追问 / 压力挑战 / 委员会评估
# tools  省略 → 缺省 [search_knowledge, rebuttal_hint, judge_score, add_review_task]
#
# 内置 debate 示例（four-day-workweek）：roles = moderator Brian + opponent David + judge Claire，
# tools: [search_knowledge, rebuttal_hint, judge_score, calculate_expression, add_review_task]`,

  debateApi: `POST /api/debate/topics
Authorization: Bearer <token>

{
  "sceneType": "debate",
  "titleZh": "远程办公是否应成为默认选项？",
  "motionEn": "Remote work should be the default for knowledge workers.",
  "category": "workplace",
  "difficulty": "intermediate",
  "duration": "8 分钟",
  "proSummary": "节省通勤、扩大人才池、提升专注时间。",
  "conSummary": "协作成本上升，新人成长与文化凝聚受损。",
  "backgroundContext": "2020 年后多家公司推行混合办公，数据对生产力的结论并不一致。",
  "keyExpressions": ["asynchronous collaboration", "talent pool", "onboarding friction"],
  "defaultStyle": "balanced",
  "roles": [
    { "id": "moderator", "roleType": "moderator", "name": "Brian", "title": "主持人",
      "voice": "brian", "avatarId": "david_2d", "persona": "中立控场，推动双方回应核心论点。" },
    { "id": "opponent", "roleType": "opponent", "name": "Sonia", "title": "反方辩手",
      "voice": "sonia", "avatarId": "sarah_2d", "persona": "擅长用数据与案例质询，语气克制但锋利。" },
    { "id": "judge", "roleType": "judge", "name": "Andrew", "title": "特邀评委",
      "voice": "andrew", "avatarId": "leo_2d", "persona": "关注论证严谨度与回应质量。" }
  ],
  "stages": [
    { "id": "opening", "label": "开篇立论", "shortTag": "立论" },
    { "id": "cross", "label": "交叉质询", "shortTag": "质询" },
    { "id": "closing", "label": "总结裁决", "shortTag": "裁决" }
  ],
  "tools": ["search_knowledge", "rebuttal_hint", "judge_score"]
}
# => 201 { "topic": { "id": "...", "maxTurns": 6, "roles": [...], "status": "private", ... } }`,

  debateZip: `echotalk_debate_<topic_id>.zip
├── manifest.json   # {format:"echotalk-debate-package", schemaVersion:2, id, sceneType, title, hasCover, coverFile}
├── debate.json     # {schemaVersion:2, type:"echotalk-debate-topic", sceneType, userRoleLabel, titleZh, motionEn,
│                   #  category, difficulty, duration, proSummary, conSummary, backgroundContext, keyExpressions,
│                   #  defaultStyle, opponent*（派生）, roles[], stages[], tools[], coverFile?}
└── cover.png       # 可选`,

  tests: `cd backend
.venv/bin/python -m pytest tests -q        # 单元 / 集成测试
.venv/bin/python scripts/smoke_scenes.py   # 内置场景冒烟`,
}

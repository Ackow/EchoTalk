// 由后端 SQLAlchemy 模型自动导出（35 张表，对应 backend/app/models/*.py），请勿手工逐表编辑。
// 列：[字段, 类型, 可空, 默认值, 键/索引, 说明]
export const dbGroups = [
 {
  "group": "账户与权限",
  "tables": [
   {
    "name": "users",
    "title": "用户主表",
    "about": "账号、会员等级、积分余额与签到状态；用户名唯一，密码为 PBKDF2-SHA256 的 salt$digest。",
    "cols": [
     [
      "id",
      "int",
      "N",
      "",
      "PK",
      "主键：用户唯一 ID，自增"
     ],
     [
      "username",
      "varchar(50)",
      "N",
      "",
      "UQ",
      "用户名：3~50 字符，唯一、必填、有索引"
     ],
     [
      "password_hash",
      "varchar(256)",
      "N",
      "",
      "",
      "密码摘要：PBKDF2-SHA256 的 salt$digest，必填"
     ],
     [
      "avatar_path",
      "varchar(128)",
      "Y",
      "",
      "",
      "头像相对路径：users/{id}/avatar-<随机串>.<ext>，NULL 表示未设置（用首字母兜底）"
     ],
     [
      "is_admin",
      "int",
      "N",
      "0",
      "",
      "管理员标识：0=普通用户，1=管理员"
     ],
     [
      "plan_tier",
      "varchar(20)",
      "N",
      "free",
      "",
      "会员等级：free/pro/enterprise"
     ],
     [
      "plan_expires_at",
      "datetime",
      "Y",
      "",
      "",
      "会员到期时间（NULL 表示永久或 Free）"
     ],
     [
      "credits_balance",
      "int",
      "N",
      "100",
      "",
      "当前可用回声积分余额"
     ],
     [
      "auto_use_credits",
      "int",
      "N",
      "1",
      "",
      "免费额度用尽后是否自动消耗积分"
     ],
     [
      "checkin_streak",
      "int",
      "N",
      "0",
      "",
      "连续签到天数"
     ],
     [
      "last_checkin_date",
      "varchar(10)",
      "Y",
      "",
      "",
      "最近签到日期（YYYY-MM-DD）"
     ],
     [
      "created_at",
      "datetime",
      "N",
      "auto",
      "",
      "注册时间：UTC，插入时自动填充"
     ]
    ],
    "unique": []
   },
   {
    "name": "auth_sessions",
    "title": "登录会话",
    "about": "仅存令牌 SHA-256 摘要，原始令牌只在登录时返回一次；有效期 30 天，退出登录写入 revoked_at。",
    "cols": [
     [
      "id",
      "int",
      "N",
      "",
      "PK",
      "主键：会话记录 ID，自增"
     ],
     [
      "user_id",
      "int",
      "N",
      "",
      "FK→users.id IDX",
      "所属用户 ID：外键 users.id，有索引"
     ],
     [
      "token_hash",
      "varchar(64)",
      "N",
      "",
      "UQ",
      "令牌摘要：令牌的 SHA-256（64 字符），唯一、有索引"
     ],
     [
      "expires_at",
      "datetime",
      "N",
      "",
      "",
      "过期时间：UTC，签发后 30 天"
     ],
     [
      "revoked_at",
      "datetime",
      "Y",
      "",
      "",
      "撤销时间：退出登录时写入，NULL 表示仍有效"
     ],
     [
      "created_at",
      "datetime",
      "N",
      "auto",
      "",
      "签发时间：UTC，插入时自动填充"
     ]
    ],
    "unique": []
   },
   {
    "name": "system_configs",
    "title": "全局开关",
    "about": "键值对配置，如「是否限制注册」「LightRAG 后台执行开关」，由管理端热更新。",
    "cols": [
     [
      "key",
      "varchar(64)",
      "N",
      "",
      "PK",
      "配置键"
     ],
     [
      "value",
      "varchar(255)",
      "N",
      "",
      "",
      "配置值"
     ],
     [
      "updated_at",
      "datetime",
      "N",
      "auto",
      "",
      "最近更新时间（UTC）"
     ]
    ],
    "unique": []
   }
  ]
 },
 {
  "group": "1v1 场景与对话",
  "tables": [
   {
    "name": "scenes",
    "title": "场景包",
    "about": "完整 ScenePackage v2 声明存于 package_json，标量列用于列表筛选与权限；内置/自建/导入三种来源。",
    "cols": [
     [
      "id",
      "varchar(50)",
      "N",
      "",
      "PK",
      "场景 ID：即 meta.id，如 cafe_ordering"
     ],
     [
      "name",
      "varchar(100)",
      "N",
      "",
      "",
      "显示名称"
     ],
     [
      "description",
      "text",
      "Y",
      "",
      "",
      "一句话描述：场景卡与列表展示"
     ],
     [
      "category",
      "varchar(30)",
      "N",
      "custom",
      "",
      "分类：daily/business/career/academic/custom"
     ],
     [
      "mode",
      "varchar(20)",
      "N",
      "conversation",
      "",
      "模式：conversation/interview/debate"
     ],
     [
      "difficulty",
      "varchar(20)",
      "Y",
      "",
      "",
      "难度五级：entry/easy/normal/hard/expert"
     ],
     [
      "package_json",
      "json",
      "N",
      "",
      "",
      "完整场景包声明（scene.yaml 解析结果）"
     ],
     [
      "source",
      "varchar(20)",
      "N",
      "custom",
      "IDX",
      "来源：builtin/custom/imported"
     ],
     [
      "status",
      "varchar(20)",
      "N",
      "private",
      "",
      "发布状态：private（本地私有）/ published（社区可见）"
     ],
     [
      "required_tier",
      "varchar(20)",
      "N",
      "free",
      "",
      "最低会员等级要求：free/pro/enterprise"
     ],
     [
      "published_at",
      "datetime",
      "Y",
      "",
      "",
      "发布时间：NULL 表示未发布"
     ],
     [
      "pkg_version",
      "int",
      "N",
      "2",
      "",
      "包结构版本：v2"
     ],
     [
      "author_id",
      "int",
      "Y",
      "",
      "FK→users.id",
      "所属用户：builtin 为 NULL"
     ],
     [
      "cover_path",
      "varchar(512)",
      "Y",
      "",
      "",
      "封面图本地相对路径（storage/scenes/{id}/cover.*），NULL 用缺省样式"
     ],
     [
      "greeting_text",
      "text",
      "Y",
      "",
      "",
      "问候语文本（TTS 预合成随语音模块接入）"
     ],
     [
      "greeting_audio_path",
      "varchar(512)",
      "Y",
      "",
      "",
      "预合成音频本地相对路径（语音模块接入后启用）"
     ],
     [
      "domain_keywords",
      "json",
      "Y",
      "",
      "",
      "跑题检测域关键词（缺省时自动提取填充）"
     ],
     [
      "created_at",
      "datetime",
      "N",
      "auto",
      "",
      "创建时间：UTC"
     ],
     [
      "updated_at",
      "datetime",
      "N",
      "auto",
      "",
      "更新时间：UTC"
     ]
    ],
    "unique": []
   },
   {
    "name": "scene_stats",
    "title": "场景互动统计",
    "about": "每个场景一行：点赞、收藏、下载（导出）计数。",
    "cols": [
     [
      "scene_id",
      "varchar(50)",
      "N",
      "",
      "PK FK→scenes.id",
      "场景 ID"
     ],
     [
      "likes",
      "int",
      "N",
      "0",
      "",
      "点赞数"
     ],
     [
      "downloads",
      "int",
      "N",
      "0",
      "",
      "下载（导出）次数"
     ],
     [
      "favorites",
      "int",
      "N",
      "0",
      "",
      "收藏数"
     ],
     [
      "updated_at",
      "datetime",
      "N",
      "auto",
      "",
      "最近互动时间：UTC"
     ]
    ],
    "unique": []
   },
   {
    "name": "scene_user_stats",
    "title": "用户-场景互动",
    "about": "(scene_id, user_id) 唯一，记录该用户是否点赞/收藏，用于切换与去重。",
    "cols": [
     [
      "id",
      "int",
      "N",
      "",
      "PK",
      "主键：自增"
     ],
     [
      "scene_id",
      "varchar(50)",
      "N",
      "",
      "FK→scenes.id IDX",
      "场景 ID"
     ],
     [
      "user_id",
      "int",
      "N",
      "",
      "FK→users.id IDX",
      "用户 ID"
     ],
     [
      "liked",
      "int",
      "N",
      "0",
      "",
      "是否已点赞：0/1（布尔语义）"
     ],
     [
      "favorited",
      "int",
      "N",
      "0",
      "",
      "是否已收藏：0/1（布尔语义）"
     ],
     [
      "updated_at",
      "datetime",
      "N",
      "auto",
      "",
      "最近互动时间：UTC"
     ]
    ],
    "unique": [
     "UNIQUE(scene_id, user_id)"
    ]
   },
   {
    "name": "practice_sessions",
    "title": "1v1 练习会话",
    "about": "scene_snapshot 保存创建时刻的场景快照，场景之后被改/删也不影响历史回放；state_json 是 LangGraph 运行态。",
    "cols": [
     [
      "id",
      "varchar(36)",
      "N",
      "",
      "PK",
      "主键"
     ],
     [
      "user_id",
      "int",
      "N",
      "",
      "FK→users.id IDX",
      "所属用户 ID"
     ],
     [
      "scene_id",
      "varchar(50)",
      "N",
      "",
      "",
      "不关联删除：历史以快照恢复"
     ],
     [
      "scene_snapshot",
      "json",
      "N",
      "",
      "",
      "创建时的完整场景包快照"
     ],
     [
      "state_json",
      "json",
      "N",
      "",
      "",
      "运行态：scenario_state / stage / stage_turns / goals / status / finish_reason"
     ],
     [
      "greeting",
      "text",
      "N",
      "",
      "",
      "问候语"
     ],
     [
      "version",
      "int",
      "N",
      "0",
      "",
      "乐观并发版本号"
     ],
     [
      "created_at",
      "datetime",
      "N",
      "auto",
      "",
      "创建时间（UTC）"
     ]
    ],
    "unique": []
   },
   {
    "name": "practice_turns",
    "title": "1v1 对话轮次",
    "about": "(session_id, number) 与 (session_id, request_id) 双唯一，request_id 保证重试幂等；trace_json 为内部工具轨迹，不对外下发。",
    "cols": [
     [
      "id",
      "varchar(36)",
      "N",
      "",
      "PK",
      "主键"
     ],
     [
      "session_id",
      "varchar(36)",
      "N",
      "",
      "FK→practice_sessions.id IDX",
      "所属会话 ID"
     ],
     [
      "request_id",
      "varchar(64)",
      "N",
      "",
      "",
      "客户端幂等请求 ID"
     ],
     [
      "number",
      "int",
      "N",
      "",
      "",
      "轮次序号（会话内唯一）"
     ],
     [
      "input_text",
      "text",
      "N",
      "",
      "",
      "用户输入文本"
     ],
     [
      "response_json",
      "json",
      "N",
      "",
      "",
      "仅公开回复与任务状态"
     ],
     [
      "trace_json",
      "json",
      "N",
      "",
      "",
      "内部工具轨迹，禁止通过接口直接下发"
     ],
     [
      "pronunciation_score",
      "json",
      "Y",
      "",
      "",
      "语音评测：发音/语调/语速/逐词得分"
     ],
     [
      "grammar_correction",
      "json",
      "Y",
      "",
      "",
      "对话纠正：语法/地道表达建议"
     ],
     [
      "created_at",
      "datetime",
      "N",
      "auto",
      "",
      "创建时间（UTC）"
     ]
    ],
    "unique": [
     "UNIQUE(session_id, number)",
     "UNIQUE(session_id, request_id)"
    ]
   }
  ]
 },
 {
  "group": "1vN 多角色（辩论 / 群面）",
  "tables": [
   {
    "name": "debate_topics",
    "title": "多角色场景（辩题/群面）",
    "about": "roles_config / stages_config / tools_config 三个 JSON 列即多角色编排声明；内置场景来自 content/debates/*.yaml。",
    "cols": [
     [
      "id",
      "varchar(64)",
      "N",
      "",
      "PK",
      "主键"
     ],
     [
      "title_zh",
      "varchar(180)",
      "N",
      "",
      "",
      "中文标题"
     ],
     [
      "motion_en",
      "text",
      "N",
      "",
      "",
      "英文议题/场景描述"
     ],
     [
      "category",
      "varchar(32)",
      "N",
      "tech",
      "IDX",
      "分类"
     ],
     [
      "category_label",
      "varchar(48)",
      "N",
      "科技伦理",
      "",
      "分类中文名"
     ],
     [
      "difficulty",
      "varchar(24)",
      "N",
      "intermediate",
      "",
      "难度"
     ],
     [
      "difficulty_label",
      "varchar(24)",
      "N",
      "进阶",
      "",
      "难度中文名"
     ],
     [
      "duration",
      "varchar(32)",
      "N",
      "8 分钟",
      "",
      "时长文案，如「8 分钟」，决定最大轮数（≤6 分钟 4 轮 / ≤9 分钟 6 轮 / 其余 8 轮）"
     ],
     [
      "pro_summary",
      "text",
      "N",
      "",
      "",
      "正方/高光要点"
     ],
     [
      "con_summary",
      "text",
      "N",
      "",
      "",
      "反方/风险要点"
     ],
     [
      "background_context",
      "text",
      "N",
      "",
      "",
      "背景资料，注入 AI 提示词"
     ],
     [
      "key_expressions",
      "json",
      "N",
      "auto",
      "",
      "关键英文表达数组"
     ],
     [
      "default_style",
      "varchar(24)",
      "N",
      "balanced",
      "",
      "默认对手强度 supportive / balanced / sharp"
     ],
     [
      "scene_type",
      "varchar(24)",
      "N",
      "debate",
      "",
      "debate | panel"
     ],
     [
      "user_role_label",
      "varchar(64)",
      "N",
      "候选人 / 主讲人",
      "",
      "用户身份文案"
     ],
     [
      "roles_config",
      "json",
      "N",
      "auto",
      "",
      "角色数组（2–4 个），见多角色开发章节"
     ],
     [
      "stages_config",
      "json",
      "N",
      "auto",
      "",
      "阶段数组（≤6 个）"
     ],
     [
      "opponent_name",
      "varchar(64)",
      "N",
      "Sonia",
      "",
      "主对手名（由 roles 派生，兼容旧版）"
     ],
     [
      "opponent_title",
      "varchar(64)",
      "N",
      "对手辩手",
      "",
      "主对手头衔"
     ],
     [
      "opponent_persona",
      "text",
      "N",
      "",
      "",
      "主对手人设"
     ],
     [
      "opponent_voice",
      "varchar(32)",
      "N",
      "sonia",
      "",
      "主对手音色"
     ],
     [
      "opponent_avatar_id",
      "varchar(32)",
      "N",
      "sarah_2d",
      "",
      "主对手形象"
     ],
     [
      "knowledge_doc_ids",
      "json",
      "N",
      "auto",
      "",
      "绑定的个人资料文档 ID 数组"
     ],
     [
      "cover_path",
      "varchar(512)",
      "Y",
      "",
      "",
      "封面相对路径"
     ],
     [
      "tools_config",
      "json",
      "N",
      "auto",
      "",
      "启用的工具 ID 数组（rebuttal_hint / judge_score / search_knowledge / calculate_expression / add_review_task）"
     ],
     [
      "status",
      "varchar(24)",
      "N",
      "private",
      "",
      "private | published"
     ],
     [
      "required_tier",
      "varchar(20)",
      "N",
      "free",
      "",
      "free | pro | enterprise"
     ],
     [
      "likes_count",
      "int",
      "N",
      "0",
      "",
      "点赞数"
     ],
     [
      "favorites_count",
      "int",
      "N",
      "0",
      "",
      "收藏数"
     ],
     [
      "is_builtin",
      "bool",
      "N",
      "False",
      "",
      "是否为系统内置"
     ],
     [
      "owner_id",
      "int",
      "Y",
      "",
      "FK→users.id IDX",
      "创建者用户 ID；内置数据为 NULL"
     ],
     [
      "created_at",
      "datetime",
      "N",
      "auto",
      "",
      "创建时间（UTC）"
     ]
    ],
    "unique": []
   },
   {
    "name": "debate_topic_reactions",
    "title": "多角色场景互动",
    "about": "kind 为 like / favorite，每用户每场景每类一行。",
    "cols": [
     [
      "id",
      "int",
      "N",
      "",
      "PK",
      "主键"
     ],
     [
      "topic_id",
      "varchar(64)",
      "N",
      "",
      "FK→debate_topics.id IDX",
      "多角色场景 ID"
     ],
     [
      "user_id",
      "int",
      "N",
      "",
      "FK→users.id IDX",
      "所属用户 ID"
     ],
     [
      "kind",
      "varchar(16)",
      "N",
      "",
      "",
      "like | favorite"
     ],
     [
      "created_at",
      "datetime",
      "N",
      "auto",
      "",
      "创建时间（UTC）"
     ]
    ],
    "unique": []
   },
   {
    "name": "debate_sessions",
    "title": "多角色会话",
    "about": "记录阶段、轮数、胜率、连击、四维分数与赛后裁决书。",
    "cols": [
     [
      "id",
      "varchar(36)",
      "N",
      "",
      "PK",
      "主键"
     ],
     [
      "user_id",
      "int",
      "N",
      "",
      "FK→users.id IDX",
      "所属用户 ID"
     ],
     [
      "topic_id",
      "varchar(64)",
      "N",
      "",
      "IDX",
      "多角色场景 ID"
     ],
     [
      "topic_title",
      "varchar(180)",
      "N",
      "",
      "",
      "场景标题快照"
     ],
     [
      "motion_en",
      "text",
      "N",
      "",
      "",
      "英文议题/场景描述"
     ],
     [
      "category",
      "varchar(32)",
      "N",
      "tech",
      "",
      "分类"
     ],
     [
      "difficulty",
      "varchar(24)",
      "N",
      "intermediate",
      "",
      "难度"
     ],
     [
      "scene_type",
      "varchar(24)",
      "N",
      "debate",
      "",
      "debate | panel"
     ],
     [
      "user_side",
      "varchar(8)",
      "N",
      "pro",
      "",
      "pro | con"
     ],
     [
      "difficulty_level",
      "varchar(24)",
      "N",
      "balanced",
      "",
      "supportive | balanced | sharp"
     ],
     [
      "stage_index",
      "int",
      "N",
      "0",
      "",
      "当前阶段下标（0 起）"
     ],
     [
      "turn_count",
      "int",
      "N",
      "0",
      "",
      "已完成的用户发言轮数"
     ],
     [
      "status",
      "varchar(20)",
      "N",
      "active",
      "",
      "active | finished"
     ],
     [
      "win_rate",
      "int",
      "N",
      "50",
      "",
      "胜率/委员会认可度（20~95）"
     ],
     [
      "combo_count",
      "int",
      "N",
      "0",
      "",
      "连续有效交锋次数"
     ],
     [
      "scores_json",
      "json",
      "N",
      "",
      "",
      "四维分数 {logic, rebuttal, fluency, presence}"
     ],
     [
      "verdict_json",
      "json",
      "Y",
      "",
      "",
      "赛后裁决书 JSON"
     ],
     [
      "created_at",
      "datetime",
      "N",
      "auto",
      "IDX",
      "创建时间（UTC）"
     ],
     [
      "updated_at",
      "datetime",
      "N",
      "auto",
      "",
      "最近更新时间（UTC）"
     ]
    ],
    "unique": []
   },
   {
    "name": "debate_turns",
    "title": "多角色发言轮次",
    "about": "user / opponent / interviewer / moderator / judge 的逐条发言，含中英文与评估 JSON。",
    "cols": [
     [
      "id",
      "varchar(36)",
      "N",
      "",
      "PK",
      "主键"
     ],
     [
      "session_id",
      "varchar(36)",
      "N",
      "",
      "FK→debate_sessions.id IDX",
      "所属会话 ID"
     ],
     [
      "turn_number",
      "int",
      "N",
      "1",
      "",
      "轮次序号"
     ],
     [
      "stage_label",
      "varchar(48)",
      "N",
      "开篇立论",
      "",
      "所属阶段名"
     ],
     [
      "role",
      "varchar(20)",
      "N",
      "",
      "",
      "moderator | interviewer | user | opponent | judge"
     ],
     [
      "speaker",
      "varchar(64)",
      "N",
      "",
      "",
      "发言者姓名"
     ],
     [
      "role_title",
      "varchar(64)",
      "N",
      "",
      "",
      "发言者头衔"
     ],
     [
      "avatar_id",
      "varchar(32)",
      "N",
      "",
      "",
      "发言者数字人形象"
     ],
     [
      "voice_style",
      "varchar(32)",
      "N",
      "brian",
      "",
      "TTS 音色"
     ],
     [
      "is_voice",
      "bool",
      "N",
      "False",
      "",
      "是否语音输入"
     ],
     [
      "duration",
      "int",
      "Y",
      "",
      "",
      "时长文案，如「8 分钟」，决定最大轮数（≤6 分钟 4 轮 / ≤9 分钟 6 轮 / 其余 8 轮）"
     ],
     [
      "en_text",
      "text",
      "N",
      "",
      "",
      "英文发言正文"
     ],
     [
      "zh_text",
      "text",
      "N",
      "",
      "",
      "中文译文/解析"
     ],
     [
      "evaluation_json",
      "json",
      "Y",
      "",
      "",
      "评委逐条评估 JSON"
     ],
     [
      "created_at",
      "datetime",
      "N",
      "auto",
      "",
      "创建时间（UTC）"
     ]
    ],
    "unique": []
   }
  ]
 },
 {
  "group": "知识库（Hybrid RAG + LightRAG）",
  "tables": [
   {
    "name": "documents",
    "title": "场景资料",
    "about": "场景包 knowledge/ 下的源文件元信息。",
    "cols": [
     [
      "id",
      "int",
      "N",
      "",
      "PK",
      "主键：资料 ID，自增"
     ],
     [
      "scene_id",
      "varchar(50)",
      "N",
      "",
      "FK→scenes.id IDX",
      "所属场景"
     ],
     [
      "owner_id",
      "int",
      "Y",
      "",
      "FK→users.id",
      "上传者：内置资料为 NULL"
     ],
     [
      "filename",
      "varchar(255)",
      "N",
      "",
      "",
      "原始文件名：导出时还原"
     ],
     [
      "content_type",
      "varchar(100)",
      "Y",
      "",
      "",
      "MIME 类型"
     ],
     [
      "chunk_count",
      "int",
      "N",
      "0",
      "",
      "分块数量"
     ],
     [
      "visibility",
      "varchar(10)",
      "N",
      "user",
      "",
      "文件级缺省可见性：user/ai_only"
     ],
     [
      "created_at",
      "datetime",
      "N",
      "auto",
      "",
      "上传时间：UTC"
     ]
    ],
    "unique": []
   },
   {
    "name": "chunks",
    "title": "场景资料分块",
    "about": "按标题分节后再切块，visibility 控制 user / ai_only；ngram FULLTEXT 索引 ft_chunks_text。",
    "cols": [
     [
      "id",
      "int",
      "N",
      "",
      "PK",
      "主键：分块 ID，自增"
     ],
     [
      "document_id",
      "int",
      "N",
      "",
      "FK→documents.id IDX",
      "所属资料"
     ],
     [
      "scene_id",
      "varchar(50)",
      "N",
      "",
      "IDX",
      "场景冗余：便于按场景隔离与重建"
     ],
     [
      "section",
      "varchar(100)",
      "Y",
      "",
      "",
      "分节名：md 标题或文件名"
     ],
     [
      "visibility",
      "varchar(10)",
      "N",
      "user",
      "",
      "分节可见性：user/ai_only"
     ],
     [
      "ordinal",
      "int",
      "N",
      "",
      "",
      "块序号：同一资料内从 0 递增"
     ],
     [
      "text",
      "text",
      "N",
      "",
      "",
      "分块文本内容"
     ]
    ],
    "unique": []
   },
   {
    "name": "chunk_embeddings",
    "title": "场景分块向量",
    "about": "与 chunks 一对一；float32×1024 二进制，更换嵌入模型后必须全量 reindex。",
    "cols": [
     [
      "id",
      "int",
      "N",
      "",
      "PK",
      "主键：自增"
     ],
     [
      "chunk_id",
      "int",
      "N",
      "",
      "FK→chunks.id UQ",
      "分块：一对一"
     ],
     [
      "model",
      "varchar(64)",
      "N",
      "",
      "",
      "生成模型：空间不兼容，换模型必须重刷"
     ],
     [
      "embedding",
      "blob",
      "N",
      "",
      "",
      "float32 × DIM 的二进制"
     ],
     [
      "created_at",
      "datetime",
      "N",
      "auto",
      "",
      "生成时间：UTC"
     ]
    ],
    "unique": []
   },
   {
    "name": "personal_documents",
    "title": "个人资料",
    "about": "用户私有工作区文档，owner_id 为隔离边界，同名上传即覆盖更新。",
    "cols": [
     [
      "id",
      "int",
      "N",
      "",
      "PK",
      "主键：资料 ID，自增"
     ],
     [
      "owner_id",
      "int",
      "N",
      "",
      "FK→users.id IDX",
      "所属用户：工作区隔离边界"
     ],
     [
      "filename",
      "varchar(255)",
      "N",
      "",
      "",
      "原始文件名：同名覆盖即更新"
     ],
     [
      "content_type",
      "varchar(100)",
      "Y",
      "",
      "",
      "MIME 类型"
     ],
     [
      "chunk_count",
      "int",
      "N",
      "0",
      "",
      "分块数量"
     ],
     [
      "created_at",
      "datetime",
      "N",
      "auto",
      "",
      "上传时间：UTC"
     ]
    ],
    "unique": []
   },
   {
    "name": "personal_chunks",
    "title": "个人资料分块",
    "about": "统一 visibility=user；FULLTEXT 索引 ft_personal_chunks_text。",
    "cols": [
     [
      "id",
      "int",
      "N",
      "",
      "PK",
      "主键：分块 ID，自增"
     ],
     [
      "document_id",
      "int",
      "N",
      "",
      "FK→personal_documents.id IDX",
      "所属资料"
     ],
     [
      "section",
      "varchar(100)",
      "Y",
      "",
      "",
      "分节名：md 标题或文件名"
     ],
     [
      "visibility",
      "varchar(10)",
      "N",
      "user",
      "",
      "个人资料统一 user"
     ],
     [
      "ordinal",
      "int",
      "N",
      "",
      "",
      "块序号：同一资料内从 0 递增"
     ],
     [
      "text",
      "text",
      "N",
      "",
      "",
      "分块文本内容"
     ]
    ],
    "unique": []
   },
   {
    "name": "personal_chunk_embeddings",
    "title": "个人分块向量",
    "about": "与 personal_chunks 一对一。",
    "cols": [
     [
      "id",
      "int",
      "N",
      "",
      "PK",
      "主键：自增"
     ],
     [
      "chunk_id",
      "int",
      "N",
      "",
      "FK→personal_chunks.id UQ",
      "分块：一对一"
     ],
     [
      "model",
      "varchar(64)",
      "N",
      "",
      "",
      "生成模型"
     ],
     [
      "embedding",
      "blob",
      "N",
      "",
      "",
      "float32 × DIM 的二进制"
     ],
     [
      "created_at",
      "datetime",
      "N",
      "auto",
      "",
      "生成时间：UTC"
     ]
    ],
    "unique": []
   }
  ]
 },
 {
  "group": "数字人与语音",
  "tables": [
   {
    "name": "avatars",
    "title": "数字人角色目录",
    "about": "内置角色与用户自建角色，可公开到市场并被他人克隆。",
    "cols": [
     [
      "id",
      "varchar(50)",
      "N",
      "",
      "PK",
      "主键"
     ],
     [
      "owner_id",
      "int",
      "Y",
      "",
      "FK→users.id IDX",
      "自建角色的作者；内置角色为 NULL"
     ],
     [
      "is_builtin",
      "int",
      "N",
      "0",
      "",
      "是否为系统内置"
     ],
     [
      "is_public",
      "int",
      "N",
      "0",
      "",
      "是否公开到数字人市场（0/1）"
     ],
     [
      "author_name",
      "varchar(100)",
      "N",
      "",
      "",
      "作者展示名"
     ],
     [
      "source_avatar_id",
      "varchar(50)",
      "Y",
      "",
      "IDX",
      "克隆来源角色 ID"
     ],
     [
      "display_name",
      "varchar(100)",
      "N",
      "",
      "",
      "角色显示名"
     ],
     [
      "kind",
      "varchar(20)",
      "N",
      "2d",
      "",
      "形象类型（目前为 2d）"
     ],
     [
      "theme",
      "varchar(30)",
      "N",
      "violet",
      "",
      "主题色"
     ],
     [
      "tagline",
      "varchar(200)",
      "N",
      "",
      "",
      "一句话标签"
     ],
     [
      "description",
      "varchar(200)",
      "N",
      "",
      "",
      "说明文案"
     ],
     [
      "greeting",
      "varchar(300)",
      "N",
      "",
      "",
      "问候语"
     ],
     [
      "default_voice",
      "varchar(50)",
      "N",
      "emma",
      "",
      "默认音色 style（如 emma）"
     ],
     [
      "appearance",
      "json",
      "Y",
      "",
      "",
      "外观参数 JSON"
     ],
     [
      "created_at",
      "datetime",
      "N",
      "auto",
      "",
      "创建时间（UTC）"
     ],
     [
      "updated_at",
      "datetime",
      "N",
      "auto",
      "",
      "最近更新时间（UTC）"
     ]
    ],
    "unique": []
   },
   {
    "name": "avatar_preferences",
    "title": "数字人偏好",
    "about": "(user_id, scene_id) 联合主键，scene_id 为空串表示「跟随场景推荐」档。",
    "cols": [
     [
      "user_id",
      "int",
      "N",
      "",
      "PK FK→users.id",
      "用户 ID：随账户云端同步"
     ],
     [
      "scene_id",
      "varchar(50)",
      "N",
      "",
      "PK",
      "场景键：''=跟随推荐，其余为场景 id（不设外键，'' 不在 scenes 表）"
     ],
     [
      "avatar_id",
      "varchar(50)",
      "N",
      "",
      "",
      "数字人形象 ID：前端固定形象清单内的 id（如 mira_2d）"
     ],
     [
      "role_id",
      "varchar(50)",
      "Y",
      "",
      "",
      "交流身份 ID：NULL 表示跟随缺省身份（已废弃，恒 NULL）"
     ],
     [
      "voice_style",
      "varchar(50)",
      "N",
      "",
      "",
      "音色风格：前端音色清单内的 style（如 emma）"
     ],
     [
      "speech_rate",
      "float",
      "N",
      "1.0",
      "",
      "语速倍率：0.75~1.25"
     ],
     [
      "lip_sync_enabled",
      "int",
      "N",
      "1",
      "",
      "口型演示开关：0/1（布尔语义）"
     ],
     [
      "created_at",
      "datetime",
      "N",
      "auto",
      "",
      "创建时间：UTC"
     ],
     [
      "updated_at",
      "datetime",
      "N",
      "auto",
      "",
      "最近保存时间（UTC）"
     ]
    ],
    "unique": []
   }
  ]
 },
 {
  "group": "听力、复习与成长",
  "tables": [
   {
    "name": "listening_units",
    "title": "听力单元",
    "about": "日常 / 四六级 / 电台 / 演讲四个频道，exercises_json 存练习题数组。",
    "cols": [
     [
      "id",
      "varchar(80)",
      "N",
      "",
      "PK",
      "主键"
     ],
     [
      "channel",
      "varchar(24)",
      "N",
      "",
      "IDX",
      "daily | cet | radio | talks"
     ],
     [
      "cet_level",
      "varchar(16)",
      "Y",
      "",
      "IDX",
      "cet4 | cet6"
     ],
     [
      "cet_section",
      "varchar(24)",
      "Y",
      "",
      "",
      "news | conversation | passage | lecture"
     ],
     [
      "channel_label",
      "varchar(64)",
      "N",
      "",
      "",
      "频道中文名"
     ],
     [
      "level",
      "varchar(48)",
      "N",
      "",
      "",
      "难度/级别文案"
     ],
     [
      "title",
      "varchar(180)",
      "N",
      "",
      "",
      "单元标题"
     ],
     [
      "subtitle",
      "text",
      "N",
      "",
      "",
      "副标题"
     ],
     [
      "duration",
      "varchar(32)",
      "N",
      "5 分钟",
      "",
      "时长文案，如「8 分钟」，决定最大轮数（≤6 分钟 4 轮 / ≤9 分钟 6 轮 / 其余 8 轮）"
     ],
     [
      "xp",
      "int",
      "N",
      "25",
      "",
      "完成单元可获得的 XP"
     ],
     [
      "accent",
      "varchar(48)",
      "N",
      "美音 · 常速",
      "",
      "口音与语速文案"
     ],
     [
      "exercises_json",
      "json",
      "N",
      "",
      "",
      "练习题数组"
     ],
     [
      "is_builtin",
      "bool",
      "N",
      "True",
      "",
      "是否为系统内置"
     ],
     [
      "owner_id",
      "int",
      "Y",
      "",
      "FK→users.id IDX",
      "创建者用户 ID；内置数据为 NULL"
     ],
     [
      "created_at",
      "datetime",
      "N",
      "auto",
      "",
      "创建时间（UTC）"
     ]
    ],
    "unique": []
   },
   {
    "name": "listening_attempts",
    "title": "听力作答记录",
    "about": "逐题记录对错、是否独立完成与使用的提示，用于错因分析。",
    "cols": [
     [
      "id",
      "int",
      "N",
      "",
      "PK",
      "主键"
     ],
     [
      "user_id",
      "int",
      "N",
      "",
      "FK→users.id IDX",
      "所属用户 ID"
     ],
     [
      "unit_id",
      "varchar(80)",
      "N",
      "",
      "IDX",
      "听力单元 ID"
     ],
     [
      "exercise_id",
      "varchar(64)",
      "N",
      "",
      "",
      "题目 ID"
     ],
     [
      "exercise_type",
      "varchar(24)",
      "N",
      "",
      "",
      "题型"
     ],
     [
      "is_correct",
      "bool",
      "N",
      "",
      "",
      "是否答对"
     ],
     [
      "is_independent",
      "bool",
      "N",
      "True",
      "",
      "是否未借助提示独立完成"
     ],
     [
      "hints_used_json",
      "json",
      "N",
      "auto",
      "",
      "使用过的提示列表"
     ],
     [
      "error_tag",
      "varchar(48)",
      "N",
      "",
      "",
      "错因标签"
     ],
     [
      "created_at",
      "datetime",
      "N",
      "auto",
      "IDX",
      "创建时间（UTC）"
     ]
    ],
    "unique": []
   },
   {
    "name": "listening_progress",
    "title": "听力单元进度",
    "about": "(user_id, unit_id) 唯一。",
    "cols": [
     [
      "id",
      "int",
      "N",
      "",
      "PK",
      "主键"
     ],
     [
      "user_id",
      "int",
      "N",
      "",
      "FK→users.id IDX",
      "所属用户 ID"
     ],
     [
      "unit_id",
      "varchar(80)",
      "N",
      "",
      "FK→listening_units.id IDX",
      "听力单元 ID"
     ],
     [
      "progress",
      "int",
      "N",
      "0",
      "",
      "0..100"
     ],
     [
      "completed_count",
      "int",
      "N",
      "0",
      "",
      "累计完成次数"
     ],
     [
      "updated_at",
      "datetime",
      "N",
      "auto",
      "",
      "最近更新时间（UTC）"
     ]
    ],
    "unique": [
     "UNIQUE(user_id, unit_id)"
    ]
   },
   {
    "name": "review_items",
    "title": "复习卡片（SM-2）",
    "about": "间隔重复算法的状态：repetitions / interval_days / ease_factor / due_at；source_key 保证由对话自动入库的幂等。",
    "cols": [
     [
      "id",
      "int",
      "N",
      "",
      "PK",
      "主键"
     ],
     [
      "user_id",
      "int",
      "N",
      "",
      "FK→users.id IDX",
      "所属用户 ID"
     ],
     [
      "kind",
      "varchar(24)",
      "N",
      "expression",
      "",
      "expression | pronunciation | grammar | listening"
     ],
     [
      "prompt",
      "text",
      "N",
      "",
      "",
      "卡片正面"
     ],
     [
      "answer",
      "text",
      "N",
      "",
      "",
      "卡片背面"
     ],
     [
      "phonetic",
      "varchar(255)",
      "N",
      "",
      "",
      "音标"
     ],
     [
      "note",
      "text",
      "N",
      "",
      "",
      "备注"
     ],
     [
      "context_text",
      "text",
      "N",
      "",
      "",
      "出处语境"
     ],
     [
      "source_type",
      "varchar(24)",
      "N",
      "manual",
      "",
      "manual | correction | pronunciation | agent_task"
     ],
     [
      "source_key",
      "varchar(120)",
      "Y",
      "",
      "",
      "幂等去重键；手动添加为 NULL"
     ],
     [
      "source_session_id",
      "varchar(36)",
      "Y",
      "",
      "IDX",
      "来源会话 ID"
     ],
     [
      "scene_id",
      "varchar(50)",
      "Y",
      "",
      "",
      "关联场景 ID"
     ],
     [
      "scene_name",
      "varchar(120)",
      "N",
      "",
      "",
      "来源场景名"
     ],
     [
      "repetitions",
      "int",
      "N",
      "0",
      "",
      "连续记住次数"
     ],
     [
      "interval_days",
      "int",
      "N",
      "0",
      "",
      "当前间隔天数"
     ],
     [
      "ease_factor",
      "float",
      "N",
      "2.5",
      "",
      "SM-2 难度系数（初值 2.5）"
     ],
     [
      "mastery",
      "int",
      "N",
      "0",
      "",
      "掌握度"
     ],
     [
      "status",
      "varchar(20)",
      "N",
      "active",
      "",
      "active | mastered"
     ],
     [
      "due_at",
      "datetime",
      "N",
      "auto",
      "",
      "下次到期时间"
     ],
     [
      "last_reviewed_at",
      "datetime",
      "Y",
      "",
      "",
      "最近复习时间"
     ],
     [
      "created_at",
      "datetime",
      "N",
      "auto",
      "",
      "创建时间（UTC）"
     ],
     [
      "updated_at",
      "datetime",
      "N",
      "auto",
      "",
      "最近更新时间（UTC）"
     ]
    ],
    "unique": [
     "UNIQUE(user_id, source_key)"
    ]
   },
   {
    "name": "user_xp_states",
    "title": "XP 与段位",
    "about": "总 XP、今日 XP、连续学习天数与听力模块签到状态。",
    "cols": [
     [
      "user_id",
      "int",
      "N",
      "",
      "PK FK→users.id",
      "所属用户 ID"
     ],
     [
      "total_xp",
      "int",
      "N",
      "0",
      "",
      "累计 XP"
     ],
     [
      "today_xp",
      "int",
      "N",
      "0",
      "",
      "今日 XP"
     ],
     [
      "today_date",
      "varchar(10)",
      "N",
      "",
      "",
      "今日日期"
     ],
     [
      "streak_days",
      "int",
      "N",
      "0",
      "",
      "连续学习天数"
     ],
     [
      "last_checkin_date",
      "varchar(10)",
      "N",
      "",
      "",
      "最近签到日期"
     ],
     [
      "checkin_streak",
      "int",
      "N",
      "0",
      "",
      "连续签到天数"
     ],
     [
      "updated_at",
      "datetime",
      "N",
      "auto",
      "",
      "最近更新时间（UTC）"
     ]
    ],
    "unique": []
   }
  ]
 },
 {
  "group": "SaaS 商业化与计量",
  "tables": [
   {
    "name": "saas_plan_configs",
    "title": "套餐配置",
    "about": "free / pro / enterprise 三档的价格、每日免费额度池、创建上限、ZIP 权限与各功能 quotas_json。",
    "cols": [
     [
      "tier",
      "varchar(20)",
      "N",
      "",
      "PK",
      "free / pro / enterprise"
     ],
     [
      "name",
      "varchar(50)",
      "N",
      "",
      "",
      "名称"
     ],
     [
      "description",
      "varchar(200)",
      "N",
      "",
      "",
      "说明文案"
     ],
     [
      "monthly_price_yuan",
      "int",
      "N",
      "0",
      "",
      "月付价格（元）"
     ],
     [
      "yearly_price_yuan",
      "int",
      "N",
      "0",
      "",
      "年付价格（元）"
     ],
     [
      "monthly_grant_credits",
      "int",
      "N",
      "0",
      "",
      "订阅期内每月赠送的积分"
     ],
     [
      "daily_free_credits",
      "int",
      "N",
      "40",
      "",
      "每日共享免费额度池点数（-1 表示无限）"
     ],
     [
      "max_custom_scenes",
      "int",
      "N",
      "2",
      "",
      "-1 表示无限制"
     ],
     [
      "max_custom_debates",
      "int",
      "N",
      "1",
      "",
      "-1 表示无限制"
     ],
     [
      "max_knowledge_docs",
      "int",
      "N",
      "0",
      "",
      "-1 表示无限制"
     ],
     [
      "allow_zip_import",
      "int",
      "N",
      "0",
      "",
      "0/1：是否允许导入场景包 ZIP"
     ],
     [
      "allow_zip_export",
      "int",
      "N",
      "0",
      "",
      "0/1：是否允许导出场景包 ZIP"
     ],
     [
      "checkin_multiplier",
      "int",
      "N",
      "1",
      "",
      "签到积分倍率"
     ],
     [
      "credit_discount_rate",
      "float",
      "N",
      "1.0",
      "",
      "超额消耗积分折扣（如 0.8 表示 8 折）"
     ],
     [
      "quotas_json",
      "json",
      "N",
      "auto",
      "",
      "各功能 action_key 的 {daily_free, credit_cost, allow_overage_credits}"
     ],
     [
      "updated_at",
      "datetime",
      "N",
      "auto",
      "",
      "最近更新时间（UTC）"
     ]
    ],
    "unique": []
   },
   {
    "name": "saas_billing_configs",
    "title": "计费换算配置",
    "about": "固定 id=1 的单行表：积分↔Token 换算与输入/输出百万 Token 采购单价。",
    "cols": [
     [
      "id",
      "int",
      "N",
      "",
      "PK",
      "固定 id=1"
     ],
     [
      "tokens_per_credit",
      "int",
      "N",
      "1000",
      "",
      "1 回声积分对应理论 Tokens"
     ],
     [
      "prompt_price_per_million",
      "float",
      "N",
      "2.0",
      "",
      "输入单价：元 / 1M Tokens"
     ],
     [
      "completion_price_per_million",
      "float",
      "N",
      "8.0",
      "",
      "输出单价：元 / 1M Tokens"
     ],
     [
      "updated_at",
      "datetime",
      "N",
      "auto",
      "",
      "最近更新时间（UTC）"
     ]
    ],
    "unique": []
   },
   {
    "name": "saas_campaigns",
    "title": "限时活动",
    "about": "积分倍率与限免功能列表，在 starts_at ~ ends_at 内生效。",
    "cols": [
     [
      "id",
      "int",
      "N",
      "",
      "PK",
      "主键"
     ],
     [
      "name",
      "varchar(80)",
      "N",
      "",
      "",
      "名称"
     ],
     [
      "description",
      "varchar(200)",
      "N",
      "",
      "",
      "说明文案"
     ],
     [
      "bonus_multiplier",
      "float",
      "N",
      "1.0",
      "",
      "任务/签到积分倍率"
     ],
     [
      "free_actions_json",
      "json",
      "N",
      "auto",
      "",
      "限免的 action_key 列表"
     ],
     [
      "starts_at",
      "datetime",
      "N",
      "",
      "",
      "生效开始时间"
     ],
     [
      "ends_at",
      "datetime",
      "N",
      "",
      "",
      "生效结束时间"
     ],
     [
      "enabled",
      "int",
      "N",
      "1",
      "",
      "是否启用（0/1）"
     ],
     [
      "created_at",
      "datetime",
      "N",
      "auto",
      "",
      "创建时间（UTC）"
     ]
    ],
    "unique": []
   },
   {
    "name": "credit_task_defs",
    "title": "任务定义",
    "about": "日常与新手任务及其积分奖励，管理端可热配置。",
    "cols": [
     [
      "task_code",
      "varchar(40)",
      "N",
      "",
      "PK",
      "任务编码"
     ],
     [
      "title",
      "varchar(80)",
      "N",
      "",
      "",
      "任务标题"
     ],
     [
      "description",
      "varchar(200)",
      "N",
      "",
      "",
      "说明文案"
     ],
     [
      "category",
      "varchar(20)",
      "N",
      "daily",
      "",
      "daily / onboarding"
     ],
     [
      "target_count",
      "int",
      "N",
      "1",
      "",
      "完成所需次数"
     ],
     [
      "reward_credits",
      "int",
      "N",
      "10",
      "",
      "完成奖励的回声积分"
     ],
     [
      "daily_limit",
      "int",
      "N",
      "1",
      "",
      "每日可领取次数"
     ],
     [
      "route_path",
      "varchar(64)",
      "N",
      "/",
      "",
      "前端跳转路径"
     ],
     [
      "enabled",
      "int",
      "N",
      "1",
      "",
      "是否启用（0/1）"
     ],
     [
      "sort_order",
      "int",
      "N",
      "10",
      "",
      "排序值，越小越靠前"
     ]
    ],
    "unique": []
   },
   {
    "name": "user_task_progress",
    "title": "任务进度",
    "about": "(user_id, task_code, period_key) 唯一；日常任务 period_key 为日期，新手任务为 LIFETIME。",
    "cols": [
     [
      "id",
      "int",
      "N",
      "",
      "PK",
      "主键"
     ],
     [
      "user_id",
      "int",
      "N",
      "",
      "FK→users.id IDX",
      "所属用户 ID"
     ],
     [
      "task_code",
      "varchar(40)",
      "N",
      "",
      "IDX",
      "任务编码"
     ],
     [
      "period_key",
      "varchar(20)",
      "N",
      "",
      "",
      "YYYY-MM-DD 或 LIFETIME"
     ],
     [
      "progress_count",
      "int",
      "N",
      "0",
      "",
      "当前周期进度"
     ],
     [
      "claimed_count",
      "int",
      "N",
      "0",
      "",
      "已领奖次数"
     ],
     [
      "updated_at",
      "datetime",
      "N",
      "auto",
      "",
      "最近更新时间（UTC）"
     ]
    ],
    "unique": [
     "UNIQUE(user_id, task_code, period_key)"
    ]
   },
   {
    "name": "user_daily_usage",
    "title": "每日额度使用",
    "about": "(user_id, date_str, action_key) 唯一，记录共享池消耗与超额积分扣减。",
    "cols": [
     [
      "id",
      "int",
      "N",
      "",
      "PK",
      "主键"
     ],
     [
      "user_id",
      "int",
      "N",
      "",
      "FK→users.id IDX",
      "所属用户 ID"
     ],
     [
      "date_str",
      "varchar(10)",
      "N",
      "",
      "IDX",
      "YYYY-MM-DD"
     ],
     [
      "action_key",
      "varchar(40)",
      "N",
      "",
      "IDX",
      "功能点编码（见 ACTION_META）"
     ],
     [
      "free_used_count",
      "int",
      "N",
      "0",
      "",
      "共享池已消耗点数"
     ],
     [
      "paid_used_count",
      "int",
      "N",
      "0",
      "",
      "超额使用次数"
     ],
     [
      "credits_spent",
      "int",
      "N",
      "0",
      "",
      "当日扣减的积分"
     ],
     [
      "updated_at",
      "datetime",
      "N",
      "auto",
      "",
      "最近更新时间（UTC）"
     ]
    ],
    "unique": [
     "UNIQUE(user_id, date_str, action_key)"
    ]
   },
   {
    "name": "credit_ledger",
    "title": "积分账本",
    "about": "每一次积分变动（签到、任务、充值、兑换、消耗、管理员调整）一行，含变动后余额。",
    "cols": [
     [
      "id",
      "int",
      "N",
      "",
      "PK",
      "主键"
     ],
     [
      "user_id",
      "int",
      "N",
      "",
      "FK→users.id IDX",
      "所属用户 ID"
     ],
     [
      "delta",
      "int",
      "N",
      "",
      "",
      "积分变动量（正为获得、负为消耗）"
     ],
     [
      "balance_after",
      "int",
      "N",
      "",
      "",
      "变动后的积分余额"
     ],
     [
      "source_type",
      "varchar(40)",
      "N",
      "",
      "IDX",
      "来源类型"
     ],
     [
      "action_key",
      "varchar(40)",
      "Y",
      "",
      "",
      "功能点编码（见 ACTION_META）"
     ],
     [
      "ref_id",
      "varchar(64)",
      "Y",
      "",
      "",
      "关联业务 ID（会话、订单等）"
     ],
     [
      "remark",
      "varchar(200)",
      "N",
      "",
      "",
      "备注"
     ],
     [
      "created_at",
      "datetime",
      "N",
      "auto",
      "IDX",
      "创建时间（UTC）"
     ]
    ],
    "unique": []
   },
   {
    "name": "subscription_orders",
    "title": "订阅/充值订单",
    "about": "历史/保留表：payment_channel 默认 mock_checkout；直接模拟下单接口已关闭，会员与积分当前通过兑换码或管理员发放。",
    "cols": [
     [
      "id",
      "int",
      "N",
      "",
      "PK",
      "主键"
     ],
     [
      "order_no",
      "varchar(40)",
      "N",
      "",
      "UQ",
      "订单号，唯一"
     ],
     [
      "user_id",
      "int",
      "N",
      "",
      "FK→users.id IDX",
      "所属用户 ID"
     ],
     [
      "order_type",
      "varchar(20)",
      "N",
      "",
      "",
      "plan_upgrade / credit_pack"
     ],
     [
      "target_tier",
      "varchar(20)",
      "Y",
      "",
      "",
      "pro / enterprise"
     ],
     [
      "billing_cycle",
      "varchar(20)",
      "Y",
      "",
      "",
      "monthly / yearly"
     ],
     [
      "credits_granted",
      "int",
      "N",
      "0",
      "",
      "发放积分"
     ],
     [
      "amount_yuan",
      "int",
      "N",
      "0",
      "",
      "金额（元）"
     ],
     [
      "status",
      "varchar(20)",
      "N",
      "paid",
      "",
      "paid / refunded"
     ],
     [
      "payment_channel",
      "varchar(30)",
      "N",
      "mock_checkout",
      "",
      "支付渠道"
     ],
     [
      "created_at",
      "datetime",
      "N",
      "auto",
      "IDX",
      "创建时间（UTC）"
     ]
    ],
    "unique": []
   },
   {
    "name": "redeem_codes",
    "title": "兑换码",
    "about": "可兑换积分或会员天数，一码一用。",
    "cols": [
     [
      "id",
      "int",
      "N",
      "",
      "PK",
      "主键"
     ],
     [
      "code",
      "varchar(40)",
      "N",
      "",
      "UQ",
      "兑换码字符串，唯一"
     ],
     [
      "reward_type",
      "varchar(20)",
      "N",
      "",
      "",
      "credits / plan_days"
     ],
     [
      "reward_credits",
      "int",
      "N",
      "0",
      "",
      "完成奖励的回声积分"
     ],
     [
      "reward_tier",
      "varchar(20)",
      "Y",
      "",
      "",
      "pro / enterprise"
     ],
     [
      "reward_days",
      "int",
      "N",
      "0",
      "",
      "奖励的会员天数"
     ],
     [
      "is_used",
      "int",
      "N",
      "0",
      "",
      "是否已核销（0/1）"
     ],
     [
      "used_by_user_id",
      "int",
      "Y",
      "",
      "IDX",
      "核销用户 ID"
     ],
     [
      "used_at",
      "datetime",
      "Y",
      "",
      "",
      "核销时间"
     ],
     [
      "expires_at",
      "datetime",
      "Y",
      "",
      "",
      "过期时间"
     ],
     [
      "note",
      "varchar(120)",
      "N",
      "",
      "",
      "备注"
     ],
     [
      "created_at",
      "datetime",
      "N",
      "auto",
      "",
      "创建时间（UTC）"
     ]
    ],
    "unique": []
   },
   {
    "name": "api_token_usage",
    "title": "Token 流水",
    "about": "按 chat / embedding / lightrag_llm 分类记录每次模型调用，用于成本与毛利核算。",
    "cols": [
     [
      "id",
      "int",
      "N",
      "",
      "PK",
      "主键"
     ],
     [
      "user_id",
      "int",
      "Y",
      "",
      "IDX",
      "所属用户 ID"
     ],
     [
      "session_id",
      "varchar(36)",
      "Y",
      "",
      "IDX",
      "所属会话 ID"
     ],
     [
      "scene_id",
      "varchar(50)",
      "Y",
      "",
      "IDX",
      "关联场景 ID"
     ],
     [
      "turn_id",
      "varchar(36)",
      "Y",
      "",
      "",
      "关联轮次 ID"
     ],
     [
      "category",
      "varchar(30)",
      "N",
      "",
      "IDX",
      "chat / embedding / lightrag_llm"
     ],
     [
      "model",
      "varchar(100)",
      "N",
      "",
      "IDX",
      "模型名称"
     ],
     [
      "prompt_tokens",
      "int",
      "N",
      "0",
      "",
      "输入 Token 数"
     ],
     [
      "completion_tokens",
      "int",
      "N",
      "0",
      "",
      "输出 Token 数"
     ],
     [
      "total_tokens",
      "int",
      "N",
      "0",
      "",
      "总 Token 数"
     ],
     [
      "call_count",
      "int",
      "N",
      "1",
      "",
      "合并的调用次数"
     ],
     [
      "created_at",
      "datetime",
      "N",
      "auto",
      "IDX",
      "创建时间（UTC）"
     ]
    ],
    "unique": []
   }
  ]
 }
]

<template>
  <div class="page-layout">
    <aside class="sidebar-nav">
      <h4>开始使用</h4>
      <a href="#quickstart" @click.prevent="scrollTo('quickstart')">快速上手</a>
      <a href="#install" @click.prevent="scrollTo('install')">安装部署</a>
      <a href="#first-run" @click.prevent="scrollTo('first-run')">首次运行</a>
      <h4>使用指南</h4>
      <a href="#guide" @click.prevent="scrollTo('guide')">核心功能</a>
      <a href="#scenes" @click.prevent="scrollTo('scenes')">场景练习</a>
      <a href="#kb" @click.prevent="scrollTo('kb')">知识库配置</a>
      <a href="#analytics" @click.prevent="scrollTo('analytics')">成长分析</a>
      <h4>开发文档</h4>
      <a href="#scene-dev" @click.prevent="scrollTo('scene-dev')">场景开发</a>
      <a href="#scene-plugin" @click.prevent="scrollTo('scene-plugin')">插件接口</a>
      <a href="#api" @click.prevent="scrollTo('api')">API 参考</a>
      <a href="#arch" @click.prevent="scrollTo('arch')">系统架构</a>
    </aside>

    <main class="doc-main">
      <h1>产品文档</h1>
      <p class="subtitle">EchoTalk v1.0.0 — AI 驱动的英语口语练习桌面应用</p>

      <h2 id="quickstart">快速上手</h2>
      <p>EchoTalk 是一款基于 AI 的英语口语练习桌面应用（Windows）。通过沉浸式场景模拟（面试 / 点餐 / 会议）、ASR 语音识别、TTS 语音合成、RAG 知识库增强及多维度发音评测，帮助你在真实语境中提升英语口语能力。</p>

      <h3 id="install">安装部署</h3>
      <p><strong>方式一：使用安装包（推荐）</strong></p>
      <ol>
        <li>前往 <router-link to="/#download" style="color:var(--primary)">下载页面</router-link> 获取 Windows 安装包</li>
        <li>运行 <code>EchoTalk Setup 1.0.0.exe</code>，按提示完成安装</li>
        <li>首次启动会自动初始化 SQLite 数据库、注入种子场景（面试 / 点餐 / 会议）并预合成问候语 TTS 音频（约 1-3 分钟）</li>
      </ol>
      <p><strong>方式二：从源码构建</strong></p>
      <pre><code># 1. 后端环境
cd backend
python -m venv ../.venv
source ../.venv/Scripts/activate   # Windows
pip install -r requirements.txt

# 2. 配置 API 密钥（可选，未配置会自动降级为本地 Mock 引擎）
cp .env.template .env
# 编辑 .env，填入各服务的 API Key

# 3. 启动后端 (FastAPI on :8000)
python main.py

# 4. 前端开发 (Vite on :5173)
cd ../frontend
npm install
npm run dev

# 5. Electron 桌面模式（自动拉起后端 + 前端）
npm run electron:dev

# 6. 打包为 Windows 安装包
npm run pack</code></pre>
      <div class="callout info">💡 后端默认运行在 <code>http://127.0.0.1:8000</code>，前端开发模式默认 <code>http://127.0.0.1:5173</code>。Electron 打包后后端端口变为 <code>18765</code>。</div>

      <h3 id="first-run">首次运行</h3>
      <p>首次启动 EchoTalk，应用会经历以下初始化阶段（前端 Splash 页面可实时查看进度）：</p>
      <table>
        <tr><th>阶段</th><th>内容</th><th>预计耗时</th></tr>
        <tr><td>Schema 升级</td><td>自适应 SQLite 表结构热升级（ALTER TABLE 热注入缺失字段）</td><td>&lt; 5s</td></tr>
        <tr><td>场景种子</td><td>注册 3 个内置场景 + Edge-TTS 预合成问候语音频</td><td>10-60s</td></tr>
        <tr><td>用户注册</td><td>自动创建 default_user 本地账户</td><td>&lt; 2s</td></tr>
      </table>
      <div class="callout info">💡 所有外部服务（STT、ISE 发音评测、LLM 对话、TTS、向量嵌入）在未配置 API Key 时<strong>自动优雅降级为本地 Mock 引擎</strong>，应用始终可用。</div>

      <h2 id="guide">使用指南</h2>

      <h3 id="scenes">场景练习</h3>
      <p>EchoTalk 的核心是 <strong>场景化角色扮演口语练习</strong>。每个场景包含：</p>
      <ul>
        <li><strong>System Prompt</strong> — AI 扮演的角色人格与对话规则（如"你是一个严格但专业的面试官 Sarah"）</li>
        <li><strong>Greeting Text</strong> — AI 说的第一句问候语，启动即触发，减少首次交互延迟</li>
        <li><strong>RAG 知识库</strong> — 场景专属的参考文档（如咖啡馆菜单、面试评价标准），AI 基于这些内容生成上下文相关的回复</li>
        <li><strong>评估规则</strong> — 针对该场景的口语评估维度（如面试侧重逻辑与专业词汇，点餐侧重日常表达）</li>
      </ul>
      <p>当前内置场景：</p>
      <table>
        <tr><th>场景</th><th>标识</th><th>AI 角色</th><th>描述</th></tr>
        <tr><td>软件工程师面试</td><td><code>interview</code></td><td>Sarah (面试官)</td><td>模拟外企前端技术面试，考察专业术语与逻辑表达</td></tr>
        <tr><td>产品发布会会议</td><td><code>meeting</code></td><td>David (产品经理)</td><td>跨国项目同步会议，讨论进度延误与资源分配</td></tr>
        <tr><td>繁忙咖啡厅点餐</td><td><code>ordering</code></td><td>Leo (咖啡师)</td><td>纽约街头咖啡馆点餐与结账对话</td></tr>
      </table>

      <h3 id="kb">知识库配置 (RAG)</h3>
      <p>EchoTalk 使用 <strong>FAISS 向量索引 + BAAI/bge-large-en-v1.5 嵌入模型</strong> 实现 RAG（检索增强生成）：</p>
      <ol>
        <li>进入场景详情页，点击「知识库管理」</li>
        <li>上传文档（支持 PDF、TXT、Markdown 格式）</li>
        <li>系统自动解析文档 → 递归分节切片（RecursiveTextSplitter，chunk_size=400，overlap=50）→ 向量化 → 存入 FAISS 本地索引</li>
        <li>对话时，用户语音转文字后自动检索 Top-K 相关分块注入 LLM 上下文</li>
      </ol>
      <div class="callout info">💡 知识库分块支持 <strong>visibility 控制</strong>：标记为 "user" 的节（如菜单、词汇表）对用户可见；标记为 "ai_only" 的节（如内部流程、定价规则）仅 AI 使用。</div>
      <div class="callout warning">⚠ 若未配置 Embedding API Key（如 Siliconflow），系统会自动降级为本地 MD5 特征哈希向量生成器，保证 RAG 流程不中断。</div>

      <h3 id="analytics">成长分析与数据</h3>
      <p>每次练习对话结束后，系统自动记录以下数据：</p>
      <ul>
        <li><strong>发音评测</strong> — 科大讯飞 ISE 引擎返回的 total_score / accuracy_score / fluency_score / integrity_score / intonation_score / liaison_score 六维评分，以及单词级发音详情（含音素级评分）</li>
        <li><strong>语法纠错</strong> — LLM 对每轮用户输入进行的语法修正建议（原文 → 优化版 → 解释 + 词汇 / 发音建议）</li>
        <li><strong>对话完整性</strong> — 是否由 AI 判定结束（is_finished）</li>
        <li><strong>历史回放</strong> — 完整保存对话文本与音频 URL（七牛云 Kodo 托管或本地静态回退），支持随时回放复盘</li>
        <li><strong>可视化雷达图</strong> — 练习记录页展示发音各维度的 ECharts 雷达图</li>
      </ul>

      <h2 id="scene-dev">场景开发</h2>
      <p>EchoTalk 的场景系统采用 <strong>插件化架构</strong>，但实际运行中场景配置主要存储在 SQLite 数据库的 <code>scenes</code> 表中。核心字段包括 system_prompt、greeting_text、default_params（JSON）等。内置场景在 <code>backend/app/main.py</code> 的 <code>seed_default_scenes()</code> 中注册。</p>

      <h3 id="scene-plugin">场景包结构与创建</h3>
      <p>场景包是一个包含 <code>scene_config.json</code> 和可选 RAG 索引文件的 .zip 压缩包：</p>
      <pre><code>my_scene_package.zip
├── scene_config.json          # 场景配置（必需）
├── my_scene.index             # FAISS 向量索引（可选）
└── my_scene.json              # 向量→文本映射（可选）</code></pre>
      <p><strong>scene_config.json 示例：</strong></p>
      <pre><code>{
  "id": "hotel_checkin",
  "name": "酒店入住英语",
  "description": "练习海外酒店入住全流程英语对话",
  "category": "travel",
  "default_params": {
    "personality": "polite and professional",
    "hotel_name": "Grand Plaza Hotel",
    "receptionist_name": "Emma"
  },
  "system_prompt": "You are Emma...",
  "greeting_text": "Good evening! Welcome to Grand Plaza Hotel. Do you have a reservation?",
  "rag_metadata": []
}</code></pre>

      <h3>场景包的导入导出</h3>
      <p>EchoTalk 内置了场景导入导出功能：</p>
      <div class="endpoint"><span class="badge method">GET</span> <code>/api/scenes/{scene_id}/export</code></div>
      <p>导出场景为 .zip 文件（含 scene_config.json + FAISS 索引文件）</p>
      <div class="endpoint"><span class="badge method">POST</span> <code>/api/scenes/import</code></div>
      <p>上传场景 .zip 包进行导入（支持覆盖更新已有场景）</p>

      <h2 id="api">API 参考</h2>
      <p>EchoTalk 后端提供完整的 RESTful API，基础路径为 <code>http://127.0.0.1:8000/api</code>。</p>

      <h3>初始化状态</h3>
      <div class="endpoint"><span class="badge method">GET</span> <code>/api/init-status</code></div>
      <p>获取后端初始化进度（phase / message / progress / detail），前端 Splash 页面轮询此接口。</p>

      <h3>场景管理</h3>
      <div class="endpoint"><span class="badge method">GET</span> <code>/api/scenes</code></div>
      <p>获取所有已注册的练习场景列表。</p>
      <div class="endpoint"><span class="badge method">GET</span> <code>/api/scenes/{scene_id}</code></div>
      <p>获取单个场景的详细配置。</p>
      <div class="endpoint"><span class="badge method">POST</span> <code>/api/scenes</code></div>
      <p>创建新的自定义口语对话场景。</p>
      <div class="endpoint"><span class="badge method">PUT</span> <code>/api/scenes/{scene_id}</code></div>
      <p>编辑修改已有场景参数。</p>
      <div class="endpoint"><span class="badge method">DELETE</span> <code>/api/scenes/{scene_id}</code></div>
      <p>删除场景及其关联的练习历史与 RAG 知识库。</p>

      <h3>场景知识库 (RAG)</h3>
      <div class="endpoint"><span class="badge method">POST</span> <code>/api/scenes/{scene_id}/upload</code></div>
      <p>上传 PDF/TXT/MD 文档，自动解析切片并录入 FAISS 向量索引。</p>
      <div class="endpoint"><span class="badge method">GET</span> <code>/api/scenes/{scene_id}/knowledge</code></div>
      <p>获取场景中用户可见（visibility=user）的知识库分节内容。</p>
      <div class="endpoint"><span class="badge method">GET</span> <code>/api/scenes/{scene_id}/knowledge/sections</code></div>
      <p>获取场景知识库的全部分节概览（含 visibility 信息）。</p>
      <div class="endpoint"><span class="badge method">PATCH</span> <code>/api/scenes/{scene_id}/knowledge/sections</code></div>
      <p>修改某个分节的可见性（user ↔ ai_only）。</p>
      <div class="endpoint"><span class="badge method">DELETE</span> <code>/api/scenes/{scene_id}/documents</code></div>
      <p>清空场景的本地 RAG 知识库所有内容。</p>

      <h3>口语会话</h3>
      <div class="endpoint"><span class="badge method">POST</span> <code>/api/dialogues/start</code></div>
      <p>启动一轮新的口语练习会话，自动生成问候语 TTS 音频。</p>
      <div class="endpoint"><span class="badge method">POST</span> <code>/api/dialogues/{history_id}/turn</code></div>
      <p>核心端点：上传用户录音 → 运行完整 Pipeline（STT → RAG → PII → ISE+LLM → TTS → Upload → 入库）。支持 <code>?stream=true</code> 参数启用 SSE 流式进度推送。</p>
      <div class="endpoint"><span class="badge method">POST</span> <code>/api/dialogues/{history_id}/settle</code></div>
      <p>会话终点结算：统计评分汇总，更新 overall_score 和 end_time。</p>
      <div class="endpoint"><span class="badge method">GET</span> <code>/api/dialogues/{history_id}</code></div>
      <p>查询指定会话的完整历史详情。</p>
      <div class="endpoint"><span class="badge method">GET</span> <code>/api/dialogues?user_id=1</code></div>
      <p>获取指定用户的所有练习会话历史列表。</p>
      <div class="endpoint"><span class="badge method">PUT</span> <code>/api/dialogues/{history_id}/style?speaking_style=formal</code></div>
      <p>切换说话风格（colloquial 口语化 / formal 书面化）。</p>
      <div class="endpoint"><span class="badge method">PUT</span> <code>/api/dialogues/{history_id}/accent?accent=uk</code></div>
      <p>切换发音口音（us 美音 / uk 英音）。</p>
      <div class="endpoint"><span class="badge method">POST</span> <code>/api/dialogues/turns/{turn_id}/synthesize?accent=uk</code></div>
      <p>按指定口音重新合成某一对话轮次的语音并缓存。</p>

      <h3>用户管理</h3>
      <div class="endpoint"><span class="badge method">GET</span> <code>/api/users/{user_id}</code></div>
      <p>获取用户信息。</p>
      <div class="endpoint"><span class="badge method">POST</span> <code>/api/users</code></div>
      <p>注册新用户。</p>

      <h3>系统设置</h3>
      <div class="endpoint"><span class="badge method">GET</span> <code>/api/settings</code></div>
      <p>获取当前系统配置（不含密钥）。</p>
      <div class="endpoint"><span class="badge method">PUT</span> <code>/api/settings</code></div>
      <p>更新系统设置，写入 settings.json 持久化。</p>

      <h2 id="arch">系统架构</h2>
      <pre><code>EchoTalk 系统架构
═══════════════════════════════════════════════════
┌─────────────────────────────────────────────────┐
│              Electron Shell                      │
│  frontend/electron/main.js  ── 自动拉起后端进程   │
│  preload.js  ── IPC 桥接暴露 backendBaseUrl      │
├─────────────────────────────────────────────────┤
│           Vue 3 SPA (frontend/src/)              │
│  ┌──────────┐ ┌──────────┐ ┌───────────────┐   │
│  │ Home.vue  │ │Practice  │ │History/Analyt.│   │
│  │ (场景选择) │ │.vue      │ │.vue (回放/图表)│   │
│  └──────────┘ └──────────┘ └───────────────┘   │
│  Pinia Store (useAppStore) ── 全局状态管理       │
│  Vue Router (Hash 模式) ── Electron 兼容路由     │
├─────────────────────────────────────────────────┤
│        FastAPI Backend (backend/app/)            │
│  ┌─────────────────────────────────────────┐    │
│  │          API Layer (/api)               │    │
│  │  scenes | dialogues | users | settings  │    │
│  └─────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────┐    │
│  │       核心管道 (Pipeline)                │    │
│  │  STT → RAG → PII → (ISE ∥ LLM) → TTS   │    │
│  └─────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────┐    │
│  │           服务层 (Services)              │    │
│  │  stt.py     ── 腾讯云 Flash ASR         │    │
│  │  assessment ── 科大讯飞 ISE WebSocket   │    │
│  │  tts.py     ── Edge-TTS / 腾讯云 TTS    │    │
│  │  rag.py     ── FAISS + BGE 向量检索     │    │
│  │  document   ── PDF/TXT/MD 解析分块      │    │
│  │  filter.py  ── PII 脱敏 (LLM+正则)      │    │
│  │  storage    ── 七牛云 Kodo / 本地回退   │    │
│  └─────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────┐    │
│  │       数据层                             │    │
│  │  SQLite (SQLAlchemy ORM)                │    │
│  │  FAISS 本地向量索引                      │    │
│  └─────────────────────────────────────────┘    │
├─────────────────────────────────────────────────┤
│           外部云服务 (可配置)                     │
│  DeepSeek / Xiaomi / OpenAI ── LLM 对话         │
│  Siliconflow ── Embedding 向量嵌入              │
│  科大讯飞 ── 发音评测 ISE                        │
│  腾讯云 ── ASR 语音识别 / TTS 语音合成           │
│  七牛云 Kodo ── 音频对象存储                     │
│  所有服务皆可降级为本地 Mock 引擎                 │
└─────────────────────────────────────────────────┘</code></pre>
    </main>
  </div>
</template>
<script setup>
const scrollTo = (id) => {
  const el = document.getElementById(id)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
</script>
<style scoped>
.page-layout { display: flex; }
.sidebar-nav { position: fixed; top: 76px; left: 0; width: 260px; height: calc(100vh - 76px); padding: 32px 24px; border-right: 1px solid var(--border); overflow-y: auto; background: rgba(8,12,20,0.5); }
.sidebar-nav h4 { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--text-dim); margin-bottom: 12px; margin-top: 24px; }
.sidebar-nav h4:first-child { margin-top: 0; }
.sidebar-nav a { display: block; padding: 10px 16px; border-radius: 8px; font-size: 0.95rem; color: var(--text-muted); transition: background 0.15s, color 0.15s; margin-bottom: 2px; cursor: pointer; }
.sidebar-nav a:hover { background: rgba(99,102,241,0.08); color: var(--text); }
.doc-main { margin-left: 260px; flex: 1; padding: 48px 64px 100px; max-width: 900px; }
.doc-main h1 { font-size: 2.8rem; font-weight: 800; margin-bottom: 12px; }
.doc-main .subtitle { font-size: 1.2rem; color: var(--text-muted); margin-bottom: 48px; }
.doc-main h2 { font-size: 1.7rem; font-weight: 700; margin-top: 56px; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 1px solid var(--border); }
.doc-main h3 { font-size: 1.3rem; font-weight: 700; margin-top: 32px; margin-bottom: 12px; }
.doc-main p { font-size: 1.05rem; color: var(--text-muted); margin-bottom: 16px; line-height: 1.8; }
.doc-main ul, .doc-main ol { margin-bottom: 16px; padding-left: 24px; }
.doc-main li { font-size: 1.02rem; color: var(--text-muted); margin-bottom: 8px; line-height: 1.7; }
.doc-main code { background: var(--bg-code); border: 1px solid var(--bg-code-border); padding: 2px 7px; border-radius: 6px; font-size: 0.9rem; font-family: 'Fira Code', 'Consolas', monospace; color: #c4b5fd; }
.doc-main pre { background: var(--bg-code); border: 1px solid var(--bg-code-border); border-radius: 10px; padding: 20px 24px; margin-bottom: 20px; overflow-x: auto; }
.doc-main pre code { background: none; border: none; padding: 0; font-size: 0.88rem; color: #e2e8f0; white-space: pre; }
.doc-main .callout { padding: 18px 22px; border-radius: 10px; margin-bottom: 20px; font-size: 1rem; line-height: 1.7; }
.doc-main .callout.info { background: rgba(59,130,246,0.08); border-left: 3px solid var(--blue); color: var(--text-muted); }
.doc-main .callout.warning { background: rgba(245,158,11,0.08); border-left: 3px solid #f59e0b; color: var(--text-muted); }
.doc-main table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 0.95rem; }
.doc-main th { text-align: left; padding: 12px 16px; background: rgba(99,102,241,0.06); color: var(--text); font-weight: 600; border-bottom: 1px solid var(--border); }
.doc-main td { padding: 12px 16px; border-bottom: 1px solid var(--border); color: var(--text-muted); }
.doc-main .badge { display: inline-block; padding: 4px 12px; border-radius: 6px; font-size: 0.8rem; font-weight: 600; background: rgba(16,185,129,0.12); color: var(--green); }
.doc-main .badge.method { background: rgba(59,130,246,0.12); color: var(--blue); }
.doc-main .endpoint { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
@media (max-width: 900px) { .sidebar-nav { display: none; } .doc-main { margin-left: 0; padding: 32px 20px 80px; } }
</style>

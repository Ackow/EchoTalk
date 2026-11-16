<template>
  <div class="docs-layout">
    <aside class="sidebar-nav">
      <div class="nav-group">
        <h4>开始使用</h4>
        <a href="#quickstart" :class="{ active: activeId === 'quickstart' }" @click.prevent="scrollTo('quickstart')">快速上手</a>
        <a href="#install" :class="{ active: activeId === 'install' }" @click.prevent="scrollTo('install')">三端启动部署</a>
        <a href="#migrations" :class="{ active: activeId === 'migrations' }" @click.prevent="scrollTo('migrations')">初始化与迁移</a>
      </div>
      <div class="nav-group">
        <h4>系统架构</h4>
        <a href="#dual-track" :class="{ active: activeId === 'dual-track' }" @click.prevent="scrollTo('dual-track')">1v1 与 1vN 双轨</a>
        <a href="#kb" :class="{ active: activeId === 'kb' }" @click.prevent="scrollTo('kb')">Hybrid + LightRAG</a>
        <a href="#saas" :class="{ active: activeId === 'saas' }" @click.prevent="scrollTo('saas')">SaaS 额度池与盈利</a>
      </div>
      <div class="nav-group">
        <h4>数据库与接口</h4>
        <a href="#database" :class="{ active: activeId === 'database' }" @click.prevent="scrollTo('database')">核心数据库表结构</a>
        <a href="#api-core" :class="{ active: activeId === 'api-core' }" @click.prevent="scrollTo('api-core')">业务 API 接口清单</a>
        <a href="#api-saas" :class="{ active: activeId === 'api-saas' }" @click.prevent="scrollTo('api-saas')">SaaS 与管理端接口</a>
        <a href="#scene-dev" :class="{ active: activeId === 'scene-dev' }" @click.prevent="scrollTo('scene-dev')">ScenePackage v2 规范</a>
      </div>
    </aside>

    <main class="doc-main">
      <div class="doc-hero">
        <span class="doc-badge">EchoTalk 2.0 工程与接口文档</span>
        <h1>产品与开发文档</h1>
        <p class="subtitle">涵盖三端部署、LangGraph 双轨架构、数据库 Schema、全量 RESTful API 与 SaaS 商业化引擎</p>
      </div>

      <h2 id="quickstart">快速上手</h2>
      <p>
        EchoTalk 2.0 采用前后端分离架构：后端基于 <strong>FastAPI + SQLAlchemy + LangGraph</strong>，用户客户端与官网基于 <strong>Vue 3 + Vite（桌面端支持 Electron）</strong>，运营后台基于 <strong>Vue 3 + Element Plus</strong>。
      </p>

      <h3 id="install">三端本地启动部署</h3>
      <pre><code># 1. 启动后端服务 (FastAPI on :8000)
cd backend
.venv/bin/python main.py

# 2. 启动用户客户端 (Vite on :5173)
cd frontend
npm install &amp;&amp; npm run dev

# 3. 启动运营管理后台 (Vite on :5174)
cd admin
npm install &amp;&amp; npm run dev

# 4. 启动产品官网与社区 (Vite on :5200，内置 /api 反向代理至 :8000)
cd docs
npm install &amp;&amp; npm run dev</code></pre>

      <h3 id="migrations">初始化与幂等迁移</h3>
      <p>后端启动时在 FastAPI <code>lifespan</code> 自动执行 <code>run_startup_migrations(engine)</code>，完成幂等建表、增量加列与默认种子同步：</p>
      <ul>
        <li><code>sync_seeds(db)</code>：同步内置 1v1 场景包（<code>backend/app/content/scenes/*.yaml</code>）。</li>
        <li><code>sync_builtin_avatars(db)</code>：同步内置 2D 数字人与音色预设。</li>
        <li><code>sync_builtin_listening(db)</code>：同步听力与四六级真题单元。</li>
        <li><code>ensure_saas_defaults(db)</code>：初始化 Free/Pro/Enterprise 三档套餐、默认任务与计费单价配置。</li>
      </ul>

      <h2 id="dual-track">1v1 与 1vN 双轨对话架构</h2>
      <ul>
        <li><strong>1v1 语音对话（Practice）</strong>：基于 LangGraph <code>StateGraph</code>（<code>agent → tools → finalize</code>），每轮最多 4 次模型调用与 6 次工具执行；支持 SSE 流式文本输出与 <code>_SentenceBuffer</code> 切句并发 <code>edge-tts</code> 音频推流。</li>
        <li><strong>1vN 多角色对话（Debate / Panel）</strong>：统一支持正反辩论（<code>debate</code>）与多人圆桌/群面（<code>panel</code>），通过 <code>roles_config</code>（2–4 位 AI 角色）、<code>stages_config</code> 与 <code>tools_config</code> 编排多角色轮流发言与赛后裁决。</li>
      </ul>

      <h3 id="kb">Hybrid RRF + LightRAG 双引擎知识库</h3>
      <ul>
        <li><strong>Hybrid RRF</strong>：SQLite FTS5 全文检索 + 语义向量余弦相似度融合重排，支持 <code>user / ai_only</code> 分节可见性隔离。</li>
        <li><strong>LightRAG 图谱引擎</strong>：专用后台事件循环线程异步抽取实体与关系图谱，支持 <code>asyncio.wait_for(..., timeout=90.0)</code> 超时保护与僵尸 <code>building</code> 状态自愈，管理端可动态启停后台执行。</li>
      </ul>

      <h3 id="saas">SaaS 共享额度池与盈利核算</h3>
      <p>全站 AI 消耗统一纳入 <strong>每日免费额度池（<code>daily_free_credits</code>）</strong>，用满 100% 后受用户 <code>auto_use_credits</code> 开关与后台全局开关控制扣减永久回声积分；管理端可根据可调的百万 Token 单价实时核算周期净毛利。</p>

      <h2 id="database">核心数据库表结构</h2>
      <table>
        <thead>
          <tr><th>表名</th><th>所属模块</th><th>核心字段与用途</th></tr>
        </thead>
        <tbody>
          <tr><td><code>users</code></td><td>账户与会员</td><td><code>id, username, password_hash, is_admin, plan_tier, plan_expires_at, credits_balance, auto_use_credits, checkin_streak, last_checkin_date</code></td></tr>
          <tr><td><code>scenes</code></td><td>1v1 场景包</td><td><code>id, name, category, mode, difficulty, package_json, source, status, required_tier, author_id, cover_path</code></td></tr>
          <tr><td><code>practice_sessions</code> / <code>practice_turns</code></td><td>1v1 会话</td><td><code>id, user_id, scene_id, state_json, turn_count</code>；轮次记录文本、音频路径、<code>pronunciation_score</code>、<code>grammar_correction</code></td></tr>
          <tr><td><code>debate_topics</code> / <code>debate_sessions</code> / <code>debate_turns</code></td><td>1vN 多角色</td><td><code>id, title_zh, motion_en, scene_type (debate|panel), roles_config, stages_config, tools_config, required_tier, win_rate, scores_json, verdict_json</code></td></tr>
          <tr><td><code>documents</code> / <code>chunks</code> / <code>personal_documents</code></td><td>知识库 RAG</td><td>场景与个人文档源文件、分块内容、<code>visibility</code> 及向量嵌入存储</td></tr>
          <tr><td><code>review_items</code></td><td>SM-2 复习</td><td><code>user_id, source_type, front_text, back_text, ease_factor, interval_days, repetitions, due_at</code></td></tr>
          <tr><td><code>api_token_usage</code></td><td>算力监控</td><td><code>user_id, session_id, category (chat|embedding|lightrag_llm), model, prompt_tokens, completion_tokens, total_tokens</code></td></tr>
          <tr><td><code>saas_plan_configs</code></td><td>SaaS 套餐</td><td><code>tier (free|pro|enterprise), daily_free_credits, monthly_grant_credits, max_custom_scenes, allow_zip_import, allow_zip_export, quotas_json</code></td></tr>
          <tr><td><code>user_daily_usage</code></td><td>共享额度池</td><td>按 <code>(user_id, date_str, action_key)</code> 记录当日共享池消耗与超额积分抵扣次数</td></tr>
          <tr><td><code>credit_ledger</code></td><td>积分账本</td><td><code>user_id, delta, balance_after, source_type, action_key, ref_id, remark</code></td></tr>
          <tr><td><code>credit_task_defs</code> / <code>user_task_progress</code></td><td>任务中心</td><td>日常与新手任务定义（XP + 回声积分双奖励）及用户周期完成/领奖状态</td></tr>
          <tr><td><code>saas_campaigns</code> / <code>subscription_orders</code> / <code>redeem_codes</code> / <code>saas_billing_configs</code></td><td>商业化运营</td><td>限时活动倍率/限免、模拟订阅充值订单、兑换码核销及 <code>tokens_per_credit</code> / API 单价配置</td></tr>
        </tbody>
      </table>

      <h2 id="api-core">业务 API 接口清单</h2>
      <table>
        <thead>
          <tr><th>方法与路径</th><th>权限</th><th>功能说明</th></tr>
        </thead>
        <tbody>
          <tr><td><code>POST /api/auth/register</code> · <code>/api/auth/login</code></td><td>公开</td><td>用户注册、登录签发 Bearer Token</td></tr>
          <tr><td><code>GET /api/scenes</code> · <code>GET /api/scenes/{id}</code></td><td>公开/可选</td><td>获取 1v1 场景列表（含 <code>required_tier</code>）与完整包详情</td></tr>
          <tr><td><code>POST /api/scenes</code> · <code>/from-template</code> · <code>/import</code></td><td>登录 + 套餐校验</td><td>创建/导入场景（校验数量上限与 <code>allow_zip_import</code>）</td></tr>
          <tr><td><code>GET /api/scenes/{id}/export</code></td><td>Enterprise</td><td>导出标准 ScenePackage v2 <code>.zip</code> 包</td></tr>
          <tr><td><code>POST /api/sessions</code></td><td>登录 + 等级校验</td><td>创建 1v1 练习会话（校验 <code>scene.required_tier</code>）</td></tr>
          <tr><td><code>POST /api/sessions/{id}/turns/stream</code></td><td>登录 + 额度池</td><td>提交 1v1 对话轮次（SSE 流式返回文本与 TTS 音频）</td></tr>
          <tr><td><code>GET /api/debate/topics</code> · <code>POST /api/debate/sessions</code></td><td>公开 / 登录</td><td>获取 1vN 多角色场景、创建辩论或群面委员会会话</td></tr>
          <tr><td><code>POST /api/debate/sessions/{id}/turns</code> · <code>/finish</code></td><td>登录 + 额度池</td><td>提交多角色轮次并推进阶段；结束生成胜负/录用裁决书</td></tr>
          <tr><td><code>GET /api/listening/units</code> · <code>POST /api/listening/attempts</code></td><td>公开 / 登录</td><td>获取听力/四六级单元、提交答题并触发任务进度</td></tr>
          <tr><td><code>GET /api/review</code> · <code>POST /api/review/{id}/submit</code></td><td>登录</td><td>SM-2 到期复习队列与记忆评级提交</td></tr>
          <tr><td><code>POST /api/knowledge/personal</code> · <code>GET .../lightrag</code></td><td>登录 + 套餐校验</td><td>上传个人资料（校验 <code>max_knowledge_docs</code>）与图谱检索</td></tr>
        </tbody>
      </table>

      <h2 id="api-saas">SaaS 与管理端接口清单</h2>
      <table>
        <thead>
          <tr><th>方法与路径</th><th>角色</th><th>功能说明</th></tr>
        </thead>
        <tbody>
          <tr><td><code>GET /api/saas/me</code> · <code>PATCH /api/saas/me/settings</code></td><td>用户</td><td>查询会员等级、积分余额、共享池进度百分比与自动扣积分开关</td></tr>
          <tr><td><code>GET /api/saas/plans</code></td><td>公开</td><td>获取三档套餐对比、加油包目录与当前生效的限时活动</td></tr>
          <tr><td><code>POST /api/saas/checkin</code> · <code>GET /api/saas/tasks</code> · <code>POST .../claim</code></td><td>用户</td><td>每日签到与任务领奖（同步发放回声积分与段位 XP）</td></tr>
          <tr><td><code>POST /api/saas/checkout/mock</code> · <code>POST /api/saas/redeem</code></td><td>用户</td><td>模拟收银台支付升级/充值与兑换码核销</td></tr>
          <tr><td><code>GET/PUT /api/admin/saas/plans</code> · <code>/tasks</code> · <code>/campaigns</code></td><td>管理员</td><td>热配置套餐额度池、功能积分单价、任务奖励与限时活动</td></tr>
          <tr><td><code>GET/PUT /api/admin/saas/billing-config</code></td><td>管理员</td><td>配置积分换算比例与输入/输出百万 Token 采购单价</td></tr>
          <tr><td><code>GET /api/admin/token-stats</code></td><td>管理员</td><td>聚合 Token 消耗与周期订阅收入/API 成本/净毛利核算</td></tr>
          <tr><td><code>GET/PUT /api/admin/knowledge/lightrag-config</code></td><td>管理员</td><td>实时开关 LightRAG 后台图谱执行引擎</td></tr>
        </tbody>
      </table>

      <h2 id="scene-dev">ScenePackage v2 包规范</h2>
      <p>每个标准场景包以 <code>manifest.json + scene.yaml + cover.* + knowledge/</code> 结构打包为 <code>.zip</code>：</p>
      <pre><code>echotalk_scene_demo.zip
├── manifest.json     # 包格式版本 (v2)、ID、导出元信息
├── scene.yaml        # 13 大顶层区块：meta / roles / stages / tools / guardrails / evaluation
├── cover.png         # 场景封面图
└── knowledge/        # 可选：场景参考资料（支持 [ai] / [user] 可见性标注）</code></pre>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const activeId = ref('quickstart')

function scrollTo(id) {
  activeId.value = id
  const el = document.getElementById(id)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
</script>

<style scoped>
.docs-layout {
  display: flex;
  max-width: 1260px;
  margin: 0 auto;
  padding: 96px 24px 64px;
  gap: 32px;
}
.sidebar-nav {
  width: 230px;
  flex-shrink: 0;
  position: sticky;
  top: 94px;
  align-self: flex-start;
  background: #ffffff;
  border: 1.5px solid var(--border);
  border-bottom: 4px solid var(--border-bottom);
  border-radius: 16px;
  padding: 18px 14px;
}
.nav-group { margin-bottom: 16px; }
.nav-group:last-child { margin-bottom: 0; }
.nav-group h4 {
  font-size: 11.5px;
  font-weight: 800;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  margin: 0 0 6px 10px;
}
.sidebar-nav a {
  display: block;
  padding: 7px 10px;
  border-radius: 9px;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-soft);
  transition: background 0.15s, color 0.15s;
}
.sidebar-nav a:hover { background: #f5f2ff; color: var(--primary-ink); }
.sidebar-nav a.active { background: #eee9ff; color: var(--primary-ink); font-weight: 700; }

.doc-main {
  flex: 1;
  min-width: 0;
  background: #ffffff;
  border: 1.5px solid var(--border);
  border-bottom: 4px solid var(--border-bottom);
  border-radius: 20px;
  padding: 34px 40px;
}
.doc-hero { margin-bottom: 28px; padding-bottom: 20px; border-bottom: 1.5px solid #efecf7; }
.doc-badge { display: inline-block; padding: 3px 10px; border-radius: 999px; background: #eee9ff; color: var(--primary-ink); font-size: 11.5px; font-weight: 700; margin-bottom: 10px; }
.doc-main h1 { font-size: 32px; font-weight: 900; color: var(--text); margin-bottom: 6px; }
.subtitle { font-size: 14.5px; color: var(--text-muted); }

.doc-main h2 { font-size: 22px; font-weight: 800; color: var(--text); margin: 30px 0 12px; padding-top: 8px; border-top: 1px solid #f2effa; }
.doc-main h3 { font-size: 17px; font-weight: 750; color: var(--primary-ink); margin: 20px 0 10px; }
.doc-main p { font-size: 14.5px; color: var(--text-soft); margin-bottom: 12px; }
.doc-main ul, .doc-main ol { padding-left: 20px; margin-bottom: 14px; color: var(--text-soft); font-size: 14.5px; }
.doc-main li { margin-bottom: 6px; }

.doc-main code {
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 12.5px;
  background: #f4f0ff;
  color: #6046b4;
  padding: 2px 6px;
  border-radius: 6px;
}
.doc-main pre {
  background: #1e1b2e;
  border: 1.5px solid #2e2946;
  border-radius: 14px;
  padding: 16px 18px;
  overflow-x: auto;
  margin: 14px 0 18px;
}
.doc-main pre code {
  background: transparent;
  color: #f1edff;
  padding: 0;
  font-size: 13px;
  line-height: 1.65;
}

.doc-main table {
  width: 100%;
  border-collapse: collapse;
  margin: 14px 0 18px;
  font-size: 13px;
  border: 1px solid #efecf7;
  border-radius: 12px;
  overflow: hidden;
}
.doc-main th, .doc-main td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #efecf7; vertical-align: top; }
.doc-main th { background: #faf9fd; font-weight: 750; color: var(--text); white-space: nowrap; }
.doc-main td { color: var(--text-soft); }

@media (max-width: 860px) {
  .docs-layout { flex-direction: column; padding-top: 86px; }
  .sidebar-nav { width: 100%; position: static; }
  .doc-main { padding: 24px 20px; }
}
</style>

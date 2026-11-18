<template>
  <div class="docs-layout">
    <aside class="sidebar-nav">
      <div v-for="group in nav" :key="group.id" class="nav-group">
        <button
          type="button"
          class="nav-group-btn"
          :class="{ open: openGroups[group.id], hasActive: isGroupActive(group) }"
          @click="toggleGroup(group.id)"
        >
          <span>{{ group.title }}</span>
          <span class="nav-group-meta">
            <span class="nav-count">{{ group.items.length }}</span>
            <span class="chevron" :class="{ open: openGroups[group.id] }">▾</span>
          </span>
        </button>
        <div v-show="openGroups[group.id]" class="nav-group-items">
          <a
            v-for="item in group.items"
            :key="item.id"
            :href="'#' + item.id"
            :class="{ active: activeId === item.id, sub: item.sub }"
            @click.prevent="scrollTo(item.id)"
          >{{ item.label }}</a>
        </div>
      </div>
    </aside>

    <main class="doc-main">
      <div class="doc-hero">
        <span class="doc-badge">EchoTalk 2.0 · 完整产品与开发文档</span>
        <h1>产品与开发文档</h1>
        <p class="subtitle">
          覆盖三端部署、系统架构、{{ tableCount }} 张数据库表、{{ apiCount }} 个 API 接口、1v1 场景包与 1vN 多角色场景的完整开发规范、SaaS 计量与运维排障。
          文档内容与 <code>backend/app</code> 源码逐项对照，表结构与接口清单由代码自动导出。
        </p>
        <div class="stat-row">
          <div class="stat"><b>{{ apiCount }}</b><span>API 接口</span></div>
          <div class="stat"><b>{{ tableCount }}</b><span>数据库表</span></div>
          <div class="stat"><b>13</b><span>场景包区块</span></div>
          <div class="stat"><b>2–4</b><span>多角色 AI 角色数</span></div>
        </div>
      </div>

      <!-- ============ 1. 开始使用 ============ -->
      <h2 id="overview">产品概览</h2>
      <p>
        EchoTalk 是面向英语口语与听力训练的 AI 学习产品。2.0 版把「对话」拆成两条互不干扰的主线，并用同一套场景包 / SaaS 额度体系托底：
      </p>
      <table>
        <thead><tr><th>能力</th><th>说明</th><th>主要入口</th></tr></thead>
        <tbody>
          <tr><td><strong>1v1 语音对话</strong></td><td>与单个 AI 角色按场景包（目标 / 阶段 / 工具 / 护栏）对话，支持语音输入、流式文本与分句 TTS、发音与语法评测。</td><td><code>/api/sessions</code></td></tr>
          <tr><td><strong>1vN 多角色对话</strong></td><td>正反辩论（<code>debate</code>）与多面试官圆桌/群面（<code>panel</code>），2–4 位 AI 角色轮流发言，评委实时点评并在赛后出具裁决书。</td><td><code>/api/debate</code></td></tr>
          <tr><td><strong>听力工作室</strong></td><td>日常 / 四六级 / 电台 / 演讲四频道，逐题作答、错因标签、XP 与每日目标。</td><td><code>/api/listening</code></td></tr>
          <tr><td><strong>复习计划</strong></td><td>SM-2 间隔重复，对话纠错、发音弱点、听力错题与多角色推荐表达自动入库。</td><td><code>/api/review</code></td></tr>
          <tr><td><strong>知识库</strong></td><td>场景资料与个人资料（简历 / JD）的 Hybrid RRF 检索 + LightRAG 图谱问答，分节可见性隔离。</td><td><code>/api/scenes/{id}/knowledge</code>、<code>/api/knowledge/personal</code></td></tr>
          <tr><td><strong>数字人</strong></td><td>内置 5 个 2D 角色 + 用户自建 / 市场克隆，偏好按「用户 × 场景」存储。</td><td><code>/api/avatars</code>、<code>/api/preferences/avatar</code></td></tr>
          <tr><td><strong>SaaS 与运营</strong></td><td>Free / Pro / Enterprise、每日共享额度池、回声积分、任务、限时活动、兑换码与成本毛利核算。</td><td><code>/api/saas</code>、<code>/api/admin</code></td></tr>
        </tbody>
      </table>

      <h3 id="architecture">系统架构</h3>
      <pre><code>{{ code.arch }}</code></pre>
      <table>
        <thead><tr><th>层</th><th>技术</th><th>目录</th></tr></thead>
        <tbody>
          <tr><td>后端 API</td><td>Python 3.12 · FastAPI · SQLAlchemy 2 · PyMySQL · LangGraph / LangChain（OpenAI 兼容接口）· edge-tts · LightRAG</td><td><code>backend/</code></td></tr>
          <tr><td>数据库</td><td>MySQL 8（utf8mb4；知识库使用 ngram FULLTEXT 索引）</td><td>—</td></tr>
          <tr><td>用户客户端</td><td>Vue 3 + Vite，桌面端以 Electron 打包</td><td><code>frontend/</code></td></tr>
          <tr><td>运营后台</td><td>Vue 3 + Element Plus</td><td><code>admin/</code></td></tr>
          <tr><td>产品官网 / 文档</td><td>Vue 3 + Vue Router + Vite，开发期内置 <code>/api</code> 反向代理至 :8000</td><td><code>website/</code></td></tr>
          <tr><td>外部能力</td><td>对话 LLM（OpenAI 兼容）· 腾讯云 Flash ASR · 讯飞 ISE 发音评测 · SiliconFlow bge-m3 向量 · LightRAG 抽取 LLM</td><td>环境变量配置</td></tr>
        </tbody>
      </table>

      <h3 id="quickstart">本地快速启动</h3>
      <pre><code>{{ code.quickstart }}</code></pre>
      <table>
        <thead><tr><th>服务</th><th>端口</th><th>备注</th></tr></thead>
        <tbody>
          <tr><td>后端 FastAPI</td><td>8000</td><td>交互式接口文档：<code>/docs</code>（Swagger）、<code>/redoc</code></td></tr>
          <tr><td>用户客户端</td><td>5173</td><td>与 Electron 主进程约定固定端口</td></tr>
          <tr><td>运营后台</td><td>5174</td><td>代理 <code>/api</code> → :8000</td></tr>
          <tr><td>产品官网 / 文档</td><td>5200</td><td>开发期代理 <code>/api</code> → :8000；Cloudflare Pages 部署时配置 <code>VITE_API_BASE_URL</code> 指向后端域名</td></tr>
        </tbody>
      </table>

      <h3 id="env">环境变量</h3>
      <p>优先级：真实环境变量 &gt; <code>backend/.env</code> &gt; 默认值。复制 <code>.env.example</code> 为 <code>.env</code> 后填写。</p>
      <table>
        <thead><tr><th>变量</th><th>默认值</th><th>作用</th></tr></thead>
        <tbody>
          <tr v-for="e in envVars" :key="e[0]"><td><code>{{ e[0] }}</code></td><td>{{ e[1] }}</td><td>{{ e[2] }}</td></tr>
        </tbody>
      </table>
      <p class="note">未配置的能力会显式降级而不是伪造结果：无对话模型 → <code>503 CHAT_NOT_CONFIGURED</code>；无 ASR → <code>503 ASR_NOT_CONFIGURED</code>（前端回退文字输入）；无嵌入 key → 检索退化为纯关键词（<code>mode=keyword</code>）；无 LightRAG LLM key → 图谱接口返回 400，上传不受影响。</p>

      <h3 id="migrations">初始化、迁移与种子</h3>
      <ul>
        <li><code>python init_db.py</code>：显式建表（<code>Base.metadata.create_all</code>）、迁移 <code>avatar_preferences</code> 主键为 <code>(user_id, scene_id)</code>、补 <code>users.avatar_path / is_admin</code> 列，并创建默认管理员（<code>ECHOTALK_ADMIN_USERNAME</code> / <code>ECHOTALK_ADMIN_PASSWORD</code>，默认 <code>admin</code> / <code>admin123456</code>，<strong>上线前务必修改</strong>），再同步内置场景与数字人。</li>
        <li>FastAPI <code>lifespan</code> 启动时执行 <code>run_startup_migrations(engine)</code>：幂等地为头像 / 多角色 / SaaS 相关表补列，随后依次 <code>ensure_saas_defaults</code>（三档套餐、六个任务、计费配置）、<code>sync_seeds</code>（<code>content/scenes/*.yaml</code>）、<code>sync_builtin_avatars</code>、<code>sync_builtin_listening</code>。同步失败只记 warning，不阻断启动（提示先运行 <code>init_db.py</code>）。</li>
        <li>多角色内置场景由 <code>content/debates/*.yaml</code> 加载并在 <code>ensure_debate_tables</code> 时写入 <code>debate_topics</code>。</li>
        <li>全文索引 <code>ft_chunks_text</code> / <code>ft_personal_chunks_text</code> 在首次检索时自动补建（失败则 <code>mode=none</code>）。</li>
      </ul>

      <h3 id="deploy">生产部署</h3>
      <p>推荐「Nginx(HTTPS) → uvicorn(127.0.0.1:8000, systemd, 2 workers) → MySQL(127.0.0.1)」，数据库与 API 均不对公网开放。<code>backend/deploy/</code> 提供 <code>README.md</code>（Ubuntu 逐步手册）、<code>server-init.sh</code>、<code>update.sh</code>、<code>echotalk-backend.service</code>、<code>nginx-echotalk.conf</code>。依赖以 <code>uv.lock</code> 精确安装（Python 要求 <code>&gt;=3.12,&lt;3.13</code>）。</p>
      <ul>
        <li>生产环境将 <code>ECHOTALK_API_HOST</code> 保持 <code>127.0.0.1</code>，<code>ECHOTALK_CORS_ORIGINS</code> 替换为真实网页域名（Electron <code>file://</code> 保留 <code>null</code>）。</li>
        <li>SSE 接口需关闭代理缓冲：后端已返回 <code>X-Accel-Buffering: no</code>，Nginx 对 <code>/api/</code> 不要再开启 <code>proxy_buffering</code>。</li>
        <li>探针：<code>/api/health</code> 存活，<code>/api/ready</code> 就绪（含 <code>SELECT 1</code>，失败 503）。</li>
      </ul>

      <!-- ============ 2. 通用约定 ============ -->
      <h2 id="conventions">API 通用约定</h2>
      <h3 id="auth">认证与权限</h3>
      <ul>
        <li>登录 / 注册返回 <code>access_token</code>，后续请求携带 <code>Authorization: Bearer &lt;token&gt;</code>。令牌有效期 30 天，退出登录即撤销；服务端只存 SHA-256 摘要。</li>
        <li>身份只来自令牌，接口从不接受客户端传入的 <code>user_id</code>（管理端代操作除外）。</li>
        <li>鉴权级别：<code>公开</code> 无需令牌；<code>可选</code> 游客可访问，登录后看到自己的私有内容；<code>用户</code> 必须登录；<code>管理员</code> 必须 <code>is_admin=1</code>，否则 <code>403 FORBIDDEN</code>。</li>
        <li>会员过期会在下次读取时自动回退为 <code>free</code>。</li>
      </ul>
      <h3 id="errors">错误响应</h3>
      <p>所有可预期错误统一为：</p>
      <pre><code>{{ code.error }}</code></pre>
      <p>未预期异常只返回统一提示，不暴露堆栈；每个响应带 <code>X-Request-ID</code>（可由请求头传入）便于日志追踪。</p>
      <table>
        <thead><tr><th>HTTP</th><th>code</th><th>含义</th></tr></thead>
        <tbody>
          <tr v-for="e in errorCodes" :key="e[1]"><td>{{ e[0] }}</td><td><code>{{ e[1] }}</code></td><td>{{ e[2] }}</td></tr>
        </tbody>
      </table>
      <h3 id="sse">SSE 事件（1v1 流式轮次）</h3>
      <p><code>POST /api/sessions/{session_id}/turns/stream</code> 返回 <code>text/event-stream</code>，每个事件形如 <code>event: &lt;name&gt;</code> + <code>data: &lt;json&gt;</code>：</p>
      <table>
        <thead><tr><th>事件</th><th>数据</th><th>说明</th></tr></thead>
        <tbody>
          <tr><td><code>guardrail</code></td><td><code>{tips: [...]}</code></td><td>护栏命中（关键词提示 / 词数 / 跑题），在模型回复前下发</td></tr>
          <tr><td><code>delta</code></td><td><code>{text}</code></td><td>回复文本增量</td></tr>
          <tr><td><code>audio</code></td><td><code>{index, text, audio_b64}</code></td><td>按句切分后并发合成的 MP3（base64），<code>index</code> 为播放顺序</td></tr>
          <tr><td><code>audio_error</code></td><td><code>{index, message}</code></td><td>单句合成失败，不影响文本</td></tr>
          <tr><td><code>correction</code></td><td>语法纠正对象</td><td>对话纠错 / 地道表达建议</td></tr>
          <tr><td><code>pronunciation</code></td><td>发音评测对象</td><td>发音 / 语调 / 语速 / 逐词得分（需 <code>audio_token</code>）</td></tr>
          <tr><td><code>audio_end</code></td><td><code>{}</code></td><td>音频推流结束</td></tr>
          <tr><td><code>done</code></td><td>完整回复载荷</td><td>含目标进度、阶段、状态与 <code>turn_id</code>；终态事件</td></tr>
          <tr><td><code>error</code></td><td><code>{message, code}</code></td><td>失败（如 <code>CHAT_MODEL_FAILED</code>、<code>CHAT_TOOL_LIMIT</code>）</td></tr>
        </tbody>
      </table>
      <p>幂等：<code>request_id</code>（≤64，<code>[A-Za-z0-9_-]</code>）相同的重复请求会直接回放缓存的 <code>delta → done</code>（与已保存的纠错 / 发音 / 音频），不会重复调用模型。</p>
      <h3 id="pagination">分页与上传</h3>
      <ul>
        <li>列表接口统一 <code>page</code> / <code>page_size</code> 查询参数；批量操作 <code>ids</code> 上限 200。</li>
        <li>文件上传均为 <code>multipart/form-data</code>，字段名 <code>file</code>；场景包只接受 <code>.zip</code>。</li>
        <li>CORS 仅放行 <code>GET / POST / PUT / PATCH / DELETE</code> 与 <code>Authorization / Content-Type / X-Request-ID</code> 头；暴露 <code>X-Request-ID / Content-Disposition</code>。</li>
      </ul>

      <!-- ============ 3. 系统架构 ============ -->
      <h2 id="dual-track">1v1 与 1vN 双轨对话架构</h2>
      <h3 id="track-1v1">1v1：LangGraph 状态机</h3>
      <ul>
        <li>图结构 <code>agent → tools → finalize</code>；每轮最多 <code>MAX_MODEL_CALLS=4</code> 次模型调用、<code>MAX_TOOL_CALLS=6</code> 次工具执行，超限抛 <code>CHAT_TOOL_LIMIT</code>。</li>
        <li>模型<strong>看不到</strong>用户 ID、场景 ID 或数据库连接；工具由请求级 <code>ToolRegistry</code> 注入，仅暴露场景包 <code>tools.allowed</code> 且已实现的工具。</li>
        <li>目标 / 阶段 / 结束条件由程序按表达式计算（<code>scene_runtime.advance</code>），模型不能直接改写运行时字段；状态类工具必须附带「本轮用户原话」作为 <code>evidence</code>，否则拒绝。</li>
        <li>整轮成功后才提交状态（<code>practice_sessions.version</code> 乐观并发，冲突返回 <code>SESSION_VERSION_CONFLICT</code>）；<code>trace_json</code> 保存内部工具轨迹但<strong>永不</strong>通过接口下发。</li>
        <li>流式：<code>_SentenceBuffer</code> 切句后并发调用 edge-tts，通过 SSE 推送；同轮可并行执行语法纠错与发音评测。</li>
      </ul>
      <h3 id="track-1vn">1vN：多角色编排</h3>
      <ul>
        <li>每个场景是一行 <code>debate_topics</code>，由 <code>roles_config</code>（2–4 位角色）、<code>stages_config</code>（≤6 阶段）、<code>tools_config</code> 描述，详见 <a href="#role-dev" @click.prevent="scrollTo('role-dev')">多角色场景开发</a>。</li>
        <li>用户每发言一次：服务端写入用户发言 → 选出本轮 AI 发言角色 → 调用 LLM 生成 JSON（对手发言、评委点评、分数增量、推荐表达）→ 回写阶段 / 胜率 / 四维分 → 返回 <code>new_messages</code>。</li>
      </ul>

      <h3 id="kb">Hybrid RRF + LightRAG 双引擎知识库</h3>
      <ul>
        <li><strong>分块</strong>：按 Markdown 标题分节，再切块写入 <code>chunks</code> / <code>personal_chunks</code>。标题行内 <code>[user]</code> / <code>[ai]</code>（亦可 <code>[用户]</code> / <code>[仅ai]</code>）标记该分节可见性，文件名也可声明缺省可见性。<code>ai_only</code> 分节只参与 AI 检索，不展示给学习者。</li>
        <li><strong>Hybrid RRF</strong>：关键词路用 MySQL ngram FULLTEXT（<code>MATCH … AGAINST</code>，中文友好）；向量路用 <code>BAAI/bge-m3</code>（1024 维）对查询实时嵌入并与 <code>chunk_embeddings</code> 逐块余弦；两路各召回 <code>top_k×3</code>，以 <code>score = Σ 1/(60+rank)</code> 融合。降级：无嵌入 key → <code>mode=keyword</code>；无全文索引 → <code>mode=none</code>。</li>
        <li><strong>换嵌入模型必须全量 <code>reindex</code></strong>（向量空间不兼容）。</li>
        <li><strong>LightRAG</strong>：专用后台事件循环线程异步抽取实体关系图谱，存储于 <code>ECHOTALK_LIGHTRAG_DIR</code>（默认 <code>backend/storage/lightrag</code>）；单次抽取 / 查询超时 <code>ECHOTALK_LIGHTRAG_LLM_TIMEOUT</code>（默认 120 s），僵尸 <code>building</code> 状态可自愈；管理端可通过 <code>lightrag-config</code> 动态启停。</li>
        <li>隔离：场景库按 <code>scene_id</code>，个人库按 <code>owner_id</code>；导出场景包携带资料<strong>源文件</strong>，不携带任何向量索引或数据库 dump。</li>
      </ul>

      <h3 id="saas">SaaS 共享额度池与盈利核算</h3>
      <p>所有 AI 消耗点统一走 <code>check_and_consume_quota(user, action_key)</code>，判定顺序如下：</p>
      <ol>
        <li><strong>限时活动限免</strong>：命中生效中活动的 <code>free_actions_json</code> → 直接放行（<code>mode=campaign_free</code>）。</li>
        <li><strong>共享免费池</strong>：套餐 <code>daily_free_credits</code> 为当日总点数（<code>-1</code> = 无限），每次调用消耗该功能的 <code>credit_cost</code> 点；池未满放行（<code>mode=free_quota</code>）。</li>
        <li>池满且该功能 <code>allow_overage_credits=false</code> → <code>403 PLAN_REQUIRED</code>。</li>
        <li>池满且用户关闭 <code>auto_use_credits</code> → <code>403 QUOTA_EXCEEDED</code>。</li>
        <li>否则按 <code>max(1, round(credit_cost × credit_discount_rate))</code> 扣回声积分（<code>mode=credits</code>，写入 <code>credit_ledger</code> 的 <code>overage_consume</code>）；余额不足 → <code>403 INSUFFICIENT_CREDITS</code>。</li>
      </ol>
      <p>另有三类权限闸：<code>check_tier_permission</code>（场景 / 多角色的 <code>required_tier</code>）、<code>check_creation_limit</code>（自建场景 / 多角色 / 知识库文档数量上限）、<code>check_zip_permission</code>（ZIP 导入 / 导出），失败统一 <code>403 PLAN_REQUIRED</code> 或 <code>PLAN_LIMIT_REACHED</code>。成本核算：管理端配置 <code>tokens_per_credit</code> 与输入 / 输出百万 Token 单价，<code>token-stats</code> 按 <code>api_token_usage</code> 聚合出 API 成本，对比订阅订单收入得出净毛利。详见 <a href="#saas-detail" @click.prevent="scrollTo('saas-detail')">SaaS 计量明细</a>。</p>

      <!-- ============ 4. 数据库 ============ -->
      <h2 id="database">数据库设计</h2>
      <p>
        共 <strong>{{ tableCount }}</strong> 张表（MySQL 8，utf8mb4），模型定义见 <code>backend/app/models/</code>。时间一律 UTC（<code>DATETIME</code>）。
        布尔语义的整型列取值 0/1。「键」列：<code>PK</code> 主键、<code>FK→</code> 外键、<code>UQ</code> 唯一、<code>IDX</code> 普通索引。
      </p>
      <h3 id="er">实体关系概览</h3>
      <pre><code>{{ code.er }}</code></pre>
      <h3 id="db-conventions">设计约定</h3>
      <ul>
        <li><strong>快照而非外联</strong>：<code>practice_sessions.scene_snapshot</code> 保存创建时的场景包，历史回放不受场景后续编辑 / 删除影响；<code>debate_sessions</code> 同样冗余 <code>topic_title / motion_en</code>。</li>
        <li><strong>声明存 JSON，标量做索引</strong>：<code>scenes.package_json</code> 为完整包，<code>category / mode / difficulty / source / status / required_tier</code> 为可筛选列。</li>
        <li><strong>幂等键</strong>：<code>practice_turns(session_id, request_id)</code>、<code>review_items(user_id, source_key)</code>、<code>user_daily_usage(user_id, date_str, action_key)</code>、<code>user_task_progress(user_id, task_code, period_key)</code>。</li>
        <li><strong>配置表热更新</strong>：<code>saas_plan_configs / credit_task_defs / saas_campaigns / saas_billing_configs / system_configs</code> 由管理端修改后立即生效。</li>
        <li><strong>全文索引</strong>：<code>ft_chunks_text</code>、<code>ft_personal_chunks_text</code>（ngram）由检索模块在运行时补建，不在模型元数据中。</li>
      </ul>

      <template v-for="g in dbGroups" :key="g.group">
        <h3 :id="'db-' + slug(g.group)">{{ g.group }}</h3>
        <div v-for="t in g.tables" :key="t.name" class="table-card">
          <div class="table-card-head">
            <code class="tname" :id="'tbl-' + t.name">{{ t.name }}</code>
            <span class="ttitle">{{ t.title }}</span>
          </div>
          <p class="table-about">{{ t.about }}</p>
          <p v-if="t.unique.length" class="table-about"><strong>联合唯一：</strong><code v-for="u in t.unique" :key="u">{{ u }}</code></p>
          <div class="table-wrap">
            <table class="compact">
              <thead><tr><th>字段</th><th>类型</th><th>空</th><th>默认</th><th>键</th><th>说明</th></tr></thead>
              <tbody>
                <tr v-for="c in t.cols" :key="c[0]">
                  <td><code>{{ c[0] }}</code></td><td>{{ c[1] }}</td><td>{{ c[2] }}</td><td>{{ c[3] }}</td><td class="keycell">{{ c[4] }}</td><td>{{ c[5] }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>

      <!-- ============ 5. API ============ -->
      <h2 id="api">API 接口参考</h2>
      <p>
        共 <strong>{{ apiCount }}</strong> 个接口，基础路径 <code>/api</code>。下方清单与后端路由逐条对应。鉴权列：
        <span class="tag t-public">公开</span> <span class="tag t-optional">可选</span> <span class="tag t-user">用户</span> <span class="tag t-admin">管理员</span>。
      </p>
      <div class="api-filter">
        <input v-model.trim="apiQuery" type="search" placeholder="搜索路径、说明或参数，例如 sessions、stream、quota …" />
        <span class="filter-count">匹配 {{ matchedCount }} / {{ apiCount }}</span>
      </div>

      <template v-for="g in filteredApi" :key="g.id">
        <h3 :id="'api-' + g.id">{{ g.title }}<span class="count-pill">{{ g.rows.length }}</span></h3>
        <p v-if="g.intro" class="group-intro">{{ g.intro }}</p>
        <div class="table-wrap">
          <table class="compact api-table">
            <thead><tr><th>方法与路径</th><th>鉴权</th><th>说明</th><th>参数 / 备注</th></tr></thead>
            <tbody>
              <tr v-for="r in g.rows" :key="r[0] + r[1]">
                <td class="path-cell"><span class="method" :class="'m-' + r[0].toLowerCase()">{{ r[0] }}</span><code>{{ r[1] }}</code></td>
                <td><span class="tag" :class="'t-' + r[2]">{{ authLabel[r[2]] }}</span></td>
                <td>{{ r[3] }}</td>
                <td class="params">{{ r[4] }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <p v-if="!filteredApi.length" class="note">没有匹配的接口，试试更短的关键词。</p>

      <h3 id="api-examples">调用示例</h3>
      <pre><code>{{ code.curl }}</code></pre>

      <!-- ============ 6. 1v1 场景包开发 ============ -->
      <h2 id="scene-dev">1v1 场景开发：ScenePackage v2 规范</h2>
      <p>
        场景包是一份声明式配置（<code>scene.yaml</code>），创建 / 编辑 / 导入三个入口共用同一套 Pydantic 全量校验（<code>app/scenes/schema.py</code>）。包只能<strong>引用</strong>已注册工具，不能定义实现。校验失败返回 <code>422 SCENE_INVALID_PACKAGE</code>，<code>details</code> 为字段路径级错误列表。
      </p>
      <h3 id="scene-structure">包结构与 ZIP 格式</h3>
      <pre><code>{{ code.zip }}</code></pre>
      <ul>
        <li><code>scene.yaml</code> 是唯一必需文件；<code>manifest.json</code> 存在时会校验 <code>format=echotalk-scene</code>、版本与 <code>checksums</code>（SHA-256）。</li>
        <li>资料源文件的 <code>user</code> 与 <code>ai_only</code> 都会导出（可见性是教学设计，非用户隐私）。</li>
        <li>1.0 旧包（<code>scene_config.json</code> / <code>*.index</code> FAISS）一律拒绝，提示用 2.0 导出包或模板重建。</li>
        <li>导入 ID 冲突返回 <code>409 SCENE_ID_CONFLICT</code>，需再带 <code>?resolve=overwrite|rename</code>；内置场景只读（<code>SCENE_BUILTIN_READONLY</code>），可「从模板创建」或「复制」。</li>
      </ul>

      <h3 id="scene-fields">顶层区块与字段</h3>
      <table>
        <thead><tr><th>区块</th><th>必填</th><th>字段与约束</th></tr></thead>
        <tbody>
          <tr v-for="r in sceneBlocks" :key="r[0]"><td><code>{{ r[0] }}</code></td><td>{{ r[1] }}</td><td>{{ r[2] }}</td></tr>
        </tbody>
      </table>

      <h3 id="scene-placeholders">提示词占位符</h3>
      <p><code>prompt.system</code> 与 <code>prompt.greeting</code> 中只允许两类占位符，否则校验报错：</p>
      <ul>
        <li><code>{param_key}</code>：引用 <code>prompt.params</code> 中声明的参数（可由学习者覆盖 <code>editable: true</code> 的参数）。</li>
        <li><code>{roles.&lt;role_id&gt;.&lt;field&gt;}</code>：引用角色字段，<code>field ∈ id / display_name / title / personality / voice / avatar</code>，且 <code>role_id</code> 必须存在。</li>
      </ul>

      <h3 id="scene-expr">条件表达式子语言</h3>
      <p><code>objectives[].check</code>、<code>stages[].exit_when</code>、<code>finish.when</code> 使用白名单表达式（<code>app/core/expr.py</code>），保存时会用声明的 <code>state</code> 做 dry-run 检查路径。<strong>禁止</strong>属性访问、任意函数调用与算术。</p>
      <pre><code>{{ code.expr }}</code></pre>
      <table>
        <thead><tr><th>可用元素</th><th>说明</th></tr></thead>
        <tbody>
          <tr><td><code>state.&lt;路径&gt;</code></td><td>场景状态，根键必须在 <code>state</code> 区块声明</td></tr>
          <tr><td><code>stage</code> / <code>stage_turns</code> / <code>turn_count</code></td><td>运行时保留键：当前阶段 id、阶段内轮数、总轮数（包内 <code>state</code> 不可声明同名键）</td></tr>
          <tr><td><code>tool_called('名')</code></td><td>本轮是否成功调用过某工具</td></tr>
          <tr><td><code>state_changed('路径')</code></td><td>本轮某状态键是否发生变化</td></tr>
          <tr><td><code>goals_done()</code></td><td>全部训练目标是否达成</td></tr>
          <tr><td>运算符</td><td><code>== != &gt;= &lt;= &gt; &lt; in</code>、<code>and / or / not</code>；字面量 <code>true / false / null</code>、数字、字符串</td></tr>
        </tbody>
      </table>

      <h3 id="scene-tools">工具注册表</h3>
      <p><code>tools.allowed</code> 必须 ⊆ 注册表；<code>tools.config</code> 的键必须 ⊆ <code>allowed</code>。写状态的工具只能改<strong>已声明</strong>的 <code>state</code> 键，值类型需与声明一致，且必须提供本轮原话 <code>evidence</code>。</p>
      <table>
        <thead><tr><th>工具</th><th>参数</th><th>作用 / 约束</th></tr></thead>
        <tbody>
          <tr v-for="t in sceneTools" :key="t[0]"><td><code>{{ t[0] }}</code></td><td>{{ t[1] }}</td><td>{{ t[2] }}</td></tr>
        </tbody>
      </table>
      <p class="note">注册表另含 <code>get_learning_profile</code>、<code>calculate_order</code>、<code>modify_order</code>、<code>record_feedback</code> 四个保留名：当前可通过校验，但运行时尚未向模型暴露（<code>ToolRegistry.schemas()</code> 只发布已实现工具）。</p>

      <h3 id="scene-runtime">运行时语义</h3>
      <ol>
        <li>创建会话：渲染 <code>prompt.greeting</code>、快照场景包，<code>initial_state</code> 生成 <code>scenario_state</code>（<code>state</code> 深拷贝）、首个阶段、全部目标 <code>done=false</code>。</li>
        <li>每轮：<code>agent</code> 调模型 → 执行工具 → <code>advance()</code>：求值 <code>objectives.check</code>（<strong>达成后不回退</strong>）→ 若有 <code>next_interview_stage</code> 请求或当前阶段 <code>exit_when</code> 为真则切换到下一阶段（最后一阶段不再推进）→ 求值 <code>finish.when</code>；否则 <code>turn_count ≥ finish.max_turns</code> 兜底结束（<code>finish_reason = condition_met | max_turns</code>）。</li>
        <li>结束：<code>on_finish: request_feedback</code> 触发复盘；<code>GET /api/sessions/{id}/report</code> 汇总目标完成度、发音五维、语法纠错、强弱词。</li>
        <li><code>evaluation.dimensions</code>：<code>source: state</code> 由程序按状态判定，<code>llm</code> 由模型评分；<code>weight</code> 为 (0,1] 加权。</li>
        <li><code>guardrails</code>：<code>language</code> / <code>min_words</code> / <code>keyword_tips</code>（命中 <code>match</code> 时推送气泡）/ <code>off_topic.domain_keywords</code>（未配置时自动提取 → <code>scenes.domain_keywords</code>）；动作统一为 <code>warn</code>，<code>max_warnings_per_turn</code> 限制 1–5 条。</li>
      </ol>

      <h3 id="scene-example">完整示例（精简自内置 cafe_ordering）</h3>
      <pre><code>{{ code.sceneYaml }}</code></pre>
      <h3 id="scene-checklist">开发清单</h3>
      <ol>
        <li>先 <code>POST /api/scenes/validate</code> 反复干跑，直至返回 <code>valid: true</code>。</li>
        <li>把「需要被验证的行为」写成 <code>state</code> 键 + <code>objectives.check</code>，不要靠提示词让模型自己判断完成。</li>
        <li>提示词里明确<strong>何时调用哪个工具</strong>，并对工具所需 <code>evidence</code> 给出示例触发词。</li>
        <li>涉及价格 / 时刻表等事实时放入 <code>knowledge/</code> 并要求 <code>search_knowledge</code>，参考答案类资料标 <code>ai_only</code>。</li>
        <li><code>finish.when</code> 必须可达，并配置合理的 <code>max_turns</code>（2–200，默认 30）。</li>
        <li>发布前设置 <code>required_tier</code>，上传封面，再 <code>publish</code> 到社区。</li>
      </ol>

      <!-- ============ 7. 多角色场景开发 ============ -->
      <h2 id="role-dev">多角色（1vN）场景开发</h2>
      <p>
        多角色场景分两种形态，共用同一张 <code>debate_topics</code> 表、同一套接口与发言流程，差异只在 <code>sceneType</code>：
      </p>
      <table>
        <thead><tr><th></th><th><code>debate</code> 正反辩论</th><th><code>panel</code> 群面 / 圆桌</th></tr></thead>
        <tbody>
          <tr><td>用户立场</td><td><code>user_side = pro | con</code>，创建会话时选择</td><td>恒为 <code>pro</code>，以 <code>userRoleLabel</code> 身份（如「高级工程师候选人」）参与</td></tr>
          <tr><td>默认角色</td><td>moderator（第 1 位）+ opponent + judge</td><td>多位 interviewer + 可选 judge</td></tr>
          <tr><td>默认阶段</td><td>开篇立论 → 交叉质询 → 焦点攻防 → 总结裁决</td><td>自我陈述 → 深度追问 → 压力挑战 → 委员会评估</td></tr>
          <tr><td>开场发言者</td><td>moderator</td><td>moderator，没有则取 roles[0]</td></tr>
          <tr><td>每轮 AI 发言者</td><td>固定为 opponent（无则 roles[0]）</td><td>非 judge 角色轮流发言，且不连续两次同一人</td></tr>
          <tr><td>裁决阈值</td><td><code>win_rate ≥ 50</code> 判用户胜</td><td><code>win_rate ≥ 60</code> 判通过（委员会认可度）</td></tr>
        </tbody>
      </table>

      <h3 id="role-model">场景数据模型</h3>
      <p>创建 / 更新使用 <code>DebateTopicIn</code>（<code>POST/PUT /api/debate/topics</code>），内置场景使用同构的 YAML（驼峰字段）。</p>
      <table>
        <thead><tr><th>字段</th><th>类型 / 取值</th><th>说明</th></tr></thead>
        <tbody>
          <tr v-for="f in topicFields" :key="f[0]"><td><code>{{ f[0] }}</code></td><td>{{ f[1] }}</td><td>{{ f[2] }}</td></tr>
        </tbody>
      </table>

      <h3 id="role-roles">角色（roles）</h3>
      <table>
        <thead><tr><th>字段</th><th>约束</th><th>说明</th></tr></thead>
        <tbody>
          <tr><td><code>id</code></td><td>≤32；重复自动加 <code>_序号</code></td><td>角色唯一标识，缺省 <code>role_N</code></td></tr>
          <tr><td><code>roleType</code></td><td><code>moderator | interviewer | opponent | judge</code></td><td>决定发言机制：非法值回退（panel → interviewer；debate 首位 moderator、其余 opponent）</td></tr>
          <tr><td><code>name</code></td><td>必填，≤64</td><td>展示名，同时作为 <code>debate_turns.speaker</code></td></tr>
          <tr><td><code>title</code></td><td>≤64</td><td>头衔，如「技术总监 Tech Lead」</td></tr>
          <tr><td><code>persona</code></td><td>≤800</td><td>注入 LLM 的人设 / 追问偏好，越具体越稳定</td></tr>
          <tr><td><code>voice</code></td><td>TTS 声音名</td><td>应在白名单内（默认 <code>sonia</code>）</td></tr>
          <tr><td><code>avatarId</code></td><td>数字人 ID</td><td>默认 <code>sarah_2d</code>；内置：<code>leo_2d / emily_2d / david_2d / sarah_2d / claire_2d</code></td></tr>
        </tbody>
      </table>
      <ul>
        <li>最多 <strong>4</strong> 个角色，超出被截断；没有任何有效角色时回退为「moderator Brian + opponent（来自 <code>opponentName</code> 等旧字段）+ judge Andrew」。</li>
        <li>保存时旧字段 <code>opponentName / Title / Persona / Voice / AvatarId</code> 由「首个 opponent → 首个 interviewer → roles[0]」自动派生，保证老客户端兼容。</li>
        <li><code>judge</code> 同时承担「点评」与「裁决」：其发言只在<strong>阶段切换时</strong>或<strong>最后一轮</strong>出现，且必须启用 <code>judge_score</code> 工具。</li>
      </ul>

      <h3 id="role-stages">阶段（stages）</h3>
      <ul>
        <li>最多 <strong>6</strong> 个，每项 <code>{id, label, shortTag}</code>；<code>label</code> 必填（≤48），<code>shortTag</code> 缺省取 <code>label</code> 前 2 字，<code>id</code> 缺省 <code>stage_N</code>。未配置时按场景类型使用默认四阶段。</li>
        <li>阶段由<strong>进度</strong>驱动而非模型决定：<code>progress = 已用用户轮数 / maxTurns</code>，<code>next_stage = ⌊progress × (阶段数 − 1)⌋</code>（只前进不后退）。</li>
        <li><code>maxTurns</code> 来自 <code>duration</code> 文案里的分钟数：≤ 6 → 4 轮；≤ 9 → 6 轮；其余 → 8 轮（无法解析时 6 轮）。</li>
      </ul>

      <h3 id="role-tools">工具（tools）</h3>
      <table>
        <thead><tr><th>工具 ID</th><th>启用后的行为</th></tr></thead>
        <tbody>
          <tr><td><code>judge_score</code></td><td>开启评分：每轮更新 <code>scores_json</code> 四维分与 <code>win_rate</code>，并允许评委在阶段切换 / 末轮点评；<strong>关闭则分数与胜率冻结（<code>win_delta=0</code>）、无评委点评</strong>。</td></tr>
          <tr><td><code>rebuttal_hint</code></td><td>让 LLM 同时产出「推荐高分英文表达」（<code>review_expression</code>）与中文提示，供复盘展示；亦兼容 <code>get_hint</code> 别名。</td></tr>
          <tr><td><code>search_knowledge</code></td><td>把 <code>knowledgeDocIds</code> 绑定的个人资料片段注入提示词（背景与目标表达始终注入，与该工具无关）。</td></tr>
          <tr><td><code>calculate_expression</code></td><td>允许在回应中做数字推演（如成本、占比）。</td></tr>
          <tr><td><code>add_review_task</code></td><td>把 LLM 推荐的表达写入 <code>review_items</code>（<code>source_type=debate</code>，<code>source_key</code> 形如 <code>debate:会话ID:发言ID</code>，幂等）。</td></tr>
        </tbody>
      </table>
      <p>字段缺失（<code>null</code>）时回退默认 <code>[search_knowledge, rebuttal_hint, judge_score, add_review_task]</code>；显式 <code>[]</code> 表示全部关闭。API 创建的默认值为 <code>[search_knowledge, rebuttal_hint, judge_score]</code>。</p>

      <h3 id="role-flow">一次发言的处理流程</h3>
      <pre><code>{{ code.roleFlow }}</code></pre>
      <h3 id="role-scoring">评分、胜率与裁决</h3>
      <table>
        <thead><tr><th>指标</th><th>规则</th></tr></thead>
        <tbody>
          <tr><td>四维分</td><td><code>logic</code> 逻辑 / <code>rebuttal</code> 反驳 / <code>fluency</code> 流利 / <code>presence</code> 临场；初值 0，首轮以 60 为基准；每轮增量夹在 [-5, +6]，结果夹在 [45, 98]。</td></tr>
          <tr><td>胜率 <code>win_rate</code></td><td>初值 50；每轮增量夹在 [-8, +8]，语音输入且 ≥ 6 词额外 +1；整体夹在 [20, 95]。</td></tr>
          <tr><td>连击 <code>combo_count</code></td><td>本轮增量 &lt; 0 清零，否则 +1。</td></tr>
          <tr><td>对手强度</td><td><code>supportive</code>（友好，B1–B2）/ <code>balanced</code>（专业，B2–C1）/ <code>sharp</code>（高压，C1），创建会话时选择，默认 <code>balanced</code>。</td></tr>
          <tr><td>裁决书</td><td><code>finish</code> 生成 <code>{winner, avg_score, xp_awarded, summary, strengths[], next_tip}</code>；首次结算 <strong>40 XP</strong>，重复调用不再加 XP。</td></tr>
          <tr><td>日常任务</td><td>提交发言与结束都会触发 <code>daily_debate_1</code> 进度。</td></tr>
        </tbody>
      </table>

      <h3 id="role-yaml">内置场景 YAML 示例（panel 群面）</h3>
      <pre><code>{{ code.panelYaml }}</code></pre>
      <h3 id="role-api">通过 API 创建（debate 辩论）</h3>
      <pre><code>{{ code.debateApi }}</code></pre>
      <h3 id="role-zip">导入 / 导出 ZIP 格式</h3>
      <pre><code>{{ code.debateZip }}</code></pre>
      <ul>
        <li>导入同样需要 <code>allow_zip_import</code>，导出需要 <code>allow_zip_export</code>（Enterprise）；空包 / 缺少 <code>debate.json</code> 返回 <code>EMPTY_DEBATE_PACKAGE</code> / <code>INVALID_DEBATE_PACKAGE</code>。</li>
        <li>内置场景只读（<code>DEBATE_BUILTIN_READONLY</code>），可 <code>duplicate</code> 后修改；管理员可把内置场景设为 <code>private</code> 隐藏。</li>
        <li>AI 辅助：<code>POST /api/debate/topics/generate</code>（<code>idea + sceneType</code>）产出完整草稿供编辑器回填，确认后再保存。</li>
      </ul>
      <h3 id="role-checklist">开发清单与常见陷阱</h3>
      <ol>
        <li>角色数 2–4；panel 至少 2 位非 judge 角色才会轮流提问，否则退化为在全体角色中轮换。</li>
        <li>为 judge 配置独立 <code>voice</code> 与 <code>avatarId</code>，避免与提问者撞声。</li>
        <li><code>persona</code> 写「关注点 + 追问方式 + 语气」，并提供 <code>backgroundContext</code> 与 <code>keyExpressions</code>（前 6 条注入提示词）。</li>
        <li><code>duration</code> 决定总轮数与阶段节奏，请与阶段数匹配（阶段数 ≤ maxTurns 才能每阶段至少一轮）。</li>
        <li>绑定个人资料（简历 / JD）使用 <code>knowledgeDocIds</code> + <code>search_knowledge</code>。</li>
        <li>发布前用不同对手强度各跑一遍，确认评分与裁决符合预期。</li>
      </ol>

      <!-- ============ 8. SaaS 明细 ============ -->
      <h2 id="saas-detail">SaaS 计量明细</h2>
      <h3 id="saas-actions">计量功能点（action_key）</h3>
      <table>
        <thead><tr><th>action_key</th><th>功能</th><th>模块</th><th>接入点</th></tr></thead>
        <tbody>
          <tr v-for="a in actionKeys" :key="a[0]"><td><code>{{ a[0] }}</code></td><td>{{ a[1] }}</td><td>{{ a[2] }}</td><td>{{ a[3] }}</td></tr>
        </tbody>
      </table>
      <h3 id="saas-plans">默认套餐</h3>
      <div class="table-wrap">
        <table class="compact">
          <thead><tr><th>项</th><th>Free</th><th>Pro</th><th>Enterprise</th></tr></thead>
          <tbody>
            <tr v-for="r in planRows" :key="r[0]"><td>{{ r[0] }}</td><td>{{ r[1] }}</td><td>{{ r[2] }}</td><td>{{ r[3] }}</td></tr>
          </tbody>
        </table>
      </div>
      <p class="note">以上为首次初始化的种子值，之后可在管理端 <code>PUT /api/admin/saas/plans/{tier}</code> 热更新。<code>quotas_json</code> 中每个功能点携带 <code>{daily_free, credit_cost, allow_overage_credits}</code>，其中额度池判定使用 <code>credit_cost</code>。</p>
      <h3 id="saas-credits">积分与任务</h3>
      <ul>
        <li><strong>新用户</strong>初始 100 回声积分。<strong>签到</strong>：基础 <code>10 × checkin_multiplier × 活动倍率</code>，连签 3 / 7 / 30 天额外 +15 / +40 / +150，同步发放 XP。</li>
        <li><strong>加油包</strong>：<code>pack_300</code>（300 点 / ¥6）、<code>pack_1000</code>（1000 点 / ¥18）、<code>pack_3000</code>（3000 点 / ¥48）。支付为模拟收银台（<code>payment_channel=mock_checkout</code>）。</li>
        <li><strong>任务奖励</strong>（积分）：</li>
      </ul>
      <table>
        <thead><tr><th>task_code</th><th>标题</th><th>目标</th><th>奖励</th><th>类别 / 触发</th></tr></thead>
        <tbody>
          <tr v-for="t in taskRows" :key="t[0]"><td><code>{{ t[0] }}</code></td><td>{{ t[1] }}</td><td>{{ t[2] }}</td><td>{{ t[3] }}</td><td>{{ t[4] }}</td></tr>
        </tbody>
      </table>
      <h3 id="saas-profit">成本与毛利</h3>
      <p><code>api_token_usage</code> 记录每次模型调用（<code>chat / embedding / lightrag_llm</code>）；管理端设置输入 / 输出百万 Token 单价（默认 ¥2 / ¥8）与 <code>tokens_per_credit</code>（默认 1000），<code>GET /api/admin/token-stats</code> 返回周期内 Token 聚合、订阅收入、API 成本与净毛利。</p>

      <!-- ============ 9. 数字人与语音 ============ -->
      <h2 id="avatar-voice">数字人与语音</h2>
      <h3 id="tts">TTS 声音白名单</h3>
      <table>
        <thead><tr><th>style</th><th>edge-tts voice</th><th>口音</th></tr></thead>
        <tbody>
          <tr v-for="v in voices" :key="v[0]"><td><code>{{ v[0] }}</code></td><td>{{ v[1] }}</td><td>{{ v[2] }}</td></tr>
        </tbody>
      </table>
      <p>历史别名自动归一：<code>us_female → emma</code>、<code>uk_female → sonia</code>、<code>us_male → andrew</code>。语速 <code>speech_rate ∈ [0.75, 1.25]</code>；单次合成文本 ≤ 500 字符。</p>
      <h3 id="avatar-dev">数字人开发</h3>
      <ul>
        <li>内置 5 个 2D 角色：<code>leo_2d</code>（咖啡师）、<code>emily_2d</code>（航司客服）、<code>david_2d</code>（项目经理）、<code>sarah_2d</code>（技术面试官）、<code>claire_2d</code>（售票员），每个绑定默认音色。</li>
        <li>自建角色：<code>appearance</code> JSON 描述外观（如 <code>base / skinTone / hairStyle / hairColor / eyeStyle / glasses / outfit / accessory / backdrop</code>），<code>publish</code> 后进入市场，他人可 <code>clone</code> / 取消克隆。</li>
        <li>场景包 <code>roles[].avatar / voice</code>、<code>avatar.preferred / rate</code> 仅为<strong>推荐值</strong>，无副作用；实际展示取用户 <code>avatar_preferences</code>（<code>scene_id=''</code> 为通用档）。</li>
        <li>语音输入链路：浏览器录制 16 kHz 单声道 PCM16 WAV（0.3–60 s）→ <code>POST /api/speech/transcriptions</code>（腾讯云 Flash ASR）→ 文本进入对话；发音评测（讯飞 ISE）输出发音 / 语调 / 语速 / 逐词得分。</li>
      </ul>

      <!-- ============ 10. 运维 ============ -->
      <h2 id="testing">测试与质量</h2>
      <pre><code>{{ code.tests }}</code></pre>
      <table>
        <thead><tr><th>测试</th><th>覆盖</th></tr></thead>
        <tbody>
          <tr><td><code>test_conversation / test_turn_streaming</code></td><td>LangGraph 工具循环、SSE 事件顺序与幂等</td></tr>
          <tr><td><code>test_scene_packaging_and_eval</code></td><td>场景包校验、ZIP 导入导出、评估</td></tr>
          <tr><td><code>test_retrieval / test_practice_knowledge</code></td><td>Hybrid RRF、分节可见性</td></tr>
          <tr><td><code>test_saas</code></td><td>额度池、积分扣减、权限闸</td></tr>
          <tr><td><code>test_review_sm2</code></td><td>SM-2 评级与到期时间</td></tr>
          <tr><td><code>test_tts / test_asr / test_greeting_audio / test_practice_audio</code></td><td>语音合成、识别与音频缓存</td></tr>
        </tbody>
      </table>
      <p>辅助脚本（<code>backend/scripts/</code>）：<code>smoke_scenes.py</code>（场景冒烟）、<code>import_cet_paper.py</code> / <code>curate_listening_library.py</code> / <code>fetch_and_import_resources.py</code>（听力与四六级资源导入）。</p>
      <h3 id="faq">常见问题</h3>
      <table>
        <thead><tr><th>现象</th><th>原因与处理</th></tr></thead>
        <tbody>
          <tr v-for="f in faqs" :key="f[0]"><td>{{ f[0] }}</td><td>{{ f[1] }}</td></tr>
        </tbody>
      </table>
    </main>

    <aside class="doc-aside">
      <div class="aside-card">
        <h4>快捷直达</h4>
        <div class="aside-links">
          <a href="#api" @click.prevent="scrollTo('api')">API 搜索 ({{ apiCount }})</a>
          <a href="#database" @click.prevent="scrollTo('database')">数据库 ({{ tableCount }} 表)</a>
          <a href="#scene-dev" @click.prevent="scrollTo('scene-dev')">ScenePackage v2</a>
          <a href="#role-dev" @click.prevent="scrollTo('role-dev')">1vN 多角色开发</a>
          <a href="#saas-detail" @click.prevent="scrollTo('saas-detail')">SaaS 计量明细</a>
          <a href="#faq" @click.prevent="scrollTo('faq')">常见问题排障</a>
        </div>
      </div>

      <div class="aside-card">
        <h4>关键契约速查</h4>
        <dl class="aside-kv">
          <div><dt>API 前缀</dt><dd><code>/api</code></dd></div>
          <div><dt>鉴权头</dt><dd><code>Bearer &lt;token&gt;</code></dd></div>
          <div><dt>令牌有效期</dt><dd>30 天（退出即撤销）</dd></div>
          <div><dt>1v1 轮次上限</dt><dd>4 模型 / 6 工具</dd></div>
          <div><dt>1vN 角色上限</dt><dd>2–4 AI 角色 / ≤6 阶段</dd></div>
          <div><dt>Embedding</dt><dd><code>bge-m3</code> · 1024 维</dd></div>
          <div><dt>TTS 语速</dt><dd>0.75 – 1.25（≤500 字）</dd></div>
          <div><dt>ASR 录音</dt><dd>16kHz PCM16 · 0.3–60s</dd></div>
        </dl>
      </div>

      <div class="aside-card">
        <h4>本地端口</h4>
        <dl class="aside-kv">
          <div><dt>FastAPI 后端</dt><dd><code>:8000</code></dd></div>
          <div><dt>用户客户端</dt><dd><code>:5173</code></dd></div>
          <div><dt>运营管理后台</dt><dd><code>:5174</code></dd></div>
          <div><dt>产品官网/文档</dt><dd><code>:5200</code></dd></div>
        </dl>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { apiGroups } from '../docs/api.js'
import { dbGroups } from '../docs/db.js'
import {
  code, envVars, errorCodes, sceneBlocks, sceneTools, topicFields,
  actionKeys, planRows, taskRows, voices, faqs,
} from '../docs/content.js'

const activeId = ref('overview')

function slug(text) {
  const map = {
    '账户与权限': 'account', '1v1 场景与对话': 'practice', '1vN 多角色（辩论 / 群面）': 'debate',
    '知识库（Hybrid RAG + LightRAG）': 'knowledge', '数字人与语音': 'avatar',
    '听力、复习与成长': 'learning', 'SaaS 商业化与计量': 'saas',
  }
  return map[text] || text
}

const nav = [
  { id: 'start', title: '开始使用', items: [
    { id: 'overview', label: '产品概览' },
    { id: 'architecture', label: '系统架构', sub: true },
    { id: 'quickstart', label: '本地快速启动', sub: true },
    { id: 'env', label: '环境变量', sub: true },
    { id: 'migrations', label: '初始化与迁移', sub: true },
    { id: 'deploy', label: '生产部署', sub: true },
  ] },
  { id: 'conv', title: 'API 通用约定', items: [
    { id: 'conventions', label: '约定总览' },
    { id: 'auth', label: '认证与权限', sub: true },
    { id: 'errors', label: '错误响应', sub: true },
    { id: 'sse', label: 'SSE 事件', sub: true },
    { id: 'pagination', label: '分页与上传', sub: true },
  ] },
  { id: 'arch', title: '系统架构', items: [
    { id: 'dual-track', label: '1v1 与 1vN 双轨' },
    { id: 'kb', label: 'Hybrid + LightRAG', sub: true },
    { id: 'saas', label: 'SaaS 额度池', sub: true },
  ] },
  { id: 'db', title: '数据库设计', items: [
    { id: 'database', label: '设计总览' },
    { id: 'er', label: '实体关系', sub: true },
    ...dbGroups.map((g) => ({ id: 'db-' + slug(g.group), label: g.group, sub: true })),
  ] },
  { id: 'api-ref', title: 'API 接口参考', items: [
    { id: 'api', label: '接口总览与搜索' },
    ...apiGroups.map((g) => ({ id: 'api-' + g.id, label: g.title, sub: true })),
    { id: 'api-examples', label: '调用示例', sub: true },
  ] },
  { id: 'scene1v1', title: '1v1 场景开发', items: [
    { id: 'scene-dev', label: 'ScenePackage v2 规范' },
    { id: 'scene-fields', label: '区块与字段', sub: true },
    { id: 'scene-expr', label: '条件表达式', sub: true },
    { id: 'scene-tools', label: '工具注册表', sub: true },
    { id: 'scene-runtime', label: '运行时语义', sub: true },
    { id: 'scene-example', label: '完整示例', sub: true },
  ] },
  { id: 'role1vn', title: '1vN 多角色开发', items: [
    { id: 'role-dev', label: '多角色形态对比' },
    { id: 'role-model', label: '场景数据模型', sub: true },
    { id: 'role-roles', label: '角色 roles', sub: true },
    { id: 'role-stages', label: '阶段 stages', sub: true },
    { id: 'role-tools', label: '工具 tools', sub: true },
    { id: 'role-flow', label: '发言处理流程', sub: true },
    { id: 'role-scoring', label: '评分与裁决', sub: true },
    { id: 'role-yaml', label: 'YAML / API / ZIP 示例', sub: true },
  ] },
  { id: 'ops', title: '运营与扩展', items: [
    { id: 'saas-detail', label: 'SaaS 计量明细' },
    { id: 'avatar-voice', label: '数字人与语音' },
    { id: 'testing', label: '测试与常见问题' },
  ] },
]

const openGroups = reactive({
  start: true,
  conv: false,
  arch: false,
  db: false,
  'api-ref': false,
  scene1v1: false,
  role1vn: false,
  ops: false,
})

function toggleGroup(id) {
  openGroups[id] = !openGroups[id]
}

function isGroupActive(group) {
  return group.items.some((item) => item.id === activeId.value)
}

watch(activeId, (id) => {
  const owner = nav.find((g) => g.items.some((item) => item.id === id))
  if (owner) openGroups[owner.id] = true
})

const authLabel = { public: '公开', optional: '可选', user: '用户', admin: '管理员' }
const tableCount = dbGroups.reduce((n, g) => n + g.tables.length, 0)
const apiCount = apiGroups.reduce((n, g) => n + g.rows.length, 0)

const apiQuery = ref('')
const filteredApi = computed(() => {
  const q = apiQuery.value.toLowerCase()
  if (!q) return apiGroups
  return apiGroups
    .map((g) => ({
      ...g,
      rows: g.rows.filter((r) => (r[0] + ' ' + r[1] + ' ' + authLabel[r[2]] + ' ' + r[3] + ' ' + r[4]).toLowerCase().includes(q)),
    }))
    .filter((g) => g.rows.length)
})
const matchedCount = computed(() => filteredApi.value.reduce((n, g) => n + g.rows.length, 0))

function scrollTo(id) {
  activeId.value = id
  const el = document.getElementById(id)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

let observer = null
onMounted(() => {
  const ids = new Set(nav.flatMap((g) => g.items.map((i) => i.id)))
  observer = new IntersectionObserver(
    (entries) => {
      const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
      if (visible.length) activeId.value = visible[0].target.id
    },
    { rootMargin: '-90px 0px -70% 0px', threshold: 0 },
  )
  document.querySelectorAll('.doc-main h2[id], .doc-main h3[id]').forEach((el) => {
    if (ids.has(el.id)) observer.observe(el)
  })
})
onBeforeUnmount(() => observer && observer.disconnect())
</script>

<style scoped>
.docs-layout {
  display: flex;
  width: 100%;
  max-width: 1760px;
  margin: 0 auto;
  padding: 16px 42px 64px;
  gap: 26px;
}
.sidebar-nav {
  width: 252px;
  flex-shrink: 0;
  position: sticky;
  top: 84px;
  align-self: flex-start;
  max-height: calc(100vh - 100px);
  overflow-y: auto;
  background: #ffffff;
  border: 1.5px solid var(--border);
  border-bottom: 4px solid var(--border-bottom);
  border-radius: 16px;
  padding: 16px 14px;
}
.doc-aside {
  width: 248px;
  flex-shrink: 0;
  position: sticky;
  top: 84px;
  align-self: flex-start;
  max-height: calc(100vh - 100px);
  overflow-y: auto;
  padding-right: 2px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.aside-card {
  background: #ffffff;
  border: 1.5px solid var(--border);
  border-bottom: 4px solid var(--border-bottom);
  border-radius: 16px;
  padding: 16px;
}
.aside-card h4 {
  font-size: 11.5px;
  font-weight: 800;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  margin-bottom: 10px;
}
.aside-links { display: flex; flex-direction: column; gap: 6px; }
.aside-links a {
  display: block;
  padding: 7px 10px;
  border-radius: 9px;
  background: #faf9fd;
  border: 1px solid #efecf7;
  font-size: 13px;
  font-weight: 650;
  color: var(--primary-ink);
  transition: background 0.15s, border-color 0.15s;
}
.aside-links a:hover { background: #eee9ff; border-color: #dcd3f5; }
.aside-kv { display: flex; flex-direction: column; gap: 8px; }
.aside-kv > div {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
  font-size: 12.5px;
  padding-bottom: 6px;
  border-bottom: 1px dashed #efecf7;
}
.aside-kv > div:last-child { border-bottom: none; padding-bottom: 0; }
.aside-kv dt { color: var(--text-muted); font-weight: 600; white-space: nowrap; }
.aside-kv dd { color: var(--text); font-weight: 700; text-align: right; }
.aside-kv code {
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 11.5px;
  background: #f4f0ff;
  color: #6046b4;
  padding: 1px 5px;
  border-radius: 5px;
}
.nav-group { margin-bottom: 6px; }
.nav-group:last-child { margin-bottom: 0; }
.nav-group-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 10px;
  border: none;
  border-radius: 9px;
  background: transparent;
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 800;
  color: var(--text-soft);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.nav-group-btn:hover { background: #f5f2ff; color: var(--primary-ink); }
.nav-group-btn.hasActive { color: var(--primary-ink); }
.nav-group-meta { display: inline-flex; align-items: center; gap: 6px; }
.nav-count {
  font-size: 10.5px;
  font-weight: 700;
  color: var(--text-dim);
  background: #f4f1fb;
  padding: 1px 6px;
  border-radius: 999px;
}
.chevron {
  display: inline-block;
  font-size: 11px;
  color: var(--text-dim);
  transform: rotate(-90deg);
  transition: transform 0.18s ease;
}
.chevron.open { transform: rotate(0deg); }
.nav-group-items { padding: 3px 0 6px; }
.sidebar-nav a {
  display: block;
  padding: 5.5px 10px 5.5px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-soft);
  transition: background 0.15s, color 0.15s;
}
.sidebar-nav a.sub {
  padding-left: 22px;
  font-size: 12.5px;
  color: var(--text-muted);
  position: relative;
}
.sidebar-nav a.sub::before {
  content: '';
  position: absolute;
  left: 12px;
  top: 50%;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #d7cff0;
  transform: translateY(-50%);
}
.sidebar-nav a.sub.active::before { background: var(--primary); }
.sidebar-nav a:hover { background: #f5f2ff; color: var(--primary-ink); }
.sidebar-nav a.active { background: #eee9ff; color: var(--primary-ink); font-weight: 700; }

.doc-main {
  flex: 1;
  min-width: 0;
  background: #ffffff;
  border: 1.5px solid var(--border);
  border-bottom: 4px solid var(--border-bottom);
  border-radius: 20px;
  padding: 24px 36px 34px;
}
.doc-hero { margin-bottom: 22px; padding-bottom: 16px; border-bottom: 1.5px solid #efecf7; }
.doc-badge { display: inline-block; padding: 3px 10px; border-radius: 999px; background: #eee9ff; color: var(--primary-ink); font-size: 11.5px; font-weight: 700; margin-bottom: 10px; }
.doc-main h1 { font-size: 32px; font-weight: 900; color: var(--text); margin-bottom: 6px; }
.subtitle { font-size: 14.5px; color: var(--text-muted); line-height: 1.7; }
.stat-row { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 16px; }
.stat {
  flex: 1; min-width: 120px; padding: 12px 14px;
  border: 1px solid #efecf7; border-radius: 11px; background: #faf9fd;
  display: flex; flex-direction: column; gap: 2px;
}
.stat b { font-size: 24px; font-weight: 900; color: #6046b4; }
.stat span { font-size: 12px; color: var(--text-dim); font-weight: 600; }

.doc-main h2 { font-size: 22px; font-weight: 800; color: var(--text); margin: 34px 0 12px; padding-top: 10px; border-top: 1px solid #f2effa; scroll-margin-top: 90px; }
.doc-main h3 { font-size: 17px; font-weight: 750; color: var(--primary-ink); margin: 24px 0 10px; scroll-margin-top: 90px; display: flex; align-items: center; gap: 8px; }
.doc-main p { font-size: 14.5px; color: var(--text-soft); margin-bottom: 12px; line-height: 1.75; }
.doc-main ul, .doc-main ol { padding-left: 20px; margin-bottom: 14px; color: var(--text-soft); font-size: 14.5px; line-height: 1.75; }
.doc-main li { margin-bottom: 6px; }
.doc-main a { color: var(--primary-ink); font-weight: 650; }

.doc-main code {
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 12.5px;
  background: #f4f0ff;
  color: #6046b4;
  padding: 2px 6px;
  border-radius: 6px;
  word-break: break-word;
}
.doc-main pre {
  background: #1e1b2e;
  border: 1.5px solid #2e2946;
  border-radius: 14px;
  padding: 16px 18px;
  overflow-x: auto;
  margin: 14px 0 18px;
}
.doc-main pre code { background: transparent; color: #f1edff; padding: 0; font-size: 12.8px; line-height: 1.65; white-space: pre; word-break: normal; }

.doc-main table {
  width: 100%;
  border-collapse: collapse;
  margin: 14px 0 18px;
  font-size: 13px;
  border: 1px solid #efecf7;
}
.doc-main th, .doc-main td { padding: 9px 12px; text-align: left; border-bottom: 1px solid #efecf7; vertical-align: top; line-height: 1.6; }
.doc-main th { background: #faf9fd; font-weight: 750; color: var(--text); white-space: nowrap; }
.doc-main td { color: var(--text-soft); }
.doc-main table.compact { font-size: 12.5px; margin: 8px 0 14px; }
.doc-main table.compact th, .doc-main table.compact td { padding: 7px 10px; }
.table-wrap { overflow-x: auto; border-radius: 12px; }
.keycell { white-space: nowrap; color: #6046b4; font-weight: 600; }

.table-card {
  border: 1px solid #efecf7; border-radius: 12px; padding: 12px 14px 4px;
  margin: 12px 0; background: #fff;
}
.table-card-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 4px; }
.table-card-head .tname { font-size: 14px; font-weight: 800; padding: 3px 9px; scroll-margin-top: 90px; }
.ttitle { font-size: 13.5px; font-weight: 700; color: var(--text); }
.doc-main .table-about { font-size: 13px; margin-bottom: 6px; color: var(--text-muted); }
.table-about code { margin-right: 6px; }

.doc-main .note { padding: 10px 14px; background: #f7f5ff; border: 1px solid #e7e1fa; border-radius: 11px; font-size: 13.5px; }
.doc-main .note.warn { background: #fff3ea; border-color: #f6d9bf; color: #8a4a1b; }
.doc-main .note.warn code { background: #ffe6d1; color: #8a4a1b; }

.api-filter { display: flex; align-items: center; gap: 12px; margin: 10px 0 6px; position: sticky; top: 76px; z-index: 5; background: #fff; padding: 6px 0; }
.api-filter input {
  flex: 1; padding: 9px 14px; font-size: 14px; color: var(--text);
  border: 1.5px solid #e6e1f2; border-bottom: 3px solid #ddd6ec; border-radius: 10px; outline: none; background: #fff;
}
.api-filter input:focus { border-color: #8b73dd; }
.filter-count { font-size: 12.5px; color: var(--text-dim); font-weight: 700; white-space: nowrap; }
.count-pill { font-size: 11px; font-weight: 800; background: #eee9ff; color: #6046b4; padding: 2px 8px; border-radius: 999px; }
.doc-main .group-intro { font-size: 13.5px; color: var(--text-muted); }

.api-table td.path-cell { white-space: nowrap; }
.doc-main .api-table td.path-cell code { background: transparent; color: #35304e; padding: 0 0 0 6px; font-size: 12.3px; }
.api-table td.params { color: var(--text-muted); font-size: 12px; min-width: 200px; }
.method { display: inline-block; min-width: 50px; text-align: center; font-size: 10.5px; font-weight: 800; padding: 2px 6px; border-radius: 6px; font-family: 'SFMono-Regular', Consolas, monospace; }
.m-get { background: #eaf7f0; color: #2a8c5f; }
.m-post { background: #f4f0ff; color: #6046b4; }
.m-put { background: #fff3ea; color: #c46a24; }
.m-patch { background: #fff3ea; color: #c46a24; }
.m-delete { background: #fdece8; color: #b84a39; }
.tag { display: inline-block; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 999px; white-space: nowrap; }
.t-public { background: #eaf7f0; color: #2a8c5f; }
.t-optional { background: #eef3fb; color: #3d6aa8; }
.t-user { background: #f4f0ff; color: #6046b4; }
.t-admin { background: #fdece8; color: #b84a39; }

@media (max-width: 1360px) {
  .doc-aside { display: none; }
}
@media (max-width: 960px) {
  .docs-layout { flex-direction: column; padding: 12px 16px 48px; }
  .sidebar-nav { width: 100%; position: static; max-height: 260px; }
  .doc-main { padding: 24px 18px; }
}
</style>

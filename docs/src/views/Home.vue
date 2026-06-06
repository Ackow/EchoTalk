<template>
  <div class="home-page">
    <!-- Hero -->
    <section class="hero" id="top">
      <div class="hero-content">
        <div class="hero-badge">🚀 AI 驱动 · 场景化学习</div>
        <h1><span class="gradient-text">EchoTalk</span><br />让英语口语脱口而出</h1>
        <p>AI 真人对练、沉浸式场景模拟、智能语音评测，从面试到点餐，覆盖高频生活场景，让你在家也能开口说地道英语。</p>
        <div class="hero-actions">
          <a href="#download" class="btn-primary">⬇ 免费下载</a>
          <router-link to="/docs" class="btn-secondary">📖 查看文档</router-link>
        </div>
        <div class="hero-stats">
          <div class="hero-stat"><div class="num">3+</div><div class="label">内置场景</div></div>
          <div class="hero-stat"><div class="num">RAG</div><div class="label">知识库增强</div></div>
          <div class="hero-stat"><div class="num">TTS</div><div class="label">真人级语音</div></div>
          <div class="hero-stat"><div class="num">∞</div><div class="label">自由扩展</div></div>
        </div>
      </div>
    </section>

    <!-- Features -->
    <section class="section" id="features">
      <div class="section-header">
        <div class="tag">Features</div>
        <h2>核心能力</h2>
        <p>从语音识别到智能对话，全链路 AI 赋能你的口语练习</p>
      </div>
      <div class="features-grid">
        <div class="feature-card" v-for="f in features" :key="f.title">
          <div class="feature-icon" :class="f.color">{{ f.icon }}</div>
          <h3>{{ f.title }}</h3>
          <p>{{ f.desc }}</p>
        </div>
      </div>
    </section>

    <!-- Scenarios -->
    <section class="section" id="scenarios">
      <div class="section-header">
        <div class="tag">Scenarios</div>
        <h2>丰富场景，覆盖高频生活</h2>
        <p>从求职面试到日常出行，每个场景都经过精心设计</p>
      </div>
      <div class="scenarios-grid">
        <div class="scenario-card" v-for="s in scenarios" :key="s.title">
          <div class="emoji">{{ s.icon }}</div>
          <h3>{{ s.title }}</h3>
          <p>{{ s.desc }}</p>
          <span class="tag-badge">{{ s.tag }}</span>
        </div>
      </div>
    </section>

    <!-- Download -->
    <section class="download-section" id="download">
      <div class="inner">
        <h2>下载 EchoTalk</h2>
        <p>支持 Windows 桌面客户端，安装即用，本地运行安全放心</p>
        <div class="download-cards">
          <a class="dl-card" href="../frontend/dist_electron/EchoTalk%20Setup%201.0.0.exe">
            <span class="dl-icon">🪟</span>
            <div class="dl-info"><div class="os">Windows 客户端</div><div class="ver">v1.0.0 · 安装包</div></div>
          </a>
          <router-link class="dl-card" to="/docs#install">
            <span class="dl-icon">📖</span>
            <div class="dl-info"><div class="os">安装指南</div><div class="ver">查看详细安装步骤</div></div>
          </router-link>
        </div>
      </div>
    </section>

    <!-- Docs Preview -->
    <section class="section" id="docs">
      <div class="section-header">
        <div class="tag">Documentation</div>
        <h2>产品文档</h2>
        <p>从快速上手到深入开发，全面的文档助你高效使用</p>
      </div>
      <div class="docs-grid">
        <div class="doc-card" v-for="d in docItems" :key="d.title">
          <div class="doc-icon">{{ d.icon }}</div>
          <h3>{{ d.title }}</h3>
          <p>{{ d.desc }}</p>
          <router-link class="doc-link" :to="d.link">阅读文档 →</router-link>
        </div>
      </div>
    </section>

    <!-- Community -->
    <section class="section" id="community">
      <div class="community-banner">
        <div class="cb-text">
          <h3>🌍 场景包社区</h3>
          <p>发现社区贡献的场景包，从旅行对话到行业英语，下载导入即可开始练习。你也可以编写并分享自己的场景包，帮助更多人学好英语。</p>
          <div class="cb-actions">
            <router-link to="/community" class="btn-primary">浏览场景包 →</router-link>
            <router-link to="/docs#scene-dev" class="btn-secondary">发布场景包</router-link>
          </div>
        </div>
        <div class="cb-visual">📦</div>
      </div>
    </section>
  </div>
</template>
<script setup>
const features = [
  { icon: '🗣️', color: 'purple', title: 'AI 真人对练', desc: '基于大语言模型的智能对话系统，支持多轮对话、上下文理解、实时纠错，让你仿佛在和真人对话。' },
  { icon: '🎭', color: 'blue', title: '沉浸式场景', desc: '面试模拟、商务会议、餐厅点餐……精心设计的场景脚本配合 AI 角色扮演，让练习身临其境。' },
  { icon: '🎵', color: 'green', title: '语音识别 & 合成', desc: '集成 STT 语音转文字与 TTS 语音合成，支持边听边说，训练你的听力和发音。' },
  { icon: '📚', color: 'amber', title: 'RAG 知识库', desc: '上传学习资料构建专属知识库，AI 回答基于你的内容生成，精准练习特定领域词汇与表达。' },
  { icon: '📊', color: 'pink', title: '成长分析', desc: '自动记录每次练习数据，可视化展示流利度、词汇量、语法准确率等维度的成长曲线。' },
  { icon: '⏪', color: 'cyan', title: '历史回放', desc: '完整保存对话记录与语音，支持随时回放复盘，找到薄弱环节反复练习。' },
]
const scenarios = [
  { icon: '💼', title: '求职面试', desc: '模拟真实面试流程，AI 扮演面试官提问，训练自我介绍、项目阐述与压力回答。', tag: 'Interview' },
  { icon: '🏢', title: '商务会议', desc: '模拟工作会议场景，练习发言、讨论、汇报等职场英语表达。', tag: 'Meeting' },
  { icon: '🍽️', title: '餐厅点餐', desc: '模拟海外餐厅点餐全流程，从入座、看菜单到结账，实用且有趣。', tag: 'Ordering' },
  { icon: '➕', title: '自定义场景', desc: '通过场景包社区下载或自行创建场景，支持自由扩展练习内容。', tag: 'Community' },
]
const docItems = [
  { icon: '🚀', title: '快速上手', desc: '安装、注册、开始你的第一堂口语课，5 分钟入门。', link: '/docs#quickstart' },
  { icon: '📖', title: '使用指南', desc: '场景选择、知识库配置、成长分析等核心功能详解。', link: '/docs#guide' },
  { icon: '🪟', title: '场景开发', desc: '了解场景插件体系，学习如何编写并发布自定义场景包。', link: '/docs#scene-dev' },
  { icon: '🔧', title: 'API 参考', desc: '后端 REST API 接口文档，方便二次开发与集成。', link: '/docs#api' },
]
</script>
<style scoped>
.hero { position: relative; min-height: 100vh; display: flex; align-items: center; justify-content: center; text-align: center; padding: 120px 24px 80px; }
.hero::before { content: ''; position: absolute; inset: 0; pointer-events: none; background: radial-gradient(ellipse 70% 50% at 50% 35%, rgba(99,102,241,0.1) 0%, transparent 70%), radial-gradient(ellipse 50% 60% at 75% 80%, rgba(59,130,246,0.06) 0%, transparent 60%); }
.hero-content { position: relative; max-width: 720px; }
.hero-badge { display: inline-flex; align-items: center; gap: 8px; padding: 8px 20px; border-radius: 99px; margin-bottom: 28px; background: rgba(99,102,241,0.1); border: 1px solid rgba(99,102,241,0.2); font-size: 0.95rem; font-weight: 600; color: var(--primary); }
.hero h1 { font-size: clamp(3.2rem, 6vw, 4.8rem); font-weight: 900; line-height: 1.15; margin-bottom: 20px; }
.hero p { font-size: 1.3rem; color: var(--text-muted); max-width: 600px; margin: 0 auto 36px; line-height: 1.8; }
.hero-actions { display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; }
.hero-stats { display: flex; gap: 56px; justify-content: center; margin-top: 56px; padding-top: 36px; border-top: 1px solid var(--border); flex-wrap: wrap; }
.hero-stat .num { font-size: 2.4rem; font-weight: 800; color: var(--primary); }
.hero-stat .label { font-size: 0.95rem; color: var(--text-dim); margin-top: 4px; }
.section { padding: 100px 24px; max-width: 1200px; margin: 0 auto; }
.section-header { text-align: center; margin-bottom: 60px; }
.section-header .tag { display: inline-block; padding: 5px 16px; border-radius: 99px; margin-bottom: 16px; background: rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.15); font-size: 0.85rem; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.1em; }
.section-header h2 { font-size: clamp(2rem, 4vw, 2.8rem); font-weight: 800; margin-bottom: 14px; }
.section-header p { font-size: 1.15rem; color: var(--text-muted); max-width: 600px; margin: 0 auto; }
.features-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 24px; }
.feature-card { padding: 36px 30px; border-radius: var(--radius); background: var(--bg-card); border: 1px solid var(--border); transition: transform 0.2s, background 0.2s, border-color 0.2s; text-align: center; }
.feature-card:hover { transform: translateY(-4px); background: var(--bg-card-hover); border-color: rgba(99,102,241,0.15); }
.feature-icon { width: 56px; height: 56px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 1.7rem; margin: 0 auto 20px; }
.feature-icon.purple { background: rgba(99,102,241,0.12); }
.feature-icon.blue   { background: rgba(59,130,246,0.12); }
.feature-icon.green  { background: rgba(16,185,129,0.12); }
.feature-icon.amber  { background: rgba(245,158,11,0.12); }
.feature-icon.pink   { background: rgba(236,72,153,0.12); }
.feature-icon.cyan   { background: rgba(6,182,212,0.12); }
.feature-card h3 { font-size: 1.2rem; font-weight: 700; margin-bottom: 10px; }
.feature-card p { font-size: 1rem; color: var(--text-muted); line-height: 1.7; }
.scenarios-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; }
.scenario-card { padding: 32px 28px; border-radius: var(--radius); background: var(--bg-card); border: 1px solid var(--border); transition: transform 0.2s, border-color 0.2s; display: flex; flex-direction: column; text-align: center; align-items: center; }
.scenario-card:hover { transform: translateY(-3px); border-color: rgba(99,102,241,0.2); }
.scenario-card .emoji { font-size: 2.6rem; margin-bottom: 18px; }
.scenario-card h3 { font-size: 1.15rem; font-weight: 700; margin-bottom: 8px; }
.scenario-card p { font-size: 0.95rem; color: var(--text-muted); line-height: 1.65; flex: 1; }
.scenario-card .tag-badge { display: inline-block; margin-top: auto; padding: 4px 12px; border-radius: 6px; font-size: 0.8rem; font-weight: 600; background: rgba(99,102,241,0.1); color: var(--primary); }
.download-section { text-align: center; padding: 100px 24px; background: linear-gradient(180deg, transparent, rgba(99,102,241,0.04) 50%, transparent); }
.download-section .inner { max-width: 700px; margin: 0 auto; }
.download-section h2 { font-size: clamp(2.2rem, 4.5vw, 3rem); font-weight: 800; margin-bottom: 16px; }
.download-section p { font-size: 1.15rem; color: var(--text-muted); margin-bottom: 36px; }
.download-cards { display: flex; gap: 20px; justify-content: center; flex-wrap: wrap; }
.dl-card { display: flex; align-items: center; gap: 16px; padding: 24px 32px; border-radius: var(--radius); background: var(--bg-card); border: 1px solid var(--border); cursor: pointer; transition: transform 0.15s, border-color 0.2s; min-width: 240px; }
.dl-card:hover { transform: translateY(-2px); border-color: var(--primary); background: var(--bg-card-hover); }
.dl-card .dl-icon { font-size: 2.2rem; }
.dl-card .dl-info .os { font-weight: 700; font-size: 1.05rem; text-align: left; }
.dl-card .dl-info .ver { font-size: 0.88rem; color: var(--text-dim); margin-top: 2px; text-align: left; }
.docs-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
.doc-card { padding: 32px; border-radius: var(--radius); background: var(--bg-card); border: 1px solid var(--border); transition: transform 0.2s, border-color 0.2s; display: flex; flex-direction: column; text-align: center; align-items: center; }
.doc-card:hover { transform: translateY(-3px); border-color: rgba(99,102,241,0.2); }
.doc-card .doc-icon { font-size: 2rem; margin-bottom: 18px; }
.doc-card h3 { font-size: 1.15rem; font-weight: 700; margin-bottom: 10px; }
.doc-card p { font-size: 0.95rem; color: var(--text-muted); line-height: 1.6; margin-bottom: 16px; flex: 1; }
.doc-card .doc-link { font-size: 0.95rem; font-weight: 600; color: var(--primary); display: inline-flex; align-items: center; gap: 6px; margin-top: auto; }
.doc-card .doc-link:hover { text-decoration: underline; }
.community-banner { border-radius: var(--radius); padding: 64px 52px; background: linear-gradient(135deg, rgba(99,102,241,0.1) 0%, rgba(59,130,246,0.06) 100%); border: 1px solid rgba(99,102,241,0.15); display: flex; align-items: center; gap: 48px; flex-wrap: wrap; }
.community-banner .cb-text { flex: 1; min-width: 280px; }
.community-banner h3 { font-size: 1.8rem; font-weight: 800; margin-bottom: 14px; }
.community-banner p { font-size: 1.05rem; color: var(--text-muted); line-height: 1.7; margin-bottom: 24px; }
.community-banner .cb-actions { display: flex; gap: 12px; flex-wrap: wrap; }
.community-banner .cb-visual { flex-shrink: 0; font-size: 5rem; opacity: 0.7; }
@media (max-width: 768px) { .hero { padding: 100px 16px 60px; } .hero-stats { gap: 28px; } .features-grid, .docs-grid { grid-template-columns: 1fr; } .community-banner { padding: 36px 24px; } }
</style>
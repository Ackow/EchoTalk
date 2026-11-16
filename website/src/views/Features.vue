<template>
  <div class="features-page">
    <section class="page-head">
      <span class="pill">Core Capabilities &amp; Scenarios</span>
      <h1>全链路 AI 口语与听力训练引擎</h1>
      <p>从低延迟语音交互、多角色群面协同到知识图谱检索与遗忘曲线复习，每一项能力都为真实开口而设计。</p>
    </section>

    <section class="cap-grid">
      <div v-for="c in capabilities" :key="c.title" class="tactile-card cap-card">
        <span class="cap-badge" :class="c.tone">{{ c.code }}</span>
        <h3>{{ c.title }}</h3>
        <p>{{ c.desc }}</p>
        <ul class="cap-points">
          <li v-for="pt in c.points" :key="pt">{{ pt }}</li>
        </ul>
      </div>
    </section>

    <section class="gallery-section">
      <div class="section-head">
        <h2>官方内置场景画廊</h2>
        <p>覆盖 1v1 日常情景、大厂技术面试、1vN 终面委员会与正反辩论对抗</p>
      </div>
      <div class="gallery-grid">
        <div v-for="s in gallery" :key="s.title" class="tactile-card gallery-card">
          <div class="cover-wrap">
            <img :src="s.cover" :alt="s.title" />
            <span class="mode-tag" :class="s.tone">{{ s.mode }}</span>
          </div>
          <div class="gallery-body">
            <h3>{{ s.title }}</h3>
            <p>{{ s.desc }}</p>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
const capabilities = [
  {
    code: '1v1 Practice',
    tone: 'purple',
    title: '1v1 沉浸式语音对话',
    desc: '基于 LangGraph StateGraph 编排工具调用与目标达成状态。',
    points: [
      'SSE 流式文本 + 切句并发 edge-tts 播报',
      '浏览器 AudioWorklet 录音与 ASR 识别确认',
      '讯飞 ISE 逐词发音评分与语法地道度纠错',
    ],
  },
  {
    code: '1vN Debate & Panel',
    tone: 'amber',
    title: '1vN 多角色辩论与群面委员会',
    desc: '支持正反辩论对抗（debate）与多面试官圆桌（panel）双模式。',
    points: [
      '自定义 2–4 位 AI 角色阵容、音色与人设',
      '按阶段轮流追问、事实核查与实时胜率/认可度',
      '赛后生成完整胜负裁决书或委员会录用评估',
    ],
  },
  {
    code: 'Listening Studio',
    tone: 'mint',
    title: '听力与四六级工作室',
    desc: '专项提升连读、弱读与长难句听辨能力。',
    points: [
      '精听 / 盲听 / 词块拼句 / 听写填空 / 跟读模仿',
      '内置 CET-4 / CET-6 真题素材与语速调节',
      '划词 AI 助教解析与错因标签自动统计',
    ],
  },
  {
    code: 'Dual RAG',
    tone: 'purple',
    title: 'Hybrid RRF + LightRAG 双引擎知识库',
    desc: '让 AI 对话伙伴真正读懂你的简历、题库或企业产品白皮书。',
    points: [
      'SQLite FTS5 全文 + 语义向量 + RRF 融合重排',
      'LightRAG 后台异步实体抽取与力导向关系图谱',
      '支持 user / ai_only 可见性隔离与管理端后台开关',
    ],
  },
  {
    code: 'SM-2 Review',
    tone: 'mint',
    title: 'SM-2 间隔重复复习计划',
    desc: '把对话中的低分词与语法错误转化为长期记忆。',
    points: [
      '自动扫描历史会话沉淀待复习表达卡片',
      'Again / Hard / Good / Easy 动态调节间隔天数',
      '联动任务中心每日打卡领取 XP 与回声积分',
    ],
  },
  {
    code: '2D Avatar',
    tone: 'amber',
    title: '程序化 2D 数字人与多音色',
    desc: '拟真语音陪伴，打破面对冷冰冰文本框的开口焦虑。',
    points: [
      'Web Audio AnalyserNode 实时计算 RMS 驱动口型同步',
      '支持按不同场景独立绑定数字人形象与语速',
      '内置多套高表现力角色预设与市场分享',
    ],
  },
]

const gallery = [
  {
    title: '纽约繁忙咖啡厅点单',
    mode: '1v1 日常对话',
    tone: 'purple',
    cover: '/images/covers/cafe_ordering.png',
    desc: '练习高频餐饮点单、客制化加料、价格核对与礼貌沟通。',
  },
  {
    title: '软件工程师全真技术面试',
    mode: '1v1 模拟面试',
    tone: 'mint',
    cover: '/images/covers/tech_interview.png',
    desc: '围绕系统架构、并发取舍与项目深挖进行多阶段追问。',
  },
  {
    title: '机场航班改签应急沟通',
    mode: '1v1 出行场景',
    tone: 'purple',
    cover: '/images/covers/airport_rebooking.png',
    desc: '模拟航班延误或取消时与柜台人员协商改签与住宿赔偿。',
  },
  {
    title: '国际列车车票预订与退改',
    mode: '1v1 出行场景',
    tone: 'purple',
    cover: '/images/covers/train_ticket.png',
    desc: '核对车次、席位偏好与跨站换乘信息，提升数字与时间表达准确度。',
  },
  {
    title: '外企三对一终面委员会',
    mode: '1vN 群面圆桌',
    tone: 'amber',
    cover: '/images/covers/panel-final-interview.png',
    desc: 'HR 总监、技术 VP 与产品负责人轮番深挖，输出录用合议评估。',
  },
  {
    title: '跨国产品立项评审圆桌',
    mode: '1vN 群面圆桌',
    tone: 'amber',
    cover: '/images/covers/panel-product-pitch.png',
    desc: '面对业务 VP、研发总监与财务合规官完成立项答辩。',
  },
  {
    title: 'AI 是否会取代初级工程师',
    mode: '1vN 正反辩论',
    tone: 'purple',
    cover: '/images/covers/ai-replace-juniors.png',
    desc: '四阶段辩论交锋，实时记录四维能力分与正反方胜率浮动。',
  },
  {
    title: '四天工作制利弊交锋',
    mode: '1vN 正反辩论',
    tone: 'purple',
    cover: '/images/covers/four-day-workweek.png',
    desc: '围绕效率、团队协作与职场文化展开英文思辨对抗。',
  },
]
</script>

<style scoped>
.features-page { max-width: 1200px; margin: 0 auto; padding: 104px 24px 56px; }
.page-head { text-align: center; max-width: 720px; margin: 0 auto 42px; }
.pill { display: inline-block; padding: 4px 12px; border-radius: 999px; background: #eee9ff; color: var(--primary-ink); font-size: 12px; font-weight: 700; margin-bottom: 10px; }
.page-head h1 { font-size: 34px; font-weight: 900; margin-bottom: 10px; }
.page-head p { font-size: 15px; color: var(--text-muted); }

.cap-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; margin-bottom: 58px; }
.cap-card { padding: 24px; transition: transform 0.16s; }
.cap-card:hover { transform: translateY(-3px); }
.cap-badge { display: inline-block; padding: 4px 10px; border-radius: 8px; font-size: 11.5px; font-weight: 800; margin-bottom: 12px; }
.cap-badge.purple { background: #eee9ff; color: #6046b4; }
.cap-badge.mint { background: #eaf7f0; color: #2a8c5f; }
.cap-badge.amber { background: #fff4e5; color: #b45309; }
.cap-card h3 { font-size: 17px; margin-bottom: 6px; }
.cap-card p { font-size: 13.5px; color: var(--text-muted); margin-bottom: 12px; }
.cap-points { list-style: none; display: flex; flex-direction: column; gap: 6px; font-size: 12.5px; color: var(--text-soft); }
.cap-points li::before { content: '•'; color: var(--primary); font-weight: 800; margin-right: 7px; }

.section-head { text-align: center; margin-bottom: 26px; }
.section-head h2 { font-size: 26px; font-weight: 800; margin-bottom: 6px; }
.section-head p { font-size: 14px; color: var(--text-muted); }
.gallery-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.gallery-card { overflow: hidden; transition: transform 0.16s; }
.gallery-card:hover { transform: translateY(-3px); }
.cover-wrap { position: relative; height: 148px; background: #f3eeff; }
.cover-wrap img { width: 100%; height: 100%; object-fit: cover; }
.mode-tag { position: absolute; top: 10px; left: 10px; padding: 3px 9px; border-radius: 999px; font-size: 10.5px; font-weight: 800; background: rgba(255, 255, 255, 0.94); }
.mode-tag.purple { color: #6046b4; }
.mode-tag.mint { color: #2a8c5f; }
.mode-tag.amber { color: #b45309; }
.gallery-body { padding: 14px 16px; }
.gallery-body h3 { font-size: 15px; margin-bottom: 4px; }
.gallery-body p { font-size: 12.5px; color: var(--text-muted); }

@media (max-width: 980px) {
  .cap-grid { grid-template-columns: 1fr; }
  .gallery-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .gallery-grid { grid-template-columns: 1fr; }
}
</style>

<template>
  <div ref="pageRef" class="features-page">
    <!-- Crisp Page Head + Category Jump Pills -->
    <section class="page-head">
      <span class="pill">EchoTalk 2.0 · Core Capabilities</span>
      <h1>全链路 AI 口语与听力引擎</h1>
      <p class="page-sub">六大核心引擎驱动，从开口表达到长期记忆闭环，一图看懂真实架构能力。</p>

      <nav class="jump-pills" aria-label="能力分区跳转">
        <a href="#arch" class="jump-pill">核心架构</a>
        <a href="#speech" class="jump-pill">多模态语音</a>
        <a href="#knowledge" class="jump-pill">知识与复习</a>
        <a href="#gallery" class="jump-pill">内置场景画廊</a>
      </nav>
    </section>

    <!-- 12-Col Visual-First Bento Capabilities Matrix -->
    <section class="cap-bento" aria-label="六大核心引擎矩阵">
      <!-- Cap 1 (7 cols): 1v1 场景语音对话 -->
      <article id="arch" class="tactile-card cap-card span-7" data-reveal>
        <div class="cap-top">
          <div class="cap-badges">
            <span class="cap-badge purple">LangGraph + AST 引擎</span>
            <span class="stat-pill mint">0% 状态幻觉</span>
          </div>
          <span class="stat-mono">10 项工具 · SSE 切句 TTS</span>
        </div>

        <h3>1v1 场景语音对话</h3>
        <p class="cap-one-line">模型专注自然交流，AST 白名单引擎依据原话子串确定性推进对话阶段。</p>

        <!-- Visual 3-Step Goal Tracker + Evidence Check -->
        <div class="ast-tracker">
          <div class="tracker-steps">
            <div class="step-chip done">✓ 1. 礼貌请求</div>
            <span class="step-line done" aria-hidden="true"></span>
            <div class="step-chip done">✓ 2. 规格定制</div>
            <span class="step-line done" aria-hidden="true"></span>
            <div class="step-chip done">✓ 3. 确认订单</div>
          </div>
          <div class="evidence-bar">
            <span class="ev-tag">Evidence Guard</span>
            <code>"a large drip coffee" ∈ input_text</code>
            <span class="ev-ok">校验通过</span>
          </div>
        </div>

        <div class="chip-row">
          <span class="tech-chip">0% 状态幻觉</span>
          <span class="tech-chip">10 项受控工具</span>
          <span class="tech-chip">SSE 切句 TTS</span>
        </div>
      </article>

      <!-- Cap 2 (5 cols): 1vN 多角色辩论 & 群面 -->
      <article class="tactile-card cap-card span-5" data-reveal>
        <div class="cap-top">
          <span class="cap-badge amber">1vN Debate &amp; Panel</span>
          <span class="stat-pill purple">2–4 AI 席位</span>
        </div>

        <h3>1vN 多角色辩论 &amp; 群面</h3>
        <p class="cap-one-line">支持正反辩论与外企群面双模式，多角色轮流追问并实时裁决胜率。</p>

        <!-- Tug-of-War + 4D Radar Split -->
        <div class="debate-mini-box">
          <div class="tug-head">
            <span class="tug-pro">我方 72%</span>
            <span class="tug-opp">对手 28%</span>
          </div>
          <div class="tug-track" aria-label="正反方实时胜率 72% 对 28%">
            <div class="tug-fill"></div>
          </div>

          <div class="radar-roles-row">
            <svg viewBox="0 0 180 128" class="mini-radar" role="img" aria-label="四维能力雷达图">
              <polygon points="90,26 128,64 90,102 52,64" fill="none" stroke="#e8e1f6" stroke-width="1" />
              <polygon points="90,42 112,64 90,86 68,64" fill="none" stroke="#efeaf9" stroke-width="1" />
              <polygon points="90,30 123,64 90,96 58,64" fill="rgba(139,115,221,0.22)" stroke="#8b73dd" stroke-width="1.8" />
              <text x="90" y="18" text-anchor="middle" class="radar-lbl">逻辑 92</text>
              <text x="135" y="67" text-anchor="start" class="radar-lbl">反驳 88</text>
              <text x="90" y="118" text-anchor="middle" class="radar-lbl">气场 90</text>
              <text x="45" y="67" text-anchor="end" class="radar-lbl">地道 86</text>
            </svg>

            <div class="role-pills-col">
              <span class="r-pill coral">Marcus · 反方</span>
              <span class="r-pill mint">Elena · 评委</span>
              <span class="r-pill purple">Leo · 队友</span>
            </div>
          </div>
        </div>
      </article>

      <!-- Cap 3 (5 cols): 程序化 2D 数字人 & 低延迟语音 -->
      <article id="speech" class="tactile-card cap-card span-5" data-reveal>
        <div class="cap-top">
          <span class="cap-badge purple">2D Avatar &amp; Audio</span>
          <span class="stat-pill mint">60fps 口型同步</span>
        </div>

        <h3>程序化 2D 数字人 &amp; 低延迟语音</h3>
        <p class="cap-one-line">浏览器直采 16kHz PCM16 零 FFmpeg 开销，AnalyserNode 实时驱动口型与眨眼。</p>

        <div class="speech-vis-box">
          <div class="eq-bars" aria-hidden="true">
            <span v-for="(h, idx) in eqHeights" :key="idx" :style="{ height: `${h}px`, animationDelay: `${idx * 90}ms` }"></span>
          </div>
          <div class="flow-pills">
            <span class="f-pill">AudioWorklet 16kHz</span>
            <span class="f-arrow">→</span>
            <span class="f-pill">Flash ASR</span>
            <span class="f-arrow">→</span>
            <span class="f-pill mint">AnalyserNode RMS</span>
          </div>
        </div>

        <div class="chip-row">
          <span class="tech-chip">0 FFmpeg</span>
          <span class="tech-chip">audio_token 复用</span>
          <span class="tech-chip">SHA256 问候缓存</span>
        </div>
      </article>

      <!-- Cap 4 (7 cols): Hybrid RRF + LightRAG 双引擎知识库 -->
      <article id="knowledge" class="tactile-card cap-card span-7" data-reveal>
        <div class="cap-top">
          <div class="cap-badges">
            <span class="cap-badge mint">Dual RAG Engine</span>
            <span class="stat-pill purple">bge-m3 1024d</span>
          </div>
          <span class="stat-mono">RRF k=60 · 后台图谱构建</span>
        </div>

        <h3>Hybrid RRF + LightRAG 双引擎知识库</h3>
        <p class="cap-one-line">MySQL ngram 全文 + 语义向量融合重排，支持 [ai] 隐藏底牌与实体关系图谱。</p>

        <div class="rag-split-box">
          <!-- Left: Document Visibility Isolation -->
          <div class="doc-vis-col">
            <div class="doc-row">
              <div>
                <strong>interview_rubric.md</strong>
                <small>18 块 · 评分准则</small>
              </div>
              <span class="vis-tag ai">[ai] 仅 AI</span>
            </div>
            <div class="doc-row">
              <div>
                <strong>candidate_brief.pdf</strong>
                <small>12 块 · 候选人须知</small>
              </div>
              <span class="vis-tag user">[user] 用户可见</span>
            </div>
          </div>

          <!-- Right: Clean SVG LightRAG Graph (labels cleanly below nodes) -->
          <div class="lr-mini-wrap">
            <svg viewBox="0 0 240 148" class="lr-mini-svg" role="img" aria-label="LightRAG 实体关系图谱">
              <line x1="120" y1="62" x2="48" y2="30" stroke="#8b73dd" stroke-width="1.5" />
              <line x1="120" y1="62" x2="192" y2="32" stroke="#8b73dd" stroke-width="1.5" />
              <line x1="120" y1="62" x2="46" y2="104" stroke="#d5cceb" stroke-width="1.3" />
              <line x1="120" y1="62" x2="190" y2="106" stroke="#8b73dd" stroke-width="1.5" />
              <g v-for="node in featuresLrNodes" :key="node.label" :transform="`translate(${node.x}, ${node.y})`">
                <circle :r="node.r" :fill="node.color" fill-opacity="0.16" :stroke="node.color" stroke-width="1.5" />
                <circle r="3.2" :fill="node.color" />
                <text x="0" :y="node.r + 11" text-anchor="middle" class="lr-mini-lbl">{{ node.label }}</text>
              </g>
            </svg>
          </div>
        </div>
      </article>

      <!-- Cap 5 (6 cols): 听力与四六级工作室 (Interactive Word Bank) -->
      <article class="tactile-card cap-card span-6" data-reveal>
        <div class="cap-top">
          <span class="cap-badge mint">Listening Studio</span>
          <span class="stat-pill purple">4 种互动题型</span>
        </div>

        <h3>听力与四六级工作室 (CET-4 / CET-6)</h3>
        <p class="cap-one-line">专项强化连读、弱读与真题精听，点击下方词块即可试玩拼句互动。</p>

        <div class="mode-pills-4">
          <span class="m-pill active">词块拼句</span>
          <span class="m-pill">听音选择</span>
          <span class="m-pill">听写填空</span>
          <span class="m-pill">跟读模仿</span>
        </div>

        <!-- Interactive Clickable Word Bank Demo -->
        <div class="wordbank-demo">
          <div class="wb-label">
            <span>拼句预览</span>
            <button type="button" class="wb-reset" @click="resetWordBank">重置词块</button>
          </div>
          <div class="wb-answer">
            <span v-if="!assembledWords.length" class="wb-placeholder">点击下方词块按语序拼接句子…</span>
            <button
              v-for="w in assembledWords"
              :key="'ans-' + w"
              type="button"
              class="wb-tile picked"
              @click="toggleWord(w)"
            >
              {{ w }}
            </button>
          </div>
          <div class="wb-pool">
            <button
              v-for="w in remainingWords"
              :key="'pool-' + w"
              type="button"
              class="wb-tile"
              @click="toggleWord(w)"
            >
              {{ w }}
            </button>
          </div>
        </div>
      </article>

      <!-- Cap 6 (6 cols): SM-2 间隔重复复习计划 -->
      <article class="tactile-card cap-card span-6" data-reveal>
        <div class="cap-top">
          <span class="cap-badge purple">SM-2 Memory Loop</span>
          <span class="stat-pill amber">&lt; 78 分自动入卡</span>
        </div>

        <h3>SM-2 间隔重复复习计划</h3>
        <p class="cap-one-line">自动沉淀对话中的低分词与语法纠错，按遗忘曲线动态调节复习间隔。</p>

        <div class="sm2-box">
          <svg viewBox="0 0 280 86" class="sm2-curve-svg" role="img" aria-label="SM-2 遗忘曲线动态间隔">
            <line x1="8" y1="72" x2="272" y2="72" stroke="#ebe7f5" stroke-width="1" />
            <line x1="8" y1="40" x2="272" y2="40" stroke="#f2eef9" stroke-dasharray="4 4" />
            <path
              d="M12 20 Q46 54 74 60 L82 16 Q132 38 168 44 L176 14 Q228 24 268 22"
              fill="none"
              stroke="#2a8c5f"
              stroke-width="2.8"
              stroke-linecap="round"
            />
            <circle cx="82" cy="16" r="4" fill="#2a8c5f" />
            <circle cx="176" cy="14" r="4" fill="#2a8c5f" />
            <circle cx="268" cy="22" r="4" fill="#2a8c5f" />
            <text x="68" y="83" class="sm2-tick">Day 1</text>
            <text x="162" y="83" class="sm2-tick">Day 6</text>
            <text x="242" y="83" class="sm2-tick">Day 15</text>
          </svg>

          <div class="sm2-ratings">
            <span class="rate-chip">Again</span>
            <span class="rate-chip">Hard</span>
            <span class="rate-chip good">Good · EF 2.5</span>
            <span class="rate-chip easy">Easy</span>
          </div>
        </div>
      </article>
    </section>

    <!-- 官方内置场景画廊（带分类筛选 Tab） -->
    <section id="gallery" class="gallery-section" data-reveal>
      <div class="gallery-head">
        <div>
          <h2>官方内置场景画廊</h2>
          <p>覆盖 1v1 日常情景、大厂技术面试、1vN 终面委员会与正反辩论对抗</p>
        </div>

        <div class="gallery-tabs" role="tablist" aria-label="按对话模式筛选场景">
          <button
            v-for="tab in galleryTabs"
            :key="tab.key"
            type="button"
            role="tab"
            :aria-selected="galleryFilter === tab.key"
            :class="{ active: galleryFilter === tab.key }"
            @click="galleryFilter = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>
      </div>

      <div class="gallery-grid">
        <article
          v-for="s in filteredGallery"
          :key="s.title"
          class="tactile-card gallery-card"
          data-reveal
        >
          <div class="cover-wrap">
            <img :src="s.cover" :alt="s.title" />
            <span class="mode-tag" :class="s.tone">{{ s.mode }}</span>
          </div>
          <div class="gallery-body">
            <h3>{{ s.title }}</h3>
            <p>{{ s.desc }}</p>
            <div class="g-tags">
              <span v-for="tag in s.tags" :key="tag">{{ tag }}</span>
            </div>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useScrollReveal } from '../composables/useScrollReveal.js'

const pageRef = ref(null)
useScrollReveal(pageRef)

const eqHeights = [10, 22, 14, 28, 18, 12, 26, 16, 24, 14, 20, 12]

const featuresLrNodes = [
  { label: 'System Design', color: '#8B73DD', x: 120, y: 62, r: 14 },
  { label: 'Sharding', color: '#2A8C5F', x: 48, y: 30, r: 10 },
  { label: 'Latency SLA', color: '#D97706', x: 192, y: 32, r: 10 },
  { label: 'Cache Tier', color: '#2A8C5F', x: 46, y: 104, r: 10 },
  { label: 'Trade-offs', color: '#C87462', x: 190, y: 106, r: 11 },
]

// Interactive Word Bank Demo
const wordBankPool = ['Could you', 'walk me through', 'the caching', 'strategy?']
const assembledWords = ref(['Could you', 'walk me through'])
const remainingWords = computed(() =>
  wordBankPool.filter((w) => !assembledWords.value.includes(w))
)

function toggleWord(word) {
  if (assembledWords.value.includes(word)) {
    assembledWords.value = assembledWords.value.filter((w) => w !== word)
  } else {
    assembledWords.value = [...assembledWords.value, word]
  }
}

function resetWordBank() {
  assembledWords.value = []
}

// Scenario Gallery with Filter Tabs
const galleryFilter = ref('all')
const galleryTabs = [
  { key: 'all', label: '全部 8' },
  { key: '1v1', label: '1v1 对话与面试 (4)' },
  { key: '1vN', label: '1vN 群面与辩论 (4)' },
]

const gallery = [
  {
    title: '纽约繁忙咖啡厅点单',
    group: '1v1',
    mode: '1v1 日常对话',
    tone: 'purple',
    cover: '/images/covers/cafe_ordering.png',
    desc: '点单定制、价格核对与礼貌替换沟通。',
    tags: ['3 个目标', '简单'],
  },
  {
    title: '软件工程师全真技术面试',
    group: '1v1',
    mode: '1v1 模拟面试',
    tone: 'mint',
    cover: '/images/covers/tech_interview.png',
    desc: '系统架构、并发取舍与项目深挖多阶段追问。',
    tags: ['AI 底牌', '专家'],
  },
  {
    title: '机场航班改签应急沟通',
    group: '1v1',
    mode: '1v1 出行场景',
    tone: 'purple',
    cover: '/images/covers/airport_rebooking.png',
    desc: '延误或取消时与地勤协商改签与补偿方案。',
    tags: ['3 个目标', '普通'],
  },
  {
    title: '国际列车车票预订与退改',
    group: '1v1',
    mode: '1v1 出行场景',
    tone: 'purple',
    cover: '/images/covers/train_ticket.png',
    desc: '核对车次、席位偏好与跨站换乘信息。',
    tags: ['数字时间', '简单'],
  },
  {
    title: '外企三对一终面委员会',
    group: '1vN',
    mode: '1vN 群面圆桌',
    tone: 'amber',
    cover: '/images/covers/panel-final-interview.png',
    desc: 'HR 总监、技术 VP 与产品负责人轮番深挖。',
    tags: ['3 AI 席位', '合议评估'],
  },
  {
    title: '跨国产品立项评审圆桌',
    group: '1vN',
    mode: '1vN 群面圆桌',
    tone: 'amber',
    cover: '/images/covers/panel-product-pitch.png',
    desc: '业务 VP、研发总监与财务合规官多视角质询。',
    tags: ['立项答辩', '实时评分'],
  },
  {
    title: 'AI 是否会取代初级工程师',
    group: '1vN',
    mode: '1vN 正反辩论',
    tone: 'purple',
    cover: '/images/covers/ai-replace-juniors.png',
    desc: '四阶段攻防交锋，实时计算四维能力分与胜率。',
    tags: ['四维雷达', '正反攻防'],
  },
  {
    title: '四天工作制利弊交锋',
    group: '1vN',
    mode: '1vN 正反辩论',
    tone: 'purple',
    cover: '/images/covers/four-day-workweek.png',
    desc: '围绕效率、团队协作与职场文化展开思辨对抗。',
    tags: ['职场思辨', '裁决报告'],
  },
]

const filteredGallery = computed(() =>
  galleryFilter.value === 'all'
    ? gallery
    : gallery.filter((item) => item.group === galleryFilter.value)
)
</script>

<style scoped>
.features-page { max-width: 1180px; margin: 0 auto; padding: 36px 24px 56px; }
.page-head { text-align: center; max-width: 740px; margin: 0 auto 38px; }
.pill { display: inline-block; padding: 4px 12px; border-radius: 999px; background: #eee9ff; color: var(--primary-ink); font-size: 12px; font-weight: 700; margin-bottom: 10px; }
.page-head h1 { font-size: clamp(30px, 3.6vw, 40px); font-weight: 900; margin-bottom: 10px; letter-spacing: -0.02em; }
.page-sub { font-size: 15px; color: var(--text-muted); margin-bottom: 18px; }

.jump-pills { display: flex; justify-content: center; gap: 8px; flex-wrap: wrap; }
.jump-pill {
  padding: 6px 14px;
  border-radius: 999px;
  border: 1.5px solid #e6dff5;
  background: #ffffff;
  font-size: 12.5px;
  font-weight: 700;
  color: #5a5572;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.jump-pill:hover { background: #f4f0ff; border-color: #c8baf0; color: #6046b4; }

/* ===== 12-Col Bento Matrix ===== */
.cap-bento {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 18px;
  margin-bottom: 62px;
}
.cap-card {
  padding: 22px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  scroll-margin-top: 96px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.cap-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 18px 40px rgba(96, 70, 180, 0.11);
}
.span-7 { grid-column: span 7; }
.span-6 { grid-column: span 6; }
.span-5 { grid-column: span 5; }

.cap-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}
.cap-badges { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.cap-badge { display: inline-block; padding: 3px 10px; border-radius: 8px; font-size: 11.5px; font-weight: 800; }
.cap-badge.purple { background: #eee9ff; color: #6046b4; }
.cap-badge.mint { background: #eaf7f0; color: #2a8c5f; }
.cap-badge.amber { background: #fff4e5; color: #b45309; }

.stat-pill {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
}
.stat-pill.mint { background: #eaf7f0; color: #2a8c5f; }
.stat-pill.purple { background: #eee9ff; color: #6046b4; }
.stat-pill.amber { background: #fff3ea; color: #c46a24; }
.stat-mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11.5px; font-weight: 700; color: #76718c; }

.cap-card h3 { font-size: 19px; font-weight: 800; color: var(--text); }
.cap-one-line { font-size: 13.5px; color: var(--text-muted); }

/* Cap 1: AST Goal Tracker */
.ast-tracker {
  border-radius: 14px;
  border: 1px solid #ebe7f5;
  background: #faf9fd;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.tracker-steps { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.step-chip {
  padding: 5px 11px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  background: #eaf7f0;
  color: #2a8c5f;
}
.step-line { flex: 1; min-width: 14px; height: 2px; background: #9bd9b8; border-radius: 2px; }
.evidence-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 8px 11px;
  border-radius: 10px;
  background: #ffffff;
  border: 1px solid #e6dff5;
  font-size: 12px;
}
.ev-tag { font-weight: 800; color: #6046b4; }
.evidence-bar code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11.5px; color: #35304e; }
.ev-ok { margin-left: auto; font-weight: 800; color: #2a8c5f; }

.chip-row { display: flex; flex-wrap: wrap; gap: 7px; margin-top: auto; }
.tech-chip {
  padding: 4px 10px;
  border-radius: 9px;
  border: 1px solid #e9e3f6;
  background: #faf9fd;
  font-size: 11.5px;
  font-weight: 700;
  color: #5a5572;
}

/* Cap 2: Debate Tug + Mini Radar */
.debate-mini-box {
  border-radius: 14px;
  border: 1px solid #ebe7f5;
  background: #faf9fd;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: auto;
}
.tug-head { display: flex; justify-content: space-between; font-size: 12px; font-weight: 800; }
.tug-pro { color: #2a8c5f; }
.tug-opp { color: #c87462; }
.tug-track { height: 9px; border-radius: 999px; background: #fdece8; overflow: hidden; }
.tug-fill { width: 72%; height: 100%; border-radius: 999px; background: linear-gradient(90deg, #8b73dd, #45c98e); }
.radar-roles-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.mini-radar { width: 170px; height: 120px; flex-shrink: 0; }
.radar-lbl { font-size: 9.5px; font-weight: 700; fill: #4b4663; }
.role-pills-col { display: flex; flex-direction: column; gap: 6px; flex: 1; }
.r-pill {
  padding: 4px 9px;
  border-radius: 9px;
  font-size: 11px;
  font-weight: 800;
  text-align: center;
}
.r-pill.coral { background: #fdece8; color: #b84a39; }
.r-pill.mint { background: #eaf7f0; color: #2a8c5f; }
.r-pill.purple { background: #eee9ff; color: #6046b4; }

/* Cap 3: Speech EQ & Flow */
.speech-vis-box {
  border-radius: 14px;
  border: 1px solid #ebe7f5;
  background: #faf9fd;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.eq-bars {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 34px;
}
.eq-bars span {
  width: 5px;
  border-radius: 999px;
  background: linear-gradient(180deg, #8b73dd, #45c98e);
  animation: eqPulse 0.9s ease-in-out infinite alternate;
}
@keyframes eqPulse {
  0% { transform: scaleY(0.45); opacity: 0.65; }
  100% { transform: scaleY(1.1); opacity: 1; }
}
.flow-pills { display: flex; align-items: center; justify-content: center; gap: 5px; flex-wrap: wrap; }
.f-pill {
  padding: 4px 8px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid #e6dff5;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11px;
  font-weight: 700;
  color: #35304e;
}
.f-pill.mint { background: #eaf7f0; border-color: #bfe7d1; color: #2a8c5f; }
.f-arrow { font-weight: 800; color: #b8a9f8; font-size: 12px; }

/* Cap 4: Dual RAG Split */
.rag-split-box {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: auto;
}
.doc-vis-col {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
}
.doc-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid #ebe7f5;
  background: #faf9fd;
}
.doc-row strong { display: block; font-size: 12.5px; color: #35304e; }
.doc-row small { display: block; font-size: 11px; color: #837f96; }
.vis-tag {
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 10.5px;
  font-weight: 800;
  white-space: nowrap;
}
.vis-tag.ai { background: #fff3ea; color: #c46a24; }
.vis-tag.user { background: #eee9ff; color: #6046b4; }
.lr-mini-wrap {
  border-radius: 12px;
  border: 1px solid #ebe7f5;
  background: #faf9fd;
  padding: 4px;
}
.lr-mini-svg { width: 100%; height: 138px; display: block; }
.lr-mini-lbl { font-size: 9.5px; font-weight: 700; fill: #35304e; }

/* Cap 5: Listening Studio + Interactive Word Bank */
.mode-pills-4 { display: flex; gap: 6px; flex-wrap: wrap; }
.m-pill {
  padding: 4px 10px;
  border-radius: 999px;
  background: #faf9fd;
  border: 1px solid #ebe7f5;
  font-size: 11.5px;
  font-weight: 700;
  color: #625e76;
}
.m-pill.active { background: #eaf7f0; border-color: #bee6d0; color: #2a8c5f; }
.wordbank-demo {
  border-radius: 14px;
  border: 1px solid #ebe7f5;
  background: #faf9fd;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: auto;
}
.wb-label { display: flex; justify-content: space-between; align-items: center; font-size: 11.5px; font-weight: 700; color: #76718c; }
.wb-reset { border: none; background: transparent; color: #6046b4; font-size: 11.5px; font-weight: 700; cursor: pointer; }
.wb-answer {
  min-height: 38px;
  border-radius: 10px;
  border: 1.5px dashed #d5cceb;
  background: #ffffff;
  padding: 5px 8px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}
.wb-placeholder { font-size: 11.5px; color: #9c96b2; }
.wb-pool { display: flex; flex-wrap: wrap; gap: 6px; min-height: 30px; }
.wb-tile {
  padding: 4px 10px;
  border-radius: 8px;
  border: 1.5px solid #e6e0f5;
  border-bottom: 2.5px solid #d7cef0;
  background: #ffffff;
  font-size: 12px;
  font-weight: 700;
  color: #35304e;
  cursor: pointer;
}
.wb-tile.picked { background: #eee9ff; border-color: #8b73dd; color: #6046b4; }

/* Cap 6: SM-2 Curve */
.sm2-box {
  border-radius: 14px;
  border: 1px solid #ebe7f5;
  background: #faf9fd;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: auto;
}
.sm2-curve-svg { width: 100%; height: 86px; display: block; }
.sm2-tick { font-size: 9.5px; font-weight: 700; fill: #837f96; font-family: ui-monospace, monospace; }
.sm2-ratings { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; text-align: center; }
.rate-chip {
  padding: 5px 4px;
  border-radius: 8px;
  border: 1px solid #ebe7f5;
  background: #ffffff;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11px;
  font-weight: 700;
  color: #625e76;
}
.rate-chip.good { background: #eaf7f0; border-color: #bee6d0; color: #2a8c5f; }
.rate-chip.easy { background: #eee9ff; border-color: #d7cbf5; color: #6046b4; }

/* ===== Interactive Scenario Gallery ===== */
.gallery-section { scroll-margin-top: 96px; }
.gallery-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 22px;
}
.gallery-head h2 { font-size: 26px; font-weight: 800; margin-bottom: 4px; }
.gallery-head p { font-size: 14px; color: var(--text-muted); }

.gallery-tabs {
  display: inline-flex;
  padding: 4px;
  border-radius: 12px;
  background: #f1edf9;
  border: 1px solid #e6dff5;
  gap: 4px;
}
.gallery-tabs button {
  border: none;
  background: transparent;
  padding: 6px 14px;
  border-radius: 9px;
  font-size: 12.5px;
  font-weight: 700;
  color: var(--text-muted);
  cursor: pointer;
}
.gallery-tabs button.active {
  background: #ffffff;
  color: var(--primary-ink);
  box-shadow: 0 2px 6px rgba(96, 70, 180, 0.12);
}

.gallery-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.gallery-card { overflow: hidden; display: flex; flex-direction: column; transition: transform 0.16s; }
.gallery-card:hover { transform: translateY(-3px); }
.cover-wrap { position: relative; height: 144px; background: #f3eeff; }
.cover-wrap img { width: 100%; height: 100%; object-fit: cover; }
.mode-tag { position: absolute; top: 10px; left: 10px; padding: 3px 9px; border-radius: 999px; font-size: 10.5px; font-weight: 800; background: rgba(255, 255, 255, 0.94); }
.mode-tag.purple { color: #6046b4; }
.mode-tag.mint { color: #2a8c5f; }
.mode-tag.amber { color: #b45309; }
.gallery-body { padding: 14px 16px; display: flex; flex-direction: column; gap: 6px; flex: 1; }
.gallery-body h3 { font-size: 15px; font-weight: 800; }
.gallery-body p { font-size: 12.5px; color: var(--text-muted); line-height: 1.45; }
.g-tags { display: flex; gap: 6px; margin-top: auto; padding-top: 4px; }
.g-tags span {
  padding: 2px 8px;
  border-radius: 6px;
  background: #faf9fd;
  border: 1px solid #efecf7;
  font-size: 10.5px;
  font-weight: 700;
  color: #6e6886;
}

@media (max-width: 980px) {
  .span-7, .span-6, .span-5 { grid-column: span 12; }
  .rag-split-box { grid-template-columns: 1fr; }
  .gallery-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .gallery-grid { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  .cap-card, .gallery-card, .eq-bars span { transition: none; animation: none; }
  .cap-card:hover, .gallery-card:hover { transform: none; }
}
</style>

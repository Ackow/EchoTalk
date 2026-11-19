<template>
  <div ref="pageRef" class="home-page">
    <!-- Hero 首屏：左侧品牌介绍与下载按钮 + 右侧 18s 宣传片一行并排，无底部控制台 -->
    <section class="hero-section">
      <div class="hero-ambient" aria-hidden="true">
        <div class="hero-grid-bg"></div>
        <div class="hero-orb orb-purple"></div>
        <div class="hero-orb orb-mint"></div>
      </div>

      <div class="hero-grid">
        <div class="hero-copy fade-in-up">
          <span class="hero-pill">
            <i class="pill-dot" aria-hidden="true"></i>
            EchoTalk 2.0
          </span>
          <h1>
            让每一次开口<br />
            <span class="gradient-text">都有真实 AI 回响</span>
          </h1>
          <p class="hero-sub">
            1v1 场景口语 · 1vN 多角色辩论 · 双引擎 RAG · 实时发音评测
          </p>
          <div class="hero-actions">
            <button type="button" class="btn-primary" @click="handleDownload">
              {{ downloadBtnText }}
            </button>
            <router-link to="/features" class="btn-secondary">
              探索核心特性 →
            </router-link>
          </div>
        </div>

        <div class="hero-video-wrap fade-in-up delay-1">
          <div class="showreel-frame">
            <video
              ref="heroVideoRef"
              class="launch-video"
              src="/videos/echotalk-launch.mp4"
              poster="/videos/echotalk-launch-poster.jpg"
              autoplay
              loop
              :muted="videoMuted"
              playsinline
              preload="metadata"
              aria-label="EchoTalk 2.0 宣传片"
              @click="toggleVideoPlay"
              @timeupdate="onVideoTimeUpdate"
            />

            <!-- 仅保留右上角极简隐形图标按钮（静音/取消静音 + 大屏剧场） -->
            <div class="video-corner-actions">
              <button
                type="button"
                class="corner-btn"
                :class="{ active: !videoMuted }"
                :aria-label="videoMuted ? '开启配音与 BGM' : '静音'"
                :title="videoMuted ? '开启配音与 BGM' : '静音'"
                @click="toggleVideoSound"
              >
                {{ videoMuted ? '🔇' : '🔊' }}
              </button>
              <button
                type="button"
                class="corner-btn"
                aria-label="大屏观看宣传片"
                title="大屏观看宣传片"
                @click="openTheater"
              >
                ⛶
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 四大核心引擎 Zig-Zag 交替展示（左文右图 ⇄ 左图右文，滑动渐入渐出） -->
    <section class="showcase-section" aria-label="四大核心引擎亮点">
      <div class="section-intro" data-reveal>
        <span class="sec-tag">核心亮点</span>
        <h2>四大核心引擎，把“哑巴英语”变成真实实战</h2>
      </div>

      <div class="zigzag-list">
        <!-- Row 1: Copy Left | Visual Right -->
        <div class="zigzag-row">
          <div class="zigzag-copy" data-reveal-left>
            <span class="sec-tag">双轨对话</span>
            <h3>从 1v1 咖啡点单到 1vN 外企群面</h3>
            <p>内置 ScenePackage v2 与 AST 白名单引擎，确定性追踪阶段与目标，告别 AI 状态幻觉。</p>
            <div class="copy-pills">
              <span class="pill-chip mint">0% 状态幻觉</span>
              <span class="pill-chip purple">2–4 AI 席位</span>
              <span class="pill-chip neutral">AST 目标推进</span>
            </div>
          </div>

          <div class="tactile-card zigzag-visual" data-reveal-right>
            <div class="visual-head">
              <span class="vis-label">1v1 + 1vN 双轨语音实训</span>
              <div class="inline-switcher" role="tablist" aria-label="切换双轨对话预览">
                <button
                  type="button"
                  role="tab"
                  :aria-selected="trackTab === '1v1'"
                  :class="{ active: trackTab === '1v1' }"
                  @click="trackTab = '1v1'"
                >
                  1v1 咖啡点单
                </button>
                <button
                  type="button"
                  role="tab"
                  :aria-selected="trackTab === '1vN'"
                  :class="{ active: trackTab === '1vN' }"
                  @click="trackTab = '1vN'"
                >
                  1vN 圆桌辩论
                </button>
              </div>
            </div>
            <div class="mini-shot-frame">
              <Transition name="shot" mode="out-in">
                <img
                  :key="trackTab"
                  :src="trackTab === '1v1' ? '/images/shots/practice.jpg' : '/images/shots/debate.jpg'"
                  :alt="trackTab === '1v1' ? '1v1 咖啡点单语音实训界面' : '1vN 多角色圆桌辩论界面'"
                />
              </Transition>
            </div>
          </div>
        </div>

        <!-- Row 2: Visual Left | Copy Right -->
        <div class="zigzag-row is-reverse">
          <div class="tactile-card zigzag-visual" data-reveal-left>
            <div class="ise-score-hero">
              <div class="score-ring-wrap">
                <svg viewBox="0 0 96 96" class="score-ring-svg" aria-hidden="true">
                  <circle cx="48" cy="48" r="39" class="ring-track" />
                  <circle cx="48" cy="48" r="39" class="ring-fill" />
                </svg>
                <div class="score-center">
                  <strong>94</strong>
                  <small>发音总分</small>
                </div>
              </div>

              <div class="ise-substats">
                <div class="substat">
                  <span>语调</span>
                  <strong>89</strong>
                </div>
                <div class="substat">
                  <span>语速</span>
                  <strong>138 WPM</strong>
                </div>
                <span class="natural-pill">✓ 表达自然准确</span>
              </div>
            </div>

            <div class="word-scores-grid" aria-label="逐词发音得分示例">
              <span class="w-chip good">Could <b>96</b></span>
              <span class="w-chip good">large <b>95</b></span>
              <span class="w-chip good">coffee <b>94</b></span>
              <span class="w-chip warn">croissant <b>84</b></span>
            </div>
          </div>

          <div class="zigzag-copy" data-reveal-right>
            <span class="sec-tag mint">旁路并行评测</span>
            <h3>开口即评测，逐词定位发音短板</h3>
            <p>单次录音签发一次性 audio_token，旁路并行完成讯飞 ISE 逐词打分与 LLM 地道度纠错。</p>
            <div class="copy-pills">
              <span class="pill-chip purple">audio_token 复用</span>
              <span class="pill-chip mint">准确度 / 语调 / WPM</span>
              <span class="pill-chip neutral">实时表达纠错</span>
            </div>
          </div>
        </div>

        <!-- Row 3: Copy Left | Visual Right -->
        <div class="zigzag-row">
          <div class="zigzag-copy" data-reveal-left>
            <span class="sec-tag">双引擎知识图谱</span>
            <h3>让 AI 真正读懂你的简历与题库</h3>
            <p>融合 MySQL ngram 全文与 bge-m3 1024 维向量 RRF 重排，并自动抽取实体关系图谱。</p>
            <div class="copy-pills">
              <span class="pill-chip purple">ngram + bge-m3 1024d</span>
              <span class="pill-chip mint">RRF k=60</span>
              <span class="pill-chip amber">[ai] 仅 AI 底牌</span>
            </div>
          </div>

          <div class="tactile-card zigzag-visual" data-reveal-right>
            <div class="lightrag-canvas">
              <svg viewBox="0 0 300 184" class="lightrag-svg" role="img" aria-label="LightRAG 实体关系图谱预览">
                <g class="lr-edges">
                  <path
                    v-for="(edge, idx) in lightragEdges"
                    :key="idx"
                    :d="edgePath(edge[0], edge[1])"
                    :class="{ hot: edge[0] === 0 || edge[1] === 0 }"
                  />
                </g>
                <g v-for="node in lightragNodes" :key="node.id" :transform="`translate(${node.x}, ${node.y})`">
                  <circle
                    :r="node.r"
                    :fill="node.color"
                    fill-opacity="0.16"
                    :stroke="node.color"
                    stroke-width="1.6"
                  />
                  <circle r="3.6" :fill="node.color" />
                  <text
                    x="0"
                    :y="node.r + 12"
                    text-anchor="middle"
                    class="lr-label"
                  >
                    {{ node.label }}
                  </text>
                </g>
              </svg>
            </div>

            <div class="vis-rows">
              <div class="vis-doc-row">
                <span>interview_rubric.md</span>
                <span class="vis-tag ai">[ai] 仅 AI 底牌</span>
              </div>
              <div class="vis-doc-row">
                <span>candidate_brief.pdf</span>
                <span class="vis-tag user">[user] 用户可见</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Row 4: Visual Left | Copy Right -->
        <div class="zigzag-row is-reverse">
          <div class="tactile-card zigzag-visual" data-reveal-left>
            <div class="loop-pipeline" aria-label="全链路流程">
              <template v-for="(step, idx) in loopNodes" :key="step.label">
                <div class="loop-node" :class="step.tone">
                  <span class="loop-dot"></span>
                  <span>{{ step.label }}</span>
                </div>
                <span v-if="idx < loopNodes.length - 1" class="loop-arrow" aria-hidden="true">→</span>
              </template>
            </div>

            <div class="split-minipanels">
              <div class="minipanel">
                <div class="minipanel-head">
                  <strong>SM-2 遗忘曲线</strong>
                  <span class="mini-tag amber">&lt; 78 分入卡</span>
                </div>
                <svg viewBox="0 0 240 76" class="sm2-svg" role="img" aria-label="SM-2 间隔重复记忆保持曲线">
                  <line x1="6" y1="64" x2="234" y2="64" stroke="#ebe7f5" stroke-width="1" />
                  <path
                    d="M10 18 Q40 48 64 53 L70 15 Q114 34 144 40 L150 13 Q198 22 230 20"
                    fill="none"
                    stroke="#2a8c5f"
                    stroke-width="2.6"
                    stroke-linecap="round"
                  />
                  <circle cx="70" cy="15" r="3.6" fill="#2a8c5f" />
                  <circle cx="150" cy="13" r="3.6" fill="#2a8c5f" />
                  <circle cx="230" cy="20" r="3.6" fill="#2a8c5f" />
                  <text x="58" y="74" class="sm2-tick">Day 1</text>
                  <text x="138" y="74" class="sm2-tick">Day 6</text>
                  <text x="206" y="74" class="sm2-tick">Day 15</text>
                </svg>
              </div>

              <div class="minipanel">
                <div class="minipanel-head">
                  <strong>共享免费额度池</strong>
                  <span class="mini-tag purple">已用 35%</span>
                </div>
                <div class="demo-bar" aria-label="今日免费额度已用 35%">
                  <div class="demo-fill"></div>
                </div>
                <div class="pool-badges">
                  <span class="d-badge green">每日签到 +10 点</span>
                  <span class="d-badge purple">
                    <EchoCreditIcon :size="13" />
                    对话 +15 XP
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div class="zigzag-copy" data-reveal-right>
            <span class="sec-tag mint">记忆与激励闭环</span>
            <h3>低分词自动入卡，每日免费额度无压力</h3>
            <p>自动抓取发音低于 78 分的词汇生成 SM-2 复习卡片，配合共享免费额度池与 XP 段位成长。</p>
            <div class="copy-pills">
              <span class="pill-chip amber">&lt; 78 分自动入卡</span>
              <span class="pill-chip purple">共享免费额度池</span>
              <span class="pill-chip mint">XP 积分激励</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 互动试听模块：还原宣传片「先出语音气泡 → 再展开原文」与三角色轮换 -->
    <div data-reveal>
      <LaunchShowcase ref="voiceDemoRef" @voice-start="muteHeroVideo" />
    </div>

    <!-- 真实客户端多端界面预览 -->
    <section class="shots-section" data-reveal aria-label="实机界面总览">
      <div class="section-intro">
        <span class="sec-tag">实机工作台</span>
        <h2>点击切换四大核心页面，所见即所得</h2>
      </div>

      <div class="preview-stage">
        <div class="preview-switcher">
          <button
            v-for="tab in previewTabs"
            :key="tab.key"
            type="button"
            :class="{ active: activePreview === tab.key }"
            :aria-pressed="activePreview === tab.key"
            @click="activePreview = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>

        <div class="mac-window">
          <div class="mac-body">
            <div class="shot-frame">
              <Transition name="shot">
                <img
                  :key="currentPreview.key"
                  :src="currentPreview.src"
                  :alt="currentPreview.label"
                  class="real-shot"
                  width="1024"
                  height="664"
                />
              </Transition>
            </div>
            <div class="shot-caption">
              <span>{{ currentPreview.caption }}</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 底部引导 -->
    <section class="bottom-cta" data-reveal>
      <div class="tactile-card cta-card">
        <div>
          <h2>准备好开启高效英语口语训练了吗？</h2>
          <p>下载 EchoTalk 2.0 桌面客户端，或浏览场景包社区与完整技术文档。</p>
        </div>
        <div class="cta-btns">
          <router-link to="/community" class="btn-secondary">浏览场景社区</router-link>
          <router-link to="/docs" class="btn-primary">阅读 2.0 文档</router-link>
        </div>
      </div>
    </section>

    <!-- 原生 Top-Layer <dialog> 大屏影院弹窗 -->
    <dialog
      ref="theaterDialogRef"
      class="theater-dialog"
      closedby="any"
      aria-labelledby="theater-title"
      @close="onTheaterClose"
    >
      <div class="theater-head">
        <div class="theater-title">
          <span class="theater-badge">EchoTalk 2.0 · 1080p 60fps</span>
          <strong id="theater-title">产品宣传片（含完整 BGM 与 Neural 英语配音）</strong>
        </div>
        <button
          type="button"
          class="theater-close"
          autofocus
          aria-label="关闭播放弹窗"
          @click="closeTheater"
        >
          ✕
        </button>
      </div>
      <div class="theater-video-wrap">
        <video
          ref="theaterVideoRef"
          class="theater-video"
          src="/videos/echotalk-launch.mp4"
          poster="/videos/echotalk-launch-poster.jpg"
          controls
          playsinline
        />
      </div>
    </dialog>

    <DownloadModal v-model:notice="dlNotice" :open="dlOpen" @close="dlOpen = false" />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import DownloadModal from '../components/DownloadModal.vue'
import EchoCreditIcon from '../components/EchoCreditIcon.vue'
import LaunchShowcase from '../components/LaunchShowcase.vue'
import { useScrollReveal } from '../composables/useScrollReveal.js'
import { detectClientTarget, triggerAutoDownload } from '../utils/clientDownload.js'

const pageRef = ref(null)
useScrollReveal(pageRef)

const dlOpen = ref(false)
const dlNotice = ref('')
const downloadBtnText = ref('下载桌面客户端')

const heroVideoRef = ref(null)
const theaterDialogRef = ref(null)
const theaterVideoRef = ref(null)
const voiceDemoRef = ref(null)

const videoMuted = ref(true)
const videoCurrentTime = ref(0)
const trackTab = ref('1v1')

const lightragNodes = [
  { id: 'n0', label: 'System Design', color: '#8B73DD', x: 150, y: 80, r: 16 },
  { id: 'n1', label: 'Sharding', color: '#2A8C5F', x: 58, y: 40, r: 12 },
  { id: 'n2', label: 'Latency SLA', color: '#D97706', x: 242, y: 42, r: 12 },
  { id: 'n3', label: 'Cache Tier', color: '#2A8C5F', x: 56, y: 126, r: 11 },
  { id: 'n4', label: 'Trade-offs', color: '#C87462', x: 238, y: 128, r: 13 },
]

const lightragEdges = [
  [0, 1],
  [0, 2],
  [0, 3],
  [0, 4],
  [1, 3],
  [2, 4],
]

function edgePath(aIdx, bIdx) {
  const na = lightragNodes[aIdx]
  const nb = lightragNodes[bIdx]
  const mx = (na.x + nb.x) / 2
  const my = (na.y + nb.y) / 2 - 8
  return `M ${na.x} ${na.y} Q ${mx} ${my} ${nb.x} ${nb.y}`
}

const loopNodes = [
  { label: '16kHz 直采', tone: 'purple' },
  { label: 'SSE 切句 TTS', tone: 'purple' },
  { label: 'ISE 评测', tone: 'mint' },
  { label: 'SM-2 复习', tone: 'mint' },
  { label: 'XP 激励', tone: 'amber' },
]

async function handleDownload() {
  const { target } = await triggerAutoDownload()
  if (target.key === 'other') {
    dlOpen.value = true
  }
}

function onVideoTimeUpdate() {
  if (heroVideoRef.value) {
    videoCurrentTime.value = heroVideoRef.value.currentTime || 0
  }
}

function toggleVideoPlay() {
  const v = heroVideoRef.value
  if (!v) return
  if (v.paused) {
    v.play().catch(() => {})
  } else {
    v.pause()
  }
}

function toggleVideoSound() {
  const v = heroVideoRef.value
  if (!v) return
  const nextMuted = !videoMuted.value
  videoMuted.value = nextMuted
  v.muted = nextMuted
  if (!nextMuted) {
    voiceDemoRef.value?.stopAudio?.()
    if (v.paused) v.play().catch(() => {})
  }
}

function muteHeroVideo() {
  videoMuted.value = true
  if (heroVideoRef.value) {
    heroVideoRef.value.muted = true
  }
}

let wasPlayingBeforeTheater = true

function openTheater() {
  voiceDemoRef.value?.stopAudio?.()
  muteHeroVideo()
  if (heroVideoRef.value) {
    wasPlayingBeforeTheater = !heroVideoRef.value.paused
    heroVideoRef.value.pause()
  }
  const dialog = theaterDialogRef.value
  if (dialog && !dialog.open) {
    dialog.showModal()
    if (theaterVideoRef.value) {
      theaterVideoRef.value.currentTime = videoCurrentTime.value
      theaterVideoRef.value.play().catch(() => {})
    }
  }
}

function closeTheater() {
  const dialog = theaterDialogRef.value
  if (dialog?.open) {
    dialog.close()
  }
}

function onTheaterClose() {
  if (theaterVideoRef.value) {
    theaterVideoRef.value.pause()
  }
  if (theaterDialogRef.value) {
    theaterDialogRef.value.returnValue = ''
  }
  if (wasPlayingBeforeTheater && heroVideoRef.value) {
    heroVideoRef.value.play().catch(() => {})
  }
}

// Safari <dialog closedby="any"> light-dismiss fallback
let removeLightDismiss = null

onMounted(async () => {
  const dialog = theaterDialogRef.value
  if (dialog && !('closedBy' in HTMLDialogElement.prototype)) {
    const outside = (e) => {
      const r = dialog.getBoundingClientRect()
      return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom
    }
    let pressedOutside = false
    const onPointerDown = (e) => {
      pressedOutside = dialog.open && outside(e)
    }
    const onPointerUp = (e) => {
      if (pressedOutside && dialog.open && outside(e)) {
        dialog.close()
      }
      pressedOutside = false
    }
    dialog.addEventListener('pointerdown', onPointerDown)
    dialog.addEventListener('pointerup', onPointerUp)
    removeLightDismiss = () => {
      dialog.removeEventListener('pointerdown', onPointerDown)
      dialog.removeEventListener('pointerup', onPointerUp)
    }
  }

  const target = await detectClientTarget()
  if (target.key !== 'other') {
    downloadBtnText.value = `下载 ${target.shortLabel}`
  }
})

onBeforeUnmount(() => {
  if (removeLightDismiss) {
    removeLightDismiss()
  }
})

const activePreview = ref('home')
const previewTabs = [
  { key: 'home', label: '今日训练', src: '/images/shots/home.jpg', caption: '今日训练工作台 · 限时双倍积分活动横幅 + 精选场景快捷入口' },
  { key: 'practice', label: '1v1 语音对话', src: '/images/shots/practice.jpg', caption: '1v1 语音对话 · 2D 数字人口型同步 + 目标达成进度条 + 实时语音输入' },
  { key: 'debate', label: '1vN 多角色', src: '/images/shots/debate.jpg', caption: '1vN 多角色辩论/群面 · 正反方胜率对抗条 + 四维战况雷达 + 轮流席位' },
  { key: 'scenes', label: '场景探索', src: '/images/shots/scenes.jpg', caption: '场景探索大厅 · 1v1 与多角色场景分类筛选 + ZIP 导入导出' },
]
const currentPreview = computed(() => previewTabs.find((t) => t.key === activePreview.value) || previewTabs[0])
</script>

<style scoped>
.home-page { padding-top: 0; position: relative; overflow-x: clip; }

/* ===== Single-Row Side-by-Side Hero & Ambient Aura ===== */
.hero-section {
  position: relative;
  max-width: 1220px;
  margin: 0 auto;
  padding: 36px 24px 20px;
}
.hero-ambient {
  position: absolute;
  inset: -44px -100px -24px;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}
.hero-grid-bg {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(to right, rgba(139, 115, 221, 0.085) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(139, 115, 221, 0.085) 1px, transparent 1px);
  background-size: 56px 56px;
  mask-image: radial-gradient(ellipse 76% 68% at 50% 45%, #000 18%, transparent 88%);
  -webkit-mask-image: radial-gradient(ellipse 76% 68% at 50% 45%, #000 18%, transparent 88%);
  animation: gridBreath 7s ease-in-out infinite;
}
.hero-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(52px);
  opacity: 0.45;
}
.hero-orb.orb-purple {
  width: 440px;
  height: 440px;
  top: -100px;
  left: -40px;
  background: radial-gradient(circle, rgba(139, 115, 221, 0.28), transparent 70%);
}
.hero-orb.orb-mint {
  width: 380px;
  height: 380px;
  top: -60px;
  right: 4%;
  background: radial-gradient(circle, rgba(69, 201, 142, 0.22), transparent 70%);
}
@keyframes gridBreath {
  0%, 100% { opacity: 0.55; transform: scale(1); }
  50% { opacity: 0.95; transform: scale(1.012); }
}

.hero-grid {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 0.88fr 1.22fr;
  gap: 36px;
  align-items: center;
}
.hero-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 5px 14px;
  border-radius: 999px;
  background: #eee9ff;
  color: var(--primary-ink);
  font-size: 13px;
  font-weight: 800;
  margin-bottom: 16px;
}
.pill-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #45c98e;
  box-shadow: 0 0 8px rgba(69, 201, 142, 0.75);
}
.hero-copy h1 {
  font-size: clamp(32px, 3.8vw, 48px);
  font-weight: 900;
  line-height: 1.15;
  letter-spacing: -0.025em;
  margin-bottom: 14px;
}
.hero-sub {
  font-size: 15.5px;
  font-weight: 600;
  color: var(--text-soft);
  margin-bottom: 24px;
}
.hero-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

/* ===== Seamless 16:9 Launch Video Frame (Zero Bottom Dock) ===== */
.hero-video-wrap {
  position: relative;
}
.showreel-frame {
  position: relative;
  aspect-ratio: 16 / 9;
  border: 1.5px solid #e6dff5;
  border-radius: 20px;
  overflow: hidden;
  background: #f8f7fd;
  box-shadow: 0 24px 64px rgba(105, 81, 184, 0.13);
}
.launch-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  cursor: pointer;
}
.video-corner-actions {
  position: absolute;
  top: 12px;
  right: 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(230, 224, 245, 0.9);
  opacity: 0.78;
  transition: opacity 0.18s ease, background 0.18s ease;
}
.showreel-frame:hover .video-corner-actions,
.video-corner-actions:focus-within {
  opacity: 1;
  background: rgba(255, 255, 255, 0.94);
}
.corner-btn {
  width: 30px;
  height: 30px;
  border-radius: 999px;
  border: none;
  background: transparent;
  color: #35304e;
  font-size: 14px;
  font-weight: 700;
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}
.corner-btn:hover { background: #eee9ff; color: #6046b4; }
.corner-btn.active { background: #8b73dd; color: #ffffff; }

/* ===== Alternating Zig-Zag Feature Showcase ===== */
.showcase-section {
  max-width: 1180px;
  margin: 68px auto 0;
  padding: 0 24px;
}
.section-intro {
  text-align: center;
  margin-bottom: 42px;
}
.sec-tag {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  background: #eee9ff;
  color: var(--primary-ink);
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 10px;
}
.sec-tag.mint { background: #eaf7f0; color: #2a8c5f; }
.section-intro h2 {
  font-size: clamp(26px, 3vw, 34px);
  font-weight: 900;
  letter-spacing: -0.02em;
  color: var(--text);
}

.zigzag-list {
  display: flex;
  flex-direction: column;
  gap: 56px;
}
.zigzag-row {
  display: grid;
  grid-template-columns: 1fr 1.08fr;
  gap: 48px;
  align-items: center;
}
.zigzag-row.is-reverse {
  grid-template-columns: 1.08fr 1fr;
}

.zigzag-copy h3 {
  font-size: clamp(24px, 2.5vw, 30px);
  font-weight: 900;
  line-height: 1.24;
  letter-spacing: -0.02em;
  color: var(--text);
  margin-bottom: 12px;
}
.zigzag-copy p {
  font-size: 15.5px;
  line-height: 1.65;
  color: var(--text-soft);
  margin-bottom: 18px;
}
.copy-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.pill-chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 11px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}
.pill-chip.purple { background: #eee9ff; color: #6046b4; }
.pill-chip.mint { background: #eaf7f0; color: #2a8c5f; }
.pill-chip.amber { background: #fff3ea; color: #c46a24; }
.pill-chip.neutral { background: #faf9fd; border: 1px solid #e8e2f6; color: #5a5572; }

.zigzag-visual {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.visual-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}
.vis-label {
  font-size: 13px;
  font-weight: 800;
  color: var(--text);
}
.inline-switcher {
  display: inline-flex;
  padding: 3px;
  border-radius: 10px;
  background: #f4f1fb;
  border: 1px solid #e6dff5;
  gap: 3px;
}
.inline-switcher button {
  border: none;
  background: transparent;
  padding: 4px 11px;
  border-radius: 8px;
  font-size: 11.5px;
  font-weight: 700;
  color: #76718c;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.inline-switcher button.active {
  background: #ffffff;
  color: #6046b4;
  box-shadow: 0 2px 6px rgba(96, 70, 180, 0.12);
}

.mini-shot-frame {
  position: relative;
  aspect-ratio: 16 / 10;
  border-radius: 14px;
  border: 1.5px solid #ebe7f5;
  overflow: hidden;
  background: #f5f2ff;
}
.mini-shot-frame img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: top center;
  display: block;
}

/* Row 2 Visual: ISE Pronunciation Score Ring & Word Chips */
.ise-score-hero {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid #ece7f6;
  background: #faf9fd;
}
.score-ring-wrap {
  position: relative;
  width: 92px;
  height: 92px;
  flex-shrink: 0;
}
.score-ring-svg { width: 100%; height: 100%; transform: rotate(-90deg); }
.ring-track { fill: none; stroke: #ebe7f5; stroke-width: 8; }
.ring-fill {
  fill: none;
  stroke: #2a8c5f;
  stroke-width: 8;
  stroke-linecap: round;
  stroke-dasharray: 245;
  stroke-dashoffset: 15;
}
.score-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.score-center strong {
  font-size: 28px;
  font-weight: 900;
  line-height: 1;
  color: #2a8c5f;
}
.score-center small {
  font-size: 10.5px;
  font-weight: 700;
  color: #76718c;
  margin-top: 2px;
}
.ise-substats {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.substat {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 13px;
  color: #625e76;
}
.substat strong {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 15px;
  font-weight: 800;
  color: #35304e;
}
.natural-pill {
  display: inline-flex;
  align-items: center;
  align-self: flex-start;
  padding: 3px 10px;
  border-radius: 999px;
  background: #eaf7f0;
  color: #2a8c5f;
  font-size: 11.5px;
  font-weight: 800;
}
.word-scores-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.w-chip {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  padding: 6px 11px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 700;
}
.w-chip b {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
}
.w-chip.good { background: #eaf7f0; color: #2a8c5f; }
.w-chip.warn { background: #fff3ea; color: #c46a24; }

/* Row 3 Visual: LightRAG Entity Graph + Visibility Rows */
.lightrag-canvas {
  border-radius: 14px;
  border: 1px solid #ebe7f5;
  background: #faf9fd;
  padding: 6px;
}
.lightrag-svg {
  width: 100%;
  height: 174px;
  display: block;
}
.lr-edges path { fill: none; stroke: #d7cff0; stroke-width: 1.3; }
.lr-edges path.hot { stroke: #8b73dd; stroke-width: 1.8; }
.lr-label { font-size: 10.5px; font-weight: 700; fill: #35304e; }
.vis-rows { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.vis-doc-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 11px;
  border-radius: 11px;
  border: 1px solid #ebe7f5;
  background: #faf9fd;
  font-size: 12px;
  font-weight: 700;
  color: #35304e;
}
.vis-tag {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10.5px;
  font-weight: 800;
  white-space: nowrap;
}
.vis-tag.ai { background: #fff3ea; color: #c46a24; }
.vis-tag.user { background: #eee9ff; color: #6046b4; }

/* Row 4 Visual: 5-Step Pipeline + SM-2 & Pool Split */
.loop-pipeline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid #ebe7f5;
  background: #faf9fd;
  flex-wrap: wrap;
}
.loop-node {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid #e6dff5;
  font-size: 11.5px;
  font-weight: 800;
  color: #35304e;
}
.loop-dot { width: 7px; height: 7px; border-radius: 50%; background: #8b73dd; }
.loop-node.mint .loop-dot { background: #2a8c5f; }
.loop-node.amber .loop-dot { background: #d97706; }
.loop-arrow { font-weight: 800; color: #b8a9f8; font-size: 13px; }

.split-minipanels {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.minipanel {
  border-radius: 14px;
  border: 1px solid #ebe7f5;
  background: #faf9fd;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.minipanel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  font-size: 12.5px;
}
.minipanel-head strong { color: #35304e; font-weight: 800; }
.mini-tag { padding: 2px 8px; border-radius: 999px; font-size: 10.5px; font-weight: 800; }
.mini-tag.amber { background: #fff3ea; color: #c46a24; }
.mini-tag.purple { background: #eee9ff; color: #6046b4; }
.sm2-svg { width: 100%; height: 72px; display: block; }
.sm2-tick { font-size: 9.5px; font-weight: 700; fill: #837f96; font-family: ui-monospace, monospace; }

.demo-bar { height: 11px; background: #ede8f9; border-radius: 999px; overflow: hidden; }
.demo-fill { width: 35%; height: 100%; background: linear-gradient(90deg, #8b73dd, #6951b8); border-radius: 999px; }
.pool-badges { display: flex; gap: 6px; flex-wrap: wrap; margin-top: auto; }
.d-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 9px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 700;
}
.d-badge.green { background: var(--green-soft); color: var(--green); }
.d-badge.purple { background: #eee9ff; color: var(--primary-ink); }

/* ===== Real App Screenshots Showcase ===== */
.shots-section {
  max-width: 1180px;
  margin: 68px auto 0;
  padding: 0 24px;
}
.preview-stage { position: relative; display: flex; flex-direction: column; gap: 14px; }
.preview-switcher {
  display: inline-flex;
  align-self: center;
  max-width: 100%;
  flex-wrap: wrap;
  justify-content: center;
  gap: 4px;
  padding: 4px;
  border-radius: 12px;
  background: #f1edf9;
  border: 1px solid #e6dff5;
}
.preview-switcher button {
  border: none;
  background: transparent;
  padding: 7px 16px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-muted);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.preview-switcher button.active {
  background: #ffffff;
  color: var(--primary-ink);
  box-shadow: 0 2px 6px rgba(96, 70, 180, 0.12);
}
.mac-window {
  max-width: 1020px;
  width: 100%;
  margin: 0 auto;
  border: 2px solid #dfd7f3;
  border-bottom: 6px solid #d0c4ec;
  border-radius: 18px;
  background: #ffffff;
  overflow: hidden;
  box-shadow: 0 18px 42px rgba(85, 68, 140, 0.12);
}
.mac-body { background: #ffffff; }
.shot-frame { position: relative; aspect-ratio: 1024 / 664; overflow: hidden; background: var(--surface-soft); }
.real-shot { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; display: block; }
.shot-enter-active, .shot-leave-active { transition: opacity 0.26s ease, transform 0.28s ease; }
.shot-enter-from { opacity: 0; transform: translateY(6px); }
.shot-leave-to { opacity: 0; transform: translateY(-6px); }
.shot-caption { padding: 10px 14px; font-size: 12.5px; color: var(--text-muted); background: #faf9fd; border-top: 1px solid #efecf7; text-align: center; }

/* ===== Bottom CTA ===== */
.bottom-cta { max-width: 1180px; margin: 56px auto 48px; padding: 0 24px; }
.cta-card { padding: 30px 34px; display: flex; justify-content: space-between; align-items: center; gap: 20px; flex-wrap: wrap; background: linear-gradient(135deg, #f5f1ff 0%, #ffffff 70%); }
.cta-card h2 { font-size: 22px; margin-bottom: 4px; }
.cta-card p { font-size: 14px; color: var(--text-muted); }
.cta-btns { display: flex; gap: 12px; flex-wrap: wrap; }

/* ===== Native Theater <dialog> Inner Chrome ===== */
.theater-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 20px;
  border-bottom: 1px solid #efecf7;
  background: #faf9fd;
}
.theater-title { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.theater-badge {
  padding: 3px 10px;
  border-radius: 999px;
  background: #eee9ff;
  color: #6046b4;
  font-size: 11.5px;
  font-weight: 800;
}
.theater-title strong { font-size: 14px; color: #35304e; }
.theater-close {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  border: 1.5px solid #e6e1f2;
  background: #ffffff;
  color: #5a5572;
  font-weight: 700;
  cursor: pointer;
}
.theater-close:hover { background: #f4f0ff; color: #6046b4; }
.theater-video-wrap { aspect-ratio: 16 / 9; background: #f8f7fd; }
.theater-video { width: 100%; height: 100%; display: block; }

.fade-in-up { animation: fadeInUp 0.55s ease both; }
.delay-1 { animation-delay: 0.12s; }
@keyframes fadeInUp { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }

@media (max-width: 960px) {
  .hero-grid,
  .zigzag-row,
  .zigzag-row.is-reverse {
    grid-template-columns: 1fr;
    gap: 28px;
  }
  .zigzag-row.is-reverse .zigzag-copy { order: -1; }
  .split-minipanels, .vis-rows { grid-template-columns: 1fr; }
}
@media (max-width: 600px) {
  .cta-card { padding: 24px; }
}
@media (prefers-reduced-motion: reduce) {
  .fade-in-up, .hero-grid-bg { animation: none; }
  .shot-enter-active, .shot-leave-active { transition: none; }
  .shot-enter-from, .shot-leave-to { transform: none; }
}
</style>

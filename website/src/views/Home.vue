<template>
  <div class="home-page">
    <!-- Hero 首屏：左侧品牌介绍 + 右侧交互式产品预览舱 -->
    <section class="hero-section">
      <div class="hero-grid">
        <div class="hero-copy fade-in-up">
          <span class="hero-pill">EchoTalk 2.0 · 触感紫白全新工作台</span>
          <h1>让每一次开口<br /><span class="gradient-text">都有真实 AI 回响</span></h1>
          <p class="hero-desc">
            集 <strong>1v1 沉浸式语音对话</strong>、<strong>1vN 多角色群面与辩论</strong>、<strong>四六级听力工作室</strong>、<strong>Hybrid + LightRAG 知识图谱</strong> 与 <strong>SM-2 间隔复习</strong> 于一体。支持按需切换的每日免费额度池，让练习轻松无压力。
          </p>
          <div class="hero-actions">
            <button type="button" class="btn-primary" @click="handleDownload">
              {{ downloadBtnText }}
            </button>
            <button type="button" class="btn-secondary" @click="handleOpenApp">
              打开本机 APP
            </button>
            <router-link to="/features" class="btn-secondary">探索核心特性</router-link>
          </div>
          <div class="hero-trust">
            <span>macOS / Windows 桌面端</span>
            <span class="sep">·</span>
            <span>SSE 流式低延迟语音</span>
            <span class="sep">·</span>
            <span>ISE 逐词发音评测</span>
          </div>
        </div>

        <!-- 右侧带外置切换器的真实界面预览舱 -->
        <div class="preview-stage fade-in-up delay-1">
          <div class="preview-switcher">
            <button
              v-for="tab in previewTabs"
              :key="tab.key"
              type="button"
              :class="{ active: activePreview === tab.key }"
              @click="activePreview = tab.key"
            >
              {{ tab.label }}
            </button>
          </div>

          <div class="mac-window">
            <div class="mac-body">
              <div class="preview-pane">
                <img :src="currentPreview.src" :alt="currentPreview.label" class="real-shot" />
                <div class="shot-caption">
                  <span>{{ currentPreview.caption }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 悬浮呼吸动画徽章（置于底部左右外侧，不遮挡切换器与截图文字） -->
          <div class="badges-row">
            <div class="float-badge static">
              <span class="b-dot green"></span>
              <span>发音准确度 <strong>94 分</strong></span>
            </div>
            <div class="float-badge static delay">
              <EchoCreditIcon :size="15" />
              <span>任务达成 <strong>+15 积分 · +15 XP</strong></span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 量化能力背书条 -->
    <section class="metrics-strip">
      <div class="metric-item">
        <strong>1v1 + 1vN</strong>
        <span>单人对话与多角色群面双轨架构</span>
      </div>
      <div class="metric-item">
        <strong>RRF + LightRAG</strong>
        <span>向量全文混合检索与图谱推理</span>
      </div>
      <div class="metric-item">
        <strong>SSE 分句 TTS</strong>
        <span>边生成边切句并发合成低延迟音频</span>
      </div>
      <div class="metric-item">
        <strong>SM-2 + ISE</strong>
        <span>遗忘曲线复习与逐词发音评测</span>
      </div>
    </section>

    <!-- Zig-Zag 交替图文介绍 -->
    <section class="zigzag-section">
      <div class="zigzag-row">
        <div class="zigzag-copy">
          <span class="sec-tag">双轨智能对话</span>
          <h2>从 1v1 咖啡点单到 1vN 外企三对一终面</h2>
          <p>
            内置 <strong>ScenePackage v2</strong> 声明式场景包引擎，实时追踪对话目标达成状态与阶段流转；切换到 <strong>多角色对话（Debate / Panel）</strong>，还可同时面对 2–4 位性格鲜明的 AI 面试官或辩手，体验真实群面压力测试。
          </p>
          <router-link to="/features" class="text-link">深入了解对话架构 →</router-link>
        </div>
        <div class="zigzag-visual tactile-card">
          <img src="/images/shots/debate.jpg" alt="EchoTalk 1vN 多角色辩论工作台" class="zigzag-shot" />
        </div>
      </div>

      <div class="zigzag-row reverse">
        <div class="zigzag-copy">
          <span class="sec-tag green">弹性商业化与任务激励</span>
          <h2>统一共享免费额度池，学习任务赚取回声积分</h2>
          <p>
            告别繁琐的单项次数限制。Free 用户每日享有共享免费额度池，用满 100% 后可自主开关是否消耗 <strong>Echo Credit</strong>；每日签到、听力磨耳朵、SM-2 复习均可同步领取 XP 段位经验与回声积分。
          </p>
          <router-link to="/pricing" class="text-link">对比 Free / Pro / Enterprise 方案 →</router-link>
        </div>
        <div class="zigzag-visual tactile-card pool-demo">
          <div class="demo-row">
            <span>今日共享免费额度池</span>
            <b>已用 35% · 剩余 65%</b>
          </div>
          <div class="demo-bar"><div class="demo-fill"></div></div>
          <div class="demo-badges">
            <span class="d-badge green">每日签到 +10 点 · +5 XP</span>
            <span class="d-badge purple">完成 1 场对话 +15 点 · +15 XP</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 底部引导 -->
    <section class="bottom-cta">
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
    <DownloadModal v-model:notice="dlNotice" :open="dlOpen" @close="dlOpen = false" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import DownloadModal from '../components/DownloadModal.vue'
import EchoCreditIcon from '../components/EchoCreditIcon.vue'
import { detectClientTarget, openLocalApp, triggerAutoDownload } from '../utils/clientDownload.js'

const dlOpen = ref(false)
const dlNotice = ref('')
const downloadBtnText = ref('下载桌面客户端')

async function handleDownload() {
  const { target } = await triggerAutoDownload()
  if (target.key === 'other') {
    dlOpen.value = true
  }
}

function handleOpenApp() {
  openLocalApp(() => {
    dlNotice.value = '未检测到本机已安装的 EchoTalk 客户端，请先下载安装。'
    dlOpen.value = true
  })
}

onMounted(async () => {
  const target = await detectClientTarget()
  if (target.key !== 'other') {
    downloadBtnText.value = `下载 ${target.shortLabel}`
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
.home-page { padding-top: 84px; }
.hero-section { max-width: 1220px; margin: 20px auto 0; padding: 0 24px; }
.hero-grid {
  display: grid;
  grid-template-columns: 1fr 1.15fr;
  gap: 36px;
  align-items: center;
}
.hero-pill {
  display: inline-block;
  padding: 5px 14px;
  border-radius: 999px;
  background: #eee9ff;
  color: var(--primary-ink);
  font-size: 12.5px;
  font-weight: 700;
  margin-bottom: 16px;
}
.hero-copy h1 {
  font-size: clamp(32px, 4vw, 48px);
  font-weight: 900;
  line-height: 1.16;
  margin-bottom: 16px;
  letter-spacing: -0.02em;
}
.hero-desc { font-size: 15.5px; color: var(--text-soft); margin-bottom: 24px; }
.hero-actions { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 18px; }
.hero-trust { font-size: 12.5px; color: var(--text-dim); display: flex; gap: 8px; flex-wrap: wrap; }

.preview-stage { position: relative; display: flex; flex-direction: column; gap: 12px; }
.preview-switcher {
  display: inline-flex;
  align-self: center;
  gap: 4px;
  padding: 4px;
  border-radius: 12px;
  background: #f1edf9;
  border: 1px solid #e6dff5;
}
.preview-switcher button {
  border: none;
  background: transparent;
  padding: 6px 14px;
  border-radius: 9px;
  font-size: 12.5px;
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
.badges-row {
  display: flex;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}
.float-badge.static {
  position: static;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 13px;
  border-radius: 12px;
  background: #ffffff;
  border: 1.5px solid var(--border);
  border-bottom: 3px solid var(--border-bottom);
  font-size: 12px;
  color: var(--text-soft);
  animation: floatY 4.2s ease-in-out infinite;
}
.float-badge.static.delay { animation-delay: 1.2s; }
.b-dot { width: 8px; height: 8px; border-radius: 50%; }
.b-dot.green { background: #2a8c5f; }
@keyframes floatY {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}

.mac-window {
  border: 2px solid #dfd7f3;
  border-bottom: 6px solid #d0c4ec;
  border-radius: 18px;
  background: #ffffff;
  overflow: hidden;
  box-shadow: 0 18px 42px rgba(85, 68, 140, 0.1);
}
.mac-body { background: #ffffff; }
.real-shot { width: 100%; height: auto; display: block; }
.zigzag-shot { width: 100%; border-radius: 12px; display: block; }
.shot-caption { padding: 9px 14px; font-size: 12px; color: var(--text-muted); background: #faf9fd; border-top: 1px solid #efecf7; text-align: center; }

.sim-panel { padding: 20px; display: flex; flex-direction: column; gap: 16px; }
.sim-header { display: flex; justify-content: space-between; align-items: center; }
.sim-tag { background: #eee9ff; color: var(--primary-ink); padding: 3px 10px; border-radius: 999px; font-size: 11.5px; font-weight: 700; }
.sim-stage { font-size: 12px; color: var(--green); font-weight: 700; }
.sim-avatars { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.sim-role { border: 1.5px solid #efecf7; border-radius: 12px; padding: 10px; text-align: center; background: #faf9fd; }
.sim-role.active { border-color: var(--primary); background: #f5f2ff; }
.role-circle { width: 34px; height: 34px; margin: 0 auto 6px; border-radius: 50%; background: var(--primary); color: #fff; font-size: 11px; font-weight: 800; display: grid; place-items: center; }
.sim-role strong { display: block; font-size: 12px; color: var(--text); }
.sim-role small { font-size: 10.5px; color: var(--text-muted); }
.sim-bubble { background: #f5f3ff; border-radius: 14px; padding: 14px 16px; }
.sim-bubble p { font-size: 13px; color: var(--text); font-style: italic; margin-bottom: 10px; }
.wave-bars { display: flex; align-items: center; gap: 4px; height: 20px; }
.wave-bars span { width: 4px; height: 8px; border-radius: 4px; background: var(--primary); animation: wave 1s ease-in-out infinite; }
@keyframes wave {
  0%, 100% { height: 6px; opacity: 0.5; }
  50% { height: 18px; opacity: 1; }
}

.sim-home { padding: 18px; text-align: center; }
.cartoon-shot { max-height: 200px; margin: 0 auto 12px; object-fit: contain; }
.sim-home-copy h4 { font-size: 15px; margin-bottom: 4px; }
.sim-home-copy p { font-size: 12.5px; color: var(--text-muted); }

.metrics-strip {
  max-width: 1220px;
  margin: 46px auto 0;
  padding: 0 24px;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}
.metric-item {
  background: #ffffff;
  border: 1.5px solid var(--border);
  border-bottom: 4px solid var(--border-bottom);
  border-radius: 16px;
  padding: 18px;
  text-align: center;
}
.metric-item strong { display: block; font-size: 18px; color: var(--primary-ink); margin-bottom: 4px; }
.metric-item span { font-size: 12.5px; color: var(--text-muted); }

.zigzag-section { max-width: 1220px; margin: 56px auto 0; padding: 0 24px; display: flex; flex-direction: column; gap: 48px; }
.zigzag-row { display: grid; grid-template-columns: 1fr 1fr; gap: 36px; align-items: center; }
.zigzag-row.reverse .zigzag-copy { order: 2; }
.sec-tag { display: inline-block; padding: 3px 11px; border-radius: 999px; background: #eee9ff; color: var(--primary-ink); font-size: 12px; font-weight: 700; margin-bottom: 10px; }
.sec-tag.green { background: var(--green-soft); color: var(--green); }
.zigzag-copy h2 { font-size: 26px; font-weight: 800; margin-bottom: 12px; line-height: 1.3; }
.zigzag-copy p { font-size: 14.5px; color: var(--text-soft); margin-bottom: 14px; }
.text-link { font-size: 14px; font-weight: 700; color: var(--primary-ink); }
.zigzag-visual { padding: 16px; }
.cover-collage { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.cover-collage img { width: 100%; height: 125px; object-fit: cover; border-radius: 12px; }

.pool-demo { padding: 26px 24px; display: flex; flex-direction: column; gap: 14px; }
.demo-row { display: flex; justify-content: space-between; font-size: 14px; }
.demo-row b { color: var(--primary-ink); }
.demo-bar { height: 12px; background: #f1edf9; border-radius: 999px; overflow: hidden; }
.demo-fill { width: 35%; height: 100%; background: linear-gradient(90deg, #8b73dd, #6951b8); border-radius: 999px; }
.demo-badges { display: flex; gap: 10px; flex-wrap: wrap; }
.d-badge { padding: 5px 11px; border-radius: 9px; font-size: 12px; font-weight: 700; }
.d-badge.green { background: var(--green-soft); color: var(--green); }
.d-badge.purple { background: #eee9ff; color: var(--primary-ink); }

.bottom-cta { max-width: 1220px; margin: 56px auto 48px; padding: 0 24px; }
.cta-card { padding: 30px 34px; display: flex; justify-content: space-between; align-items: center; gap: 20px; flex-wrap: wrap; background: linear-gradient(135deg, #f5f1ff 0%, #ffffff 70%); }
.cta-card h2 { font-size: 22px; margin-bottom: 4px; }
.cta-card p { font-size: 14px; color: var(--text-muted); }
.cta-btns { display: flex; gap: 12px; }

.fade-in-up { animation: fadeInUp 0.55s ease both; }
.delay-1 { animation-delay: 0.12s; }
@keyframes fadeInUp { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }

@media (max-width: 960px) {
  .hero-grid, .metrics-strip, .zigzag-row { grid-template-columns: 1fr; }
  .zigzag-row.reverse .zigzag-copy { order: 0; }
}
</style>

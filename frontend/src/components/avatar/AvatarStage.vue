<script setup>
// 数字人舞台：分层 SVG 角色 + 状态表演 + 口型驱动。
// 组件只接收 props，不拉数据、不持业务状态 —— 对话页 / 面试页 / 角色页共用同一份渲染。
import { computed, ref } from 'vue'
import AppIcon from '../AppIcon.vue'
import { useLipsync } from './useLipsync'

const props = defineProps({
  avatar: { type: Object, default: null },   // 形象声明 { id, display_name, theme, palette }；null 走缺省占位
  state: { type: String, default: 'idle' },   // 会话状态机取值：idle/listening/thinking/speaking
  size: { type: Number, default: 300 },       // 舞台宽度（px），内部按比例缩放
  lipSync: { type: String, default: 'state' }, // 实际口型级别：timeline/envelope/state/off
  showBackdrop: { type: Boolean, default: true },
})

// ---- 主题配色：每个形象一套，深色舞台上靠这套变量区分角色 ----
const PALETTES = {
  violet: { skin: '#f0dbd7', skinShade: '#e0bfbc', hair: '#3f3a58', cloth: '#6f6cc4', clothShade: '#5a58a8', accent: '#a9a4f0' },
  teal: { skin: '#e8cdb8', skinShade: '#d4b39c', hair: '#22333a', cloth: '#3f8f80', clothShade: '#2f7266', accent: '#7fd0bd' },
  amber: { skin: '#f2ddc4', skinShade: '#dcc0a0', hair: '#4a3524', cloth: '#c98a4b', clothShade: '#a86f38', accent: '#f0c088' },
  slate: { skin: '#e4d5cc', skinShade: '#cbb8ae', hair: '#2b2f3a', cloth: '#5a6478', clothShade: '#454e60', accent: '#9aa7c0' },
}
const palette = computed(() => PALETTES[props.avatar?.theme] || PALETTES.slate)
const initial = computed(() => (props.avatar?.display_name || 'A').trim().charAt(0).toUpperCase())

// ---- 口型：L1/L2 由 composable 驱动 CSS 变量，L3 走 state 类 ----
const { mouthOpen } = useLipsync()
const mouthStyle = computed(() => ({ '--mouth-open': mouthOpen.value.toFixed(3) }))

// 演示状态：角色页按钮直接改这里预览各状态，不依赖真实音频
const demoState = ref(null)
const shownState = computed(() => demoState.value || props.state)

const stateLabel = computed(() => ({
  idle: '待机', listening: '倾听', thinking: '思考', speaking: '说话',
}[shownState.value] || '待机'))
const lipLabel = computed(() => ({ timeline: '时间轴', envelope: '音量', state: '播放状态', off: '已关闭' }[props.lipSync] || '播放状态'))

defineExpose({
  // 预览一轮指定状态；传 null 回到真实会话状态
  playDemo(state = 'speaking') { demoState.value = state },
  stopDemo() { demoState.value = null },
})
</script>

<template>
  <!-- 深色聚光舞台：全应用唯一的暗区，把数字人推到视觉焦点 -->
  <div class="stage" :class="[`is-${shownState}`, `lip-${lipSync}`, { 'no-backdrop': !showBackdrop }]" :style="{ width: `${size}px` }">
    <div class="stage-grid" aria-hidden="true" />
    <div class="stage-glow" aria-hidden="true" />

    <svg class="figure" viewBox="0 0 200 260" role="img" :aria-label="`${avatar?.display_name || '数字人'}，当前${stateLabel}`">
      <defs>
        <linearGradient :id="`cloth-${avatar?.id || 'default'}`" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" :stop-color="palette.cloth" />
          <stop offset="1" :stop-color="palette.clothShade" />
        </linearGradient>
        <clipPath :id="(`head-clip-${avatar?.id || 'default'}`)">
          <path d="M100 34c26 0 42 19 42 45 0 30-19 52-42 52s-42-22-42-52c0-26 16-45 42-45z" />
        </clipPath>
      </defs>

      <!-- 0 backdrop：地面投影 -->
      <ellipse class="shadow" cx="100" cy="241" rx="54" ry="7" fill="#000" opacity=".34" />

      <!-- 1 body：躯干 + 服装（肩线上提到颈根，避免头身之间露出背景） -->
      <g class="layer-body">
        <path d="M100 138c33 0 56 19 60 45l5 60H35l5-60c4-26 27-45 60-45z" :fill="`url(#cloth-${avatar?.id || 'default'})`" />
        <!-- 领口内衬，制造深度 -->
        <path d="M100 138c11 0 20 3 27 8l-27 31-27-31c7-5 16-8 27-8z" fill="#fff" opacity=".92" />
        <path d="M100 138c-4 0-8 .3-12 1l12 15 12-15c-4-.7-8-1-12-1z" :fill="palette.clothShade" opacity=".55" />
        <!-- 肩线：让脖子与躯干的过渡自然 -->
        <path d="M78 143c7 4 14 6 22 6s15-2 22-6" fill="none" :stroke="palette.clothShade" stroke-width="1.6" opacity=".4" />
      </g>

      <!-- 2 hair_back：后层头发 -->
      <path class="layer-hair-back" d="M100 28c32 0 50 22 50 54 0 20-4 34-9 42l-8-3c4-9 6-20 6-32 0-24-16-40-39-40s-39 16-39 40c0 12 2 23 6 32l-8 3c-5-8-9-22-9-42 0-32 18-54 50-54z" :fill="palette.hair" />

      <!-- 3 neck：颈部，向上延伸进头后向下到肩线 -->
      <path d="M88 118h24v26c0 6-24 6-24 0z" :fill="palette.skinShade" />

      <!-- 4 head：头部底色 -->
      <path class="layer-head" d="M100 34c26 0 42 19 42 45 0 30-19 52-42 52s-42-22-42-52c0-26 16-45 42-45z" :fill="palette.skin" />

      <!-- 5 face：眼 / 眉 / 鼻 -->
      <g class="layer-face">
        <!-- 眉：thinking 时上移，speaking 时随口型微动 -->
        <g class="brows">
          <path d="M76 82c5-3 12-3 17 0" fill="none" :stroke="palette.hair" stroke-width="2.6" stroke-linecap="round" />
          <path d="M107 82c5-3 12-3 17 0" fill="none" :stroke="palette.hair" stroke-width="2.6" stroke-linecap="round" />
        </g>
        <!-- 眼：listening 时眨眼频率降低 -->
        <g class="eyes">
          <g class="eye left"><ellipse cx="85" cy="94" rx="4" ry="4.6" :fill="palette.hair" /><circle cx="86.4" cy="92.6" r="1.3" fill="#fff" opacity=".9" /></g>
          <g class="eye right"><ellipse cx="115" cy="94" rx="4" ry="4.6" :fill="palette.hair" /><circle cx="116.4" cy="92.6" r="1.3" fill="#fff" opacity=".9" /></g>
        </g>
        <!-- 鼻 -->
        <path d="M100 100v9c0 2-2 3-4 3" fill="none" :stroke="palette.skinShade" stroke-width="2" stroke-linecap="round" />
      </g>

      <!-- 6 mouth：受 --mouth-open 驱动（0 闭合 → 1 全开） -->
      <g class="layer-mouth" :style="mouthStyle">
        <ellipse class="mouth-open" cx="100" cy="117" rx="7" ry="4" fill="#7d4a52" />
        <ellipse class="mouth-teeth" cx="100" cy="115" rx="5.4" ry="1.5" fill="#fff" opacity=".85" />
      </g>

      <!-- 7 hair_front：刘海 -->
      <path class="layer-hair-front" d="M58 78c-2-32 16-52 42-52s44 20 42 52c-6-16-16-24-24-26-4 8-14 12-24 12-16 0-28-6-32-18-2 8-3 20-4 32z" :fill="palette.hair" />
      <!-- accent：强调色发饰，避免造型千篇一律 -->
      <path class="layer-accent" d="M136 52c8 2 14 8 16 16-6-4-12-5-18-4z" :fill="palette.accent" opacity=".9" />
    </svg>

    <!-- 轻量头像模式：仅首字母 + 状态环，作为 2D 的降级层 -->
    <div v-if="avatar?.kind === 'head'" class="head-only">
      <span class="head-ring" aria-hidden="true" />
      <span class="head-letter">{{ initial }}</span>
    </div>

    <!-- 3D 占位：不留空白，明确说明接入位置 -->
    <div v-if="avatar?.kind === '3d'" class="stage-empty">
      <AppIcon name="box" :size="26" />
      <p>3D 资源位</p>
      <small>Three.js / VRM 接入后启用，当前显示 2D 示意形象</small>
    </div>

    <!-- 舞台标注：左下状态、右上口型级别（如实上报，不谎称时间轴） -->
    <span class="stage-tag left">{{ stateLabel }}</span>
    <span class="stage-tag right">{{ lipLabel }}</span>
  </div>
</template>

<style scoped>
/* ---- 舞台：深色聚光区，全应用唯一暗区 ---- */
.stage {
  position: relative;
  display: grid;
  place-items: center;
  max-width: 100%; /* 兜底：容器被压缩时舞台跟着缩，不撑破布局 */
  aspect-ratio: 4 / 5;
  overflow: hidden;
  border-radius: 14px;
  background: #23243c;
  isolation: isolate;
}
.stage.no-backdrop { background: #2b2d4e; }

/* 细网格纹理，给暗区一层可读的底纹 */
.stage-grid {
  position: absolute; inset: 0;
  background-image: linear-gradient(rgba(255, 255, 255, .045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, .045) 1px, transparent 1px);
  background-size: 28px 28px;
}
/* 顶部聚光，营造舞台打光 */
.stage-glow {
  position: absolute; top: -32%; left: 50%;
  width: 150%; aspect-ratio: 1.4;
  transform: translateX(-50%);
  background: radial-gradient(closest-side, rgba(169, 164, 240, .3), transparent 72%);
  pointer-events: none;
}
.figure { position: relative; width: 74%; height: auto; }

/* ---- 状态表演：全部走 transform / opacity，避免触发布局 ---- */
@media (prefers-reduced-motion: no-preference) {
  /* speaking：轻微前倾 + 摆动 */
  .is-speaking .figure { animation: speak-lean 1.9s ease-in-out infinite; }
  /* thinking：整体上移，模拟视线离开 */
  .is-thinking .figure { animation: think-lift 2.6s ease-in-out infinite; }
  .is-thinking .brows { animation: brow-shift 2.6s ease-in-out infinite; }
  /* listening：眨眼频率降低（专注感） */
  .is-listening .eyes { animation: blink-calm 5.2s ease-in-out infinite; }
  .is-idle .eyes { animation: blink 4.4s ease-in-out infinite; }
  .is-speaking .eyes { animation: blink 3.6s ease-in-out infinite; }
}
@keyframes speak-lean { 0%, 100% { transform: translateY(0) rotate(0) } 50% { transform: translateY(-3px) rotate(.6deg) } }
@keyframes think-lift { 0%, 100% { transform: translateY(0) } 50% { transform: translateY(-7px) } }
@keyframes brow-shift { 0%, 100% { transform: translateY(0) } 50% { transform: translateY(-3.5px) } }
@keyframes blink { 0%, 94%, 100% { transform: scaleY(1) } 97% { transform: scaleY(.08) } }
@keyframes blink-calm { 0%, 96%, 100% { transform: scaleY(1) } 98% { transform: scaleY(.08) } }

/* ---- 口型 ---- */
.mouth-open { transform-box: fill-box; transform-origin: center; transform: scaleY(.16); }
.mouth-teeth { opacity: 0; }
/* L1 / L2：由 composable 写入 --mouth-open（0~1），覆盖上面的默认值 */
.lip-timeline .mouth-open, .lip-envelope .mouth-open { transform: scaleY(calc(.16 + var(--mouth-open, 0) * 2.4)); }
.lip-timeline .mouth-teeth, .lip-envelope .mouth-teeth { opacity: calc(.25 + var(--mouth-open, 0) * .75); }
/* L3：仅用播放状态，固定开合 + 轻微节奏感 */
.lip-state.is-speaking .mouth-open { animation: mouth-fallback .42s ease-in-out infinite alternate; }
.lip-state.is-speaking .mouth-teeth { animation: mouth-fallback-teeth .42s ease-in-out infinite alternate; }
@keyframes mouth-fallback { from { transform: scaleY(.5) } to { transform: scaleY(1.5) } }
@keyframes mouth-fallback-teeth { from { opacity: .3 } to { opacity: 1 } }
/* off：始终闭合 */
.lip-off .mouth-open { transform: scaleY(.16); }
.lip-off .mouth-teeth { opacity: 0; }

/* ---- 轻量头像降级层 ---- */
.head-only { position: absolute; inset: 0; display: grid; place-items: center; }
.head-ring {
  position: absolute; width: 46%; aspect-ratio: 1;
  border-radius: 50%;
  border: 2px solid rgba(169, 164, 240, .5);
  transition: transform .3s cubic-bezier(.16, 1, .3, 1), border-color .3s;
}
.is-speaking .head-ring { transform: scale(1.08); border-color: rgba(169, 164, 240, .95); }
.is-listening .head-ring { border-color: rgba(127, 208, 189, .7); }
.is-thinking .head-ring { border-style: dashed; }
.head-letter { position: relative; font-family: Georgia, 'Times New Roman', serif; font-size: 76px; color: #e8e8f6; line-height: 1; }

/* ---- 3D 占位 ---- */
.stage-empty { position: absolute; inset: 0; display: grid; align-content: center; justify-items: center; gap: 7px; padding: 22px; text-align: center; color: #9a9cc4; }
.stage-empty p { margin: 0; font-size: 14px; color: #c6c7e4; }
.stage-empty small { max-width: 220px; font-size: 11.5px; line-height: 1.7; color: #8688b0; }

/* ---- 舞台标注 ---- */
.stage-tag {
  position: absolute; top: 11px;
  padding: 3px 8px; border-radius: 5px;
  font-size: 11px; letter-spacing: .04em;
  background: rgba(255, 255, 255, .12);
  color: #dcdcf0;
  backdrop-filter: blur(4px);
}
.stage-tag.left { left: 11px; }
.stage-tag.right { right: 11px; }
.is-speaking .stage-tag.left { background: rgba(169, 164, 240, .32); color: #fff; }
.is-listening .stage-tag.left { background: rgba(127, 208, 189, .28); color: #e6faf4; }
.is-thinking .stage-tag.left { background: rgba(240, 192, 136, .26); color: #fdf1e2; }
</style>

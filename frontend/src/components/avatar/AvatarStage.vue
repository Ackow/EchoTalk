<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import CharacterPortrait from './CharacterPortrait.vue'
import { resolveAppearance } from './avatarAppearance'

const props = defineProps({
  // 当前形象对象（api/avatar.js 的 FALLBACK_AVATARS 项）：驱动名字、主题与文案
  avatar: { type: Object, default: null },
  appearance: { type: Object, default: null },
  state: { type: String, default: 'idle' },
  size: { type: Number, default: 420 },
  lipSync: { type: String, default: 'state' },
  showBackdrop: { type: Boolean, default: true },
})
const emit = defineEmits(['state-change'])
const demoState = ref(null)
const happy = ref(false)
const greeting = ref('')
const gaze = ref({ x: 0, y: 0 })
let responseTimer
let demoTimer
// 展示名拆分：display_name 形如 "Mira · 米拉"，取英文部分用于台词与角标
const firstName = computed(() => (props.avatar?.display_name || 'Leo').split(' · ')[0])
const shownState = computed(() => demoState.value || props.state)
const effectiveAppearance = computed(() => props.appearance || props.avatar?.appearance || null)
const resolvedBackdrop = computed(() => resolveAppearance(props.avatar?.id || 'leo_2d', effectiveAppearance.value).backdrop)
watch(shownState, state => emit('state-change', state), { immediate: true })
const stateLabel = computed(() => ({ idle: '准备好了', listening: '认真倾听', thinking: '想一想…', speaking: '说话演示' }[shownState.value] || '准备好了'))
const message = computed(() => greeting.value || ({ idle: `Hi, I’m ${firstName.value}. 很高兴见到你。`, listening: 'Take your time. 我在听。', thinking: 'Let me think for a moment…', speaking: 'Let’s start with a little conversation.' }[shownState.value]))

// 指针只驱动小幅视线与头部偏移，不改变业务状态；离开舞台后回到正视。
function look(event) {
  if (event.pointerType === 'touch' || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  const rect = event.currentTarget.getBoundingClientRect()
  gaze.value = { x: Math.max(-1, Math.min(1, (event.clientX - rect.left) / rect.width * 2 - 1)), y: Math.max(-1, Math.min(1, (event.clientY - rect.top) / rect.height * 2 - 1)) }
}
function greet() {
  clearTimeout(responseTimer)
  happy.value = true
  greeting.value = props.avatar?.greeting || 'Hey! 今天想聊点什么？'
  responseTimer = setTimeout(() => { happy.value = false; greeting.value = '' }, 2400)
}
function playDemo(state = 'idle', durationMs = 5000) {
  clearTimeout(responseTimer)
  clearTimeout(demoTimer)
  happy.value = false
  greeting.value = ''
  demoState.value = state
  // 说话演示按时长自动复位（默认 5s），避免无音频时一直张嘴。
  if (state === 'speaking') demoTimer = setTimeout(() => { demoState.value = null }, Math.max(1500, durationMs))
}
// 换形象时清除上个角色的表情和演示，不继承未结束的互动。
watch(() => props.avatar?.id, () => {
  clearTimeout(responseTimer); clearTimeout(demoTimer)
  happy.value = false; greeting.value = ''; demoState.value = null; gaze.value = { x: 0, y: 0 }
})

defineExpose({ playDemo, greet, stopDemo() { clearTimeout(demoTimer); demoState.value = null } })
onBeforeUnmount(() => { clearTimeout(responseTimer); clearTimeout(demoTimer) })
</script>

<template>
  <div class="stage" :class="[`is-${shownState}`, `char-${avatar?.id || 'leo_2d'}`, `bg-${resolvedBackdrop}`, { 'no-backdrop': !showBackdrop, delighted: happy }]" :style="{ width: `${size}px` }" @pointermove="look" @pointerleave="gaze = { x: 0, y: 0 }">
    <!-- 场景专属插画背景（柔化对比度，突出前景数字人） -->
    <svg v-if="showBackdrop && resolvedBackdrop !== 'studio'" class="scene-backdrop" viewBox="0 0 400 460" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <!-- Leo: 纽约街头咖啡厅内景 -->
      <template v-if="resolvedBackdrop === 'cafe'">
        <!-- 墙面与木质护墙板 -->
        <rect x="0" y="0" width="400" height="330" fill="#fbf3ea" />
        <rect x="0" y="310" width="400" height="150" fill="#ead8c7" />
        <line x1="0" y1="310" x2="400" y2="310" stroke="#d5bc9f" stroke-width="3" />
        <!-- 拱形落地窗与室外暖阳 -->
        <path d="M28,280 L28,120 C28,55 152,55 152,120 L152,280 Z" fill="#fef7e2" stroke="#d8bfa3" stroke-width="3" />
        <line x1="90" y1="72" x2="90" y2="280" stroke="#e4cfb6" stroke-width="2.5" />
        <line x1="28" y1="185" x2="152" y2="185" stroke="#e4cfb6" stroke-width="2.5" />
        <circle cx="116" cy="126" r="22" fill="#fde68a" opacity="0.6" />
        <!-- 右侧菜单黑板与咖啡架 -->
        <rect x="256" y="76" width="114" height="84" rx="8" fill="#594a6e" opacity="0.22" stroke="#b9a7cf" stroke-width="2.5" />
        <line x1="274" y1="100" x2="348" y2="100" stroke="#ffffff" stroke-width="3" stroke-linecap="round" opacity="0.7" />
        <line x1="274" y1="118" x2="330" y2="118" stroke="#fde68a" stroke-width="2.5" stroke-linecap="round" opacity="0.8" />
        <line x1="274" y1="134" x2="340" y2="134" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" opacity="0.55" />
        <!-- 层架与咖啡杯罐 -->
        <line x1="250" y1="205" x2="376" y2="205" stroke="#cfa987" stroke-width="4" stroke-linecap="round" />
        <rect x="266" y="177" width="22" height="26" rx="4" fill="#d8b4fe" opacity="0.65" />
        <rect x="296" y="182" width="18" height="21" rx="3" fill="#fcd34d" opacity="0.65" />
        <path d="M326,184 L348,184 L344,203 L330,203 Z" fill="#ffffff" stroke="#cfa987" stroke-width="2" />
        <!-- 吊灯 -->
        <line x1="200" y1="0" x2="200" y2="40" stroke="#b0967a" stroke-width="2.5" />
        <path d="M174,58 C174,40 226,40 226,58 Z" fill="#f3c68f" opacity="0.85" />
        <!-- 前景吧台边缘 -->
        <rect x="0" y="378" width="400" height="82" fill="#dfc4ab" opacity="0.55" />
      </template>

      <!-- Emily: 机场航站楼与停机坪 -->
      <template v-else-if="resolvedBackdrop === 'airport'">
        <!-- 落地玻璃幕墙与天空 -->
        <rect x="0" y="0" width="400" height="310" fill="#e6f5ff" />
        <path d="M0,255 Q200,235 400,255 L400,310 L0,310 Z" fill="#d8e7f5" />
        <!-- 云朵 -->
        <path d="M38,118 Q62,98 90,114 Q108,106 120,122 L38,122 Z" fill="#ffffff" opacity="0.85" />
        <path d="M276,94 Q298,78 324,92 Q342,84 352,98 L276,98 Z" fill="#ffffff" opacity="0.8" />
        <!-- 远景飞机轮廓与航线 -->
        <path d="M286,162 L322,150 L314,162 L330,168 L306,169 L298,176 L296,166 Z" fill="#94b8d8" opacity="0.7" />
        <path d="M230,192 Q262,180 286,166" fill="none" stroke="#93c5fd" stroke-width="2" stroke-dasharray="4 4" />
        <!-- 航站楼倾斜玻璃立柱 -->
        <line x1="76" y1="0" x2="52" y2="310" stroke="#c7dcef" stroke-width="4" />
        <line x1="324" y1="0" x2="348" y2="310" stroke="#c7dcef" stroke-width="4" />
        <line x1="0" y1="196" x2="400" y2="196" stroke="#d0e2f2" stroke-width="2.5" />
        <!-- 登机口信息牌 -->
        <rect x="26" y="42" width="118" height="44" rx="8" fill="#4f4678" opacity="0.24" />
        <circle cx="44" cy="64" r="7" fill="#34d399" opacity="0.85" />
        <line x1="58" y1="58" x2="126" y2="58" stroke="#ffffff" stroke-width="3" stroke-linecap="round" opacity="0.8" />
        <line x1="58" y1="70" x2="102" y2="70" stroke="#a7f3d0" stroke-width="2.5" stroke-linecap="round" opacity="0.85" />
        <!-- 机场服务柜台 -->
        <rect x="0" y="310" width="400" height="150" fill="#e9e4f5" />
        <rect x="0" y="366" width="400" height="14" fill="#c7d9ec" />
      </template>

      <!-- Claire: 火车站售票大厅与站台列车 -->
      <template v-else-if="resolvedBackdrop === 'station'">
        <!-- 车站拱形穹顶与采光玻璃 -->
        <rect x="0" y="0" width="400" height="315" fill="#eef1fc" />
        <path d="M24,280 L24,132 C24,42 184,42 184,132 L184,280 Z" fill="#fef9ec" stroke="#d5d9ef" stroke-width="3" />
        <line x1="104" y1="62" x2="104" y2="280" stroke="#dfe4f6" stroke-width="2.5" />
        <line x1="24" y1="186" x2="184" y2="186" stroke="#dfe4f6" stroke-width="2.5" />
        <!-- 车站大钟 -->
        <circle cx="298" cy="86" r="30" fill="#ffffff" stroke="#b9c0e6" stroke-width="3" />
        <line x1="298" y1="86" x2="298" y2="68" stroke="#4f4678" stroke-width="2.5" stroke-linecap="round" />
        <line x1="298" y1="86" x2="312" y2="92" stroke="#6366f1" stroke-width="2.5" stroke-linecap="round" />
        <!-- 电子车次牌 -->
        <rect x="236" y="136" width="136" height="52" rx="8" fill="#2d3352" opacity="0.86" />
        <circle cx="254" cy="154" r="4" fill="#34d399" />
        <line x1="266" y1="154" x2="354" y2="154" stroke="#e2e8f0" stroke-width="3" stroke-linecap="round" />
        <line x1="254" y1="170" x2="334" y2="170" stroke="#fde68a" stroke-width="2.5" stroke-linecap="round" opacity="0.9" />
        <!-- 远景高速列车剪影 -->
        <path d="M38,248 L158,248 Q182,248 190,270 L38,270 Z" fill="#a5b4fc" opacity="0.72" />
        <rect x="52" y="254" width="24" height="8" rx="3" fill="#ffffff" opacity="0.85" />
        <rect x="84" y="254" width="24" height="8" rx="3" fill="#ffffff" opacity="0.85" />
        <rect x="116" y="254" width="24" height="8" rx="3" fill="#ffffff" opacity="0.85" />
        <!-- 售票窗口台面 -->
        <rect x="0" y="310" width="400" height="150" fill="#ebe7f7" />
        <rect x="0" y="366" width="400" height="14" fill="#d3ccf0" />
      </template>

      <!-- David: 现代玻璃会议室 -->
      <template v-else-if="resolvedBackdrop === 'meeting'">
        <!-- 室内墙面与落地窗城市天际线 -->
        <rect x="0" y="0" width="400" height="320" fill="#eef1fc" />
        <!-- 左侧落地窗城市剪影 -->
        <rect x="22" y="48" width="132" height="236" rx="10" fill="#e0e7ff" stroke="#c7d2fe" stroke-width="2.5" />
        <rect x="34" y="160" width="28" height="124" fill="#c7d2fe" opacity="0.6" />
        <rect x="68" y="128" width="32" height="156" fill="#bcc8fa" opacity="0.6" />
        <rect x="106" y="176" width="34" height="108" fill="#c7d2fe" opacity="0.55" />
        <!-- 右侧项目发布看板 -->
        <rect x="242" y="64" width="136" height="118" rx="10" fill="#ffffff" opacity="0.72" stroke="#c7d2fe" stroke-width="2.5" />
        <rect x="256" y="80" width="54" height="8" rx="4" fill="#818cf8" opacity="0.55" />
        <rect x="256" y="98" width="34" height="24" rx="4" fill="#ddd6fe" opacity="0.85" />
        <rect x="296" y="98" width="34" height="24" rx="4" fill="#bfdbfe" opacity="0.85" />
        <rect x="336" y="98" width="30" height="24" rx="4" fill="#a7f3d0" opacity="0.85" />
        <path d="M258,156 L284,142 L310,148 L352,130" fill="none" stroke="#6366f1" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" opacity="0.65" />
        <!-- 会议桌与背景墙 -->
        <rect x="0" y="320" width="400" height="140" fill="#e3dff2" />
        <rect x="0" y="368" width="400" height="92" fill="#d3cde8" opacity="0.65" />
      </template>

      <!-- Sarah: 科技公司技术面试室 -->
      <template v-else-if="resolvedBackdrop === 'interview'">
        <!-- 柔和工作室墙面 -->
        <rect x="0" y="0" width="400" height="325" fill="#f3effc" />
        <!-- 左侧书架与绿植 -->
        <rect x="24" y="64" width="106" height="196" rx="8" fill="#e8e0f7" stroke="#d5c8ef" stroke-width="2.5" />
        <line x1="24" y1="128" x2="130" y2="128" stroke="#d5c8ef" stroke-width="3" />
        <line x1="24" y1="192" x2="130" y2="192" stroke="#d5c8ef" stroke-width="3" />
        <rect x="36" y="86" width="14" height="40" rx="2" fill="#a78bfa" opacity="0.55" />
        <rect x="54" y="92" width="12" height="34" rx="2" fill="#93c5fd" opacity="0.6" />
        <rect x="70" y="84" width="16" height="42" rx="2" fill="#c4b5fd" opacity="0.7" />
        <!-- 小盆栽 -->
        <rect x="90" y="170" width="22" height="20" rx="4" fill="#d8b4fe" opacity="0.75" />
        <path d="M101,170 Q92,150 84,154 M101,170 Q102,146 108,150 M101,170 Q112,152 118,158" fill="none" stroke="#6ee7b7" stroke-width="3.5" stroke-linecap="round" />
        <!-- 右侧技术白板（系统架构节点与代码符号） -->
        <rect x="252" y="70" width="124" height="114" rx="10" fill="#ffffff" opacity="0.72" stroke="#d8ccf5" stroke-width="2.5" />
        <path d="M276,94 L268,102 L276,110 M288,91 L282,113 M294,94 L302,102 L294,110" fill="none" stroke="#8b73dd" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" opacity="0.65" />
        <rect x="270" y="132" width="28" height="18" rx="5" fill="#ddd6fe" />
        <rect x="328" y="132" width="28" height="18" rx="5" fill="#a7f3d0" />
        <line x1="298" y1="141" x2="328" y2="141" stroke="#a78bfa" stroke-width="2.5" stroke-dasharray="3 3" />
        <!-- 面试室桌面 -->
        <rect x="0" y="325" width="400" height="135" fill="#e6def5" />
        <rect x="0" y="372" width="400" height="88" fill="#d7cce9" opacity="0.55" />
      </template>

      <!-- 图书馆 -->
      <template v-else-if="resolvedBackdrop === 'library'">
        <rect x="0" y="0" width="400" height="330" fill="#f7f2eb" />
        <!-- 拱形书架墙 -->
        <rect x="18" y="48" width="118" height="250" rx="8" fill="#efe4d6" stroke="#decbb6" stroke-width="2.5" />
        <line x1="18" y1="110" x2="136" y2="110" stroke="#decbb6" stroke-width="3" />
        <line x1="18" y1="172" x2="136" y2="172" stroke="#decbb6" stroke-width="3" />
        <line x1="18" y1="234" x2="136" y2="234" stroke="#decbb6" stroke-width="3" />
        <rect x="30" y="68" width="14" height="40" rx="2" fill="#b79ced" opacity="0.7" />
        <rect x="48" y="74" width="12" height="34" rx="2" fill="#f2c48d" opacity="0.8" />
        <rect x="64" y="66" width="16" height="42" rx="2" fill="#9bd8c1" opacity="0.75" />
        <rect x="34" y="132" width="18" height="38" rx="2" fill="#93c5fd" opacity="0.65" />
        <rect x="56" y="138" width="14" height="32" rx="2" fill="#d8b4fe" opacity="0.7" />
        <!-- 右侧台灯与书架 -->
        <rect x="264" y="58" width="118" height="240" rx="8" fill="#efe4d6" stroke="#decbb6" stroke-width="2.5" />
        <line x1="264" y1="126" x2="382" y2="126" stroke="#decbb6" stroke-width="3" />
        <line x1="264" y1="194" x2="382" y2="194" stroke="#decbb6" stroke-width="3" />
        <rect x="282" y="84" width="14" height="40" rx="2" fill="#f2c48d" opacity="0.75" />
        <rect x="300" y="80" width="16" height="44" rx="2" fill="#b79ced" opacity="0.65" />
        <path d="M324,194 L344,194 L340,174 L328,174 Z" fill="#a7f3d0" opacity="0.85" />
        <circle cx="334" cy="184" r="22" fill="#fde68a" opacity="0.22" />
        <!-- 阅览长桌 -->
        <rect x="0" y="330" width="400" height="130" fill="#e6d7c7" />
        <rect x="0" y="370" width="400" height="90" fill="#dac6b2" opacity="0.6" />
      </template>

      <!-- 公园街头 -->
      <template v-else-if="resolvedBackdrop === 'park'">
        <rect x="0" y="0" width="400" height="320" fill="#ecf9f4" />
        <!-- 柔和云朵与远景树冠 -->
        <ellipse cx="96" cy="96" rx="46" ry="20" fill="#ffffff" opacity="0.75" />
        <ellipse cx="308" cy="82" rx="52" ry="22" fill="#ffffff" opacity="0.7" />
        <circle cx="64" cy="240" r="68" fill="#bce8d5" opacity="0.6" />
        <circle cx="118" cy="256" r="52" fill="#a7dec7" opacity="0.55" />
        <circle cx="334" cy="236" r="72" fill="#bce8d5" opacity="0.6" />
        <circle cx="282" cy="258" r="48" fill="#cdeee0" opacity="0.65" />
        <!-- 路灯剪影 -->
        <line x1="316" y1="138" x2="316" y2="320" stroke="#9fc4b6" stroke-width="4" />
        <circle cx="316" cy="132" r="12" fill="#fef3c7" stroke="#9fc4b6" stroke-width="2.5" />
        <!-- 草坪与步道 -->
        <rect x="0" y="308" width="400" height="152" fill="#d7efe4" />
        <rect x="0" y="358" width="400" height="102" fill="#e6e2f2" opacity="0.7" />
      </template>

      <!-- 黄昏天台 -->
      <template v-else-if="resolvedBackdrop === 'rooftop'">
        <rect x="0" y="0" width="400" height="316" fill="#fbece8" />
        <!-- 落日余晖圆盘 -->
        <circle cx="306" cy="112" r="42" fill="#ffd5b8" opacity="0.72" />
        <circle cx="306" cy="112" r="64" fill="#ffd5b8" opacity="0.22" />
        <!-- 远景城市天际线 -->
        <rect x="18" y="206" width="44" height="110" rx="4" fill="#dfd2ec" opacity="0.75" />
        <rect x="70" y="182" width="52" height="134" rx="4" fill="#d3c2e6" opacity="0.72" />
        <rect x="276" y="194" width="48" height="122" rx="4" fill="#d7c7e8" opacity="0.75" />
        <rect x="332" y="172" width="50" height="144" rx="4" fill="#cbb9e0" opacity="0.72" />
        <!-- 天台护栏 -->
        <line x1="0" y1="302" x2="400" y2="302" stroke="#c7b5dc" stroke-width="4" />
        <line x1="48" y1="302" x2="48" y2="340" stroke="#c7b5dc" stroke-width="3" />
        <line x1="352" y1="302" x2="352" y2="340" stroke="#c7b5dc" stroke-width="3" />
        <rect x="0" y="316" width="400" height="144" fill="#e6d8ef" />
      </template>

      <!-- 温馨书房 -->
      <template v-else-if="resolvedBackdrop === 'study'">
        <rect x="0" y="0" width="400" height="325" fill="#f6f1fb" />
        <!-- 暖意挂画与窗帘 -->
        <rect x="28" y="64" width="112" height="148" rx="10" fill="#fffaf0" stroke="#ddd2ef" stroke-width="2.5" />
        <circle cx="84" cy="116" r="24" fill="#fde68a" opacity="0.55" />
        <path d="M36,192 Q68,158 102,184 Q122,172 134,192 Z" fill="#c4b5fd" opacity="0.45" />
        <!-- 右侧壁灯与备忘板 -->
        <rect x="262" y="76" width="112" height="106" rx="10" fill="#ffffff" opacity="0.72" stroke="#ddd2ef" stroke-width="2.5" />
        <rect x="278" y="94" width="38" height="28" rx="4" fill="#fef3c7" />
        <rect x="324" y="98" width="34" height="24" rx="4" fill="#ddd6fe" />
        <rect x="284" y="132" width="66" height="10" rx="5" fill="#e9e1f8" />
        <!-- 书桌 -->
        <rect x="0" y="325" width="400" height="135" fill="#eadff5" />
        <rect x="0" y="372" width="400" height="88" fill="#dcd0ec" opacity="0.6" />
      </template>

      <!-- 极简纯紫 -->
      <template v-else>
        <circle cx="316" cy="96" r="62" fill="#ffffff" opacity="0.32" />
        <circle cx="84" cy="286" r="84" fill="#dcd0f4" opacity="0.3" />
      </template>
    </svg>
    <div class="stage-top"><span class="status"><i />{{ stateLabel }}</span><span class="edition">{{ firstName.toUpperCase() }} / 01</span></div>
    <div class="halo" aria-hidden="true" />
    <span class="spark spark-one" aria-hidden="true">✦</span><span class="spark spark-two" aria-hidden="true">✧</span>
    <button class="character" type="button" :aria-label="`和 ${firstName} 打招呼`" @click="greet">
      <CharacterPortrait :character="avatar?.id || 'leo_2d'" :appearance="effectiveAppearance" :gaze="gaze" :happy="happy" :state="shownState" :lip-sync="lipSync !== 'off'" :theme="avatar?.theme || 'amber'" :name="firstName" />
    </button>
    <div class="stage-bottom"><p class="speech" role="status" aria-live="polite">{{ message }}</p></div>
  </div>
</template>

<style scoped>
.stage { position: relative; max-width: 100%; aspect-ratio: 4 / 5; overflow: hidden; border-radius: 22px; isolation: isolate; background: linear-gradient(155deg, #f7f2ee 0%, #eee7f5 56%, #ded8ed 100%); border: 1px solid #e4dceb; }
.stage.bg-cafe, .stage.char-leo_2d { background: linear-gradient(160deg, #fff8ee 0%, #f7effc 58%, #eadff7 100%); border-color: #eadfd4; }
.stage.bg-airport, .stage.char-emily_2d { background: linear-gradient(160deg, #eefcf7 0%, #eff2fc 58%, #e4dcf7 100%); border-color: #d6ebe6; }
.stage.bg-station, .stage.char-claire_2d { background: linear-gradient(160deg, #eef2ff 0%, #f5f2fc 58%, #e4ddf7 100%); border-color: #dce0f5; }
.stage.bg-meeting, .stage.char-david_2d { background: linear-gradient(160deg, #eef2ff 0%, #efeafc 58%, #e0daf5 100%); border-color: #dbe0f5; }
.stage.bg-interview, .stage.char-sarah_2d { background: linear-gradient(160deg, #f7f2ff 0%, #ede6fb 58%, #dfd4f4 100%); border-color: #e2d8f5; }
.stage.bg-library { background: linear-gradient(160deg, #fbf7f1 0%, #f4ede4 58%, #e8dccf 100%); border-color: #e6d8c8; }
.stage.bg-park { background: linear-gradient(160deg, #effcf6 0%, #e7f6f0 58%, #dceee8 100%); border-color: #d2eae0; }
.stage.bg-rooftop { background: linear-gradient(160deg, #fff1eb 0%, #f8e8ef 58%, #ead9f2 100%); border-color: #ebd8e6; }
.stage.bg-study { background: linear-gradient(160deg, #faf7ff 0%, #f2ebfb 58%, #e6dcf6 100%); border-color: #e4d9f3; }
.stage.bg-studio { background: linear-gradient(155deg, #faf8ff 0%, #eee7fb 58%, #e2d8f6 100%); border-color: #e4dceb; }
.stage.no-backdrop { background: #f5f3f8; border-color: #e4dceb; }
.scene-backdrop { position: absolute; inset: 0; width: 100%; height: 100%; z-index: 0; pointer-events: none; }
.stage-top { position: absolute; top: 22px; left: 24px; right: 24px; z-index: 2; display: flex; align-items: center; justify-content: space-between; }
.status { display: flex; align-items: center; gap: 7px; font-size: 11px; color: #5e546d; }
.status i { width: 6px; height: 6px; border-radius: 50%; background: #80a695; box-shadow: 0 0 0 4px #80a69515; }
.is-thinking .status i { background: #be9771; }.is-speaking .status i { background: #9280ba; }
.edition { font-size: 9px; letter-spacing: .18em; color: #95889f; }
.halo { position: absolute; width: 78%; aspect-ratio: 1; top: 13%; left: 11%; border-radius: 50%; background: linear-gradient(160deg, #fff9 0%, #ffffff08 100%); border: 1px solid #fff9; box-shadow: 0 0 0 18px #ffffff17; }
.character { position: absolute; bottom: 0; left: 5%; width: 90%; height: 88%; padding: 0; border: 0; background: transparent; cursor: pointer; -webkit-tap-highlight-color: transparent; }
.character:focus-visible { outline: 2px solid #8570ad; outline-offset: -12px; border-radius: 24px; }
.spark { position: absolute; z-index: 1; color: #b6a0bf; pointer-events: none; }.spark-one { top: 24%; left: 11%; font-size: 24px; }.spark-two { top: 44%; right: 12%; font-size: 20px; }
.delighted .spark { color: #9273b0; }
.stage-bottom { position: absolute; bottom: 14px; left: 18px; right: 18px; pointer-events: none; text-align: center; }
.speech { display: inline-block; margin: 0; padding: 9px 15px; max-width: 100%; border: 1px solid #ffffffb3; border-radius: 13px; background: #fffef4e6; box-shadow: 0 4px 20px #5742670a; color: #665270; font-size: 12px; line-height: 1.55; }
.interaction-hint { display: block; width: fit-content; margin: 0 auto; padding: 3px 10px; border-radius: 20px; background: #ffffffb3; font-size: 10px; color: #625672; }
@media (prefers-reduced-motion: no-preference) { .spark { animation: float 4s ease-in-out infinite; }.spark-two { animation-delay: -2s; } }
@keyframes float { 50% { transform: translateY(-5px); opacity: .65; } }
</style>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import CharacterPortrait from './CharacterPortrait.vue'

const props = defineProps({
  // 当前形象对象（api/avatar.js 的 FALLBACK_AVATARS 项）：驱动名字、主题与文案
  avatar: { type: Object, default: null },
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
const firstName = computed(() => (props.avatar?.display_name || 'Mira').split(' · ')[0])
const shownState = computed(() => demoState.value || props.state)
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
  <div class="stage" :class="[`is-${shownState}`, { 'no-backdrop': !showBackdrop, delighted: happy }]" :style="{ width: `${size}px` }" @pointermove="look" @pointerleave="gaze = { x: 0, y: 0 }">
    <div class="stage-top"><span class="status"><i />{{ stateLabel }}</span><span class="edition">{{ firstName.toUpperCase() }} / 01</span></div>
    <div class="halo" aria-hidden="true" />
    <span class="spark spark-one" aria-hidden="true">✦</span><span class="spark spark-two" aria-hidden="true">✧</span>
    <button class="character" type="button" :aria-label="`和 ${firstName} 打招呼`" @click="greet">
      <CharacterPortrait :character="avatar?.id || 'mira_2d'" :gaze="gaze" :happy="happy" :state="shownState" :lip-sync="lipSync !== 'off'" :theme="avatar?.theme || 'violet'" :name="firstName" />
    </button>
    <div class="stage-bottom"><p class="speech" role="status" aria-live="polite">{{ message }}</p></div>
  </div>
</template>

<style scoped>
.stage { position: relative; max-width: 100%; aspect-ratio: 4 / 5; overflow: hidden; border-radius: 22px; isolation: isolate; background: linear-gradient(155deg, #f7f2ee 0%, #eee7f5 56%, #ded8ed 100%); border: 1px solid #e4dceb; }
.stage.no-backdrop { background: #f5f3f8; }
.stage-top { position: absolute; top: 22px; left: 24px; right: 24px; z-index: 2; display: flex; align-items: center; justify-content: space-between; }
.status { display: flex; align-items: center; gap: 7px; font-size: 11px; color: #5e546d; }
.status i { width: 6px; height: 6px; border-radius: 50%; background: #80a695; box-shadow: 0 0 0 4px #80a69515; }
.is-thinking .status i { background: #be9771; }.is-speaking .status i { background: #9280ba; }
.edition { font-size: 9px; letter-spacing: .18em; color: #95889f; }
.halo { position: absolute; width: 82%; aspect-ratio: 1; top: 17%; left: 9%; border-radius: 50%; background: linear-gradient(160deg, #fff9 0%, #ffffff08 100%); border: 1px solid #fff9; box-shadow: 0 0 0 18px #ffffff17; }
.character { position: absolute; bottom: 0; left: 5%; width: 90%; height: 94%; padding: 0; border: 0; background: transparent; cursor: pointer; -webkit-tap-highlight-color: transparent; }
.character:focus-visible { outline: 2px solid #8570ad; outline-offset: -12px; border-radius: 24px; }
.spark { position: absolute; z-index: 1; color: #b6a0bf; pointer-events: none; }.spark-one { top: 29%; left: 12%; font-size: 24px; }.spark-two { top: 49%; right: 13%; font-size: 20px; }
.delighted .spark { color: #9273b0; }
.stage-bottom { position: absolute; bottom: 17px; left: 18px; right: 18px; pointer-events: none; text-align: center; }
.speech { display: inline-block; margin: 0 0 9px; padding: 10px 16px; max-width: 100%; border: 1px solid #ffffffb3; border-radius: 13px; background: #fffef4e6; box-shadow: 0 4px 20px #5742670a; color: #665270; font-size: 12px; line-height: 1.6; }
.interaction-hint { display: block; width: fit-content; margin: 0 auto; padding: 3px 10px; border-radius: 20px; background: #ffffffb3; font-size: 10px; color: #625672; }
@media (prefers-reduced-motion: no-preference) { .spark { animation: float 4s ease-in-out infinite; }.spark-two { animation-delay: -2s; } }
@keyframes float { 50% { transform: translateY(-5px); opacity: .65; } }
</style>

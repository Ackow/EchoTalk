<template>
  <Teleport to="body">
    <div
      v-if="popover.open"
      ref="cardEl"
      class="lookup-popover"
      role="dialog"
      aria-label="划词解释与朗读"
      :style="{ left: `${popover.left}px`, top: `${popover.top}px` }"
      @mousedown.stop
    >
      <div class="lookup-head">
        <div class="lookup-term">
          <b>{{ popover.text }}</b>
          <span v-if="popover.phonetic" class="lookup-phonetic">{{ popover.phonetic }}</span>
        </div>
        <div class="lookup-tools">
          <button
            class="lookup-icon-btn"
            type="button"
            :class="{ active: audioBusy }"
            title="朗读发音"
            aria-label="朗读发音"
            @click="playAudio"
          >
            <AppIcon name="volume" :size="14" />
          </button>
          <button
            v-if="signedIn"
            class="lookup-icon-btn"
            type="button"
            :class="{ saved: popover.saved }"
            :disabled="popover.saved || saving"
            :title="popover.saved ? '已加入复习计划' : '加入复习计划'"
            aria-label="加入复习计划"
            @click="saveToReview"
          >
            <AppIcon :name="popover.saved ? 'check' : 'plus'" :size="14" />
          </button>
          <button class="lookup-close-btn" type="button" aria-label="关闭" @click="close">
            <AppIcon name="x" :size="13" />
          </button>
        </div>
      </div>
      <div v-if="popover.loading" class="lookup-loading">
        <span class="sk-line w70"></span>
        <span class="sk-line w40"></span>
      </div>
      <template v-else>
        <p class="lookup-trans">{{ popover.translation }}</p>
        <p v-if="popover.tip" class="lookup-tip">{{ popover.tip }}</p>
      </template>
    </div>
  </Teleport>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import AppIcon from '../AppIcon.vue'
import { explainSelection } from '../../api/speech'
import { synthesizeSpeech } from '../../api/avatar'
import { createReviewItem } from '../../api/review'

const props = defineProps({
  voiceStyle: { type: String, default: '' },
  sceneName: { type: String, default: '' },
  signedIn: { type: Boolean, default: false },
})

const cardEl = ref(null)
const popover = ref({
  open: false,
  text: '',
  context: '',
  phonetic: '',
  translation: '',
  tip: '',
  loading: false,
  saved: false,
  left: 0,
  top: 0,
})
const audioBusy = ref(false)
const saving = ref(false)
const explainCache = new Map()
const audioCache = new Map()
let activeAudio = null
let reqSeq = 0

function close() {
  reqSeq += 1
  if (activeAudio) {
    activeAudio.pause()
    activeAudio.onended = activeAudio.onerror = null
    activeAudio = null
  }
  audioBusy.value = false
  popover.value.open = false
}

async function handleSelection(containerEl) {
  const sel = window.getSelection?.()
  if (!sel || sel.isCollapsed) return
  const raw = sel.toString().replace(/\s+/g, ' ').trim()
  if (!raw || raw.length > 180 || !/[a-zA-Z]/.test(raw)) return
  const range = sel.rangeCount ? sel.getRangeAt(0) : null
  if (!range || !containerEl?.contains(range.commonAncestorContainer)) return
  const bubbleEl = range.commonAncestorContainer.nodeType === 1
    ? range.commonAncestorContainer.closest?.('.bubble-text')
    : range.commonAncestorContainer.parentElement?.closest?.('.bubble-text')
  if (!bubbleEl) return

  const rect = range.getBoundingClientRect()
  if (!rect.width && !rect.height) return

  const cardW = 310
  const left = Math.max(12, Math.min(window.innerWidth - cardW - 12, rect.left + rect.width / 2 - cardW / 2))
  const placeAbove = rect.top > 180
  const top = placeAbove ? rect.top - 10 : rect.bottom + 10
  const context = (bubbleEl.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 400)
  const cacheKey = `${raw}::${context}`
  const seq = ++reqSeq

  popover.value = {
    open: true,
    text: raw,
    context,
    phonetic: '',
    translation: '',
    tip: '',
    loading: true,
    saved: false,
    left,
    top: placeAbove ? Math.max(12, top - 118) : Math.min(window.innerHeight - 160, top),
  }

  if (explainCache.has(cacheKey)) {
    popover.value = { ...popover.value, ...explainCache.get(cacheKey), loading: false }
    return
  }

  try {
    const { data } = await explainSelection(raw, context)
    if (seq !== reqSeq) return
    const result = {
      phonetic: data?.phonetic || '',
      translation: data?.translation || '暂无释义',
      tip: data?.tip || '',
    }
    explainCache.set(cacheKey, result)
    popover.value = { ...popover.value, ...result, loading: false }
  } catch {
    if (seq !== reqSeq) return
    popover.value = {
      ...popover.value,
      translation: props.signedIn ? '解释加载失败，可点击右侧朗读听发音。' : '登录后可使用划词翻译，当前可点击右侧朗读听发音。',
      loading: false,
    }
  }
}

async function playAudio() {
  const text = popover.value.text
  if (!text) return
  if (audioBusy.value && activeAudio) {
    activeAudio.pause()
    activeAudio = null
    audioBusy.value = false
    return
  }
  audioBusy.value = true
  const cacheKey = `${text}::${props.voiceStyle || ''}`
  try {
    let url = audioCache.get(cacheKey)
    if (!url) {
      const blob = await synthesizeSpeech(text, props.voiceStyle || undefined, 0.92)
      url = URL.createObjectURL(blob)
      audioCache.set(cacheKey, url)
    }
    const audio = new Audio(url)
    activeAudio = audio
    audio.onended = audio.onerror = () => {
      if (activeAudio === audio) activeAudio = null
      audioBusy.value = false
    }
    await audio.play()
  } catch {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      const utter = new SpeechSynthesisUtterance(text)
      utter.lang = 'en-US'
      utter.rate = 0.92
      utter.onend = utter.onerror = () => { audioBusy.value = false }
      window.speechSynthesis.speak(utter)
    } else {
      audioBusy.value = false
    }
  }
}

async function saveToReview() {
  if (!props.signedIn || popover.value.saved || saving.value) return
  saving.value = true
  try {
    await createReviewItem({
      kind: 'expression',
      prompt: popover.value.translation || `掌握表达：${popover.value.text}`,
      answer: popover.value.text,
      phonetic: popover.value.phonetic || '',
      note: popover.value.tip || '',
      context_text: popover.value.context ? `原句：${popover.value.context}` : '',
      scene_name: props.sceneName || '',
    })
    popover.value.saved = true
  } catch {
    // 保持按钮可重试
  } finally {
    saving.value = false
  }
}

function onGlobalMouseDown(e) {
  if (!popover.value.open) return
  if (cardEl.value?.contains(e.target)) return
  close()
}
function onGlobalKeyDown(e) {
  if (e.key === 'Escape' && popover.value.open) close()
}

onMounted(() => {
  window.addEventListener('mousedown', onGlobalMouseDown)
  window.addEventListener('keydown', onGlobalKeyDown)
})
onBeforeUnmount(() => {
  window.removeEventListener('mousedown', onGlobalMouseDown)
  window.removeEventListener('keydown', onGlobalKeyDown)
  close()
  for (const url of audioCache.values()) URL.revokeObjectURL(url)
  audioCache.clear()
})

defineExpose({ handleSelection, close })
</script>

<style scoped>
.lookup-popover {
  position: fixed; z-index: 50; width: 310px; max-width: calc(100vw - 24px);
  padding: 12px 14px; border: 1.5px solid #dfd7f4; border-bottom: 4px solid #d1c6ee;
  border-radius: 14px; background: #fff; box-shadow: 0 14px 36px rgba(42, 34, 72, .16);
}
.lookup-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; margin-bottom: 8px; }
.lookup-term { min-width: 0; }
.lookup-term b { display: block; font-size: 14px; font-weight: 700; color: #2d294b; line-height: 1.35; word-break: break-word; }
.lookup-phonetic { display: inline-block; margin-top: 2px; font-size: 12px; color: #7c62d2; }
.lookup-tools { display: flex; align-items: center; gap: 4px; flex: 0 0 auto; }
.lookup-icon-btn, .lookup-close-btn {
  display: grid; place-items: center; width: 26px; height: 26px;
  border: 1px solid #e6e0f5; border-radius: 8px; background: #faf8ff; color: #6b52c1;
}
.lookup-icon-btn:hover:not(:disabled), .lookup-icon-btn.active { background: #efe9ff; border-color: #cabdf2; }
.lookup-icon-btn.saved { background: #e8f8f0; border-color: #bce4cf; color: #257a55; }
.lookup-close-btn { border-color: transparent; background: transparent; color: #8c86a3; }
.lookup-close-btn:hover { background: #f3f1f9; color: #2d294b; }
.lookup-loading { display: flex; flex-direction: column; gap: 7px; padding: 2px 0; }
.sk-line { height: 12px; border-radius: 5px; background: linear-gradient(90deg, #eef0f5 25%, #f6f7fa 45%, #eef0f5 65%); background-size: 200% 100%; animation: shimmer 1.3s infinite; }
.sk-line.w40 { width: 40%; }
.sk-line.w70 { width: 70%; }
@keyframes shimmer { from { background-position: 200% 0; } to { background-position: -200% 0; } }
.lookup-trans { margin: 0; font-size: 13.5px; line-height: 1.55; color: #2d294b; font-weight: 500; }
.lookup-tip { margin: 6px 0 0; padding-top: 6px; border-top: 1px dashed #ebe6f7; font-size: 12px; line-height: 1.5; color: #6e6885; }
</style>

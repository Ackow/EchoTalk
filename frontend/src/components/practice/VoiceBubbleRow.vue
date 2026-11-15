<template>
  <div class="voice-bubble-item" :class="{ 'is-user': isUser }">
    <!-- 纯文字用户输入（非语音） -->
    <div v-if="isUser && !isVoice" class="bubble">
      <p class="bubble-text">{{ text }}</p>
    </div>

    <!-- 主音频胶囊 + 原文/收起折叠面板（对话与辩论统一复用） -->
    <template v-else>
      <div class="bubble-row" :class="{ 'is-user-voice': isUser }">
        <button
          v-if="isUser && !showOriginal"
          class="original-toggle"
          type="button"
          :aria-expanded="expanded"
          @click="$emit('toggle-original', $event)"
        >
          <AppIcon name="file-text" :size="13" />
          {{ expanded ? '收起' : '原文' }}
        </button>

        <button
          class="ai-voice-capsule"
          :class="[
            role,
            {
              'user-voice-capsule': isUser,
              playing,
              'is-busy': busy,
              'is-static': isStatic,
            },
          ]"
          :style="{ width: computedWidth }"
          type="button"
          :disabled="busy"
          :aria-label="playAriaLabel || (playing ? '停止播放语音' : '播放语音')"
          @click="$emit('toggle-play')"
        >
          <i
            v-if="playing"
            class="capsule-progress"
            :style="{ width: `${Math.min(100, Math.max(0, progress))}%` }"
            aria-hidden="true"
          ></i>
          <span v-if="busy" class="tts-bars" aria-hidden="true"><i /><i /><i /></span>
          <svg
            v-else
            class="voice-wave-icon"
            width="16"
            height="18"
            viewBox="0 0 16 18"
            fill="none"
            aria-hidden="true"
          >
            <circle cx="3" cy="9" r="1.35" fill="currentColor" />
            <path
              d="M6 5.8a4.5 4.5 0 0 1 0 6.4M8.5 3.3a8 8 0 0 1 0 11.4"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
            />
          </svg>
          <span class="capsule-duration">{{ durationLabel }}</span>
        </button>

        <button
          v-if="!isUser && !showOriginal"
          class="original-toggle"
          type="button"
          :aria-expanded="expanded"
          @click="$emit('toggle-original', $event)"
        >
          <AppIcon name="file-text" :size="13" />
          {{ expanded ? '收起' : '原文' }}
        </button>
      </div>

      <transition
        name="panel"
        @enter="onPanelEnter"
        @after-enter="onPanelAfterEnter"
        @leave="onPanelLeave"
        @after-leave="onPanelAfterLeave"
      >
        <div
          v-show="(showOriginal || expanded) && text.trim()"
          class="original-panel"
          :class="{ 'is-user': isUser }"
        >
          <div v-if="htmlText" class="bubble-text md-body" v-html="htmlText" />
          <p v-else class="bubble-text">{{ text }}</p>
          <p v-if="zhText" class="bubble-zh">{{ zhText }}</p>
        </div>
      </transition>
    </template>

    <slot name="after-bubble" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  role: { type: String, default: 'agent' },
  isUser: { type: Boolean, default: false },
  isVoice: { type: Boolean, default: true },
  text: { type: String, default: '' },
  zhText: { type: String, default: '' },
  htmlText: { type: String, default: '' },
  duration: { type: Number, default: 0 },
  capsuleWidth: { type: String, default: '' },
  playing: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
  isStatic: { type: Boolean, default: false },
  progress: { type: Number, default: 0 },
  showOriginal: { type: Boolean, default: false },
  expanded: { type: Boolean, default: false },
  playAriaLabel: { type: String, default: '' },
})

defineEmits(['toggle-play', 'toggle-original'])

function estimateSec(str) {
  const words = String(str || '').trim().split(/\s+/).filter(Boolean).length
  return Math.max(3, Math.round(words / 2.4))
}

const durationSeconds = computed(() => {
  if (props.duration) return Math.max(1, Math.ceil(props.duration))
  return estimateSec(props.text)
})

const computedWidth = computed(() => {
  if (props.capsuleWidth) return props.capsuleWidth
  return `${Math.min(320, Math.max(120, 110 + durationSeconds.value * 9))}px`
})

const durationLabel = computed(() => {
  if (props.busy) return '语音合成中…'
  return `${durationSeconds.value}"`
})

function onPanelEnter(el) {
  el.style.height = '0px'
  el.style.opacity = '0'
  void el.offsetHeight
  el.style.height = `${el.scrollHeight}px`
  el.style.opacity = '1'
}
function onPanelAfterEnter(el) {
  el.style.height = ''
  el.style.opacity = ''
}
function onPanelLeave(el) {
  el.style.height = `${el.scrollHeight}px`
  el.style.opacity = '1'
  void el.offsetHeight
  el.style.height = '0px'
  el.style.opacity = '0'
}
function onPanelAfterLeave(el) {
  el.style.height = ''
  el.style.opacity = ''
}
</script>

<style scoped>
.voice-bubble-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  max-width: 100%;
}

.voice-bubble-item.is-user {
  align-items: flex-end;
}

.bubble {
  padding: 11px 15px;
  background: white;
  border: 1px solid #ededf3;
  border-radius: 4px 15px 15px 15px;
}

.voice-bubble-item.is-user .bubble {
  background: #e4e2ff;
  border-color: #dedbfc;
  color: #37365e;
  border-radius: 15px 4px 15px 15px;
}

.bubble-text {
  margin: 0;
  font-size: 14px;
  line-height: 1.75;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  color: #2d294b;
}

.bubble-zh {
  margin: 6px 0 0;
  font-size: 12.5px;
  line-height: 1.55;
  color: #6f6a84;
}

.bubble-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ai-voice-capsule {
  position: relative;
  display: flex;
  align-items: center;
  gap: 5px;
  height: 40px;
  min-width: 120px;
  max-width: 100%;
  padding: 0 12px;
  border: 1.5px solid #eae6f2;
  border-bottom: 3px solid #e4dfec;
  border-radius: 5px 16px 16px 16px;
  background: white;
  color: #694ec0;
  overflow: hidden;
  transition: width 0.2s ease, background 0.15s, transform 0.15s;
}

.ai-voice-capsule:hover:not(:disabled) {
  background: #f6f2ff;
  transform: scale(1.02);
}

.ai-voice-capsule:active:not(:disabled) {
  transform: scale(0.98);
}

.ai-voice-capsule:disabled {
  opacity: 0.7;
  cursor: wait;
}

.ai-voice-capsule.playing {
  background: white;
}

.ai-voice-capsule.opponent {
  border-color: #f2d5cd;
  border-bottom-color: #e4bdb2;
  color: #b84a39;
}

.ai-voice-capsule.judge {
  border-color: #cce7d8;
  border-bottom-color: #b1d9c3;
  color: #248256;
}

.ai-voice-capsule.user-voice-capsule {
  flex-direction: row-reverse;
  border-color: #d9d0f8;
  border-bottom-color: #c8bbef;
  border-radius: 16px 5px 16px 16px;
  background: #eee9ff;
  color: #4e3b94;
}

.ai-voice-capsule.user-voice-capsule:hover:not(:disabled) {
  background: #e6deff;
}

.ai-voice-capsule.user-voice-capsule .voice-wave-icon {
  transform: scaleX(-1);
}

.ai-voice-capsule.user-voice-capsule .capsule-progress {
  left: auto;
  right: 0;
}

.ai-voice-capsule.user-voice-capsule.is-static {
  opacity: 0.92;
}

.capsule-progress {
  position: absolute;
  left: 0;
  bottom: 0;
  height: 3px;
  background: #8b73dd;
  transition: width 0.12s linear;
}

.ai-voice-capsule.user-voice-capsule .capsule-progress {
  background: rgba(115, 87, 204, 0.28);
}

.capsule-duration {
  font-size: 12.5px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.voice-wave-icon {
  flex: 0 0 auto;
}

.ai-voice-capsule.is-busy {
  border-color: #c8bbf0;
  background: linear-gradient(90deg, #faf8ff 0%, #f1ebff 50%, #faf8ff 100%);
  background-size: 200% 100%;
  animation: tts-shimmer 1.6s ease-in-out infinite;
}

.tts-bars {
  display: inline-flex;
  align-items: center;
  gap: 2.5px;
  height: 14px;
}

.tts-bars i {
  width: 2.5px;
  height: 6px;
  border-radius: 999px;
  background: #7b61ff;
  animation: tts-bar 0.9s ease-in-out infinite;
}

.tts-bars i:nth-child(2) { animation-delay: 0.15s; }
.tts-bars i:nth-child(3) { animation-delay: 0.3s; }

@keyframes tts-bar {
  0%, 100% { height: 5px; opacity: 0.55; }
  50% { height: 14px; opacity: 1; }
}

@keyframes tts-shimmer {
  0% { background-position: 100% 0; }
  100% { background-position: -100% 0; }
}

.original-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  border: 1.5px solid #e6e3f2;
  border-bottom: 3px solid #dad4ec;
  border-radius: 999px;
  background: #fff;
  color: #6b6485;
  font-size: 12px;
  font-weight: 650;
  transition: color 0.15s, border-color 0.15s;
  white-space: nowrap;
}

.original-toggle:hover {
  color: #5b43b0;
  border-color: #c9bdf0;
}

.original-panel {
  max-width: 100%;
  margin-top: 7px;
  padding: 11px 15px;
  border: 1px solid #ededf3;
  border-radius: 4px 15px 15px 15px;
  background: #fff;
}

.original-panel.is-user {
  border-color: #eae6f2;
  background: #fff;
  color: #393451;
  border-radius: 15px 4px 15px 15px;
  text-align: left;
}

.panel-enter-active,
.panel-leave-active {
  transition: height 0.22s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.18s ease, margin-top 0.22s cubic-bezier(0.22, 1, 0.36, 1), padding-top 0.22s cubic-bezier(0.22, 1, 0.36, 1), padding-bottom 0.22s cubic-bezier(0.22, 1, 0.36, 1);
  overflow: hidden;
}

.md-body {
  white-space: normal;
}
.md-body :deep(p) { margin: 0 0 6px; }
.md-body :deep(p:last-child) { margin-bottom: 0; }
.md-body :deep(strong) { font-weight: 700; color: #2d294b; }
</style>

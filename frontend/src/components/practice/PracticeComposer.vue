<template>
  <footer class="composer-area">
    <p v-if="playbackNotice" class="playback-notice" role="status"><AppIcon name="volume" :size="13" />{{ playbackNotice }}</p>
    <p v-if="error" class="chat-error" role="alert"><AppIcon name="alert" :size="14" />{{ error }}</p>

    <!-- AI 帮助回复建议条 -->
    <div v-if="replySuggestions.length" class="ai-suggest-tray" role="region" aria-label="AI 参考回复">
      <div class="ai-suggest-head">
        <span><AppIcon name="sparkles" :size="13" />AI 参考回复（点击填入，可编辑或朗读）</span>
        <div class="ai-suggest-actions">
          <button type="button" class="ai-mini-btn" :disabled="suggesting" @click="emit('request-assist')">{{ suggesting ? '生成中…' : '换一批' }}</button>
          <button type="button" class="ai-mini-close" title="关闭" @click="emit('clear-suggestions')"><AppIcon name="x" :size="13" /></button>
        </div>
      </div>
      <div class="ai-suggest-list">
        <button
          v-for="(item, idx) in replySuggestions"
          :key="idx"
          type="button"
          class="ai-suggest-chip"
          @click="emit('apply-suggestion', item.en)"
        >
          <b>{{ item.en }}</b>
          <span v-if="item.zh">{{ item.zh }}</span>
        </button>
      </div>
    </div>

    <!-- 语音优先：单行紧凑条，待机 / 录音中 / 转写确认三态共用 .composer 外壳 -->
    <template v-if="inputMode === 'voice'">
      <div v-if="transcribedText" class="composer voice-result is-staged" role="status">
        <button
          type="button"
          class="ai-voice-capsule user-voice-capsule staged-capsule"
          :class="{ playing: playingKey === '__pending__' }"
          @click="playingKey === '__pending__' ? emit('stop-audio') : emit('play-pending')"
        >
          <i v-if="playingKey === '__pending__'" class="capsule-progress" :style="{ width: `${Math.min(100, playbackTime / (playbackDuration || pendingVoiceDuration || 2) * 100)}%` }" aria-hidden="true"></i>
          <svg class="voice-wave-icon" width="16" height="18" viewBox="0 0 16 18" fill="none" aria-hidden="true"><circle cx="3" cy="9" r="1.35" fill="currentColor"/><path d="M6 5.8a4.5 4.5 0 0 1 0 6.4M8.5 3.3a8 8 0 0 1 0 11.4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
          <span class="capsule-duration">{{ playingKey === '__pending__' ? '试听中…' : `试听 ${Math.max(1, Math.ceil(pendingVoiceDuration || estimateSeconds(transcribedText)))}"` }}</span>
        </button>
        <div class="voice-result-actions">
          <button class="icon-button" type="button" title="重新录制" :disabled="voiceBusy" @click="emit('retry-recording')"><AppIcon name="rotate" :size="15" /></button>
          <button class="icon-button" type="button" title="放弃录音" :disabled="voiceBusy" @click="emit('discard-pending')"><AppIcon name="x" :size="15" /></button>
          <button class="send-button" type="button" :disabled="sending || finished" @click="emit('send-transcribed')">
            <span v-if="sending" class="ui-spinner send-spinner" aria-hidden="true" />
            <AppIcon v-else name="send" :size="14" />
            <span>{{ sending ? '发送中' : '发送' }}</span>
          </button>
        </div>
      </div>

      <div v-else-if="voiceBusy" class="composer voice-bar live" role="status" aria-live="polite">
        <button v-if="voiceStatus === 'recording'" class="mic-orb stop" type="button" title="结束并转写" @click="emit('stop-recording')"><AppIcon name="square" :size="15" /><i class="orb-pulse" aria-hidden="true"></i></button>
        <span v-else class="mic-orb static"><span class="ui-spinner" aria-hidden="true" /></span>
        <div class="voice-bar-info">
          <b>{{ voiceStatusLabel }}<template v-if="voiceStatus === 'recording'"> · {{ String(recordingSeconds).padStart(2, '0') }} / 60 秒</template></b>
          <span v-if="voiceStatus === 'recording'" class="live-hint">说英语，点左侧按钮结束<span class="live-wave" aria-hidden="true"><i v-for="n in 7" :key="n" :style="{ height: levelBar(n - 1) }"></i></span></span>
          <span v-else>{{ voiceStatus === 'transcribing' ? '正在识别，请稍候…' : '正在整理录音…' }}</span>
        </div>
        <button class="icon-button" type="button" :disabled="voiceStatus === 'transcribing'" title="取消录音" @click="emit('cancel-recording')"><AppIcon name="x" :size="15" /></button>
      </div>

      <div v-else class="composer voice-bar idle">
        <button
          class="voice-trigger"
          type="button"
          :disabled="sending || finished || asrAvailable === false || !recordingSupported"
          :title="voiceCtaText"
          aria-label="开始语音输入"
          @click="emit('start-recording')"
        >
          <span class="mic-orb" aria-hidden="true"><AppIcon name="mic" :size="17" /><i class="orb-ring"></i></span>
          <span class="voice-bar-info">
            <b>{{ voiceCtaText }}</b>
            <span>{{ voiceHintText }}</span>
          </span>
        </button>
        <button class="foot-toggle in-bar" type="button" :disabled="sending || finished || suggesting" @click="emit('request-assist')">
          <span v-if="suggesting" class="ui-spinner" aria-hidden="true" />
          <AppIcon v-else name="sparkles" :size="13" />
          <span>{{ suggesting ? '思考中…' : 'AI 帮回复' }}</span>
        </button>
        <button class="foot-toggle in-bar" type="button" :disabled="voiceBusy" @click="emit('toggle-input-mode')"><AppIcon name="pencil" :size="13" />文字输入</button>
      </div>

      <div v-if="voiceBusy || transcribedText" class="composer-foot">
        <span>{{ voiceHintText }}</span>
        <button class="foot-toggle" type="button" :disabled="voiceBusy" @click="emit('toggle-input-mode')"><AppIcon name="pencil" :size="12" />改用文字输入</button>
      </div>
    </template>

    <!-- 文字模式 -->
    <template v-else>
      <div class="composer">
        <textarea
          ref="composerBox"
          :value="draft"
          class="composer-input"
          rows="2"
          maxlength="4000"
          :disabled="sending || finished"
          :placeholder="finished ? '本次练习已结束' : '用英语写下你的回答…'"
          aria-label="你的英语回答"
          @keydown.enter.exact="handleEnter"
          @input="onInput"
        ></textarea>
        <button class="icon-button" type="button" title="改用语音输入" :disabled="voiceBusy" @click="emit('toggle-input-mode')"><AppIcon name="mic" :size="15" /></button>
        <button class="send-button" type="button" :disabled="sending || finished || !draft.trim()" @click="emit('send-turn')">
          <span v-if="sending" class="ui-spinner send-spinner" aria-hidden="true" />
          <AppIcon v-else name="arrow-right" :size="18" />
          <span>{{ sending ? '发送中' : '发送' }}</span>
        </button>
      </div>
      <div class="composer-foot">
        <span class="keyboard-hint"><kbd>Enter</kbd> 发送<span>·</span><kbd>Shift + Enter</kbd> 换行</span>
        <button class="foot-toggle in-bar ai-assist-btn" type="button" :disabled="sending || finished || suggesting" title="让 AI 帮你生成参考回复" @click="emit('request-assist')">
          <span v-if="suggesting" class="ui-spinner" aria-hidden="true" />
          <AppIcon v-else name="sparkles" :size="13" />
          <span>{{ suggesting ? '生成中…' : 'AI 帮回复' }}</span>
        </button>
      </div>
    </template>
  </footer>
</template>

<script setup>
import { nextTick, ref } from 'vue'
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  playbackNotice: { type: String, default: '' },
  error: { type: String, default: '' },
  replySuggestions: { type: Array, default: () => [] },
  suggesting: { type: Boolean, default: false },
  inputMode: { type: String, default: 'voice' },
  transcribedText: { type: String, default: '' },
  playingKey: { type: String, default: '' },
  playbackTime: { type: Number, default: 0 },
  playbackDuration: { type: Number, default: 0 },
  pendingVoiceDuration: { type: Number, default: 0 },
  voiceBusy: { type: Boolean, default: false },
  voiceStatus: { type: String, default: 'idle' },
  voiceStatusLabel: { type: String, default: '' },
  recordingSeconds: { type: Number, default: 0 },
  recordingLevel: { type: Number, default: 0 },
  sending: { type: Boolean, default: false },
  finished: { type: Boolean, default: false },
  asrAvailable: { type: Boolean, default: null },
  recordingSupported: { type: Boolean, default: true },
  voiceCtaText: { type: String, default: '' },
  voiceHintText: { type: String, default: '' },
  draft: { type: String, default: '' },
})

const emit = defineEmits([
  'request-assist',
  'clear-suggestions',
  'apply-suggestion',
  'play-pending',
  'stop-audio',
  'retry-recording',
  'discard-pending',
  'send-transcribed',
  'stop-recording',
  'cancel-recording',
  'start-recording',
  'toggle-input-mode',
  'update:draft',
  'send-turn',
])

const composerBox = ref(null)

function estimateSeconds(text) {
  const words = (text || '').trim().split(/\s+/).filter(Boolean).length
  return Math.max(2, Math.round(words / 2))
}

function levelBar(index) {
  const scale = [0.45, 0.72, 1, 0.85, 0.95, 0.62, 0.4][index] || 0.5
  return `${Math.round(4 + props.recordingLevel * 11 * scale)}px`
}

function onInput(event) {
  const box = event.target
  emit('update:draft', box.value)
  box.style.height = 'auto'
  box.style.height = `${Math.min(box.scrollHeight, 132)}px`
}

function handleEnter(event) {
  if (event.shiftKey || event.isComposing) return
  event.preventDefault()
  emit('send-turn')
}

async function focusInput() {
  await nextTick()
  const box = composerBox.value
  if (box) {
    box.style.height = 'auto'
    box.style.height = `${Math.min(box.scrollHeight, 132)}px`
    box.focus()
  }
}

function resetHeight() {
  if (composerBox.value) composerBox.value.style.height = 'auto'
}

defineExpose({ focusInput, resetHeight })
</script>

<style scoped>
.composer-area { flex-shrink: 0; margin: 0 20px; padding: 13px 0 12px; border-top: 1px solid var(--line); }
.composer { display: flex; align-items: flex-end; gap: 10px; padding: 10px; border: 1.5px solid #eae6f2; border-bottom-width: 3px; border-radius: 16px; background: #fff; transition: border-color .15s; }
.composer:focus-within { border-color: #b5a4e9; }
.composer-input { display: block; flex: 1; min-width: 0; min-height: 42px; max-height: 132px; padding: 0 3px; outline: none; border: 0; resize: none; background: transparent; font: inherit; font-size: 14.5px; line-height: 1.7; color: #2d294b; }
.composer-input::placeholder { color: #9c96b2; }
.send-button { display: flex; align-items: center; justify-content: center; gap: 5px; height: 36px; padding: 0 15px; border: 1.5px solid #7960cc; border-bottom: 4px solid #6349b4; border-radius: 11px; color: white; background: #8b73dd; font-size: 13px; font-weight: 700; transition: background .15s, transform .12s; }
.send-button:hover:not(:disabled) { background: #7d64d1; transform: translateY(-1px); }
.send-button:active:not(:disabled) { transform: translateY(1px); border-bottom-width: 2px; }
.send-button:disabled { opacity: .5; cursor: not-allowed; }
.composer-foot { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 7px; margin-top: 9px; color: #7c7693; font-size: 11.5px; }
.keyboard-hint { display: flex; align-items: center; gap: 5px; }
.keyboard-hint > span { margin: 0 3px; }
kbd { font-family: inherit; font-size: 10.5px; }
.chat-error { display: flex; align-items: center; gap: 5px; margin: 0 0 10px; color: var(--danger); font-size: 13px; }
.ui-spinner { width: 13px; height: 13px; border-radius: 50%; flex: 0 0 auto; border: 2px solid rgba(105, 78, 192, 0.22); border-top-color: #694ec0; animation: spin .72s linear infinite; }
.send-spinner { width: 14px; height: 14px; border-color: rgba(255, 255, 255, 0.34); border-top-color: #fff; }
.ai-voice-capsule { position: relative; display: flex; align-items: center; gap: 5px; height: 40px; min-width: 120px; max-width: 100%; padding: 0 12px; border: 1.5px solid #d9d0f8; border-bottom: 3px solid #c8bbef; border-radius: 999px; background: #eee9ff; color: #4e3b94; overflow: hidden; transition: width .2s ease, background .15s, transform .15s; }
.ai-voice-capsule:hover:not(:disabled) { background: #e6deff; transform: scale(1.02); }
.capsule-progress { position: absolute; left: 0; bottom: 0; height: 3px; background: #8b73dd; transition: width .12s linear; }
.capsule-duration { font-size: 12.5px; font-weight: 700; font-variant-numeric: tabular-nums; white-space: nowrap; }
.voice-wave-icon { flex: 0 0 auto; }
.playback-notice { display: flex; align-items: flex-start; gap: 6px; margin: 0 0 10px; color: var(--muted); font-size: 12px; line-height: 1.7; }
.voice-bar { position: relative; align-items: center; gap: 12px; min-height: 62px; }
.voice-bar.idle { justify-content: space-between; padding: 8px 12px 8px 8px; }
.voice-trigger { display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0; padding: 4px 10px 4px 4px; border: 0; border-radius: 13px; background: transparent; text-align: left; transition: background .15s; }
.voice-trigger:hover:not(:disabled) { background: #f6f2ff; }
.voice-trigger:hover:not(:disabled) .mic-orb { background: #7d64d1; transform: translateY(-1px) scale(1.03); }
.voice-trigger:active:not(:disabled) .mic-orb { transform: translateY(1px) scale(.97); border-bottom-width: 2px; }
.voice-trigger:hover:not(:disabled) .voice-bar-info b { color: #5b43b0; }
.voice-trigger:disabled { opacity: .65; cursor: not-allowed; }
.voice-trigger:disabled .mic-orb { background: #c9cbea; border-color: #b8badc; border-bottom-color: #a6a9cd; }
.voice-bar.live { border-color: #e0d8f5; background: #faf8ff; }
.mic-orb { position: relative; display: grid; place-items: center; width: 44px; height: 44px; flex: 0 0 44px; border: 2px solid #7358c8; border-bottom: 4px solid #593ea8; border-radius: 50%; background: #8b73dd; color: #fff; box-shadow: inset 0 2px 0 rgba(255, 255, 255, .25); transition: background .15s, transform .12s; }
.mic-orb:hover:not(:disabled) { background: #7d64d1; transform: translateY(-1px) scale(1.03); }
.mic-orb:active:not(:disabled) { transform: translateY(1px) scale(.97); border-bottom-width: 2px; }
.mic-orb:disabled { background: #c9cbea; border-color: #b8badc; border-bottom-color: #a6a9cd; cursor: not-allowed; }
.mic-orb.stop { background: var(--danger); border-color: #a13a4b; border-bottom-color: #842b3a; }
.mic-orb.static { background: #e3e2f4; border: 0; color: var(--brand-deep); animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.orb-ring { position: absolute; inset: -5px; border: 1.5px solid rgba(98, 101, 232, .3); border-radius: 50%; animation: orb-breathe 2.2s ease-in-out infinite; }
@keyframes orb-breathe { 50% { transform: scale(1.14); opacity: .35; } }
.orb-pulse { position: absolute; inset: -4px; border: 2px solid var(--danger); border-radius: 50%; animation: voice-ping 1.2s ease-out infinite; }
@keyframes voice-ping { from { opacity: .8; transform: scale(.9); } to { opacity: 0; transform: scale(1.3); } }
.voice-bar-info { display: flex; min-width: 0; flex: 1; flex-direction: column; align-items: flex-start; gap: 3px; border: 0; background: transparent; text-align: left; }
.voice-bar-info b { font-size: 14px; font-weight: 600; color: var(--ink); font-variant-numeric: tabular-nums; }
.voice-bar-info span { color: var(--muted); font-size: 11.5px; }
.live-hint { display: inline-flex; align-items: center; gap: 9px; }
.live-wave { display: inline-flex; align-items: center; gap: 2.5px; height: 15px; }
.live-wave i { width: 3px; border-radius: 2px; background: var(--brand); transition: height .12s ease; }
.icon-button { display: grid; place-items: center; width: 32px; height: 32px; flex: 0 0 32px; border: 0; border-radius: 8px; background: transparent; color: var(--muted); transition: background .15s, color .15s; }
.icon-button:hover:not(:disabled) { background: #f0f1f6; color: var(--ink); }
.icon-button:disabled { opacity: .45; }
.foot-toggle { display: inline-flex; align-items: center; gap: 5px; padding: 2px 4px; border: 0; background: transparent; color: #7c7693; font-size: 12px; font-weight: 600; transition: color .15s, background .15s, border-color .15s; }
.foot-toggle:hover:not(:disabled) { color: var(--ink); }
.foot-toggle:disabled { opacity: .5; }
.foot-toggle.in-bar { height: 34px; padding: 0 12px; border: 1.5px solid #e7e1f5; border-bottom: 3px solid #dcd3f0; border-radius: 11px; background: #faf8ff; color: #694ec0; font-weight: 700; white-space: nowrap; }
.foot-toggle.in-bar:hover:not(:disabled) { border-color: #c9bdf0; background: #f2ecff; color: #583eb0; }
.ai-assist-btn { height: 30px; padding: 0 11px; font-size: 11.5px; border-radius: 9px; }
.ai-suggest-tray {
  margin-bottom: 10px; padding: 10px 12px; border-radius: 14px;
  border: 1.5px solid #e6dff5; background: #faf8ff; display: grid; gap: 8px;
}
.ai-suggest-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; font-size: 11.5px; font-weight: 650; color: #694ec0; }
.ai-suggest-head > span { display: inline-flex; align-items: center; gap: 5px; }
.ai-suggest-actions { display: flex; align-items: center; gap: 6px; }
.ai-mini-btn {
  border: 1px solid #dfd6f4; background: #fff; color: #694ec0; font-size: 11px; font-weight: 600;
  padding: 2px 8px; border-radius: 999px; cursor: pointer;
}
.ai-mini-btn:hover:not(:disabled) { background: #f2ecff; }
.ai-mini-close { border: 0; background: transparent; color: #8c85a6; padding: 2px; display: inline-flex; cursor: pointer; border-radius: 6px; }
.ai-mini-close:hover { background: #ede7fa; color: #583eb0; }
.ai-suggest-list {
  display: grid;
  gap: 6px;
  max-height: 180px;
  overflow-y: auto;
  padding-right: 4px;
}
.ai-suggest-chip {
  display: flex; flex-direction: column; align-items: flex-start; gap: 2px; width: 100%;
  padding: 8px 11px; border-radius: 11px; border: 1.5px solid #ece6f8; border-bottom-width: 2.5px;
  background: #fff; text-align: left; cursor: pointer; transition: border-color .15s, background .15s;
}
.ai-suggest-chip:hover { border-color: #b79ced; background: #f6f2ff; }
.ai-suggest-chip b { font-size: 13px; font-weight: 600; color: #2d294b; line-height: 1.45; }
.ai-suggest-chip span { font-size: 11.5px; color: #7c7693; }
.voice-result { flex-direction: column; align-items: stretch; gap: 8px; border-color: #d9e8de; background: #f4faf6; }
.voice-result.is-staged { flex-direction: row; align-items: center; justify-content: space-between; gap: 10px; border-color: #e4def7; background: #faf8ff; }
.staged-capsule { border-radius: 999px; min-width: 132px; }
.voice-result-actions { display: flex; align-items: center; justify-content: flex-end; gap: 6px; }
@media (max-width: 1100px) { .composer-area { margin: 0 14px; } }
</style>

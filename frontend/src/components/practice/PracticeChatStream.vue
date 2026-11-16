<template>
  <div ref="chatBody" class="chat-body" role="log" aria-label="聊天记录" :aria-busy="sending" @mouseup="emit('selection', chatBody)" @scroll="emit('scroll')">
    <div class="conversation-start"><span></span><small>练习开始 · 放轻松，试着用英语表达</small><span></span></div>
    <article v-for="msg in messages" :key="msg.key" class="msg-row" :class="msg.role">
      <span v-if="msg.role === 'agent'" class="msg-avatar">
        <CharacterPortrait
          :character="companionAvatar?.id || 'leo_2d'"
          :appearance="companionAvatar?.appearance || null"
          :animated="false"
          :lip-sync="false"
          state="idle"
          :name="roleName"
        />
      </span>
      <div class="message-content">
        <span class="message-author">{{ msg.role === 'agent' ? activeRole?.display_name || '交流伙伴' : '你' }}</span>
        <VoiceBubbleRow
          v-if="msg.role === 'user'"
          role="user"
          :is-user="true"
          :is-voice="Boolean(msg.isVoice)"
          :text="msg.text"
          :duration="msg.duration || 0"
          :capsule-width="capsuleWidth(msg)"
          :playing="playingKey === msg.key"
          :is-static="!msg.audioUrl && !msg.hasUserAudio"
          :progress="playbackTime / (playbackDuration || msg.duration || estimateSeconds(msg.text)) * 100"
          :show-original="showOriginal"
          :expanded="expandedMessages.has(msg.key)"
          :play-aria-label="playingKey === msg.key ? '停止播放我的语音' : '播放我的语音'"
          @toggle-play="playingKey === msg.key ? emit('stop-audio') : emit('play-user-voice', msg)"
          @toggle-original="emit('toggle-original', msg.key, $event)"
        >
          <template #after-bubble>
            <div v-if="msg.guardrailTips?.length" class="guardrail-tips">
              <div
                v-for="(tip, ti) in msg.guardrailTips"
                :key="`${msg.key}-tip-${ti}`"
                class="guardrail-tip-pill"
                :class="`is-${tip.kind || 'keyword_tip'}`"
              >
                <AppIcon :name="tip.kind === 'min_words' ? 'info' : 'sparkles'" :size="12" />
                <span>{{ tip.message }}</span>
              </div>
            </div>
            <div v-if="msg.pronunciationScore || msg.grammarCorrection" class="user-feedback-wrap">
              <button
                type="button"
                class="fb-collapse-pill"
                :class="{ 'is-open': expandedFeedback.has(msg.key) }"
                :aria-expanded="expandedFeedback.has(msg.key)"
                @click="emit('toggle-feedback', msg.key)"
              >
                <template v-if="msg.pronunciationScore">
                  <AppIcon name="mic" :size="12" />
                  <span>发音 <b :class="scoreTier(msg.pronunciationScore.total_score)">{{ Math.round(msg.pronunciationScore.total_score) }}</b></span>
                  <span v-if="msg.pronunciationScore.intonation_score != null" class="fb-sep" aria-hidden="true">·</span>
                  <span v-if="msg.pronunciationScore.intonation_score != null">语调 <b :class="scoreTier(msg.pronunciationScore.intonation_score)">{{ Math.round(msg.pronunciationScore.intonation_score) }}</b></span>
                  <span v-if="msg.pronunciationScore.speech_rate_wpm != null" class="fb-sep" aria-hidden="true">·</span>
                  <span v-if="msg.pronunciationScore.speech_rate_wpm != null">{{ msg.pronunciationScore.speech_rate_wpm }} WPM</span>
                  <span v-if="msg.grammarCorrection?.has_error" class="fb-dot-hint" title="有表达建议" />
                </template>
                <template v-else-if="msg.grammarCorrection?.has_error">
                  <AppIcon name="sparkles" :size="12" />
                  <span>{{ msg.grammarCorrection.issue_type === 'naturalness' ? '更地道表达建议' : '表达纠正建议' }}</span>
                </template>
                <template v-else>
                  <AppIcon name="check" :size="12" />
                  <span>表达自然准确</span>
                </template>
                <AppIcon name="chevron-down" :size="12" :class="{ flip: expandedFeedback.has(msg.key) }" />
              </button>

              <transition
                name="panel"
                @enter="onPanelEnter"
                @after-enter="onPanelAfterEnter"
                @leave="onPanelLeave"
                @after-leave="onPanelAfterLeave"
              >
                <div v-show="expandedFeedback.has(msg.key)" class="user-feedback-card">
                  <div v-if="msg.pronunciationScore" class="fb-summary">
                    <div class="fb-stats">
                      <span class="fb-stat">
                        <AppIcon name="mic" :size="12" />
                        <span>发音</span>
                        <b :class="scoreTier(msg.pronunciationScore.total_score)">{{ Math.round(msg.pronunciationScore.total_score) }}</b>
                      </span>
                      <span v-if="msg.pronunciationScore.intonation_score != null" class="fb-sep" aria-hidden="true">·</span>
                      <span v-if="msg.pronunciationScore.intonation_score != null" class="fb-stat">
                        <span>语调</span>
                        <b :class="scoreTier(msg.pronunciationScore.intonation_score)">{{ Math.round(msg.pronunciationScore.intonation_score) }}</b>
                      </span>
                      <span v-if="msg.pronunciationScore.speech_rate_wpm != null" class="fb-sep" aria-hidden="true">·</span>
                      <span v-if="msg.pronunciationScore.speech_rate_wpm != null" class="fb-stat">
                        <span>{{ msg.pronunciationScore.speech_rate_wpm }} WPM</span>
                        <small>{{ rateLabel(msg.pronunciationScore.rate_level) }}</small>
                      </span>
                    </div>
                  </div>

                  <div v-if="msg.pronunciationScore?.words?.length" class="fb-words">
                    <span
                      v-for="(w, wi) in msg.pronunciationScore.words"
                      :key="`${msg.key}-w-${wi}`"
                      class="fb-word"
                      :class="scoreTier(w.score ?? w.total_score)"
                      :title="`得分 ${Math.round(w.score ?? w.total_score ?? 0)}`"
                    >{{ w.word }}<small>{{ Math.round(w.score ?? w.total_score ?? 0) }}</small></span>
                  </div>

                  <div v-if="msg.grammarCorrection" class="fb-correction" :class="{ 'is-good': !msg.grammarCorrection.has_error }">
                    <template v-if="msg.grammarCorrection.has_error">
                      <div class="fb-corr-label">
                        <AppIcon name="sparkles" :size="12" />
                        <span>{{ msg.grammarCorrection.issue_type === 'naturalness' ? '更地道表达' : '表达纠正' }}</span>
                      </div>
                      <p class="fb-corr-sentence">{{ msg.grammarCorrection.corrected }}</p>
                      <p v-if="msg.grammarCorrection.explanation" class="fb-corr-note">{{ msg.grammarCorrection.explanation }}</p>
                      <div v-if="msg.grammarCorrection.better_expressions?.length" class="fb-alts">
                        <span v-for="(alt, ai) in msg.grammarCorrection.better_expressions" :key="`${msg.key}-alt-${ai}`" class="fb-alt">{{ alt }}</span>
                      </div>
                    </template>
                    <template v-else>
                      <div class="fb-corr-ok">
                        <AppIcon name="check" :size="12" />
                        <span>表达自然准确</span>
                      </div>
                    </template>
                  </div>
                </div>
              </transition>
            </div>
          </template>
        </VoiceBubbleRow>
        <VoiceBubbleRow
          v-else
          role="agent"
          :is-user="false"
          :is-voice="true"
          :text="msg.text"
          :html-text="renderMessageMd(msg.text)"
          :duration="msg.duration || 0"
          :capsule-width="capsuleWidth(msg)"
          :playing="playingKey === msg.key"
          :busy="ttsBusyKey === msg.key"
          :progress="playbackTime / (playbackDuration || estimateSeconds(msg.text)) * 100"
          :show-original="showOriginal"
          :expanded="expandedMessages.has(msg.key)"
          :play-aria-label="playingKey === msg.key ? '停止播放回复' : '播放回复语音'"
          @toggle-play="playingKey === msg.key ? emit('stop-audio') : emit('play-message', msg)"
          @toggle-original="emit('toggle-original', msg.key, $event)"
        />
      </div>
      <UserAvatar v-if="msg.role === 'user'" class="msg-avatar-user" :user="user" :size="30" />
    </article>

    <div
      v-if="sending && (!messages.length || messages[messages.length - 1]?.role !== 'agent' || !messages[messages.length - 1]?.text.trim())"
      class="thinking-message"
      role="status"
    >
      <span class="msg-avatar">
        <CharacterPortrait :character="companionAvatar?.id || 'leo_2d'" :appearance="companionAvatar?.appearance || null" :animated="false" :lip-sync="false" state="idle" :name="roleName" />
      </span>
      <span class="thinking-dots"><i></i><i></i><i></i></span>
      <small>正在组织回复…</small>
    </div>

    <PracticeEndingCard
      :finished="finished"
      :paying="paying"
      :starting="starting"
      :report-loading="reportLoading"
      :finish-text="finishText"
      :completed-goals="completedGoals"
      :goals-count="goalsCount"
      :turn-count="turnCount"
      :stage="stage"
      :stages="stages"
      :scene-id="sceneId"
      :scene-mode="sceneMode"
      :scenario-state="scenarioState"
      :messages="messages"
      @action="emit('action', $event)"
      @open-report="emit('open-report')"
      @back-to-select="emit('back-to-select')"
      @restart="emit('restart')"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import AppIcon from '../AppIcon.vue'
import CharacterPortrait from '../avatar/CharacterPortrait.vue'
import UserAvatar from '../UserAvatar.vue'
import PracticeEndingCard from './PracticeEndingCard.vue'
import VoiceBubbleRow from './VoiceBubbleRow.vue'

defineProps({
  messages: { type: Array, default: () => [] },
  sending: { type: Boolean, default: false },
  companionAvatar: { type: Object, default: null },
  roleName: { type: String, default: '' },
  activeRole: { type: Object, default: null },
  user: { type: Object, default: null },
  playingKey: { type: String, default: '' },
  ttsBusyKey: { type: String, default: '' },
  playbackTime: { type: Number, default: 0 },
  playbackDuration: { type: Number, default: 0 },
  showOriginal: { type: Boolean, default: false },
  expandedMessages: { type: Object, required: true },
  expandedFeedback: { type: Object, required: true },
  capsuleWidth: { type: Function, required: true },
  estimateSeconds: { type: Function, required: true },
  renderMessageMd: { type: Function, required: true },
  scoreTier: { type: Function, required: true },
  rateLabel: { type: Function, required: true },
  onPanelEnter: { type: Function, required: true },
  onPanelAfterEnter: { type: Function, required: true },
  onPanelLeave: { type: Function, required: true },
  onPanelAfterLeave: { type: Function, required: true },
  finished: { type: Boolean, default: false },
  paying: { type: Boolean, default: false },
  starting: { type: Boolean, default: false },
  reportLoading: { type: Boolean, default: false },
  finishText: { type: String, default: '' },
  completedGoals: { type: Number, default: 0 },
  goalsCount: { type: Number, default: 0 },
  turnCount: { type: Number, default: 0 },
  stage: { type: String, default: '' },
  stages: { type: Array, default: () => [] },
  sceneId: { type: String, default: '' },
  sceneMode: { type: String, default: '' },
  scenarioState: { type: Object, default: () => ({}) },
})

const emit = defineEmits([
  'selection',
  'scroll',
  'stop-audio',
  'play-user-voice',
  'play-message',
  'toggle-original',
  'toggle-feedback',
  'action',
  'open-report',
  'back-to-select',
  'restart',
])

const chatBody = ref(null)

function scrollToBottom() {
  if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight
}

defineExpose({ scrollToBottom, chatBody })
</script>

<style scoped>
.chat-body { flex: 1; min-height: 0; overflow: auto; overscroll-behavior: contain; padding: 20px 24px 28px; scrollbar-width: thin; background: #f8f9fc; }
.conversation-start { display: flex; align-items: center; justify-content: center; gap: 12px; margin: 0 0 28px; color: #7c7693; }
.conversation-start span { height: 1px; flex: 1; max-width: 60px; background: #e6e1f2; }
.conversation-start small { font-size: 12px; text-align: center; }
.msg-row { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 25px; }
.msg-row.user { justify-content: flex-end; }
.msg-avatar { display: flex; align-items: flex-start; justify-content: center; width: 30px; height: 30px; flex: 0 0 30px; overflow: hidden; margin-top: 21px; border-radius: 10px; background: #f0effa; color: #7771ac; font-size: 12.5px; font-weight: 600; }
.msg-avatar :deep(.portrait) { width: 144%; height: 144%; flex: 0 0 auto; transform: translateY(-2px); display: block; pointer-events: none; }
.msg-avatar-user { margin-top: 21px; flex: 0 0 30px; border-radius: 12px; }
.message-content { display: flex; flex-direction: column; align-items: flex-start; max-width: min(82%, 640px); }
.msg-row.user .message-content { align-items: flex-end; }
.message-author { margin-bottom: 6px; font-size: 12px; color: #7c7693; font-weight: 600; }
.thinking-message { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; }
.thinking-message .msg-avatar { margin-top: 0; }
.thinking-message small { color: var(--muted, #76718c); font-size: 12.5px; }
.thinking-dots { display: flex; gap: 4px; padding: 12px; border-radius: 10px; background: var(--bg, #f4f2fa); }
.thinking-dots i { width: 4px; height: 4px; border-radius: 50%; background: var(--brand, #8b73dd); }
.user-feedback-wrap { margin-top: 6px; display: flex; flex-direction: column; align-items: flex-end; }
.guardrail-tips { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; margin-top: 4px; max-width: min(100%, 440px); }
.guardrail-tip-pill { display: inline-flex; align-items: flex-start; gap: 6px; padding: 6px 10px; border-radius: 10px; font-size: 12px; line-height: 1.45; color: #5b4598; background: #f4f0ff; border: 1px solid #e3d9ff; text-align: left; }
.guardrail-tip-pill.is-min_words { color: #8c5a12; background: #fff8eb; border-color: #f3dfb8; }
.guardrail-tip-pill :deep(svg) { flex-shrink: 0; margin-top: 2px; }
.fb-collapse-pill {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 4px 10px; border-radius: 999px; cursor: pointer;
  background: #fff; border: 1.5px solid #e6e3f2; border-bottom-width: 2.5px;
  color: #6b6485; font-size: 11.5px; font-weight: 600;
  transition: background .15s, border-color .15s;
}
.fb-collapse-pill:hover, .fb-collapse-pill.is-open { background: #fff; border-color: #d3c9f0; color: #53439c; }
.fb-collapse-pill b.is-high { color: #16a34a; }
.fb-collapse-pill b.is-mid { color: #d97706; }
.fb-collapse-pill b.is-low { color: #e11d48; }
.fb-collapse-pill .flip { transform: rotate(180deg); transition: transform .18s; }
.fb-dot-hint { width: 6px; height: 6px; border-radius: 999px; background: #8b73dd; flex-shrink: 0; }
.user-feedback-card {
  margin-top: 6px; max-width: 440px; width: fit-content; min-width: 240px;
  background: #fff; border: 1.5px solid #eae6f2; border-bottom: 3px solid #e4dfec;
  border-radius: 14px; padding: 9px 13px; text-align: left;
  display: flex; flex-direction: column; gap: 8px;
}
.fb-summary { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.fb-stats { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; font-size: 12px; color: #7c7693; }
.fb-stat { display: inline-flex; align-items: center; gap: 4px; }
.fb-stat b { font-weight: 750; font-size: 12.5px; }
.fb-stat b.is-high { color: #16a34a; }
.fb-stat b.is-mid { color: #d97706; }
.fb-stat b.is-low { color: #e11d48; }
.fb-stat small { font-size: 11px; color: #8b84a3; }
.fb-sep { color: #d5cfe4; font-weight: 700; }
.fb-words {
  display: flex; flex-wrap: wrap; gap: 6px 10px;
  padding: 7px 10px; border-radius: 10px; background: #faf9fd; border: 1px solid #f0ecf8;
}
.fb-word {
  display: inline-flex; align-items: baseline; gap: 3px; font-size: 12.5px; font-weight: 600;
  color: #393451; padding-bottom: 1px; border-bottom: 2px solid transparent;
}
.fb-word small { font-size: 10px; font-weight: 600; color: #8c85a6; }
.fb-word.is-high { border-bottom-color: #86efac; }
.fb-word.is-mid { border-bottom-color: #fcd34d; }
.fb-word.is-low { border-bottom-color: #fda4af; color: #be123c; }
.fb-word.is-low small { color: #e11d48; }
.fb-correction { padding-top: 7px; border-top: 1px solid #f0ecf7; }
.fb-summary + .fb-correction, .fb-words + .fb-correction { padding-top: 8px; }
.user-feedback-card > .fb-correction:first-child { padding-top: 0; border-top: 0; }
.fb-corr-label { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; font-weight: 700; color: #7357cc; margin-bottom: 3px; }
.fb-corr-sentence { margin: 0; font-size: 13px; font-weight: 650; color: #2d294b; line-height: 1.5; }
.fb-corr-note { margin: 3px 0 0; font-size: 12px; color: #6e6885; line-height: 1.55; }
.fb-alts { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 6px; }
.fb-alt {
  padding: 2px 8px; border-radius: 8px; background: #f7f5fc;
  border: 1px solid #e7e1f5; color: #544b75; font-size: 11.5px; line-height: 1.45;
}
.fb-corr-ok { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 600; color: #1f7a4c; }
.panel-enter-active, .panel-leave-active {
  transition: height .22s cubic-bezier(.22, 1, .36, 1), opacity .18s ease, margin-top .22s cubic-bezier(.22, 1, .36, 1), padding-top .22s cubic-bezier(.22, 1, .36, 1), padding-bottom .22s cubic-bezier(.22, 1, .36, 1), border-top-width .22s cubic-bezier(.22, 1, .36, 1), border-bottom-width .22s cubic-bezier(.22, 1, .36, 1);
  overflow: hidden;
}
@media (min-width: 1550px) { .chat-body { padding: 24px 36px; } }
@media (max-width: 1100px) { .chat-body { padding: 16px 14px; } }
@media (max-width: 480px) { .message-content { max-width: 82%; } }
@media (prefers-reduced-motion: no-preference) {
  .thinking-dots i { animation: breathe 1.2s ease-in-out infinite; }
  .thinking-dots i:nth-child(2) { animation-delay: .15s; }
  .thinking-dots i:nth-child(3) { animation-delay: .3s; }
  @keyframes breathe { 50% { opacity: .25; transform: translateY(-2px); } }
}
</style>

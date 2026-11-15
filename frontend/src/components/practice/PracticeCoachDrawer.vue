<template>
  <aside class="chat-side" aria-label="练习辅助">
    <section class="companion-card">
      <div class="side-head"><h3>交流伙伴</h3></div>
      <div class="companion-stage">
        <AvatarStage :avatar="companionAvatar" :state="voiceBusy ? (voiceStatus === 'recording' ? 'listening' : 'thinking') : avatarState" :size="238" />
      </div>
      <div class="companion-identity">
        <b>{{ activeRole?.display_name || '交流伙伴' }}</b>
        <span>{{ activeRole?.title || '英语练习伙伴' }}</span>
      </div>
      <div class="companion-meta">
        <label class="autoplay-control">
          <input :checked="autoPlayReplies" type="checkbox" @change="onAutoPlayChange" />自动播放
        </label>
        <span class="voice-summary" :title="selectedVoiceLabel">
          <AppIcon name="volume" :size="12" />{{ selectedVoiceLabel }}
        </span>
      </div>
      <div class="companion-rate">
        <span class="rate-label">语速</span>
        <input
          :value="speechRate"
          type="range"
          min="0.75"
          max="1.25"
          step="0.05"
          class="rate-slider"
          aria-label="语速调节"
          @input="emit('update:speechRate', Number($event.target.value))"
          @change="emit('save-speech-rate')"
        />
        <span class="rate-value">{{ Number(speechRate).toFixed(2) }}×</span>
      </div>
    </section>

    <section class="support-card">
      <div class="support-head">
        <h3>训练目标</h3>
        <span>{{ completedGoals }} / {{ goals.length }}</span>
      </div>
      <progress class="goal-progress" :value="completedGoals" :max="goals.length || 1" aria-label="训练目标完成进度"></progress>
      <ul v-if="goals.length" class="goal-list">
        <li v-for="(goal, index) in goals" :key="goal.id" :class="{ done: goal.done }">
          <span class="goal-number">
            <AppIcon v-if="goal.done" name="check" :size="12" />
            <template v-else>{{ index + 1 }}</template>
          </span>
          <span>
            {{ goal.label }}
            <small v-if="!goalHasCheck(goal.id)">尚未接入自动判定</small>
          </span>
        </li>
      </ul>
      <p v-else class="support-empty">这个场景采用开放交流，按自己的节奏继续。</p>
    </section>
  </aside>
</template>

<script setup>
import AppIcon from '../AppIcon.vue'
import AvatarStage from '../avatar/AvatarStage.vue'

defineProps({
  companionAvatar: { type: Object, required: true },
  voiceBusy: { type: Boolean, default: false },
  voiceStatus: { type: String, default: 'idle' },
  avatarState: { type: String, default: 'idle' },
  activeRole: { type: Object, default: null },
  autoPlayReplies: { type: Boolean, default: true },
  selectedVoiceLabel: { type: String, default: '' },
  speechRate: { type: Number, default: 1.0 },
  completedGoals: { type: Number, default: 0 },
  goals: { type: Array, default: () => [] },
  goalHasCheck: { type: Function, required: true },
})

const emit = defineEmits(['update:autoPlayReplies', 'save-auto-play', 'update:speechRate', 'save-speech-rate'])

function onAutoPlayChange(e) {
  emit('update:autoPlayReplies', e.target.checked)
  emit('save-auto-play')
}
</script>

<style scoped>
.chat-side { display: flex; flex-direction: column; gap: 14px; min-height: 0; overflow-y: auto; }
.companion-card, .support-card {
  border: 1.5px solid #ebe7f5;
  border-bottom: 4px solid #e5def1;
  border-radius: 18px;
  background: #fff;
  overflow: hidden;
}
.companion-card { display: flex; flex-direction: column; flex: 0 0 auto; padding: 12px; }
.side-head { display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; margin-bottom: 9px; }
h3 { margin: 0; color: #2d294b; font-size: 14px; font-weight: 750; }
.companion-stage { display: flex; flex: 0 0 auto; height: 196px; }
.companion-card :deep(.stage) { width: 100% !important; height: 100%; aspect-ratio: auto; border-radius: 12px; border: 0; background: #f4f2fa; }
.companion-card :deep(.stage-top), .companion-card :deep(.edition), .companion-card :deep(.stage-bottom), .companion-card :deep(.spark) { display: none; }
.companion-card :deep(.character) { left: 17%; width: 66%; height: 93%; }
.companion-card :deep(.halo) { width: 64%; left: 18%; top: 15%; }
.companion-identity { display: flex; align-items: baseline; gap: 7px; flex-shrink: 0; margin: 10px 0 9px; }
.companion-identity b { color: #2d294b; font-size: 14px; font-weight: 750; }
.companion-identity span { overflow: hidden; color: #7c7693; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.companion-meta { display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-shrink: 0; padding-top: 8px; border-top: 1px solid #f1eef8; }
.companion-meta .autoplay-control { display: inline-flex; align-items: center; gap: 5px; margin: 0; color: #6e6886; font-size: 12px; font-weight: 600; white-space: nowrap; }
.companion-meta .autoplay-control input { width: 13px; height: 13px; accent-color: #8b73dd; }
.voice-summary { display: inline-flex; align-items: center; gap: 4px; min-width: 0; overflow: hidden; color: #7c7693; font-size: 11.5px; text-overflow: ellipsis; white-space: nowrap; }
.companion-rate { display: flex; align-items: center; gap: 8px; flex-shrink: 0; margin-top: 8px; padding-top: 8px; border-top: 1px dashed #f1eef8; }
.rate-label { flex: 0 0 auto; font-size: 11.5px; font-weight: 600; color: #6e6886; }
.rate-slider { flex: 1; min-width: 0; height: 4px; accent-color: #8b73dd; cursor: pointer; }
.rate-value { flex: 0 0 auto; min-width: 42px; text-align: right; font-size: 11.5px; font-weight: 700; color: #694ec0; font-variant-numeric: tabular-nums; }
.support-card { display: flex; flex: 0 0 auto; flex-direction: column; }
.support-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 12px 14px 9px; }
.support-head span { color: #694ec0; font-size: 12px; font-weight: 750; font-variant-numeric: tabular-nums; }
.goal-progress { display: block; width: calc(100% - 28px); height: 6px; margin: 0 14px; border: 0; appearance: none; background: #f0eff7; border-radius: 999px; overflow: hidden; accent-color: #8b73dd; }
.goal-progress::-webkit-progress-bar { background: #eee9fa; }
.goal-progress::-webkit-progress-value { background: #8b73dd; border-radius: 999px; }
.goal-progress::-moz-progress-bar { background: #8b73dd; }
.goal-list { list-style: none; padding: 4px 14px 8px; margin: 0; }
.goal-list li { display: flex; gap: 9px; align-items: flex-start; padding: 6px 0; color: #3d3857; font-size: 12.5px; line-height: 1.65; }
.goal-number { display: grid; place-items: center; width: 20px; height: 20px; flex: 0 0 20px; border: 1.5px solid #e2daf5; border-radius: 50%; color: #7c7693; font-size: 11px; font-weight: 700; }
.done .goal-number { color: #2c8a5e; border-color: #bde4cf; background: #e8f8f0; }
.done > span:last-child { color: #7c7693; }
.goal-list small { display: block; color: #7c7693; font-size: 11px; line-height: 1.6; }
.support-empty { margin: 8px 14px 12px; color: var(--muted, #76718c); font-size: 12px; line-height: 1.8; }
@media (max-height: 720px) {
  .companion-stage { height: 158px; }
  .companion-identity { margin: 8px 0 7px; }
  .goal-list li { padding: 5px 0; }
}
@media (max-width: 760px) {
  .chat-side { display: grid; grid-template-columns: 1fr 1fr; overflow: visible; min-height: auto; }
}
@media (max-width: 480px) {
  .chat-side { grid-template-columns: 1fr; }
}
</style>

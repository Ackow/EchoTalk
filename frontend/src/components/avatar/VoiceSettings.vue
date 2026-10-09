<template>
  <!-- 声音设置：声音 / 语速 / 演示口型开关。 -->
  <section class="voice-settings">
    <label class="field">
      <span class="field-label">声音</span>
      <div class="voice-row">
        <AppSelect aria-label="声音预设" :model-value="voiceStyle" :options="voiceOptions" @update:model-value="emit('update:voiceStyle', $event)" />
        <button class="preview-btn" type="button" :disabled="!channelAvailable" @click="emit('preview')">
          <svg v-if="!previewing" viewBox="0 0 12 12" aria-hidden="true"><path d="M3 1.8v8.4L10 6z" fill="currentColor" /></svg>
          <svg v-else viewBox="0 0 12 12" aria-hidden="true"><rect x="2.5" y="2.5" width="7" height="7" rx="1.5" fill="currentColor" /></svg>
          {{ previewing ? '停止' : '试听' }}
        </button>
      </div>
      <small v-if="!channelAvailable" class="field-tip warn">{{ probing ? '正在检测声音渠道…' : '声音渠道暂不可用，无法试听' }}</small>
    </label>

    <div class="field">
      <span class="field-label">语速 <b class="rate-value">{{ rateLabel }}</b></span>
      <div class="rate-row">
        <span class="rate-bound">0.75×</span>
        <input
          class="rate-slider"
          type="range" min="75" max="125" step="5"
          :value="Math.round(speechRate * 100)"
          aria-label="语速"
          @input="onRate($event.target.value)"
        />
        <span class="rate-bound">1.25×</span>
      </div>
    </div>

    <div class="switch-row">
      <div class="switch-text">
        <b>说话时显示口型</b>
        <small>仅用于角色动作演示</small>
      </div>
      <label class="switch">
        <input aria-label="说话时显示口型" type="checkbox" :checked="lipSyncEnabled" @change="emit('update:lipSyncEnabled', $event.target.checked)" />
        <span class="switch-track" aria-hidden="true"><span class="switch-thumb" /></span>
      </label>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import AppSelect from '../AppSelect.vue'

const props = defineProps({
  voiceStyle: { type: String, default: '' },
  voices: { type: Array, default: () => [] },
  speechRate: { type: Number, default: 1 },
  lipSyncEnabled: { type: Boolean, default: true },
  previewing: { type: Boolean, default: false },
})
const emit = defineEmits(['update:voiceStyle', 'update:speechRate', 'update:lipSyncEnabled', 'preview'])

const voiceOptions = computed(() => props.voices.map((v) => ({ value: v.style, label: v.label, hint: v.available === false ? '不可用' : '' })))
const channelAvailable = computed(() => props.voices.some((v) => v.available))
const probing = computed(() => props.voices.length > 0 && props.voices.every((v) => v.available == null))

const rateLabel = computed(() => `${props.speechRate.toFixed(2)}× ${props.speechRate === 1 ? '标准语速' : ''}`.trim())
function onRate(val) { emit('update:speechRate', Number(val) / 100) }

</script>

<style scoped>
.voice-settings { display: grid; gap: 15px; }
/* 公共 AppSelect 默认按内容宽度收缩，这里在表单里让它撑满剩余宽度 */
.field :deep(.app-select) { display: block; width: 100%; }
.field { display: grid; gap: 6px; }
.voice-row { display: flex; align-items: stretch; gap: 8px; }
.voice-row :deep(.app-select) { flex: 1; min-width: 0; }
.preview-btn {
  display: inline-flex; flex: 0 0 auto; align-items: center; gap: 5px; padding: 0 12px;
  border: 1px solid var(--line); border-radius: 8px; background: var(--surface);
  color: var(--ink-soft); font-size: 12.5px; cursor: pointer;
  transition: border-color .15s, color .15s, background .15s;
}
.preview-btn svg { width: 11px; height: 11px; }
.preview-btn:hover:not(:disabled) { border-color: #d5d7e6; color: var(--ink); background: #fafafd; }
.preview-btn:disabled { opacity: .55; cursor: not-allowed; }
.field-label { display: flex; align-items: baseline; gap: 6px; font-size: 12.5px; color: var(--muted); }
.rate-value { font-size: 12.5px; font-weight: 500; color: var(--brand-deep, var(--brand)); font-variant-numeric: tabular-nums; }
.field-tip { font-size: 11.5px; line-height: 1.6; color: var(--faint); }
.field-tip.warn { color: #a4711f; }

.rate-row { display: flex; align-items: center; gap: 9px; }
.rate-bound { font-size: 11px; color: var(--faint); font-variant-numeric: tabular-nums; }
.rate-slider { flex: 1; height: 22px; accent-color: var(--brand); cursor: pointer; }
.rate-slider:focus-visible { outline: 2px solid var(--brand); outline-offset: 3px; border-radius: 4px; }

.switch-row {
  display: flex; align-items: center; justify-content: space-between; gap: 14px;
  padding-top: 14px; border-top: 1px solid var(--line);
}
.switch-text b { display: block; font-size: 13px; font-weight: 500; color: var(--ink); }
.switch-text small { display: block; margin-top: 2px; font-size: 11.5px; color: var(--muted); }

/* 开关：自绘轨道，input 仍可键盘操作 */
.switch { position: relative; display: inline-flex; flex: 0 0 auto; cursor: pointer; }
.switch input { position: absolute; inset: 0; width: 100%; height: 100%; margin: 0; opacity: 0; cursor: pointer; }
.switch-track {
  display: block; width: 38px; height: 22px; padding: 2px; border-radius: 11px;
  background: #d8dae6; transition: background .18s;
}
.switch-thumb {
  display: block; width: 18px; height: 18px; border-radius: 50%;
  background: #fff; box-shadow: 0 1px 3px rgba(34, 37, 59, .3);
  transition: transform .18s cubic-bezier(.16, 1, .3, 1);
}
.switch input:checked + .switch-track { background: var(--brand); }
.switch input:checked + .switch-track .switch-thumb { transform: translateX(16px); }
.switch input:focus-visible + .switch-track { outline: 2px solid var(--brand); outline-offset: 2px; }
</style>

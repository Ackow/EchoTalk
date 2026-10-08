<template>
  <!-- 声音设置：呈现方式 / 声音 / 语速 / 口型开关。语速范围与服务端 clamp(0.5, 2.0) 一致。 -->
  <section class="voice-settings">
    <label class="field">
      <span class="field-label">呈现方式</span>
      <AppSelect :model-value="presentationMode" :options="modeOptions" @update:model-value="emit('update:presentationMode', $event)" />
      <small class="field-tip">{{ modeTip }}</small>
    </label>

    <label class="field">
      <span class="field-label">声音</span>
      <AppSelect :model-value="voiceStyle" :options="voiceOptions" @update:model-value="emit('update:voiceStyle', $event)" />
      <small v-if="!channelAvailable" class="field-tip warn">语音渠道未探测成功，显示本地缺省表</small>
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
        <small>当前实际级别：{{ lipLabel }}</small>
      </div>
      <label class="switch">
        <input type="checkbox" :checked="lipSyncEnabled" @change="emit('update:lipSyncEnabled', $event.target.checked)" />
        <span class="switch-track" aria-hidden="true"><span class="switch-thumb" /></span>
      </label>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import AppSelect from '../AppSelect.vue'

const props = defineProps({
  presentationMode: { type: String, default: 'auto' },
  voiceStyle: { type: String, default: '' },
  voices: { type: Array, default: () => [] },
  speechRate: { type: Number, default: 1 },
  lipSyncEnabled: { type: Boolean, default: true },
  lipLevel: { type: String, default: 'state' }, // 实际生效的口型级别，如实展示
})
const emit = defineEmits(['update:presentationMode', 'update:voiceStyle', 'update:speechRate', 'update:lipSyncEnabled'])

const modeOptions = [
  { value: 'auto', label: '自动（推荐）', hint: '2D 不可用时降级头像' },
  { value: '2d', label: '2D 数字人' },
  { value: 'head', label: '轻量头像' },
  { value: '3d', label: '3D 数字人 · three.js' },
]
const modeTip = computed(() => ({
  auto: '按形象可用性自动选择，2D 不可用时落到轻量头像',
  '2d': '分层形象 + 基础口型，首批已支持',
  head: '仅显示角色头像与发言状态',
  '3d': 'three.js 程序化 3D 角色：呼吸 / 眨眼 / 口型同步，配色随角色主题自动切换，无需模型文件',
}[props.presentationMode]))

const voiceOptions = computed(() => props.voices.map((v) => ({ value: v.style, label: v.label, hint: v.available ? '' : '不可用' })))
const channelAvailable = computed(() => props.voices.some((v) => v.available))

const rateLabel = computed(() => `${props.speechRate.toFixed(2)}× ${props.speechRate === 1 ? '标准语速' : ''}`.trim())
function onRate(val) { emit('update:speechRate', Number(val) / 100) }

const lipLabel = computed(() => (!props.lipSyncEnabled ? '已关闭' : {
  timeline: 'L1 时间轴（与语音对齐）',
  envelope: 'L2 音量包络',
  state: 'L3 播放状态',
  off: '不可用，保持闭合',
}[props.lipLevel] || 'L3 播放状态'))
</script>

<style scoped>
.voice-settings { display: grid; gap: 15px; }
/* 公共 AppSelect 默认按内容宽度收缩，这里在表单里让它撑满字段容器 */
.field :deep(.app-select) { display: block; width: 100%; }
.field { display: grid; gap: 6px; }
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

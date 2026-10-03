<template>
  <!-- 公共自绘下拉：原生 select 的弹出列表由操作系统渲染无法自定义样式，统一改用本组件。 -->
  <div ref="wrap" class="app-select" @keydown.escape.stop="open = false">
    <button
      class="as-trigger"
      :class="{ open }"
      type="button"
      aria-haspopup="listbox"
      :aria-expanded="open"
      :aria-label="ariaLabel"
      @click="open = !open"
    >
      <span v-if="label" class="as-label">{{ label }}</span>
      <span class="as-value">{{ currentLabel }}</span>
      <AppIcon class="as-chev" :class="{ flip: open }" name="chevron-down" :size="14" />
    </button>
    <ul v-if="open" class="as-menu" role="listbox">
      <li v-for="opt in options" :key="opt.value" role="option" :aria-selected="opt.value === modelValue">
        <button class="as-option" :class="{ active: opt.value === modelValue }" type="button" @click="choose(opt.value)">
          <span class="as-opt-name">{{ opt.label }}</span>
          <span v-if="opt.hint" class="as-opt-hint">{{ opt.hint }}</span>
          <AppIcon v-if="opt.value === modelValue" class="as-opt-check" name="check" :size="13" />
        </button>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' }, // 当前选中值
  options: { type: Array, required: true }, // [{ value, label, hint? }]
  label: { type: String, default: '' }, // 触发器内左侧固定文案（如「场景」「排序」）
  ariaLabel: { type: String, default: '下拉选择' },
  placeholder: { type: String, default: '请选择' },
})
const emit = defineEmits(['update:modelValue'])

const open = ref(false)
const wrap = ref(null)

const currentLabel = computed(() => props.options.find((o) => o.value === props.modelValue)?.label || props.placeholder)

function choose(value) {
  emit('update:modelValue', value)
  open.value = false
}

function onGlobalMouseDown(event) {
  if (open.value && wrap.value && !wrap.value.contains(event.target)) open.value = false
}

onMounted(() => document.addEventListener('mousedown', onGlobalMouseDown))
onBeforeUnmount(() => document.removeEventListener('mousedown', onGlobalMouseDown))
</script>

<style scoped>
.app-select { position: relative; display: inline-block; max-width: 100%; }

/* 触发器：与筛选行 34px 控件同规格 */
.as-trigger { position: relative; display: inline-flex; align-items: center; gap: 8px; height: 34px; max-width: 100%; padding: 0 30px 0 12px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); cursor: pointer; font-family: inherit; transition: border-color .15s, box-shadow .15s; }
.as-trigger:hover { border-color: #d5d7e6; }
.as-trigger.open, .as-trigger:focus-visible { border-color: var(--brand); box-shadow: 0 0 0 3px var(--brand-soft); outline: none; }
.as-label { flex: 0 0 auto; font-size: 12.5px; color: var(--muted); }
.as-value { max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--ink); font-size: 13.5px; font-weight: 500; }
.as-chev { position: absolute; right: 10px; color: var(--muted); pointer-events: none; transition: transform .18s; }
.as-chev.flip { transform: rotate(180deg); }

/* 弹出菜单：自绘列表，选中项品牌色高亮 */
.as-menu { position: absolute; top: calc(100% + 6px); left: 0; z-index: 60; min-width: 100%; width: max-content; max-width: 380px; max-height: 264px; overflow-y: auto; margin: 0; padding: 5px; list-style: none; background: var(--surface); border: 1px solid var(--line); border-radius: 10px; box-shadow: 0 10px 28px rgba(34, 37, 59, .14); }
.as-option { display: flex; align-items: center; gap: 8px; width: 100%; padding: 7px 9px; border: 0; border-radius: 7px; background: transparent; color: var(--ink); font-size: 13px; font-family: inherit; text-align: left; cursor: pointer; transition: background .12s; }
.as-option:hover { background: var(--bg); }
.as-option.active { background: var(--brand-soft); color: var(--brand-deep, var(--brand)); }
.as-option.active:hover { background: var(--brand-soft); }
.as-opt-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500; }
.as-opt-hint { flex: 0 0 auto; font-size: 11.5px; color: var(--muted); }
.as-option.active .as-opt-hint { color: var(--brand); }
.as-opt-check { flex: 0 0 auto; color: var(--brand); }
</style>

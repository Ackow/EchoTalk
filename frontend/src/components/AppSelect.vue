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
      @click="toggle"
    >
      <span v-if="label" class="as-label">{{ label }}</span>
      <span class="as-value">{{ currentLabel }}</span>
      <AppIcon class="as-chev" :class="{ flip: open }" name="chevron-down" :size="14" />
    </button>
    <transition :name="openUp ? 'as-pop-up' : 'as-pop'">
      <ul v-if="open" class="as-menu" :class="{ 'is-up': openUp }" :style="{ maxHeight: `${menuMaxHeight}px` }" role="listbox">
        <li v-for="opt in options" :key="opt.value" role="option" :aria-selected="opt.value === modelValue">
          <button class="as-option" :class="{ active: opt.value === modelValue }" type="button" @click="choose(opt.value)">
            <span class="as-opt-name">{{ opt.label }}</span>
            <span v-if="opt.hint" class="as-opt-hint">{{ opt.hint }}</span>
            <AppIcon v-if="opt.value === modelValue" class="as-opt-check" name="check" :size="13" />
          </button>
        </li>
      </ul>
    </transition>
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
const openUp = ref(false)
const menuMaxHeight = ref(240)
const wrap = ref(null)

const currentLabel = computed(() => props.options.find((o) => o.value === props.modelValue)?.label || props.placeholder)

function toggle() {
  if (!open.value && wrap.value) {
    const rect = wrap.value.getBoundingClientRect()
    const spaceBelow = window.innerHeight - rect.bottom - 14
    const spaceAbove = rect.top - 14
    openUp.value = spaceBelow < 200 && spaceAbove > spaceBelow
    const available = openUp.value ? spaceAbove : spaceBelow
    menuMaxHeight.value = Math.min(240, Math.max(120, Math.floor(available)))
  }
  open.value = !open.value
}

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

/* 触发器：统一 38px 高度与 EchoTalk 2.0 淡紫触感边框 */
.as-trigger { position: relative; display: inline-flex; align-items: center; gap: 8px; height: 38px; box-sizing: border-box; max-width: 100%; padding: 0 32px 0 13px; border: 1.5px solid #e9e5f1; border-bottom-width: 3px; border-radius: 12px; background: #fff; cursor: pointer; font-family: inherit; transition: border-color .15s, background .15s, box-shadow .15s; }
.as-trigger:hover { border-color: #cfc1f1; background: #fcfaff; }
.as-trigger.open, .as-trigger:focus-visible { border-color: #9b83e5; border-bottom-color: #8067d1; box-shadow: 0 0 0 3px #f0eaff; outline: none; }
.as-label { flex: 0 0 auto; font-size: 12.5px; font-weight: 600; color: #7c7693; }
.as-value { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #2d294b; font-size: 13.5px; font-weight: 600; }
.as-chev { position: absolute; right: 11px; color: #7c7693; pointer-events: none; transition: transform .18s, color .15s; }
.as-trigger.open .as-chev { color: #654ab8; }
.as-chev.flip { transform: rotate(180deg); }

/* 弹出菜单：自绘列表，淡紫圆角与选中高亮（自动适配上下空间，不超出视口） */
.as-menu { position: absolute; top: calc(100% + 6px); left: 0; z-index: 60; min-width: 100%; width: max-content; max-width: 380px; max-height: 240px; overflow-y: auto; margin: 0; padding: 6px; list-style: none; background: #fff; border: 1.5px solid #e6dff5; border-bottom-width: 4px; border-radius: 14px; box-shadow: 0 12px 30px rgba(101, 74, 184, .14); transform-origin: top left; }
.as-menu.is-up { top: auto; bottom: calc(100% + 6px); transform-origin: bottom left; }
.as-pop-enter-active, .as-pop-up-enter-active { transition: opacity 180ms cubic-bezier(0.22, 1, 0.36, 1), transform 180ms cubic-bezier(0.22, 1, 0.36, 1); }
.as-pop-leave-active, .as-pop-up-leave-active { transition: opacity 130ms ease, transform 130ms ease; }
.as-pop-enter-from { opacity: 0; transform: translateY(-6px) scale(0.97); }
.as-pop-leave-to { opacity: 0; transform: translateY(-4px) scale(0.98); }
.as-pop-up-enter-from { opacity: 0; transform: translateY(6px) scale(0.97); }
.as-pop-up-leave-to { opacity: 0; transform: translateY(4px) scale(0.98); }
@media (prefers-reduced-motion: reduce) {
  .as-pop-enter-active, .as-pop-leave-active, .as-pop-up-enter-active, .as-pop-up-leave-active, .as-chev { transition: none; }
}
.as-option { display: flex; align-items: center; gap: 8px; width: 100%; padding: 8px 10px; border: 0; border-radius: 9px; background: transparent; color: #2d294b; font-size: 13px; font-family: inherit; text-align: left; cursor: pointer; transition: background .12s, color .12s; }
.as-option:hover { background: #faf8ff; }
.as-option.active { background: #f0eaff; color: #654ab8; }
.as-option.active:hover { background: #ebe4fa; }
.as-opt-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 550; }
.as-option.active .as-opt-name { font-weight: 650; }
.as-opt-hint { flex: 0 0 auto; font-size: 11.5px; color: #7c7693; }
.as-option.active .as-opt-hint { color: #8069c7; }
.as-opt-check { flex: 0 0 auto; color: #8b73dd; }
</style>

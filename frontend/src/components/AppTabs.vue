<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number], required: true },
  options: { type: Array, required: true }, // [{ value, label, count? }]
  ariaLabel: { type: String, default: '选项切换' },
})
const emit = defineEmits(['update:modelValue'])

const valOf = (opt) => (opt.value !== undefined ? opt.value : opt.key)

const trackRef = ref(null)
const itemRefs = ref([])
const thumb = ref({ left: 0, width: 0, ready: false, animate: false })
let observer = null

function syncThumb(animate = true) {
  const idx = props.options.findIndex((o) => valOf(o) === props.modelValue)
  const el = itemRefs.value[idx]
  if (!el) return
  thumb.value = {
    left: el.offsetLeft,
    width: el.offsetWidth,
    ready: true,
    animate: animate && thumb.value.ready,
  }
}

watch(
  () => [props.modelValue, props.options],
  async () => {
    await nextTick()
    syncThumb(true)
  },
  { deep: true }
)

onMounted(async () => {
  await nextTick()
  syncThumb(false)
  if (typeof ResizeObserver !== 'undefined' && trackRef.value) {
    observer = new ResizeObserver(() => syncThumb(false))
    observer.observe(trackRef.value)
  }
})

onBeforeUnmount(() => {
  observer?.disconnect()
})
</script>

<template>
  <div ref="trackRef" class="app-tabs" role="tablist" :aria-label="ariaLabel">
    <span
      v-if="thumb.ready"
      class="app-tab-thumb"
      :class="{ animate: thumb.animate }"
      :style="{ width: `${thumb.width}px`, transform: `translateX(${thumb.left - 3}px)` }"
      aria-hidden="true"
    />
    <button
      v-for="(opt, index) in options"
      :key="valOf(opt)"
      :ref="(el) => { if (el) itemRefs[index] = el }"
      type="button"
      role="tab"
      class="app-tab"
      :class="{ active: modelValue === valOf(opt) }"
      :aria-selected="modelValue === valOf(opt)"
      @click="emit('update:modelValue', valOf(opt))"
    >
      <span>{{ opt.label }}</span>
      <span v-if="opt.count !== undefined" class="app-tab-count">{{ opt.count }}</span>
    </button>
  </div>
</template>

<style scoped>
.app-tabs {
  position: relative;
  display: inline-flex;
  align-items: center;
  height: 38px;
  box-sizing: border-box;
  padding: 3px;
  border-radius: 12px;
  background: #efeafc;
  border: 1.5px solid #e2daf5;
  gap: 3px;
  max-width: 100%;
  overflow-x: auto;
  scrollbar-width: none;
}
.app-tabs::-webkit-scrollbar { display: none; }

.app-tab-thumb {
  position: absolute;
  top: 3px;
  left: 3px;
  height: 29px;
  border-radius: 9px;
  background: #ffffff;
  box-shadow: 0 2px 6px rgba(101, 74, 184, 0.12);
  z-index: 0;
  pointer-events: none;
}
.app-tab-thumb.animate {
  transition: transform 240ms cubic-bezier(0.22, 1, 0.36, 1), width 240ms cubic-bezier(0.22, 1, 0.36, 1);
}

.app-tab {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: 30px;
  padding: 0 14px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: #6b6584;
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  white-space: nowrap;
  cursor: pointer;
  transition: color .18s ease;
}
.app-tab:hover { color: #393451; }
.app-tab.active { color: #654ab8; }
.app-tab:focus-visible { outline: 2px solid #8b73dd; outline-offset: -2px; }
.app-tab-count {
  font-size: 11.5px;
  font-weight: 600;
  opacity: 0.72;
  font-variant-numeric: tabular-nums;
}
.app-tab.active .app-tab-count { opacity: 0.92; }

@media (prefers-reduced-motion: reduce) {
  .app-tab-thumb.animate { transition: none; }
}
</style>

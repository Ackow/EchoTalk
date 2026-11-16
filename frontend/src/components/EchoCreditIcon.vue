<template>
  <svg
    class="echo-credit-icon"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <defs>
      <linearGradient :id="gradOuter" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stop-color="#FFB84D" />
        <stop offset="55%" stop-color="#F59E0B" />
        <stop offset="100%" stop-color="#D97706" />
      </linearGradient>
      <linearGradient :id="gradInner" x1="5" y1="5" x2="19" y2="19" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stop-color="#FFFBEB" />
        <stop offset="100%" stop-color="#FDE68A" />
      </linearGradient>
    </defs>
    <!-- 外层圆润八角星币底座 -->
    <rect x="2" y="2" width="20" height="20" rx="6.5" :fill="`url(#${gradOuter})`" />
    <!-- 内层浅金凹槽 -->
    <rect x="4.2" y="4.2" width="15.6" height="15.6" rx="4.6" :fill="`url(#${gradInner})`" />
    <!-- 中心回声共鸣星芒 + 声波弧线（Echo Core） -->
    <path
      d="M12 6.8L13.35 10.15L16.7 11.5L13.35 12.85L12 16.2L10.65 12.85L7.3 11.5L10.65 10.15L12 6.8Z"
      fill="#B45309"
    />
    <path
      d="M15.8 8.3C16.85 9.15 17.45 10.28 17.45 11.5C17.45 12.72 16.85 13.85 15.8 14.7"
      stroke="#D97706"
      stroke-width="1.4"
      stroke-linecap="round"
    />
    <path
      d="M8.2 8.3C7.15 9.15 6.55 10.28 6.55 11.5C6.55 12.72 7.15 13.85 8.2 14.7"
      stroke="#D97706"
      stroke-width="1.4"
      stroke-linecap="round"
    />
  </svg>
</template>

<script setup>
import { useId } from 'vue'

defineProps({
  size: { type: [Number, String], default: 16 },
})

const uid = typeof useId === 'function' ? useId() : Math.random().toString(36).slice(2, 8)
const gradOuter = `ec-outer-${uid}`
const gradInner = `ec-inner-${uid}`
</script>

<style scoped>
.echo-credit-icon {
  display: inline-block;
  vertical-align: -0.18em;
  flex-shrink: 0;
}
</style>

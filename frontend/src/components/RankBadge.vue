<template>
  <!-- 段位徽章：粗描边卡通风 + 随 Lv.1→Lv.6 逐级叠加的层级感图腾 -->
  <span class="rank-crest" :class="{ locked }" :style="{ width: `${size}px`, height: `${size}px` }">
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <!-- 盾牌外框 -->
      <path
        d="M32 7 51 14.5v15.2c0 12.6-8 21.8-19 26.3C21 51.5 13 42.3 13 29.7V14.5L32 7Z"
        :fill="palette.bg"
        stroke="#55466e"
        stroke-width="3.2"
        stroke-linejoin="round"
      />

      <!-- 高阶内盾衬底（Lv.4+ 增加内层盾框，强化进阶厚度） -->
      <path
        v-if="level >= 4"
        d="M32 12.5 46 18.2v11.3c0 9.6-5.9 16.7-14 20.3-8.1-3.6-14-10.7-14-20.3V18.2L32 12.5Z"
        fill="#ffffff"
        fill-opacity="0.45"
        stroke="#55466e"
        stroke-width="1.8"
        stroke-linejoin="round"
      />

      <!-- Lv.1 微光旅人：单核微光 -->
      <g v-if="level === 1">
        <circle cx="32" cy="30" r="6.5" :fill="palette.fg" stroke="#55466e" stroke-width="2.8" />
        <circle cx="32" cy="30" r="2.2" fill="#55466e" />
      </g>

      <!-- Lv.2 捕风听者：核心 + 两侧声波扩散 -->
      <g v-else-if="level === 2">
        <circle cx="32" cy="30" r="5" :fill="palette.fg" stroke="#55466e" stroke-width="2.6" />
        <path d="M23.5 24.5a8.5 8.5 0 0 0 0 11" stroke="#55466e" stroke-width="2.8" stroke-linecap="round" />
        <path d="M40.5 24.5a8.5 8.5 0 0 1 0 11" stroke="#55466e" stroke-width="2.8" stroke-linecap="round" />
      </g>

      <!-- Lv.3 声纹破译师：外框棱镜 + 核心锁定 -->
      <g v-else-if="level === 3">
        <path
          d="M32 18 44 30 32 42 20 30 32 18Z"
          :fill="palette.fg"
          stroke="#55466e"
          stroke-width="2.8"
          stroke-linejoin="round"
        />
        <circle cx="32" cy="30" r="4.2" fill="#ffe484" stroke="#55466e" stroke-width="2.2" />
      </g>

      <!-- Lv.4 频率领航员：内盾 + 双翼跃升箭头 -->
      <g v-else-if="level === 4">
        <path
          d="M32 18 42.5 36.5 32 32 21.5 36.5 32 18Z"
          :fill="palette.fg"
          stroke="#55466e"
          stroke-width="2.8"
          stroke-linejoin="round"
        />
        <path d="M25 40.5 32 37.5 39 40.5" stroke="#55466e" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" />
      </g>

      <!-- Lv.5 共鸣大师：内盾 + 三峰王冠 + 底座 -->
      <g v-else-if="level === 5">
        <path
          d="M21 36 23 23.5 29 29 32 20 35 29 41 23.5 43 36H21Z"
          :fill="palette.fg"
          stroke="#55466e"
          stroke-width="2.6"
          stroke-linejoin="round"
        />
        <rect x="22" y="39" width="20" height="3.6" rx="1.8" fill="#ffe484" stroke="#55466e" stroke-width="2" />
      </g>

      <!-- Lv.6 声域传说：内盾 + 双翼桂冠 + 耀星 -->
      <g v-else>
        <path d="M21 27c-1 7 3.5 13 11 15.5M43 27c1 7-3.5 13-11 15.5" stroke="#55466e" stroke-width="2.6" stroke-linecap="round" />
        <path
          d="M32 17.5 35.4 24.8 43.3 25.9 37.6 31.4 39 39.2 32 35.5 25 39.2 26.4 31.4 20.7 25.9 28.6 24.8 32 17.5Z"
          fill="#ffe484"
          stroke="#55466e"
          stroke-width="2.5"
          stroke-linejoin="round"
        />
      </g>

      <!-- 小阶星点区分：I（1 颗）、II（2 颗）、III / MAX（3 颗） -->
      <g v-if="pipCount > 0">
        <circle
          v-for="(cx, i) in pipPositions"
          :key="i"
          :cx="cx"
          :cy="pipCount === 3 && i === 1 ? 52.5 : 53.5"
          :r="pipCount === 3 && i === 1 ? 4.2 : 3.5"
          fill="#ffe484"
          stroke="#55466e"
          stroke-width="2.2"
        />
      </g>
    </svg>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  level: { type: Number, required: true },
  subRank: { type: String, default: '' }, // I | II | III | MAX
  size: { type: Number, default: 52 },
  locked: { type: Boolean, default: false }
})

const pipCount = computed(() => {
  if (props.subRank === 'I') return 1
  if (props.subRank === 'II') return 2
  if (props.subRank === 'III' || props.subRank === 'MAX') return 3
  return 0
})

const pipPositions = computed(() => {
  if (pipCount.value === 1) return [32]
  if (pipCount.value === 2) return [26, 38]
  if (pipCount.value === 3) return [21.5, 32, 42.5]
  return []
})

const PALETTES = {
  1: { bg: '#e8e2fc', fg: '#ffffff' },
  2: { bg: '#a7dfc5', fg: '#ffffff' },
  3: { bg: '#c7ddff', fg: '#ffffff' },
  4: { bg: '#fde4a6', fg: '#ffffff' },
  5: { bg: '#fbcfe8', fg: '#ffffff' },
  6: { bg: '#d8c8fb', fg: '#fff3db' }
}

const palette = computed(() => PALETTES[props.level] || PALETTES[1])
</script>

<style scoped>
.rank-crest {
  display: inline-flex;
  flex: 0 0 auto;
}

.rank-crest.locked {
  filter: grayscale(0.85) opacity(0.5);
}

.rank-crest svg {
  width: 100%;
  height: 100%;
  display: block;
}
</style>

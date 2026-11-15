<template>
  <!-- 场景封面：分类色调 + 专属矢量插画/上传封面图；加载失败回落内置插画 -->
  <div class="scene-cover" :class="[`tone-${tone}`, { 'has-image': hasImage, 'has-art': !hasImage && customArt }]">
    <img v-if="hasImage" :src="scene.cover_image_url || coverUrl(scene.id)" :alt="`${scene.name}场景封面`" @error="imageFailed = true" />
    <svg v-else-if="customArt === 'train'" class="scene-cover-svg" viewBox="0 0 360 150" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <rect width="360" height="150" fill="#eef1ff" />
      <path d="M22,126 L22,52 C22,14 114,14 114,52 L114,126 Z" fill="#fef9ec" stroke="#d5daf2" stroke-width="2.5" />
      <line x1="68" y1="24" x2="68" y2="126" stroke="#e2e6f7" stroke-width="2" />
      <line x1="22" y1="82" x2="114" y2="82" stroke="#e2e6f7" stroke-width="2" />
      <circle cx="304" cy="40" r="18" fill="#fff" stroke="#bfc6ea" stroke-width="2.5" />
      <line x1="304" y1="40" x2="304" y2="29" stroke="#5b4f8c" stroke-width="2" stroke-linecap="round" />
      <line x1="304" y1="40" x2="313" y2="44" stroke="#7c62d2" stroke-width="2" stroke-linecap="round" />
      <path d="M138,108 L314,108 Q336,108 344,126 L138,126 Z" fill="#c7d2fe" />
      <path d="M148,108 L300,108 Q318,108 326,118 L148,118 Z" fill="#a5b4fc" opacity="0.65" />
      <rect x="160" y="113" width="24" height="7" rx="3" fill="#fff" opacity="0.9" />
      <rect x="194" y="113" width="24" height="7" rx="3" fill="#fff" opacity="0.9" />
      <rect x="228" y="113" width="24" height="7" rx="3" fill="#fff" opacity="0.9" />
      <rect x="262" y="113" width="24" height="7" rx="3" fill="#fff" opacity="0.9" />
      <rect y="126" width="360" height="24" fill="#e2def5" />
    </svg>
    <svg v-else-if="customArt === 'airport'" class="scene-cover-svg" viewBox="0 0 360 150" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <rect width="360" height="150" fill="#eaf4ff" />
      <path d="M232,48 Q248,36 266,46 Q278,40 286,52 L232,52 Z" fill="#fff" opacity="0.9" />
      <path d="M294,32 Q306,22 320,30 Q330,26 336,36 L294,36 Z" fill="#fff" opacity="0.85" />
      <path d="M244,82 L288,68 L278,82 L298,90 L268,91 L258,100 L256,87 Z" fill="#a5c4e8" />
      <path d="M196,104 Q224,94 244,84" fill="none" stroke="#93c5fd" stroke-width="2" stroke-dasharray="4 4" />
      <line x1="168" y1="0" x2="154" y2="118" stroke="#d0e3f7" stroke-width="3" />
      <line x1="332" y1="0" x2="346" y2="118" stroke="#d0e3f7" stroke-width="3" />
      <rect y="118" width="360" height="32" fill="#e6e2f5" />
    </svg>
    <svg v-else-if="customArt === 'interview'" class="scene-cover-svg" viewBox="0 0 360 150" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <rect width="360" height="150" fill="#f3efff" />
      <rect x="204" y="22" width="126" height="72" rx="8" fill="#fff" opacity="0.85" stroke="#ddd4f5" stroke-width="2" />
      <rect x="218" y="36" width="44" height="7" rx="3.5" fill="#b7a7eb" />
      <rect x="218" y="50" width="76" height="6" rx="3" fill="#e2dbf7" />
      <rect x="218" y="62" width="60" height="6" rx="3" fill="#e2dbf7" />
      <rect x="276" y="34" width="38" height="38" rx="8" fill="#efeafc" stroke="#d3c6f2" stroke-width="1.5" />
      <path d="M126,118 L184,118 L174,90 L134,90 Z" fill="#d8ccf8" />
      <rect x="118" y="118" width="74" height="6" rx="3" fill="#b7a7eb" />
      <rect y="124" width="360" height="26" fill="#ebe5fa" />
    </svg>
    <div v-else class="scene-cover-art" aria-hidden="true"><span><AppIcon :name="icon" :size="26" /></span></div>
    <div class="scene-cover-copy">
      <small>{{ categoryLabel }}</small>
      <h3>{{ scene.name }}</h3>
    </div>
    <span class="scene-cover-mark" aria-hidden="true"><AppIcon :name="markIcon" :size="16" /></span>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import AppIcon from '../AppIcon.vue'
import { coverUrl } from '../../api/scenes'
import { sceneIcon, sceneTone } from '../../constants/sceneMeta'

const props = defineProps({
  scene: { type: Object, required: true },
  categoryLabel: { type: String, default: '' }, // 分类文案由页面传入（两页文案不同）
  markIcon: { type: String, default: 'arrow-up-right' },
})

const imageFailed = ref(false) // 封面图 404 时回落色调底，不污染父级数据
const hasImage = computed(() => Boolean(props.scene.cover_path || props.scene.cover_image_url) && !imageFailed.value)
const icon = computed(() => sceneIcon(props.scene)) // 图标与色调映射收敛到 constants/sceneMeta
const tone = computed(() => sceneTone(props.scene))
const customArt = computed(() => {
  const id = String(props.scene?.id || '').toLowerCase()
  if (id.includes('train')) return 'train'
  if (id.includes('airport')) return 'airport'
  if (id.includes('interview')) return 'interview'
  return ''
})
</script>

<style scoped>
.scene-cover { position: relative; isolation: isolate; display: flex; min-height: 100px; align-items: flex-end; overflow: hidden; margin: -1.5px -1.5px 0; padding: 12px 15px; border-radius: 17px 17px 0 0; }
.scene-cover::before, .scene-cover::after { position: absolute; z-index: -1; border-radius: 50%; content: ''; pointer-events: none; }
.scene-cover::before { width: 118px; height: 118px; top: -58px; right: -10px; background: #ffffff72; }
.scene-cover::after { width: 74px; height: 74px; top: 36px; right: 62px; background: #ffffff55; }
.scene-cover.tone-daily { background: #fff0dc; color: #654d3b; }
.scene-cover.tone-travel { background: #e7efff; color: #405981; }
.scene-cover.tone-business { background: #e5f3eb; color: #355f4b; }
.scene-cover.tone-career { background: #eee9ff; color: #4e3e78; }
.scene-cover.tone-academic { background: #e8efff; color: #405981; }
.scene-cover.tone-custom { background: #f5eaf1; color: #6b4c60; }
.scene-cover > img, .scene-cover-svg { position: absolute; z-index: -2; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.scene-cover.has-art::before, .scene-cover.has-art::after { display: none; }
.scene-cover.has-image::before { display: none; }
.scene-cover.has-image::after {
  inset: 0; width: auto; height: auto; border-radius: 0;
  background:
    linear-gradient(90deg, rgba(28, 28, 40, .42) 0%, rgba(28, 28, 40, .18) 52%, rgba(28, 28, 40, 0) 80%),
    linear-gradient(180deg, rgba(28, 28, 40, 0) 42%, rgba(28, 28, 40, .44) 76%, rgba(24, 24, 36, .68) 100%);
}
.scene-cover.has-image { color: #fff; }
.scene-cover.has-image .scene-cover-copy h3 { text-shadow: 0 1px 6px rgba(18, 18, 28, .55); }
.scene-cover.has-image .scene-cover-art { display: none; }
.scene-cover-copy { position: relative; z-index: 1; min-width: 0; max-width: calc(100% - 70px); }
.scene-cover-copy small { display: inline-flex; align-items: center; min-height: 20px; padding: 0 8px; border: 1px solid #ffffffa8; border-radius: 999px; background: #ffffffb8; color: #5e5271; font-size: 10.5px; font-weight: 700; }
.scene-cover.has-image .scene-cover-copy small { border-color: rgba(255, 255, 255, .36); background: rgba(34, 34, 46, .58); color: #fff; backdrop-filter: blur(4px); }
.scene-cover-copy h3 { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; margin: 6px 0 0; color: inherit; font-size: 15.5px; font-weight: 800; line-height: 1.3; letter-spacing: -.02em; text-wrap: pretty; }
.scene-cover-art { position: absolute; top: 10px; right: 18px; display: grid; width: 66px; height: 66px; place-items: center; border: 1px solid #ffffffb0; border-radius: 50%; background: #ffffff80; color: currentColor; transform: rotate(-7deg); }
.scene-cover-art::after { position: absolute; right: -9px; bottom: 1px; width: 21px; height: 21px; border: 1px solid #ffffffb0; border-radius: 8px; background: #ffffffb8; content: ''; }
.scene-cover-art > span { display: grid; width: 44px; height: 44px; place-items: center; border-radius: 15px; background: #ffffffb8; }
.scene-cover-mark { position: absolute; top: 9px; right: 10px; z-index: 2; display: grid; width: 26px; height: 26px; place-items: center; border: 1px solid #ffffffa8; border-radius: 50%; background: #ffffffc9; color: #6b58a4; opacity: 0; transform: translate(-3px, 3px); transition: opacity .16s, transform .16s; }
/* 封面自身 hover 时浮出跳转角标；整卡 hover 由页面用 :deep 补一条同效规则 */
.scene-cover:hover .scene-cover-mark, .scene-cover:focus-within .scene-cover-mark { opacity: 1; transform: translate(0, 0); }
@media (max-width: 760px) { .scene-cover { min-height: 92px; padding: 11px 13px; }.scene-cover-art { right: 12px; transform: scale(.88) rotate(-7deg); }.scene-cover-copy { max-width: calc(100% - 62px); }.scene-cover-copy h3 { font-size: 14.5px; } }
@media (prefers-reduced-motion: reduce) { .scene-cover-mark { transition: none; } }
</style>

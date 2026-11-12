<template>
  <!-- 场景封面：分类色调 + 右上圆形图标 + 分类/标题；有上传封面图时图片铺满并转白字，加载失败回落色调底 -->
  <div class="scene-cover" :class="[`tone-${tone}`, { 'has-image': hasImage }]">
    <img v-if="hasImage" :src="coverUrl(scene.id)" :alt="`${scene.name}场景封面`" @error="imageFailed = true" />
    <div class="scene-cover-art" aria-hidden="true"><span><AppIcon :name="icon" :size="26" /></span></div>
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
const hasImage = computed(() => Boolean(props.scene.cover_path) && !imageFailed.value)
const icon = computed(() => sceneIcon(props.scene)) // 图标与色调映射收敛到 constants/sceneMeta
const tone = computed(() => sceneTone(props.scene))
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
.scene-cover > img { position: absolute; z-index: -2; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.scene-cover.has-image::after { top: 0; right: 0; width: auto; height: auto; border-radius: 0; background: linear-gradient(180deg, #1c173000 20%, #1c1730a8 100%); }
.scene-cover.has-image { color: #fff; }
.scene-cover.has-image .scene-cover-art { display: none; }
.scene-cover-copy { position: relative; z-index: 1; min-width: 0; max-width: calc(100% - 70px); }
.scene-cover-copy small { display: inline-flex; align-items: center; min-height: 20px; padding: 0 8px; border: 1px solid #ffffffa8; border-radius: 999px; background: #ffffffb8; color: #5e5271; font-size: 10.5px; font-weight: 700; }
.scene-cover.has-image .scene-cover-copy small { border-color: #ffffff40; background: #30284055; color: #fff; }
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

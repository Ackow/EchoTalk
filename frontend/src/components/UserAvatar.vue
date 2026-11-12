<template>
  <!-- 用户头像：有自定义头像显示图片，否则回落用户名首字母，未登录显示人形图标 -->
  <span class="user-avatar" :style="boxStyle" role="img" :aria-label="label">
    <img v-if="url && !broken" :src="url" :alt="label" @error="broken = true" />
    <template v-else-if="user">{{ initial }}</template>
    <AppIcon v-else name="user" :size="iconSize" />
  </span>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import AppIcon from './AppIcon.vue'
import { avatarUrl } from '../api/auth'

const props = defineProps({
  user: { type: Object, default: null }, // 当前用户（含 id / username / avatar_path）
  size: { type: Number, default: 0 }, // 直径像素：设置页 104；传 0 交给样式表决定（侧栏需随窗口高度缩放）
})

const broken = ref(false) // 图片加载失败（文件被清理等）：静默回落到首字母
const url = computed(() => avatarUrl(props.user))
watch(url, () => { broken.value = false }) // 换头像后重新尝试加载

const initial = computed(() => (props.user?.username || '').slice(0, 1).toUpperCase())
const label = computed(() => (props.user ? `${props.user.username} 的头像` : '未登录'))
const iconSize = computed(() => (props.size ? Math.round(props.size * 0.46) : 15))
const boxStyle = computed(() => (props.size ? {
  width: `${props.size}px`,
  height: `${props.size}px`,
  fontSize: `${Math.max(12, Math.round(props.size * 0.42))}px`,
} : {})) // 不传尺寸时不写内联样式，避免压过窄窗口下的媒体查询
</script>

<style scoped>
.user-avatar {
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  overflow: hidden;
  border-radius: 50%;
  background: #fff;
  color: #775dc9;
  font-weight: 700;
  line-height: 1;
  box-shadow: inset 0 0 0 1px var(--line);
  user-select: none;
}
.user-avatar img { display: block; width: 100%; height: 100%; object-fit: cover; }
</style>

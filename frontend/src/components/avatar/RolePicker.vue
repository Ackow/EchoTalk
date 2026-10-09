<template>
  <!-- 角色选择：先选场景角色，再选该角色的形象。映射关系来自场景包 roles[].avatar 推荐值。 -->
  <section class="role-picker">
    <div class="block">
      <div class="block-head">
        <h3>交流角色</h3>
        <span class="hint">来自场景包推荐</span>
      </div>
      <div class="role-list" role="radiogroup" aria-label="交流角色">
        <button
          v-for="r in roles"
          :key="r.id"
          class="role-chip"
          :class="{ active: r.id === modelValue }"
          type="button"
          role="radio"
          :aria-checked="r.id === modelValue"
          @click="emit('update:modelValue', r.id)"
        >
          <span class="role-avatar" :style="{ background: themeOf(r.avatar).cloth }">{{ r.display_name.charAt(0) }}</span>
          <span class="role-text">
            <b>{{ r.display_name }}</b>
            <small>{{ r.title }}</small>
          </span>
        </button>
      </div>
    </div>

    <div class="block">
      <div class="block-head">
        <h3>形象</h3>
        <span class="hint">{{ sourceLabel }}</span>
      </div>
      <div class="avatar-list" role="radiogroup" aria-label="数字人形象">
        <button
          v-for="a in avatars"
          :key="a.id"
          class="avatar-chip"
          :class="{ active: a.id === avatarId }"
          type="button"
          role="radio"
          :aria-checked="a.id === avatarId"
          @click="emit('update:avatarId', a.id)"
        >
          <span class="chip-thumb" :style="{ background: themeOf(a.id).cloth }">{{ a.display_name.charAt(0) }}</span>
          <span class="chip-name">{{ a.display_name.split(' · ')[0] }}</span>
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },     // 当前角色 id
  avatarId: { type: String, default: '' },       // 当前形象 id
  roles: { type: Array, default: () => [] },     // 场景角色列表
  avatars: { type: Array, default: () => [] },   // 可用形象列表
  source: { type: String, default: 'user' },     // 解析来源：user/scene_role/scene_package/default
})
const emit = defineEmits(['update:modelValue', 'update:avatarId'])

// 与 AvatarStage 共用同一套配色，缩略图与舞台形象一致
const THEME_COLOR = {
  sarah_2d: '#6f6cc4', leo_2d: '#c98a4b', david_2d: '#3f8f80', default: '#5a6478',
}
function themeOf(id) { return { cloth: THEME_COLOR[id] || '#5a6478' } }

const sourceLabel = computed(() => ({
  user: '你的选择',
  scene_role: '场景推荐',
  scene_package: '整包推荐',
  default: '应用缺省',
}[props.source] || '应用缺省'))
</script>

<style scoped>
.role-picker { display: grid; gap: 18px; }
.block-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; margin-bottom: 9px; }
.block-head h3 { margin: 0; font-size: 13px; font-weight: 600; color: var(--ink); }
.hint { font-size: 11.5px; color: var(--faint); }

.role-list { display: grid; gap: 6px; }
.role-chip {
  display: flex; align-items: center; gap: 10px; width: 100%;
  padding: 8px 10px; border: 1px solid var(--line); border-radius: 9px;
  background: var(--surface); cursor: pointer; text-align: left;
  transition: border-color .16s, background .16s;
}
.role-chip:hover { border-color: #d5d7e6; }
.role-chip.active { border-color: var(--brand); background: var(--brand-soft); }
.role-avatar {
  display: grid; width: 30px; height: 30px; flex: 0 0 30px; place-items: center;
  border-radius: 8px; color: #fff; font-size: 13px; font-weight: 600;
}
.role-text { display: flex; min-width: 0; flex-direction: column; gap: 1px; }
.role-text b { font-size: 13.5px; font-weight: 500; color: var(--ink); }
.role-text small { font-size: 11.5px; color: var(--muted); }
.role-chip.active .role-text b { color: var(--brand-deep, var(--brand)); }

.avatar-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }
.avatar-chip {
  position: relative; display: flex; align-items: center; gap: 8px;
  min-height: 44px; padding: 6px 9px; border: 1px solid var(--line); border-radius: 9px;
  background: var(--surface); cursor: pointer; text-align: left;
  transition: border-color .16s, background .16s;
}
.avatar-chip:hover:not(:disabled) { border-color: #d5d7e6; }
.avatar-chip.active { border-color: var(--brand); background: var(--brand-soft); }
.avatar-chip:disabled { cursor: default; opacity: .62; }
.chip-thumb {
  display: grid; width: 26px; height: 26px; flex: 0 0 26px; place-items: center;
  border-radius: 7px; color: #fff; font-size: 12px; font-weight: 600;
}
.chip-name { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12.5px; color: var(--ink-soft); }
.avatar-chip.active .chip-name { color: var(--brand-deep, var(--brand)); font-weight: 500; }
.chip-tag { position: absolute; top: 4px; right: 5px; font-size: 10px; color: var(--faint); }
</style>

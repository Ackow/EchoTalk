<template>
  <section class="avatar-page">
    <!-- 工具行式页头：与全站各页同构（紧凑标题 + 右侧操作），消除页面间布局误差 -->
    <header class="page-head">
      <div class="head-text">
        <h1 class="head-title">数字人角色</h1>
        <p class="head-desc">选择你的交流伙伴——形象、声音与语速只影响呈现层，不改变场景训练内容，设置对所有场景生效。</p>
      </div>
      <div class="head-actions">
        <button class="ghost-button" type="button" :disabled="saving" @click="onReset">
          <AppIcon name="rotate" :size="14" />恢复默认
        </button>
        <button class="primary-button" type="button" :disabled="saving" @click="onSave">
          <AppIcon v-if="saving" name="loader" :size="14" class="spin" />
          <AppIcon v-else name="check" :size="14" />{{ saving ? '保存中' : '保存角色选择' }}
        </button>
      </div>
    </header>

    <!-- 非对称主区：舞台占更大权重，控制区收窄 -->
    <div class="layout">
      <!-- 左：深色聚光舞台 + 状态演示 -->
      <div class="stage-col">
        <div class="stage-head">
          <div>
            <h2 class="serif-name">{{ currentAvatar?.display_name || '默认形象' }}</h2>
            <p class="stage-sub">{{ currentRole?.title || '演示角色' }} · {{ modeLabel }}</p>
          </div>
          <span class="source-chip" :class="source">{{ sourceLabel }}</span>
        </div>

        <AvatarStage
          ref="stageRef"
          :avatar="currentAvatar"
          :state="'idle'"
          :lip-sync="effectiveLip"
          :size="stageSize"
        />

        <!-- 状态演示：逐个预览四种状态，不依赖真实音频 -->
        <div class="demo-bar">
          <span class="demo-label">状态演示</span>
          <div class="demo-btns">
            <button
              v-for="d in demoStates" :key="d.value"
              class="demo-btn" :class="{ active: d.value === demoState }"
              type="button" :aria-pressed="d.value === demoState"
              @click="onDemo(d.value)"
            >{{ d.label }}</button>
          </div>
          <button class="link-button" type="button" @click="previewInDialogue">在对话中预览</button>
        </div>

        <!-- 口型级别说明：如实展示当前实际跑在哪一级 -->
        <div class="lip-levels">
          <p class="levels-title">口型驱动</p>
          <ul>
            <li v-for="l in lipRows" :key="l.level" :class="{ on: l.active }">
              <span class="lv-badge">{{ l.level }}</span>
              <span class="lv-text">{{ l.text }}</span>
              <span v-if="l.active" class="lv-now">当前</span>
            </li>
          </ul>
        </div>
      </div>

      <!-- 右：档案卡式控制区 -->
      <aside class="panel">
        <div class="panel-head">
          <h2>角色与声音</h2>
          <span v-if="sampleOnly" class="sample-chip">示例数据</span>
        </div>

        <RolePicker
          v-model="roleId"
          :avatar-id="avatarId"
          :roles="roles"
          :avatars="avatars"
          :source="source"
          @update:avatar-id="avatarId = $event"
        />

        <hr class="separator" />

        <VoiceSettings
          v-model:presentation-mode="presentationMode"
          v-model:voice-style="voiceStyle"
          v-model:speech-rate="speechRate"
          v-model:lip-sync-enabled="lipSyncEnabled"
          :voices="voices"
          :lip-level="effectiveLip"
        />

        <hr class="separator" />

        <!-- 3D 资源位：留明确位置，不做空白 -->
        <div class="future-block">
          <h3>3D 资源位</h3>
          <p>Three.js / VRM 角色、动作与细口型将在此接入。当前阶段保持头像与 2D 可用，界面位置与数据结构已预留。</p>
          <button class="ghost-button" type="button" @click="onResourceInfo">管理形象资源</button>
        </div>
      </aside>
    </div>

    <p class="page-note">
      优先级：你的选择 &gt; 场景包推荐 &gt; 应用缺省。场景包只在
      <code>roles[].avatar</code> 与 <code>avatar.preferred</code> 里携带推荐值，不携带形象资产。
    </p>

    <!-- 操作反馈：aria-live 让读屏用户也能感知 -->
    <transition name="toast">
      <p v-if="toast" class="toast" role="status" aria-live="polite">{{ toast }}</p>
    </transition>
  </section>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import AvatarStage from '../components/avatar/AvatarStage.vue'
import RolePicker from '../components/avatar/RolePicker.vue'
import VoiceSettings from '../components/avatar/VoiceSettings.vue'
import {
  FALLBACK_AVATARS, FALLBACK_ROLES, FALLBACK_VOICES,
  listAvatars, listVoices, getAvatarPreference, saveAvatarPreference, resetAvatarPreference,
} from '../api/avatar'
import { session } from '../auth/session'

const router = useRouter()
const stageRef = ref(null)

// ---- 表单状态 ----
const avatars = ref(FALLBACK_AVATARS)
const voices = ref(FALLBACK_VOICES)
const roles = ref(FALLBACK_ROLES)
const roleId = ref(FALLBACK_ROLES[0].id)
const avatarId = ref('')
const voiceStyle = ref(FALLBACK_VOICES[0].style)
const speechRate = ref(1)
const presentationMode = ref('auto')
const lipSyncEnabled = ref(true)
const source = ref('scene_role')   // 解析来源，用于展示"你的选择 / 场景推荐"
const sampleOnly = ref(true)       // 接口未就绪时为 true，页面标注示例
const saving = ref(false)
const toast = ref('')

// ---- 演示状态 ----
const demoStates = [
  { value: 'idle', label: '待机' },
  { value: 'listening', label: '倾听' },
  { value: 'thinking', label: '思考' },
  { value: 'speaking', label: '说话' },
]
const demoState = ref('speaking')
function onDemo(v) {
  demoState.value = v
  stageRef.value?.playDemo(v)
}

// 舞台宽度随窗口变化，保持 4:5 比例在可用空间内
const stageSize = ref(320)
function measure() {
  const col = document.querySelector('.stage-col')
  if (!col) return
  // 双重约束：不超过所在列，也不超过视口宽度减去页面内边距（窄屏下页面 padding 变小）
  const viewportCap = document.documentElement.clientWidth - 32
  stageSize.value = Math.max(220, Math.min(420, Math.floor(col.clientWidth), viewportCap))
}
let resizeTimer = null
function onResize() {
  clearTimeout(resizeTimer)
  resizeTimer = setTimeout(measure, 120) // 防抖，避免拖拽窗口时高频重算
}
// 侧栏折叠 / 窗口变化都会改列宽，用 ResizeObserver 兜住仅靠 window.resize 漏掉的情况
let observer = null
onMounted(() => {
  measure()
  window.addEventListener('resize', onResize)
  const col = document.querySelector('.stage-col')
  if (col && typeof ResizeObserver !== 'undefined') {
    observer = new ResizeObserver(() => {
      clearTimeout(resizeTimer)
      resizeTimer = setTimeout(measure, 80)
    })
    observer.observe(col)
  }
  loadAll()
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  clearTimeout(resizeTimer)
  if (observer) { observer.disconnect(); observer = null }
})

// ---- 数据加载：接口失败时保留缺省数据并标注示例 ----
async function loadAll() {
  try {
    const [av, vo] = await Promise.all([listAvatars(), listVoices()])
    avatars.value = av
    voices.value = vo
    sampleOnly.value = false // 拿到真实接口数据
  } catch {
    avatars.value = FALLBACK_AVATARS
    voices.value = FALLBACK_VOICES
    sampleOnly.value = true
  }
  const pref = await getAvatarPreference()
  if (pref) applyPreference(pref)
  else applySceneRecommendation()
  measure()
}

function applyPreference(p) {
  if (p.role_id) roleId.value = p.role_id
  if (p.avatar_id) { avatarId.value = p.avatar_id; source.value = 'user' }
  if (p.voice_style) voiceStyle.value = p.voice_style
  if (typeof p.speech_rate === 'number') speechRate.value = p.speech_rate
  if (p.presentation_mode) presentationMode.value = p.presentation_mode
  if (typeof p.lip_sync_enabled === 'boolean') lipSyncEnabled.value = p.lip_sync_enabled
}

// 未设置偏好时按场景包推荐值落位（用户偏好 > 场景角色推荐 > 整包推荐 > 缺省）
function applySceneRecommendation() {
  const role = roles.value.find((r) => r.id === roleId.value) || roles.value[0]
  const rec = role?.avatar
  if (rec && avatars.value.some((a) => a.id === rec)) {
    avatarId.value = rec
    source.value = 'scene_role'
  } else {
    avatarId.value = 'default'
    source.value = 'default'
  }
}
// 切角色时，若用户未显式选过形象（source=user），跟随新角色推荐
watch(roleId, (id, old) => {
  if (source.value === 'user' && old) return // 用户已显式选择，不被场景改写
  const role = roles.value.find((r) => r.id === id)
  const rec = role?.avatar
  if (rec && avatars.value.some((a) => a.id === rec)) {
    avatarId.value = rec
    source.value = 'scene_role'
  } else {
    applySceneRecommendation()
  }
})
// 用户手动改形象 → 标记为 user（解析链最高优先级）
watch(avatarId, (id, old) => {
  if (old && id !== old) source.value = 'user'
})

// ---- 派生值 ----
const currentRole = computed(() => roles.value.find((r) => r.id === roleId.value) || roles.value[0])
const currentAvatar = computed(() => {
  const base = avatars.value.find((a) => a.id === avatarId.value) || avatars.value.find((a) => a.id === 'default')
  if (!base) return null
  // presentationMode 强制 head 时降级为头像形态；auto 走资产自身 kind
  if (presentationMode.value === 'head') return { ...base, kind: 'head' }
  if (presentationMode.value === '3d') return { ...base, kind: '3d' }
  if (presentationMode.value === '2d') return { ...base, kind: '2d' }
  return base
})
const effectiveLip = computed(() => (lipSyncEnabled.value ? 'state' : 'off'))
const sourceLabel = computed(() => ({ user: '你的选择', scene_role: '场景推荐', scene_package: '整包推荐', default: '应用缺省' }[source.value]))
const modeLabel = computed(() => ({ auto: '自动', '2d': '2D 数字人', head: '轻量头像', '3d': '3D 占位' }[presentationMode.value]))
const lipRows = computed(() => [
  { level: 'L1', text: 'TTS 词级时间戳驱动，口型与语音对齐', active: effectiveLip.value === 'timeline' },
  { level: 'L2', text: '音量包络驱动，开合随实时音量', active: effectiveLip.value === 'envelope' },
  { level: 'L3', text: '播放状态驱动，固定开合节奏', active: effectiveLip.value === 'state' },
  { level: '—', text: '口型关闭，嘴部保持闭合', active: effectiveLip.value === 'off' },
])

// ---- 操作 ----
function showToast(msg) {
  toast.value = msg
  setTimeout(() => { toast.value = '' }, 2600)
}
async function onSave() {
  if (!session.token) { showToast('请先登录后再保存偏好'); return }
  saving.value = true
  try {
    await saveAvatarPreference({
      role_id: roleId.value,
      avatar_id: avatarId.value,
      voice_style: voiceStyle.value,
      speech_rate: speechRate.value,
      presentation_mode: presentationMode.value,
      lip_sync_enabled: lipSyncEnabled.value,
    })
    source.value = 'user'
    showToast('已保存到你的偏好，对所有场景生效')
  } catch (err) {
    showToast(err.message || '保存失败，请稍后重试')
  } finally {
    saving.value = false
  }
}
async function onReset() {
  try {
    await resetAvatarPreference()
  } catch {
    // 游客或接口未就绪：仅本地恢复
  }
  applySceneRecommendation()
  speechRate.value = 1
  presentationMode.value = 'auto'
  lipSyncEnabled.value = true
  showToast('已恢复为跟随场景推荐')
}
function previewInDialogue() {
  // 对话页尚未接入真实数字人，先跳到占位页并说明，不伪装已连通
  router.push({ name: 'practice' })
  showToast('对话页接入后将直接使用该形象')
}
function onResourceInfo() {
  showToast('3D 资源管理：本期仅保留位置，未接入上传与下载')
}
</script>

<style scoped>
/* 文字可读性：--muted / --faint 的 AA 覆盖写在 assets/styles.css 的 .avatar-page 作用域，
   那里同时作用于子组件（scoped 样式无法把 token 传给子组件）。 */
.avatar-page { flex: 1; min-height: 0; display: flex; flex-direction: column; padding: 22px 28px 32px; overflow-y: auto; } /* 与全站页面容器同一内边距 */

/* ---- 页头：与全站工具行同构（紧凑标题 + 右侧操作），不再使用衬线大标题 ---- */
.page-head { display: flex; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 12px; }
.head-title { margin: 0; font-size: 15.5px; font-weight: 650; color: var(--ink); }
.head-text { min-width: 0; flex: 1 1 auto; } /* 让按钮始终留在视口内，标题区先压缩 */
.head-desc { margin: 3px 0 0; font-size: 12.5px; line-height: 1.6; color: var(--muted); }
.head-actions { display: flex; gap: 9px; min-width: 0; justify-content: flex-end; flex-wrap: nowrap; }
/* 按钮保持单行：恢复默认两字 + 图标在窄屏仍不折行 */
.head-actions .ghost-button, .head-actions .primary-button { white-space: nowrap; flex: 0 0 auto; }

/* 衬线字体仅保留给舞台人名（David·产品经理），页头不再占用 */
.serif-name {
  margin: 0;
  font-family: Georgia, 'Times New Roman', 'Songti SC', serif; /* 编辑感衬线，区别于全站 Inter 正文 */
  font-size: 27px; font-weight: 400; letter-spacing: -.01em; line-height: 1.25;
  color: var(--ink);
}

/* ---- 非对称布局：舞台 1.55fr / 控制区 1fr ---- */
.layout { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(320px, 1fr); gap: 22px; align-items: start; }
.stage-col { display: grid; gap: 14px; min-width: 0; }
.stage-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.stage-sub { margin: 5px 0 0; font-size: 12.5px; color: var(--muted); }

.source-chip { padding: 4px 9px; border-radius: 6px; font-size: 11.5px; font-weight: 500; white-space: nowrap; }
.source-chip.user { background: var(--brand-soft); color: var(--brand-deep, var(--brand)); }
.source-chip.scene_role, .source-chip.scene_package { background: #e6ecfb; color: #33619f; }
.source-chip.default { background: #eeeff3; color: var(--ink-soft); }

/* ---- 状态演示条 ---- */
.demo-bar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.demo-label { font-size: 11.5px; color: var(--faint); }
.demo-btns { display: flex; gap: 4px; padding: 3px; border: 1px solid var(--line); border-radius: 9px; background: var(--surface); }
.demo-btn {
  height: 28px; padding: 0 12px; border: 0; border-radius: 7px;
  background: transparent; color: var(--ink-soft); font-size: 12.5px; cursor: pointer;
  transition: background .15s, color .15s;
}
.demo-btn:hover { color: var(--ink); }
.demo-btn.active { background: var(--brand-soft); color: var(--brand-deep, var(--brand)); font-weight: 500; }
.link-button { margin-left: auto; padding: 0; border: 0; background: transparent; color: var(--brand); font-size: 12.5px; cursor: pointer; }
.link-button:hover { text-decoration: underline; text-underline-offset: 3px; }

/* ---- 口型级别列表 ---- */
.lip-levels { padding: 13px 15px; border: 1px solid var(--line); border-radius: 11px; background: var(--surface); }
.levels-title { margin: 0 0 9px; font-size: 11.5px; letter-spacing: .04em; color: var(--faint); }
.lip-levels ul { display: grid; gap: 6px; margin: 0; padding: 0; list-style: none; }
.lip-levels li { display: flex; align-items: center; gap: 9px; font-size: 12.5px; color: var(--faint); }
.lip-levels li.on { color: var(--ink); }
.lv-badge {
  display: grid; width: 26px; height: 20px; flex: 0 0 26px; place-items: center;
  border-radius: 5px; background: #f1f2f7; font-size: 11px; font-weight: 500; color: var(--muted);
}
.lip-levels li.on .lv-badge { background: var(--brand-soft); color: var(--brand-deep, var(--brand)); }
.lv-text { flex: 1; }
.lv-now { padding: 2px 7px; border-radius: 4px; background: var(--brand); color: #fff; font-size: 10.5px; }

/* ---- 控制面板 ---- */
.panel { display: flex; flex-direction: column; gap: 16px; padding: 18px; border: 1px solid var(--line); border-radius: 13px; background: var(--surface); }
.panel > * { min-width: 0; } /* 防止 grid/flex 子项被内容撑破 */
.panel-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.panel-head h2 { margin: 0; font-size: 15px; font-weight: 600; }
.sample-chip { padding: 3px 8px; border-radius: 5px; background: #fdf4e3; color: #8a6116; font-size: 10.5px; }
.separator { height: 1px; margin: 0; border: 0; background: var(--line); }
.future-block h3 { margin: 0 0 6px; font-size: 13px; font-weight: 600; }
.future-block p { margin: 0 0 10px; font-size: 12px; line-height: 1.75; color: var(--muted); }

.ghost-button { display: inline-flex; align-items: center; gap: 6px; height: 34px; padding: 0 14px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--ink-soft); font-size: 13.5px; cursor: pointer; transition: border-color .15s, background .15s; }
.ghost-button:hover:not(:disabled) { border-color: #d5d7e6; background: #fafafd; }
.ghost-button:disabled { opacity: .55; cursor: default; }
.primary-button { display: inline-flex; align-items: center; gap: 6px; height: 34px; padding: 0 16px; border: 0; border-radius: 8px; background: var(--brand); color: #fff; font-size: 13.5px; font-weight: 500; cursor: pointer; transition: background .15s; }
.primary-button:hover:not(:disabled) { background: var(--brand-deep); }
.primary-button:disabled { opacity: .55; cursor: default; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.page-note { margin: 20px 0 0; font-size: 12px; line-height: 1.85; color: var(--faint); }
.page-note code { padding: 1px 5px; border-radius: 4px; background: #f1f2f7; font-size: 11.5px; color: var(--ink-soft); }

/* 操作反馈：底部居中浮层，不遮挡表单 */
.toast {
  position: fixed; bottom: 24px; left: 50%; z-index: 40;
  margin: 0; padding: 11px 18px; transform: translateX(-50%);
  border-radius: 9px; background: #34364f; color: #fff;
  font-size: 12.5px; line-height: 1.6; white-space: nowrap;
  box-shadow: 0 8px 26px rgba(34, 37, 59, .26);
}
.toast-enter-active, .toast-leave-active { transition: opacity .2s, transform .2s cubic-bezier(.16, 1, .3, 1); }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translate(-50%, 8px); }

/* ---- 入场序列：4 组错峰 ---- */
@media (prefers-reduced-motion: no-preference) {
  .head-text, .stage-col, .panel, .page-note { animation: rise .42s cubic-bezier(.22, .8, .32, 1) both; }
  .stage-col { animation-delay: .08s; }
  .panel { animation-delay: .16s; }
  .page-note { animation-delay: .24s; }
}
@keyframes rise { from { opacity: 0; transform: translateY(14px) } to { opacity: 1; transform: none } }

/* ---- 响应式：窄屏按顺序堆叠，舞台置顶 ---- */
@media (max-width: 1080px) {
  .layout { grid-template-columns: minmax(0, 1fr); }
  .panel { order: 2; }
}
@media (max-width: 720px) {
  .avatar-page { padding: 18px 16px 28px; }
  .page-head { flex-direction: column; align-items: stretch; gap: 10px; }
  .head-actions { justify-content: stretch; }
  .head-actions .ghost-button, .head-actions .primary-button { flex: 1; justify-content: center; }
  .link-button { margin-left: 0; }
}
</style>

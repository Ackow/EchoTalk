<script setup>
// 数字人角色页：流程为「先选场景 → 再选形象与音色」，组合可任意搭配。
// 布局对齐 Scenes / Knowledge：工具行（场景 + 操作）→ 左状态预览 + 右设置卡。
// 偏好登录后存数据库（/preferences/avatar），游客存本机；交流身份已移除，role_id 恒为 null。
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import AppSelect from '../components/AppSelect.vue'
import AvatarStage from '../components/avatar/AvatarStage.vue'
import CharacterPortrait from '../components/avatar/CharacterPortrait.vue'
import VoiceSettings from '../components/avatar/VoiceSettings.vue'
import {
  FALLBACK_AVATARS, FALLBACK_VOICES, VOICE_STYLE_ALIASES,
  fetchTtsVoices, getAvatarPreference, resetAvatarPreference, saveAvatarPreference, synthesizeSpeech,
} from '../api/avatar'
import { listScenes } from '../api/scenes'
import { session } from '../auth/session'

const AVATARS = FALLBACK_AVATARS // 初版写死前端的固定形象清单
const DEFAULTS = { avatarId: 'mira_2d', voiceStyle: 'emma', sceneId: '', speechRate: 1, lipSyncEnabled: true }

const stage = ref(null)
const sceneId = ref(DEFAULTS.sceneId) // '' 表示跟随场景推荐
const avatarId = ref(DEFAULTS.avatarId)
const voiceStyle = ref(DEFAULTS.voiceStyle)
const speechRate = ref(DEFAULTS.speechRate)
const lipSyncEnabled = ref(DEFAULTS.lipSyncEnabled)
const savedRemote = ref(false) // 当前偏好是否已存数据库
const toast = ref('')
const previewState = ref('idle')
const voices = ref(FALLBACK_VOICES.map((v) => ({ ...v }))) // 声音清单：available 由渠道探测结果覆盖
let toastTimer

const notify = (message) => {
  toast.value = message
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.value = ''), 2800)
}

// ── 声音渠道探测：进入页面时后台探测一次，结果驱动试听按钮可用性 ──
async function probeVoices() {
  const list = await fetchTtsVoices()
  if (!Array.isArray(list)) return
  voices.value = voices.value.map((v) => {
    const found = list.find((item) => item.style === v.style)
    return found ? { ...v, available: Boolean(found.available) } : v
  })
}

const avatar = computed(() => AVATARS.find((a) => a.id === avatarId.value) || AVATARS[0])
const nameOf = (a) => a.display_name.split(' · ')[0] // 展示名英文部分
const cnNameOf = (a) => a.display_name.split(' · ')[1] || ''

// 主题主色：形象 chips 底色（与 CharacterPortrait 衣着色一致）
const THEME_ACCENT = { violet: '#9282bb', teal: '#74b3a0', blue: '#7d95c6', amber: '#cba468' }
const accentOf = (theme) => THEME_ACCENT[theme] || '#5a6478'

// ── 场景选项：内置 + 自己的场景（游客也可浏览内置），置顶工具行首先选择 ──
const sceneOptions = ref([{ value: '', label: '跟随场景推荐' }])
async function loadScenes() {
  try {
    const { data } = await listScenes()
    sceneOptions.value = [
      { value: '', label: '跟随场景推荐' },
      ...data.items.map((s) => ({ value: s.id, label: s.name })),
    ]
  } catch { /* 后端不可用时保留下拉缺省项 */ }
}

// ── 偏好读取：登录读数据库（/preferences/avatar），游客或后端不可用读本机 ──
const storageKey = computed(() => `echotalk-avatar-2d:${session.user?.id ?? 'guest'}`)
function readLocal() {
  try { return JSON.parse(localStorage.getItem(storageKey.value) || 'null') } catch { return null }
}
function writeLocal() {
  try { localStorage.setItem(storageKey.value, JSON.stringify(payload())) } catch { /* 隐私模式等场景允许失败 */ }
}
function clearLocal() {
  try { localStorage.removeItem(storageKey.value) } catch { /* 同上 */ }
}

// 校验后应用一份偏好数据：清单外的 id 一律忽略，保持页面可用；旧枚举 style 先归一。
// 注意：不回写 sceneId —— 档位由场景下拉驱动，回写会造成 watch 回环
function applyPref(pref) {
  if (pref.avatar_id && AVATARS.some((a) => a.id === pref.avatar_id)) avatarId.value = pref.avatar_id
  const style = VOICE_STYLE_ALIASES[pref.voice_style] || pref.voice_style
  if (style && FALLBACK_VOICES.some((v) => v.style === style)) voiceStyle.value = style
  if (Number.isFinite(pref.speech_rate)) speechRate.value = Math.min(1.25, Math.max(0.75, pref.speech_rate))
  if (typeof pref.lip_sync_enabled === 'boolean') lipSyncEnabled.value = pref.lip_sync_enabled
}

function payload() {
  return {
    avatar_id: avatarId.value,
    role_id: null, // 交流身份已移除
    voice_style: voiceStyle.value,
    scene_id: sceneId.value || null,
    speech_rate: speechRate.value,
    lip_sync_enabled: lipSyncEnabled.value,
  }
}

function resetCombo() {
  // 形象 × 音色 × 节奏回到缺省组合；不动场景选择（档位由用户控制）
  avatarId.value = DEFAULTS.avatarId
  voiceStyle.value = DEFAULTS.voiceStyle
  speechRate.value = DEFAULTS.speechRate
  lipSyncEnabled.value = DEFAULTS.lipSyncEnabled
}

function resetToDefaults() {
  sceneId.value = DEFAULTS.sceneId
  resetCombo()
  savedRemote.value = false
  stopPreview()
  stage.value?.stopDemo()
}

// ── 声音试听：合成当前选中音色的示例句，播放时数字人进入说话状态 ──
const previewing = ref(false)
let previewAudio = null
let previewUrl = null

function stopPreview() {
  if (previewAudio) {
    previewAudio.pause()
    previewAudio.onended = previewAudio.onerror = previewAudio.onloadedmetadata = null
    previewAudio = null
  }
  if (previewUrl) { URL.revokeObjectURL(previewUrl); previewUrl = null }
  previewing.value = false
}

async function previewVoice() {
  if (previewing.value) return stopPreview() // 再次点击 = 停止
  stopPreview()
  const sample = `Hi, I'm ${nameOf(avatar.value)}. So nice to meet you! Let's start practicing together.`
  previewing.value = true
  try {
    const blob = await synthesizeSpeech(sample, voiceStyle.value, speechRate.value)
    const url = URL.createObjectURL(blob)
    const audio = new Audio(url)
    previewUrl = url
    previewAudio = audio
    // 音频元数据就绪后按真实时长驱动"说话"状态；结束或出错统一复位
    audio.onloadedmetadata = () => stage.value?.playDemo('speaking', Math.ceil((audio.duration || 4) * 1000) + 300)
    audio.onended = stopPreview
    audio.onerror = () => { stopPreview(); notify('音频播放失败，请重试') }
    await audio.play()
  } catch (error) {
    stopPreview()
    notify(error?.message || '试听失败，请稍后重试')
  }
}

// ── 偏好读取：按当前场景档读数据库；偏好是「每场景一份」，切换场景即加载对应配置 ──
async function load() {
  if (!session.token) {
    savedRemote.value = false
    return // 游客不读云档，保留当前界面组合
  }
  try {
    const pref = await getAvatarPreference(sceneId.value)
    if (pref && pref.avatar_id) {
      applyPref(pref) // 该场景档有已保存配置：采用
      savedRemote.value = true
      return
    }
    // 该场景档从未保存：跟随推荐档尝试继承本机旧偏好作升级路径，具体场景回缺省组合
    if (!sceneId.value) {
      const local = readLocal()
      if (local) applyPref(local)
    } else {
      resetCombo()
    }
    savedRemote.value = false
  } catch { /* 后端不可用：保留当前界面组合 */ }
}

// 场景切换 → 加载目标场景档的配置（含未配置场景回缺省）
watch(sceneId, () => load())

async function save() {
  // 未登录不允许保存：偏好绑定账户，引导先登录（游客仍可浏览与试玩）
  if (!session.token) {
    savedRemote.value = false
    return notify('登录后才能保存偏好，可点击左下角「游客」登录或注册')
  }
  writeLocal() // 本机始终留一份，断网时选择不丢失
  try {
    const pref = await saveAvatarPreference(payload())
    if (pref?.avatar_id) applyPref(pref)
    savedRemote.value = true
    notify('偏好已保存')
  } catch (error) {
    notify(error.message)
  }
}

async function reset() {
  clearLocal()
  if (session.token) {
    try { await resetAvatarPreference(sceneId.value) } catch (error) { return notify(error.message) }
  }
  resetCombo() // 只重置当前场景档的组合，保留场景选择
  savedRemote.value = false
  notify('已恢复默认设置')
}

// 账户切换（登录/登出/换号）时回到缺省并重读偏好
watch(() => session.user?.id, () => {
  resetToDefaults()
  load()
  loadScenes()
})

load()
loadScenes()
probeVoices()
onBeforeUnmount(() => { clearTimeout(toastTimer); stopPreview() })

const states = [
  { value: 'idle', label: '待机' },
  { value: 'listening', label: '倾听' },
  { value: 'thinking', label: '思考' },
  { value: 'speaking', label: '说话' },
]
</script>

<template>
  <section class="avatar-page">
    <!-- 工具行：场景选择（流程第一步）+ 操作按钮 -->
    <div class="av-toolbar">
      <div class="toolbar-left">
        <AppSelect v-model="sceneId" :options="sceneOptions" label="场景" aria-label="训练场景" />
      </div>
      <div class="toolbar-actions">
        <button class="ghost-button" type="button" @click="reset">恢复默认</button>
        <button class="primary-button slim" type="button" :title="session.token ? '保存偏好到账户' : '登录后才能保存偏好'" @click="save">
          <AppIcon name="check" :size="14" />保存设置
        </button>
      </div>
    </div>

    <!-- 主体：左状态预览 + 右设置（先形象后音色） -->
    <div class="av-layout">
      <section class="preview-card" aria-label="状态预览">
        <AvatarStage
          ref="stage"
          :avatar="avatar"
          :size="440"
          :lip-sync="lipSyncEnabled ? 'state' : 'off'"
          @state-change="previewState = $event"
        />
        <div class="state-section">
          <div class="state-buttons">
            <button
              v-for="s in states"
              :key="s.value"
              type="button"
              :aria-pressed="previewState === s.value"
              :class="{ active: previewState === s.value }"
              @click="stage?.playDemo(s.value)"
            >{{ s.label }}</button>
          </div>
        </div>
      </section>

      <aside class="settings">
        <!-- 01 形象 -->
        <section class="settings-card">
          <div class="card-heading"><h2>形象</h2><span class="card-no">01</span></div>
          <div class="avatar-list" role="radiogroup" aria-label="数字人形象">
            <button
              v-for="a in AVATARS"
              :key="a.id"
              type="button"
              role="radio"
              class="avatar-chip"
              :class="{ active: avatarId === a.id }"
              :aria-checked="avatarId === a.id"
              @click="avatarId = a.id"
            >
              <span class="chip-thumb" :style="{ background: accentOf(a.theme) }">
                <CharacterPortrait :character="a.id" :animated="false" :theme="a.theme" :name="nameOf(a)" />
              </span>
              <span class="chip-text">
                <b>{{ nameOf(a) }}</b>
                <small>{{ cnNameOf(a) }}</small>
              </span>
            </button>
          </div>
          <p class="character-description"><b>{{ nameOf(avatar) }}</b><span>{{ avatar.description }}</span></p>
          <p class="helper">任意形象都可以搭配任意音色进入当前场景。</p>
        </section>

        <!-- 02 声音与节奏 -->
        <section class="settings-card">
          <div class="card-heading"><h2>声音与节奏</h2><span class="card-no">02</span></div>
          <VoiceSettings
            v-model:voice-style="voiceStyle"
            v-model:speech-rate="speechRate"
            v-model:lip-sync-enabled="lipSyncEnabled"
            :voices="voices"
            :previewing="previewing"
            @preview="previewVoice"
          />
        </section>
      </aside>
    </div>

    <!-- 轻提示：位置与样式对齐 Scenes / Knowledge -->
    <transition name="toast">
      <div v-if="toast" class="toast" role="status" aria-live="polite">{{ toast }}</div>
    </transition>
  </section>
</template>

<style scoped>
/* 布局与类名对齐 Scenes.vue：工具行 → 内容区 → toast；全部使用全局设计令牌 */
.avatar-page { flex: 1; min-height: 0; display: flex; flex-direction: column; padding: 22px 28px 32px; overflow-y: auto; }

/* ===== 工具行：场景在前，操作在后 ===== */
.av-toolbar { display: flex; flex: 0 0 auto; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 14px; }
.toolbar-left { display: flex; align-items: center; gap: 10px; min-width: 0; }
.toolbar-actions { display: flex; align-items: center; gap: 9px; }

/* 按钮：与 Scenes.vue 同款（覆盖全局 primary-button 的表单样式） */
.ghost-button { display: inline-flex; align-items: center; gap: 6px; height: 34px; padding: 0 14px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--ink-soft); font-size: 13.5px; transition: border-color .15s, color .15s, background .15s; }
.ghost-button:hover { border-color: #d5d7e6; color: var(--ink); background: #fafafd; }
.primary-button.slim { width: auto; height: 34px; margin-top: 0; gap: 6px; padding: 0 15px; justify-content: center; display: inline-flex; }

/* ===== 主体布局：两列等高，底边对齐 ===== */
.av-layout { display: grid; grid-template-columns: minmax(0, 1.08fr) minmax(300px, 0.92fr); gap: 14px; max-width: 1080px; width: 100%; margin: 0 auto; align-items: stretch; }
.preview-card { display: flex; flex-direction: column; min-width: 0; height: 100%; padding: 16px; border: 1px solid var(--line); border-radius: 12px; background: var(--surface); }
/* 舞台占满卡片剩余高度，宽度按 4:5 比例由高度推出并限制上限 */
.preview-card :deep(.stage) { flex: 1 1 auto; width: auto !important; max-width: 440px; min-height: 0; margin: 0 auto; }
.preview-card :deep(.state-section) { flex: 0 0 auto; }

/* 状态按钮行：预览卡内唯一附加内容 */
.state-section { border-top: 1px solid var(--line); padding-top: 13px; margin-top: 14px; }
.state-buttons { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
.state-buttons button { background: var(--surface); color: var(--ink-soft); border: 1px solid var(--line); border-radius: 8px; padding: 9px 0; cursor: pointer; font-size: 12.5px; transition: border-color .15s, background .15s, color .15s; }
.state-buttons button:hover { border-color: #d5d7e6; color: var(--ink); }
.state-buttons button.active { background: var(--brand-soft); border-color: var(--brand); color: var(--brand-deep, var(--brand)); font-weight: 500; }

/* ===== 右侧设置卡：声音卡吃掉剩余高度，保证与左列等高 ===== */
.settings { display: grid; grid-template-rows: auto 1fr; gap: 14px; min-width: 0; height: 100%; }
.settings-card { border: 1px solid var(--line); border-radius: 12px; background: var(--surface); padding: 15px 16px; min-width: 0; }
.card-heading { display: flex; justify-content: space-between; align-items: center; margin-bottom: 13px; }
.card-heading h2 { margin: 0; font-size: 13.5px; font-weight: 600; color: var(--ink); }
.card-no { color: var(--faint); font-size: 11.5px; font-variant-numeric: tabular-nums; }

/* 形象选择：两列卡片网格 */
.avatar-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.avatar-chip {
  display: flex; align-items: center; gap: 10px; padding: 7px 10px 7px 7px;
  border: 1px solid var(--line); border-radius: 10px; background: var(--surface);
  cursor: pointer; text-align: left; transition: border-color .16s, background .16s;
}
.avatar-chip:hover { border-color: #d5d7e6; }
.avatar-chip.active { border-color: var(--brand); background: var(--brand-soft); }
.chip-thumb { position: relative; display: grid; width: 38px; height: 44px; flex: 0 0 38px; place-items: end center; overflow: hidden; border-radius: 8px; }
.chip-thumb :deep(svg) { position: absolute; bottom: -6px; width: 52px; height: 62px; }
.chip-text { display: flex; min-width: 0; flex-direction: column; gap: 1px; }
.chip-text b { font-size: 13.5px; font-weight: 500; color: var(--ink); }
.chip-text small { font-size: 11px; color: var(--muted); }
.avatar-chip.active .chip-text b { color: var(--brand-deep, var(--brand)); }
.character-description { display: flex; flex-direction: column; gap: 5px; margin: 14px 0 0; padding: 10px 12px; border-radius: 8px; background: var(--bg); font-size: 11.5px; line-height: 1.6; color: var(--muted); }.character-description b { font-size: 12px; color: var(--ink-soft); font-weight: 500; }
.helper { font-size: 12px; color: var(--muted); line-height: 1.7; margin: 11px 0 0; text-wrap: pretty; }

/* 轻提示：位置与样式对齐 Scenes.vue */
.toast { position: fixed; top: 58px; left: 50%; z-index: 50; transform: translate(-50%, 0); max-width: min(460px, calc(100vw - 40px)); padding: 9px 16px; border-radius: 9px; background: #2b2d4e; color: #fff; font-size: 13px; box-shadow: 0 10px 28px rgba(34, 37, 59, .22); }
.toast-enter-active, .toast-leave-active { transition: opacity .2s, transform .2s; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translate(-50%, -6px); }

button:focus-visible { outline: 2px solid var(--brand); outline-offset: 2px; }

@media (max-width: 960px) {
  .av-layout { grid-template-columns: minmax(0, 1fr) minmax(280px, 0.9fr); gap: 12px; }
}
@media (max-width: 860px) {
  .av-toolbar { flex-wrap: wrap; }
  .toolbar-actions { margin-left: auto; }
  .av-layout { grid-template-columns: minmax(0, 1fr); }
  /* 单列堆叠时取消等高约束，舞台回到固定宽度 */
  .preview-card { height: auto; }
  .preview-card :deep(.stage) { flex: 0 0 auto; width: 100% !important; }
  .settings { height: auto; grid-template-rows: none; }
}
</style>

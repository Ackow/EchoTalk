<script setup>
// 数字人角色页：分为「场景配置」（为每个场景挑选已创建好的角色与音色）和「创作角色」（先捏脸定制并保存，再在场景配置中选用）。
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import AppSelect from '../components/AppSelect.vue'
import AppTabs from '../components/AppTabs.vue'
import AvatarStage from '../components/avatar/AvatarStage.vue'
import CharacterPortrait from '../components/avatar/CharacterPortrait.vue'
import AppearanceCustomizer from '../components/avatar/AppearanceCustomizer.vue'
import VoiceSettings from '../components/avatar/VoiceSettings.vue'
import {
  FALLBACK_AVATARS, FALLBACK_VOICES, VOICE_STYLE_ALIASES,
  cloneMarketAvatar, createAvatar, deleteAvatar, fetchTtsVoices, getAvatarPreference, listAvatars,
  listMarketAvatars, publishAvatar, resetAvatarPreference, saveAvatarPreference, synthesizeSpeech,
  uncloneMarketAvatar, updateAvatar,
} from '../api/avatar'
import { resolveAppearance, resolveRoleVoiceStyle } from '../components/avatar/avatarAppearance'
import { getScene, listScenes } from '../api/scenes'
import { session } from '../auth/session'
import { usePageLoading } from '../app/loading'

const avatars = ref([...FALLBACK_AVATARS])
const DEFAULTS = { avatarId: 'leo_2d', voiceStyle: 'emma', sceneId: '', speechRate: 1, lipSyncEnabled: true }

const activeTab = ref('assign') // 'assign' | 'studio' | 'market'
const stage = ref(null)
const studioStage = ref(null)
const marketStage = ref(null)
const marketAvatars = ref([])
const marketKeyword = ref('')
const selectedMarketId = ref(null)
const cloningId = ref(null)
const sceneId = ref(DEFAULTS.sceneId)
const avatarId = ref(DEFAULTS.avatarId)
const voiceStyle = ref(DEFAULTS.voiceStyle)
const speechRate = ref(DEFAULTS.speechRate)
const lipSyncEnabled = ref(DEFAULTS.lipSyncEnabled)
const savedRemote = ref(false)
const toast = ref('')
const previewState = ref('idle')
const voices = ref(FALLBACK_VOICES.map((v) => ({ ...v })))
let toastTimer

const notify = (message) => {
  toast.value = message
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.value = ''), 2800)
}

// ── 声音渠道探测 ──
async function probeVoices() {
  const list = await fetchTtsVoices()
  if (!Array.isArray(list)) return
  voices.value = voices.value.map((v) => {
    const found = list.find((item) => item.style === v.style)
    return found ? { ...v, available: Boolean(found.available) } : v
  })
}

const avatar = computed(() => avatars.value.find((a) => a.id === avatarId.value) || avatars.value[0])
const customAvatars = computed(() => avatars.value.filter((a) => !a.is_builtin && !['leo_2d', 'emily_2d', 'david_2d', 'sarah_2d'].includes(a.id)))
const nameOf = (a) => (a?.display_name || 'Leo').split(' · ')[0]
const cnNameOf = (a) => (a?.display_name || '').split(' · ')[1] || ''

const THEME_ACCENT = { violet: '#9282bb', teal: '#74b3a0', blue: '#7d95c6', amber: '#cba468' }
const accentOf = (theme) => THEME_ACCENT[theme] || '#8b73dd'

// ── 创作角色工作室状态 ──
const editingCustomId = ref(null)
const savingStudio = ref(false)
const studioForm = ref({
  display_name: '',
  description: '',
  theme: 'violet',
  is_public: false,
  appearance: resolveAppearance('leo_2d'),
})

function startNewCustom() {
  editingCustomId.value = null
  studioForm.value = {
    display_name: '',
    description: '',
    theme: 'violet',
    is_public: false,
    appearance: resolveAppearance('leo_2d'),
  }
}

function editCustomAvatar(item) {
  editingCustomId.value = item.id
  studioForm.value = {
    display_name: item.display_name || '',
    description: item.description || '',
    theme: item.theme || 'violet',
    is_public: Boolean(item.is_public),
    appearance: resolveAppearance('leo_2d', item.appearance),
  }
}

const studioPreviewAvatar = computed(() => ({
  id: 'leo_2d',
  display_name: studioForm.value.display_name.trim() || 'New Avatar',
  theme: studioForm.value.theme,
  appearance: studioForm.value.appearance,
}))

async function saveStudioAvatar(publish = false) {
  if (!session.token) {
    return notify('登录后才能创建并保存自定义角色')
  }
  const name = studioForm.value.display_name.trim()
  if (!name) return notify('请先填写角色名称')
  savingStudio.value = true
  try {
    const nextPublic = publish ? true : studioForm.value.is_public
    const body = {
      display_name: name,
      theme: studioForm.value.theme,
      description: studioForm.value.description.trim() || '自定义角色',
      tagline: studioForm.value.description.trim() || '用户创作的专属交流伙伴',
      greeting: `Hi, I'm ${name.split(' · ')[0]}. Let's practice together!`,
      default_voice: voiceStyle.value || 'emma',
      is_public: nextPublic,
      appearance: studioForm.value.appearance,
    }
    const wasEditing = Boolean(editingCustomId.value)
    const saved = wasEditing
      ? await updateAvatar(editingCustomId.value, body)
      : await createAvatar(body)
    await loadAvatars()
    if (saved?.id) {
      editingCustomId.value = saved.id
      avatarId.value = saved.id
      studioForm.value.is_public = Boolean(saved.is_public)
    }
    if (publish) notify('角色已公开发布！所有用户均可在「场景配置」中选用')
    else notify(wasEditing ? '自定义角色已更新，可在「场景配置」中选用' : '新角色已创建，可在「场景配置」中选用')
  } catch (err) {
    notify(err?.message || '保存角色失败，请重试')
  } finally {
    savingStudio.value = false
  }
}

async function togglePublishStudioAvatar() {
  if (!session.token) return notify('登录后才能发布自定义角色')
  if (!editingCustomId.value) return saveStudioAvatar(true)
  savingStudio.value = true
  try {
    const next = !studioForm.value.is_public
    const updated = await publishAvatar(editingCustomId.value, next)
    studioForm.value.is_public = Boolean(updated?.is_public)
    await loadAvatars()
    notify(studioForm.value.is_public ? '角色已公开发布！' : '已设为仅自己可见')
  } catch (err) {
    notify(err?.message || '操作失败，请重试')
  } finally {
    savingStudio.value = false
  }
}

async function removeCustomAvatar(item) {
  if (!session.token) return
  try {
    await deleteAvatar(item.id)
    if (editingCustomId.value === item.id) startNewCustom()
    if (avatarId.value === item.id) avatarId.value = DEFAULTS.avatarId
    await loadAvatars()
    notify('已删除自定义角色')
  } catch (err) {
    notify(err?.message || '删除失败')
  }
}

async function loadAvatars() {
  try {
    const list = await listAvatars()
    if (Array.isArray(list) && list.length) avatars.value = list
  } catch { /* 回退本地清单 */ }
}

async function loadMarketAvatars() {
  try {
    const list = await listMarketAvatars()
    marketAvatars.value = list
    if (!selectedMarketId.value && list.length) selectedMarketId.value = list[0].id
  } catch {
    marketAvatars.value = []
  }
}

const filteredMarketAvatars = computed(() => {
  const kw = marketKeyword.value.trim().toLowerCase()
  if (!kw) return marketAvatars.value
  return marketAvatars.value.filter((item) =>
    `${item.display_name} ${item.description} ${item.author_name}`.toLowerCase().includes(kw)
  )
})

const selectedMarketAvatar = computed(() =>
  marketAvatars.value.find((a) => a.id === selectedMarketId.value) || filteredMarketAvatars.value[0] || avatar.value
)

function isMarketAcquired(item) {
  return Boolean(item?.is_acquired) || customAvatars.value.some((a) => a.source_avatar_id === item.id)
}

async function toggleMarketAvatar(item) {
  if (!session.token) return notify('登录后才能获取或取消角色')
  cloningId.value = item.id
  try {
    if (isMarketAcquired(item)) {
      const removedIds = new Set(
        customAvatars.value.filter((a) => a.source_avatar_id === item.id).map((a) => a.id)
      )
      await uncloneMarketAvatar(item.id)
      await Promise.all([loadAvatars(), loadMarketAvatars()])
      if (removedIds.has(avatarId.value)) {
        avatarId.value = avatars.value[0]?.id || 'leo_2d'
      }
      notify(`已取消获取「${nameOf(item)}」`)
    } else {
      const cloned = await cloneMarketAvatar(item.id)
      await Promise.all([loadAvatars(), loadMarketAvatars()])
      if (cloned?.id) avatarId.value = cloned.id
      notify(`已获取「${nameOf(item)}」，可在「场景配置」中选用`)
    }
  } catch (err) {
    notify(err?.message || '操作失败，请重试')
  } finally {
    cloningId.value = null
  }
}

watch(activeTab, (tab) => {
  if (tab === 'market') void loadMarketAvatars()
})

// ── 场景选项与默认角色/音色解析 ──
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

const sceneDefaultsCache = new Map()
async function getSceneDefaults(id) {
  if (!id) return { avatarId: DEFAULTS.avatarId, voiceStyle: DEFAULTS.voiceStyle }
  if (sceneDefaultsCache.has(id)) return sceneDefaultsCache.get(id)
  try {
    const { data } = await getScene(id)
    const role = data?.package?.roles?.[0]
    const resolved = {
      avatarId: role?.avatar && avatars.value.some((a) => a.id === role.avatar) ? role.avatar : DEFAULTS.avatarId,
      voiceStyle: resolveRoleVoiceStyle(role?.voice, FALLBACK_VOICES.map((v) => v.style)),
    }
    sceneDefaultsCache.set(id, resolved)
    return resolved
  } catch {
    return { avatarId: DEFAULTS.avatarId, voiceStyle: DEFAULTS.voiceStyle }
  }
}

async function applySceneDefaults(id = sceneId.value) {
  const target = await getSceneDefaults(id)
  if (id !== sceneId.value) return
  avatarId.value = target.avatarId
  voiceStyle.value = target.voiceStyle
  speechRate.value = DEFAULTS.speechRate
  lipSyncEnabled.value = DEFAULTS.lipSyncEnabled
}

// ── 偏好读写 ──
const storageKey = computed(() => `echotalk-avatar-2d:${session.user?.id ?? 'guest'}`)
function readLocal() {
  try { return JSON.parse(localStorage.getItem(storageKey.value) || 'null') } catch { return null }
}
function writeLocal() {
  try { localStorage.setItem(storageKey.value, JSON.stringify(payload())) } catch { /* ignore */ }
}
function clearLocal() {
  try { localStorage.removeItem(storageKey.value) } catch { /* ignore */ }
}

function applyPref(pref) {
  if (pref.avatar_id && avatars.value.some((a) => a.id === pref.avatar_id)) avatarId.value = pref.avatar_id
  const style = VOICE_STYLE_ALIASES[pref.voice_style] || pref.voice_style
  if (style && FALLBACK_VOICES.some((v) => v.style === style)) voiceStyle.value = style
  if (Number.isFinite(pref.speech_rate)) speechRate.value = Math.min(1.25, Math.max(0.75, pref.speech_rate))
  if (typeof pref.lip_sync_enabled === 'boolean') lipSyncEnabled.value = pref.lip_sync_enabled
}

function payload() {
  return {
    avatar_id: avatarId.value,
    role_id: null,
    voice_style: voiceStyle.value,
    scene_id: sceneId.value || null,
    speech_rate: speechRate.value,
    lip_sync_enabled: lipSyncEnabled.value,
  }
}

function resetCombo() {
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

// ── 声音试听 ──
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
  if (previewing.value) return stopPreview()
  stopPreview()
  const sample = `Hi, I'm ${nameOf(avatar.value)}. So nice to meet you! Let's start practicing together.`
  previewing.value = true
  try {
    const blob = await synthesizeSpeech(sample, voiceStyle.value, speechRate.value)
    const url = URL.createObjectURL(blob)
    const audio = new Audio(url)
    previewUrl = url
    previewAudio = audio
    audio.onloadedmetadata = () => stage.value?.playDemo('speaking', Math.ceil((audio.duration || 4) * 1000) + 300)
    audio.onended = stopPreview
    audio.onerror = () => { stopPreview(); notify('音频播放失败，请重试') }
    await audio.play()
  } catch (error) {
    stopPreview()
    notify(error?.message || '试听失败，请稍后重试')
  }
}

// ── 偏好加载 ──
async function load() {
  const targetSceneId = sceneId.value
  if (!session.token) {
    savedRemote.value = false
    if (targetSceneId) await applySceneDefaults(targetSceneId)
    return
  }
  try {
    const pref = await getAvatarPreference(targetSceneId)
    if (targetSceneId !== sceneId.value) return
    if (pref && pref.avatar_id) {
      applyPref(pref)
      savedRemote.value = true
      return
    }
    if (!targetSceneId) {
      const local = readLocal()
      if (local) applyPref(local)
      else resetCombo()
    } else {
      await applySceneDefaults(targetSceneId)
    }
    savedRemote.value = false
  } catch { /* 后端不可用：保留当前界面组合 */ }
}

watch(sceneId, () => load())

async function save() {
  if (!session.token) {
    savedRemote.value = false
    return notify('登录后才能保存偏好，可点击左下角「游客」登录或注册')
  }
  writeLocal()
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
  await applySceneDefaults(sceneId.value)
  savedRemote.value = false
  notify('已恢复默认设置')
}

watch(() => session.user?.id, () => {
  resetToDefaults()
  loadAvatars()
  load()
  loadScenes()
})

const finishLoading = usePageLoading()
Promise.allSettled([loadAvatars(), load(), loadScenes(), probeVoices()]).then(finishLoading)
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
    <!-- 顶部工具栏：模式 Tab + 场景选择 + 操作按钮 -->
    <div class="av-toolbar">
      <div class="toolbar-left">
        <AppTabs
          v-model="activeTab"
          :options="[
            { value: 'assign', label: '场景配置' },
            { value: 'studio', label: '创作角色' },
            { value: 'market', label: '角色市场' },
          ]"
          aria-label="数字人工作区模式"
        />
        <AppSelect v-if="activeTab === 'assign'" v-model="sceneId" :options="sceneOptions" label="场景" aria-label="训练场景" />
      </div>

      <div v-if="activeTab === 'assign'" class="toolbar-actions">
        <button class="ghost-button" type="button" @click="reset">恢复默认</button>
        <button class="primary-button slim" type="button" :title="session.token ? '保存偏好到账户' : '登录后才能保存偏好'" @click="save">
          <AppIcon name="check" :size="14" />保存设置
        </button>
      </div>
      <div v-else-if="activeTab === 'studio'" class="toolbar-actions">
        <button class="ghost-button" type="button" @click="startNewCustom">新建角色</button>
        <button class="ghost-button publish-btn" :class="{ published: studioForm.is_public }" type="button" :disabled="savingStudio" @click="togglePublishStudioAvatar">
          <AppIcon name="globe" :size="14" />{{ studioForm.is_public ? '已发布' : '发布角色' }}
        </button>
        <button class="primary-button slim" type="button" :disabled="savingStudio" @click="saveStudioAvatar(false)">
          <AppIcon name="check" :size="14" />{{ editingCustomId ? '保存修改' : '保存为新角色' }}
        </button>
      </div>
      <div v-else class="toolbar-actions">
        <button class="ghost-button" type="button" @click="loadMarketAvatars">刷新市场</button>
        <button class="primary-button slim" type="button" @click="activeTab = 'studio'; startNewCustom()">
          <AppIcon name="plus" :size="14" />去创作角色
        </button>
      </div>
    </div>

    <!-- Tab 1: 场景配置 -->
    <div v-if="activeTab === 'assign'" class="av-layout">
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
        <section class="settings-card">
          <div class="card-heading">
            <h2>形象</h2>
            <div class="heading-actions">
              <button type="button" class="studio-link" @click="activeTab = 'studio'; startNewCustom()">+ 创作新角色</button>
              <span class="card-no">01</span>
            </div>
          </div>
          <div class="avatar-list" role="radiogroup" aria-label="数字人形象">
            <button
              v-for="a in avatars"
              :key="a.id"
              type="button"
              role="radio"
              class="avatar-chip"
              :class="{ active: avatarId === a.id }"
              :aria-checked="avatarId === a.id"
              @click="avatarId = a.id"
            >
              <span class="chip-thumb" :style="{ background: accentOf(a.theme) }">
                <CharacterPortrait :character="a.id" :appearance="a.appearance" :animated="false" :theme="a.theme" :name="nameOf(a)" />
              </span>
              <span class="chip-text">
                <b>{{ nameOf(a) }}</b>
                <small>{{ cnNameOf(a) || (a.is_public && !a.is_owner ? `公开 · ${a.author_name || '社区'}` : a.is_public ? '已发布' : '自定义角色') }}</small>
              </span>
            </button>
          </div>
          <p class="character-description"><b>{{ nameOf(avatar) }}</b><span>{{ avatar.description }}</span></p>
          <p class="helper">任意形象都可以搭配任意音色进入当前场景；如需新造型，请先在「创作角色」中制作保存。</p>
        </section>

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

    <!-- Tab 2: 创作角色 -->
    <div v-else-if="activeTab === 'studio'" class="av-layout">
      <section class="preview-card" aria-label="创作角色预览">
        <AvatarStage
          ref="studioStage"
          :avatar="studioPreviewAvatar"
          :appearance="studioForm.appearance"
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
              @click="studioStage?.playDemo(s.value)"
            >{{ s.label }}</button>
          </div>
        </div>
      </section>

      <aside class="settings studio-settings">
        <section class="settings-card">
          <div class="card-heading"><h2>角色信息与外观</h2><span class="card-no">01</span></div>
          <div class="studio-fields">
            <label class="field-item">
              <span>角色名称</span>
              <input v-model="studioForm.display_name" type="text" maxlength="40" placeholder="例如：Alex · 亚历克斯" />
            </label>
            <label class="field-item">
              <span>角色简介</span>
              <input v-model="studioForm.description" type="text" maxlength="80" placeholder="例如：风趣的伦敦咖啡师" />
            </label>
          </div>
          <AppearanceCustomizer
            character-id="leo_2d"
            :model-value="studioForm.appearance"
            @update:model-value="studioForm.appearance = $event"
            @reset="studioForm.appearance = resolveAppearance('leo_2d')"
          />
        </section>
      </aside>
    </div>

    <!-- Tab 3: 角色市场 -->
    <div v-else class="av-layout">
      <section class="preview-card" aria-label="市场角色预览">
        <AvatarStage
          ref="marketStage"
          :avatar="selectedMarketAvatar"
          :appearance="selectedMarketAvatar?.appearance"
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
              @click="marketStage?.playDemo(s.value)"
            >{{ s.label }}</button>
          </div>
        </div>
      </section>

      <aside class="settings studio-settings">
        <section class="settings-card market-card">
          <div class="card-heading">
            <h2>角色市场</h2>
            <span class="card-no">{{ filteredMarketAvatars.length }}</span>
          </div>
          <label class="market-search">
            <AppIcon name="search" :size="14" />
            <input v-model="marketKeyword" type="search" placeholder="搜索角色名、简介或作者" />
          </label>
          <div v-if="filteredMarketAvatars.length" class="market-list">
            <div
              v-for="item in filteredMarketAvatars"
              :key="item.id"
              class="market-item"
              :class="{ active: selectedMarketAvatar?.id === item.id }"
              @click="selectedMarketId = item.id"
            >
              <span class="chip-thumb" :style="{ background: accentOf(item.theme) }">
                <CharacterPortrait :character="item.id" :appearance="item.appearance" :animated="false" :name="nameOf(item)" />
              </span>
              <div class="market-meta">
                <div class="market-title">
                  <b>{{ item.display_name }}</b>
                  <span class="author-tag">{{ item.author_name || '社区创作者' }}</span>
                </div>
                <p>{{ item.description || item.tagline || '社区分享的数字人角色' }}</p>
              </div>
              <button
                v-if="!item.is_owner"
                type="button"
                class="acquire-btn"
                :class="{ acquired: isMarketAcquired(item) }"
                :disabled="cloningId === item.id"
                @click.stop="toggleMarketAvatar(item)"
              >
                <template v-if="cloningId === item.id">{{ isMarketAcquired(item) ? '取消中...' : '获取中...' }}</template>
                <template v-else-if="isMarketAcquired(item)">
                  <span class="acq-default">已获取</span>
                  <span class="acq-hover">取消获取</span>
                </template>
                <template v-else>获取角色</template>
              </button>
              <span v-else class="owner-badge">我的发布</span>
            </div>
          </div>
          <p v-else class="helper market-empty">
            暂无其他创作者发布的公开角色。你可以在「创作角色」中设计一个新伙伴并点击「发布角色」，成为第一位分享者！
          </p>
        </section>
      </aside>
    </div>

    <transition name="toast">
      <div v-if="toast" class="toast" role="status" aria-live="polite">{{ toast }}</div>
    </transition>
  </section>
</template>

<style scoped>
.avatar-page { flex: 1; min-height: 0; display: flex; flex-direction: column; padding: 18px clamp(18px, 2.4vw, 32px) 22px; overflow-y: auto; background: #faf9ff; }

/* ===== 工具行 ===== */
.av-toolbar { display: flex; flex: 0 0 auto; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 14px; }
.toolbar-left { display: flex; align-items: center; gap: 12px; min-width: 0; flex-wrap: wrap; }
.toolbar-actions { display: flex; align-items: center; gap: 9px; }

.ghost-button { display: inline-flex; align-items: center; gap: 6px; height: 38px; box-sizing: border-box; padding: 0 14px; border: 1.5px solid #e9e5f1; border-bottom-width: 3px; border-radius: 12px; background: var(--surface); color: var(--ink-soft); font-size: 13.5px; font-weight: 650; transition: border-color .15s, color .15s, background .15s; }
.ghost-button:hover { border-color: #d5d7e6; color: var(--ink); background: #fafafd; }
.primary-button.slim { width: auto; height: 38px; box-sizing: border-box; margin-top: 0; gap: 6px; padding: 0 15px; justify-content: center; display: inline-flex; border: 1.5px solid #8067d1; border-bottom-width: 3px; border-radius: 12px; background: #8b73dd; font-size: 13.5px; font-weight: 650; }
.primary-button.slim:disabled { opacity: 0.6; cursor: not-allowed; }

/* ===== 主体布局：左右等高对齐 ===== */
.av-layout { display: grid; grid-template-columns: minmax(0, 0.96fr) minmax(320px, 1.04fr); gap: 16px; max-width: 1080px; width: 100%; min-height: 580px; margin: 0 auto; align-items: stretch; }
.preview-card { display: flex; flex-direction: column; align-self: stretch; box-sizing: border-box; min-width: 0; min-height: 0; padding: 18px; border: 2px solid #ebe7f5; border-bottom: 5px solid #e5def1; border-radius: 19px; background: #fff; }
.preview-card :deep(.stage) { flex: 1 1 auto; width: 100% !important; max-width: 100%; height: 100%; aspect-ratio: auto; min-height: 460px; margin: 0 auto; }
.preview-card :deep(.state-section) { flex: 0 0 auto; }

.state-section { border-top: 1px solid #efedf5; padding-top: 13px; margin-top: 14px; }
.state-buttons { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.state-buttons button { min-height: 38px; background: var(--surface); color: var(--ink-soft); border: 1.5px solid #e9e5f1; border-bottom-width: 3px; border-radius: 12px; padding: 9px 0; cursor: pointer; font-size: 12.5px; font-weight: 600; transition: border-color .15s, background .15s, color .15s; }
.state-buttons button:hover { border-color: #d5d7e6; color: var(--ink); }
.state-buttons button.active { border-color: #9b83e5; border-bottom-color: #8067d1; background: #f0eaff; color: #654ab8; }

.settings { display: grid; grid-template-rows: auto 1fr; gap: 16px; align-self: stretch; min-width: 0; min-height: 0; }
.studio-settings { grid-template-rows: 1fr; min-height: 0; }
.studio-settings .settings-card { box-sizing: border-box; height: 100%; overflow-y: auto; }
.publish-btn.published { border-color: #34d399; border-bottom-color: #10b981; background: #ecfdf5; color: #047857; }

/* 角色市场 */
.market-card { display: flex; flex-direction: column; }
.market-search {
  display: flex; align-items: center; gap: 8px; height: 36px; padding: 0 12px; margin-bottom: 12px;
  border-radius: 11px; border: 1.5px solid #e6dff5; background: #faf9ff; color: #7c7693;
}
.market-search input { flex: 1; min-width: 0; border: 0; background: transparent; color: #2d294b; font-size: 13px; outline: none; }
.market-list { display: grid; gap: 8px; }
.market-item {
  display: flex; align-items: center; gap: 11px; padding: 9px 11px; border-radius: 14px;
  border: 1.5px solid #ece8f4; border-bottom-width: 3px; background: #fff; cursor: pointer;
  transition: border-color .15s, background .15s;
}
.market-item:hover { border-color: #cfc1f1; background: #fcfaff; }
.market-item.active { border-color: #a58ee9; border-bottom-color: #8067d1; background: #f3efff; }
.market-meta { flex: 1; min-width: 0; }
.market-title { display: flex; align-items: center; gap: 7px; }
.market-title b { font-size: 13.5px; font-weight: 600; color: #2d294b; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.author-tag { font-size: 11px; padding: 1px 7px; border-radius: 999px; background: #f2edff; color: #6d55c7; font-weight: 600; flex: 0 0 auto; }
.market-meta p { margin: 2px 0 0; font-size: 11.5px; color: #7c7693; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.acquire-btn {
  flex: 0 0 auto; min-width: 76px; height: 30px; padding: 0 11px; border-radius: 9px;
  border: 1.5px solid #8067d1; border-bottom-width: 2.5px; background: #8b73dd; color: #fff;
  font-size: 12px; font-weight: 600; cursor: pointer; transition: all .15s ease;
}
.acquire-btn:hover { background: #7c62d6; }
.acquire-btn.acquired { border-color: #cbd5e1; border-bottom-color: #94a3b8; background: #f8fafc; color: #475569; }
.acquire-btn.acquired .acq-hover { display: none; }
.acquire-btn.acquired:hover { border-color: #fca5a5; border-bottom-color: #ef4444; background: #fef2f2; color: #dc2626; }
.acquire-btn.acquired:hover .acq-default { display: none; }
.acquire-btn.acquired:hover .acq-hover { display: inline; }
.acquire-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.owner-badge { flex: 0 0 auto; font-size: 11.5px; font-weight: 600; color: #059669; padding: 3px 8px; border-radius: 8px; background: #ecfdf5; }
.market-empty { margin-top: 8px; }
.settings-card { border: 2px solid #ebe7f5; border-bottom: 5px solid #e5def1; border-radius: 19px; background: #fff; padding: 17px 18px; min-width: 0; }
.card-heading { display: flex; justify-content: space-between; align-items: center; margin-bottom: 13px; }
.card-heading h2 { margin: 0; font-size: 15px; font-weight: 750; color: #393451; }
.heading-actions { display: flex; align-items: center; gap: 8px; }
.studio-link { border: 0; background: transparent; padding: 2px 6px; font-size: 12px; font-weight: 600; color: #7c62d6; cursor: pointer; border-radius: 6px; }
.studio-link:hover { background: #f3efff; }
.card-no { display: grid; width: 28px; height: 28px; place-items: center; border-radius: 10px; background: #f2edff; color: #8069c7; font-size: 11.5px; font-weight: 700; font-variant-numeric: tabular-nums; }

.avatar-list {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); align-content: start; gap: 8px;
  height: 136px; overflow-y: auto; padding-right: 4px; scrollbar-gutter: stable;
}
.avatar-list::-webkit-scrollbar { width: 5px; }
.avatar-list::-webkit-scrollbar-thumb { background: #dcd4ef; border-radius: 999px; }
.avatar-list::-webkit-scrollbar-track { background: transparent; }
.avatar-chip {
  display: flex; align-items: center; gap: 10px; min-height: 62px; padding: 7px 10px 7px 7px;
  border: 1.5px solid #ece8f4; border-bottom-width: 3px; border-radius: 14px; background: #fff;
  cursor: pointer; text-align: left; transition: border-color .16s, background .16s;
}
.avatar-chip:hover { border-color: #cfc1f1; background: #fcfaff; }
.avatar-chip.active { border-color: #a58ee9; border-bottom-color: #8067d1; background: #f3efff; }
.chip-thumb { position: relative; display: grid; width: 38px; height: 44px; flex: 0 0 38px; place-items: end center; overflow: hidden; border-radius: 11px; }
.chip-thumb :deep(svg) { position: absolute; bottom: -2px; width: 46px; height: 52px; }
.chip-text { display: flex; min-width: 0; flex: 1; flex-direction: column; gap: 1px; }
.chip-text b { font-size: 13.5px; font-weight: 500; color: var(--ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chip-text small { font-size: 11px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.avatar-chip.active .chip-text b { color: var(--brand-deep, var(--brand)); }
.character-description { display: flex; flex-direction: column; gap: 5px; margin: 14px 0 0; padding: 10px 12px; border-radius: 12px; background: #f7f5fc; font-size: 11.5px; line-height: 1.6; color: var(--muted); }
.character-description b { font-size: 12px; color: var(--ink-soft); font-weight: 500; }
.helper { font-size: 12px; color: var(--muted); line-height: 1.7; margin: 11px 0 0; text-wrap: pretty; }
.empty-note { margin-top: 0; }

/* 创作角色列表与表单 */
.custom-list { display: grid; gap: 8px; }
.custom-item {
  display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 13px;
  border: 1.5px solid #ece8f4; background: #fff; cursor: pointer; transition: border-color .15s, background .15s;
}
.custom-item:hover { border-color: #cfc1f1; }
.custom-item.active { border-color: #a58ee9; background: #f3efff; }
.del-btn { border: 0; background: transparent; color: #9c95b0; font-size: 12px; padding: 4px 8px; border-radius: 7px; cursor: pointer; }
.del-btn:hover { background: #fee2e2; color: #dc2626; }

.studio-fields { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 4px; }
.field-item { display: grid; gap: 5px; }
.field-item span { font-size: 11.5px; font-weight: 600; color: #6b6584; }
.field-item input {
  height: 36px; padding: 0 11px; border-radius: 10px; border: 1.5px solid #e6dff5;
  background: #faf9ff; color: #2d294b; font-size: 13px; outline: none;
}
.field-item input:focus { border-color: #8b73dd; background: #fff; }

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
  .av-layout { grid-template-columns: minmax(0, 1fr); height: auto; min-height: 0; }
  .preview-card { height: auto; }
  .preview-card :deep(.stage) { flex: 0 0 auto; width: 100% !important; height: auto; aspect-ratio: 4 / 5; min-height: 0; }
  .settings { height: auto; grid-template-rows: none; }
  .studio-settings .settings-card { height: auto; overflow-y: visible; }
  .studio-fields { grid-template-columns: 1fr; }
}
</style>

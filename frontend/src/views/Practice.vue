<template>
  <section class="practice-page" :class="{ 'is-overlay-only': embeddedScene && phase === 'select' }">
    <PracticeScenePicker
      v-if="phase === 'select' && !resuming"
      :embedded-only="Boolean(embeddedScene)"
      :scenes="scenes"
      :loading-scenes="loadingScenes"
      :starting="starting"
      :error="error"
      :signed-in="Boolean(session.user)"
      :confirm-scene="confirmScene"
      :latest-history="latestHistory"
      :checking-history="checkingHistory"
      :history-error="historyError"
      @choose="chooseScene"
      @cancel-confirm="confirmScene = null"
      @confirm-start="confirmStart"
      @resume-scene="startScene"
    />

    <!-- 历史记录入口：会话恢复完成前不渲染场景选择页；全局遮罩显示时容器留白、不重复跑一份动画 -->
    <div v-else-if="resuming" class="practice-loading" aria-busy="true" aria-live="polite">
      <template v-if="!loadingVisible">
        <span class="loading-ring" aria-hidden="true"></span>
        <div class="loading-copy">
          <b>正在打开这次练习</b>
          <small>正在恢复对话记录与训练进度…</small>
        </div>
        <span class="loading-track" aria-hidden="true"><i></i></span>
      </template>
    </div>

    <div v-else-if="phase === 'chat'" class="chat-page">
      <!-- 延续旧版独立场景工具栏，场景操作不再挤占聊天卡头部。 -->
      <header class="session-toolbar">
        <button class="back-button" type="button" :disabled="sending" aria-label="返回场景选择" title="切换场景" @click="backToSelect"><AppIcon name="chevron-left" :size="19" /></button>
        <div class="session-heading">
          <h2>{{ sceneTitle }}</h2>
          <p>{{ categoryLabel(sceneMeta?.package?.meta?.category) }}<span>·</span>{{ finished ? '本次练习已完成' : '场景口语练习' }}<span>·</span>{{ stateInfo.turn_count || 0 }} 轮对话</p>
        </div>
        <button class="ghost-button reference-button" :class="{ active: knowledgeOpen }" type="button" @click="knowledgeOpen = !knowledgeOpen"><AppIcon name="book-open" :size="14" />{{ knowledgeOpen ? '收起参考板' : '参考板' }}</button>
      </header>

      <div class="chat-layout" :class="{ 'has-knowledge': knowledgeOpen }">
        <section class="chat-card" aria-label="对话内容">
          <header class="chat-head">
            <span class="role-avatar">
              <CharacterPortrait
                :character="companionAvatar?.id || 'leo_2d'"
                :appearance="companionAvatar?.appearance || null"
                :animated="false"
                :lip-sync="false"
                state="idle"
                :name="roleName"
              />
            </span>
            <div class="role-info"><b>{{ roleName }}</b><span class="role-status"><i class="status-dot" :class="{ busy: sending }" />{{ conversationStatus }}</span></div>
            <button class="text-toggle" type="button" :aria-pressed="showOriginal" @click="showOriginal = !showOriginal"><AppIcon name="file-text" :size="14" />{{ showOriginal ? '原文已显示' : '原文已隐藏' }}</button>
          </header>

          <!-- 阶段 / 目标 / 场景状态：原在右栏底部，上移到对话卡顶部，开口时视线不用来回跑 -->
          <div class="progress-rail">
            <button
              v-if="currentStage"
              ref="stageButton"
              type="button"
              class="rail-stage rail-stage-btn"
              :title="currentStage.guidance || currentStage.name"
              :aria-expanded="stageOpen"
              @click="toggleStagePop"
            >
              <AppIcon name="chart-line" :size="12" />
              <small>阶段</small>
              <b>{{ currentStage.name }}</b>
              <em v-if="stageTotal">{{ stageIndex }} / {{ stageTotal }}</em>
              <AppIcon v-if="stageList.length" name="chevron-down" :size="12" :class="{ flip: stageOpen }" />
            </button>
            <span v-else class="rail-stage is-open">
              <AppIcon name="chart-line" :size="12" /><small>阶段</small><b>开放交流</b>
            </span>
            <div v-if="stateRows.length" class="rail-state">
              <button ref="stateButton" class="rail-state-button" type="button" title="场景状态" :aria-expanded="stateOpen" @click="toggleStatePop">
                <AppIcon name="eye" :size="12" />状态<AppIcon name="chevron-down" :size="12" :class="{ flip: stateOpen }" />
              </button>
            </div>
          </div>

          <PracticeChatStream
            ref="chatStreamRef"
            :messages="messages"
            :sending="sending"
            :companion-avatar="companionAvatar"
            :role-name="roleName"
            :active-role="activeRole"
            :user="session.user"
            :playing-key="playingKey"
            :tts-busy-key="ttsBusyKey"
            :playback-time="playbackTime"
            :playback-duration="playbackDuration"
            :show-original="showOriginal"
            :expanded-messages="expandedMessages"
            :expanded-feedback="expandedFeedback"
            :capsule-width="capsuleWidth"
            :estimate-seconds="estimateSeconds"
            :render-message-md="renderMessageMd"
            :score-tier="scoreTier"
            :rate-label="rateLabel"
            :on-panel-enter="onPanelEnter"
            :on-panel-after-enter="onPanelAfterEnter"
            :on-panel-leave="onPanelLeave"
            :on-panel-after-leave="onPanelAfterLeave"
            :finished="finished"
            :paying="paying"
            :starting="starting"
            :report-loading="reportLoading"
            :finish-text="finishText"
            :completed-goals="completedGoals"
            :goals-count="stateInfo.goals?.length || 0"
            :turn-count="stateInfo.turn_count || 0"
            :stage="stateInfo.stage || ''"
            :stages="sceneMeta?.package?.stages || []"
            :scene-id="sessionInfo?.scene_id || ''"
            :scene-mode="sceneMeta?.package?.meta?.mode || ''"
            :scenario-state="stateInfo.scenario_state || {}"
            @selection="lookupRef?.handleSelection($event)"
            @scroll="lookupRef?.close()"
            @stop-audio="stopAudio()"
            @play-user-voice="playUserVoice($event)"
            @play-message="playMessage($event)"
            @toggle-original="toggleOriginal"
            @toggle-feedback="toggleFeedback($event)"
            @action="runSessionAction"
            @open-report="openSessionReport"
            @back-to-select="backToSelect"
            @restart="restartCurrentScene"
          />

          <PracticeComposer
            ref="composerRef"
            v-model:draft="draft"
            :playback-notice="playbackNotice"
            :error="error"
            :reply-suggestions="replySuggestions"
            :suggesting="suggesting"
            :input-mode="inputMode"
            :transcribed-text="transcribedText"
            :playing-key="playingKey"
            :playback-time="playbackTime"
            :playback-duration="playbackDuration"
            :pending-voice-duration="pendingVoiceDuration"
            :voice-busy="voiceBusy"
            :voice-status="voiceStatus"
            :voice-status-label="voiceStatusLabel"
            :recording-seconds="recordingSeconds"
            :recording-level="recordingLevel"
            :sending="sending"
            :finished="finished"
            :asr-available="asrAvailable"
            :recording-supported="recordingSupported"
            :voice-cta-text="voiceCtaText"
            :voice-hint-text="voiceHintText"
            @request-assist="requestReplyAssist"
            @clear-suggestions="replySuggestions = []"
            @apply-suggestion="applySuggestion"
            @play-pending="playPendingVoice"
            @stop-audio="stopAudio"
            @retry-recording="retryRecording"
            @discard-pending="discardPendingVoice"
            @send-transcribed="sendTranscribed"
            @stop-recording="stopRecording"
            @cancel-recording="cancelRecording"
            @start-recording="startRecording"
            @toggle-input-mode="toggleInputMode"
            @send-turn="sendTurn"
          />
        </section>

        <PracticeCoachDrawer
          v-model:auto-play-replies="autoPlayReplies"
          v-model:speech-rate="speechRate"
          :companion-avatar="companionAvatar"
          :voice-busy="voiceBusy"
          :voice-status="voiceStatus"
          :avatar-state="avatarState"
          :active-role="activeRole"
          :selected-voice-label="selectedVoiceLabel"
          :completed-goals="completedGoals"
          :goals="stateInfo.goals || []"
          :goal-has-check="goalHasCheck"
          @save-auto-play="saveAutoPlayPreference"
          @save-speech-rate="saveSpeechRatePreference"
        />

        <transition name="dock-slide">
          <PracticeKnowledge
            v-if="knowledgeOpen"
            class="chat-knowledge-dock"
            :scene-id="sessionInfo.scene_id"
            :description="sceneMeta?.package?.meta?.description || ''"
            :goals="stateInfo.goals || []"
            @close="knowledgeOpen = false"
          />
        </transition>
      </div>
    </div>

    <!-- 场景状态浮层：挂在 body 上，避免被对话卡圆角裁切 -->
    <Teleport to="body">
      <template v-if="stageOpen">
        <div class="rail-pop-backdrop" @click="stageOpen = false"></div>
        <div class="rail-pop stage-pop" role="dialog" aria-label="对话阶段" :style="{ top: `${stagePop.top}px`, left: `${stagePop.left}px` }">
          <p>场景流程共 {{ stageTotal }} 个阶段</p>
          <ul class="stage-pop-list">
            <li
              v-for="(st, idx) in stageList"
              :key="st.id"
              :class="{ 'is-done': idx + 1 < stageIndex || finished, 'is-current': idx + 1 === stageIndex && !finished }"
            >
              <span class="stage-num"><AppIcon v-if="idx + 1 < stageIndex || finished" name="check" :size="11" /><template v-else>{{ idx + 1 }}</template></span>
              <div class="stage-meta">
                <b>{{ st.name }}</b>
                <small v-if="formatStageGuidance(st.guidance)">{{ formatStageGuidance(st.guidance) }}</small>
              </div>
            </li>
          </ul>
        </div>
      </template>

      <template v-if="stateOpen">
        <div class="rail-pop-backdrop" @click="stateOpen = false"></div>
        <div class="rail-pop" role="dialog" aria-label="场景状态" :style="{ top: `${statePop.top}px`, right: `${statePop.right}px` }">
          <p>根据对话更新，仅供练习参考。</p>
          <ul><li v-for="row in stateRows" :key="row.key"><span>{{ row.key }}</span><b>{{ row.value }}</b></li></ul>
        </div>
      </template>

      <PracticeReviewModal :open="reportOpen" :report="sessionReport" @close="reportOpen = false" />
    </Teleport>

    <PracticeLookupPopover
      ref="lookupRef"
      :voice-style="voiceStyle"
      :scene-name="sceneTitle"
      :signed-in="Boolean(session.token)"
    />
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marked } from 'marked'
import AppIcon from '../components/AppIcon.vue'
import CharacterPortrait from '../components/avatar/CharacterPortrait.vue'
import PracticeChatStream from '../components/practice/PracticeChatStream.vue'
import PracticeCoachDrawer from '../components/practice/PracticeCoachDrawer.vue'
import PracticeComposer from '../components/practice/PracticeComposer.vue'
import PracticeKnowledge from '../components/practice/PracticeKnowledge.vue'
import PracticeLookupPopover from '../components/practice/PracticeLookupPopover.vue'
import PracticeReviewModal from '../components/practice/PracticeReviewModal.vue'
import PracticeScenePicker from '../components/practice/PracticeScenePicker.vue'
import { base64ToMp3Blob, useTtsAudioQueue } from '../composables/useTtsAudioQueue'
import { getScene, listScenes } from '../api/scenes'
import { applySessionAction, createSession, getSession, getSessionReport, getLatestSession, getGreetingAudio, getTurnAudio, getUserTurnAudio, submitTurnStream, suggestReply } from '../api/sessions'
import { loadingVisible, usePageLoading } from '../app/loading'
import { syncGlobalXpProfile } from '../app/xp'
import { getSpeechStatus } from '../api/speech'
import { useVoiceInput } from '../composables/useVoiceInput'
import { FALLBACK_AVATARS, FALLBACK_VOICES, getAvatarPreference, listAvatars, saveAvatarPreference, VOICE_STYLE_ALIASES } from '../api/avatar'
import { resolveRoleVoiceStyle } from '../components/avatar/avatarAppearance'
import { session } from '../auth/session'

const props = defineProps({
  embeddedScene: { type: Object, default: null },
})
const emit = defineEmits(['exit', 'phase'])

const CATEGORY_LABELS = { daily: '日常', interview: '面试', career: '职业', academic: '学术', custom: '自定义', travel: '旅行', business: '商务', campus: '校园', debate: '辩论' }
const route = useRoute()
const router = useRouter()
const FINISH_REASONS = { condition_met: '场景任务已完成，本次练习结束。', max_turns: '已达到本场景的轮次上限，练习结束。' }

const phase = ref('select') // select=选场景 / chat=对话中
const resuming = ref(Boolean(!props.embeddedScene && route.query.session)) // 从历史记录进入会话时，恢复完成前保持加载态
// 页面级加载：场景列表（及历史会话恢复）到位后才收起全局遮罩；恢复入口已知会慢，立即盖住
const finishLoading = props.embeddedScene
  ? () => {}
  : usePageLoading(route.query.session ? '正在打开这次练习' : '', Boolean(route.query.session))
const scenes = ref([])
const allScenesList = ref([])
const loadingScenes = ref(false)
const starting = ref(false)
const error = ref('')
const confirmScene = ref(null) // 进入对话前的确认弹窗（点确认才创建会话）
const latestHistory = ref(null)
const checkingHistory = ref(false)
const historyError = ref('')
const lookupRef = ref(null)
let historyGeneration = 0

const sessionInfo = ref(null) // 后端会话公开字段 { id, scene_id, greeting, state, version }
const sceneMeta = ref(null) // 场景详情（阶段名/角色/描述）
const messages = ref([]) // { key, role: 'user'|'agent', text }
const draft = ref('')
const sending = ref(false)
const chatStreamRef = ref(null)
const chatBody = computed(() => chatStreamRef.value?.chatBody || null)
const composerRef = ref(null)
const asrAvailable = ref(null)
const inputMode = ref('voice') // 语音优先：voice=麦克风主输入 / text=文字备选
const transcribedText = ref('') // 语音转写结果：待用户确认后发送
const pendingAudioToken = ref('') // 语音暂存令牌：随下一轮流式对话提交给讯飞发音评估
const pendingVoiceBlobUrl = ref('') // 本地录音预览 URL：用于展示用户语音胶囊与回放
const pendingVoiceDuration = ref(0)

function clearPendingVoice(revoke = true) {
  pendingAudioToken.value = ''
  pendingVoiceDuration.value = 0
  if (revoke && pendingVoiceBlobUrl.value) {
    URL.revokeObjectURL(pendingVoiceBlobUrl.value)
  }
  pendingVoiceBlobUrl.value = ''
}

const {
  status: voiceStatus, seconds: recordingSeconds, level: recordingLevel,
  busy: voiceBusy, supported: recordingSupported,
  start: beginRecording, stop: stopRecording, cancel: cancelRecording,
} = useVoiceInput({
  onResult(text, meta) {
    // 录音识别后暂存为可试听的语音条，支持试听、重录或直接发送。
    if (pendingVoiceBlobUrl.value) URL.revokeObjectURL(pendingVoiceBlobUrl.value)
    transcribedText.value = [draft.value.trim(), text].filter(Boolean).join(' ')
    pendingAudioToken.value = meta?.audio_token || ''
    pendingVoiceBlobUrl.value = meta?.blob ? URL.createObjectURL(meta.blob) : ''
    pendingVoiceDuration.value = Number(meta?.duration || 0)
    avatarState.value = 'idle'
  },
  onError(message) { error.value = message; avatarState.value = 'idle' },
})
const voiceStatusLabel = computed(() => ({ requesting: '正在请求麦克风权限…', recording: '正在录音', stopping: '正在整理录音…', transcribing: '正在识别英语…' }[voiceStatus.value] || '语音输入'))
const avatarState = ref('idle') // 数字人展示状态：idle/listening/thinking/speaking
const stateOpen = ref(false) // 对话卡顶部的「场景状态」浮层
const stateButton = ref(null)
const statePop = ref({ top: 0, right: 0 })
// 浮层固定定位：按按钮实际位置计算坐标，避免被对话卡的圆角裁掉
function toggleStatePop() {
  if (!stateOpen.value && stateButton.value) {
    const rect = stateButton.value.getBoundingClientRect()
    statePop.value = { top: Math.round(rect.bottom + 8), right: Math.round(window.innerWidth - rect.right) }
  }
  stateOpen.value = !stateOpen.value
}
const knowledgeOpen = ref(false) // 场景知识点弹窗（参照 1.0 独立面板，分资料模块 Tab）
const showOriginal = ref(false) // 默认语音气泡：原文默认隐藏，可全局显示或逐条展开
const expandedMessages = ref(new Set())
const expandedFeedback = ref(new Set())
let msgSeq = 0

function toggleFeedback(key) {
  const next = new Set(expandedFeedback.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  expandedFeedback.value = next
}

function scoreTier(score) {
  const n = Number(score || 0)
  if (n >= 85) return 'is-high'
  if (n >= 70) return 'is-mid'
  return 'is-low'
}

function rateLabel(level) {
  return { slow: '偏慢', natural: '适中', normal: '适中', fast: '偏快' }[level] || '适中'
}

// TTS 播报：音色/语速取场景档偏好，未设置时用缺省值
const voiceStyle = ref('emma')
const speechRate = ref(1)
const selectedVoiceLabel = computed(() => FALLBACK_VOICES.find(voice => voice.style === voiceStyle.value)?.label || voiceStyle.value)
const ttsBusyKey = ref('')
const playingKey = ref('')
const playbackTime = ref(0) // 当前播放秒数（胶囊进度条用）
const playbackDuration = ref(0) // 当前音频总时长（元数据加载后更新）
// 语音胶囊：宽度与预估时长按词数估算（对齐 1.0 的 getCapsuleWidth / getWavDuration）
function estimateSeconds(text) {
  const words = (text || '').trim().split(/\s+/).filter(Boolean).length
  return Math.max(2, Math.round(words / 2))
}
function capsuleWidth(msg) {
  const seconds = msg.duration ? Math.ceil(msg.duration) : estimateSeconds(msg.text)
  return `${Math.min(320, Math.max(120, 110 + seconds * 9))}px`
}
let currentAudio = null
const audioCache = new Map() // 当前练习内复用音频，不向磁盘持久化私人对话。
let playbackGeneration = 0 // 丢弃切换消息或离开页面后才完成的语音合成
let sessionGeneration = 0
const autoPlayReplies = ref(localStorage.getItem('echotalk:autoplay-replies') !== '0')
const playbackNotice = ref('')

function saveAutoPlayPreference() {
  localStorage.setItem('echotalk:autoplay-replies', autoPlayReplies.value ? '1' : '0')
  if (!autoPlayReplies.value) stopAudio()
}

async function saveSpeechRatePreference() {
  const rate = Math.min(1.25, Math.max(0.75, Number(speechRate.value) || 1))
  speechRate.value = rate
  if (currentAudio) currentAudio.playbackRate = rate
  if (!session.token) return
  try {
    await saveAvatarPreference({
      scene_id: sessionInfo.value?.scene_id || undefined,
      avatar_id: companionAvatarId.value || undefined,
      voice_style: voiceStyle.value || undefined,
      speech_rate: rate,
    })
  } catch { /* 离线或未授权时仅保留当前会话语速 */ }
}

watch(speechRate, (rate) => {
  if (currentAudio) currentAudio.playbackRate = rate
})

const stateInfo = computed(() => sessionInfo.value?.state || {})
const finished = computed(() => stateInfo.value.status === 'finished')
const finishText = computed(() => FINISH_REASONS[stateInfo.value.finish_reason] || '本次练习已结束。')
const activeRole = computed(() => sceneMeta.value?.package?.roles?.[0] || null)
const roleName = computed(() => activeRole.value ? `${activeRole.value.display_name} · ${activeRole.value.title || '对话伙伴'}` : '场景对话伙伴')
const roleInitial = computed(() => (activeRole.value?.display_name || 'A').slice(0, 1).toUpperCase())
const userInitial = computed(() => (session.user?.username || 'A').slice(0, 1).toUpperCase())
const sceneTitle = computed(() => sceneMeta.value?.package?.meta?.name || sceneMeta.value?.name || '场景对话')
const currentStage = computed(() => {
  const stages = stageList.value
  if (!stages.length) return null
  if (finished.value) return stages[stages.length - 1]
  return stages.find(stage => stage.id === stateInfo.value.stage) || stages[0]
})
// 阶段进度：用于顶部信息条显示「2 / 4」
const stageList = computed(() => sceneMeta.value?.package?.stages || [])
const stageTotal = computed(() => stageList.value.length)
const stageIndex = computed(() => {
  if (finished.value && stageTotal.value) return stageTotal.value
  const i = stageList.value.findIndex(stage => stage.id === stateInfo.value.stage)
  return i >= 0 ? i + 1 : 0
})
const stageOpen = ref(false)
const stageButton = ref(null)
const stagePop = ref({ top: 0, left: 0 })
function toggleStagePop() {
  stateOpen.value = false
  if (!stageOpen.value && stageButton.value) {
    const rect = stageButton.value.getBoundingClientRect()
    stagePop.value = { top: Math.round(rect.bottom + 8), left: Math.round(rect.left) }
  }
  stageOpen.value = !stageOpen.value
}
function formatStageGuidance(text) {
  if (!text) return ''
  return String(text)
    .replace(/；?\s*[^；。]*调用\s*`?[a-z0-9_]+`?[^；。]*/gi, '')
    .trim()
}
const reportOpen = ref(false)
const reportLoading = ref(false)
const sessionReport = ref(null)
async function openSessionReport() {
  if (!sessionInfo.value?.id || reportLoading.value) return
  reportLoading.value = true
  try {
    const { data } = await getSessionReport(sessionInfo.value.id)
    sessionReport.value = data
    reportOpen.value = true
  } catch (err) {
    error.value = err?.message || '生成练习报告失败，请稍后重试'
  } finally {
    reportLoading.value = false
  }
}
const completedGoals = computed(() => (stateInfo.value.goals || []).filter(goal => goal.done).length)
const goalHasCheck = id => Boolean(sceneMeta.value?.package?.objectives?.find(goal => goal.id === id)?.check)
const conversationStatus = computed(() => finished.value ? '本次练习已结束' : voiceBusy.value ? voiceStatusLabel.value : sending.value ? '正在思考你的回答…' : ttsBusyKey.value ? '正在准备语音…' : playingKey.value ? '正在播放回复' : '等待你的回应')
// 语音优先 CTA 文案：按服务配置、环境支持与练习状态给出可执行提示
const voiceCtaText = computed(() => {
  if (asrAvailable.value === false) return '语音暂不可用'
  if (!recordingSupported.value) return '当前环境不支持录音'
  if (sending.value) return '正在发送…'
  if (finished.value) return '本次练习已结束'
  return '点击说英语'
})
// 待机条副标题：补充主文案之外的使用说明
const voiceHintText = computed(() => {
  if (asrAvailable.value === false) return '切换文字输入可以继续交流'
  if (!recordingSupported.value) return '切换文字输入可以继续交流'
  if (finished.value) return '退出后可另选场景练习'
  return '最长 60 秒，录完可试听或重录'
})
// 场景状态变量是场景包里的机器键名（update_scene_state 按此写入），只展示已登记中文名的键；未登记的键不直接暴露英文
const STATE_LABELS = { polite_request: '礼貌请求', issue_explained: '问题说明', rebooked: '新行程', options_compared: '方案比较', reported: '进度汇报', clarified: '问题澄清', next_step: '下一步', confirmed: '订单确认', paid: '付款', order: '点单内容', greeted: '打招呼', price_asked: '问价', booked: '预订', payment_method: '支付方式', paid_amount: '实付金额' }
const paying = ref(false)
const paymentMethodLabel = (id) => ({ card: '刷卡支付', apple_pay: 'Apple Pay', cash: '现金支付' }[id] || id)
const renderMessageMd = (text) => marked.parse(String(text || '').trim(), { breaks: true, async: false }).trim()

async function runSessionAction(action, payload) {
  if (!sessionInfo.value || paying.value) return
  paying.value = true
  error.value = ''
  try {
    const { data } = await applySessionAction(sessionInfo.value.id, action, payload)
    if (data?.session) sessionInfo.value = data.session
    await scrollToBottom()
  } catch (err) {
    error.value = err.message
  } finally {
    paying.value = false
  }
}

async function restartCurrentScene() {
  const scene = scenes.value.find((s) => s.id === sessionInfo.value?.scene_id) || props.embeddedScene || { id: sessionInfo.value?.scene_id, name: sceneTitle.value }
  if (!scene?.id) return
  await startScene(scene, null)
}
// 场景状态卡：展示标量字段与非内部数组（如点单列表）
const stateRows = computed(() =>
  Object.entries(stateInfo.value.scenario_state || {})
    .filter(([key, value]) => STATE_LABELS[key] && (['string', 'number', 'boolean'].includes(typeof value) || Array.isArray(value)))
    .map(([key, value]) => {
      if (Array.isArray(value)) {
        const text = value.length
          ? value.map((item) => (typeof item === 'string' ? item : item?.name || item?.item || JSON.stringify(item))).join('、')
          : '暂无'
        return { key: STATE_LABELS[key], value: text }
      }
      if (key === 'payment_method') return { key: STATE_LABELS[key], value: paymentMethodLabel(String(value)) }
      if (key === 'paid_amount') return { key: STATE_LABELS[key], value: `$${value}` }
      return { key: STATE_LABELS[key], value: typeof value === 'boolean' ? (value ? '已确认' : '待确认') : String(value) }
    })
)
const avatarsList = ref([...FALLBACK_AVATARS])
// 伙伴形象：优先用户场景档偏好，其次当前场景角色推荐（含自定义外观），最后缺省清单首个
const companionAvatar = computed(() => {
  const id = companionAvatarId.value || activeRole.value?.avatar
  const base = avatarsList.value.find((a) => a.id === id) || avatarsList.value[0] || FALLBACK_AVATARS[0]
  if (!companionAvatarId.value && activeRole.value?.appearance) {
    return { ...base, appearance: activeRole.value.appearance }
  }
  return base
})
const companionAvatarId = ref(null)

const categoryLabel = (key) => CATEGORY_LABELS[key] || key || '通用'

async function toggleOriginal(key, event) {
  // 按消息展开原文，沿用旧版语音消息与文本分开展示的交互。
  if (expandedMessages.value.has(key)) {
    expandedMessages.value.delete(key)
    return
  }
  expandedMessages.value.add(key)
  const rowEl = event?.currentTarget?.closest('.msg-row')
  await nextTick()
  const box = chatBody.value
  if (!box || box.scrollHeight <= box.clientHeight) return
  if (rowEl) {
    const boxRect = box.getBoundingClientRect()
    const rowRect = rowEl.getBoundingClientRect()
    if (rowRect.bottom <= boxRect.bottom - 8) return
  }
  void scrollToBottom(true)
}

function onPanelEnter(el) {
  el.style.height = 'auto'
  const targetHeight = el.getBoundingClientRect().height
  el.style.height = '0px'
  el.style.opacity = '0'
  el.style.marginTop = '0px'
  el.style.paddingTop = '0px'
  el.style.paddingBottom = '0px'
  el.style.borderTopWidth = '0px'
  el.style.borderBottomWidth = '0px'
  void el.offsetHeight
  el.style.height = `${targetHeight}px`
  el.style.opacity = '1'
  el.style.marginTop = ''
  el.style.paddingTop = ''
  el.style.paddingBottom = ''
  el.style.borderTopWidth = ''
  el.style.borderBottomWidth = ''
}

function onPanelAfterEnter(el) {
  el.style.height = ''
  el.style.opacity = ''
}

function onPanelLeave(el) {
  const currentHeight = el.getBoundingClientRect().height
  el.style.height = `${currentHeight}px`
  el.style.opacity = '1'
  void el.offsetHeight
  el.style.height = '0px'
  el.style.opacity = '0'
  el.style.marginTop = '0px'
  el.style.paddingTop = '0px'
  el.style.paddingBottom = '0px'
  el.style.borderTopWidth = '0px'
  el.style.borderBottomWidth = '0px'
}

function onPanelAfterLeave(el) {
  el.style.height = ''
  el.style.opacity = ''
  el.style.marginTop = ''
  el.style.paddingTop = ''
  el.style.paddingBottom = ''
  el.style.borderTopWidth = ''
  el.style.borderBottomWidth = ''
}

watch(showOriginal, (val) => {
  if (val) void scrollToBottom(true)
})

function pushMessage(role, text) {
  const msg = { key: `m${++msgSeq}`, role, text }
  messages.value.push(msg)
  scrollToBottom()
  return messages.value[messages.value.length - 1]
}

async function scrollToBottom(smooth = false) {
  await nextTick()
  const el = chatBody.value
  if (!el) return
  if (smooth) {
    requestAnimationFrame(() => {
      el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
    })
    return
  }
  el.scrollTop = el.scrollHeight
  requestAnimationFrame(() => {
    if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight
  })
}

// ---- 场景选择与会话创建 -----------------------------------------------------

async function loadCustomAvatars() {
  try {
    const list = await listAvatars()
    if (Array.isArray(list) && list.length) avatarsList.value = list
  } catch { /* 回退本地清单 */ }
}

onMounted(async () => {
  void loadCustomAvatars()
  getSpeechStatus().then(({ data }) => { asrAvailable.value = data.configured }).catch(() => {})
  if (props.embeddedScene) {
    finishLoading()
    void chooseScene(props.embeddedScene)
    return
  }
  // 历史记录入口：会话详情与场景列表并行拉取，过渡态不必串行等两次往返
  const resumeId = route.query.session
  const pendingSession = resumeId ? getSession(resumeId) : null
  if (pendingSession) pendingSession.catch(() => {}) // 场景列表失败时避免留下未处理的拒绝
  loadingScenes.value = true
  try {
    const { data } = await listScenes()
    const allScenes = data?.items || []
    allScenesList.value = allScenes
    // 优先展示本人创建以及已收藏的场景；新用户尚无自有/收藏场景时兜底展示官方内置场景
    const curated = allScenes.filter(
      (s) => (session.user && s.author_id === session.user.id) || s.stats?.favorited
    )
    scenes.value = curated.length ? curated : allScenes.filter((s) => s.source === 'builtin')
    const selected = route.query.scene ? allScenes.find(scene => scene.id === route.query.scene) : null
    if (selected) void chooseScene(selected)
    else if (resumeId) await resumeSession(resumeId, pendingSession) // 从历史记录进入某次会话：等恢复完成再收遮罩
  } catch (err) {
    error.value = err.message
  } finally {
    loadingScenes.value = false
    finishLoading() // 场景列表（或恢复的会话）就绪，交还遮罩
  }
})

watch(phase, (val) => {
  if (props.embeddedScene) emit('phase', val)
})

watch(confirmScene, (val) => {
  if (props.embeddedScene && phase.value === 'select' && !val && !starting.value) {
    emit('exit')
  }
})

async function resumeSession(sessionId, pending) {
  // 历史记录入口：先按会话查出所属场景，再复用 startScene 的恢复流程回放对话
  if (!session.token) {
    error.value = '请先登录后查看练习记录。'
    resuming.value = false
    return
  }
  try {
    const { data } = await (pending || getSession(sessionId))
    let scene = scenes.value.find(item => item.id === data.scene_id)
      || allScenesList.value.find(item => item.id === data.scene_id)
    if (!scene && data.scene_id) {
      scene = {
        id: data.scene_id,
        name: data.scene_display?.meta?.name || data.scene_id,
        ...(data.scene_display || {}),
      }
    }
    if (!scene) { error.value = '对应的场景已不可用，无法打开这条练习记录。'; return }
    await startScene(scene, sessionId)
  } catch (err) {
    error.value = err.message
  } finally {
    resuming.value = false // 成功时已切到对话态；失败则退回场景选择并显示原因
  }
}

async function chooseScene(scene) {
  if (starting.value) return // 已在准备会话时不重复弹窗
  confirmScene.value = scene
  latestHistory.value = null
  historyError.value = ''
  const generation = ++historyGeneration
  if (!session.token) { historyError.value = '请先登录后开始练习。'; return }
  checkingHistory.value = true
  try {
    const { data } = await getLatestSession(scene.id)
    if (generation === historyGeneration && confirmScene.value?.id === scene.id) {
      latestHistory.value = data.session?.state?.status === 'finished' ? null : data.session
    }
  } catch (err) {
    if (generation === historyGeneration && confirmScene.value?.id === scene.id) historyError.value = err.message
  } finally {
    if (generation === historyGeneration) checkingHistory.value = false
  }
}

async function startScene(scene, existingId = null) {
  if (starting.value) return
  starting.value = true
  const generation = ++sessionGeneration
  error.value = ''
  historyError.value = ''
  stopAudio()
  clearAudioCache()
  replySuggestions.value = []
  stateOpen.value = false
  stageOpen.value = false
  reportOpen.value = false
  sessionReport.value = null
  draft.value = ''
  transcribedText.value = ''
  try {
    const hasCachedMeta = sceneMeta.value?.package?.meta?.id === scene.id
    // 知识点面板按需独立加载，不因资料服务失败阻塞进入对话；同场景「再来一次」直接复用已缓存的场景元数据。
    const [detailRes, sessionRes, preference] = await Promise.all([
      hasCachedMeta ? Promise.resolve({ data: sceneMeta.value }) : getScene(scene.id),
      existingId ? getSession(existingId) : createSession(scene.id),
      hasCachedMeta ? Promise.resolve(null) : getAvatarPreference(scene.id),
    ])
    if (generation !== sessionGeneration) return
    sceneMeta.value = { ...detailRes.data, package: sessionRes.data.scene_display || detailRes.data.package }
    if (!hasCachedMeta) applyVoicePreference(preference, activeRole.value?.voice)
    sessionInfo.value = sessionRes.data
    messages.value = []
    const greetingMessage = sessionRes.data.greeting ? pushMessage('agent', sessionRes.data.greeting) : null
    if (greetingMessage) greetingMessage.greetingSessionId = sessionRes.data.id
    for (const turn of sessionRes.data.turns || []) {
      const userTurnMsg = pushMessage('user', turn.input_text)
      userTurnMsg.isVoice = Boolean(turn.pronunciation_score)
      userTurnMsg.duration = turn.pronunciation_score?.duration_sec || null
      userTurnMsg.turnId = turn.turn_id
      userTurnMsg.sessionId = sessionRes.data.id
      userTurnMsg.hasUserAudio = Boolean(turn.has_user_audio)
      userTurnMsg.pronunciationScore = turn.pronunciation_score || null
      userTurnMsg.grammarCorrection = turn.grammar_correction || null
      const reply = pushMessage('agent', turn.text)
      reply.turnId = turn.turn_id
      reply.sessionId = sessionRes.data.id
    }
    phase.value = 'chat'
    if (props.embeddedScene) emit('phase', 'chat')
    avatarState.value = 'idle'
    confirmScene.value = null // 进入成功后收起确认弹窗
    await scrollToBottom()
    if (generation !== sessionGeneration) return
    composerRef.value?.focusInput()
    if (!existingId && greetingMessage && autoPlayReplies.value) void playMessage(greetingMessage, { automatic: true })
  } catch (err) {
    if (phase.value === 'chat') error.value = err.message
    else historyError.value = err.message
  } finally {
    starting.value = false
  }
}

function confirmStart() {
  // 弹窗确认入口：真正发起会话创建
  if (confirmScene.value) startScene(confirmScene.value)
}

function applyVoicePreference(pref, roleVoice) {
  voiceStyle.value = resolveRoleVoiceStyle(roleVoice, FALLBACK_VOICES.map((v) => v.style))
  speechRate.value = 1
  companionAvatarId.value = pref?.avatar_id || null
  const style = VOICE_STYLE_ALIASES[pref?.voice_style] || pref?.voice_style
  if (style && FALLBACK_VOICES.some((v) => v.style === style)) voiceStyle.value = style
  if (Number.isFinite(pref?.speech_rate)) speechRate.value = Math.min(1.25, Math.max(0.75, pref.speech_rate))
}

function backToSelect() {
  if (sending.value) return
  sessionGeneration += 1
  activeStreamController?.abort()
  replySuggestions.value = []
  playbackNotice.value = ''
  cancelRecording()
  transcribedText.value = ''
  clearPendingVoice()
  stopAudio()
  clearAudioCache()
  phase.value = 'select'
  sessionInfo.value = null
  sceneMeta.value = null
  messages.value = []
  draft.value = ''
  expandedMessages.value.clear()
  stateOpen.value = false
  stageOpen.value = false
  reportOpen.value = false
  sessionReport.value = null
  error.value = ''
  if (props.embeddedScene) { emit('exit'); return }
  if (route.query.session) { router.replace({ name: 'history' }); return } // 由历史记录进入时退回列表，而非场景选择
}

// ---- 对话轮次 ---------------------------------------------------------------

function startRecording() {
  if (sending.value || finished.value || voiceBusy.value) return
  stopAudio()
  error.value = ''
  transcribedText.value = ''
  clearPendingVoice()
  avatarState.value = 'listening' // 数字人进入倾听姿态
  beginRecording()
}

function retryRecording() {
  // 转写结果不满意：清掉结果直接重录
  transcribedText.value = ''
  clearPendingVoice()
  startRecording()
}

function sendTranscribed() {
  // 确认发送语音转写文本（保留语音属性与 audio_token，用于展示语音胶囊与发音评测）
  const text = transcribedText.value.trim()
  if (!text || sending.value || finished.value) return
  const voiceMeta = {
    isVoice: true,
    text,
    audioToken: pendingAudioToken.value || undefined,
    audioUrl: pendingVoiceBlobUrl.value || '',
    duration: pendingVoiceDuration.value || 0,
  }
  clearPendingVoice(false) // audioUrl 移交给消息对象，不立即 revoke
  transcribedText.value = ''
  sendTurn(voiceMeta)
}

function toggleInputMode() {
  // 语音/文字互切（录音中禁用切换，避免设备资源泄漏）
  if (voiceBusy.value) return
  transcribedText.value = ''
  clearPendingVoice()
  inputMode.value = inputMode.value === 'voice' ? 'text' : 'voice'
  if (inputMode.value === 'text') nextTick(() => composerRef.value?.focusInput())
}

let activeStreamController = null
const {
  resetStreamAudioQueue,
  getStreamPlaybackGen,
  enqueueStreamAudioChunk,
  markStreamAudioEnded,
  pumpStreamAudio,
} = useTtsAudioQueue({
  messages,
  playingKey,
  playbackTime,
  playbackDuration,
  avatarState,
  speechRate,
  playbackNotice,
  estimateSeconds,
  getCurrentAudio: () => currentAudio,
  setCurrentAudio: (audio) => { currentAudio = audio },
})
const suggesting = ref(false)
const replySuggestions = ref([])

async function requestReplyAssist() {
  if (!sessionInfo.value?.id || suggesting.value || sending.value || finished.value) return
  suggesting.value = true
  error.value = ''
  try {
    const { data } = await suggestReply(sessionInfo.value.id)
    replySuggestions.value = Array.isArray(data?.suggestions) ? data.suggestions : []
    if (!replySuggestions.value.length) error.value = '暂未生成参考回复，请再试一次'
  } catch (err) {
    error.value = err?.message || '生成参考回复失败，请稍后重试'
  } finally {
    suggesting.value = false
  }
}

async function applySuggestion(enText) {
  if (!enText) return
  draft.value = enText
  replySuggestions.value = []
  if (inputMode.value !== 'text') inputMode.value = 'text'
  await nextTick()
  composerRef.value?.focusInput()
}

function discardPendingVoice() {
  stopAudio()
  transcribedText.value = ''
  clearPendingVoice()
}

function playPendingVoice() {
  if (!pendingVoiceBlobUrl.value) return
  void playUserVoice({
    key: '__pending__',
    audioUrl: pendingVoiceBlobUrl.value,
    duration: pendingVoiceDuration.value,
  })
}

async function playUserVoice(msg) {
  if (!msg) return
  stopAudio()
  let url = msg.audioUrl
  if (!url && msg.hasUserAudio && msg.sessionId && msg.turnId) {
    try {
      const blob = await getUserTurnAudio(msg.sessionId, msg.turnId)
      url = URL.createObjectURL(blob)
      msg.audioUrl = url
    } catch {
      return
    }
  }
  if (!url) {
    playbackNotice.value = '该条历史录音未保留音频文件，可点击左侧「原文」查看文字。'
    return
  }
  const audio = new Audio(url)
  currentAudio = audio
  playingKey.value = msg.key
  playbackTime.value = 0
  playbackDuration.value = msg.duration || 0
  audio.ontimeupdate = () => { playbackTime.value = currentAudio?.currentTime || 0 }
  audio.onloadedmetadata = () => {
    if (Number.isFinite(currentAudio?.duration)) playbackDuration.value = currentAudio.duration
  }
  const done = () => {
    if (currentAudio === audio) currentAudio = null
    playingKey.value = ''
    playbackTime.value = 0
  }
  audio.onended = done
  audio.onerror = done
  try {
    await audio.play()
  } catch {
    done()
  }
}

async function sendTurn(voiceMeta = null) {
  const isVoiceTurn = Boolean(voiceMeta?.isVoice)
  const text = String(isVoiceTurn ? (voiceMeta?.text ?? '') : draft.value).trim()
  if (!text || sending.value || finished.value || voiceBusy.value) return
  if (text.length > 4000) { error.value = '回答超过 4000 字，请精简后再发送。'; return }
  transcribedText.value = ''
  const audioToken = isVoiceTurn ? voiceMeta.audioToken : undefined
  if (!isVoiceTurn) clearPendingVoice()
  replySuggestions.value = []
  stopAudio()
  sending.value = true
  const generation = sessionGeneration
  let replyMessage = null
  let doneReceived = false
  avatarState.value = 'thinking'
  error.value = ''
  draft.value = ''
  composerRef.value?.resetHeight()
  const userMsg = pushMessage('user', text) // 乐观上屏，失败时按 key 撤回
  if (isVoiceTurn) {
    userMsg.isVoice = true
    userMsg.audioUrl = voiceMeta.audioUrl || ''
    userMsg.duration = voiceMeta.duration || 0
  }
  const controller = new AbortController()
  activeStreamController = controller
  const expectedStreamGen = getStreamPlaybackGen()
  const streamedBlobs = []
  let hadAudioError = false

  try {
    const requestId = crypto.randomUUID() // 幂等键：网络重试时后端去重
    await submitTurnStream(sessionInfo.value.id, requestId, text, {
      voiceStyle: voiceStyle.value,
      includeAudio: autoPlayReplies.value,
      audioToken,
      signal: controller.signal,
      onCorrection(data) {
        if (generation !== sessionGeneration) return
        userMsg.grammarCorrection = data
        scrollToBottom()
      },
      onPronunciation(data) {
        if (generation !== sessionGeneration) return
        userMsg.pronunciationScore = data
        scrollToBottom()
      },
      onDelta(delta) {
        if (generation !== sessionGeneration || !delta) return
        if (!replyMessage && !delta.trim()) return
        if (!replyMessage) {
          replyMessage = pushMessage('agent', '')
          if (autoPlayReplies.value) ttsBusyKey.value = replyMessage.key
        }
        replyMessage.text += delta
        scrollToBottom()
      },
      onDone(data) {
        if (generation !== sessionGeneration) return
        doneReceived = true
        if (!replyMessage) {
          replyMessage = pushMessage('agent', data.text)
          if (autoPlayReplies.value) ttsBusyKey.value = replyMessage.key
        } else {
          replyMessage.text = data.text
        }
        replyMessage.turnId = data.turn_id
        replyMessage.sessionId = data.session_id
        sessionInfo.value = { ...sessionInfo.value, state: data.state, version: data.version }
        sending.value = false
        if (!autoPlayReplies.value && avatarState.value === 'thinking') avatarState.value = 'idle'
        scrollToBottom()
      },
      onAudio(chunk) {
        if (generation !== sessionGeneration || !autoPlayReplies.value || !chunk?.audio_b64) return
        if (expectedStreamGen !== getStreamPlaybackGen()) return
        const msgKey = replyMessage?.key || ''
        if (ttsBusyKey.value === msgKey) ttsBusyKey.value = ''
        const blob = base64ToMp3Blob(chunk.audio_b64)
        streamedBlobs.push(blob)
        enqueueStreamAudioChunk(blob, chunk.text || '')
        if (!currentAudio && msgKey) void pumpStreamAudio(msgKey, expectedStreamGen)
      },
      onAudioError() {
        hadAudioError = true
      },
      onAudioEnd() {
        if (generation !== sessionGeneration) return
        if (replyMessage && ttsBusyKey.value === replyMessage.key) ttsBusyKey.value = ''
        if (!hadAudioError && streamedBlobs.length && replyMessage) {
          audioCache.set(JSON.stringify([replyMessage.key, voiceStyle.value]), new Blob(streamedBlobs, { type: 'audio/mpeg' }))
        }
        markStreamAudioEnded(replyMessage?.key || '')
      },
    })
    if (doneReceived) void syncGlobalXpProfile()
  } catch (err) {
    if (generation !== sessionGeneration || err?.name === 'AbortError') return
    if (!doneReceived) {
      // 提交失败：撤回乐观气泡，把输入还给用户重发
      const removeKeys = new Set([userMsg.key, replyMessage?.key].filter(Boolean))
      messages.value = messages.value.filter((m) => !removeKeys.has(m.key))
      draft.value = text
      error.value = err.message
    }
  } finally {
    if (activeStreamController === controller) activeStreamController = null
    if (replyMessage && ttsBusyKey.value === replyMessage.key) ttsBusyKey.value = ''
    sending.value = false
    if (avatarState.value === 'thinking') avatarState.value = 'idle'
    scrollToBottom()
  }
}

// ---- TTS 播报 ---------------------------------------------------------------

async function playMessage(msg, { automatic = false } = {}) {
  if (voiceBusy.value || sending.value) return
  stopAudio()
  playbackNotice.value = ''
  const generation = playbackGeneration
  ttsBusyKey.value = msg.key
  try {
    const cacheKey = JSON.stringify([msg.key, voiceStyle.value])
    let blob = audioCache.get(cacheKey)
    if (!blob) {
      blob = msg.greetingSessionId
        ? await getGreetingAudio(msg.greetingSessionId, voiceStyle.value, 1)
        : await getTurnAudio(msg.sessionId, msg.turnId, voiceStyle.value, 1)
      if (generation !== playbackGeneration) return
      audioCache.set(cacheKey, blob)
    }
    if (generation !== playbackGeneration) return
    const url = URL.createObjectURL(blob)
    currentAudio = new Audio(url)
    currentAudio.preservesPitch = true
    currentAudio.playbackRate = speechRate.value
    currentAudio.ontimeupdate = () => { playbackTime.value = currentAudio?.currentTime || 0 }
    currentAudio.onloadedmetadata = () => {
      playbackDuration.value = Number.isFinite(currentAudio?.duration) ? currentAudio.duration : 0
      const displayed = messages.value.find(item => item.key === msg.key)
      if (displayed && playbackDuration.value) displayed.duration = playbackDuration.value
    }
    currentAudio.onended = () => stopAudio()
    currentAudio.onerror = () => stopAudio()
    await currentAudio.play()
    if (generation !== playbackGeneration) return
    ttsBusyKey.value = ''
    playingKey.value = msg.key
    avatarState.value = 'speaking'
  } catch (err) {
    if (generation !== playbackGeneration) return
    if (err.name === 'NotAllowedError') playbackNotice.value = '浏览器阻止了自动播放，请点击回复下方的「听语音」。'
    else if (automatic) playbackNotice.value = `自动播放未完成：${err.message || '语音合成失败'}，可点击「听语音」重试。`
    else error.value = err.message || '语音合成失败'
    stopAudio()
  }
}

function stopAudio() {
  playbackGeneration += 1
  resetStreamAudioQueue()
  if (currentAudio) {
    currentAudio.pause()
    if (currentAudio.src?.startsWith('blob:')) URL.revokeObjectURL(currentAudio.src)
    currentAudio = null
  }
  ttsBusyKey.value = ''
  playingKey.value = ''
  playbackTime.value = 0
  playbackDuration.value = 0
  if (avatarState.value === 'speaking') avatarState.value = 'idle'
}

function clearAudioCache() { audioCache.clear() }

onBeforeUnmount(() => {
  sessionGeneration += 1
  activeStreamController?.abort()
  stopAudio()
  lookupRef.value?.close()
  clearAudioCache()
})
</script>

<style scoped>
.autoplay-control { display: flex; align-items: center; gap: 7px; margin: 10px 0 12px; color: var(--ink-soft); font-size: 12px; }.autoplay-control input { accent-color: var(--brand); }
.playback-notice { display: flex; align-items: flex-start; gap: 6px; margin: 0 0 10px; color: var(--muted); font-size: 12px; line-height: 1.7; }
/* 录音与转写共用单行输入条（.composer 外壳），三态等高，文字草稿不随录音清空。 */
.mic-input-button { display: none; } /* 已被语音优先布局取代，保留类名防止外部引用报错 */
/* 语音优先：单行紧凑条（42px 圆形麦克风 + 信息列 + 右侧操作） */
.voice-bar { position: relative; align-items: center; gap: 12px; min-height: 62px; }
/* 待机态：左整块语音触发按钮，右文字模式切换，布局更饱满 */
.voice-bar.idle { justify-content: space-between; padding: 8px 12px 8px 8px; }
.voice-trigger { display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0; padding: 4px 10px 4px 4px; border: 0; border-radius: 13px; background: transparent; text-align: left; transition: background .15s; }
.voice-trigger:hover:not(:disabled) { background: #f6f2ff; }
.voice-trigger:hover:not(:disabled) .mic-orb { background: #7d64d1; transform: translateY(-1px) scale(1.03); }
.voice-trigger:active:not(:disabled) .mic-orb { transform: translateY(1px) scale(.97); border-bottom-width: 2px; }
.voice-trigger:hover:not(:disabled) .voice-bar-info b { color: #5b43b0; }
.voice-trigger:disabled { opacity: .65; cursor: not-allowed; }
.voice-trigger:disabled .mic-orb { background: #c9cbea; border-color: #b8badc; border-bottom-color: #a6a9cd; }
.voice-bar.live { border-color: #e0d8f5; background: #faf8ff; }
.mic-orb { position: relative; display: grid; place-items: center; width: 44px; height: 44px; flex: 0 0 44px; border: 2px solid #7358c8; border-bottom: 4px solid #593ea8; border-radius: 50%; background: #8b73dd; color: #fff; box-shadow: inset 0 2px 0 rgba(255, 255, 255, .25); transition: background .15s, transform .12s; }
.mic-orb:hover:not(:disabled) { background: #7d64d1; transform: translateY(-1px) scale(1.03); }
.mic-orb:active:not(:disabled) { transform: translateY(1px) scale(.97); border-bottom-width: 2px; }
.mic-orb:disabled { background: #c9cbea; border-color: #b8badc; border-bottom-color: #a6a9cd; cursor: not-allowed; }
.mic-orb.stop { background: var(--danger); border-color: #a13a4b; border-bottom-color: #842b3a; }
.mic-orb.static { background: #e3e2f4; border: 0; color: var(--brand-deep); animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.orb-ring { position: absolute; inset: -5px; border: 1.5px solid rgba(98, 101, 232, .3); border-radius: 50%; animation: orb-breathe 2.2s ease-in-out infinite; }
@keyframes orb-breathe { 50% { transform: scale(1.14); opacity: .35; } }
.orb-pulse { position: absolute; inset: -4px; border: 2px solid var(--danger); border-radius: 50%; animation: voice-ping 1.2s ease-out infinite; }
@keyframes voice-ping { from { opacity: .8; transform: scale(.9); } to { opacity: 0; transform: scale(1.3); } }
.voice-bar-info { display: flex; min-width: 0; flex: 1; flex-direction: column; align-items: flex-start; gap: 3px; border: 0; background: transparent; text-align: left; }
.voice-bar-info b { font-size: 14px; font-weight: 600; color: var(--ink); font-variant-numeric: tabular-nums; }
.voice-bar-info span { color: var(--muted); font-size: 11.5px; }
button.voice-bar-info:hover:not(:disabled) b { color: var(--brand-deep); }
button.voice-bar-info:disabled { opacity: .65; cursor: not-allowed; }
.live-hint { display: inline-flex; align-items: center; gap: 9px; }
.live-wave { display: inline-flex; align-items: center; gap: 2.5px; height: 15px; }
.live-wave i { width: 3px; border-radius: 2px; background: var(--brand); transition: height .12s ease; }
.icon-button { display: grid; place-items: center; width: 32px; height: 32px; flex: 0 0 32px; border: 0; border-radius: 8px; background: transparent; color: var(--muted); transition: background .15s, color .15s; }
.icon-button:hover:not(:disabled) { background: #f0f1f6; color: var(--ink); }
.icon-button:disabled { opacity: .45; }
/* foot 行右侧的模式切换小按钮 */
.foot-toggle { display: inline-flex; align-items: center; gap: 5px; padding: 2px 4px; border: 0; background: transparent; color: #7c7693; font-size: 12px; font-weight: 600; transition: color .15s, background .15s, border-color .15s; }
.foot-toggle:hover:not(:disabled) { color: var(--ink); }
.foot-toggle:disabled { opacity: .5; }
.foot-toggle.in-bar { height: 34px; padding: 0 12px; border: 1.5px solid #e7e1f5; border-bottom: 3px solid #dcd3f0; border-radius: 11px; background: #faf8ff; color: #694ec0; font-weight: 700; white-space: nowrap; }
.foot-toggle.in-bar:hover:not(:disabled) { border-color: #c9bdf0; background: #f2ecff; color: #583eb0; }
.ai-assist-btn { height: 30px; padding: 0 11px; font-size: 11.5px; border-radius: 9px; }
.ai-suggest-tray {
  margin-bottom: 10px; padding: 10px 12px; border-radius: 14px;
  border: 1.5px solid #e6dff5; background: #faf8ff; display: grid; gap: 8px;
}
.ai-suggest-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; font-size: 11.5px; font-weight: 650; color: #694ec0; }
.ai-suggest-head > span { display: inline-flex; align-items: center; gap: 5px; }
.ai-suggest-actions { display: flex; align-items: center; gap: 6px; }
.ai-mini-btn {
  border: 1px solid #dfd6f4; background: #fff; color: #694ec0; font-size: 11px; font-weight: 600;
  padding: 2px 8px; border-radius: 999px; cursor: pointer;
}
.ai-mini-btn:hover:not(:disabled) { background: #f2ecff; }
.ai-mini-close { border: 0; background: transparent; color: #8c85a6; padding: 2px; display: inline-flex; cursor: pointer; border-radius: 6px; }
.ai-mini-close:hover { background: #ede7fa; color: #583eb0; }
.ai-suggest-list { display: grid; gap: 6px; }
.ai-suggest-chip {
  display: flex; flex-direction: column; align-items: flex-start; gap: 2px; width: 100%;
  padding: 8px 11px; border-radius: 11px; border: 1.5px solid #ece6f8; border-bottom-width: 2.5px;
  background: #fff; text-align: left; cursor: pointer; transition: border-color .15s, background .15s;
}
.ai-suggest-chip:hover { border-color: #b79ced; background: #f6f2ff; }
.ai-suggest-chip b { font-size: 13px; font-weight: 600; color: #2d294b; line-height: 1.45; }
.ai-suggest-chip span { font-size: 11.5px; color: #7c7693; }
/* 转写结果确认：绿色浅底，文本限三行，操作右对齐 */
.voice-result { flex-direction: column; align-items: stretch; gap: 8px; border-color: #d9e8de; background: #f4faf6; }
.voice-result.is-staged { flex-direction: row; align-items: center; justify-content: space-between; gap: 10px; border-color: #e4def7; background: #faf8ff; }
.staged-capsule { border-radius: 999px; min-width: 132px; }
.voice-result-text { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 3; overflow: hidden; margin: 0; color: var(--ink); font-size: 14.5px; line-height: 1.7; white-space: pre-wrap; overflow-wrap: anywhere; }
.voice-result-actions { display: flex; align-items: center; justify-content: flex-end; gap: 6px; }
/* 继承旧版「场景工具栏 + 对话主区 + 辅助栏」，沿用 2.0 的色彩与控件。 */
.practice-page { flex: 1; min-height: 0; min-width: 0; display: flex; flex-direction: column; }
.practice-page.is-overlay-only { display: contents; }
button, a, textarea, select, summary { -webkit-app-region: no-drag; }
button { cursor: pointer; } button:disabled { cursor: not-allowed; }
button:focus-visible, a:focus-visible, summary:focus-visible { outline: 2px solid var(--brand); outline-offset: 3px; }
/* ---- 选场景页：工具行 + 卡片网格（对齐场景探索页） ---- */
.page-scroll { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: auto; padding: 22px 28px 32px; }
/* 历史记录入口的过渡态：会话恢复完成前不渲染场景选择页，避免列表闪一下 */
.practice-loading { display: flex; flex: 1; flex-direction: column; align-items: center; justify-content: center; gap: 16px; background: #faf9ff; }
.loading-ring { width: 40px; height: 40px; border: 3.5px solid #e2d8f8; border-top-color: #7c62d2; border-radius: 50%; box-shadow: 0 0 0 8px #f3eefd; animation: spin .8s linear infinite; }
.loading-copy { display: flex; flex-direction: column; align-items: center; gap: 6px; text-align: center; }
.loading-copy b { color: #3f3959; font-size: 15px; font-weight: 700; letter-spacing: -.01em; }
.loading-copy small { color: #948da8; font-size: 12.5px; }
.loading-track { position: relative; width: 156px; height: 4px; overflow: hidden; border-radius: 999px; background: #e8e1f7; }
.loading-track i { position: absolute; top: 0; bottom: 0; left: 0; width: 46%; border-radius: 999px; background: linear-gradient(90deg, #b6a2ee, #7c62d2); animation: loading-slide 1.1s cubic-bezier(.5, 0, .5, 1) infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes loading-slide { from { transform: translateX(-105%); } to { transform: translateX(230%); } }
.pick-toolbar { display: flex; flex: 0 0 auto; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.seg-filter { display: inline-flex; gap: 4px; padding: 4px; border: 1.5px solid #e9e5f1; border-radius: 13px; background: #fff; }
.seg-item { display: inline-flex; align-items: center; gap: 6px; height: 34px; padding: 0 13px; border: 0; border-radius: 10px; background: transparent; color: var(--ink-soft); font-size: 13.5px; font-weight: 600; white-space: nowrap; transition: background .15s, color .15s; }
.seg-item:hover { color: var(--ink); }
.seg-item.active { background: #eee8ff; color: #694fc1; font-weight: 700; }
.seg-count { color: var(--muted); font-size: 11.5px; }
.seg-item.active .seg-count { color: var(--brand); }
.toolbar-right { display: flex; align-items: center; gap: 9px; }
.search-box { position: relative; display: inline-flex; align-items: center; gap: 7px; width: 240px; height: 34px; padding: 0 10px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--faint); transition: border-color .15s, box-shadow .15s; }
.search-box:focus-within { border-color: var(--brand); box-shadow: 0 0 0 3px rgba(98, 101, 232, .12); }
.search-box input { flex: 1; min-width: 0; border: 0; outline: none; background: transparent; color: var(--ink); font-size: 13.5px; }
.search-box input::placeholder { color: var(--faint); }
.search-box input::-webkit-search-cancel-button { -webkit-appearance: none; appearance: none; display: none; }
.search-clear { display: grid; place-items: center; width: 18px; height: 18px; border: 0; border-radius: 50%; background: #eef0f5; color: var(--muted); transition: background .15s, color .15s; }
.search-clear:hover { background: #e3e5ee; color: var(--ink); }
.login-hint, .page-error { display: flex; flex-wrap: wrap; align-items: center; gap: 5px; margin: 0 0 18px; color: var(--muted); font-size: 13px; }
.login-hint a { color: var(--brand); }.page-error { color: var(--danger); }
.scene-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(275px, 1fr)); gap: 14px; align-content: start; flex: 1 0 auto; }
.scene-card { display: flex; flex-direction: column; padding: 0; overflow: visible; border: 1.5px solid #ebe7f5; border-bottom: 4px solid #e5def1; border-radius: 19px; background: #fff; text-align: left; transition: border-color .18s, transform .18s, box-shadow .18s; animation: card-in .38s cubic-bezier(.22, .8, .32, 1) backwards; }
.scene-card:hover:not(.busy) { border-color: #cfc1f1; border-bottom-color: #d9cdef; transform: translateY(-3px); box-shadow: 0 8px 18px #51408412; }
.scene-card:active:not(.busy) { transform: translateY(0); }
.scene-card:focus-visible { outline: 2px solid var(--brand); outline-offset: 3px; }
.scene-card.busy { opacity: .6; pointer-events: none; }
/* 整卡 hover 也让封面右上角标浮出（角标在子组件内，需穿透） */
.scene-card:hover :deep(.scene-cover-mark), .scene-card:focus-visible :deep(.scene-cover-mark) { opacity: 1; transform: translate(0, 0); }
/* 卡片正文：与封面对齐的内边距，foot 行贴底保证同排卡片底部齐平 */
.card-body { display: flex; flex-direction: column; flex: 1; padding: 13px 15px 15px; }
@keyframes card-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
.card-head { display: flex; align-items: center; gap: 7px; margin-bottom: 9px; }
.mode-chip { display: inline-flex; align-items: center; gap: 4px; height: 22px; padding: 0 9px; border-radius: 999px; background: var(--brand-soft); color: var(--brand-deep); font-size: 11.5px; font-weight: 600; }
.diff-chip { display: inline-flex; align-items: center; height: 22px; padding: 0 9px; border-radius: 999px; background: #f1f2f7; color: var(--ink-soft); font-size: 11.5px; font-weight: 600; }
.diff-chip.entry { background: #e3f2ea; color: #2f7a52; }
.diff-chip.easy { background: #e0f2ef; color: #257a6b; }
.diff-chip.normal { background: #e3ecfb; color: #33619f; }
.diff-chip.hard { background: #fdefe0; color: #b26a24; }
.diff-chip.expert { background: #fbe7e7; color: #b03a3a; }
.scene-desc { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; min-height: 42px; margin: 0; color: #6d6880; font-size: 13.5px; line-height: 1.55; text-wrap: pretty; }
.scene-foot { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: auto; padding-top: 12px; border-top: 1px solid #efedf5; }
.scene-meta { display: flex; flex-wrap: wrap; gap: 4px 8px; min-width: 0; }
.scene-meta span { display: inline-flex; align-items: center; gap: 3px; color: var(--muted); font-size: 11px; white-space: nowrap; }
.scene-go { display: inline-flex; align-items: center; gap: 4px; flex: 0 0 auto; color: var(--brand); font-size: 12.5px; font-weight: 600; white-space: nowrap; }
.scenes-empty { grid-column: 1 / -1; display: grid; justify-items: center; padding: 46px 20px; border: 2px dashed #d9d0ef; border-radius: 18px; background: #fff; text-align: center; }
.empty-icon { display: grid; width: 54px; height: 54px; place-items: center; border: 0; border-radius: 18px; background: #f0eaff; color: #8067d1; }
.scenes-empty h3 { margin: 14px 0 6px; font-size: 16px; font-weight: 600; }
.scenes-empty p { margin: 0; max-width: 400px; color: var(--muted); font-size: 13.5px; line-height: 1.65; text-wrap: pretty; }
.pagination { display: flex; flex-wrap: wrap; flex: 0 0 auto; justify-content: flex-end; align-items: center; gap: 6px; margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--line); }
.page-info { color: var(--muted); font-size: 12.5px; margin-right: 8px; }
.page-btn { display: inline-flex; align-items: center; gap: 4px; height: 31px; padding: 0 11px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--ink-soft); font-size: 13px; transition: border-color .15s, color .15s, background .15s; }
.page-btn:hover:not(:disabled):not(.active) { border-color: #d5d7e6; color: var(--ink); }
.page-btn:disabled { opacity: .45; cursor: default; }
.page-num { width: 31px; justify-content: center; padding: 0; }
.page-num.active { border-color: var(--brand); background: var(--brand-soft); color: var(--brand-deep, var(--brand)); font-weight: 500; }
.scene-card.skeleton { animation: none; cursor: default; }
.sk-cover { height: 100px; margin: -1.5px -1.5px 0; border-radius: 17px 17px 0 0; background: linear-gradient(90deg, #f0eef7 25%, #f8f7fc 45%, #f0eef7 65%); background-size: 200% 100%; animation: shimmer 1.3s infinite; }
.sk-body { padding: 13px 17px 17px; }
.sk-line { height: 12px; margin-top: 10px; border-radius: 5px; background: linear-gradient(90deg, #eef0f5 25%, #f6f7fa 45%, #eef0f5 65%); background-size: 200% 100%; animation: shimmer 1.3s infinite; }
.sk-line.w40 { width: 40%; margin-top: 0; }
.sk-line.w80 { width: 80%; height: 14px; }
.sk-line.w60 { width: 60%; }
.sk-line.w70 { width: 70%; }
@keyframes shimmer { from { background-position: 200% 0; } to { background-position: -200% 0; } }

/* ---- 进入对话确认弹窗（对齐场景探索页弹窗规范） ---- */
.modal-backdrop { position: fixed; inset: 0; z-index: 40; display: grid; place-items: center; background: var(--scrim-bg, rgba(34, 37, 59, .28)); -webkit-backdrop-filter: var(--scrim-blur, blur(2px)); backdrop-filter: var(--scrim-blur, blur(2px)); animation: fade-in .18s ease; }
.modal-card { width: min(380px, calc(100vw - 48px)); padding: 24px; border-radius: 14px; background: var(--surface); box-shadow: 0 18px 48px rgba(34, 37, 59, .18); animation: pop-in .22s cubic-bezier(.22, .8, .32, 1); }
.modal-icon { display: grid; width: 38px; height: 38px; margin-bottom: 14px; place-items: center; border-radius: 10px; background: var(--brand-soft); color: var(--brand-deep); }
.modal-card h3 { margin: 0 0 8px; font-size: 16.5px; font-weight: 600; }
.modal-card > p { margin: 0 0 14px; color: var(--muted); font-size: 13.5px; line-height: 1.65; text-wrap: pretty; }
.modal-facts { display: flex; flex-direction: column; gap: 7px; margin: 0 0 18px; padding: 11px 13px; border: 1px solid var(--line); border-radius: 10px; background: #fbfbfd; list-style: none; }
.modal-facts li { display: flex; align-items: center; justify-content: space-between; font-size: 12.5px; }
.modal-facts span { color: var(--muted); }
.modal-facts b { font-weight: 500; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; }
.confirm-button { display: inline-flex; align-items: center; gap: 6px; height: 38px; padding: 0 16px; border: 1.5px solid #7960cc; border-bottom: 4px solid #6349b4; border-radius: 12px; background: #8b73dd; color: #fff; font-size: 13.5px; font-weight: 700; transition: background .15s, transform .12s; }
.confirm-button:hover:not(:disabled) { background: #7d64d1; transform: translateY(-1px); }
.confirm-button:active:not(:disabled) { transform: translateY(1px); border-bottom-width: 2px; }
.confirm-button:disabled { opacity: .6; }
@keyframes fade-in { from { opacity: 0; } }
@keyframes pop-in { from { opacity: 0; transform: translateY(8px) scale(.97); } }
.ghost-button, .exit-button { display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; gap: 7px; min-height: 36px; padding: 0 13px; border: 1.5px solid #e7e1f5; border-bottom: 3px solid #dcd3f0; border-radius: 12px; background: white; color: #5b5572; font-size: 13px; font-weight: 650; text-decoration: none; transition: border-color .15s, background .15s, color .15s, transform .12s; }
.ghost-button:hover, .reference-button.active { border-color: #c9bdf0; background: #f3effd; color: #5b43b0; }
.exit-button { color: #a14959; background: #fff7f8; border-color: #f0dfe3; border-bottom-color: #e5ccd2; }
.exit-button:hover { background: #fdeff1; border-color: #e5c3cb; } button:disabled { opacity: .5; }
/* 页面内只滚动消息与辅助栏，输入始终可见。 */
.chat-page { display: flex; flex-direction: column; flex: 1; min-height: 0; padding: 0 24px 22px; }
.session-toolbar { display: flex; align-items: center; gap: 12px; flex: 0 0 auto; min-height: 72px; padding: 12px 0; }
.back-button { display: grid; place-items: center; width: 36px; height: 36px; flex-shrink: 0; background: white; border: 1.5px solid #e7e1f5; border-bottom: 3px solid #dcd3f0; border-radius: 11px; color: #6e6886; transition: border-color .15s, background .15s, color .15s, transform .12s; }
.back-button:hover { border-color: #c9bdf0; background: #f8f5ff; color: #5b43b0; }
.session-heading { min-width: 0; flex: 1; }.session-heading h2 { margin: 0; color: #2d294b; font-size: 18px; font-weight: 800; line-height: 1.5; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.session-heading p { margin: 3px 0 0; color: #7c7693; font-size: 12.5px; }.session-heading p span { margin: 0 8px; }
.chat-layout { flex: 1; min-height: 0; display: grid; grid-template-columns: minmax(0, 1fr) 264px; gap: 16px; }
.chat-layout.has-knowledge { grid-template-columns: minmax(0, 1fr) 360px; }
@media (max-width: 1439px) {
  .chat-layout.has-knowledge .chat-side { display: none; }
}
@media (min-width: 1440px) {
  .chat-layout.has-knowledge { grid-template-columns: minmax(0, 1fr) 248px 360px; }
}
@media (max-width: 960px) {
  .chat-layout.has-knowledge { grid-template-columns: minmax(0, 1fr) 236px; }
  .chat-knowledge-dock { position: fixed; right: 16px; bottom: 16px; top: 82px; z-index: 45; width: min(360px, calc(100vw - 32px)); height: auto !important; box-shadow: 0 20px 56px rgba(45, 41, 75, .24); }
}
.chat-card { display: flex; flex-direction: column; min-width: 0; min-height: 0; background: white; border: 1px solid var(--line); border-radius: 14px; overflow: hidden; }
.chat-head { display: flex; align-items: center; gap: 10px; padding: 14px 20px; border-bottom: 1px solid var(--line); flex-shrink: 0; }
.role-avatar { display: flex; align-items: flex-start; justify-content: center; flex: 0 0 36px; width: 36px; height: 36px; overflow: hidden; border-radius: 12px; background: #eee9ff; color: #694ec0; font-size: 14px; font-weight: 750; }
.role-avatar :deep(.portrait), .msg-avatar :deep(.portrait) { width: 144%; height: 144%; flex: 0 0 auto; transform: translateY(-2px); display: block; pointer-events: none; }
.dock-slide-enter-active, .dock-slide-leave-active { transition: opacity .22s cubic-bezier(.22, .8, .32, 1), transform .24s cubic-bezier(.22, .8, .32, 1); }
.dock-slide-enter-from, .dock-slide-leave-to { opacity: 0; transform: translateX(18px) scale(.98); }
.msg-avatar-user { margin-top: 21px; flex: 0 0 30px; border-radius: 12px; }
.role-info { flex: 1; min-width: 0; }.role-info b { display: block; color: #2d294b; font-size: 14px; font-weight: 750; }.role-status { display: flex; align-items: center; gap: 5px; margin-top: 4px; color: #7c7693; font-size: 12px; }.status-dot { width: 6px; height: 6px; border-radius: 50%; background: #48b884; }.status-dot.busy { background: #8b73dd; }
.text-toggle { display: inline-flex; align-items: center; gap: 5px; border: 1.5px solid #e6e3f2; border-bottom: 3px solid #dad4ec; border-radius: 999px; padding: 6px 11px; background: #faf9ff; color: #6b6485; font-size: 12px; font-weight: 650; transition: border-color .15s, background .15s, color .15s; }.text-toggle:hover { border-color: #c9bdf0; color: #5b43b0; }.text-toggle[aria-pressed="true"] { color: #694ec0; background: #eee9ff; border-color: #cfc1f1; border-bottom-color: #bfb0ea; }
/* 顶部信息条：阶段 / 场景状态，横向一条读完，不占右栏高度 */
.progress-rail { display: flex; align-items: center; gap: 9px; flex-shrink: 0; padding: 8px 18px; border-bottom: 1px solid #f1eef8; background: #fbfaff; }
.rail-stage { display: inline-flex; align-items: center; gap: 6px; min-width: 0; height: 28px; padding: 0 11px; border: 1.5px solid #e7e1f5; border-radius: 999px; background: #fff; color: #5b43b0; font-size: 12px; }
.rail-stage small { flex-shrink: 0; color: #7c7693; font-size: 11px; white-space: nowrap; }
.rail-stage b { overflow: hidden; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.rail-stage em { flex-shrink: 0; padding-left: 8px; border-left: 1px solid #ece8f8; color: #7c7693; font-size: 11px; font-style: normal; font-variant-numeric: tabular-nums; }
.rail-stage.is-open { color: #7c7693; }
.rail-goal { display: inline-flex; align-items: center; gap: 7px; min-width: 0; margin-left: auto; color: #9a94b4; font-size: 11px; white-space: nowrap; }
.rail-goal b { color: #6d6590; font-size: 11.5px; font-variant-numeric: tabular-nums; white-space: nowrap; }
.rail-goal progress { width: 60px; height: 5px; border: 0; border-radius: 999px; overflow: hidden; appearance: none; background: #ece9f7; }
.rail-goal progress::-webkit-progress-bar { background: #ece9f7; }
.rail-goal progress::-webkit-progress-value { border-radius: 999px; background: #9b8ce0; }
.rail-goal progress::-moz-progress-bar { border-radius: 999px; background: #9b8ce0; }
.rail-state { flex-shrink: 0; margin-left: auto; }
.rail-state-button { display: inline-flex; align-items: center; gap: 5px; height: 28px; padding: 0 11px; border: 1.5px solid #e7e1f5; border-bottom: 3px solid #dcd3f0; border-radius: 999px; background: #fff; color: #6b6485; font-size: 12px; font-weight: 600; transition: border-color .15s, color .15s; }
.rail-state-button:hover { border-color: #c9bdf0; color: #5b43b0; }
.rail-state-button svg:last-child { transition: transform .15s; }
.rail-state-button .flip { transform: rotate(180deg); }
.rail-pop-backdrop { position: fixed; inset: 0; z-index: 40; }
.rail-pop { position: fixed; z-index: 41; width: 212px; padding: 12px 14px; border: 1.5px solid #ebe7f5; border-bottom: 3px solid #e5def1; border-radius: 14px; background: #fff; box-shadow: 0 12px 32px rgba(52, 44, 86, .14); }
.rail-pop p { margin: 0 0 6px; color: var(--muted); font-size: 11px; }
.rail-pop ul { margin: 0; padding: 0; list-style: none; }
.rail-pop li { display: flex; justify-content: space-between; gap: 12px; padding: 5px 0; font-size: 12px; }
.rail-pop li span { color: var(--muted); }
.rail-pop li b { font-weight: 600; text-align: right; overflow-wrap: anywhere; }
.chat-body { flex: 1; min-height: 0; overflow: auto; overscroll-behavior: contain; padding: 20px 24px 28px; scrollbar-width: thin; background: #f8f9fc; }
.conversation-start { display: flex; align-items: center; justify-content: center; gap: 12px; margin: 0 0 28px; color: #7c7693; }.conversation-start span { height: 1px; flex: 1; max-width: 60px; background: #e6e1f2; }.conversation-start small { font-size: 12px; text-align: center; }
.msg-row { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 25px; }.msg-row.user { justify-content: flex-end; }.msg-avatar { display: flex; align-items: flex-start; justify-content: center; width: 30px; height: 30px; flex: 0 0 30px; overflow: hidden; margin-top: 21px; border-radius: 10px; background: #f0effa; color: #7771ac; font-size: 12.5px; font-weight: 600; }.msg-avatar.user { background: #e9edf7; color: #6c7a9a; }
.message-content { display: flex; flex-direction: column; align-items: flex-start; max-width: min(82%, 640px); }.msg-row.user .message-content { align-items: flex-end; }.message-author { margin-bottom: 6px; font-size: 12px; color: #7c7693; font-weight: 600; }
.bubble { padding: 11px 15px; background: white; border: 1px solid #ededf3; border-radius: 4px 15px 15px 15px; }.msg-row.user .bubble { background: #e4e2ff; border-color: #dedbfc; color: #37365e; border-radius: 15px 4px 15px 15px; }.bubble-text { margin: 0; font-size: 14px; line-height: 1.75; white-space: pre-wrap; overflow-wrap: anywhere; }
/* agent 语音气泡：交互结构沿用 1.0（胶囊常驻+进度条+原文面板），外观对齐 2.0 */
.bubble-row { display: flex; align-items: center; gap: 10px; }
.ai-voice-capsule { position: relative; display: flex; align-items: center; gap: 5px; height: 40px; min-width: 120px; max-width: 100%; padding: 0 12px; border: 1px solid #e8e7f0; border-radius: 4px 16px 16px 16px; background: white; color: #694ec0; overflow: hidden; transition: width .2s ease, background .15s, transform .15s; }
.ai-voice-capsule:hover:not(:disabled) { background: #f0efff; transform: scale(1.02); }
.ai-voice-capsule:active:not(:disabled) { transform: scale(.98); }
.ai-voice-capsule:disabled { opacity: .7; cursor: wait; }
.ai-voice-capsule.playing { background: white; }
.capsule-progress { position: absolute; left: 0; bottom: 0; height: 3px; background: #8b73dd; transition: width .12s linear; }
.capsule-duration { font-size: 12.5px; font-weight: 700; font-variant-numeric: tabular-nums; white-space: nowrap; }
.voice-wave-icon { flex: 0 0 auto; }
.spin { animation: spin 1s linear infinite; }
.ui-spinner {
  width: 13px; height: 13px; border-radius: 50%; flex: 0 0 auto;
  border: 2px solid rgba(105, 78, 192, 0.22); border-top-color: #694ec0;
  animation: spin .72s linear infinite;
}
.send-spinner { width: 14px; height: 14px; border-color: rgba(255, 255, 255, 0.34); border-top-color: #fff; }
.ai-voice-capsule.is-busy { border-color: #c8bbf0; background: linear-gradient(90deg, #faf8ff 0%, #f1ebff 50%, #faf8ff 100%); background-size: 200% 100%; animation: tts-shimmer 1.6s ease-in-out infinite; }
.tts-bars { display: inline-flex; align-items: center; gap: 2.5px; height: 14px; }
.tts-bars i { width: 2.5px; height: 6px; border-radius: 999px; background: #7b61ff; animation: tts-bar 0.9s ease-in-out infinite; }
.tts-bars i:nth-child(2) { animation-delay: 0.15s; }
.tts-bars i:nth-child(3) { animation-delay: 0.3s; }
@keyframes tts-bar { 0%, 100% { height: 5px; opacity: 0.55; } 50% { height: 14px; opacity: 1; } }
@keyframes tts-shimmer { 0% { background-position: 100% 0; } 100% { background-position: -100% 0; } }
.original-toggle { display: inline-flex; align-items: center; gap: 4px; padding: 5px 10px; border: 1.5px solid #e6e3f2; border-bottom: 3px solid #dad4ec; border-radius: 999px; background: #fff; color: #6b6485; font-size: 12px; font-weight: 650; transition: color .15s, border-color .15s; white-space: nowrap; }
.original-toggle:hover { color: #5b43b0; border-color: #c9bdf0; }
.original-panel { max-width: 100%; margin-top: 7px; padding: 11px 15px; border: 1px solid #ededf3; border-radius: 4px 15px 15px 15px; background: #fff; }
.panel-enter-active, .panel-leave-active {
  transition: height .22s cubic-bezier(.22, 1, .36, 1), opacity .18s ease, margin-top .22s cubic-bezier(.22, 1, .36, 1), padding-top .22s cubic-bezier(.22, 1, .36, 1), padding-bottom .22s cubic-bezier(.22, 1, .36, 1), border-top-width .22s cubic-bezier(.22, 1, .36, 1), border-bottom-width .22s cubic-bezier(.22, 1, .36, 1);
  overflow: hidden;
}
.thinking-message { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; }.thinking-message .msg-avatar { margin-top: 0; }.thinking-message small { color: var(--muted); font-size: 12.5px; }.thinking-dots { display: flex; gap: 4px; padding: 12px; border-radius: 10px; background: var(--bg); }.thinking-dots i { width: 4px; height: 4px; border-radius: 50%; background: var(--brand); }
.finish-banner { display: flex; align-items: center; gap: 8px; padding: 12px; color: #4a7f63; border-radius: 8px; background: #f1f8f3; font-size: 13.5px; }
.md-body { white-space: normal; }
.md-body :deep(p) { margin: 0 0 6px; }
.md-body :deep(p:last-child) { margin-bottom: 0; }
.md-body :deep(strong) { font-weight: 700; color: #2d294b; }
.md-body :deep(ul), .md-body :deep(ol) { margin: 4px 0 6px; padding-left: 18px; }
.md-body :deep(code) { padding: 1px 5px; border-radius: 4px; background: #f3f1fb; font-size: .9em; }
/* 右栏：伙伴舞台固定紧凑高度，目标卡紧随其后自然排布，避免人物上下大面积留白 */
.chat-side { display: flex; flex-direction: column; gap: 12px; min-height: 0; overflow-y: auto; }
.companion-card, .support-card { border: 1px solid var(--line); background: white; border-radius: 14px; overflow: hidden; }
.companion-card { display: flex; flex-direction: column; flex: 0 0 auto; padding: 12px; }
.side-head { display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; margin-bottom: 9px; }
h3 { margin: 0; color: #2d294b; font-size: 14px; font-weight: 750; }
.side-link { color: #7c7693; display: flex; padding: 3px; }
.companion-stage { display: flex; flex: 0 0 auto; height: 196px; }
.companion-card :deep(.stage) { width: 100% !important; height: 100%; aspect-ratio: auto; border-radius: 12px; border: 0; background: #f4f2fa; }
.companion-card :deep(.stage-top), .companion-card :deep(.edition), .companion-card :deep(.stage-bottom), .companion-card :deep(.spark) { display: none; }
.companion-card :deep(.character) { left: 17%; width: 66%; height: 93%; }
.companion-card :deep(.halo) { width: 64%; left: 18%; top: 15%; }
.companion-identity { display: flex; align-items: baseline; gap: 7px; flex-shrink: 0; margin: 10px 0 9px; }
.companion-identity b { color: #2d294b; font-size: 14px; font-weight: 750; }
.companion-identity span { overflow: hidden; color: #7c7693; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.companion-meta { display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-shrink: 0; padding-top: 8px; border-top: 1px solid #f1eef8; }
.companion-meta .autoplay-control { display: inline-flex; align-items: center; gap: 5px; margin: 0; color: #6e6886; font-size: 12px; font-weight: 600; white-space: nowrap; }
.companion-meta .autoplay-control input { width: 13px; height: 13px; accent-color: #8b73dd; }
.voice-summary { display: inline-flex; align-items: center; gap: 4px; min-width: 0; overflow: hidden; color: #7c7693; font-size: 11.5px; text-overflow: ellipsis; white-space: nowrap; }
.companion-rate { display: flex; align-items: center; gap: 8px; flex-shrink: 0; margin-top: 8px; padding-top: 8px; border-top: 1px dashed #f1eef8; }
.rate-label { flex: 0 0 auto; font-size: 11.5px; font-weight: 600; color: #6e6886; }
.rate-slider { flex: 1; min-width: 0; height: 4px; accent-color: #8b73dd; cursor: pointer; }
.rate-value { flex: 0 0 auto; min-width: 42px; text-align: right; font-size: 11.5px; font-weight: 700; color: #694ec0; font-variant-numeric: tabular-nums; }
.voice-settings { border-top: 1px solid var(--line); padding-top: 10px; }summary { cursor: pointer; list-style: none; }summary::-webkit-details-marker { display: none; }.voice-settings summary { display: flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--ink-soft); }.voice-settings summary span { margin-left: auto; font-size: 11.5px; }.voice-controls { display: grid; gap: 8px; padding: 12px 0 1px; }.voice-controls label { color: var(--muted); font-size: 11.5px; }.voice-select { min-width: 0; width: 100%; height: 32px; border: 1px solid var(--line); border-radius: 6px; color: var(--ink-soft); background: white; font-size: 12.5px; }.voice-rate { width: 100%; accent-color: var(--brand); }
.support-card { display: flex; flex: 0 0 auto; flex-direction: column; }
.support-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 12px 14px 9px; }
.support-head span { color: #694ec0; font-size: 12px; font-weight: 750; font-variant-numeric: tabular-nums; }
.goal-progress { display: block; width: calc(100% - 28px); height: 6px; margin: 0 14px; border: 0; appearance: none; background: #f0eff7; border-radius: 999px; overflow: hidden; accent-color: #8b73dd; }.goal-progress::-webkit-progress-bar { background: #eee9fa; }.goal-progress::-webkit-progress-value { background: #8b73dd; border-radius: 999px; }.goal-progress::-moz-progress-bar { background: #8b73dd; }
.goal-list { list-style: none; padding: 4px 14px 0; margin: 0; }.goal-list li { display: flex; gap: 9px; align-items: flex-start; padding: 6px 0; color: #3d3857; font-size: 12.5px; line-height: 1.65; }.goal-number { display: grid; place-items: center; width: 20px; height: 20px; flex: 0 0 20px; border: 1.5px solid #e2daf5; border-radius: 50%; color: #7c7693; font-size: 11px; font-weight: 700; }.done .goal-number { color: #2c8a5e; border-color: #bde4cf; background: #e8f8f0; }.done>span:last-child { color: #7c7693; }
.goal-list small { display: block; color: #7c7693; font-size: 11px; line-height: 1.6; }
.support-foot { display: flex; align-items: center; gap: 5px; margin: 6px 0 0; padding: 8px 14px 10px; border-top: 1px solid #f5f2fb; color: #7c7693; font-size: 11px; }
.support-empty { margin: 8px 14px 12px; color: var(--muted); font-size: 12px; line-height: 1.8; }
.reference-link { display: flex; align-items: center; justify-content: space-between; margin-top: 18px; color: var(--brand); text-decoration: none; font-size: 12.5px; }
/* 场景知识点（参考 Tab，迁移自 1.0 知识抽屉） */
@media (min-width: 1550px) { .chat-page { padding: 0 36px 28px; }.chat-layout { grid-template-columns: minmax(0, 1fr) 288px; gap: 22px; }.chat-body { padding: 24px 36px; } }
@media (max-width: 1100px) { .chat-page { padding: 0 16px 16px; }.chat-layout { grid-template-columns: minmax(0, 1fr) 236px; gap: 12px; }.chat-head { padding: 12px 14px; }.progress-rail { gap: 7px; padding: 7px 14px; }.rail-stage, .rail-state-button { padding: 0 8px; }.rail-stage small { display: none; }.rail-goal progress { width: 40px; }.chat-body { padding: 16px 14px; }.composer-area { margin: 0 14px; }.role-info b { font-size: 13px; } }
/* 矮窗口：收紧头像高度，保证右栏一屏装下 */
@media (max-height: 720px) { .session-toolbar { min-height: 64px; padding: 10px 0; }.companion-stage { height: 158px; }.companion-identity { margin: 8px 0 7px; }.goal-list li { padding: 5px 0; } }
@media (max-width: 760px) { .chat-page { overflow: auto; }.chat-layout { display: flex; flex-direction: column; flex: 1 0 auto; }.chat-card { min-height: 520px; height: calc(100dvh - 170px); }.chat-side { display: grid; grid-template-columns: 1fr 1fr; overflow: visible; min-height: auto; }.session-toolbar { flex-wrap: wrap; gap: 8px; padding: 12px 0; }.session-heading h2 { font-size: 14px; }.session-heading { flex-basis: calc(100% - 45px); }.reference-button { margin-left: 40px; }.session-toolbar .exit-button { margin-left: auto; }.page-scroll { padding: 24px 18px; }.keyboard-hint { display: none; } }
@media (max-width: 480px) { .chat-side { grid-template-columns: 1fr; }.message-content { max-width: 82%; }.bubble { padding: 10px 12px; }.bubble-text { font-size: 14px; }.text-toggle { max-width: 80px; }.role-info b { max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } }
@media (prefers-reduced-motion: no-preference) { .thinking-dots i { animation: breathe 1.2s ease-in-out infinite; }.thinking-dots i:nth-child(2) { animation-delay: .15s; }.thinking-dots i:nth-child(3) { animation-delay: .3s; }@keyframes breathe { 50% { opacity: .25; transform: translateY(-2px); } } }
/* 对话页与练习场景统一：更清楚的任务卡片与轻柔聊天底色。 */
.page-scroll { padding: 24px clamp(18px, 2.4vw, 34px) 30px; background: #faf9ff; }
.pick-toolbar { margin-bottom: 18px; }
.chat-page { padding: 0 clamp(16px, 2vw, 30px) 24px; background: #faf9ff; }
.session-toolbar { min-height: 74px; }
.session-heading h2 { color: #393451; font-weight: 750; }
.chat-card, .companion-card, .support-card { border: 1.5px solid #ebe7f5; border-bottom: 4px solid #e5def1; border-radius: 18px; }
.chat-head { background: #fff; }
.chat-body { background: #faf9fd; }
.chat-side { gap: 14px; }
.companion-card, .support-card { background: #fff; }
.msg-avatar { border-radius: 12px; background: #eee9ff; color: #7059c0; }
.msg-avatar.user { background: #e8f3ee; color: #568b72; }
.bubble { border: 1.5px solid #eae6f2; border-bottom: 3px solid #e4dfec; border-radius: 5px 17px 17px 17px; background: #fff; }
.msg-row.user .bubble { border-color: #d9d0f8; border-bottom-color: #c8bbef; border-radius: 17px 5px 17px 17px; background: #eee9ff; color: #393451; }
.bubble-row.is-user-voice { justify-content: flex-end; }
.user-voice-capsule {
  flex-direction: row-reverse;
  border-color: #d9d0f8; border-bottom-color: #c8bbef;
  border-radius: 16px 5px 16px 16px;
  background: #eee9ff; color: #4e3b94;
}
.user-voice-capsule.staged-capsule .voice-wave-icon { transform: none; }
.user-voice-capsule:hover:not(:disabled) { background: #e6deff; }
.user-voice-capsule .capsule-progress { background: rgba(115, 87, 204, 0.14); }
.user-voice-capsule.is-static { opacity: 0.92; }
.original-panel.is-user {
  border-color: #eae6f2; background: #fff; color: #393451;
  border-radius: 15px 4px 15px 15px; text-align: left;
}
.user-feedback-wrap { margin-top: 6px; display: flex; flex-direction: column; align-items: flex-end; max-width: 100%; }
.fb-collapse-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px; border-radius: 999px; cursor: pointer;
  background: #fff; border: 1.5px solid #e6e3f2; border-bottom-width: 2.5px;
  color: #6b6485; font-size: 11.5px; font-weight: 600;
  transition: background .15s, border-color .15s;
}
.fb-collapse-pill:hover, .fb-collapse-pill.is-open { background: #fff; border-color: #d3c9f0; color: #53439c; }
.fb-collapse-pill b.is-high { color: #16a34a; }
.fb-collapse-pill b.is-mid { color: #d97706; }
.fb-collapse-pill b.is-low { color: #e11d48; }
.fb-collapse-pill .flip { transform: rotate(180deg); transition: transform .18s; }
.fb-dot-hint { width: 6px; height: 6px; border-radius: 999px; background: #8b73dd; flex-shrink: 0; }
.user-feedback-card {
  margin-top: 6px; max-width: 440px; width: fit-content; min-width: 240px;
  background: #fff; border: 1.5px solid #eae6f2; border-bottom: 3px solid #e4dfec;
  border-radius: 14px; padding: 9px 13px; text-align: left;
  display: flex; flex-direction: column; gap: 8px;
}
.fb-summary { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.fb-stats { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; font-size: 12px; color: #7c7693; }
.fb-stat { display: inline-flex; align-items: center; gap: 4px; }
.fb-stat b { font-weight: 750; font-size: 12.5px; }
.fb-stat b.is-high { color: #16a34a; }
.fb-stat b.is-mid { color: #d97706; }
.fb-stat b.is-low { color: #e11d48; }
.fb-stat small { font-size: 11px; color: #8b84a3; }
.fb-sep { color: #d5cfe4; font-weight: 700; }
.fb-word-toggle {
  display: inline-flex; align-items: center; gap: 3px; flex-shrink: 0;
  border: 0; background: #f6f4fc; color: #6d5cb0; border-radius: 999px;
  padding: 2px 8px; font-size: 11px; font-weight: 650; cursor: pointer;
  transition: background .15s;
}
.fb-word-toggle:hover { background: #ede8fb; }
.fb-word-toggle .flip { transform: rotate(180deg); }
.fb-words {
  display: flex; flex-wrap: wrap; gap: 6px 10px;
  padding: 7px 10px; border-radius: 10px; background: #faf9fd; border: 1px solid #f0ecf8;
}
.fb-word {
  display: inline-flex; align-items: baseline; gap: 3px; font-size: 12.5px; font-weight: 600;
  color: #393451; padding-bottom: 1px; border-bottom: 2px solid transparent;
}
.fb-word small { font-size: 10px; font-weight: 600; color: #8c85a6; }
.fb-word.is-high { border-bottom-color: #86efac; }
.fb-word.is-mid { border-bottom-color: #fcd34d; }
.fb-word.is-low { border-bottom-color: #fda4af; color: #be123c; }
.fb-word.is-low small { color: #e11d48; }
.fb-correction { padding-top: 7px; border-top: 1px solid #f0ecf7; }
.fb-summary + .fb-correction, .fb-words + .fb-correction { padding-top: 8px; }
.user-feedback-card > .fb-correction:first-child { padding-top: 0; border-top: 0; }
.fb-corr-label { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; font-weight: 700; color: #7357cc; margin-bottom: 3px; }
.fb-corr-sentence { margin: 0; font-size: 13px; font-weight: 650; color: #2d294b; line-height: 1.5; }
.fb-corr-note { margin: 3px 0 0; font-size: 12px; color: #6e6885; line-height: 1.55; }
.fb-alts { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 6px; }
.fb-alt {
  padding: 2px 8px; border-radius: 8px; background: #f7f5fc;
  border: 1px solid #e7e1f5; color: #544b75; font-size: 11.5px; line-height: 1.45;
}
.fb-corr-ok { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 600; color: #1f7a4c; }
.ai-voice-capsule { border: 1.5px solid #eae6f2; border-bottom: 3px solid #e4dfec; border-radius: 5px 16px 16px 16px; }
.ai-voice-capsule:hover:not(:disabled) { background: #f6f2ff; }
.ai-voice-capsule.user-voice-capsule:not(.staged-capsule) {
  flex-direction: row-reverse;
  border-color: #d9d0f8; border-bottom-color: #c8bbef;
  border-radius: 16px 5px 16px 16px;
  background: #eee9ff; color: #4e3b94;
}
.ai-voice-capsule.user-voice-capsule:not(.staged-capsule):hover:not(:disabled) { background: #e6deff; }
.user-voice-capsule:not(.staged-capsule) .voice-wave-icon { transform: scaleX(-1); }
.user-voice-capsule:not(.staged-capsule) .capsule-progress { left: auto; right: 0; }
.ai-voice-capsule.user-voice-capsule.staged-capsule {
  flex-direction: row;
  border-color: #d9d0f8; border-bottom-color: #c8bbef;
  border-radius: 999px;
  background: #eee9ff; color: #4e3b94;
}
.ai-voice-capsule.user-voice-capsule.staged-capsule .voice-wave-icon { transform: none; }
.ai-voice-capsule.user-voice-capsule.staged-capsule .capsule-progress { left: 0; right: auto; }
.original-toggle, .text-toggle { border-radius: 999px; }
.composer { border: 1.5px solid #eae6f2; border-bottom-width: 3px; border-radius: 16px; background: #fff; }
.composer:focus-within { border-color: #b5a4e9; }
.primary-button.slim, .ghost-button, .confirm-button, .exit-button { min-height: 38px; border-radius: 12px; font-weight: 650; }
.back-button { width: 36px; height: 36px; border: 1.5px solid #e7e1f5; border-bottom: 3px solid #dcd3f0; border-radius: 11px; }
.ghost-button { border: 1.5px solid #e7e1f5; border-bottom: 3px solid #dcd3f0; }
.exit-button { border: 1.5px solid #f0dfe3; border-bottom: 3px solid #e5ccd2; }
.text-toggle, .original-toggle { border: 1.5px solid #e6e3f2; border-bottom: 3px solid #dad4ec; }
.back-button:active, .ghost-button:active, .exit-button:active { transform: translateY(1px); }
.confirm-button { border-bottom: 4px solid #6951b8; background: #8b73dd; }
.modal-card { border: 1.5px solid #ebe7f5; border-bottom: 5px solid #e5def1; border-radius: 20px; }
.modal-icon { border-radius: 14px; background: #f0eaff; color: #7158c4; }

.rail-stage-btn { cursor: pointer; font-family: inherit; font-size: 12px; line-height: 1; transition: border-color .15s, background .15s; }
.rail-stage-btn:hover { border-color: #c9bce8; background: #f8f6ff; }
.stage-pop { width: 292px; max-width: calc(100vw - 24px); }
.stage-pop .stage-pop-list { display: grid; gap: 6px; }
.stage-pop .stage-pop-list li { display: flex; align-items: flex-start; justify-content: flex-start; gap: 9px; padding: 6px 8px; border-radius: 10px; text-align: left; }
.stage-pop .stage-pop-list li.is-current { background: #f4f0ff; }
.stage-num {
  display: grid; place-items: center; width: 20px; height: 20px; flex: 0 0 20px; margin-top: 1px;
  border: 1.5px solid #e2daf5; border-radius: 50%; color: #7c7693; font-size: 11px; font-weight: 700;
}
.stage-pop .stage-pop-list li.is-current .stage-num { border-color: #8b73dd; background: #8b73dd; color: #fff; }
.stage-pop .stage-pop-list li.is-done .stage-num { border-color: #bde4cf; background: #e8f8f0; color: #2c8a5e; }
.stage-pop .stage-meta { display: flex; flex: 1; flex-direction: column; gap: 2px; min-width: 0; text-align: left; }
.stage-pop .stage-meta b { display: block; font-size: 12.5px; font-weight: 650; color: #2d294b; text-align: left; }
.stage-pop .stage-pop-list li.is-done .stage-meta b { color: #6e6885; }
.stage-pop .stage-meta small { display: block; font-size: 11px; line-height: 1.5; color: #7c7693; text-align: left; }

</style>

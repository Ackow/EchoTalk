<template>
  <section class="debate-page">
    <!-- 视图一：多角色对话大厅 -->
    <div v-if="!inArena" class="debate-hub">
      <div class="debate-toolbar">
        <AppTabs
          v-model="selectedCategory"
          :options="categoryOptions"
          aria-label="场景分类筛选"
        />
        <div class="hub-meta-chips">
          <span class="meta-chip">辩论对抗 · 多人圆桌/群面</span>
          <span class="meta-chip brand">完成整场 +40 XP</span>
        </div>
      </div>

      <div v-if="topicsLoading" class="hub-state-banner">正在加载多角色场景库...</div>
      <div v-else-if="topicsError" class="hub-state-banner error">{{ topicsError }}</div>

      <div class="topics-grid">
        <article
          v-for="topic in filteredTopics"
          :key="topic.id"
          class="topic-card"
          @click="openSetupModal(topic)"
        >
          <div class="topic-head">
            <div class="topic-badges">
              <span class="cat-badge">{{ topic.categoryLabel }}</span>
              <span class="submode-badge" :class="topic.sceneType === 'panel' ? 'panel' : 'debate'">
                {{ topic.sceneType === 'panel' ? '多人对话' : '正反辩论' }}
              </span>
            </div>
            <span class="diff-badge" :class="topic.levelTone">{{ topic.levelLabel }}</span>
          </div>

          <h3 class="topic-title">{{ topic.titleZh }}</h3>
          <p class="topic-motion">{{ topic.motionEn }}</p>

          <div class="stance-preview">
            <div class="stance-row pro">
              <span class="stance-tag">{{ topic.sceneType === 'panel' ? '亮点' : '正方' }}</span>
              <p>{{ topic.proSummary }}</p>
            </div>
            <div class="stance-row con">
              <span class="stance-tag">{{ topic.sceneType === 'panel' ? '追问' : '反方' }}</span>
              <p>{{ topic.conSummary }}</p>
            </div>
          </div>

          <div class="topic-foot">
            <span class="topic-meta">
              <AppIcon name="clock" :size="13" />
              <span>{{ topic.duration }} · {{ topic.stages?.length || 4 }} 阶段 · {{ topic.roles?.length || 3 }} 角色</span>
            </span>
            <div class="topic-actions">
              <button
                v-if="topic.canManage"
                type="button"
                class="topic-icon-btn"
                title="编辑场景"
                @click.stop="openEditTopic(topic)"
              >
                <AppIcon name="pencil" :size="13" />
              </button>
              <button
                v-if="topic.canManage"
                type="button"
                class="topic-icon-btn danger"
                title="删除场景"
                @click.stop="askRemoveTopic(topic)"
              >
                <AppIcon name="trash" :size="13" />
              </button>
              <button type="button" class="topic-btn" @click.stop="openSetupModal(topic)">
                {{ topic.sceneType === 'panel' ? '进入圆桌' : '开始辩论' }}
              </button>
            </div>
          </div>
        </article>

        <div v-if="!topicsLoading && !topicsError && !filteredTopics.length" class="debate-empty-card">
          <div class="debate-empty-icon"><AppIcon name="compass" :size="20" /></div>
          <h3>{{ selectedCategory !== 'all' ? '该分类下暂无多角色场景' : '训练台暂无多角色场景' }}</h3>
          <p>
            {{
              selectedCategory !== 'all'
                ? '可以切换其他分类，或前往场景探索页浏览并收藏更多多角色场景。'
                : '在场景探索页收藏内置/社区场景，或新建专属群面与辩论场景。'
            }}
          </p>
          <button
            type="button"
            class="debate-empty-cta"
            @click="router.push({ name: 'scenes', query: { tab: 'debate' } })"
          >
            <AppIcon name="compass" :size="14" />
            <span>前往场景探索</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 视图二：多角色沉浸式对话 / 辩论工作台 -->
    <div v-else class="debate-arena">
      <header class="arena-head">
        <div class="arena-head-left">
          <button type="button" class="back-btn" @click="exitArena">
            <AppIcon name="chevron-left" :size="16" />
            <span>返回</span>
          </button>
          <div class="arena-title-wrap">
            <div class="arena-title-row">
              <h2>{{ activeTopic.titleZh }}</h2>
              <span class="my-side-pill" :class="isPanelMode ? 'panel' : userSide">
                {{ isPanelMode ? `我方：${activeTopic?.userRoleLabel || '候选人 / 主讲人'}` : `我方：${userSide === 'pro' ? '正方' : '反方'}` }}
              </span>
            </div>
            <p class="arena-motion">{{ activeTopic.motionEn }}</p>
          </div>
        </div>

        <div class="arena-head-actions">
          <button
            type="button"
            class="ghost-btn"
            :class="{ active: showZh }"
            @click="showZh = !showZh"
          >
            {{ showZh ? '隐藏中文' : '双语对照' }}
          </button>
          <button type="button" class="primary-btn" :disabled="finishing" @click="requestFinishVerdict">
            <AppIcon name="star" :size="15" />
            <span>{{ finishing ? (isPanelMode ? '评估中…' : '裁决中…') : (isPanelMode ? '结束并查看评估' : '结束并裁决') }}</span>
          </button>
        </div>
      </header>

      <!-- 统一工作区：主对话流 + 右侧多角色数字人圆桌舞台 -->
      <div class="arena-grid">
        <div class="chat-panel">
          <!-- 顶部：实时胜率 / 认可度进度 + 阶段条 -->
          <div class="panel-top">
            <div v-if="!isPanelMode" class="battle-hud">
              <div class="hud-side mine">
                <span class="hud-label">我方 ({{ userSide === 'pro' ? '正' : '反' }})</span>
                <strong>{{ winRate }}%</strong>
              </div>
              <div class="tug-bar" :aria-label="`当前赢面 ${winRate}%`">
                <div class="tug-fill" :style="{ width: `${winRate}%` }">
                  <span class="tug-spark"></span>
                </div>
              </div>
              <div class="hud-side opp">
                <strong>{{ 100 - winRate }}%</strong>
                <span class="hud-label">对手</span>
              </div>
              <span class="combo-pill" :class="{ hot: comboCount >= 2 }">
                <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                  <path d="M9.2 1.5L3.5 9h4.2l-1 5.5L12.5 7H8.3l.9-5.5z" fill="currentColor" />
                </svg>
                <span>连击 ×{{ comboCount }}</span>
              </span>
              <span class="round-pill">第 {{ turnCount }}/{{ maxTurns }} 轮</span>
            </div>

            <div v-else class="battle-hud">
              <div class="hud-side mine">
                <span class="hud-label">委员会认可度</span>
                <strong>{{ winRate }}%</strong>
              </div>
              <div class="tug-bar panel" :aria-label="`委员会认可度 ${winRate}%`">
                <div class="tug-fill" :style="{ width: `${winRate}%` }">
                  <span class="tug-spark"></span>
                </div>
              </div>
              <span class="combo-pill" :class="{ hot: comboCount >= 2 }">
                <span>有效回应 ×{{ comboCount }}</span>
              </span>
              <span class="round-pill">第 {{ turnCount }}/{{ maxTurns }} 轮</span>
            </div>

            <div
              class="stage-bar"
              :style="{ gridTemplateColumns: `repeat(${activeStages.length}, minmax(0, 1fr))` }"
            >
              <div
                v-for="(st, idx) in activeStages"
                :key="st.id"
                class="stage-pill"
                :class="{ done: idx < stageIndex, active: idx === stageIndex }"
              >
                <span class="step-num">{{ idx < stageIndex ? '✓' : idx + 1 }}</span>
                <span>{{ st.label }}</span>
              </div>
            </div>
          </div>

          <!-- 中间：主音频辅文字的气泡式对话流 -->
          <div ref="feedRef" class="debate-feed">
            <div
              v-for="msg in messages"
              :key="msg.id"
              class="msg-row"
              :class="msg.role === 'user' ? 'is-user' : 'is-ai'"
            >
              <div v-if="msg.role !== 'user'" class="msg-avatar" :class="msg.role">
                {{ msg.speaker.slice(0, 1) }}
              </div>
              <div class="msg-col">
                <div class="msg-meta">
                  <span class="role-tag" :class="msg.role">{{ msg.roleLabel }}</span>
                  <span class="msg-speaker">{{ msg.speaker }}</span>
                  <span class="msg-stage">{{ msg.stageLabel }}</span>
                </div>

                <VoiceBubbleRow
                  :role="msg.role"
                  :is-user="msg.role === 'user'"
                  :is-voice="msg.role !== 'user' || Boolean(msg.isVoice)"
                  :text="msg.en"
                  :zh-text="showZh ? msg.zh : ''"
                  :duration="msg.duration || 0"
                  :playing="playingMsgId === msg.id"
                  :busy="loadingMsgId === msg.id"
                  :progress="msgAudioProgress"
                  :show-original="false"
                  :expanded="expandedMsgIds.has(msg.id)"
                  @toggle-play="toggleMsgAudio(msg)"
                  @toggle-original="toggleMsgText(msg.id)"
                />
              </div>
            </div>
          </div>

          <!-- 底部：语音优先输入栏 -->
          <PracticeComposer
            v-model:draft="draft"
            :input-mode="inputMode"
            :voice-busy="voiceBusy"
            :voice-status="voiceStatus"
            :voice-status-label="voiceStatusLabel"
            :recording-seconds="recordingSeconds"
            :recording-supported="recordingSupported"
            :asr-available="asrAvailable"
            :voice-cta-text="voiceCtaText"
            :voice-hint-text="voiceHintText"
            :transcribed-text="transcribedText"
            :pending-voice-duration="pendingVoiceDuration"
            :playing-key="playingKey"
            :playback-time="playbackTime"
            :playback-duration="playbackDuration"
            :sending="sending"
            :finished="false"
            :suggesting="suggesting"
            :reply-suggestions="debateSuggestions"
            :level-bar="levelBar"
            :error="voiceError"
            :playback-notice="''"
            @start-recording="startVoiceInput"
            @stop-recording="stopRecording"
            @cancel-recording="cancelRecording"
            @retry-recording="retryRecording"
            @discard-pending="clearPendingVoice"
            @play-pending="playPendingVoice"
            @stop-audio="stopPendingVoice"
            @send-transcribed="sendPendingVoice"
            @send-turn="submitUserTurn()"
            @toggle-input-mode="toggleInputMode"
            @request-assist="toggleDebateTips"
            @apply-suggestion="applyDebateTip"
            @clear-suggestions="debateSuggestions = []"
          />
        </div>

        <!-- 右侧：多角色同屏圆桌舞台 + 四维雷达战况面板 -->
        <aside class="arena-side">
          <div class="side-card roundtable-stage">
            <div class="side-card-head">
              <h4>{{ isPanelMode ? '同台对话席位' : '圆桌辩论席' }}</h4>
              <label class="auto-play-check">
                <input v-model="autoPlayAudio" type="checkbox" />
                <span>自动播报</span>
              </label>
            </div>
            <div
              class="stage-seats"
              :style="{ gridTemplateColumns: `repeat(${Math.min(4, Math.max(2, aiRoles.length))}, minmax(0, 1fr))` }"
            >
              <button
                v-for="role in aiRoles"
                :key="role.id"
                type="button"
                class="seat-stage-card"
                :class="[role.roleType, { speaking: speakingRole === role.id }]"
                @click="speakingRole = role.id"
              >
                <span v-if="speakingRole === role.id" class="live-dot" aria-hidden="true"></span>
                <div class="seat-portrait-box">
                  <CharacterPortrait
                    :character="roleAvatarObj(role).id"
                    :appearance="roleAvatarObj(role).appearance || null"
                    :state="roleStageState(role.id)"
                    :lip-sync="true"
                    :theme="roleAvatarObj(role).theme || 'amber'"
                    :name="role.name"
                  />
                </div>
                <strong class="seat-name">{{ role.name }}</strong>
                <span class="seat-role">{{ role.title }}</span>
              </button>
            </div>
          </div>

          <div class="side-card">
            <div class="side-card-head">
              <h4>{{ isPanelMode ? '实时评估雷达' : '战况雷达' }}</h4>
              <span class="momentum-tag" :class="winRate >= 50 ? 'up' : 'down'">
                {{ isPanelMode ? '认可度' : (winRate >= 50 ? '占优' : '胶着') }} {{ winRate }}%
              </span>
            </div>

            <!-- 4 维 SVG 迷你雷达图 -->
            <div class="radar-wrap">
              <svg viewBox="0 0 248 184" class="radar-svg" aria-label="四维能力雷达图">
                <polygon
                  v-for="(ring, rIdx) in [0.35, 0.65, 1]"
                  :key="rIdx"
                  :points="radarRingPoints(ring)"
                  class="radar-grid"
                />
                <line x1="124" y1="38" x2="124" y2="146" class="radar-axis" />
                <line x1="70" y1="92" x2="178" y2="92" class="radar-axis" />
                <polygon :points="radarDataPoints" class="radar-area" />
                <circle
                  v-for="(pt, pIdx) in radarDataCoords"
                  :key="pIdx"
                  :cx="pt.x"
                  :cy="pt.y"
                  r="3.5"
                  class="radar-dot"
                />
                <text x="124" y="24" text-anchor="middle" class="radar-label">逻辑 {{ scores.logic }}</text>
                <text x="186" y="96" text-anchor="start" class="radar-label">{{ isPanelMode ? '应变' : '反驳' }} {{ scores.rebuttal }}</text>
                <text x="124" y="168" text-anchor="middle" class="radar-label">气场 {{ scores.presence }}</text>
                <text x="62" y="96" text-anchor="end" class="radar-label">地道 {{ scores.fluency }}</text>
              </svg>
            </div>

            <div class="mini-kpi-row">
              <span class="kpi-chip">阶段目标：{{ activeStages[stageIndex]?.shortTag || '推进' }}</span>
              <span class="kpi-chip xp">+40 XP</span>
            </div>
          </div>
        </aside>
      </div>
    </div>

    <!-- 选边与配置弹窗 -->
    <div v-if="setupTopic" class="modal-backdrop" @click.self="setupTopic = null">
      <div class="setup-modal">
        <div class="setup-head">
          <div class="topic-badges">
            <span class="cat-badge">{{ setupTopic.categoryLabel }}</span>
            <span class="submode-badge" :class="setupTopic.sceneType === 'panel' ? 'panel' : 'debate'">
              {{ setupTopic.sceneType === 'panel' ? '多人对话 / 群面' : '正反辩论' }}
            </span>
          </div>
          <h3>{{ setupTopic.titleZh }}</h3>
          <p>{{ setupTopic.motionEn }}</p>
        </div>

        <div v-if="setupTopic.sceneType !== 'panel'" class="setup-section">
          <label>选择你的辩论立场</label>
          <div class="side-picker">
            <button
              type="button"
              class="side-option pro"
              :class="{ selected: userSide === 'pro' }"
              @click="userSide = 'pro'"
            >
              <strong>正方（支持）</strong>
              <span>{{ setupTopic.proSummary }}</span>
            </button>
            <button
              type="button"
              class="side-option con"
              :class="{ selected: userSide === 'con' }"
              @click="userSide = 'con'"
            >
              <strong>反方（反对）</strong>
              <span>{{ setupTopic.conSummary }}</span>
            </button>
          </div>
        </div>

        <div v-else class="setup-section">
          <label>本场身份与同台 AI 阵容</label>
          <div class="panel-lineup-card">
            <div class="panel-user-row">
              <span>你的身份</span>
              <strong>{{ setupTopic.userRoleLabel || '候选人 / 主讲人' }}</strong>
            </div>
            <div class="panel-roles-chips">
              <span v-for="r in (setupTopic.roles || [])" :key="r.id || r.name" class="panel-role-pill">
                <b>{{ r.name }}</b> · {{ r.title || '评审成员' }}
              </span>
            </div>
          </div>
        </div>

        <div class="setup-section">
          <label>{{ setupTopic.sceneType === 'panel' ? 'AI 追问压力等级' : 'AI 对手交锋风格' }}</label>
          <div class="style-pills">
            <button
              v-for="opt in OPPONENT_STYLES"
              :key="opt.id"
              type="button"
              class="style-pill"
              :class="{ selected: opponentStyle === opt.id }"
              @click="opponentStyle = opt.id"
            >
              {{ opt.label }}
            </button>
          </div>
        </div>

        <p v-if="setupError" class="setup-error">{{ setupError }}</p>

        <div class="setup-actions">
          <button type="button" class="btn-cancel" @click="setupTopic = null">取消</button>
          <button type="button" class="btn-start" @click="enterArena">
            {{ setupTopic.sceneType === 'panel' ? '进入多人对话场' : '进入辩论场' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 终场评估 / 裁决报告弹窗 -->
    <div v-if="showVerdictModal" class="modal-backdrop" @click.self="showVerdictModal = false">
      <div class="verdict-modal">
        <div class="verdict-head">
          <span class="xp-badge">+{{ verdictResult?.xp_awarded ?? 40 }} XP</span>
          <h3>{{ isPanelMode ? '多角色综合评估报告' : '评委终场裁决报告' }}</h3>
          <p>{{ activeTopic?.titleZh }}</p>
        </div>
        <div class="verdict-scores">
          <div class="v-score">
            <strong>{{ verdictResult?.avg_score ?? Math.round((scores.logic + scores.rebuttal + scores.fluency + scores.presence) / 4) }}</strong>
            <span>综合表现分</span>
          </div>
          <div class="v-summary">
            <strong>{{ isPanelMode ? '委员会评语' : '裁决评语' }}</strong>
            <p>{{ verdictResult?.summary || '表达清晰切题、回应结构稳定；建议后续多补充具体数据或真实案例进一步提升说服力。' }}</p>
          </div>
        </div>
        <div class="setup-actions">
          <button type="button" class="btn-cancel" @click="showVerdictModal = false">{{ isPanelMode ? '继续对话' : '继续辩论' }}</button>
          <button type="button" class="btn-start" @click="finishToHub">返回场景大厅</button>
        </div>
      </div>
    </div>

    <!-- 删除确认弹窗 -->
    <div v-if="deletingTopic" class="modal-backdrop" @click.self="deletingTopic = null">
      <div class="setup-modal delete-confirm-modal">
        <div class="setup-head">
          <span class="cat-badge">删除确认</span>
          <h3>确认删除「{{ deletingTopic.titleZh }}」？</h3>
          <p>删除后无法恢复该自定义多角色场景，但已产生的历史练习记录不受影响。</p>
        </div>
        <div class="setup-actions">
          <button type="button" class="btn-cancel" @click="deletingTopic = null">取消</button>
          <button type="button" class="btn-danger" @click="confirmRemoveTopic">确认删除</button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import AppTabs from '../components/AppTabs.vue'
import CharacterPortrait from '../components/avatar/CharacterPortrait.vue'
import PracticeComposer from '../components/practice/PracticeComposer.vue'
import VoiceBubbleRow from '../components/practice/VoiceBubbleRow.vue'
import { usePageLoading } from '../app/loading'
import { FALLBACK_AVATARS, listAvatars, synthesizeSpeech } from '../api/avatar'
import {
  createDebateSession,
  deleteDebateTopic,
  finishDebateSession,
  getDebateSession,
  listDebateTopics,
  submitDebateTurn,
  suggestDebateReply,
} from '../api/debate'
import { getSpeechStatus } from '../api/speech'
import { useVoiceInput } from '../composables/useVoiceInput'

const route = useRoute()
const router = useRouter()
const finishLoading = usePageLoading()

const topics = ref([])
const topicsLoading = ref(false)
const topicsError = ref('')
const setupError = ref('')
const avatarOptions = ref([...FALLBACK_AVATARS])

const STAGES = [
  { id: 'opening', label: '开篇立论', shortTag: '立论', guide: '用 2–3 句清晰亮明我方核心立场，并给出 1 个最有力支撑理由。' },
  { id: 'cross', label: '交叉质询', shortTag: '质询', guide: '针对对方刚才的质疑正面回应，并用 “However / Even if...” 稳住前提。' },
  { id: 'rebuttal', label: '焦点攻防', shortTag: '攻防', guide: '抓住双方最大分歧点直接反击，尽量带入一个具体场景或对比。' },
  { id: 'closing', label: '总结裁决', shortTag: '裁决', guide: '重申我方核心收益，对比双方得失，完成收官陈词。' }
]

const OPPONENT_STYLES = [
  { id: 'gentle', label: '温和引导' },
  { id: 'logical', label: '逻辑严密' },
  { id: 'sharp', label: '犀利压迫' }
]

const selectedCategory = ref('all')
const categoryOptions = computed(() => [
  { value: 'all', label: '全部场景', count: topics.value.length },
  { value: 'tech', label: '科技伦理', count: topics.value.filter((t) => t.category === 'tech').length },
  { value: 'workplace', label: '职场文化', count: topics.value.filter((t) => t.category === 'workplace').length },
  { value: 'education', label: '教育成长', count: topics.value.filter((t) => t.category === 'education').length },
  { value: 'society', label: '社会生活', count: topics.value.filter((t) => t.category === 'society').length }
])

const filteredTopics = computed(() => {
  if (selectedCategory.value === 'all') return topics.value
  return topics.value.filter((t) => t.category === selectedCategory.value)
})

const setupTopic = ref(null)
const deletingTopic = ref(null)
const activeTopic = ref(null)
const activeSessionSceneType = ref('debate')
const activeMaxTurns = ref(6)
const debateSessionId = ref('')
const inArena = ref(false)
const userSide = ref('pro')
const opponentStyle = ref('logical')

const isPanelMode = computed(() => (activeTopic.value?.sceneType || activeSessionSceneType.value) === 'panel')
const activeStages = computed(() => (Array.isArray(activeTopic.value?.stages) && activeTopic.value.stages.length ? activeTopic.value.stages : STAGES))
const maxTurns = computed(() => activeMaxTurns.value || activeTopic.value?.maxTurns || 6)

const stageIndex = ref(0)
const turnCount = ref(1)
const speakingRole = ref('moderator')
const showZh = ref(true)
const showVerdictModal = ref(false)
const verdictResult = ref(null)
const finishing = ref(false)
const sending = ref(false)
const suggesting = ref(false)
const draft = ref('')
const feedRef = ref(null)
const debateSuggestions = ref([])
const scores = ref({ logic: 78, rebuttal: 74, fluency: 82, presence: 80 })
const winRate = ref(54)
const comboCount = ref(1)
const autoPlayAudio = ref(true)
const playingMsgId = ref('')
const loadingMsgId = ref('')
const msgAudioProgress = ref(0)
const expandedMsgIds = ref(new Set())
let msgAudioEl = null
let seqPlaybackToken = 0
const debateTtsCache = new Map()

// 语音输入状态（与语音对话页 Practice.vue 保持一致）
const inputMode = ref('voice')
const asrAvailable = ref(true)
const voiceError = ref('')
const transcribedText = ref('')
const pendingVoiceBlobUrl = ref('')
const pendingVoiceDuration = ref(0)
const playingKey = ref('')
const playbackTime = ref(0)
const playbackDuration = ref(0)
let previewAudio = null

const {
  supported: recordingSupported,
  status: voiceStatus,
  busy: voiceBusy,
  seconds: recordingSeconds,
  levelBars,
  start: startRecording,
  stop: stopRecording,
  cancel: cancelRecording,
} = useVoiceInput({
  onResult(text, meta) {
    if (pendingVoiceBlobUrl.value) URL.revokeObjectURL(pendingVoiceBlobUrl.value)
    transcribedText.value = [draft.value.trim(), text].filter(Boolean).join(' ')
    pendingVoiceBlobUrl.value = meta?.blob ? URL.createObjectURL(meta.blob) : ''
    pendingVoiceDuration.value = Number(meta?.duration || 0)
  },
  onError(message) {
    voiceError.value = message
  }
})

const voiceStatusLabel = computed(() => ({
  requesting: '正在请求麦克风权限…',
  recording: '正在录音',
  stopping: '正在整理录音…',
  transcribing: '正在识别英语…'
}[voiceStatus.value] || '语音输入'))

const voiceCtaText = computed(() => {
  if (!recordingSupported) return '当前环境不支持录音'
  if (asrAvailable.value === false) return '语音识别暂不可用'
  return '点击开始语音发言'
})

const voiceHintText = computed(() => {
  if (!recordingSupported || asrAvailable.value === false) return '可切换右侧「文字输入」直接发表辩词'
  return '支持英语语音识别 · 识别后可试听或切换文字编辑'
})

function levelBar(idx) {
  return `${Math.max(4, Math.round((levelBars.value?.[idx] || 0.15) * 18))}px`
}

async function startVoiceInput() {
  voiceError.value = ''
  stopPendingVoice()
  await startRecording()
}

function stopPendingVoice() {
  if (previewAudio) {
    previewAudio.pause()
    previewAudio = null
  }
  playingKey.value = ''
  playbackTime.value = 0
}

function playPendingVoice() {
  if (!pendingVoiceBlobUrl.value) return
  stopPendingVoice()
  previewAudio = new Audio(pendingVoiceBlobUrl.value)
  playingKey.value = '__pending__'
  previewAudio.ontimeupdate = () => {
    playbackTime.value = previewAudio?.currentTime || 0
    playbackDuration.value = previewAudio?.duration || pendingVoiceDuration.value || 2
  }
  previewAudio.onended = () => {
    playingKey.value = ''
  }
  previewAudio.play().catch(() => {
    playingKey.value = ''
  })
}

function clearPendingVoice() {
  stopPendingVoice()
  if (pendingVoiceBlobUrl.value) {
    URL.revokeObjectURL(pendingVoiceBlobUrl.value)
    pendingVoiceBlobUrl.value = ''
  }
  transcribedText.value = ''
  pendingVoiceDuration.value = 0
}

async function retryRecording() {
  clearPendingVoice()
  await startVoiceInput()
}

function toggleInputMode() {
  if (inputMode.value === 'voice') {
    if (transcribedText.value) {
      draft.value = transcribedText.value
      clearPendingVoice()
    }
    inputMode.value = 'text'
  } else {
    inputMode.value = 'voice'
  }
}

function sendPendingVoice() {
  const text = transcribedText.value.trim()
  if (!text) return
  const dur = Math.max(1, Math.round(pendingVoiceDuration.value || 2))
  clearPendingVoice()
  void submitUserTurn({ text, isVoice: true, duration: dur })
}

const aiRoles = computed(() => {
  const list = activeTopic.value?.roles
  if (Array.isArray(list) && list.length) {
    return list.map((r, idx) => ({
      id: r.id || `role_${idx + 1}`,
      roleType: r.roleType || 'interviewer',
      initial: (r.name || 'AI').slice(0, 1).toUpperCase(),
      name: r.name || `Role ${idx + 1}`,
      title: r.title || '',
      avatarId: r.avatarId || 'sarah_2d',
      voice: r.voice || 'sonia',
    }))
  }
  return [
    { id: 'moderator', roleType: 'moderator', initial: 'M', name: 'Brian', title: '主持人', avatarId: 'david_2d', voice: 'brian' },
    {
      id: 'opponent',
      roleType: 'opponent',
      initial: userSide.value === 'pro' ? '反' : '正',
      name: activeTopic.value?.opponentName || 'Sonia',
      title: activeTopic.value?.opponentTitle || (userSide.value === 'pro' ? '反方辩手' : '正方辩手'),
      avatarId: activeTopic.value?.opponentAvatarId || 'sarah_2d',
      voice: activeTopic.value?.opponentVoice || 'sonia',
    },
    { id: 'judge', roleType: 'judge', initial: 'J', name: 'Andrew', title: '特邀评委', avatarId: 'leo_2d', voice: 'andrew' }
  ]
})

function roleAvatarObj(role) {
  const targetId = typeof role === 'string'
    ? (aiRoles.value.find((r) => r.id === role || r.roleType === role)?.avatarId || 'david_2d')
    : (role?.avatarId || 'david_2d')
  return avatarOptions.value.find((a) => a.id === targetId) || avatarOptions.value[0] || FALLBACK_AVATARS[0]
}

function findRoleIdForMessage(msg) {
  if (!msg || msg.role === 'user') return ''
  const list = aiRoles.value
  const bySpeaker = msg.speaker && list.find((r) => r.name === msg.speaker)
  if (bySpeaker) return bySpeaker.id
  const byType = msg.role && list.find((r) => r.roleType === msg.role || r.id === msg.role)
  if (byType) return byType.id
  return list[0]?.id || ''
}

function roleStageState(roleId) {
  if (playingMsgId.value && speakingRole.value === roleId) return 'speaking'
  if (voiceBusy.value && speakingRole.value === roleId) return 'listening'
  return 'idle'
}

function radarRingPoints(scale) {
  const cx = 124
  const cy = 92
  const r = 54 * scale
  return `${cx},${(cy - r).toFixed(1)} ${(cx + r).toFixed(1)},${cy} ${cx},${(cy + r).toFixed(1)} ${(cx - r).toFixed(1)},${cy}`
}

const radarDataCoords = computed(() => {
  const cx = 124
  const cy = 92
  const r = 54
  return [
    { x: cx, y: Number((cy - (r * scores.value.logic) / 100).toFixed(1)) },
    { x: Number((cx + (r * scores.value.rebuttal) / 100).toFixed(1)), y: cy },
    { x: cx, y: Number((cy + (r * scores.value.presence) / 100).toFixed(1)) },
    { x: Number((cx - (r * scores.value.fluency) / 100).toFixed(1)), y: cy }
  ]
})

const radarDataPoints = computed(() => radarDataCoords.value.map((p) => `${p.x},${p.y}`).join(' '))

function estimateSec(text) {
  const words = String(text || '').trim().split(/\s+/).filter(Boolean).length
  return Math.max(3, Math.round(words / 2.4))
}

function toggleMsgText(id) {
  const next = new Set(expandedMsgIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expandedMsgIds.value = next
}

function stopMsgAudio(cancelSequence = true) {
  if (cancelSequence) seqPlaybackToken += 1
  if (msgAudioEl) {
    msgAudioEl.pause()
    msgAudioEl.onended = null
    msgAudioEl.ontimeupdate = null
    msgAudioEl.onerror = null
    msgAudioEl = null
  }
  playingMsgId.value = ''
  msgAudioProgress.value = 0
}

function clearMsgAudioCache() {
  stopMsgAudio(true)
}

async function fetchMsgTtsUrl(msg) {
  const cacheKey = `${msg.voiceStyle || 'brian'}:${msg.en}`
  let url = debateTtsCache.get(cacheKey)
  if (!url) {
    loadingMsgId.value = msg.id
    try {
      const blob = await synthesizeSpeech(msg.en, msg.voiceStyle || 'brian', 1.0)
      url = URL.createObjectURL(blob)
      if (debateTtsCache.size >= 50) {
        const oldestKey = debateTtsCache.keys().next().value
        const oldestUrl = debateTtsCache.get(oldestKey)
        if (oldestUrl) URL.revokeObjectURL(oldestUrl)
        debateTtsCache.delete(oldestKey)
      }
      debateTtsCache.set(cacheKey, url)
    } finally {
      if (loadingMsgId.value === msg.id) loadingMsgId.value = ''
    }
  }
  return url
}

function playSingleMsgAudio(msg, token) {
  return new Promise((resolve) => {
    if (!msg?.en || !inArena.value || token !== seqPlaybackToken) {
      resolve()
      return
    }
    const rid = findRoleIdForMessage(msg)
    if (rid) speakingRole.value = rid
    fetchMsgTtsUrl(msg)
      .then((url) => {
        if (!inArena.value || token !== seqPlaybackToken) {
          resolve()
          return
        }
        stopMsgAudio(false)
        msgAudioEl = new Audio(url)
        playingMsgId.value = msg.id
        msgAudioProgress.value = 0
        const finish = () => {
          stopMsgAudio(false)
          resolve()
        }
        msgAudioEl.ontimeupdate = () => {
          if (msgAudioEl?.duration) {
            msgAudioProgress.value = Math.min(100, (msgAudioEl.currentTime / msgAudioEl.duration) * 100)
          }
        }
        msgAudioEl.onended = finish
        msgAudioEl.onerror = finish
        msgAudioEl.play().catch(finish)
      })
      .catch(() => resolve())
  })
}

async function playMessagesSequentially(msgList) {
  if (!Array.isArray(msgList) || !msgList.length) return
  stopMsgAudio(true)
  const token = seqPlaybackToken
  for (const msg of msgList) {
    if (!inArena.value || token !== seqPlaybackToken) break
    await playSingleMsgAudio(msg, token)
  }
}

async function toggleMsgAudio(msg) {
  if (!msg?.en) return
  if (playingMsgId.value === msg.id) {
    stopMsgAudio(true)
    return
  }
  stopMsgAudio(true)
  const token = seqPlaybackToken
  await playSingleMsgAudio(msg, token)
}

const messages = ref([])

async function toggleDebateTips() {
  if (debateSuggestions.value.length) {
    debateSuggestions.value = []
    return
  }
  if (Array.isArray(activeTopic.value?.tools) && !activeTopic.value.tools.includes('rebuttal_hint')) {
    voiceError.value = '当前场景未启用「回复与表达提示」工具'
    return
  }
  if (suggesting.value) return
  if (!debateSessionId.value) {
    voiceError.value = '当前会话尚未就绪，请重新进入多角色对话场'
    return
  }
  suggesting.value = true
  voiceError.value = ''
  try {
    const { data } = await suggestDebateReply(debateSessionId.value)
    if (Array.isArray(data?.suggestions) && data.suggestions.length) {
      debateSuggestions.value = data.suggestions
    } else {
      voiceError.value = '暂无可用提示，请稍后再试'
    }
  } catch (err) {
    voiceError.value = err?.message || '获取参考回复提示失败，请重试'
  } finally {
    suggesting.value = false
  }
}

function applyDebateTip(en) {
  draft.value = draft.value ? `${draft.value.trim()} ${en}` : en
  inputMode.value = 'text'
  debateSuggestions.value = []
}

function openSetupModal(topic) {
  setupError.value = ''
  setupTopic.value = topic
}

function normalizeTopicItem(t) {
  const toneMap = { beginner: 'easy', intermediate: 'medium', advanced: 'hard' }
  return {
    ...t,
    levelLabel: t.difficultyLabel || '进阶',
    levelTone: toneMap[t.difficulty] || 'medium'
  }
}

function openEditTopic(topic) {
  router.push({ name: 'debate-edit', params: { id: topic.id }, query: { from: 'debate' } })
}

function askRemoveTopic(topic) {
  deletingTopic.value = topic
}

async function confirmRemoveTopic() {
  if (!deletingTopic.value) return
  const target = deletingTopic.value
  deletingTopic.value = null
  try {
    await deleteDebateTopic(target.id)
    topics.value = topics.value.filter((t) => t.id !== target.id)
  } catch {
    // 忽略删除失败
  }
}

async function enterArena() {
  if (!setupTopic.value) return
  const chosen = setupTopic.value
  setupError.value = ''
  const styleToLevel = { gentle: 'supportive', logical: 'balanced', sharp: 'sharp' }
  try {
    const { data } = await createDebateSession({
      topic_id: chosen.id,
      user_side: chosen.sceneType === 'panel' ? 'pro' : userSide.value,
      difficulty_level: styleToLevel[opponentStyle.value] || 'balanced'
    })
    activeTopic.value = data.topic || chosen
    activeSessionSceneType.value = data.session.scene_type || activeTopic.value?.sceneType || 'debate'
    activeMaxTurns.value = data.session.max_turns || activeTopic.value?.maxTurns || 6
    setupTopic.value = null
    inArena.value = true
    debateSessionId.value = data.session.id
    stageIndex.value = data.session.stage_index
    turnCount.value = data.session.turn_count
    winRate.value = data.session.win_rate
    comboCount.value = data.session.combo_count
    scores.value = data.session.scores
    debateSuggestions.value = []
    voiceError.value = ''
    verdictResult.value = null
    clearPendingVoice()
    clearMsgAudioCache()
    expandedMsgIds.value = new Set()
    messages.value = data.messages || []
    speakingRole.value = findRoleIdForMessage(messages.value[0]) || aiRoles.value[0]?.id || 'moderator'
    if (autoPlayAudio.value && messages.value.length) {
      void nextTick(() => playMessagesSequentially(messages.value.filter((m) => m.role !== 'user')))
    }
  } catch (err) {
    setupError.value = err?.message || '进入多角色对话场失败，请先登录或稍后重试'
  }
}

function exitArena() {
  clearPendingVoice()
  clearMsgAudioCache()
  inArena.value = false
  activeTopic.value = null
  debateSessionId.value = ''
  verdictResult.value = null
}

async function requestFinishVerdict() {
  if (finishing.value) return
  if (!debateSessionId.value) {
    showVerdictModal.value = true
    return
  }
  finishing.value = true
  try {
    const { data } = await finishDebateSession(debateSessionId.value)
    verdictResult.value = { ...data.verdict, xp_awarded: data.xp_awarded ?? data.verdict?.xp_awarded ?? 40 }
  } catch {
    // 兜底保留弹窗展示
  } finally {
    finishing.value = false
    showVerdictModal.value = true
  }
}

function finishToHub() {
  showVerdictModal.value = false
  exitArena()
}

async function submitUserTurn(voicePayload = null) {
  const isVoice = Boolean(voicePayload?.isVoice)
  const text = String(isVoice ? voicePayload.text : draft.value).trim()
  if (!text || sending.value) return
  if (!debateSessionId.value) {
    voiceError.value = '当前会话未连接，请退出后重新进入'
    return
  }
  if (!isVoice) draft.value = ''
  debateSuggestions.value = []
  voiceError.value = ''
  sending.value = true
  try {
    const { data } = await submitDebateTurn(debateSessionId.value, {
      text,
      is_voice: isVoice,
      duration: voicePayload?.duration || null
    })
    const newMsgs = data.new_messages || []
    messages.value.push(...newMsgs)
    stageIndex.value = data.session.stage_index
    turnCount.value = data.session.turn_count
    if (data.session.max_turns) activeMaxTurns.value = data.session.max_turns
    comboCount.value = data.session.combo_count
    winRate.value = data.session.win_rate
    scores.value = data.session.scores
    const aiMsgs = newMsgs.filter((m) => m.role !== 'user')
    const firstAi = aiMsgs[0]
    if (firstAi) {
      const rid = findRoleIdForMessage(firstAi)
      if (rid) speakingRole.value = rid
    }
    await nextTick()
    if (feedRef.value) feedRef.value.scrollTop = feedRef.value.scrollHeight
    if (autoPlayAudio.value && aiMsgs.length) {
      void playMessagesSequentially(aiMsgs)
    }
  } catch (err) {
    if (!isVoice) draft.value = text
    voiceError.value = err?.message || '提交发言失败，请重试'
  } finally {
    sending.value = false
  }
}

onMounted(async () => {
  try {
    const [, avList] = await Promise.all([
      getSpeechStatus()
        .then(({ data }) => { asrAvailable.value = Boolean(data?.configured) })
        .catch(() => { asrAvailable.value = true }),
      listAvatars().catch(() => null),
    ])
    if (Array.isArray(avList) && avList.length) {
      avatarOptions.value = avList
    }

    topicsLoading.value = true
    topicsError.value = ''
    try {
      const { data } = await listDebateTopics()
      if (Array.isArray(data?.items)) {
        const allTopics = data.items.map(normalizeTopicItem)
        // 优先展示本人创建或已收藏的场景；新用户尚无自有/收藏时兜底展示官方内置场景
        const curated = allTopics.filter((t) => t.isMine || t.stats?.favorited)
        let visible = curated.length ? curated : allTopics.filter((t) => t.isBuiltin !== false)
        const topicIdParam = String(route.query?.topic || '').trim()
        if (topicIdParam) {
          const foundTopic = allTopics.find((t) => t.id === topicIdParam)
          if (foundTopic) {
            if (!visible.some((t) => t.id === foundTopic.id)) visible = [foundTopic, ...visible]
            openSetupModal(foundTopic)
          }
        }
        topics.value = visible
      }
    } catch (err) {
      topicsError.value = err?.message || '多角色场景加载失败，请刷新或登录后重试'
    } finally {
      topicsLoading.value = false
    }

    const resumeId = String(route.query?.session || '').trim()
    if (resumeId) {
      try {
        const { data } = await getDebateSession(resumeId)
        debateSessionId.value = data.session.id
        activeTopic.value = data.topic || {
          id: data.session.topic_id,
          titleZh: data.session.topic_title,
          motionEn: data.session.motion_en,
          sceneType: data.session.scene_type || 'debate',
        }
        activeSessionSceneType.value = data.session.scene_type || activeTopic.value?.sceneType || 'debate'
        activeMaxTurns.value = data.session.max_turns || activeTopic.value?.maxTurns || 6
        userSide.value = data.session.user_side || 'pro'
        stageIndex.value = data.session.stage_index || 0
        turnCount.value = data.session.turn_count || 1
        winRate.value = data.session.win_rate || 54
        comboCount.value = data.session.combo_count || 1
        scores.value = data.session.scores || { logic: 78, rebuttal: 74, fluency: 82, presence: 80 }
        verdictResult.value = data.session.verdict || null
        messages.value = data.messages || []
        const lastAi = [...messages.value].reverse().find((m) => m.role !== 'user')
        speakingRole.value = findRoleIdForMessage(lastAi) || aiRoles.value[0]?.id || 'moderator'
        inArena.value = true
      } catch {
        // 忽略无效的 session query
      }
    }
  } finally {
    finishLoading()
  }
})

onBeforeUnmount(() => {
  clearPendingVoice()
  clearMsgAudioCache()
})
</script>

<style scoped>
.debate-page {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 22px 28px 28px;
  overflow-y: auto;
}

.debate-hub {
  width: 100%;
  max-width: 1320px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.debate-arena {
  width: 100%;
  max-width: 1320px;
  margin: 0 auto;
  flex: 1;
  min-height: 520px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.debate-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.hub-meta-chips {
  display: flex;
  align-items: center;
  gap: 8px;
}

.meta-chip {
  padding: 5px 11px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface);
  font-size: 12px;
  color: var(--ink-soft);
}

.meta-chip.brand {
  border-color: #dadcf8;
  background: var(--brand-soft);
  color: var(--brand);
  font-weight: 500;
}

/* 卡片对齐 Scenes.vue / EchoTalk 扁平克制规范 */
.topics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(310px, 1fr));
  gap: 14px;
}

.topic-card {
  display: flex;
  flex-direction: column;
  padding: 16px 18px;
  border: 1.5px solid #ebe7f5;
  border-bottom: 4px solid #e3dcf2;
  border-radius: 18px;
  background: #ffffff;
  cursor: pointer;
  transition: border-color 0.16s, transform 0.16s, box-shadow 0.16s;
}

.topic-card:hover {
  transform: translateY(-2px);
  border-color: #c7bbf0;
  box-shadow: 0 10px 24px rgba(59, 49, 102, 0.07);
}

.topic-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}

.cat-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 6px;
  background: var(--brand-soft);
  color: var(--brand);
  font-size: 11px;
  font-weight: 500;
}

.topic-badges {
  display: flex;
  align-items: center;
  gap: 6px;
}

.diff-badge,
.xp-badge {
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
}

.diff-badge.easy { background: #eef8f3; color: #2a875a; }
.diff-badge.medium { background: #eff0ff; color: var(--brand); }
.diff-badge.hard { background: #fdf3ee; color: #b95e2f; }

.xp-badge {
  background: #eef8f3;
  color: #2a875a;
}

.topic-title {
  margin: 0 0 4px;
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
  line-height: 1.4;
}

.topic-motion {
  margin: 0 0 12px;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.5;
}

.stance-preview {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.stance-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 7px 10px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fafbfe;
  font-size: 12px;
  line-height: 1.45;
  color: var(--ink-soft);
}

.stance-row p { margin: 0; }

.stance-tag {
  flex: 0 0 auto;
  padding: 1px 6px;
  border-radius: 5px;
  font-size: 10.5px;
  font-weight: 600;
}

.stance-row.pro .stance-tag { background: #e8f6ef; color: #257a50; }
.stance-row.con .stance-tag { background: #fcefeb; color: #b54c3c; }

.topic-foot {
  margin-top: 13px;
  padding-top: 11px;
  border-top: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.topic-meta {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--muted);
}

.topic-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.topic-icon-btn {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 1.5px solid #e6e1f2;
  border-bottom: 2.5px solid #d6cee8;
  border-radius: 9px;
  background: #ffffff;
  color: #6b6584;
}

.topic-icon-btn:hover {
  border-color: #c2b6e6;
  color: #5d43b2;
}

.topic-icon-btn.danger:hover {
  border-color: #eab7ae;
  color: #b84a39;
}

.topic-manage-modal {
  width: min(680px, 100%);
  max-height: min(88vh, 780px);
  overflow-y: auto;
}

.ai-gen-box {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 8px;
  border: 1.5px solid #e1d8f5;
  border-radius: 13px;
  background: #f7f4ff;
}

.ai-gen-box input {
  flex: 1;
  min-width: 0;
  border: 0;
  background: transparent;
  padding: 4px 8px;
  font-size: 13px;
  color: #2c2742;
  outline: none;
}

.ai-gen-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 32px;
  padding: 0 12px;
  border: 1.5px solid #8067d1;
  border-bottom: 3px solid #6951b8;
  border-radius: 10px;
  background: #8b73dd;
  color: #ffffff;
  font-size: 12px;
  font-weight: 700;
  flex: 0 0 auto;
}

.ai-gen-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-row-3 {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.topic-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.form-row-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-field span {
  font-size: 12px;
  font-weight: 600;
  color: #554f6c;
}

.form-field input,
.form-field textarea,
.form-field select {
  padding: 8px 11px;
  border: 1.5px solid #e4dff0;
  border-radius: 10px;
  background: #faf9fe;
  font-size: 13px;
  color: #2c2742;
  font-family: inherit;
}

.form-error {
  margin: 0;
  font-size: 12px;
  color: #b84a39;
}

.topic-btn {
  height: 32px;
  padding: 0 14px;
  border: 1.5px solid #d9d1f2;
  border-bottom: 3px solid #c5b9e9;
  border-radius: 10px;
  background: #f6f3ff;
  color: #6046b4;
  font-size: 12.5px;
  font-weight: 700;
  transition: background 0.14s, color 0.14s, border-color 0.14s;
}

.topic-card:hover .topic-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.topic-icon-btn {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 1.5px solid #e6e1f2;
  border-bottom: 2.5px solid #d6cee8;
  border-radius: 9px;
  background: #ffffff;
  color: #6b6584;
}

.topic-icon-btn:hover {
  border-color: #c2b6e6;
  color: #5d43b2;
}

.topic-icon-btn.danger:hover {
  border-color: #eab7ae;
  color: #b84a39;
}

.topic-manage-modal {
  width: min(680px, 100%);
  max-height: min(88vh, 780px);
  overflow-y: auto;
}

.ai-gen-box {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 8px;
  border: 1.5px solid #e1d8f5;
  border-radius: 13px;
  background: #f7f4ff;
}

.ai-gen-box input {
  flex: 1;
  min-width: 0;
  border: 0;
  background: transparent;
  padding: 4px 8px;
  font-size: 13px;
  color: #2c2742;
  outline: none;
}

.ai-gen-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 32px;
  padding: 0 12px;
  border: 1.5px solid #8067d1;
  border-bottom: 3px solid #6951b8;
  border-radius: 10px;
  background: #8b73dd;
  color: #ffffff;
  font-size: 12px;
  font-weight: 700;
  flex: 0 0 auto;
}

.ai-gen-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-row-3 {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.topic-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.form-row-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-field span {
  font-size: 12px;
  font-weight: 600;
  color: #554f6c;
}

.form-field input,
.form-field textarea,
.form-field select {
  padding: 8px 11px;
  border: 1.5px solid #e4dff0;
  border-radius: 10px;
  background: #faf9fe;
  font-size: 13px;
  color: #2c2742;
  font-family: inherit;
}

.form-error {
  margin: 0;
  font-size: 12px;
  color: #b84a39;
}

.topic-btn {
  border-color: #8067d1;
  border-bottom-color: #6951b8;
  background: #8b73dd;
  color: #ffffff;
}

/* ===== 辩论场 ===== */
.arena-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 13px 16px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--surface);
}

.arena-head-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.back-btn,
.ghost-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 32px;
  padding: 0 11px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--surface);
  color: var(--ink-soft);
  font-size: 12.5px;
  flex: 0 0 auto;
}

.ghost-btn.active {
  border-color: #cfd2f7;
  background: var(--brand-soft);
  color: var(--brand);
}

.arena-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.arena-title-row h2 {
  margin: 0;
  font-size: 15.5px;
  font-weight: 600;
  color: var(--ink);
}

.my-side-pill {
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
}

.my-side-pill.pro { background: #e8f6ef; color: #257a50; }
.my-side-pill.con { background: #fcefeb; color: #b54c3c; }

.arena-motion {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--muted);
}

.arena-head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}

.primary-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 33px;
  padding: 0 14px;
  border: 1.5px solid #8067d1;
  border-bottom: 3px solid #6951b8;
  border-radius: 10px;
  background: #8b73dd;
  color: #ffffff;
  font-size: 12.5px;
  font-weight: 700;
}

.arena-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 288px;
  gap: 14px;
}

.chat-panel {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--surface);
  overflow: hidden;
}

.panel-top {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  gap: 9px;
  padding: 11px 16px;
  border-bottom: 1.5px solid #ebe7f5;
  background: #faf9fe;
}

.battle-hud {
  display: flex;
  align-items: center;
  gap: 10px;
}

.hud-side {
  display: inline-flex;
  align-items: baseline;
  gap: 5px;
  flex: 0 0 auto;
  font-size: 12px;
}

.hud-side.mine strong {
  color: #6951b8;
  font-size: 14px;
  font-weight: 800;
}

.hud-side.opp strong {
  color: #b84a39;
  font-size: 14px;
  font-weight: 800;
}

.hud-label {
  color: #6f6a84;
  font-weight: 600;
}

.tug-bar {
  position: relative;
  flex: 1;
  min-width: 90px;
  height: 11px;
  border-radius: 999px;
  background: #fde6df;
  border: 1px solid #f2cec4;
  overflow: hidden;
}

.tug-fill {
  position: relative;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #9881e6 0%, #7459cf 100%);
  transition: width 0.35s ease;
}

.tug-spark {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: #ffffff;
  opacity: 0.85;
}

.combo-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 9px;
  border-radius: 999px;
  border: 1px solid #e6e0f5;
  background: #f5f2fd;
  color: #6951b8;
  font-size: 11.5px;
  font-weight: 700;
  flex: 0 0 auto;
}

.combo-pill.hot {
  border-color: #f3c89b;
  background: #fff4e8;
  color: #c25e18;
}

.round-pill {
  padding: 3px 9px;
  border-radius: 999px;
  background: var(--brand-soft);
  color: var(--brand);
  font-size: 11.5px;
  font-weight: 700;
  flex: 0 0 auto;
}

.stage-bar {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
}

.stage-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 9px;
  border-radius: 9px;
  background: var(--surface);
  border: 1.5px solid #ebe7f5;
  font-size: 12px;
  color: var(--muted);
}

.stage-pill.active {
  border-color: #c9cbf4;
  background: var(--brand-soft);
  color: #6046b4;
  font-weight: 700;
}

.stage-pill.done {
  border-color: #cbe7d7;
  background: #f3fbf6;
  color: #2a875a;
}

.step-num {
  display: grid;
  place-items: center;
  width: 17px;
  height: 17px;
  border-radius: 50%;
  background: #f0f1f7;
  font-size: 10.5px;
  font-weight: 700;
}

.stage-pill.active .step-num { background: #8b73dd; color: #ffffff; }
.stage-pill.done .step-num { background: #35a876; color: #ffffff; }

.debate-feed {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
  padding: 18px 20px;
  background: #fbfafd;
}

.msg-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  max-width: 86%;
}

.msg-row.is-user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.msg-avatar {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  margin-top: 18px;
  border-radius: 50%;
  background: #eee9ff;
  color: #654ab8;
  font-size: 13.5px;
  font-weight: 700;
}

.msg-avatar.opponent { background: #fdeee9; color: #b84a39; }
.msg-avatar.interviewer { background: #eaf2ff; color: #365fb3; }
.msg-avatar.judge { background: #e8f6ee; color: #248256; }

.msg-col {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.msg-row.is-user .msg-col {
  align-items: flex-end;
}

.msg-meta {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: #7f7b93;
}

.role-tag {
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  background: #eee9ff;
  color: #6046b4;
}

.role-tag.opponent { background: #fde6df; color: #b84a39; }
.role-tag.interviewer { background: #e4eeff; color: #365fb3; }
.role-tag.judge { background: #dcf3e6; color: #248256; }
.role-tag.user { background: #8b73dd; color: #ffffff; }

.msg-speaker { font-weight: 700; color: #3c3752; }
.msg-stage { color: #9a96ad; }

.audio-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.msg-row.is-user .audio-row {
  flex-direction: row-reverse;
}

.voice-capsule {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 148px;
  height: 36px;
  padding: 0 14px;
  border: 1.5px solid #dfd7f5;
  border-bottom: 3px solid #cbbfea;
  border-radius: 12px;
  background: #ffffff;
  color: #5b43ad;
  font-size: 13px;
  font-weight: 700;
  overflow: hidden;
  transition: transform 0.12s, background 0.14s, border-color 0.14s;
}

.voice-capsule > * {
  position: relative;
  z-index: 1;
}

.voice-capsule.user {
  border-color: #8067d1;
  border-bottom-color: #6951b8;
  background: #8b73dd;
  color: #ffffff;
}

.voice-capsule.opponent {
  border-color: #f1cec4;
  border-bottom-color: #dfb0a2;
  color: #b84a39;
}

.voice-capsule.judge {
  border-color: #c8e7d6;
  border-bottom-color: #a9d6be;
  color: #248256;
}

.voice-capsule:active {
  transform: translateY(1px);
}

.capsule-progress {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  z-index: 0;
  background: rgba(139, 115, 221, 0.16);
  transition: width 0.15s linear;
}

.voice-capsule.user .capsule-progress {
  background: rgba(255, 255, 255, 0.22);
}

.transcript-toggle {
  height: 30px;
  padding: 0 10px;
  border: 1px solid #e5e1f2;
  border-radius: 9px;
  background: #ffffff;
  color: #6e6982;
  font-size: 12px;
  font-weight: 600;
}

.transcript-toggle:hover {
  border-color: #cbbfea;
  color: #5b43ad;
}

.msg-bubble {
  padding: 12px 15px;
  border: 1.5px solid #ebe7f5;
  border-radius: 14px;
  background: #ffffff;
}

.msg-bubble.user {
  border-color: #d6cbf7;
  background: #f5f1ff;
}

.msg-bubble.judge {
  border-color: #d3edde;
  background: #f5fbf7;
}

.msg-en {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  color: #26223b;
  line-height: 1.62;
  letter-spacing: 0.01em;
}

.msg-zh {
  margin: 6px 0 0;
  font-size: 12.5px;
  color: #6f6a84;
  line-height: 1.55;
}

.arena-side {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.side-card {
  padding: 14px 15px;
  border: 1.5px solid #ebe7f5;
  border-radius: 15px;
  background: var(--surface);
}

.roundtable-stage {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stage-seats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 7px;
}

.seat-stage-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 4px 7px;
  border: 1.5px solid #ebe7f5;
  border-bottom: 3px solid #dfd8f0;
  border-radius: 12px;
  background: #faf9fe;
  text-align: center;
  transition: border-color 0.16s, background 0.16s, transform 0.14s;
}

.seat-stage-card.speaking {
  border-color: #8b73dd;
  border-bottom-color: #6951b8;
  background: #f5f1ff;
}

.seat-stage-card.opponent.speaking {
  border-color: #df9d8f;
  border-bottom-color: #c87462;
  background: #fdf6f4;
}

.seat-stage-card.interviewer.speaking {
  border-color: #93b7f2;
  border-bottom-color: #4f79cc;
  background: #f3f7ff;
}

.seat-stage-card.judge.speaking {
  border-color: #82cca4;
  border-bottom-color: #4aa777;
  background: #f3fbf7;
}

.seat-portrait-box {
  width: 68px;
  height: 76px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #ece7f6;
  overflow: hidden;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.seat-portrait-box :deep(svg) {
  width: 100%;
  height: 100%;
  display: block;
}

.live-dot {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #7c5fd6;
}

.seat-stage-card.opponent .seat-portrait-box {
  width: 68px;
  height: 76px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #ece7f6;
  overflow: hidden;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.seat-portrait-box :deep(svg) {
  width: 100%;
  height: 100%;
  display: block;
}

.live-dot { background: #c85845; }
.seat-stage-card.judge .seat-portrait-box {
  width: 68px;
  height: 76px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #ece7f6;
  overflow: hidden;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.seat-portrait-box :deep(svg) {
  width: 100%;
  height: 100%;
  display: block;
}

.live-dot { background: #298a5b; }

.seat-name {
  font-size: 11.5px;
  font-weight: 700;
  color: #2f2a46;
  line-height: 1.2;
}

.seat-role {
  font-size: 10px;
  color: #7c7792;
  white-space: nowrap;
}

.auto-play-check {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  color: #6d6882;
  cursor: pointer;
}

.auto-play-check input {
  accent-color: #8b73dd;
}

.side-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.side-card-head h4 {
  margin: 0;
  font-size: 13.5px;
  font-weight: 700;
  color: var(--ink);
}

.momentum-tag {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 700;
}

.momentum-tag.up {
  background: #eee9ff;
  color: #6046b4;
}

.momentum-tag.down {
  background: #fdeee9;
  color: #b84a39;
}

.radar-wrap {
  display: grid;
  place-items: center;
  padding: 4px 0;
}

.radar-svg {
  width: 100%;
  max-width: 248px;
  height: auto;
}

.radar-grid {
  fill: none;
  stroke: #e8e3f5;
  stroke-width: 1.1;
}

.radar-axis {
  stroke: #e2dcf2;
  stroke-width: 1;
  stroke-dasharray: 2 2;
}

.radar-area {
  fill: rgba(139, 115, 221, 0.24);
  stroke: #7a5fd6;
  stroke-width: 2;
}

.radar-dot {
  fill: #6951b8;
  stroke: #ffffff;
  stroke-width: 1.5;
}

.radar-label {
  fill: #5c5772;
  font-size: 10.5px;
  font-weight: 700;
}

.mini-kpi-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 6px;
}

.kpi-chip {
  padding: 4px 9px;
  border-radius: 8px;
  background: #f6f4fc;
  color: #5b5670;
  font-size: 11.5px;
  font-weight: 600;
}

.kpi-chip.xp {
  background: #e8f6ef;
  color: #257a50;
  font-weight: 700;
}

/* 弹窗（统一遮罩变量） */
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: grid;
  place-items: center;
  padding: 20px;
  background: var(--scrim-bg, rgba(34, 37, 59, .28));
  -webkit-backdrop-filter: var(--scrim-blur, blur(2px));
  backdrop-filter: var(--scrim-blur, blur(2px));
}

.setup-modal,
.verdict-modal {
  width: min(520px, 100%);
  padding: 22px 24px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--surface);
  box-shadow: 0 20px 56px rgba(34, 37, 59, .18);
}

.setup-head h3,
.verdict-head h3 {
  margin: 8px 0 4px;
  font-size: 16.5px;
  font-weight: 600;
  color: var(--ink);
}

.setup-head p,
.verdict-head p {
  margin: 0;
  font-size: 12.5px;
  color: var(--muted);
}

.setup-section { margin-top: 16px; }
.setup-section label { display: block; margin-bottom: 8px; font-size: 12.5px; font-weight: 600; color: var(--ink); }

.side-picker {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.side-option {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 11px 12px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--surface);
  text-align: left;
}

.side-option strong { font-size: 13px; color: var(--ink); }
.side-option span { font-size: 11.5px; color: var(--muted); line-height: 1.45; }
.side-option.pro.selected { border-color: #35a876; background: #f3fbf7; }
.side-option.con.selected { border-color: #d96b57; background: #fff7f5; }

.style-pills { display: flex; gap: 8px; }

.style-pill {
  padding: 6px 13px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface);
  font-size: 12.5px;
  color: var(--ink-soft);
}

.style-pill.selected {
  border-color: var(--brand);
  background: var(--brand-soft);
  color: var(--brand);
  font-weight: 600;
}

.verdict-scores {
  display: grid;
  grid-template-columns: 106px minmax(0, 1fr);
  gap: 14px;
  margin-top: 16px;
  padding: 14px;
  border-radius: 12px;
  background: #f7f8fc;
}

.v-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface);
  padding: 10px;
}

.v-score strong { font-size: 26px; color: var(--brand); }
.v-score span { font-size: 11px; color: var(--muted); }
.v-summary strong { font-size: 13px; color: var(--ink); }
.v-summary p { margin: 5px 0 0; font-size: 12.5px; color: var(--ink-soft); line-height: 1.55; }

.setup-actions {
  margin-top: 18px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.btn-cancel {
  height: 35px;
  padding: 0 15px;
  border: 1.5px solid #e6e1f2;
  border-bottom: 3px solid #ddd6ec;
  border-radius: 10px;
  background: #ffffff;
  color: #5a5572;
  font-size: 13px;
  font-weight: 600;
}

.btn-start {
  height: 35px;
  padding: 0 17px;
  border: 1.5px solid #8067d1;
  border-bottom: 3px solid #6951b8;
  border-radius: 10px;
  background: #8b73dd;
  color: #ffffff;
  font-size: 13px;
  font-weight: 700;
}

.hub-state-banner {
  padding: 12px 16px;
  border-radius: 12px;
  background: #f5f3fb;
  border: 1px solid #e4def4;
  color: #5b517c;
  font-size: 13px;
  font-weight: 600;
}

.debate-empty-card {
  grid-column: 1 / -1;
  display: grid;
  justify-items: center;
  padding: 46px 20px;
  border: 2px dashed #d9d0ef;
  border-radius: 18px;
  background: #ffffff;
  text-align: center;
}

.debate-empty-icon {
  display: grid;
  width: 54px;
  height: 54px;
  place-items: center;
  border-radius: 18px;
  background: #f0eaff;
  color: #8067d1;
}

.debate-empty-card h3 {
  margin: 14px 0 6px;
  font-size: 16px;
  font-weight: 700;
  color: #2f2a44;
}

.debate-empty-card p {
  margin: 0;
  max-width: 420px;
  color: #77708f;
  font-size: 13.5px;
  line-height: 1.65;
}

.debate-empty-cta {
  margin-top: 16px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 38px;
  padding: 0 16px;
  border: 1.5px solid #7960cc;
  border-bottom: 4px solid #6349b4;
  border-radius: 12px;
  background: #8b73dd;
  color: #ffffff;
  font-size: 13.5px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s ease, transform 0.12s ease;
}

.debate-empty-cta:hover {
  background: #7d64d1;
  transform: translateY(-1px);
}

.hub-state-banner.error,
.setup-error {
  background: #fff5f5;
  border: 1px solid #f7caca;
  color: #c53a3a;
  border-radius: 10px;
  padding: 9px 12px;
  font-size: 12.5px;
  font-weight: 600;
  margin-top: 12px;
}

.doc-check-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.doc-check-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1.5px solid #e6e1f2;
  background: #ffffff;
  color: #5a5572;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
}

.doc-check-pill.checked {
  border-color: #8067d1;
  background: #f3effd;
  color: #5a42b3;
}

.submode-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
}
.submode-badge.debate { background: #f3effd; color: #674bc3; }
.submode-badge.panel { background: #e8f3ff; color: #2d62b5; }
.my-side-pill.panel { background: #e8f3ff; color: #2d62b5; border-color: #cbe0fc; }
.tug-bar.panel { flex: 1; background: #ede9f9; }

.panel-lineup-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 14px;
  border: 1.5px solid #ebe7f5;
  border-radius: 12px;
  background: #faf8ff;
}
.panel-user-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
}
.panel-user-row span { color: var(--muted); }
.panel-user-row strong { color: #5b44b6; font-weight: 700; }
.panel-roles-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.panel-role-pill {
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid #dfd7f3;
  background: #fff;
  color: #4a4362;
  font-size: 12px;
}

.delete-confirm-modal { max-width: 420px; }
.btn-danger {
  min-height: 38px;
  padding: 0 18px;
  border: 1.5px solid #d14852;
  border-bottom: 4px solid #ad2c36;
  border-radius: 12px;
  background: #e1525d;
  color: #fff;
  font-size: 13.5px;
  font-weight: 700;
  cursor: pointer;
}

@media (max-width: 960px) {
  .arena-grid,
  .roundtable-row,
  .stage-bar {
    grid-template-columns: 1fr;
  }
}
</style>

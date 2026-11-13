<template>
  <section class="practice-page">
    <div v-if="phase === 'select' && !resuming" class="page-scroll">
      <div class="pick-toolbar">
        <AppTabs
          v-model="pickCategory"
          :options="pickCategories.map((c) => ({ value: c.key, label: c.label, count: countFor(c.key) }))"
          aria-label="场景分类筛选"
        />
        <div class="toolbar-right">
          <label class="search-box">
            <AppIcon name="search" :size="14" />
            <input v-model="keyword" type="search" placeholder="搜索场景名称或描述" />
            <button v-if="keyword" class="search-clear" type="button" aria-label="清空搜索" @click="keyword = ''">
              <AppIcon name="x" :size="12" />
            </button>
          </label>
          <router-link :to="{ name: 'scenes' }" class="ghost-button"><AppIcon name="compass" :size="14" />探索全部场景</router-link>
        </div>
      </div>
      <p v-if="!session.user" class="login-hint"><AppIcon name="info" :size="14" />开始练习前，请先<router-link :to="{ name: 'login' }">登录</router-link>，保存你的对话进度。</p>
      <p v-if="error" class="page-error" role="alert"><AppIcon name="alert" :size="14" />{{ error }}</p>
      <div v-if="!loadingScenes" class="scene-grid">
        <article
          v-for="(scene, index) in filteredScenes" :key="scene.id"
          class="scene-card"
          :class="{ busy: starting }"
          role="button" tabindex="0"
          :aria-disabled="starting"
          :style="{ animationDelay: `${Math.min(index, 8) * 45}ms` }"
          @click="chooseScene(scene)"
          @keydown.enter.prevent="chooseScene(scene)"
          @keydown.space.prevent="chooseScene(scene)"
        >
          <!-- 封面与场景探索页共用同一组件，色调/图标/标题层级保持一致 -->
          <SceneCover :scene="scene" :category-label="coverLabel(scene.category)" mark-icon="arrow-right" />
          <div class="card-body">
            <div class="card-head">
              <span class="mode-chip"><AppIcon :name="modeIcon(scene.mode)" :size="13" />{{ modeLabel(scene.mode) }}</span>
              <span v-if="scene.difficulty" class="diff-chip" :class="diffClass(scene.difficulty)">{{ diffLabel(scene.difficulty) }}</span>
            </div>
            <p class="scene-desc">{{ scene.description || '在真实情境中练习英语表达。' }}</p>
            <div class="scene-foot">
              <span class="scene-meta">
                <span v-if="scene.objective_count"><AppIcon name="target" :size="12" />{{ scene.objective_count }} 个目标</span>
                <span v-if="scene.stage_count"><AppIcon name="chart-line" :size="12" />{{ scene.stage_count }} 阶段</span>
                <span v-if="scene.knowledge_count"><AppIcon name="book-open" :size="12" />{{ scene.knowledge_count }} 份资料</span>
              </span>
              <span class="scene-go">{{ starting ? '准备中…' : '开始对话' }}<AppIcon name="arrow-right" :size="14" /></span>
            </div>
          </div>
        </article>
        <div v-if="!filteredScenes.length" class="scenes-empty">
          <div class="empty-icon"><AppIcon name="messages" :size="20" /></div>
          <h3>{{ keyword || pickCategory !== 'all' ? '没有匹配的场景' : '暂无可对话场景' }}</h3>
          <p>{{ keyword || pickCategory !== 'all' ? '换个关键词或分类再试试。' : '到场景探索页创建或导入一个场景包，再回到这里开始对话。' }}</p>
        </div>
      </div>
      <div v-else class="scene-grid" aria-busy="true" aria-label="正在加载场景">
        <div v-for="n in 4" :key="n" class="scene-card skeleton">
          <div class="sk-cover"></div>
          <div class="sk-body">
            <div class="sk-line w40"></div>
            <div class="sk-line w80"></div>
            <div class="sk-line w60"></div>
            <div class="sk-line w70"></div>
          </div>
        </div>
      </div>
    </div>

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

    <div v-else class="chat-page">
      <!-- 延续旧版独立场景工具栏，场景操作不再挤占聊天卡头部。 -->
      <header class="session-toolbar">
        <button class="back-button" type="button" :disabled="sending" aria-label="返回场景选择" title="切换场景" @click="backToSelect"><AppIcon name="chevron-left" :size="19" /></button>
        <div class="session-heading">
          <h2>{{ sceneTitle }}</h2>
          <p>{{ categoryLabel(sceneMeta?.package?.meta?.category) }}<span>·</span>{{ finished ? '本次练习已完成' : '场景口语练习' }}<span>·</span>{{ stateInfo.turn_count || 0 }} 轮对话</p>
        </div>
        <button class="ghost-button reference-button" type="button" @click="knowledgeOpen = true"><AppIcon name="book-open" :size="14" />知识点</button>
        <button class="exit-button" type="button" :disabled="sending" @click="finishAndExit"><AppIcon name="log-out" :size="14" />退出练习</button>
      </header>

      <div class="chat-layout">
        <section class="chat-card" aria-label="对话内容">
          <header class="chat-head">
            <span class="role-avatar">{{ roleInitial }}</span>
            <div class="role-info"><b>{{ roleName }}</b><span class="role-status"><i class="status-dot" :class="{ busy: sending }" />{{ conversationStatus }}</span></div>
            <button class="text-toggle" type="button" :aria-pressed="showOriginal" @click="showOriginal = !showOriginal"><AppIcon name="file-text" :size="14" />{{ showOriginal ? '原文已显示' : '原文已隐藏' }}</button>
          </header>

          <!-- 阶段 / 目标 / 场景状态：原在右栏底部，上移到对话卡顶部，开口时视线不用来回跑 -->
          <div class="progress-rail">
            <span v-if="currentStage" class="rail-stage" :title="currentStage.guidance || currentStage.name">
              <AppIcon name="chart-line" :size="12" />
              <small>阶段</small>
              <b>{{ currentStage.name }}</b>
              <em v-if="stageTotal">{{ stageIndex }} / {{ stageTotal }}</em>
            </span>
            <span v-else class="rail-stage is-open">
              <AppIcon name="chart-line" :size="12" /><small>阶段</small><b>开放交流</b>
            </span>
            <div v-if="stateRows.length" class="rail-state">
              <button ref="stateButton" class="rail-state-button" type="button" title="场景状态" :aria-expanded="stateOpen" @click="toggleStatePop">
                <AppIcon name="eye" :size="12" />状态<AppIcon name="chevron-down" :size="12" :class="{ flip: stateOpen }" />
              </button>
            </div>
          </div>

          <div ref="chatBody" class="chat-body" role="log" aria-label="聊天记录" :aria-busy="sending">
            <div class="conversation-start"><span></span><small>练习开始 · 放轻松，试着用英语表达</small><span></span></div>
            <article v-for="msg in messages" :key="msg.key" class="msg-row" :class="msg.role">
              <span v-if="msg.role === 'agent'" class="msg-avatar">{{ roleInitial }}</span>
              <div class="message-content">
                <span class="message-author">{{ msg.role === 'agent' ? activeRole?.display_name || '交流伙伴' : '你' }}</span>
                <div v-if="msg.role === 'user'" class="bubble"><p class="bubble-text">{{ msg.text }}</p></div>
                <!-- agent 消息：参照 1.0 的语音胶囊展现——深灰胶囊常驻，原文面板平滑展开，胶囊不消失 -->
                <template v-else>
                  <div class="bubble-row">
                    <button class="ai-voice-capsule" :class="{ playing: playingKey === msg.key }" :style="{ width: capsuleWidth(msg) }" type="button" :disabled="ttsBusyKey === msg.key" :aria-label="playingKey === msg.key ? '停止播放回复' : '播放回复语音'" @click="playingKey === msg.key ? stopAudio() : playMessage(msg)">
                      <i v-if="playingKey === msg.key" class="capsule-progress" :style="{ width: `${Math.min(100, playbackTime / (playbackDuration || estimateSeconds(msg.text)) * 100)}%` }" aria-hidden="true"></i>
                      <AppIcon v-if="ttsBusyKey === msg.key" name="loader" :size="16" class="spin" />
                      <svg v-else class="voice-wave-icon" width="16" height="18" viewBox="0 0 16 18" fill="none" aria-hidden="true"><circle cx="3" cy="9" r="1.35" fill="currentColor"/><path d="M6 5.8a4.5 4.5 0 0 1 0 6.4M8.5 3.3a8 8 0 0 1 0 11.4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
                      <span class="capsule-duration">{{ ttsBusyKey === msg.key ? '准备中' : msg.duration ? `${Math.ceil(msg.duration)}\"` : `${estimateSeconds(msg.text)}\"` }}</span>
                    </button>
                    <button v-if="!showOriginal" class="original-toggle" type="button" :aria-expanded="expandedMessages.has(msg.key)" @click="toggleOriginal(msg.key)"><AppIcon name="file-text" :size="13" />{{ expandedMessages.has(msg.key) ? '收起' : '原文' }}</button>
                  </div>
                  <transition name="panel">
                    <div v-show="showOriginal || expandedMessages.has(msg.key)" class="original-panel"><p class="bubble-text">{{ msg.text }}</p></div>
                  </transition>
                </template>
              </div>
              <span v-if="msg.role === 'user'" class="msg-avatar user">{{ userInitial }}</span>
            </article>
            <div v-if="sending" class="thinking-message" role="status"><span class="msg-avatar">{{ roleInitial }}</span><span class="thinking-dots"><i></i><i></i><i></i></span><small>正在组织回复…</small></div>
            <div v-if="finished" class="finish-banner"><AppIcon name="check" :size="16" />{{ finishText }}</div>
          </div>

          <footer class="composer-area">
            <p v-if="playbackNotice" class="playback-notice" role="status"><AppIcon name="volume" :size="13" />{{ playbackNotice }}</p>
            <p v-if="error" class="chat-error" role="alert"><AppIcon name="alert" :size="14" />{{ error }}</p>

            <!-- 语音优先：单行紧凑条，待机 / 录音中 / 转写确认三态共用 .composer 外壳 -->
            <template v-if="inputMode === 'voice'">
              <!-- 转写结果：确认后再发送 -->
              <div v-if="transcribedText" class="composer voice-result" role="status">
                <p class="voice-result-text">{{ transcribedText }}</p>
                <div class="voice-result-actions">
                  <button class="icon-button" type="button" title="重新录制" :disabled="voiceBusy" @click="retryRecording"><AppIcon name="rotate" :size="15" /></button>
                  <button class="send-button" type="button" :disabled="sending || finished" @click="sendTranscribed"><AppIcon :name="sending ? 'loader' : 'send'" :size="14" />{{ sending ? '发送中' : '发送' }}</button>
                </div>
              </div>
              <!-- 录音中 / 识别中 -->
              <div v-else-if="voiceBusy" class="composer voice-bar live" role="status" aria-live="polite">
                <button v-if="voiceStatus === 'recording'" class="mic-orb stop" type="button" title="结束并转写" @click="stopRecording"><AppIcon name="square" :size="15" /><i class="orb-pulse" aria-hidden="true"></i></button>
                <span v-else class="mic-orb static"><AppIcon name="loader" :size="16" /></span>
                <div class="voice-bar-info">
                  <b>{{ voiceStatusLabel }}<template v-if="voiceStatus === 'recording'"> · {{ String(recordingSeconds).padStart(2, '0') }} / 60 秒</template></b>
                  <span v-if="voiceStatus === 'recording'" class="live-hint">说英语，点左侧按钮结束<span class="live-wave" aria-hidden="true"><i v-for="n in 7" :key="n" :style="{ height: levelBar(n - 1) }"></i></span></span>
                  <span v-else>{{ voiceStatus === 'transcribing' ? '正在识别，请稍候…' : '正在整理录音…' }}</span>
                </div>
                <button class="icon-button" type="button" :disabled="voiceStatus === 'transcribing'" title="取消录音" @click="cancelRecording"><AppIcon name="x" :size="15" /></button>
              </div>
              <!-- 待机：录音区合并为单一整块触发按钮，右侧独立放置文字模式切换 -->
              <div v-else class="composer voice-bar idle">
                <button
                  class="voice-trigger"
                  type="button"
                  :disabled="sending || finished || asrAvailable === false || !recordingSupported"
                  :title="voiceCtaText"
                  aria-label="开始语音输入"
                  @click="startRecording"
                >
                  <span class="mic-orb" aria-hidden="true"><AppIcon name="mic" :size="17" /><i class="orb-ring"></i></span>
                  <span class="voice-bar-info">
                    <b>{{ voiceCtaText }}</b>
                    <span>{{ voiceHintText }}</span>
                  </span>
                </button>
                <button class="foot-toggle in-bar" type="button" :disabled="voiceBusy" @click="toggleInputMode"><AppIcon name="pencil" :size="13" />文字输入</button>
              </div>
              <div v-if="voiceBusy || transcribedText" class="composer-foot">
                <span>{{ voiceHintText }}</span>
                <button class="foot-toggle" type="button" :disabled="voiceBusy" @click="toggleInputMode"><AppIcon name="pencil" :size="12" />改用文字输入</button>
              </div>
            </template>

            <!-- 文字模式：右侧加麦克风图标，随时切回语音 -->
            <template v-else>
              <div class="composer">
                <textarea ref="composerBox" v-model="draft" class="composer-input" rows="2" maxlength="4000" :disabled="sending || finished" :placeholder="finished ? '本次练习已结束' : '用英语写下你的回答…'" aria-label="你的英语回答" @keydown.enter.exact="handleComposerEnter" @input="autoGrow"></textarea>
                <button class="icon-button" type="button" title="改用语音输入" :disabled="voiceBusy" @click="toggleInputMode"><AppIcon name="mic" :size="15" /></button>
                <button class="send-button" type="button" :disabled="sending || finished || !draft.trim()" @click="sendTurn"><AppIcon :name="sending ? 'loader' : 'arrow-right'" :size="18" /><span>发送</span></button>
              </div>
              <div class="composer-foot"><span class="keyboard-hint"><kbd>Enter</kbd> 发送<span>·</span><kbd>Shift + Enter</kbd> 换行</span></div>
            </template>
          </footer>
        </section>

        <aside class="chat-side" aria-label="练习辅助">
          <section class="companion-card">
            <div class="side-head"><h3>交流伙伴</h3></div>
            <div class="companion-stage">
              <AvatarStage :avatar="companionAvatar" :state="voiceBusy ? (voiceStatus === 'recording' ? 'listening' : 'thinking') : avatarState" :size="238" :show-backdrop="false" />
            </div>
            <div class="companion-identity"><b>{{ activeRole?.display_name || '交流伙伴' }}</b><span>{{ activeRole?.title || '英语练习伙伴' }}</span></div>
            <div class="companion-meta">
              <label class="autoplay-control"><input v-model="autoPlayReplies" type="checkbox" @change="saveAutoPlayPreference" />自动播放</label>
              <span class="voice-summary" :title="selectedVoiceLabel"><AppIcon name="volume" :size="12" />{{ selectedVoiceLabel }}</span>
            </div>
            <div class="companion-rate">
              <span class="rate-label">语速</span>
              <input
                v-model.number="speechRate"
                type="range"
                min="0.75"
                max="1.25"
                step="0.05"
                class="rate-slider"
                aria-label="语速调节"
                @change="saveSpeechRatePreference"
              />
              <span class="rate-value">{{ speechRate.toFixed(2) }}×</span>
            </div>
          </section>

          <!-- 目标清单：阶段与进度已上移到对话卡顶部，这里只留可勾选的细项 -->
          <section class="support-card">
            <div class="support-head">
              <h3>训练目标</h3>
              <span>{{ completedGoals }} / {{ stateInfo.goals?.length || 0 }}</span>
            </div>
            <progress class="goal-progress" :value="completedGoals" :max="stateInfo.goals?.length || 1" aria-label="训练目标完成进度"></progress>
            <ul v-if="stateInfo.goals?.length" class="goal-list">
              <li v-for="(goal, index) in stateInfo.goals" :key="goal.id" :class="{ done: goal.done }">
                <span class="goal-number"><AppIcon v-if="goal.done" name="check" :size="12" /><template v-else>{{ index + 1 }}</template></span>
                <span>{{ goal.label }}<small v-if="!goalHasCheck(goal.id)">尚未接入自动判定</small></span>
              </li>
            </ul>
            <p v-else class="support-empty">这个场景采用开放交流，按自己的节奏继续。</p>
            <p class="support-foot"><AppIcon name="headphones" :size="13" />练习反馈尚未接入</p>
          </section>
        </aside>
      </div>
    </div>

    <!-- 进入对话确认弹窗：确认后才创建会话 -->
    <div v-if="confirmScene" class="modal-backdrop" @click.self="confirmScene = null">
      <div class="modal-card" role="alertdialog" aria-modal="true" :aria-label="`开始场景 ${confirmScene.name}`">
        <div class="modal-icon"><AppIcon name="messages" :size="18" /></div>
        <h3>「{{ confirmScene.name }}」</h3>
        <p v-if="checkingHistory">正在查找练习记录…</p>
        <p v-else-if="historyError" class="history-error" role="alert">{{ historyError }}</p>
        <p v-else-if="latestHistory">{{ latestHistory.state?.status === 'finished' ? '你有一条已结束的练习记录，可以查看记录或开始新练习。' : '你有一条未结束的练习记录，要继续上次练习还是新开一场？' }}</p>
        <p v-else>将创建一条新的练习会话，与场景角色从开场白开始对话。</p>
        <ul v-if="!latestHistory && !checkingHistory && !historyError" class="modal-facts">
          <li v-if="confirmScene.objective_count"><span>训练目标</span><b>{{ confirmScene.objective_count }} 个</b></li>
          <li v-if="confirmScene.stage_count"><span>对话阶段</span><b>{{ confirmScene.stage_count }} 个</b></li>
          <li v-if="confirmScene.difficulty"><span>难度</span><b>{{ diffLabel(confirmScene.difficulty) }}</b></li>
        </ul>
        <div class="modal-actions">
          <button class="ghost-button" type="button" :disabled="starting" @click="confirmScene = null">取消</button>
          <button v-if="historyError" class="ghost-button" type="button" :disabled="checkingHistory" @click="chooseScene(confirmScene)">重试</button>
          <button v-if="latestHistory" class="ghost-button" type="button" :disabled="starting || checkingHistory" @click="startScene(confirmScene, latestHistory.id)">{{ latestHistory.state?.status === 'finished' ? '查看记录' : '继续练习' }}</button>
          <button class="confirm-button" type="button" :disabled="starting || checkingHistory || !!historyError" @click="confirmStart">
            <AppIcon :name="starting ? 'loader' : 'arrow-right'" :size="14" />{{ starting ? '准备中…' : latestHistory ? '新开练习' : '确认开始' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 场景状态浮层：挂在 body 上，避免被对话卡圆角裁切 -->
    <Teleport to="body">
      <template v-if="stateOpen">
        <div class="rail-pop-backdrop" @click="stateOpen = false"></div>
        <div class="rail-pop" role="dialog" aria-label="场景状态" :style="{ top: `${statePop.top}px`, right: `${statePop.right}px` }">
          <p>根据对话更新，仅供练习参考。</p>
          <ul><li v-for="row in stateRows" :key="row.key"><span>{{ row.key }}</span><b>{{ row.value }}</b></li></ul>
        </div>
      </template>
    </Teleport>

    <!-- 场景知识点弹窗：分资料模块 Tab + Markdown 正文（对齐 1.0 的独立知识面板） -->
    <PracticeKnowledge v-if="knowledgeOpen" :scene-id="sessionInfo.scene_id" :description="sceneMeta?.package?.meta?.description || ''" :goals="stateInfo.goals || []" @close="knowledgeOpen = false" />
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import AppTabs from '../components/AppTabs.vue'
import AvatarStage from '../components/avatar/AvatarStage.vue'
import PracticeKnowledge from '../components/practice/PracticeKnowledge.vue'
import SceneCover from '../components/scene/SceneCover.vue'
import { getScene, listScenes } from '../api/scenes'
import { createSession, getSession, getLatestSession, getGreetingAudio, getTurnAudio, submitTurn } from '../api/sessions'
import { loadingVisible, usePageLoading } from '../app/loading'
import { getSpeechStatus } from '../api/speech'
import { useVoiceInput } from '../composables/useVoiceInput'
import { FALLBACK_AVATARS, FALLBACK_VOICES, getAvatarPreference, listAvatars, saveAvatarPreference, VOICE_STYLE_ALIASES } from '../api/avatar'
import { resolveRoleVoiceStyle } from '../components/avatar/avatarAppearance'
import { session } from '../auth/session'

const CATEGORY_LABELS = { daily: '日常', interview: '面试', career: '职业', academic: '学术', custom: '自定义', travel: '旅行', business: '商务', campus: '校园', debate: '辩论' }
const route = useRoute()
const router = useRouter()
const FINISH_REASONS = { condition_met: '场景任务已完成，本次练习结束。', max_turns: '已达到本场景的轮次上限，练习结束。' }

const phase = ref('select') // select=选场景 / chat=对话中
const resuming = ref(Boolean(route.query.session)) // 从历史记录进入会话时，恢复完成前保持加载态
// 页面级加载：场景列表（及历史会话恢复）到位后才收起全局遮罩；恢复入口已知会慢，立即盖住
const finishLoading = usePageLoading(route.query.session ? '正在打开这次练习' : '', Boolean(route.query.session))
const scenes = ref([])
const loadingScenes = ref(false)
const starting = ref(false)
const error = ref('')
const pickCategory = ref('all') // 选场景页分类筛选
const keyword = ref('') // 选场景页搜索关键词
const confirmScene = ref(null) // 进入对话前的确认弹窗（点确认才创建会话）
const latestHistory = ref(null)
const checkingHistory = ref(false)
const historyError = ref('')
let historyGeneration = 0

const sessionInfo = ref(null) // 后端会话公开字段 { id, scene_id, greeting, state, version }
const sceneMeta = ref(null) // 场景详情（阶段名/角色/描述）
const messages = ref([]) // { key, role: 'user'|'agent', text }
const draft = ref('')
const sending = ref(false)
const chatBody = ref(null)
const composerBox = ref(null)
const asrAvailable = ref(null)
const inputMode = ref('voice') // 语音优先：voice=麦克风主输入 / text=文字备选
const transcribedText = ref('') // 语音转写结果：待用户确认后发送
const {
  status: voiceStatus, seconds: recordingSeconds, level: recordingLevel,
  busy: voiceBusy, supported: recordingSupported,
  start: beginRecording, stop: stopRecording, cancel: cancelRecording,
} = useVoiceInput({
  onResult(text) {
    // 转写结果先展示在语音模式里，用户点「发送」才真正进入对话。
    transcribedText.value = [draft.value.trim(), text].filter(Boolean).join(' ')
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
let msgSeq = 0

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
const currentStage = computed(() => sceneMeta.value?.package?.stages?.find(stage => stage.id === stateInfo.value.stage))
// 阶段进度：用于顶部信息条显示「2 / 4」
const stageTotal = computed(() => sceneMeta.value?.package?.stages?.length || 0)
const stageIndex = computed(() => {
  const i = (sceneMeta.value?.package?.stages || []).findIndex(stage => stage.id === stateInfo.value.stage)
  return i >= 0 ? i + 1 : 0
})
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
  return '最长 60 秒，转写后确认发送'
})
// 录音中迷你声波：7 根柱子按基准波形 × 实时音量缩放
const LEVEL_BARS = [0.35, 0.6, 0.9, 1, 0.75, 0.5, 0.65]
function levelBar(i) {
  const scaled = LEVEL_BARS[i % LEVEL_BARS.length] * (0.35 + recordingLevel.value * 1.3)
  return `${Math.max(3, Math.min(15, Math.round(scaled * 15)))}px`
}
// 场景状态变量是场景包里的机器键名（update_scene_state 按此写入），只展示已登记中文名的键；未登记的键不直接暴露英文
const STATE_LABELS = { issue_explained: '问题说明', rebooked: '新行程', options_compared: '方案比较', reported: '进度汇报', clarified: '问题澄清', next_step: '下一步', confirmed: '订单确认', paid: '付款', order: '点单内容', greeted: '打招呼', price_asked: '问价', booked: '预订' }
// 场景状态卡：仅展示原始值字段，对象/数组不强行渲染
const stateRows = computed(() =>
  Object.entries(stateInfo.value.scenario_state || {})
    .filter(([key, value]) => STATE_LABELS[key] && ['string', 'number', 'boolean'].includes(typeof value))
    .map(([key, value]) => ({ key: STATE_LABELS[key], value: typeof value === 'boolean' ? (value ? '已确认' : '待确认') : String(value) }))
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
// 卡片封面沿用场景探索页的长文案，筛选 Tab 与对话页副标题仍用短文案
const COVER_LABELS = { daily: '日常沟通', business: '职场沟通', career: '求职训练', academic: '学术场景', custom: '自定义' }
const coverLabel = (key) => COVER_LABELS[key] || categoryLabel(key)
const diffLabel = (key) => ({ entry: '入门', easy: '简单', normal: '普通', hard: '困难', expert: '专家' }[key] || key)
const diffClass = (key) => ({ entry: 'entry', easy: 'easy', normal: 'normal', hard: 'hard', expert: 'expert' }[key] || 'normal')

// 场景模式 → 图标与中文标签（对齐场景探索页的卡片徽标）
const MODE_META = { conversation: { icon: 'messages', label: '对话' }, interview: { icon: 'briefcase', label: '面试' }, debate: { icon: 'messages', label: '辩论' } }
const modeIcon = (mode) => MODE_META[mode]?.icon || 'messages'
const modeLabel = (mode) => MODE_META[mode]?.label || mode

// 选场景页：分类 Tab 按实际数据生成（全部 + 出现过的分类），带计数
const pickCategories = computed(() => {
  const seen = new Map()
  for (const scene of scenes.value) seen.set(scene.category, (seen.get(scene.category) || 0) + 1)
  return [{ key: 'all', label: '全部', count: scenes.value.length },
    ...[...seen.keys()].map((key) => ({ key, label: categoryLabel(key), count: seen.get(key) }))]
})
const countFor = (key) => pickCategories.value.find((cat) => cat.key === key)?.count || 0
// 分类 + 关键词过滤（名称、描述、标签）
const filteredScenes = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return scenes.value.filter((scene) => {
    if (pickCategory.value !== 'all' && scene.category !== pickCategory.value) return false
    if (!text) return true
    return [scene.name, scene.description, ...(scene.tags || [])].some((field) => String(field || '').toLowerCase().includes(text))
  })
})

function toggleOriginal(key) {
  // 按消息展开原文，沿用旧版语音消息与文本分开展示的交互。
  if (expandedMessages.value.has(key)) expandedMessages.value.delete(key)
  else expandedMessages.value.add(key)
}

function handleComposerEnter(event) {
  // 输入法选词时的 Enter 不应发送尚未确认的文字。
  if (event.isComposing || event.keyCode === 229) return
  event.preventDefault()
  sendTurn()
}

function pushMessage(role, text) {
  const msg = { key: `m${++msgSeq}`, role, text }
  messages.value.push(msg)
  scrollToBottom()
  return messages.value[messages.value.length - 1]
}

async function scrollToBottom() {
  await nextTick()
  if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight
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
  // 历史记录入口：会话详情与场景列表并行拉取，过渡态不必串行等两次往返
  const resumeId = route.query.session
  const pendingSession = resumeId ? getSession(resumeId) : null
  if (pendingSession) pendingSession.catch(() => {}) // 场景列表失败时避免留下未处理的拒绝
  loadingScenes.value = true
  try {
    const { data } = await listScenes()
    scenes.value = data?.items || []
    const selected = scenes.value.find(scene => scene.id === route.query.scene)
    if (selected) void chooseScene(selected)
    else if (resumeId) await resumeSession(resumeId, pendingSession) // 从历史记录进入某次会话：等恢复完成再收遮罩
  } catch (err) {
    error.value = err.message
  } finally {
    loadingScenes.value = false
    finishLoading() // 场景列表（或恢复的会话）就绪，交还遮罩
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
    const scene = scenes.value.find(item => item.id === data.scene_id)
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
    if (generation === historyGeneration && confirmScene.value?.id === scene.id) latestHistory.value = data.session
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
  try {
    // 知识点面板按需独立加载，不因资料服务失败阻塞进入对话。
    const [detailRes, sessionRes, preference] = await Promise.all([
      getScene(scene.id),
      existingId ? getSession(existingId) : createSession(scene.id),
      getAvatarPreference(scene.id),
    ])
    if (generation !== sessionGeneration) return
    sceneMeta.value = { ...detailRes.data, package: sessionRes.data.scene_display || detailRes.data.package }
    applyVoicePreference(preference, activeRole.value?.voice)
    sessionInfo.value = sessionRes.data
    messages.value = []
    const greetingMessage = sessionRes.data.greeting ? pushMessage('agent', sessionRes.data.greeting) : null
    if (greetingMessage) greetingMessage.greetingSessionId = sessionRes.data.id
    for (const turn of sessionRes.data.turns || []) {
      pushMessage('user', turn.input_text)
      const reply = pushMessage('agent', turn.text)
      reply.turnId = turn.turn_id
      reply.sessionId = sessionRes.data.id
    }
    phase.value = 'chat'
    avatarState.value = 'idle'
    confirmScene.value = null // 进入成功后收起确认弹窗
    await nextTick()
    if (generation !== sessionGeneration) return
    composerBox.value?.focus()
    if (!existingId && greetingMessage && autoPlayReplies.value) void playMessage(greetingMessage, { automatic: true })
  } catch (err) {
    historyError.value = err.message
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
  playbackNotice.value = ''
  cancelRecording()
  transcribedText.value = ''
  stopAudio()
  clearAudioCache()
  phase.value = 'select'
  sessionInfo.value = null
  sceneMeta.value = null
  messages.value = []
  draft.value = ''
  expandedMessages.value.clear()
  stateOpen.value = false
  error.value = ''
  if (route.query.session) { router.replace({ name: 'history' }); return } // 由历史记录进入时退回列表，而非场景选择
}

function finishAndExit() {
  // 复盘报告依赖训练报告模块（未接入），先做客户端确认后返回
  if (window.confirm(route.query.session ? '退出回放并返回历史记录？' : '退出当前练习并返回场景列表？')) backToSelect()
}

// ---- 对话轮次 ---------------------------------------------------------------

function autoGrow(event) {
  const box = event.target
  box.style.height = 'auto'
  box.style.height = `${Math.min(box.scrollHeight, 132)}px`
}

function startRecording() {
  if (sending.value || finished.value || voiceBusy.value) return
  stopAudio()
  error.value = ''
  transcribedText.value = ''
  avatarState.value = 'listening' // 数字人进入倾听姿态
  beginRecording()
}

function retryRecording() {
  // 转写结果不满意：清掉结果直接重录
  transcribedText.value = ''
  startRecording()
}

function sendTranscribed() {
  // 确认发送语音转写文本
  const text = transcribedText.value.trim()
  if (!text || sending.value || finished.value) return
  draft.value = text
  transcribedText.value = ''
  sendTurn()
}

function toggleInputMode() {
  // 语音/文字互切（录音中禁用切换，避免设备资源泄漏）
  if (voiceBusy.value) return
  transcribedText.value = ''
  inputMode.value = inputMode.value === 'voice' ? 'text' : 'voice'
  if (inputMode.value === 'text') nextTick(() => composerBox.value?.focus())
}

async function sendTurn() {
  const text = draft.value.trim()
  if (!text || sending.value || finished.value || voiceBusy.value) return
  if (text.length > 4000) { error.value = '回答超过 4000 字，请精简后再发送。'; return }
  transcribedText.value = ''
  stopAudio()
  sending.value = true
  const generation = sessionGeneration
  let replyMessage = null
  avatarState.value = 'thinking'
  error.value = ''
  draft.value = ''
  if (composerBox.value) composerBox.value.style.height = 'auto'
  const userMsg = pushMessage('user', text) // 乐观上屏，失败时按 key 撤回
  try {
    const requestId = crypto.randomUUID() // 幂等键：网络重试时后端去重
    const { data } = await submitTurn(sessionInfo.value.id, requestId, text)
    if (generation !== sessionGeneration) return
    replyMessage = pushMessage('agent', data.text)
    replyMessage.turnId = data.turn_id
    replyMessage.sessionId = data.session_id
    sessionInfo.value = { ...sessionInfo.value, state: data.state, version: data.version }
  } catch (err) {
    if (generation !== sessionGeneration) return
    // 提交失败：撤回乐观气泡，把输入还给用户重发
    messages.value = messages.value.filter((m) => m.key !== userMsg.key)
    draft.value = text
    error.value = err.message
  } finally {
    sending.value = false
    avatarState.value = 'idle'
    scrollToBottom()
    if (generation === sessionGeneration && replyMessage && autoPlayReplies.value) void playMessage(replyMessage, { automatic: true })
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
onBeforeUnmount(() => { sessionGeneration += 1; stopAudio(); clearAudioCache() })
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
/* 转写结果确认：绿色浅底，文本限三行，操作右对齐 */
.voice-result { flex-direction: column; align-items: stretch; gap: 8px; border-color: #d9e8de; background: #f4faf6; }
.voice-result-text { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 3; overflow: hidden; margin: 0; color: var(--ink); font-size: 14.5px; line-height: 1.7; white-space: pre-wrap; overflow-wrap: anywhere; }
.voice-result-actions { display: flex; align-items: center; justify-content: flex-end; gap: 6px; }
/* 继承旧版「场景工具栏 + 对话主区 + 辅助栏」，沿用 2.0 的色彩与控件。 */
.practice-page { flex: 1; min-height: 0; min-width: 0; display: flex; flex-direction: column; }
button, a, textarea, select, summary { -webkit-app-region: no-drag; }
button { cursor: pointer; } button:disabled { cursor: not-allowed; }
button:focus-visible, a:focus-visible, summary:focus-visible { outline: 2px solid var(--brand); outline-offset: 3px; }
/* ---- 选场景页：工具行 + 卡片网格（对齐场景探索页） ---- */
.page-scroll { flex: 1; min-height: 0; overflow: auto; padding: 22px 28px 32px; }
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
.pick-toolbar { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
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
.scene-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(275px, 1fr)); gap: 14px; align-content: start; }
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
.modal-backdrop { position: fixed; inset: 0; z-index: 40; display: grid; place-items: center; background: rgba(34, 37, 59, .28); animation: fade-in .18s ease; }
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
.ghost-button:hover { border-color: #c9bdf0; background: #f8f5ff; color: #5b43b0; }
.exit-button { color: #a14959; background: #fff7f8; border-color: #f0dfe3; border-bottom-color: #e5ccd2; }
.exit-button:hover { background: #fdeff1; border-color: #e5c3cb; } button:disabled { opacity: .5; }
/* 页面内只滚动消息与辅助栏，输入始终可见。 */
.chat-page { display: flex; flex-direction: column; flex: 1; min-height: 0; padding: 0 24px 22px; }
.session-toolbar { display: flex; align-items: center; gap: 12px; flex: 0 0 auto; min-height: 72px; padding: 12px 0; }
.back-button { display: grid; place-items: center; width: 36px; height: 36px; flex-shrink: 0; background: white; border: 1.5px solid #e7e1f5; border-bottom: 3px solid #dcd3f0; border-radius: 11px; color: #6e6886; transition: border-color .15s, background .15s, color .15s, transform .12s; }
.back-button:hover { border-color: #c9bdf0; background: #f8f5ff; color: #5b43b0; }
.session-heading { min-width: 0; flex: 1; }.session-heading h2 { margin: 0; color: #2d294b; font-size: 18px; font-weight: 800; line-height: 1.5; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.session-heading p { margin: 3px 0 0; color: #7c7693; font-size: 12.5px; }.session-heading p span { margin: 0 8px; }
.chat-layout { flex: 1; min-height: 0; display: grid; grid-template-columns: minmax(0, 1fr) 264px; gap: 16px; }
.chat-card { display: flex; flex-direction: column; min-width: 0; min-height: 0; background: white; border: 1px solid var(--line); border-radius: 14px; overflow: hidden; }
.chat-head { display: flex; align-items: center; gap: 10px; padding: 14px 20px; border-bottom: 1px solid var(--line); flex-shrink: 0; }
.role-avatar { display: grid; place-items: center; flex: 0 0 36px; width: 36px; height: 36px; border-radius: 12px; background: #eee9ff; color: #694ec0; font-size: 14px; font-weight: 750; }
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
.msg-row { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 25px; }.msg-row.user { justify-content: flex-end; }.msg-avatar { display: grid; place-items: center; width: 30px; height: 30px; flex: 0 0 30px; margin-top: 21px; border-radius: 10px; background: #f0effa; color: #7771ac; font-size: 12.5px; font-weight: 600; }.msg-avatar.user { background: #e9edf7; color: #6c7a9a; }
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
.original-toggle { display: inline-flex; align-items: center; gap: 4px; padding: 5px 10px; border: 1.5px solid #e6e3f2; border-bottom: 3px solid #dad4ec; border-radius: 999px; background: #fff; color: #6b6485; font-size: 12px; font-weight: 650; transition: color .15s, border-color .15s; white-space: nowrap; }
.original-toggle:hover { color: #5b43b0; border-color: #c9bdf0; }
.original-panel { max-width: 100%; margin-top: 7px; padding: 11px 15px; border: 1px solid #ededf3; border-radius: 4px 15px 15px 15px; background: #fff; }
.panel-enter-active, .panel-leave-active { transition: opacity .18s ease, transform .18s ease; }
.panel-enter-from, .panel-leave-to { opacity: 0; transform: translateY(-4px); }
.thinking-message { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; }.thinking-message .msg-avatar { margin-top: 0; }.thinking-message small { color: var(--muted); font-size: 12.5px; }.thinking-dots { display: flex; gap: 4px; padding: 12px; border-radius: 10px; background: var(--bg); }.thinking-dots i { width: 4px; height: 4px; border-radius: 50%; background: var(--brand); }
.finish-banner { display: flex; align-items: center; gap: 8px; padding: 12px; color: #4a7f63; border-radius: 8px; background: #f1f8f3; font-size: 13.5px; }
.composer-area { flex-shrink: 0; margin: 0 20px; padding: 13px 0 12px; border-top: 1px solid var(--line); }
.composer { display: flex; align-items: flex-end; gap: 10px; padding: 10px; border: 1px solid #e6e6f0; border-radius: 11px; background: #fcfcfe; transition: border-color .15s; }.composer:focus-within { border-color: #a9a7e9; }.composer-input { display: block; flex: 1; min-width: 0; min-height: 42px; max-height: 132px; padding: 0 3px; outline: none; border: 0; resize: none; background: transparent; font: inherit; font-size: 14.5px; line-height: 1.7; color: #2d294b; }.composer-input::placeholder { color: #9c96b2; }.send-button { display: flex; align-items: center; justify-content: center; gap: 5px; height: 36px; padding: 0 15px; border: 1.5px solid #7960cc; border-bottom: 4px solid #6349b4; border-radius: 11px; color: white; background: #8b73dd; font-size: 13px; font-weight: 700; transition: background .15s, transform .12s; }.send-button:hover:not(:disabled) { background: #7d64d1; transform: translateY(-1px); }.send-button:active:not(:disabled) { transform: translateY(1px); border-bottom-width: 2px; }
.composer-foot { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 7px; margin-top: 9px; color: #7c7693; font-size: 11.5px; }.recording-note { display: flex; align-items: center; gap: 4px; }.keyboard-hint { display: flex; align-items: center; gap: 5px; }.keyboard-hint>span { margin: 0 3px; }kbd { font-family: inherit; font-size: 10.5px; }.chat-error { display: flex; align-items: center; gap: 5px; margin: 0 0 10px; color: var(--danger); font-size: 13px; }
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
.ai-voice-capsule { border: 1.5px solid #eae6f2; border-bottom: 3px solid #e4dfec; border-radius: 5px 16px 16px 16px; }
.ai-voice-capsule:hover:not(:disabled) { background: #f6f2ff; }
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

</style>

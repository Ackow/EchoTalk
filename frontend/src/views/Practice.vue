<template>
  <section class="practice-page">
    <!-- 进入会话前选场景；工具行 + 卡片网格对齐场景探索页，不做 hero。 -->
    <div v-if="phase === 'select'" class="page-scroll">
      <div class="pick-toolbar">
        <div class="seg-filter" role="tablist" aria-label="场景分类筛选">
          <button
            v-for="cat in pickCategories" :key="cat.key"
            type="button" role="tab"
            class="seg-item"
            :class="{ active: pickCategory === cat.key }"
            :aria-selected="pickCategory === cat.key"
            @click="pickCategory = cat.key"
          >
            {{ cat.label }}<span class="seg-count">{{ countFor(cat.key) }}</span>
          </button>
        </div>
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
        <button
          v-for="(scene, index) in filteredScenes" :key="scene.id"
          class="scene-card" type="button"
          :disabled="starting"
          :style="{ animationDelay: `${Math.min(index, 8) * 45}ms` }"
          @click="confirmScene = scene"
        >
          <span class="card-head">
            <span class="mode-chip"><AppIcon :name="modeIcon(scene.mode)" :size="13" />{{ modeLabel(scene.mode) }}</span>
            <span v-if="scene.difficulty" class="diff-chip" :class="diffClass(scene.difficulty)">{{ diffLabel(scene.difficulty) }}</span>
          </span>
          <b class="scene-name">{{ scene.name }}</b>
          <span class="scene-desc">{{ scene.description || '在真实情境中练习英语表达。' }}</span>
          <span class="scene-foot">
            <span class="scene-meta">
              <span v-if="scene.objective_count"><AppIcon name="target" :size="12" />{{ scene.objective_count }} 个目标</span>
              <span v-if="scene.stage_count"><AppIcon name="chart-line" :size="12" />{{ scene.stage_count }} 阶段</span>
              <span v-if="scene.knowledge_count"><AppIcon name="book-open" :size="12" />{{ scene.knowledge_count }} 份资料</span>
            </span>
            <span class="scene-go">{{ starting ? '准备中…' : '开始对话' }}<AppIcon name="arrow-right" :size="14" /></span>
          </span>
        </button>
        <div v-if="!filteredScenes.length" class="scenes-empty">
          <div class="empty-icon"><AppIcon name="messages" :size="20" /></div>
          <h3>{{ keyword || pickCategory !== 'all' ? '没有匹配的场景' : '暂无可对话场景' }}</h3>
          <p>{{ keyword || pickCategory !== 'all' ? '换个关键词或分类再试试。' : '到场景探索页创建或导入一个场景包，再回到这里开始对话。' }}</p>
        </div>
      </div>
      <div v-else class="scene-grid" aria-busy="true" aria-label="正在加载场景">
        <div v-for="n in 4" :key="n" class="scene-card skeleton">
          <div class="sk-line w40"></div>
          <div class="sk-line w80"></div>
          <div class="sk-line w60"></div>
          <div class="sk-line w70"></div>
        </div>
      </div>
    </div>

    <div v-else class="chat-page">
      <!-- 延续旧版独立场景工具栏，场景操作不再挤占聊天卡头部。 -->
      <header class="session-toolbar">
        <button class="back-button" type="button" :disabled="sending" aria-label="返回场景选择" title="切换场景" @click="backToSelect"><AppIcon name="chevron-left" :size="19" /></button>
        <div class="session-heading"><h2>{{ sceneTitle }}</h2><p>{{ categoryLabel(sceneMeta?.package?.meta?.category) }}<span>·</span>{{ finished ? '本次练习已完成' : '场景口语练习' }}</p></div>
        <span class="session-counter"><AppIcon name="messages" :size="14" />{{ stateInfo.turn_count || 0 }} 轮对话</span>
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
                    <button class="ai-voice-capsule" :class="{ playing: playingKey === msg.key }" :style="{ width: capsuleWidth(msg.text) }" type="button" :disabled="ttsBusyKey === msg.key" :aria-label="playingKey === msg.key ? '停止播放回复' : '播放回复语音'" @click="playingKey === msg.key ? stopAudio() : playMessage(msg)">
                      <i v-if="playingKey === msg.key" class="capsule-progress" :style="{ width: `${Math.min(100, playbackTime / (playbackDuration || estimateSeconds(msg.text)) * 100)}%` }" aria-hidden="true"></i>
                      <AppIcon :name="ttsBusyKey === msg.key ? 'loader' : playingKey === msg.key ? 'pause' : 'headphones'" :size="16" :class="{ spin: ttsBusyKey === msg.key }" />
                      <span class="capsule-duration">{{ ttsBusyKey === msg.key ? '合成中' : playingKey === msg.key ? `${Math.round(playbackTime)}″ / ${Math.round(playbackDuration || estimateSeconds(msg.text))}″` : `${estimateSeconds(msg.text)}″` }}</span>
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
              <!-- 待机：纯居中构图，模式切换下沉到 foot 行 -->
              <div v-else class="composer voice-bar idle">
                <button class="mic-orb" type="button" :disabled="sending || finished || asrAvailable === false || !recordingSupported" :title="voiceCtaText" aria-label="开始语音输入" @click="startRecording"><AppIcon name="mic" :size="17" /><i class="orb-ring" aria-hidden="true"></i></button>
                <button class="voice-bar-info" type="button" :disabled="sending || finished || asrAvailable === false || !recordingSupported" @click="startRecording">
                  <b>{{ voiceCtaText }}</b>
                  <span>{{ voiceHintText }}</span>
                </button>
              </div>
              <div class="composer-foot">
                <span><AppIcon name="mic" :size="12" />{{ asrAvailable === false ? '语音暂不可用' : '转写结果确认后再发送' }}</span>
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
            <div class="side-head"><h3>交流伙伴</h3><router-link :to="{ name: 'avatar' }" class="side-link" aria-label="设置数字人形象"><AppIcon name="settings" :size="15" /></router-link></div>
            <AvatarStage :avatar="companionAvatar" :state="voiceBusy ? (voiceStatus === 'recording' ? 'listening' : 'thinking') : avatarState" :size="238" :show-backdrop="false" />
            <div class="companion-identity"><b>{{ activeRole?.display_name || '交流伙伴' }}</b><span>{{ activeRole?.title || '英语练习伙伴' }}</span></div>
            <label class="autoplay-control"><input v-model="autoPlayReplies" type="checkbox" @change="saveAutoPlayPreference" />自动播放问候与回复</label>
            <details class="voice-settings"><summary><AppIcon name="volume" :size="13" />声音与语速<span>{{ speechRate.toFixed(2) }}×</span><AppIcon name="chevron-down" :size="13" /></summary><div class="voice-controls"><label for="practice-voice">播报音色</label><select id="practice-voice" v-model="voiceStyle" class="voice-select"><option v-for="voice in voices" :key="voice.style" :value="voice.style">{{ voice.label || voice.style }}{{ voice.available === false ? '（不可用）' : '' }}</option></select><label for="practice-rate">语速 {{ speechRate.toFixed(2) }}×</label><input id="practice-rate" v-model.number="speechRate" class="voice-rate" type="range" min="0.75" max="1.25" step="0.05" /></div></details>
          </section>

          <section class="support-card">
            <div class="support-tabs" role="group" aria-label="辅助信息"><button v-for="tab in supportTabs" :key="tab.id" type="button" :aria-pressed="sideTab === tab.id" :class="{ active: sideTab === tab.id }" @click="sideTab = tab.id">{{ tab.label }}</button></div>
            <div v-if="sideTab === 'task'" class="support-content">
              <div class="task-heading"><h3>本次训练目标</h3><span>{{ completedGoals }} / {{ stateInfo.goals?.length || 0 }}</span></div>
              <progress class="goal-progress" :value="completedGoals" :max="stateInfo.goals?.length || 1" aria-label="训练目标完成进度"></progress>
              <div v-if="currentStage" class="current-stage"><small>当前阶段</small><b>{{ currentStage.name }}</b><p v-if="currentStage.guidance">{{ currentStage.guidance }}</p></div>
              <ul v-if="stateInfo.goals?.length" class="goal-list"><li v-for="(goal, index) in stateInfo.goals" :key="goal.id" :class="{ done: goal.done }"><span class="goal-number"><AppIcon v-if="goal.done" name="check" :size="12" /><template v-else>{{ index + 1 }}</template></span><span>{{ goal.label }}</span></li></ul>
              <p v-else class="support-empty">这个场景采用开放交流，按自己的节奏继续。</p>
            </div>
            <div v-else-if="sideTab === 'feedback'" class="support-content"><span class="support-symbol"><AppIcon name="headphones" :size="21" /></span><h3>先交流，再打磨表达</h3><p class="support-description">逐句纠错与发音评分尚未开放。你可以回放伙伴的回复，留意表达方式和语音节奏。</p></div>
          </section>

          <section class="support-card state-card">
            <details class="state-details">
              <summary>场景状态<AppIcon name="chevron-down" :size="13" /></summary>
              <ul v-if="stateRows.length" class="state-list"><li v-for="row in stateRows" :key="row.key"><span>{{ row.key }}</span><b>{{ row.value }}</b></li></ul>
              <p v-else class="support-empty">本场景暂无可展示的运行状态。</p>
            </details>
          </section>
        </aside>
      </div>
    </div>

    <!-- 进入对话确认弹窗：确认后才创建会话 -->
    <div v-if="confirmScene" class="modal-backdrop" @click.self="confirmScene = null">
      <div class="modal-card" role="alertdialog" aria-modal="true" :aria-label="`开始场景 ${confirmScene.name}`">
        <div class="modal-icon"><AppIcon name="messages" :size="18" /></div>
        <h3>开始「{{ confirmScene.name }}」？</h3>
        <p>将创建一条新的练习会话，与场景角色从开场白开始对话。</p>
        <ul class="modal-facts">
          <li v-if="confirmScene.objective_count"><span>训练目标</span><b>{{ confirmScene.objective_count }} 个</b></li>
          <li v-if="confirmScene.stage_count"><span>对话阶段</span><b>{{ confirmScene.stage_count }} 个</b></li>
          <li v-if="confirmScene.difficulty"><span>难度</span><b>{{ diffLabel(confirmScene.difficulty) }}</b></li>
        </ul>
        <div class="modal-actions">
          <button class="ghost-button" type="button" :disabled="starting" @click="confirmScene = null">取消</button>
          <button class="confirm-button" type="button" :disabled="starting" @click="confirmStart">
            <AppIcon :name="starting ? 'loader' : 'arrow-right'" :size="14" />{{ starting ? '准备中…' : '确认开始' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 场景知识点弹窗：分资料模块 Tab + Markdown 正文（对齐 1.0 的独立知识面板） -->
    <PracticeKnowledge v-if="knowledgeOpen" :scene-id="sessionInfo.scene_id" :description="sceneMeta?.package?.meta?.description || ''" @close="knowledgeOpen = false" />
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import AvatarStage from '../components/avatar/AvatarStage.vue'
import PracticeKnowledge from '../components/practice/PracticeKnowledge.vue'
import { getScene, listScenes } from '../api/scenes'
import { createSession, getGreetingAudio, submitTurn } from '../api/sessions'
import { getSpeechStatus } from '../api/speech'
import { useVoiceInput } from '../composables/useVoiceInput'
import { FALLBACK_AVATARS, FALLBACK_VOICES, fetchTtsVoices, getAvatarPreference, synthesizeSpeech, VOICE_STYLE_ALIASES } from '../api/avatar'
import { session } from '../auth/session'

const CATEGORY_LABELS = { daily: '日常', interview: '面试', career: '职业', academic: '学术', custom: '自定义', travel: '旅行', business: '商务', campus: '校园', debate: '辩论' }
const FINISH_REASONS = { condition_met: '场景任务已完成，本次练习结束。', max_turns: '已达到本场景的轮次上限，练习结束。' }

const phase = ref('select') // select=选场景 / chat=对话中
const scenes = ref([])
const loadingScenes = ref(false)
const starting = ref(false)
const error = ref('')
const pickCategory = ref('all') // 选场景页分类筛选
const keyword = ref('') // 选场景页搜索关键词
const confirmScene = ref(null) // 进入对话前的确认弹窗（点确认才创建会话）

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
const sideTab = ref('task')
const knowledgeOpen = ref(false) // 场景知识点弹窗（参照 1.0 独立面板，分资料模块 Tab）
const showOriginal = ref(false) // 默认语音气泡：原文默认隐藏，可全局显示或逐条展开
const expandedMessages = ref(new Set())
const supportTabs = [{ id: 'task', label: '任务' }, { id: 'feedback', label: '反馈' }] // 知识点已改为独立弹窗（对齐 1.0），不再占右栏 Tab
let msgSeq = 0

// TTS 播报：音色/语速取场景档偏好，未设置时用缺省值
const voices = ref(FALLBACK_VOICES)
const voiceStyle = ref('emma')
const speechRate = ref(1)
const ttsBusyKey = ref('')
const playingKey = ref('')
const playbackTime = ref(0) // 当前播放秒数（胶囊进度条用）
const playbackDuration = ref(0) // 当前音频总时长（元数据加载后更新）
// 语音胶囊：宽度与预估时长按词数估算（对齐 1.0 的 getCapsuleWidth / getWavDuration）
function estimateSeconds(text) {
  const words = (text || '').trim().split(/\s+/).filter(Boolean).length
  return Math.max(2, Math.round(words / 2))
}
function capsuleWidth(text) {
  return `${Math.min(320, Math.max(120, 110 + estimateSeconds(text) * 9))}px`
}
let currentAudio = null
let playbackGeneration = 0 // 丢弃切换消息或离开页面后才完成的语音合成
let sessionGeneration = 0
const autoPlayReplies = ref(localStorage.getItem('echotalk:autoplay-replies') !== '0')
const playbackNotice = ref('')

function saveAutoPlayPreference() {
  localStorage.setItem('echotalk:autoplay-replies', autoPlayReplies.value ? '1' : '0')
  if (!autoPlayReplies.value) stopAudio()
}

const stateInfo = computed(() => sessionInfo.value?.state || {})
const finished = computed(() => stateInfo.value.status === 'finished')
const finishText = computed(() => FINISH_REASONS[stateInfo.value.finish_reason] || '本次练习已结束。')
const activeRole = computed(() => sceneMeta.value?.package?.roles?.[0] || null)
const roleName = computed(() => activeRole.value ? `${activeRole.value.display_name} · ${activeRole.value.title || '对话伙伴'}` : '场景对话伙伴')
const roleInitial = computed(() => (activeRole.value?.display_name || 'A').slice(0, 1).toUpperCase())
const userInitial = computed(() => (session.user?.username || 'A').slice(0, 1).toUpperCase())
const sceneTitle = computed(() => sceneMeta.value?.package?.meta?.name || sceneMeta.value?.name || '场景对话')
const currentStage = computed(() => sceneMeta.value?.package?.stages?.find(stage => stage.id === stateInfo.value.stage))
const completedGoals = computed(() => (stateInfo.value.goals || []).filter(goal => goal.done).length)
const conversationStatus = computed(() => finished.value ? '本次练习已结束' : voiceBusy.value ? voiceStatusLabel.value : sending.value ? '正在思考你的回答…' : ttsBusyKey.value ? '正在准备语音…' : playingKey.value ? '正在播放回复' : '等待你的回应')
// 语音优先 CTA 文案：按服务配置、环境支持与练习状态给出可执行提示
const voiceCtaText = computed(() => {
  if (asrAvailable.value === false) return '语音服务未配置，请改用文字输入'
  if (!recordingSupported.value) return '当前环境不支持录音，请改用文字输入'
  if (sending.value) return '正在发送…'
  if (finished.value) return '本次练习已结束'
  return '点击说英语'
})
// 待机条副标题：补充主文案之外的使用说明
const voiceHintText = computed(() => {
  if (asrAvailable.value === false) return '切换文字输入可以继续交流'
  if (!recordingSupported.value) return '切换文字输入可以继续交流'
  if (finished.value) return '退出后可另选场景练习'
  return '英语语音 · 最长 60 秒 · 转写后确认发送'
})
// 录音中迷你声波：7 根柱子按基准波形 × 实时音量缩放
const LEVEL_BARS = [0.35, 0.6, 0.9, 1, 0.75, 0.5, 0.65]
function levelBar(i) {
  const scaled = LEVEL_BARS[i % LEVEL_BARS.length] * (0.35 + recordingLevel.value * 1.3)
  return `${Math.max(3, Math.min(15, Math.round(scaled * 15)))}px`
}
// 场景状态卡：仅展示原始值字段，对象/数组不强行渲染
const stateRows = computed(() =>
  Object.entries(stateInfo.value.scenario_state || {})
    .filter(([, value]) => ['string', 'number', 'boolean'].includes(typeof value))
    .map(([key, value]) => ({ key, value: String(value) }))
)
// 伙伴形象：优先用户场景档偏好，其次缺省清单首个
const companionAvatar = computed(() => {
  const id = companionAvatarId.value
  return FALLBACK_AVATARS.find((a) => a.id === id) || FALLBACK_AVATARS[0]
})
const companionAvatarId = ref(null)

const categoryLabel = (key) => CATEGORY_LABELS[key] || key || '通用'
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
  return msg
}

async function scrollToBottom() {
  await nextTick()
  if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight
}

// ---- 场景选择与会话创建 -----------------------------------------------------

onMounted(async () => {
  getSpeechStatus().then(({ data }) => { asrAvailable.value = data.configured }).catch(() => {})
  loadingScenes.value = true
  try {
    const { data } = await listScenes()
    scenes.value = data?.items || []
  } catch (err) {
    error.value = err.message
  } finally {
    loadingScenes.value = false
  }
  const list = await fetchTtsVoices()
  if (list?.length) voices.value = list // 探测失败保持前端缺省清单
})

async function startScene(scene) {
  if (starting.value) return
  starting.value = true
  const generation = ++sessionGeneration
  error.value = ''
  try {
    // 知识点面板按需独立加载，不因资料服务失败阻塞进入对话。
    const [detailRes, sessionRes] = await Promise.all([
      getScene(scene.id),
      createSession(scene.id),
    ])
    if (generation !== sessionGeneration) return
    sceneMeta.value = detailRes.data
    sessionInfo.value = sessionRes.data
    messages.value = []
    const greetingMessage = sessionRes.data.greeting ? pushMessage('agent', sessionRes.data.greeting) : null
    if (greetingMessage) greetingMessage.greetingSessionId = sessionRes.data.id
    phase.value = 'chat'
    avatarState.value = 'idle'
    confirmScene.value = null // 进入成功后收起确认弹窗
    await loadVoicePreference(scene.id)
    await nextTick()
    if (generation !== sessionGeneration) return
    composerBox.value?.focus()
    if (greetingMessage && autoPlayReplies.value) void playMessage(greetingMessage, { automatic: true })
  } catch (err) {
    error.value = err.message
  } finally {
    starting.value = false
  }
}

function confirmStart() {
  // 弹窗确认入口：真正发起会话创建
  if (confirmScene.value) startScene(confirmScene.value)
}

async function loadVoicePreference(sceneId) {
  const pref = await getAvatarPreference(sceneId)
  companionAvatarId.value = pref?.avatar_id || null
  const style = VOICE_STYLE_ALIASES[pref?.voice_style] || pref?.voice_style
  if (style && voices.value.some((v) => v.style === style)) voiceStyle.value = style
  if (Number.isFinite(pref?.speech_rate)) speechRate.value = Math.min(1.25, Math.max(0.75, pref.speech_rate))
}

function backToSelect() {
  if (sending.value) return
  sessionGeneration += 1
  playbackNotice.value = ''
  cancelRecording()
  transcribedText.value = ''
  stopAudio()
  phase.value = 'select'
  sessionInfo.value = null
  sceneMeta.value = null
  messages.value = []
  draft.value = ''
  expandedMessages.value.clear()
  sideTab.value = 'task'
  error.value = ''
}

function finishAndExit() {
  // 复盘报告依赖训练报告模块（未接入），先做客户端确认后返回
  if (window.confirm('退出当前练习并返回场景列表？')) backToSelect()
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
    const blob = msg.greetingSessionId
      ? await getGreetingAudio(msg.greetingSessionId, voiceStyle.value, speechRate.value)
      : await synthesizeSpeech(msg.text, voiceStyle.value, speechRate.value)
    if (generation !== playbackGeneration) return
    const url = URL.createObjectURL(blob)
    currentAudio = new Audio(url)
    currentAudio.ontimeupdate = () => { playbackTime.value = currentAudio?.currentTime || 0 }
    currentAudio.onloadedmetadata = () => { playbackDuration.value = isFinite(currentAudio?.duration) ? currentAudio.duration : 0 }
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

onBeforeUnmount(() => { sessionGeneration += 1; stopAudio() })
</script>

<style scoped>
.autoplay-control { display: flex; align-items: center; gap: 7px; margin: 10px 0 12px; color: var(--ink-soft); font-size: 12px; }.autoplay-control input { accent-color: var(--brand); }
.playback-notice { display: flex; align-items: flex-start; gap: 6px; margin: 0 0 10px; color: var(--muted); font-size: 12px; line-height: 1.7; }
/* 录音与转写共用单行输入条（.composer 外壳），三态等高，文字草稿不随录音清空。 */
.mic-input-button { display: none; } /* 已被语音优先布局取代，保留类名防止外部引用报错 */
/* 语音优先：单行紧凑条（42px 圆形麦克风 + 信息列 + 右侧操作） */
.voice-bar { position: relative; align-items: center; gap: 12px; min-height: 62px; }
/* 待机态：麦克风按钮组水平居中（模式切换已下沉到 foot 行） */
.voice-bar.idle { justify-content: center; }
.voice-bar.idle .voice-bar-info { flex: 0 1 auto; } /* 取消 flex:1 拉伸，居中才有可分配空隙 */
.voice-bar.live { border-color: #e0d8f5; background: #faf8ff; }
.mic-orb { position: relative; display: grid; place-items: center; width: 42px; height: 42px; flex: 0 0 42px; border: 0; border-radius: 50%; background: var(--brand); color: #fff; transition: background .15s, transform .15s; }
.mic-orb:hover:not(:disabled) { background: var(--brand-deep); transform: scale(1.04); }
.mic-orb:active:not(:disabled) { transform: scale(.95); }
.mic-orb:disabled { background: #c9cbea; cursor: not-allowed; }
.mic-orb.stop { background: var(--danger); }
.mic-orb.static { background: #e3e2f4; color: var(--brand-deep); animation: spin 1s linear infinite; }
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
/* foot 行右侧的模式切换小按钮（语音条本体保持纯居中，不再放图标钮） */
.foot-toggle { display: inline-flex; align-items: center; gap: 4px; padding: 2px 4px; border: 0; background: transparent; color: var(--muted); font-size: 11.5px; transition: color .15s; }
.foot-toggle:hover:not(:disabled) { color: var(--ink); }
.foot-toggle:disabled { opacity: .5; }
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
.pick-toolbar { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.seg-filter { display: inline-flex; gap: 3px; padding: 3px; border: 1px solid var(--line); border-radius: 9px; background: var(--surface); }
.seg-item { display: inline-flex; align-items: center; gap: 6px; height: 31px; padding: 0 13px; border: 0; border-radius: 7px; background: transparent; color: var(--ink-soft); font-size: 13.5px; transition: background .15s, color .15s; }
.seg-item:hover { color: var(--ink); }
.seg-item.active { background: var(--brand-soft); color: var(--brand-deep); font-weight: 500; }
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
.scene-card { display: flex; flex-direction: column; padding: 15px 16px 14px; border: 1px solid var(--line); border-radius: 12px; background: var(--surface); text-align: left; transition: border-color .18s, transform .18s, box-shadow .18s; animation: card-in .38s cubic-bezier(.22, .8, .32, 1) both; }
.scene-card:hover:not(:disabled) { border-color: #d8daea; transform: translateY(-2px); box-shadow: 0 6px 18px rgba(34, 37, 59, .06); }
.scene-card:active:not(:disabled) { transform: translateY(0); }
.scene-card:disabled { opacity: .6; }
@keyframes card-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
.card-head { display: flex; align-items: center; gap: 7px; margin-bottom: 11px; }
.mode-chip { display: inline-flex; align-items: center; gap: 4px; height: 22px; padding: 0 9px; border-radius: 6px; background: var(--brand-soft); color: var(--brand-deep); font-size: 11.5px; font-weight: 500; }
.diff-chip { display: inline-flex; align-items: center; height: 22px; padding: 0 9px; border-radius: 6px; background: #f1f2f7; color: var(--ink-soft); font-size: 11.5px; font-weight: 500; }
.diff-chip.entry { background: #e3f2ea; color: #2f7a52; }
.diff-chip.easy { background: #e0f2ef; color: #257a6b; }
.diff-chip.normal { background: #e3ecfb; color: #33619f; }
.diff-chip.hard { background: #fdefe0; color: #b26a24; }
.diff-chip.expert { background: #fbe7e7; color: #b03a3a; }
.scene-name { font-size: 15.5px; font-weight: 600; letter-spacing: -.01em; }
.scene-desc { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; min-height: 42px; margin-top: 6px; color: var(--muted); font-size: 13.5px; line-height: 1.55; text-wrap: pretty; }
.scene-foot { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-top: 13px; padding-top: 13px; border-top: 1px solid var(--line); }
.scene-meta { display: flex; flex-wrap: wrap; gap: 4px 10px; }
.scene-meta span { display: inline-flex; align-items: center; gap: 4px; color: var(--muted); font-size: 11.5px; }
.scene-go { display: inline-flex; align-items: center; gap: 4px; color: var(--brand); font-size: 12.5px; font-weight: 500; white-space: nowrap; }
.scenes-empty { grid-column: 1 / -1; display: grid; justify-items: center; padding: 46px 20px; border: 1px dashed var(--line); border-radius: 14px; background: rgba(255, 255, 255, .55); text-align: center; }
.empty-icon { display: grid; width: 48px; height: 48px; place-items: center; border: 1px solid #e3e4fb; border-radius: 12px; background: var(--brand-soft); color: var(--brand); }
.scenes-empty h3 { margin: 14px 0 6px; font-size: 16px; font-weight: 600; }
.scenes-empty p { margin: 0; max-width: 400px; color: var(--muted); font-size: 13.5px; line-height: 1.65; text-wrap: pretty; }
.scene-card.skeleton { animation: none; cursor: default; }
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
.confirm-button { display: inline-flex; align-items: center; gap: 6px; height: 34px; padding: 0 15px; border: 0; border-radius: 8px; background: var(--brand); color: #fff; font-size: 13.5px; font-weight: 500; transition: background .15s; }
.confirm-button:hover:not(:disabled) { background: var(--brand-deep); }
.confirm-button:disabled { opacity: .6; }
@keyframes fade-in { from { opacity: 0; } }
@keyframes pop-in { from { opacity: 0; transform: translateY(8px) scale(.97); } }
.ghost-button, .exit-button { display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; gap: 7px; min-height: 34px; padding: 0 12px; border: 1px solid var(--line); border-radius: 8px; background: white; color: var(--ink-soft); font-size: 13px; text-decoration: none; }
.ghost-button:hover { border-color: #c9cbea; color: var(--brand-deep); }
.exit-button { color: #9d5865; background: #fff8f8; border-color: #f0dfe3; }
.exit-button:hover { background: #fbeef1; } button:disabled { opacity: .5; }
/* 页面内只滚动消息与辅助栏，输入始终可见。 */
.chat-page { display: flex; flex-direction: column; flex: 1; min-height: 0; padding: 0 24px 22px; }
.session-toolbar { display: flex; align-items: center; gap: 12px; flex: 0 0 auto; min-height: 84px; padding: 14px 0; }
.back-button { display: grid; place-items: center; width: 32px; height: 32px; flex-shrink: 0; background: white; border: 1px solid var(--line); border-radius: 8px; color: var(--muted); }
.session-heading { min-width: 0; flex: 1; }.session-heading h2 { margin: 0; font-size: 18px; font-weight: 600; line-height: 1.5; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.session-heading p { margin: 3px 0 0; color: var(--muted); font-size: 12.5px; }.session-heading p span { margin: 0 8px; }
.session-counter { display: flex; align-items: center; gap: 6px; margin-right: 4px; color: var(--muted); font-size: 12.5px; white-space: nowrap; }
.chat-layout { flex: 1; min-height: 0; display: grid; grid-template-columns: minmax(0, 1fr) 292px; gap: 18px; }
.chat-card { display: flex; flex-direction: column; min-width: 0; min-height: 0; background: white; border: 1px solid var(--line); border-radius: 14px; overflow: hidden; }
.chat-head { display: flex; align-items: center; gap: 10px; padding: 14px 20px; border-bottom: 1px solid var(--line); flex-shrink: 0; }
.role-avatar { display: grid; place-items: center; flex: 0 0 36px; width: 36px; height: 36px; border-radius: 12px; background: var(--brand-soft); color: var(--brand); font-size: 14px; font-weight: 600; }
.role-info { flex: 1; min-width: 0; }.role-info b { display: block; font-size: 14px; font-weight: 600; }.role-status { display: flex; align-items: center; gap: 5px; margin-top: 4px; color: var(--muted); font-size: 12px; }.status-dot { width: 5px; height: 5px; border-radius: 50%; background: #78a993; }.status-dot.busy { background: var(--brand); }
.text-toggle { display: inline-flex; align-items: center; gap: 5px; border: 0; padding: 6px; background: transparent; color: var(--muted); font-size: 12.5px; }.text-toggle[aria-pressed="true"] { color: var(--brand); }
.chat-body { flex: 1; min-height: 0; overflow: auto; overscroll-behavior: contain; padding: 20px 24px 28px; scrollbar-width: thin; }
.conversation-start { display: flex; align-items: center; justify-content: center; gap: 12px; margin: 0 0 28px; color: var(--faint); }.conversation-start span { height: 1px; flex: 1; max-width: 60px; background: var(--line); }.conversation-start small { font-size: 12px; text-align: center; }
.msg-row { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 25px; }.msg-row.user { justify-content: flex-end; }.msg-avatar { display: grid; place-items: center; width: 30px; height: 30px; flex: 0 0 30px; margin-top: 21px; border-radius: 10px; background: #f0effa; color: #7771ac; font-size: 12.5px; font-weight: 600; }.msg-avatar.user { background: #e9edf7; color: #6c7a9a; }
.message-content { display: flex; flex-direction: column; align-items: flex-start; max-width: min(82%, 640px); }.msg-row.user .message-content { align-items: flex-end; }.message-author { margin-bottom: 6px; font-size: 12px; color: var(--muted); }
.bubble { padding: 13px 17px; background: #f5f6fa; border-radius: 2px 13px 13px 13px; }.msg-row.user .bubble { background: #eeedff; color: #46457c; border-radius: 13px 2px 13px 13px; }.bubble-text { margin: 0; font-size: 15px; line-height: 1.85; white-space: pre-wrap; overflow-wrap: anywhere; }
/* agent 语音气泡：交互结构沿用 1.0（胶囊常驻+进度条+原文面板），外观对齐 2.0——实色品牌紫、扁平无渐变阴影，与发送按钮/麦克风圆钮同色 */
.bubble-row { display: flex; align-items: center; gap: 10px; }
.ai-voice-capsule { position: relative; display: flex; align-items: center; gap: 9px; height: 38px; min-width: 120px; padding: 0 15px; border: 0; border-radius: 19px; border-top-left-radius: 3px; background: var(--brand); color: #fff; overflow: hidden; transition: background .15s, transform .15s; }
.ai-voice-capsule:hover:not(:disabled) { background: var(--brand-deep); transform: scale(1.02); }
.ai-voice-capsule:active:not(:disabled) { transform: scale(.98); }
.ai-voice-capsule:disabled { opacity: .7; cursor: wait; }
.ai-voice-capsule.playing { background: var(--brand-deep); }
.capsule-progress { position: absolute; left: 0; bottom: 0; height: 3px; background: rgba(255, 255, 255, .45); transition: width .12s linear; }
.capsule-duration { font-size: 12.5px; font-weight: 600; font-variant-numeric: tabular-nums; }
.spin { animation: spin 1s linear infinite; }
.original-toggle { display: inline-flex; align-items: center; gap: 4px; padding: 4px 2px; border: 0; background: transparent; color: var(--brand); font-size: 12.5px; transition: color .15s; }
.original-toggle:hover { color: var(--brand-deep); }
.original-panel { max-width: 76%; margin-top: 8px; padding: 12px 15px; border-radius: 2px 13px 13px 13px; background: #f5f6fa; }
.panel-enter-active, .panel-leave-active { transition: opacity .18s ease, transform .18s ease; }
.panel-enter-from, .panel-leave-to { opacity: 0; transform: translateY(-4px); }
.thinking-message { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; }.thinking-message .msg-avatar { margin-top: 0; }.thinking-message small { color: var(--muted); font-size: 12.5px; }.thinking-dots { display: flex; gap: 4px; padding: 12px; border-radius: 10px; background: var(--bg); }.thinking-dots i { width: 4px; height: 4px; border-radius: 50%; background: var(--brand); }
.finish-banner { display: flex; align-items: center; gap: 8px; padding: 12px; color: #4a7f63; border-radius: 8px; background: #f1f8f3; font-size: 13.5px; }
.composer-area { flex-shrink: 0; margin: 0 20px; padding: 13px 0 12px; border-top: 1px solid var(--line); }
.composer { display: flex; align-items: flex-end; gap: 10px; padding: 10px; border: 1px solid #e6e6f0; border-radius: 11px; background: #fcfcfe; transition: border-color .15s; }.composer:focus-within { border-color: #a9a7e9; }.composer-input { display: block; flex: 1; min-width: 0; min-height: 42px; max-height: 132px; padding: 0 3px; outline: none; border: 0; resize: none; background: transparent; font: inherit; font-size: 14.5px; line-height: 1.7; color: var(--ink); }.composer-input::placeholder { color: var(--faint); }.send-button { display: flex; align-items: center; justify-content: center; gap: 4px; height: 34px; padding: 0 14px; border: 0; border-radius: 8px; color: white; background: var(--brand); font-size: 13px; }.send-button:hover:not(:disabled) { background: var(--brand-deep); }
.composer-foot { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 7px; margin-top: 9px; color: var(--faint); font-size: 11.5px; }.recording-note { display: flex; align-items: center; gap: 4px; }.keyboard-hint { display: flex; align-items: center; gap: 5px; }.keyboard-hint>span { margin: 0 3px; }kbd { font-family: inherit; font-size: 10.5px; }.chat-error { display: flex; align-items: center; gap: 5px; margin: 0 0 10px; color: var(--danger); font-size: 13px; }
.chat-side { display: flex; flex-direction: column; gap: 14px; min-height: 0; overflow: auto; scrollbar-width: thin; }.companion-card, .support-card { flex-shrink: 0; border: 1px solid var(--line); background: white; border-radius: 14px; overflow: hidden; }.companion-card { padding: 14px; }.side-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }h3 { margin: 0; font-size: 13.5px; font-weight: 600; }.side-link { color: var(--muted); display: flex; padding: 3px; }
.companion-card :deep(.stage) { width: 100% !important; aspect-ratio: 1.4; border-radius: 10px; border: 0; background: #f4f2fa; }.companion-card :deep(.stage-top) { top: 12px; left: 12px; right: 12px; }.companion-card :deep(.edition), .companion-card :deep(.stage-bottom), .companion-card :deep(.spark) { display: none; }.companion-card :deep(.character) { left: 18%; width: 64%; height: 90%; }.companion-card :deep(.halo) { width: 62%; left: 19%; top: 17%; }.companion-identity { display: flex; align-items: center; gap: 7px; margin: 12px 0; }.companion-identity b { font-size: 14px; font-weight: 600; }.companion-identity span { font-size: 12px; color: var(--muted); }
.voice-settings { border-top: 1px solid var(--line); padding-top: 10px; }summary { cursor: pointer; list-style: none; }summary::-webkit-details-marker { display: none; }.voice-settings summary { display: flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--ink-soft); }.voice-settings summary span { margin-left: auto; font-size: 11.5px; }.voice-controls { display: grid; gap: 8px; padding: 12px 0 1px; }.voice-controls label { color: var(--muted); font-size: 11.5px; }.voice-select { min-width: 0; width: 100%; height: 32px; border: 1px solid var(--line); border-radius: 6px; color: var(--ink-soft); background: white; font-size: 12.5px; }.voice-rate { width: 100%; accent-color: var(--brand); }
.support-tabs { display: flex; gap: 4px; padding: 0 14px; border-bottom: 1px solid var(--line); }.support-tabs button { flex: 1; height: 44px; border: 0; border-bottom: 2px solid transparent; background: transparent; color: var(--muted); font-size: 13.5px; }.support-tabs button.active { color: var(--brand); border-bottom-color: var(--brand); font-weight: 500; }.support-content { height: 320px; overflow-y: auto; scrollbar-width: thin; padding: 17px 16px; }.task-heading { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }.task-heading span { color: var(--brand); font-size: 12px; font-variant-numeric: tabular-nums; }.goal-progress { display: block; width: 100%; height: 4px; border: 0; appearance: none; background: #f0eff7; border-radius: 4px; overflow: hidden; accent-color: var(--brand); }.goal-progress::-webkit-progress-bar { background: #f0eff7; }.goal-progress::-webkit-progress-value { background: #8985df; border-radius: 4px; }.goal-progress::-moz-progress-bar { background: #8985df; }
.current-stage { margin-top: 16px; padding: 10px 12px; border-left: 2px solid #b2adea; background: #f8f7fd; }.current-stage small { display: block; font-size: 10.5px; color: var(--muted); margin-bottom: 5px; }.current-stage b { font-size: 12.5px; font-weight: 500; }.current-stage p { margin: 6px 0 0; color: var(--muted); font-size: 11.5px; line-height: 1.8; }.goal-list { list-style: none; padding: 0; margin: 15px 0 0; }.goal-list li { display: flex; gap: 9px; align-items: flex-start; padding: 8px 0; color: var(--ink-soft); font-size: 12.5px; line-height: 1.7; }.goal-number { display: grid; place-items: center; width: 20px; height: 20px; flex: 0 0 20px; border: 1px solid var(--line); border-radius: 50%; color: var(--muted); font-size: 10.5px; }.done .goal-number { color: #4c8a6a; border-color: #dceee1; background: #eff8f2; }.done>span:last-child { color: var(--muted); }
/* 场景状态：右栏底部独立折叠卡（对齐桌面稿）。 */
.state-card { flex-shrink: 0; }
.state-details { margin: 0; padding: 0; border: 0; }
.state-details summary { display: flex; align-items: center; justify-content: space-between; padding: 13px 16px; color: var(--ink); font-size: 13px; font-weight: 600; }
.state-details[open] summary { border-bottom: 1px solid var(--line); }
.state-details .state-list, .state-details .support-empty { margin: 0; padding: 12px 16px 14px; }
.state-list { list-style: none; }.state-list li { display: flex; justify-content: space-between; gap: 12px; margin-top: 8px; font-size: 12px; }.state-list span { color: var(--muted); }.state-list b { font-weight: 500; text-align: right; overflow-wrap: anywhere; }.support-description, .support-empty { margin: 10px 0 0; color: var(--muted); font-size: 12.5px; line-height: 1.9; }.support-symbol { display: inline-flex; color: var(--brand); margin-bottom: 14px; }.reference-link { display: flex; align-items: center; justify-content: space-between; margin-top: 18px; color: var(--brand); text-decoration: none; font-size: 12.5px; }
/* 场景知识点（参考 Tab，迁移自 1.0 知识抽屉） */
@media (min-width: 1550px) { .chat-page { padding: 0 36px 28px; }.chat-layout { grid-template-columns: minmax(0, 1fr) 320px; gap: 22px; }.chat-body { padding: 24px 36px; } }
@media (max-width: 1100px) { .chat-page { padding: 0 16px 16px; }.chat-layout { grid-template-columns: minmax(0, 1fr) 252px; gap: 12px; }.session-counter { display: none; }.chat-head { padding: 12px 14px; }.chat-body { padding: 16px 14px; }.composer-area { margin: 0 14px; }.role-info b { font-size: 13px; } }
@media (max-width: 760px) { .chat-page { overflow: auto; }.chat-layout { display: flex; flex-direction: column; flex: 1 0 auto; }.chat-card { min-height: 520px; height: calc(100dvh - 170px); }.chat-side { display: grid; grid-template-columns: 1fr 1fr; overflow: visible; min-height: auto; }.session-toolbar { flex-wrap: wrap; gap: 8px; padding: 12px 0; }.session-heading h2 { font-size: 14px; }.session-heading { flex-basis: calc(100% - 45px); }.reference-button { margin-left: 40px; }.session-toolbar .exit-button { margin-left: auto; }.page-scroll { padding: 24px 18px; }.keyboard-hint { display: none; } }
@media (max-width: 480px) { .chat-side { grid-template-columns: 1fr; }.message-content { max-width: 82%; }.bubble { padding: 10px 12px; }.bubble-text { font-size: 14px; }.text-toggle { max-width: 80px; }.role-info b { max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } }
@media (prefers-reduced-motion: no-preference) { .thinking-dots i { animation: breathe 1.2s ease-in-out infinite; }.thinking-dots i:nth-child(2) { animation-delay: .15s; }.thinking-dots i:nth-child(3) { animation-delay: .3s; }@keyframes breathe { 50% { opacity: .25; transform: translateY(-2px); } } }
</style>

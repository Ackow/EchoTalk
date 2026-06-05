<template>
  <div class="practice-layout">
    <!-- Header Block -->
    <header class="practice-header glass-panel">
      <div class="header-left">
        <el-button class="back-btn hover-scale" link @click="goHome">
          <el-icon><ArrowLeft /></el-icon>
          <span>退出场景</span>
        </el-button>
        <div class="divider"></div>
        <div class="scene-meta">
          <h2 class="scene-title">{{ scene?.name || '口语演练' }}</h2>
          <p class="scene-desc">{{ formatCategory(scene?.category) }} · 智能口语对话</p>
        </div>
        <template v-if="isProcessing">
          <div class="header-status-divider"></div>
          <div class="header-status-panel">
            <div class="status-title-row">
              <el-icon class="status-icon voice-icon-spinning"><Loading /></el-icon>
              <span class="status-big-title">{{ currentBigStatus }}</span>
            </div>
            <span class="status-playful-remark">{{ currentPlayfulRemark }}</span>
          </div>
        </template>
      </div>
      <div class="header-right">
        <!-- Params Status Panel -->
        <div class="active-params" v-if="activeParams && Object.keys(activeParams).length > 0">
          <div v-for="(val, key) in activeParams" :key="key" :class="['param-tag', getParamTagClass(key)]">
            <span class="key">{{ translateKey(key) }}:</span>
            <span class="val">{{ val }}</span>
          </div>
        </div>
        <el-button type="danger" size="default" class="settle-btn hover-scale" @click="handleSettle" :disabled="turns.length < 2">
          <el-icon><CircleCheck /></el-icon>
          <span>结束并结算</span>
        </el-button>
      </div>
    </header>

    <!-- Main Content Grid -->
    <div class="practice-grid">
      <!-- Left side: Dialogue Area -->
      <section class="dialogue-box glass-panel">
        <!-- Waiting state before session starts -->
        <div v-if="!sessionStarted" class="start-session-prompt">
          <el-icon class="prompt-icon"><Microphone /></el-icon>
          <h3>准备好开始本次口语演练了吗？</h3>
          <p>我们将针对设定好的场景与背景知识库与你进行模拟对话。你的发音将被多维度评估，语法表述也将获得润色建议。</p>
          <el-button type="primary" size="large" class="start-session-btn hover-scale" @click="startDialogueSession" :loading="startingSession">
            <span>进入练习会话</span>
          </el-button>
        </div>

        <template v-else>
          <div class="chat-history" ref="chatHistoryRef">
            <div v-for="(turn, idx) in turns" :key="turn.id || idx" :class="['message-row', turn.role === 'user' ? 'user-row' : 'ai-row']">
              <!-- AI 消息模块 -->
              <template v-if="turn.role === 'assistant'">
                <div class="avatar ai-avatar">AI</div>
                <div class="bubble-wrapper">
                  <div class="bubble-row">
                    <!-- 始终显示的灰色语音胶囊 (点击播放原音) -->
                    <div class="voice-capsule ai-voice-capsule" :style="{ width: getCapsuleWidth(turn) }" @click="playAudio(turn.audio_url, turn.id || idx)">
                      <div 
                        class="voice-capsule-progress-bar" 
                        v-if="playingTurnId === (turn.id || idx) && currentPlaybackDuration > 0"
                        :style="{ width: (currentPlaybackTime / currentPlaybackDuration * 100) + '%' }"
                      ></div>
                      <el-icon class="voice-icon" v-if="playingTurnId === (turn.id || idx)"><VideoPause /></el-icon>
                      <el-icon class="voice-icon" v-else><Headset /></el-icon>
                      <span class="voice-duration" v-if="playingTurnId === (turn.id || idx)">
                        {{ Math.round(currentPlaybackTime) }}" / {{ Math.round(currentPlaybackDuration || getWavDurationSeconds(turn)) }}"
                      </span>
                      <span class="voice-duration" v-else>{{ getWavDuration(turn) }}</span>
                    </div>
                    <!-- 文本折叠按钮 -->
                    <el-button type="primary" link class="translate-toggle-btn" @click="toggleTurnExpanded(idx, turn)">
                      <el-icon><Document /></el-icon>
                      <span>{{ expandedTurns[turn.id || idx] ? '收起' : '译文' }}</span>
                    </el-button>
                  </div>

                  <!-- 点击展开后的翻译文本解析框 (平滑展开) -->
                  <el-collapse-transition>
                    <div v-show="expandedTurns[turn.id || idx]" class="bubble-translation-panel ai-bubble glass-card">
                      <p class="message-text">{{ turn.text }}</p>
                    </div>
                  </el-collapse-transition>
                </div>
              </template>

              <!-- 用户消息模块 -->
              <template v-else>
                <!-- 1. 录音刚结束时的临时加载气泡 -->
                <div v-if="turn.isTemp" class="bubble-wrapper">
                  <!-- ASR 提取出文字时即时预览 -->
                  <el-collapse-transition>
                    <div v-if="turn.text" class="bubble-translation-panel user-bubble glass-card temp-text-bubble">
                      <p class="message-text">{{ turn.text }}</p>
                    </div>
                  </el-collapse-transition>
                  <div 
                    class="voice-capsule temp-capsule" 
                    :style="{ width: getCapsuleWidth(turn) }"
                    @click="turn.audio_url && playAudio(turn.audio_url, turn.id)"
                  >
                    <div 
                      class="voice-capsule-progress-bar" 
                      v-if="playingTurnId === turn.id && currentPlaybackDuration > 0"
                      :style="{ width: (currentPlaybackTime / currentPlaybackDuration * 100) + '%' }"
                    ></div>
                    <el-icon class="voice-icon" v-if="playingTurnId === turn.id"><VideoPause /></el-icon>
                    <el-icon class="voice-icon-spinning" v-else><Loading /></el-icon>
                    <span class="voice-duration" v-if="playingTurnId === turn.id">
                      {{ Math.round(currentPlaybackTime) }}" / {{ Math.round(currentPlaybackDuration || getWavDurationSeconds(turn)) }}"
                    </span>
                    <span class="voice-duration" v-else>{{ turn.recordingDuration || 2 }}"</span>
                  </div>
                </div>

                <!-- 2. 已合成评估完毕或正在评估的用户气泡 -->
                <div v-else :class="['bubble-wrapper', { 'is-selected': selectedTurnIndex === idx }]">
                  <div class="bubble-row">
                    <!-- 展开/折叠文本按钮 -->
                    <el-button type="success" link class="translate-toggle-btn-user" @click="toggleTurnExpanded(idx, turn)">
                      <el-icon><Document /></el-icon>
                      <span>{{ expandedTurns[turn.id || idx] ? '收起' : '文本' }}</span>
                    </el-button>

                    <!-- 始终显示的绿色语音胶囊：点击播放原音并选中 -->
                    <div class="voice-capsule" :style="{ width: getCapsuleWidth(turn) }" @click="selectAndPlayUserTurn(idx, turn)">
                      <div 
                        class="voice-capsule-progress-bar" 
                        v-if="playingTurnId === (turn.id || idx) && currentPlaybackDuration > 0"
                        :style="{ width: (currentPlaybackTime / currentPlaybackDuration * 100) + '%' }"
                      ></div>
                      <el-icon class="voice-icon" v-if="playingTurnId === (turn.id || idx)"><VideoPause /></el-icon>
                      <el-icon class="voice-icon" v-else><Mic /></el-icon>
                      <span class="voice-duration" v-if="playingTurnId === (turn.id || idx)">
                        {{ Math.round(currentPlaybackTime) }}" / {{ Math.round(currentPlaybackDuration || getWavDurationSeconds(turn)) }}"
                      </span>
                      <span class="voice-duration" v-else>{{ getWavDuration(turn) }}</span>
                      
                      <!-- 评分标签 (只有在没有评估中状态，且有评分数据时显示) -->
                      <span class="voice-capsule-score" v-if="turn.pronunciation_score && !turn.isEvaluating">
                        {{ Math.round(turn.pronunciation_score.total_score) }}分
                      </span>
                      <!-- 评估中闪烁状态 -->
                      <span class="voice-capsule-score-loading" v-else-if="turn.isEvaluating">
                        <el-icon class="voice-icon-spinning"><Loading /></el-icon> 测评中
                      </span>
                    </div>
                  </div>

                  <!-- 选中展开状态：显示完整文字与发音面板 -->
                  <el-collapse-transition>
                    <!-- 点击文字区域时选中本行进行右侧评测分析 -->
                    <div 
                      v-show="expandedTurns[turn.id || idx]" 
                      class="bubble-translation-panel user-bubble glass-card selected-bubble" 
                      @click="selectUserTurnOnly(idx)"
                    >
                      <p class="message-text">{{ turn.text }}</p>
                      
                      <!-- 显示正在评估的详细状态 -->
                      <!-- <div class="evaluating-status-text" v-if="turn.isEvaluating">
                        <el-icon class="voice-icon-spinning"><Loading /></el-icon>
                        <span>{{ turn.evaluationStatusText || '正在评测发音与语法...' }}</span>
                      </div> -->

<!--                      <div class="bubble-score" v-if="turn.pronunciation_score && !turn.isEvaluating">-->
<!--                        <el-tag size="small" type="success" effect="dark" class="score-tag">-->
<!--                          {{ Math.round(turn.pronunciation_score.total_score) }}分-->
<!--                        </el-tag>-->
<!--                      </div>-->
                    </div>
                  </el-collapse-transition>
                </div>
                <div class="avatar user-avatar">ME</div>
              </template>
            </div>

            <!-- Loading AI Thinking -->
            <div v-if="showAiThinking" class="message-row ai-row">
              <div class="avatar ai-avatar">AI</div>
              <div class="bubble-wrapper">
                <div class="bubble ai-bubble glass-card thinking-bubble">
                  <div class="dot-flashing"></div>
                  <span class="thinking-text">{{ aiThinkingStatusText }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Dialogue Controller at bottom of left panel -->
          <div class="dialogue-controls glass-panel">
            <!-- Canvas Wave -->
            <div class="wave-container">
              <canvas ref="canvasRef" width="550" height="60" class="wave-canvas"></canvas>
              <div class="wave-overlay-text font-display" v-if="isRecording">正在说话... 请保持麦克风近距离清晰录制</div>
              <div class="wave-overlay-text text-muted font-display" v-else-if="isProcessing">正在上传并执行多阶段口语评测管道</div>
              <div class="wave-overlay-text text-muted font-display" v-else>点击下方麦克风开始录音 🎙️</div>
            </div>

            <div class="control-actions">
              <!-- Rate controller -->
              <div class="rate-controller">
                <span class="label">播放语速:</span>
                <el-radio-group v-model="playbackRate" size="default" @change="changePlaybackRate">
                  <el-radio-button :value="0.8">0.8x</el-radio-button>
                  <el-radio-button :value="1.0">1.0x</el-radio-button>
                  <el-radio-button :value="1.2">1.2x</el-radio-button>
                </el-radio-group>
              </div>

              <!-- Main Mic Button -->
              <div class="mic-button-wrapper">
                <el-button 
                  type="primary" 
                  :class="['mic-btn hover-scale', { 'recording-active': isRecording }]"
                  @click="toggleRecording"
                  :disabled="isProcessing"
                  circle
                >
                  <el-icon v-if="isRecording"><CircleClose /></el-icon>
                  <el-icon v-else><Microphone /></el-icon>
                </el-button>
                <div class="btn-subtext">{{ isRecording ? '点击结束' : '开始录音' }}</div>
              </div>

              <div class="placeholder-action">
                <el-collapse-transition>
                  <div v-if="isRecording" class="cancel-recording-wrapper">
                    <el-button 
                      type="danger" 
                      class="cancel-btn hover-scale"
                      @click="cancelRecording"
                      circle
                    >
                      <el-icon><Delete /></el-icon>
                    </el-button>
                    <div class="btn-subtext danger-text">取消录音</div>
                  </div>
                </el-collapse-transition>
              </div>
            </div>
          </div>
        </template>
      </section>

      <!-- Right side: Evaluation & Feedback Panel -->
      <section class="feedback-panel glass-panel">
        <h3 class="panel-title">发音与语法实时评估</h3>
        
        <div v-if="selectedUserTurn" class="feedback-content" v-loading="selectedUserTurn.isEvaluating" element-loading-text="正在评估发音与语法中..." element-loading-background="rgba(17, 24, 39, 0.7)">
          <!-- Radar Chart container -->
          <div class="radar-section">
            <div class="section-subtitle">发音能力五维雷达图</div>
            <div class="radar-wrapper">
              <EChartsRadar :score-data="selectedUserTurn.pronunciation_score" />
            </div>
            <div class="score-details" v-if="selectedUserTurn.pronunciation_score">
              <div class="score-item">
                <span class="label">发音准确度:</span>
                <span class="value success-text">{{ selectedUserTurn.pronunciation_score.accuracy_score }}分</span>
              </div>
              <div class="score-item">
                <span class="label">表达流利度:</span>
                <span class="value warning-text">{{ selectedUserTurn.pronunciation_score.fluency_score }}分</span>
              </div>
              <div class="score-item">
                <span class="label">发音完整度:</span>
                <span class="value primary-text">{{ selectedUserTurn.pronunciation_score.integrity_score }}分</span>
              </div>
            </div>
          </div>

          <!-- Grammar correction container -->
          <div class="grammar-section" v-if="selectedUserTurn.grammar_correction">
            <div class="section-subtitle">语法及表达优化建议</div>
            <div class="grammar-card glass-card">
              <!-- No error -->
              <div v-if="selectedUserTurn.grammar_correction.original === selectedUserTurn.grammar_correction.corrected" class="grammar-correct-state">
                <el-icon class="correct-icon"><SuccessFilled /></el-icon>
                <p class="correct-desc">{{ selectedUserTurn.grammar_correction.explanation }}</p>
              </div>
              <!-- Has corrections -->
              <div v-else class="grammar-error-state">
                <div class="correction-row">
                  <div class="label-badge label-red">原文 (Original)</div>
                  <p class="correction-text error-text">{{ selectedUserTurn.grammar_correction.original }}</p>
                </div>
                <div class="correction-row">
                  <div class="label-badge label-green">优化 (Polished)</div>
                  <p class="correction-text success-text">{{ selectedUserTurn.grammar_correction.corrected }}</p>
                </div>
                <div class="correction-explanation">
                  <span class="exp-title">修改说明 (Explanation):</span>
                  <p class="exp-content">{{ selectedUserTurn.grammar_correction.explanation }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div v-else class="feedback-empty">
          <el-icon class="feedback-empty-icon"><InfoFilled /></el-icon>
          <p>开启对话并点击你的绿色胶囊语音条，即可在此处展开转文字与发音评估雷达图！</p>
        </div>
      </section>
    </div>

    <!-- Settle Dialog (Larger sizing) -->
    <el-dialog
      v-model="isSettleOpen"
      title="口语练习会话总结报告"
      width="720px"
      class="custom-dialog"
      :show-close="false"
      :close-on-click-modal="false"
      top="5vh"
      @opened="onSettleDialogOpen"
      @closed="onSettleDialogClose"
    >
      <div class="settlement-report" v-if="settlementReport">
        <div class="report-header">
          <div class="score-circle">
            <span class="score-num text-gradient">{{ settlementReport.overall_score }}</span>
            <span class="score-label">平均口语评分</span>
          </div>
          <h3 class="scene-done-name">{{ scene?.name }}</h3>
          <p class="duration">练习时间: {{ formatDuration(settlementReport.start_time, settlementReport.end_time) }}</p>
        </div>

        <!-- 丰富多维数据汇总 -->
        <div class="settle-metrics-grid">
          <div class="metric-card">
            <span class="m-val">{{ turns.filter(t => t.role === 'user').length }} 句</span>
            <span class="m-lbl">练习总句数</span>
          </div>
          <div class="metric-card">
            <span class="m-val primary-text">{{ totalWords }} 字</span>
            <span class="m-lbl">练习发言总词数</span>
          </div>
          <div class="metric-card">
            <span class="m-val success-text">{{ averageScores.accuracy_score }} 分</span>
            <span class="m-lbl">发音准确度</span>
          </div>
          <div class="metric-card">
            <span class="m-val warning-text">{{ averageScores.fluency_score }} 分</span>
            <span class="m-lbl">发音流利度</span>
          </div>
          <div class="metric-card">
            <span class="m-val info-text">{{ averageScores.integrity_score }} 分</span>
            <span class="m-lbl">发音完整度</span>
          </div>
          <div class="metric-card">
            <span class="m-val danger-text">{{ grammarIssuesCount }} 处</span>
            <span class="m-lbl">语法优化建议</span>
          </div>
        </div>

        <!-- 本次最佳发音单句高亮 -->
        <div class="best-turn-highlight" v-if="bestTurn">
          <div class="highlight-title">🌟 本次练习最佳单句发音 ({{ Math.round(bestTurn.pronunciation_score.total_score) }}分)</div>
          <p class="highlight-text">"{{ bestTurn.text }}"</p>
        </div>

        <div class="radar-wrapper-settle">
          <EChartsRadar v-if="settleRadarReady" :score-data="averageScores" height="360px" />
        </div>

        <div class="report-footer-tips">
          <el-icon><Opportunity /></el-icon>
          <p class="tips-text">{{ getEvaluationTips }}</p>
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button type="primary" @click="closeSettleAndGoHome" class="settle-go-home-btn">返回大厅</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAppStore } from '../store/useAppStore'
import EChartsRadar from '../components/EChartsRadar.vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const route = useRoute()
const store = useAppStore()

// State variables
const scene = computed(() => store.currentScene)
const activeParams = computed(() => store.activeParams)
const turns = computed(() => store.dialogueTurns)
const historyId = computed(() => store.activeHistoryId)

const sessionStarted = ref(false)
const startingSession = ref(false)
const isRecording = ref(false)
const isProcessing = ref(false)
const isSettleOpen = ref(false)
const settleRadarReady = ref(false)

const onSettleDialogOpen = () => {
  settleRadarReady.value = true
}

const onSettleDialogClose = () => {
  settleRadarReady.value = false
}

const selectedTurnIndex = ref(null)
// 存储所有 Turn 的展开/折叠状态，键是 turn.id || idx，值为 true 表示展开，false 表示折叠
const expandedTurns = ref({})
// 存储流式数据包的处理提示文案
const processingStatusText = ref('发音评估与思考中...')
const currentBigStatus = ref('上传语音')
const currentPlayfulRemark = ref('正在安全上传您的音频...')

// SSE 实时控制 AI 气泡的展现与文案
const showAiThinking = ref(false)
const aiThinkingStatusText = ref('AI 正在组织语言，撰写角色回复~')

const playbackRate = ref(1.0)
const playingTurnId = ref(null)
const activeAudio = ref(null)

// 跟踪音频播放进度状态
const currentPlaybackTime = ref(0)
const currentPlaybackDuration = ref(0)

const settlementReport = ref(null)
const averageScores = ref({
  total_score: 0,
  accuracy_score: 0,
  fluency_score: 0,
  integrity_score: 0
})

// Web Audio API & Canvas state
const canvasRef = ref(null)
const chatHistoryRef = ref(null)
const phase = ref(0)
let waveAnimationId = null
let audioContext = null
let scriptProcessor = null
let mediaStreamSource = null
let audioStream = null
let leftchannel = []
let recordingLength = 0
let analyser = null

// Check if a temporary user bubble is currently processing
const hasTempUserBubble = computed(() => {
  return turns.value.some(t => t.isTemp)
})

// Select user turn for details
const selectedUserTurn = computed(() => {
  if (selectedTurnIndex.value === null) return null
  const turn = turns.value[selectedTurnIndex.value]
  return turn && turn.role === 'user' && !turn.isTemp ? turn : null
})

// 计算发言总词数
const totalWords = computed(() => {
  const userTurns = turns.value.filter(t => t.role === 'user' && !t.isTemp)
  let count = 0
  userTurns.forEach(t => {
    if (t.text) {
      count += t.text.split(/\s+/).filter(Boolean).length
    }
  })
  return count
})

// 根据总结报告评分给出段位评价
const getEvaluationTips = computed(() => {
  const score = averageScores.value.total_score || 0
  if (score >= 85) {
    return '口语大师 (Oral Master)！在本次练习中，你的发音流利度和准确度均达到了极高水准。你表现得非常完美，请继续保持这股学习劲头，迎接更多挑战！'
  } else if (score >= 70) {
    return '口语良才 (Good Speaker)！你的发音和表达基础非常扎实。可以尝试在接下来的对话中更多关注词汇连读与流利度，多做跟读练习，工作与社交上将更加游刃有余！'
  } else {
    return '口语新星 (Rising Star)！你的表达十分勇敢，这是学好英语口语最重要的一步。建议根据AI给出的口音分析，多回放并修正单句发音，加油！'
  }
})

// 播放原音并且选中本行进行详细分析
const selectAndPlayUserTurn = (idx, turn) => {
  selectedTurnIndex.value = idx
  playAudio(turn.audio_url, turn.id || idx)
}

// 仅选中本行，不重新播报原音
const selectUserTurnOnly = (idx) => {
  selectedTurnIndex.value = idx
}

// 计算语音胶囊的宽度，时长越长气泡越长
const getCapsuleWidth = (turn) => {
  let seconds = 3
  if (turn.recordingDuration) {
    seconds = turn.recordingDuration
  } else if (turn.text) {
    const words = turn.text.split(' ').length
    seconds = Math.max(2, Math.round(words / 2))
  }
  // 时长每多一秒，宽度加 9px，范围限制在 120px 到 320px
  const width = Math.min(320, Math.max(120, 110 + seconds * 9))
  return `${width}px`
}

// 获取以秒为单位的语音时长
const getWavDurationSeconds = (turn) => {
  if (turn.recordingDuration) return turn.recordingDuration
  if (turn.text) {
    const words = turn.text.split(' ').length
    return Math.max(2, Math.round(words / 2))
  }
  return 3
}

// Lifecycle
onMounted(async () => {
  if (!store.currentScene && route.params.sceneId) {
    try {
      const res = await axios.get(`${store.backendBaseUrl}/api/scenes/${route.params.sceneId}`)
      store.setCurrentScene(res.data)
    } catch (err) {
      ElMessage.error('加载场景失败，将返回大厅')
      router.push('/')
    }
  }
  
  if (!store.currentScene) {
    router.push('/')
  }
})

onUnmounted(() => {
  stopAudio()
  stopRecordingResources()
  if (waveAnimationId) {
    cancelAnimationFrame(waveAnimationId)
  }
})

// Go back home
const goHome = () => {
  if (sessionStarted.value && turns.value.length > 1) { // 剔除了欢迎语的第一轮
    ElMessageBox.confirm(
      '确定退出当前场景吗？未结算的练习将不会记录平均发音总分。',
      '提示',
      {
        confirmButtonText: '确定退出',
        cancelButtonText: '取消',
        type: 'warning'
      }
    ).then(() => {
      store.clearActiveSession()
      router.push('/')
    }).catch(() => {})
  } else {
    store.clearActiveSession()
    router.push('/')
  }
}

// Start new dialogue session
const startDialogueSession = async () => {
  if (!scene.value) return
  startingSession.value = true
  
  try {
    // 1. 获取用户所有的历史会话
    const res = await axios.get(`${store.backendBaseUrl}/api/dialogues/?user_id=1`)
    const historyList = res.data
    
    // 2. 查找本场景下未结算的会话 (end_time 为 null)
    const unsettled = historyList.find(
      h => h.scene_id === scene.value.id && h.end_time === null
    )
    
    if (unsettled) {
      startingSession.value = false // 暂停 loading 以便用户操作弹窗
      
      ElMessageBox.confirm(
        '检测到您在该场景下有未完成的练习，是否继续上一次的对话？',
        '恢复上次练习',
        {
          confirmButtonText: '继续上次练习',
          cancelButtonText: '开始新练习',
          type: 'info',
          distinguishCancelAndClose: true
        }
      ).then(() => {
        // 用户选择继续上次练习
        resumeDialogueSession(unsettled.id)
      }).catch((action) => {
        if (action === 'cancel') {
          // 用户选择开始新练习
          startNewDialogueSession()
        }
      })
    } else {
      // 没有未结算的会话，直接创建新练习
      await startNewDialogueSession()
    }
  } catch (err) {
    console.error('检查未结算会话失败:', err)
    // 降级：直接创建新会话
    await startNewDialogueSession()
  } finally {
    startingSession.value = false
  }
}

// 恢复上次练习会话
const resumeDialogueSession = async (historyId) => {
  startingSession.value = true
  try {
    const res = await axios.get(`${store.backendBaseUrl}/api/dialogues/${historyId}`)
    
    // 载入历史记录数据
    store.setActiveHistoryId(res.data.id)
    sessionStarted.value = true
    
    if (res.data.turns && res.data.turns.length > 0) {
      res.data.turns.forEach(turn => {
        store.addDialogueTurn(turn)
      })
    }
    
    ElMessage.success('成功恢复上一次的练习会话！')
    
    nextTick(() => {
      drawWave()
      scrollToBottom()
    })
  } catch (err) {
    ElMessage.error('恢复会话失败，将为您开启新练习')
    await startNewDialogueSession()
  } finally {
    startingSession.value = false
  }
}

// 开启新练习的独立逻辑
const startNewDialogueSession = async () => {
  startingSession.value = true
  try {
    const res = await axios.post(`${store.backendBaseUrl}/api/dialogues/start`, {
      user_id: 1, // 默认 ID=1 预注册用户
      scene_id: scene.value.id,
      custom_params: activeParams.value
    })
    
    store.setActiveHistoryId(res.data.id)
    sessionStarted.value = true
    
    if (res.data.turns && res.data.turns.length > 0) {
      res.data.turns.forEach(turn => {
        store.addDialogueTurn(turn)
      })
      
      // 自动播放 AI 问候语语音
      const greetingTurn = res.data.turns[0]
      if (greetingTurn.audio_url) {
        nextTick(() => {
          playAudio(greetingTurn.audio_url, 0)
        })
      }
    }
    
    nextTick(() => {
      drawWave()
    })
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '启动口语练习会话失败，请确保后端服务已开启并且数据库已经重置更新')
  } finally {
    startingSession.value = false
  }
}

// Recording controls
const toggleRecording = () => {
  if (isRecording.value) {
    finishRecordingAndUpload()
  } else {
    startRecording()
  }
}

const cancelRecording = () => {
  stopRecordingResources()
  leftchannel = []
  recordingLength = 0
  ElMessage.info('已取消本次录音')
}

const startRecording = async () => {
  try {
    stopAudio()
    leftchannel = []
    recordingLength = 0
    
    audioStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    
    const AudioContextClass = window.AudioContext || window.webkitAudioContext
    audioContext = new AudioContextClass({ sampleRate: 16000 })
    
    analyser = audioContext.createAnalyser()
    analyser.fftSize = 256
    
    mediaStreamSource = audioContext.createMediaStreamSource(audioStream)
    mediaStreamSource.connect(analyser)
    
    scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1)
    mediaStreamSource.connect(scriptProcessor)
    scriptProcessor.connect(audioContext.destination)
    
    scriptProcessor.onaudioprocess = (e) => {
      if (!isRecording.value) return
      const samples = e.inputBuffer.getChannelData(0)
      leftchannel.push(new Float32Array(samples))
      recordingLength += samples.length
    }
    
    isRecording.value = true
  } catch (err) {
    console.error('麦克风采集故障:', err)
    ElMessage.error('无法启用麦克风设备，请检查应用麦克风系统权限')
    stopRecordingResources()
  }
}

const finishRecordingAndUpload = async () => {
  if (!isRecording.value) return
  isRecording.value = false
  isProcessing.value = true
  currentBigStatus.value = '上传语音'
  currentPlayfulRemark.value = '正在安全上传您的音频...'
  
  // 计算录音秒数
  const durationSec = Math.max(1, Math.round(recordingLength / 16000))
  
  // 创建本地临时加载气泡
  const tempTurnId = 'temp_' + Date.now()
  const tempBubble = {
    id: tempTurnId,
    role: 'user',
    text: '',
    audio_url: null,
    isTemp: true,
    isEvaluating: false,
    evaluationStatusText: '正在认真聆听您说了什么~',
    recordingDuration: durationSec
  }
  store.addDialogueTurn(tempBubble)
  scrollToBottom()
  
  showAiThinking.value = false
  
  try {
    const mergedBuffer = mergeBuffers(leftchannel, recordingLength)
    const currentSampleRate = audioContext ? audioContext.sampleRate : 16000
    
    let finalSamples = mergedBuffer
    if (currentSampleRate !== 16000) {
      finalSamples = downsampleBuffer(mergedBuffer, currentSampleRate, 16000)
    }
    
    const wavBlob = encodeWAV(finalSamples, 16000)
    const localAudioUrl = URL.createObjectURL(wavBlob)
    
    // 更新临时气泡的音频播放 URL，允许用户在评估未完成前点击播放自己的录音
    const tempIdx = store.dialogueTurns.findIndex(t => t.id === tempTurnId)
    if (tempIdx !== -1) {
      store.dialogueTurns[tempIdx].audio_url = localAudioUrl
    }

    const audioFile = new File([wavBlob], 'recording.wav', { type: 'audio/wav' })
    
    const formData = new FormData()
    formData.append('file', audioFile)
    
    stopRecordingResources()
    
    // 改用原生 fetch 方式请求后端以消费 Server-Sent Events (SSE) 流式响应
    // 传递 stream=true Query 参数以启用后端分阶段推送
    const streamUrl = `${store.backendBaseUrl}/api/dialogues/${historyId.value}/turn?stream=true`
    
    const response = await fetch(streamUrl, {
      method: 'POST',
      body: formData
    })
    
    if (!response.ok) {
      throw new Error(`HTTP 异常状态码: ${response.status}`)
    }
    
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop()
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6).trim()
          if (!dataStr) continue
          
          try {
            const data = JSON.parse(dataStr)
            
            if (data.status === 'asr') {
              processingStatusText.value = '正在认真聆听您说了什么~'
              currentBigStatus.value = '语音解析'
              currentPlayfulRemark.value = '正在认真聆听您说了什么~'
              const idx = store.dialogueTurns.findIndex(t => t.id === tempTurnId)
              if (idx !== -1) {
                store.dialogueTurns[idx].evaluationStatusText = '正在认真聆听您说了什么~'
              }
            } else if (data.status === 'asr_done') {
              // ASR 转译完毕，提前在用户加载气泡上呈现转译出的英文文本，并变绿正常渲染，同时设定为口音评测中
              currentBigStatus.value = '安全检测'
              currentPlayfulRemark.value = '转译成功，准备开始分析~'
              const idx = store.dialogueTurns.findIndex(t => t.id === tempTurnId)
              if (idx !== -1) {
                store.dialogueTurns[idx].text = data.text
                store.dialogueTurns[idx].isTemp = false // 转为绿色气泡，用户体验连贯
                store.dialogueTurns[idx].isEvaluating = true
                store.dialogueTurns[idx].evaluationStatusText = '转译成功，开始发音与隐私分析~'
                
                // 自动选中并平滑展开文本
                selectedTurnIndex.value = idx
                expandedTurns.value[tempTurnId] = true
              }
              scrollToBottom()
            } else if (data.status === 'pii') {
              processingStatusText.value = '正在保护您的隐私，进行敏感信息脱敏~'
              currentBigStatus.value = '隐私保护'
              currentPlayfulRemark.value = '正在保护您的隐私，进行敏感信息脱敏~'
              const idx = store.dialogueTurns.findIndex(t => t.id === tempTurnId || t.text === data.text)
              if (idx !== -1) {
                store.dialogueTurns[idx].isEvaluating = true
                store.dialogueTurns[idx].evaluationStatusText = '正在保护您的隐私，进行敏感信息脱敏~'
              }
            } else if (data.status === 'ise') {
              processingStatusText.value = '正在检测您的口音，分析发音表现~'
              currentBigStatus.value = '口音分析'
              currentPlayfulRemark.value = '正在检测您的口音，分析发音表现~'
              const idx = store.dialogueTurns.findIndex(t => t.id === tempTurnId || t.text === data.text)
              if (idx !== -1) {
                store.dialogueTurns[idx].isEvaluating = true
                store.dialogueTurns[idx].evaluationStatusText = '正在检测您的口音，分析发音表现~'
              }
            } else if (data.status === 'llm') {
              // 口语分析结束，开启 AI 气泡展示
              processingStatusText.value = 'AI 正在组织语言，撰写角色回复~'
              currentBigStatus.value = '生成回复'
              currentPlayfulRemark.value = 'AI 正在组织语言，撰写角色回复~'
              const idx = store.dialogueTurns.findIndex(t => t.id === tempTurnId || t.text === data.text)
              if (idx !== -1) {
                store.dialogueTurns[idx].isEvaluating = false
              }
              showAiThinking.value = true
              aiThinkingStatusText.value = '正在组织语言，撰写角色回复~'
              scrollToBottom()
            } else if (data.status === 'done') {
              const [userTurn, aiTurn] = data.result
              userTurn.recordingDuration = durationSec
              
              const tempIdx = store.dialogueTurns.findIndex(t => t.id === tempTurnId || t.text === userTurn.text)
              if (tempIdx !== -1) {
                store.dialogueTurns.splice(tempIdx, 1)
              }
              
              store.addDialogueTurn(userTurn)
              store.addDialogueTurn(aiTurn)
              
              showAiThinking.value = false
              
              const lastUserIdx = turns.value.length - 2
              selectedTurnIndex.value = lastUserIdx >= 0 ? lastUserIdx : null
              if (lastUserIdx >= 0) {
                const lastUserTurn = turns.value[lastUserIdx]
                expandedTurns.value[lastUserTurn.id || lastUserIdx] = true
              }
              
              scrollToBottom()
              
              if (aiTurn.audio_url) {
                playAudio(aiTurn.audio_url, turns.value.length - 1)
              }
            } else if (data.status === 'error') {
              throw new Error(data.detail || '流式管道异常')
            }
          } catch (err) {
            console.error('流式包解析异常:', err)
          }
        }
      }
    }
  } catch (err) {
    console.error('音频转译与流式 Pipeline 交互故障:', err)
    ElMessage.error(err.message || '转译发音评估失败，请重试')
    const tempIdx = store.dialogueTurns.findIndex(t => t.id === tempTurnId)
    if (tempIdx !== -1) {
      store.dialogueTurns.splice(tempIdx, 1)
    }
  } finally {
    isProcessing.value = false
    showAiThinking.value = false
    processingStatusText.value = '发音评估与思考中...'
  }
}

const stopRecordingResources = () => {
  if (scriptProcessor) {
    scriptProcessor.disconnect()
    scriptProcessor = null
  }
  if (mediaStreamSource) {
    mediaStreamSource.disconnect()
    mediaStreamSource = null
  }
  if (audioStream) {
    audioStream.getTracks().forEach(track => track.stop())
    audioStream = null
  }
  if (audioContext) {
    audioContext.close()
    audioContext = null
  }
  isRecording.value = false
}

// Float32 array merging
const mergeBuffers = (buffers, length) => {
  const result = new Float32Array(length)
  let offset = 0
  for (let i = 0; i < buffers.length; i++) {
    result.set(buffers[i], offset)
    offset += buffers[i].length
  }
  return result
}

// Resampling down to 16kHz
const downsampleBuffer = (buffer, rate, imageSampleRate) => {
  if (rate === imageSampleRate) return buffer
  const sampleRateRatio = rate / imageSampleRate
  const newLength = Math.round(buffer.length / sampleRateRatio)
  const result = new Float32Array(newLength)
  let offsetResult = 0
  let offsetBuffer = 0
  
  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio)
    let accum = 0
    let count = 0
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
      accum += buffer[i]
      count++
    }
    result[offsetResult] = count > 0 ? accum / count : 0
    offsetResult++
    offsetBuffer = nextOffsetBuffer
  }
  return result
}

// Encode to Wav Format
const encodeWAV = (samples, sampleRate) => {
  const buffer = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(buffer)
  
  const writeString = (v, offset, str) => {
    for (let i = 0; i < str.length; i++) {
      v.setUint8(offset + i, str.charCodeAt(i))
    }
  }
  
  writeString(view, 0, 'RIFF')
  view.setUint32(4, 36 + samples.length * 2, true)
  writeString(view, 8, 'WAVE')
  writeString(view, 12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeString(view, 36, 'data')
  view.setUint32(40, samples.length * 2, true)
  
  let offset = 44
  for (let i = 0; i < samples.length; i++, offset += 2) {
    let s = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true)
  }
  
  return new Blob([view], { type: 'audio/wav' })
}

// Canvas wave drawing
const drawWave = () => {
  if (!canvasRef.value) return
  const canvas = canvasRef.value
  const ctx = canvas.getContext('2d')
  const width = canvas.width
  const height = canvas.height
  
  ctx.clearRect(0, 0, width, height)
  
  let amplitude = 6
  if (isRecording.value && analyser) {
    const dataArray = new Uint8Array(analyser.frequencyBinCount)
    analyser.getByteTimeDomainData(dataArray)
    
    let sum = 0
    for (let i = 0; i < dataArray.length; i++) {
      const v = (dataArray[i] - 128) / 128
      sum += v * v
    }
    const rms = Math.sqrt(sum / dataArray.length)
    amplitude = Math.max(6, rms * 150)
  }
  
  phase.value += 0.08
  
  const waves = [
    { color: 'rgba(99, 102, 241, 0.45)', speed: 0.08, noise: 1.0, phaseOffset: 0 },
    { color: 'rgba(59, 130, 246, 0.35)', speed: -0.06, noise: 0.8, phaseOffset: Math.PI / 3 },
    { color: 'rgba(16, 185, 129, 0.25)', speed: 0.1, noise: 0.6, phaseOffset: Math.PI / 1.5 }
  ]
  
  ctx.globalCompositeOperation = 'screen'
  
  waves.forEach(w => {
    ctx.beginPath()
    ctx.strokeStyle = w.color
    ctx.lineWidth = w === waves[0] ? 2.5 : 1.5
    
    for (let x = 0; x < width; x++) {
      const scaling = Math.sin((x / width) * Math.PI)
      const y = height / 2 + scaling * amplitude * w.noise * Math.sin(x * 0.02 + phase.value * (w.speed > 0 ? 1 : -1) + w.phaseOffset)
      
      if (x === 0) {
        ctx.moveTo(x, y)
      } else {
        ctx.lineTo(x, y)
      }
    }
    ctx.stroke()
  })
  
  waveAnimationId = requestAnimationFrame(drawWave)
}

// Audio player management
const playAudio = (url, turnId) => {
  const isSame = (playingTurnId.value === turnId)
  stopAudio()
  
  if (isSame) {
    return
  }
  
  if (!url) {
    ElMessage.info('当前播放链接失效或本轮次无合成语音。')
    return
  }
  
  let fullUrl = url
  if (!url.startsWith('http') && !url.startsWith('blob:')) {
    fullUrl = `${store.backendBaseUrl}${url}`
  }
  
  const audio = new Audio(fullUrl)
  audio.playbackRate = playbackRate.value
  
  currentPlaybackTime.value = 0
  currentPlaybackDuration.value = 0
  
  audio.ontimeupdate = () => {
    currentPlaybackTime.value = audio.currentTime
    if (audio.duration && !isNaN(audio.duration)) {
      currentPlaybackDuration.value = audio.duration
    }
  }
  
  audio.onloadedmetadata = () => {
    if (audio.duration && !isNaN(audio.duration)) {
      currentPlaybackDuration.value = audio.duration
    }
  }
  
  audio.onended = () => {
    playingTurnId.value = null
    activeAudio.value = null
    currentPlaybackTime.value = 0
    currentPlaybackDuration.value = 0
  }
  
  audio.onerror = () => {
    ElMessage.error('音频加载播放失败，可能已被云端清空')
    playingTurnId.value = null
    activeAudio.value = null
    currentPlaybackTime.value = 0
    currentPlaybackDuration.value = 0
  }
  
  playingTurnId.value = turnId
  activeAudio.value = audio
  audio.play()
}

const stopAudio = () => {
  if (activeAudio.value) {
    activeAudio.value.pause()
    activeAudio.value = null
  }
  playingTurnId.value = null
  currentPlaybackTime.value = 0
  currentPlaybackDuration.value = 0
}

const changePlaybackRate = (val) => {
  playbackRate.value = val
  if (activeAudio.value) {
    activeAudio.value.playbackRate = val
  }
}

// Chat scroll helper
const scrollToBottom = () => {
  nextTick(() => {
    if (chatHistoryRef.value) {
      chatHistoryRef.value.scrollTo({
        top: chatHistoryRef.value.scrollHeight,
        behavior: 'smooth'
      })
    }
  })
}

// 切换任意 Turn (包括 AI 和用户消息) 的展开/折叠状态的通用处理函数
const toggleTurnExpanded = (idx, turn) => {
  const key = turn.id || idx
  expandedTurns.value[key] = !expandedTurns.value[key]
  
  // 如果展开的是用户本人的正式消息，则需要在右侧评测面板中同步选中展示
  if (turn.role === 'user' && !turn.isTemp) {
    if (expandedTurns.value[key]) {
      selectedTurnIndex.value = idx
    } else {
      if (selectedTurnIndex.value === idx) {
        selectedTurnIndex.value = null
      }
    }
  }
}

// Settle session
const handleSettle = () => {
  ElMessageBox.confirm(
    '确定结束当前场景并生成结算成绩报告吗？',
    '结算提示',
    {
      confirmButtonText: '确定结算',
      cancelButtonText: '继续练习',
      type: 'success'
    }
  ).then(async () => {
    try {
      const res = await axios.post(`${store.backendBaseUrl}/api/dialogues/${historyId.value}/settle`)
      settlementReport.value = res.data
      
      calculateAverageScores()
      isSettleOpen.value = true
    } catch (err) {
      ElMessage.error('结算对话失败，请检查连接')
    }
  }).catch(() => {})
}

const calculateAverageScores = () => {
  const userTurns = turns.value.filter(t => t.role === 'user' && t.pronunciation_score)
  if (userTurns.length === 0) return
  
  let acc = 0, flu = 0, inte = 0, tot = 0
  userTurns.forEach(t => {
    acc += t.pronunciation_score.accuracy_score || 0
    flu += t.pronunciation_score.fluency_score || 0
    inte += t.pronunciation_score.integrity_score || 0
    tot += t.pronunciation_score.total_score || 0
  })
  
  averageScores.value = {
    total_score: Math.round(tot / userTurns.length),
    accuracy_score: Math.round(acc / userTurns.length),
    fluency_score: Math.round(flu / userTurns.length),
    integrity_score: Math.round(inte / userTurns.length),
    grammar_score: Math.round(tot / userTurns.length)
  }
}

// 统计语法建议总数
const grammarIssuesCount = computed(() => {
  const userTurns = turns.value.filter(t => t.role === 'user' && t.grammar_correction)
  let count = 0
  userTurns.forEach(t => {
    if (t.grammar_correction.original !== t.grammar_correction.corrected) {
      count++
    }
  })
  return count
})

// 查找最佳单句发音
const bestTurn = computed(() => {
  const userTurns = turns.value.filter(t => t.role === 'user' && t.pronunciation_score)
  if (userTurns.length === 0) return null
  let maxScore = -1
  let best = null
  userTurns.forEach(t => {
    const score = t.pronunciation_score.total_score || 0
    if (score > maxScore) {
      maxScore = score
      best = t
    }
  })
  return best
})

// 根据不同的参数 key 渲染亮丽的多彩背景与边框主题样式
const getParamTagClass = (key) => {
  const keyLower = String(key).toLowerCase()
  if (keyLower.includes('company')) return 'tag-blue'
  if (keyLower.includes('topic') || keyLower.includes('issue')) return 'tag-purple'
  if (keyLower.includes('personality') || keyLower.includes('character')) return 'tag-orange'
  if (keyLower.includes('name') || keyLower.includes('interviewer')) return 'tag-green'
  return 'tag-default'
}

const closeSettleAndGoHome = () => {
  isSettleOpen.value = false
  store.clearActiveSession()
  router.push('/')
}

// Utility formatting helpers
const formatCategory = (category) => {
  const mapping = {
    interview: '职场面试',
    ordering: '日常点餐',
    meeting: '商务会议',
    custom: '自定义练习'
  }
  return mapping[category] || '练习场景'
}

const translateKey = (key) => {
  const mapping = {
    personality: '性格/特质',
    company_name: '公司',
    job_title: '面试岗位',
    interviewer_name: '面试官',
    store_name: '店铺',
    cashier_name: '服务员',
    chairperson_name: '主持人',
    topic: '会议议题',
    character_name: '角色名称'
  }
  return mapping[key] || key
}

const formatDuration = (start, end) => {
  if (!start || !end) return '未知'
  try {
    const s = new Date(start)
    const e = new Date(end)
    const diffMs = Math.abs(e - s)
    const diffSec = Math.floor(diffMs / 1000)
    const min = Math.floor(diffSec / 60)
    const sec = diffSec % 60
    return `${min}分${sec}秒`
  } catch {
    return '1分24秒'
  }
}

// Calculate audio duration dynamically for UI display
const getWavDuration = (turn) => {
  if (turn.recordingDuration) return `${turn.recordingDuration}"`
  // 简易自适应估算，1s录音大概对应 1.5 - 2.5 个单词
  if (turn.text) {
    const words = turn.text.split(' ').length
    const est = Math.max(2, Math.round(words / 2))
    return `${est}"`
  }
  return '3"'
}
</script>

<style scoped>
.practice-layout {
  padding: 16px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-color);
  gap: 16px;
}

/* Header styling */
.practice-header {
  min-height: 85px;
  height: auto;
  padding: 16px 28px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-btn {
  color: var(--text-secondary) !important;
  font-size: 1.05rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 4px;
}

.back-btn:hover {
  color: var(--primary-color) !important;
}

.divider {
  width: 1px;
  height: 28px;
  background-color: rgba(255, 255, 255, 0.08);
}

.scene-meta {
  display: flex;
  flex-direction: column;
}

.scene-title {
  font-size: 1.85rem;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.scene-desc {
  font-size: 1.05rem;
  color: var(--text-muted);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.active-params {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-width: 650px;
  overflow-y: auto;
  justify-content: flex-end;
}

.param-tag {
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 0.88rem;
  white-space: nowrap;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.param-tag .key {
  color: var(--text-muted);
  margin-right: 4px;
}

.param-tag .val {
  color: var(--text-secondary);
  font-weight: 600;
}

/* 多彩提示参数药丸样式 */
.tag-blue {
  background: rgba(59, 130, 246, 0.2) !important;
  border: 1px solid rgba(59, 130, 246, 0.45) !important;
  color: #a5f3fc !important;
}
.tag-purple {
  background: rgba(168, 85, 247, 0.2) !important;
  border: 1px solid rgba(168, 85, 247, 0.45) !important;
  color: #e9d5ff !important;
}
.tag-orange {
  background: rgba(249, 115, 22, 0.2) !important;
  border: 1px solid rgba(249, 115, 22, 0.45) !important;
  color: #ffedd5 !important;
}
.tag-green {
  background: rgba(16, 185, 129, 0.2) !important;
  border: 1px solid rgba(16, 185, 129, 0.45) !important;
  color: #d1fae5 !important;
}
.tag-default {
  background: rgba(255, 255, 255, 0.06) !important;
  border: 1px solid rgba(255, 255, 255, 0.12) !important;
  color: var(--text-secondary) !important;
}

.settle-btn {
  background: linear-gradient(135deg, var(--danger-color) 0%, #b91c1c 100%) !important;
  border: none !important;
  font-weight: 600;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.2);
}

.settle-btn:disabled,
.settle-btn.is-disabled {
  background: rgba(255, 255, 255, 0.08) !important;
  border: 1px solid rgba(255, 255, 255, 0.05) !important;
  color: var(--text-muted) !important;
  box-shadow: none !important;
  opacity: 0.35 !important;
  cursor: not-allowed !important;
}

/* Grid layout with adjusted desktop proportions (72% and 28%) */
.practice-grid {
  display: flex;
  flex-grow: 1;
  gap: 16px;
  overflow: hidden;
  height: calc(100vh - 118px);
}

/* Dialogue Box (72%) */
.dialogue-box {
  width: 72%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.start-session-prompt {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  padding: 40px;
}

.prompt-icon {
  font-size: 4rem;
  color: var(--primary-color);
  margin-bottom: 20px;
  filter: drop-shadow(0 0 10px rgba(99, 102, 241, 0.4));
}

.start-session-prompt h3 {
  font-size: 1.4rem;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.start-session-prompt p {
  font-size: 0.9rem;
  color: var(--text-secondary);
  max-width: 450px;
  line-height: 1.6;
  margin-bottom: 30px;
}

.start-session-btn {
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%) !important;
  border: none !important;
  font-weight: 600;
  padding: 14px 32px;
  font-size: 1rem;
  border-radius: 8px;
}

.chat-history {
  flex-grow: 1;
  padding: 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.message-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
}

.user-row {
  justify-content: flex-end;
}

.user-row .bubble-wrapper {
  align-items: flex-end;
}

.user-row .bubble-row {
  justify-content: flex-end;
}

.ai-row {
  justify-content: flex-start;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 700;
  flex-shrink: 0;
  margin-top: 4px;
}

.ai-avatar {
  background: var(--primary-color);
  color: #fff;
  box-shadow: 0 0 10px rgba(99, 102, 241, 0.4);
}

.user-avatar {
  background: var(--accent-color);
  color: #fff;
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.4);
}

.bubble-wrapper {
  max-width: 72%;
  display: flex;
  flex-direction: column;
  cursor: pointer;
}

/* WeChat Style Voice Capsule */
.voice-capsule {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 100px;
  height: 40px;
  padding: 0 16px;
  background: linear-gradient(135deg, #059669 0%, #10b981 100%) !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  box-shadow: 0 4px 10px rgba(16, 185, 129, 0.25);
  color: #fff;
  transition: var(--transition-smooth);
  border-top-right-radius: 2px;
  position: relative;
  overflow: hidden;
}

/* 语音播放进度条 */
.voice-capsule-progress-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 3px;
  background-color: rgba(255, 255, 255, 0.65);
  box-shadow: 0 0 4px rgba(255, 255, 255, 0.8);
  transition: width 0.1s linear;
}

.voice-capsule:hover {
  transform: scale(1.03);
  box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
}

.temp-capsule {
  background: linear-gradient(135deg, #4b5563 0%, #6b7280 100%) !important;
  box-shadow: 0 4px 10px rgba(107, 114, 128, 0.25);
  cursor: pointer;
}

.temp-capsule:hover {
  background: linear-gradient(135deg, #4b5563 0%, #6b7280 100%) !important;
  box-shadow: 0 4px 15px rgba(107, 114, 128, 0.5) !important;
}

.ai-voice-capsule {
  background: linear-gradient(135deg, #374151 0%, #4b5563 100%) !important;
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
  border-top-right-radius: 20px !important;
  border-top-left-radius: 2px !important;
}

.ai-voice-capsule:hover {
  background: linear-gradient(135deg, #4b5563 0%, #6b7280 100%) !important;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.35);
}

.voice-playing-text {
  font-size: 0.72rem;
  background: rgba(255, 255, 255, 0.15);
  padding: 1px 6px;
  border-radius: 10px;
  margin-left: auto;
  font-weight: bold;
  color: #818cf8;
}

.voice-icon {
  font-size: 1.1rem;
}

.voice-icon-spinning {
  font-size: 1.1rem;
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.voice-duration {
  font-size: 0.85rem;
  font-weight: 700;
  font-family: var(--font-display);
}

.voice-capsule-score {
  font-size: 0.72rem;
  background: rgba(255, 255, 255, 0.25);
  padding: 1px 6px;
  border-radius: 10px;
  margin-left: auto;
  font-weight: bold;
}

.voice-capsule-score-loading {
  font-size: 0.7rem;
  background: rgba(251, 191, 36, 0.25);
  color: #fbbf24;
  padding: 1px 6px;
  border-radius: 10px;
  margin-left: auto;
  font-weight: bold;
  display: flex;
  align-items: center;
  gap: 4px;
}

/* Bubble style when expanded */
.bubble {
  padding: 12px 18px;
  border-radius: 14px;
  position: relative;
  transition: var(--transition-smooth);
}

.ai-bubble {
  background: rgba(31, 41, 55, 0.5) !important;
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-top-left-radius: 2px;
}

.user-bubble {
  background: rgba(99, 102, 241, 0.12) !important;
  border: 1px solid rgba(99, 102, 241, 0.25);
  border-top-right-radius: 2px;
}

.selected-bubble {
  border-color: var(--primary-color) !important;
  box-shadow: 0 0 16px rgba(99, 102, 241, 0.35);
  background: rgba(99, 102, 241, 0.18) !important;
}

.bubble-wrapper.is-selected .voice-capsule {
  box-shadow: 0 0 14px rgba(16, 185, 129, 0.45);
  border-color: rgba(16, 185, 129, 0.6) !important;
}

.message-text {
  font-size: 0.95rem;
  line-height: 1.55;
  color: var(--text-primary);
  word-wrap: break-word;
  white-space: pre-wrap;
}

.bubble-actions {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
}

.bubble-actions-user {
  margin-top: 10px;
  border-top: 1px dashed rgba(255, 255, 255, 0.08);
  padding-top: 8px;
  display: flex;
  justify-content: flex-end;
}

.audio-play-btn {
  color: #818cf8 !important;
  font-size: 0.8rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
}

.user-audio-play-btn {
  color: #a7f3d0 !important;
  font-size: 0.78rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
}

.bubble-score {
  position: absolute;
  bottom: -10px;
  right: 12px;
}

.score-tag {
  background-color: var(--accent-color) !important;
  border: none !important;
  font-weight: 700;
  font-family: var(--font-display);
}

.bubble-tips {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-align: right;
  margin-top: 4px;
  padding-right: 4px;
  opacity: 0.4;
  transition: var(--transition-smooth);
}

.bubble-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.translate-toggle-btn,
.translate-toggle-btn-user {
  font-size: 0.8rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px !important;
  height: auto !important;
  border-radius: 6px !important;
  background: rgba(255, 255, 255, 0.03) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  transition: var(--transition-smooth);
}

.translate-toggle-btn {
  color: #818cf8 !important;
}

.translate-toggle-btn:hover {
  background: rgba(129, 140, 248, 0.1) !important;
  border-color: rgba(129, 140, 248, 0.3) !important;
}

.translate-toggle-btn-user {
  color: #34d399 !important;
}

.translate-toggle-btn-user:hover {
  background: rgba(52, 211, 153, 0.1) !important;
  border-color: rgba(52, 211, 153, 0.3) !important;
}

.evaluating-status-text {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  color: #fbbf24;
  margin-top: 8px;
  background: rgba(251, 191, 36, 0.06);
  border: 1px dashed rgba(251, 191, 36, 0.2);
  padding: 6px 10px;
  border-radius: 6px;
}

/* 微信式胶囊下方滑动滑出的解析面板 */
.bubble-translation-panel {
  margin-top: 8px;
  width: 100%;
  padding: 14px 18px;
  box-sizing: border-box;
}

.temp-text-bubble {
  background: rgba(255, 255, 255, 0.02) !important;
  border: 1px dashed rgba(255, 255, 255, 0.1) !important;
  border-radius: 12px;
  padding: 10px 14px !important;
  margin-bottom: 8px;
}

.bubble-tips-always {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-align: right;
  margin-top: 4px;
  padding-right: 4px;
  opacity: 0.8;
}

/* Thinking Bubble */
.thinking-bubble {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(31, 41, 55, 0.3) !important;
  padding: 14px 20px;
}

.thinking-text {
  font-size: 0.85rem;
  color: var(--text-muted);
}

.dot-flashing {
  position: relative;
  width: 8px;
  height: 8px;
  border-radius: 5px;
  background-color: var(--primary-color);
  color: var(--primary-color);
  animation: dotFlashing 1s infinite linear alternate;
  animation-delay: .5s;
  display: inline-block;
  margin-right: 20px;
  margin-left: 8px;
}
.dot-flashing::before, .dot-flashing::after {
  content: '';
  display: inline-block;
  position: absolute;
  top: 0;
}
.dot-flashing::before {
  left: -12px;
  width: 8px;
  height: 8px;
  border-radius: 5px;
  background-color: var(--primary-color);
  color: var(--primary-color);
  animation: dotFlashing 1s infinite linear alternate;
  animation-delay: 0s;
}
.dot-flashing::after {
  left: 12px;
  width: 8px;
  height: 8px;
  border-radius: 5px;
  background-color: var(--primary-color);
  color: var(--primary-color);
  animation: dotFlashing 1s infinite linear alternate;
  animation-delay: 1s;
}

@keyframes dotFlashing {
  0% {
    background-color: var(--primary-color);
  }
  50%, 100% {
    background-color: rgba(99, 102, 241, 0.15);
  }
}

/* Controls Box (magnified height and grid centered) */
.dialogue-controls {
  height: 205px;
  margin: 16px;
  background: rgba(17, 24, 39, 0.8) !important;
  border: 1px solid rgba(255, 255, 255, 0.06);
  padding: 18px 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  flex-shrink: 0;
}

.wave-container {
  height: 60px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.15);
}

.wave-canvas {
  width: 100%;
  height: 100%;
}

.wave-overlay-text {
  position: absolute;
  font-size: 0.8rem;
  color: #a5b4fc;
  font-weight: 600;
  letter-spacing: 0.05em;
  pointer-events: none;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
}

.control-actions {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  width: 100%;
}

.rate-controller {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-self: start;
}

.rate-controller .label {
  font-size: 0.92rem;
  color: var(--text-muted);
  font-weight: 600;
}

:deep(.rate-controller .el-radio-button__inner) {
  background: rgba(17, 24, 39, 0.6) !important;
  border-color: rgba(255, 255, 255, 0.08) !important;
  color: var(--text-secondary) !important;
}

:deep(.rate-controller .el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: var(--primary-color) !important;
  color: #fff !important;
  border-color: var(--primary-color) !important;
}

.mic-button-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  z-index: 10;
  justify-self: center;
}

.mic-btn {
  width: 72px !important;
  height: 72px !important;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%) !important;
  border: none !important;
  box-shadow: 0 4px 20px 0 rgba(99, 102, 241, 0.45);
  font-size: 2.0rem !important;
  color: #fff !important;
}

.mic-btn.recording-active {
  background: linear-gradient(135deg, var(--danger-color) 0%, #b91c1c 100%) !important;
  animation: pulseRecording 1.5s infinite;
  box-shadow: 0 4px 20px 0 rgba(239, 68, 68, 0.5);
}

@keyframes pulseRecording {
  0% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.6);
  }
  70% {
    transform: scale(1.04);
    box-shadow: 0 0 0 12px rgba(239, 68, 68, 0);
  }
  100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0);
  }
}

.btn-subtext {
  font-size: 0.7rem;
  color: var(--text-secondary);
  font-weight: 600;
  margin-top: 4px;
}

.placeholder-action {
  justify-self: end;
  min-width: 60px;
}

.cancel-recording-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.cancel-btn {
  width: 44px !important;
  height: 44px !important;
  background: rgba(239, 68, 68, 0.15) !important;
  border: 1px solid rgba(239, 68, 68, 0.3) !important;
  color: #f87171 !important;
  box-shadow: 0 4px 10px rgba(239, 68, 68, 0.1);
  font-size: 1.15rem !important;
}

.cancel-btn:hover {
  background: #ef4444 !important;
  border-color: #ef4444 !important;
  color: #fff !important;
  box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4);
}

.danger-text {
  color: #f87171 !important;
}

/* Feedback Panel (28%) */
.feedback-panel {
  width: 28%;
  padding: 24px;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.panel-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  padding-bottom: 12px;
}

.feedback-empty {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  color: var(--text-muted);
  gap: 16px;
  padding: 20px;
}

.feedback-empty-icon {
  font-size: 3rem;
  color: var(--text-muted);
  opacity: 0.5;
}

.feedback-empty p {
  font-size: 0.85rem;
  line-height: 1.5;
  max-width: 250px;
}

.feedback-content {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.section-subtitle {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.radar-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  background: rgba(0, 0, 0, 0.12);
  border-radius: 10px;
  padding: 10px;
}

.score-details {
  display: flex;
  justify-content: space-around;
  margin-top: 14px;
}

.score-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.score-item .label {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.score-item .value {
  font-size: 1.05rem;
  font-weight: 700;
  font-family: var(--font-display);
}

.success-text {
  color: var(--accent-color) !important;
}

.warning-text {
  color: var(--warning-color) !important;
}

.primary-text {
  color: #818cf8 !important;
}

/* Grammar correction box */
.grammar-card {
  padding: 16px;
}

.grammar-correct-state {
  display: flex;
  align-items: center;
  gap: 10px;
}

.correct-icon {
  font-size: 1.6rem;
  color: var(--accent-color);
}

.correct-desc {
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.4;
}

.grammar-error-state {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.correction-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.label-badge {
  align-self: flex-start;
  font-size: 0.7rem;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  letter-spacing: 0.02em;
}

.label-red {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.label-green {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.correction-text {
  font-size: 0.88rem;
  line-height: 1.45;
  padding: 8px 12px;
  border-radius: 6px;
  white-space: pre-wrap;
}

.error-text {
  background: rgba(239, 68, 68, 0.04);
  border-left: 3px solid var(--danger-color);
  color: #fca5a5;
  text-decoration: line-through rgba(239, 68, 68, 0.4);
}

.success-text {
  background: rgba(16, 185, 129, 0.04);
  border-left: 3px solid var(--accent-color);
  color: #a7f3d0;
  font-weight: 500;
}

.correction-explanation {
  border-top: 1px dashed rgba(255, 255, 255, 0.06);
  padding-top: 10px;
}

.exp-title {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-weight: 600;
  display: block;
  margin-bottom: 4px;
}

.exp-content {
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.45;
}

/* Settle Dialog */
:deep(.custom-dialog) {
  background: rgba(17, 24, 39, 0.85) !important;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-radius: 16px !important;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6) !important;
}

:deep(.custom-dialog .el-dialog__header) {
  text-align: center;
}

:deep(.custom-dialog .el-dialog__title) {
  color: var(--text-primary) !important;
  font-weight: 700;
}

.settlement-report {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 0;
  width: 100%;
}

/* 结算多维报表 CSS (3 Columns Grid) */
.settle-metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  width: 100%;
  margin-bottom: 20px;
}

.metric-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 12px 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  text-align: center;
}

.metric-card .m-val {
  font-size: 1.15rem;
  font-weight: 800;
  font-family: var(--font-display);
}

.metric-card .m-lbl {
  font-size: 0.68rem;
  color: var(--text-muted);
  font-weight: 600;
}

.best-turn-highlight {
  background: rgba(16, 185, 129, 0.06);
  border: 1px solid rgba(16, 185, 129, 0.15);
  border-radius: 8px;
  padding: 12px 16px;
  width: 100%;
  margin-bottom: 20px;
}

.highlight-title {
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--accent-color);
  margin-bottom: 6px;
}

.highlight-text {
  font-size: 0.88rem;
  color: var(--text-primary);
  font-style: italic;
  line-height: 1.4;
}

.report-header {
  text-align: center;
  margin-bottom: 20px;
}

.score-circle {
  width: 110px;
  height: 110px;
  border-radius: 50%;
  background: rgba(99, 102, 241, 0.05);
  border: 2px solid rgba(99, 102, 241, 0.15);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin: 0 auto 12px;
  box-shadow: 0 0 20px rgba(99, 102, 241, 0.1);
}

.score-num {
  font-size: 2.4rem;
  font-family: var(--font-display);
  font-weight: 800;
  line-height: 1;
}

.score-label {
  font-size: 0.7rem;
  color: var(--text-muted);
  font-weight: 600;
  margin-top: 2px;
}

.scene-done-name {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-primary);
}

.duration {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 4px;
}

.radar-wrapper-settle {
  width: 100%;
  display: flex;
  justify-content: center;
  background: rgba(0, 0, 0, 0.1);
  border-radius: 10px;
  padding: 10px;
  margin-bottom: 20px;
}

.report-footer-tips {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  background: rgba(99, 102, 241, 0.04);
  border: 1px dashed rgba(99, 102, 241, 0.15);
  border-radius: 8px;
  padding: 12px;
  width: 100%;
}

.report-footer-tips .el-icon {
  font-size: 1.3rem;
  color: var(--warning-color);
  flex-shrink: 0;
  margin-top: 2px;
}

.tips-text {
  font-size: 0.8rem;
  color: #a5b4fc;
  line-height: 1.45;
}

.settle-go-home-btn {
  width: 100%;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%) !important;
  border: none !important;
  font-weight: 600;
  padding: 12px 0;
  border-radius: 8px;
  font-size: 0.95rem;
}

.info-text {
  color: #06b6d4 !important;
}

.danger-text {
  color: #fca5a5 !important;
}

/* Header Status Panel next to Scene Meta */
.header-status-divider {
  width: 1px;
  height: 28px;
  background-color: rgba(255, 255, 255, 0.08);
  margin: 0 8px;
}

.header-status-panel {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 6px 16px;
  background: rgba(99, 102, 241, 0.06);
  border: 1px dashed rgba(99, 102, 241, 0.15);
  border-radius: 8px;
  animation: pulse-border 2s infinite ease-in-out;
}

.status-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-icon {
  color: var(--primary-color);
  font-size: 0.95rem;
}

.status-big-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--primary-color);
  letter-spacing: 0.5px;
}

.status-playful-remark {
  font-size: 0.78rem;
  color: var(--text-secondary);
  margin-top: 2px;
}

@keyframes pulse-border {
  0% {
    border-color: rgba(99, 102, 241, 0.15);
    background: rgba(99, 102, 241, 0.06);
  }
  50% {
    border-color: rgba(99, 102, 241, 0.35);
    background: rgba(99, 102, 241, 0.1);
  }
  100% {
    border-color: rgba(99, 102, 241, 0.15);
    background: rgba(99, 102, 241, 0.06);
  }
}
</style>

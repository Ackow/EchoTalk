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
      </div>
      <div class="header-right">
        <!-- Params Status Panel -->
        <div class="active-params" v-if="activeParams && Object.keys(activeParams).length > 0">
          <div v-for="(val, key) in activeParams" :key="key" class="param-tag">
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
          <p>我们将针对设定好的自定义场景和背景知识库与你进行模拟对话。你的发音将被多维度评估，语法表述也将获得润色建议。</p>
          <el-button type="primary" size="large" class="start-session-btn hover-scale" @click="startDialogueSession" :loading="startingSession">
            <span>进入练习会话</span>
          </el-button>
        </div>

        <template v-else>
          <div class="chat-history" ref="chatHistoryRef">
            <div v-for="(turn, idx) in turns" :key="turn.id || idx" :class="['message-row', turn.role === 'user' ? 'user-row' : 'ai-row']">
              <!-- AI Message -->
              <template v-if="turn.role === 'assistant'">
                <div class="avatar ai-avatar">AI</div>
                <div class="bubble-wrapper">
                  <div class="bubble ai-bubble glass-card">
                    <p class="message-text">{{ turn.text }}</p>
                    <div class="bubble-actions">
                      <el-button type="primary" link class="audio-play-btn" @click="playAudio(turn.audio_url, turn.id || idx)">
                        <el-icon v-if="playingTurnId === (turn.id || idx)"><VideoPlay /></el-icon>
                        <el-icon v-else><Headset /></el-icon>
                        <span>{{ playingTurnId === (turn.id || idx) ? '播报中...' : '播放原声' }}</span>
                      </el-button>
                    </div>
                  </div>
                </div>
              </template>

              <!-- User Message -->
              <template v-else>
                <div class="bubble-wrapper" @click="selectUserTurn(idx)">
                  <div :class="['bubble user-bubble glass-card', { 'selected-bubble': selectedTurnIndex === idx }]">
                    <p class="message-text">{{ turn.text }}</p>
                    <div class="bubble-score" v-if="turn.pronunciation_score">
                      <el-tag size="small" type="success" effect="dark" class="score-tag">
                        {{ turn.pronunciation_score.total_score }}分
                      </el-tag>
                    </div>
                  </div>
                  <div class="bubble-tips">点击可查看详细测评</div>
                </div>
                <div class="avatar user-avatar">ME</div>
              </template>
            </div>

            <!-- Loading AI Thinking -->
            <div v-if="isProcessing" class="message-row ai-row">
              <div class="avatar ai-avatar">AI</div>
              <div class="bubble-wrapper">
                <div class="bubble ai-bubble glass-card thinking-bubble">
                  <div class="dot-flashing"></div>
                  <span class="thinking-text">AI 正在转译并测评你的发音，请稍候...</span>
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
                <el-radio-group v-model="playbackRate" size="small" @change="changePlaybackRate">
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

              <div class="placeholder-action"></div>
            </div>
          </div>
        </template>
      </section>

      <!-- Right side: Evaluation & Feedback Panel -->
      <section class="feedback-panel glass-panel">
        <h3 class="panel-title">发音与语法实时评估</h3>
        
        <div v-if="selectedUserTurn" class="feedback-content">
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
          <p>开启对话并点击你的绿色对话气泡，即可在此处查看该轮的实时发音雷达图和语法纠错！</p>
        </div>
      </section>
    </div>

    <!-- Settle Dialog -->
    <el-dialog
      v-model="isSettleOpen"
      title="口语练习会话总结报告"
      width="520px"
      class="custom-dialog"
      :show-close="false"
      :close-on-click-modal="false"
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

        <div class="radar-wrapper-settle">
          <EChartsRadar :score-data="averageScores" height="220px" />
        </div>

        <div class="report-footer-tips">
          <el-icon><Opportunity /></el-icon>
          <p class="tips-text">你做得非常好！在本次对话中，你积极完成了口语表达。多尝试不同的场景，对你的语感会有显著提升！</p>
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
const selectedTurnIndex = ref(null)

const playbackRate = ref(1.0)
const playingTurnId = ref(null)
const activeAudio = ref(null)

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

// Select user turn for details
const selectedUserTurn = computed(() => {
  if (selectedTurnIndex.value === null) return null
  const turn = turns.value[selectedTurnIndex.value]
  return turn && turn.role === 'user' ? turn : null
})

// Lifecycle
onMounted(async () => {
  // If no scene in store, attempt to load it
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
  if (sessionStarted.value && turns.value.length > 0) {
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
    const res = await axios.post(`${store.backendBaseUrl}/api/dialogues/start`, {
      user_id: 1, // 默认 ID=1 预注册用户
      scene_id: scene.value.id
    })
    
    store.setActiveHistoryId(res.data.id)
    sessionStarted.value = true
    
    // Add custom greeting according to scene category
    let greetingText = "Hello! Let's start practicing."
    if (scene.value.id === 'interview') {
      greetingText = "Hello! I am David, the engineering manager. Thank you for coming today. Let's start the interview. Can you please introduce yourself and tell me about your experience with React Native?"
    } else if (scene.value.id === 'ordering' || scene.value.id === 'cafe') {
      greetingText = "Welcome to Metro Cafe! What can I get started for you today?"
    } else if (scene.value.id === 'meeting') {
      greetingText = "Hi team, thanks for joining. Today we are aligning on the Q3 product launch delays. Let's start with your updates. How is the React Native frontend progress?"
    } else if (scene.value.default_params?.character_name) {
      greetingText = `Hello! I am ${scene.value.default_params.character_name}. Welcome to this scenario! What would you like to practice today?`
    }
    
    // Insert mock greeting turn local-only (doesn't need upload, guides user input)
    store.addDialogueTurn({
      role: 'assistant',
      text: greetingText,
      audio_url: null
    })
    
    // Start empty quiet soundwave
    nextTick(() => {
      drawWave()
    })
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '启动口语练习会话失败，请确保后端服务正常')
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

const startRecording = async () => {
  try {
    stopAudio()
    leftchannel = []
    recordingLength = 0
    
    audioStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    
    const AudioContextClass = window.AudioContext || window.webkitAudioContext
    // Attempt 16000Hz sampling directly
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
  
  try {
    const mergedBuffer = mergeBuffers(leftchannel, recordingLength)
    const currentSampleRate = audioContext ? audioContext.sampleRate : 16000
    
    // Downsample if required
    let finalSamples = mergedBuffer
    if (currentSampleRate !== 16000) {
      finalSamples = downsampleBuffer(mergedBuffer, currentSampleRate, 16000)
    }
    
    const wavBlob = encodeWAV(finalSamples, 16000)
    const audioFile = new File([wavBlob], 'recording.wav', { type: 'audio/wav' })
    
    const formData = new FormData()
    formData.append('file', audioFile)
    
    stopRecordingResources()
    
    const res = await axios.post(
      `${store.backendBaseUrl}/api/dialogues/${historyId.value}/turn`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' }
      }
    )
    
    // Backend returns [user_turn, assistant_turn]
    const [userTurn, aiTurn] = res.data
    store.addDialogueTurn(userTurn)
    store.addDialogueTurn(aiTurn)
    
    // Auto-select latest user turn for evaluation panel
    const lastUserIdx = turns.value.length - 2
    selectedTurnIndex.value = lastUserIdx >= 0 ? lastUserIdx : null
    
    // Scroll chat window to bottom
    scrollToBottom()
    
    // Auto-play AI response
    if (aiTurn.audio_url) {
      playAudio(aiTurn.audio_url, turns.value.length - 1)
    }
  } catch (err) {
    console.error('音频转译与Pipeline管道交互异常:', err)
    ElMessage.error(err.response?.data?.detail || '发音评测失败，请重试说话')
  } finally {
    isProcessing.value = false
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
  view.setUint16(20, 1, true) // PCM raw format
  view.setUint16(22, 1, true) // Mono
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true) // 16bit
  writeString(view, 36, 'data')
  view.setUint32(40, samples.length * 2, true)
  
  // Float32 to Int16
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
  
  let amplitude = 6 // Quiet state
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
  stopAudio()
  
  if (!url) {
    ElMessage.info('该轮次无可用音频文件。')
    return
  }
  
  if (playingTurnId.value === turnId) {
    playingTurnId.value = null
    return
  }
  
  let fullUrl = url
  if (!url.startsWith('http')) {
    fullUrl = `${store.backendBaseUrl}${url}`
  }
  
  const audio = new Audio(fullUrl)
  audio.playbackRate = playbackRate.value
  
  audio.onended = () => {
    playingTurnId.value = null
    activeAudio.value = null
  }
  
  audio.onerror = () => {
    ElMessage.error('音频加载播放失败，可能已被七牛云自动失效')
    playingTurnId.value = null
    activeAudio.value = null
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

// Select user turn for inspection
const selectUserTurn = (index) => {
  if (turns.value[index]?.role === 'user') {
    selectedTurnIndex.value = index
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
      
      // Calculate average scores from turns
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
    grammar_score: Math.round(tot / userTurns.length) // 使用综合分兜底
  }
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
  height: 70px;
  padding: 12px 24px;
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
  font-size: 0.95rem;
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
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.scene-desc {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.active-params {
  display: flex;
  gap: 8px;
  max-width: 400px;
  overflow-x: auto;
}

.param-tag {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  padding: 4px 8px;
  font-size: 0.75rem;
  white-space: nowrap;
}

.param-tag .key {
  color: var(--text-muted);
  margin-right: 4px;
}

.param-tag .val {
  color: var(--text-secondary);
  font-weight: 600;
}

.settle-btn {
  background: linear-gradient(135deg, var(--danger-color) 0%, #b91c1c 100%) !important;
  border: none !important;
  font-weight: 600;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.2);
}

/* Grid layout */
.practice-grid {
  display: flex;
  flex-grow: 1;
  gap: 16px;
  overflow: hidden;
  height: calc(100vh - 118px);
}

/* Left side panel */
.dialogue-box {
  width: 63%;
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

.audio-play-btn {
  color: #818cf8 !important;
  font-size: 0.8rem;
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
  opacity: 0;
  transition: var(--transition-smooth);
}

.bubble-wrapper:hover .bubble-tips {
  opacity: 1;
}

/* Thinking Bubble animation */
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

/* Controls Box */
.dialogue-controls {
  height: 140px;
  margin: 16px;
  background: rgba(17, 24, 39, 0.8) !important;
  border: 1px solid rgba(255, 255, 255, 0.06);
  padding: 12px 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
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
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rate-controller {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rate-controller .label {
  font-size: 0.8rem;
  color: var(--text-muted);
  font-weight: 500;
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
  margin-top: -30px; /* 拉出控制条 */
  z-index: 10;
}

.mic-btn {
  width: 60px !important;
  height: 60px !important;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%) !important;
  border: none !important;
  box-shadow: 0 4px 18px 0 rgba(99, 102, 241, 0.45);
  font-size: 1.6rem !important;
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
  width: 140px; /* 与左侧配平 */
}

/* Right side feedback panel */
.feedback-panel {
  width: 37%;
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

/* Settle Dialog details */
:deep(.custom-dialog) {
  background: #111827 !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-radius: 12px !important;
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
</style>

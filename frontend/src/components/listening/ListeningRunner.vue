<template>
  <div class="runner-wrap">
    <header class="runner-header">
      <button type="button" class="icon-close-btn" title="退出训练" @click="handleExit">
        <AppIcon name="x" :size="16" />
      </button>

      <div class="progress-track" aria-label="训练进度">
        <div class="progress-fill" :style="{ width: `${progressPercent}%` }"></div>
      </div>

      <div class="runner-badges">
        <span v-if="isMockRestricted" class="mock-timer-badge" :class="{ urgent: mockSecondsLeft <= 120 }">
          {{ mockTimerLabel }}
        </span>
        <span v-if="combo >= 2" class="combo-badge">{{ combo }} 连击</span>
        <span
          class="track-mode-badge"
          :class="currentHintUsed || isMockRestricted ? 'assisted' : 'independent'"
        >
          {{ isMockRestricted ? '模拟考场模式' : currentHintUsed ? '已使用辅助' : '原速独立作答' }}
        </span>
      </div>
    </header>

    <!-- 结算页 -->
    <div v-if="finished" class="summary-card">
      <div class="summary-icon">
        <AppIcon name="check" :size="28" />
      </div>
      <h2>{{ unit.title }} · 训练完成！</h2>
      <p class="summary-sub">系统已将本次「原速独立作答」与「辅助后理解」分开记录，不污染真实听力画像。</p>

      <div class="summary-metrics">
        <div class="metric-box">
          <span>获得经验</span>
          <strong>+{{ unit.xp }} XP</strong>
        </div>
        <div class="metric-box">
          <span>原速独立正确</span>
          <strong>{{ independentCorrectCount }} / {{ totalCount }}</strong>
        </div>
        <div class="metric-box">
          <span>总完成正确</span>
          <strong>{{ totalCorrectCount }} / {{ totalCount }}</strong>
        </div>
      </div>

      <div v-if="sessionWeakTags.length" class="weak-box">
        <span>本次待巩固标签：</span>
        <span v-for="tag in sessionWeakTags" :key="tag" class="weak-tag">{{ tag }}</span>
      </div>

      <div class="summary-actions">
        <button type="button" class="ghost-button" @click="resetRunner">再练一次</button>
        <button type="button" class="primary-button" @click="handleExit">返回听力工作室</button>
      </div>
    </div>

    <!-- 答题主区域 -->
    <div v-else class="exercise-stage">
      <div class="exercise-card">
        <div class="exercise-type-row">
          <span class="type-pill">{{ typeLabel(currentExercise.type) }}</span>
          <span class="step-counter">第 {{ currentIndex + 1 }} / {{ totalCount }} 题</span>
        </div>

        <h3 class="exercise-prompt">{{ currentExercise.prompt }}</h3>

        <!-- 双速语音播放器 -->
        <div class="audio-player-box">
          <button
            type="button"
            class="primary-button play-btn"
            :class="{ playing: isSpeaking && speakRate === 1.0 }"
            @click="playAudio(1.0)"
          >
            <AppIcon name="headphones" :size="16" />
            <span>{{ isSpeaking && speakRate === 1.0 ? '正在播放…' : '播放原速 1.0×' }}</span>
          </button>

          <button
            type="button"
            class="slow-button"
            :class="{ playing: isSpeaking && speakRate === 0.75 }"
            :disabled="isMockRestricted"
            :title="isMockRestricted ? '模拟模式禁用慢速' : '0.75× 慢速精听'"
            @click="playAudio(0.75)"
          >
            <AppIcon name="clock" :size="15" />
            <span>0.75× 慢速</span>
          </button>

          <div class="wave-bars" :class="{ active: isSpeaking }" aria-hidden="true">
            <i v-for="n in 14" :key="n" :style="{ '--i': n }"></i>
          </div>
        </div>

        <!-- 渐进式辅助（L1-L3，模拟模式禁用） -->
        <div v-if="!isMockRestricted" class="hint-strip">
          <button
            type="button"
            class="hint-btn"
            :class="{ active: showKeywords }"
            @click="revealHint('keywords')"
          >
            {{ showKeywords ? '隐藏关键词' : '提示 1 · 关键词' }}
          </button>
          <button
            type="button"
            class="hint-btn"
            :class="{ active: showTranscript }"
            @click="revealHint('transcript')"
          >
            {{ showTranscript ? '隐藏英文原文' : '提示 2 · 英文原文' }}
          </button>
          <button
            type="button"
            class="hint-btn"
            :class="{ active: showZh }"
            @click="revealHint('zh')"
          >
            {{ showZh ? '隐藏中文释义' : '提示 3 · 中文释义' }}
          </button>
        </div>

        <div v-if="showKeywords || showTranscript || showZh" class="hint-drawer">
          <p v-if="showKeywords" class="hint-line">
            <b>关键词：</b>
            <span v-for="kw in currentExercise.keywords" :key="kw" class="kw-chip">{{ kw }}</span>
          </p>
          <p v-if="showTranscript" class="hint-line"><b>英文原文：</b>{{ currentExercise.audioText }}</p>
          <p v-if="showZh" class="hint-line"><b>中文参考：</b>{{ currentExercise.zhText }}</p>
        </div>

        <!-- 题型 A：Word Bank 听音拼句 -->
        <div v-if="currentExercise.type === 'word_bank'" class="word-bank-area">
          <div class="answer-tray" :class="{ empty: selectedTokens.length === 0 }">
            <span v-if="selectedTokens.length === 0" class="tray-placeholder">点击下方单词气泡按顺序拼出句子…</span>
            <button
              v-for="(tok, idx) in selectedTokens"
              :key="`${tok.id}-sel`"
              type="button"
              class="word-tile selected"
              :disabled="checked"
              @click="removeToken(idx)"
            >
              {{ tok.word }}
            </button>
          </div>

          <div class="bank-pool">
            <button
              v-for="tok in bankTokens"
              :key="tok.id"
              type="button"
              class="word-tile"
              :class="{ used: tok.used }"
              :disabled="tok.used || checked"
              @click="pickToken(tok)"
            >
              {{ tok.word }}
            </button>
          </div>
        </div>

        <!-- 题型 B：Choice 单选 -->
        <div v-else-if="currentExercise.type === 'choice'" class="choice-list">
          <button
            v-for="opt in currentExercise.options"
            :key="opt.key"
            type="button"
            class="choice-item"
            :class="{
              selected: selectedChoice === opt.key,
              correct: checked && opt.key === currentExercise.answer,
              wrong: checked && selectedChoice === opt.key && opt.key !== currentExercise.answer
            }"
            :disabled="checked"
            @click="selectedChoice = opt.key"
          >
            <span class="choice-key">{{ opt.key }}</span>
            <span class="choice-text">{{ opt.text }}</span>
          </button>
        </div>

        <!-- 题型 C：Cloze 听写填空 -->
        <div v-else-if="currentExercise.type === 'cloze'" class="cloze-area">
          <p class="cloze-sentence">
            <template v-for="(part, idx) in clozeParts" :key="idx">
              <span>{{ part }}</span>
              <input
                v-if="idx < currentExercise.blanks.length"
                v-model="clozeInputs[idx]"
                type="text"
                class="cloze-input"
                :class="clozeInputClass(idx)"
                :disabled="checked"
                :placeholder="`空格 ${idx + 1}`"
                autocomplete="off"
              />
            </template>
          </p>
          <div v-if="checked" class="cloze-diff-hint">
            参考答案：<b>{{ currentExercise.blanks.join(' / ') }}</b>
          </div>
        </div>

        <!-- 题型 D：Shadowing 跟读 -->
        <div v-else-if="currentExercise.type === 'shadowing'" class="shadowing-area">
          <div class="chunks-row">
            <span v-for="(chunk, idx) in currentExercise.chunks" :key="idx" class="chunk-pill">
              {{ chunk }}
            </span>
          </div>
          <div class="record-box">
            <button
              type="button"
              class="record-btn"
              :class="{ recording: isRecording }"
              :disabled="checked"
              @click="toggleMockRecord"
            >
              <AppIcon name="mic" :size="17" />
              <span>{{ isRecording ? '点击停止录音…' : shadowRecorded ? '重新跟读录音' : '点击开始跟读' }}</span>
            </button>
            <div v-if="shadowScore" class="shadow-score-row">
              <span>准确度 <b>{{ shadowScore.accuracy }}</b></span>
              <span>流利度 <b>{{ shadowScore.fluency }}</b></span>
              <span>完整度 <b>{{ shadowScore.integrity }}</b></span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部检查与即时反馈栏 -->
    <footer
      v-if="!finished"
      class="runner-footer"
      :class="checked ? (isCorrect ? 'state-correct' : 'state-wrong') : ''"
    >
      <div v-if="!checked" class="footer-inner">
        <button type="button" class="text-ghost-btn" @click="skipExercise">跳过此题</button>
        <button
          type="button"
          class="primary-button"
          :disabled="!canCheck"
          @click="checkAnswer"
        >
          检查答案
        </button>
      </div>

      <div v-else class="footer-inner feedback-mode">
        <div class="feedback-copy">
          <div class="feedback-title">
            <strong>{{ isCorrect ? '回答正确！' : '差一点，再听一遍细节' }}</strong>
            <span class="error-tag-chip">{{ currentExercise.errorTag }}</span>
          </div>
          <p class="feedback-tip">{{ currentExercise.tip }}</p>
        </div>
        <div class="feedback-actions">
          <button
            v-if="!isCorrect"
            type="button"
            class="btn-review-add"
            :class="{ added: addedToReview }"
            @click="handleAddToReview"
          >
            {{ addedToReview ? '已加入复习计划' : '+ 加入错题本' }}
          </button>
          <button type="button" class="btn-next" @click="nextExercise">
            {{ currentIndex + 1 >= totalCount ? '查看结算' : '继续下一题' }}
          </button>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import AppIcon from '../AppIcon.vue'
import {
  addListeningReview,
  completeListeningUnit,
  getListeningAudioUrl,
  submitListeningAttempt
} from '../../api/listening'
import { addGlobalXp, applyXpSnapshot, syncGlobalXpProfile } from '../../app/xp'
import { session } from '../../auth/session'

const props = defineProps({
  unit: { type: Object, required: true },
  isMockRestricted: { type: Boolean, default: false }
})

const emit = defineEmits(['exit', 'completed'])

const currentIndex = ref(0)
const finished = ref(false)
const combo = ref(0)
const mockSecondsLeft = ref(1500)
let mockTimerId = null

const mockTimerLabel = computed(() => {
  const m = String(Math.floor(mockSecondsLeft.value / 60)).padStart(2, '0')
  const s = String(mockSecondsLeft.value % 60).padStart(2, '0')
  return `${m}:${s}`
})

function startMockTimer() {
  stopMockTimer()
  if (!props.isMockRestricted) return
  const minutes = props.unit?.cetLevel === 'cet6' ? 30 : 25
  mockSecondsLeft.value = minutes * 60
  mockTimerId = setInterval(() => {
    if (finished.value) {
      stopMockTimer()
      return
    }
    if (mockSecondsLeft.value > 0) {
      mockSecondsLeft.value -= 1
    } else {
      stopMockTimer()
    }
  }, 1000)
}

function stopMockTimer() {
  if (mockTimerId) {
    clearInterval(mockTimerId)
    mockTimerId = null
  }
}

const isSpeaking = ref(false)
const speakRate = ref(1.0)

const showKeywords = ref(false)
const showTranscript = ref(false)
const showZh = ref(false)
const currentHintUsed = ref(false)

const checked = ref(false)
const isCorrect = ref(false)
const addedToReview = ref(false)

const bankTokens = ref([])
const selectedTokens = ref([])
const selectedChoice = ref('')
const clozeInputs = ref([])
const isRecording = ref(false)
const shadowRecorded = ref(false)
const shadowScore = ref(null)

const independentCorrectCount = ref(0)
const totalCorrectCount = ref(0)
const sessionWeakTags = ref([])

const totalCount = computed(() => props.unit?.exercises.length || 0)
const currentExercise = computed(() => props.unit?.exercises[currentIndex.value] || null)
const progressPercent = computed(() => {
  if (!totalCount.value) return 0
  return Math.round(((currentIndex.value + (finished.value ? 1 : 0)) / totalCount.value) * 100)
})

const clozeParts = computed(() => {
  if (!currentExercise.value?.template) return []
  return currentExercise.value.template.split('____')
})

const canCheck = computed(() => {
  const ex = currentExercise.value
  if (!ex) return false
  if (ex.type === 'word_bank') return selectedTokens.value.length > 0
  if (ex.type === 'choice') return Boolean(selectedChoice.value)
  if (ex.type === 'cloze') return clozeInputs.value.some((v) => v.trim().length > 0)
  if (ex.type === 'shadowing') return shadowRecorded.value
  return false
})

function typeLabel(type) {
  const map = {
    word_bank: '听音拼句',
    choice: '听音选义',
    cloze: '听写填空',
    shadowing: 'Shadowing 跟读'
  }
  return map[type] || '听力训练'
}

let activeAudioEl = null

function speakFallback(text, rate) {
  if (text && 'speechSynthesis' in window) {
    const utter = new SpeechSynthesisUtterance(text)
    utter.lang = 'en-US'
    utter.rate = rate
    utter.onstart = () => {
      isSpeaking.value = true
    }
    utter.onend = () => {
      isSpeaking.value = false
    }
    utter.onerror = () => {
      isSpeaking.value = false
    }
    window.speechSynthesis.speak(utter)
  } else {
    isSpeaking.value = true
    setTimeout(() => {
      isSpeaking.value = false
    }, 1800)
  }
}

function playAudio(rate) {
  const ex = currentExercise.value
  if (!ex) return
  stopAudio()
  speakRate.value = rate

  const audioSrc = ex.audioUrl || (ex.audioText ? getListeningAudioUrl(ex.audioText, rate) : '')
  if (audioSrc) {
    const audio = new Audio(audioSrc)
    if (ex.audioUrl) {
      audio.playbackRate = rate
      if (typeof ex.startMs === 'number') {
        audio.currentTime = ex.startMs / 1000
      }
    }
    audio.onplay = () => {
      isSpeaking.value = true
    }
    audio.ontimeupdate = () => {
      if (ex.audioUrl && typeof ex.endMs === 'number' && audio.currentTime * 1000 >= ex.endMs) {
        stopAudio()
      }
    }
    audio.onended = () => {
      isSpeaking.value = false
    }
    audio.onerror = () => {
      isSpeaking.value = false
      if (!ex.audioUrl && ex.audioText) {
        speakFallback(ex.audioText, rate)
      }
    }
    activeAudioEl = audio
    audio.play().catch(() => {
      isSpeaking.value = false
      if (!ex.audioUrl && ex.audioText) {
        speakFallback(ex.audioText, rate)
      }
    })
  } else {
    speakFallback(ex.audioText, rate)
  }

  if (rate < 1.0) {
    currentHintUsed.value = true
  }
}

function stopAudio() {
  isSpeaking.value = false
  if (activeAudioEl) {
    activeAudioEl.pause()
    activeAudioEl = null
  }
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel()
  }
}

function initExerciseState() {
  stopAudio()
  checked.value = false
  isCorrect.value = false
  addedToReview.value = false
  showKeywords.value = false
  showTranscript.value = false
  showZh.value = false
  currentHintUsed.value = false

  selectedTokens.value = []
  selectedChoice.value = ''
  isRecording.value = false
  shadowRecorded.value = false
  shadowScore.value = null

  const ex = currentExercise.value
  if (!ex) return
  if (ex.type === 'word_bank') {
    const merged = [...ex.tokens, ...(ex.distractors || [])]
    bankTokens.value = merged
      .map((word, idx) => ({ id: `${ex.id}-${idx}`, word, used: false, sortKey: (word.length * 17 + idx * 31) % 97 }))
      .sort((a, b) => a.sortKey - b.sortKey)
  } else if (ex.type === 'cloze') {
    clozeInputs.value = ex.blanks.map(() => '')
  }
}

function resetRunner() {
  currentIndex.value = 0
  finished.value = false
  combo.value = 0
  independentCorrectCount.value = 0
  totalCorrectCount.value = 0
  sessionWeakTags.value = []
  initExerciseState()
  startMockTimer()
}

watch(
  () => [props.unit, props.isMockRestricted],
  () => {
    resetRunner()
  },
  { immediate: true }
)

function handleExit() {
  stopAudio()
  stopMockTimer()
  emit('exit')
}

function revealHint(kind) {
  currentHintUsed.value = true
  if (kind === 'keywords') showKeywords.value = !showKeywords.value
  if (kind === 'transcript') showTranscript.value = !showTranscript.value
  if (kind === 'zh') showZh.value = !showZh.value
}

function pickToken(tok) {
  if (tok.used || checked.value) return
  tok.used = true
  selectedTokens.value.push(tok)
}

function removeToken(idx) {
  if (checked.value) return
  const [removed] = selectedTokens.value.splice(idx, 1)
  if (removed) removed.used = false
}

function toggleMockRecord() {
  if (isRecording.value) {
    isRecording.value = false
    shadowRecorded.value = true
    shadowScore.value = { accuracy: 89, fluency: 86, integrity: 95 }
  } else {
    stopAudio()
    isRecording.value = true
  }
}

function clozeInputClass(idx) {
  if (!checked.value) return ''
  const expected = (currentExercise.value.blanks[idx] || '').trim().toLowerCase()
  const actual = (clozeInputs.value[idx] || '').trim().toLowerCase()
  return expected === actual ? 'ok' : 'err'
}

async function checkAnswer() {
  const ex = currentExercise.value
  if (!ex) return
  let ok = false

  if (ex.type === 'word_bank') {
    ok = selectedTokens.value.map((t) => t.word).join(' ').trim() === ex.tokens.join(' ').trim()
  } else if (ex.type === 'choice') {
    ok = selectedChoice.value === ex.answer
  } else if (ex.type === 'cloze') {
    ok = ex.blanks.every(
      (b, idx) => (clozeInputs.value[idx] || '').trim().toLowerCase() === b.trim().toLowerCase()
    )
  } else if (ex.type === 'shadowing') {
    ok = Boolean(shadowScore.value && shadowScore.value.accuracy >= 75)
  }

  checked.value = true
  isCorrect.value = ok

  const isIndependent = !currentHintUsed.value || props.isMockRestricted
  if (ok) {
    combo.value += 1
    totalCorrectCount.value += 1
    if (isIndependent) {
      independentCorrectCount.value += 1
    }
  } else {
    combo.value = 0
    if (ex.errorTag && !sessionWeakTags.value.includes(ex.errorTag)) {
      sessionWeakTags.value.push(ex.errorTag)
    }
  }

  if (session.token && props.unit) {
    const hintsUsed = []
    if (speakRate.value < 1.0) hintsUsed.push('slow')
    if (showKeywords.value) hintsUsed.push('keywords')
    if (showTranscript.value) hintsUsed.push('transcript')
    if (showZh.value) hintsUsed.push('zh')
    try {
      const { data } = await submitListeningAttempt({
        unitId: props.unit.id,
        exerciseId: ex.id,
        exerciseType: ex.type,
        isCorrect: ok,
        isIndependent,
        hintsUsed,
        errorTag: ex.errorTag || '',
        stepIndex: currentIndex.value,
        totalSteps: totalCount.value
      })
      applyXpSnapshot(data)
    } catch {
      // 网络异常时不阻塞当前做题流程
    }
  }
}

async function handleAddToReview() {
  if (addedToReview.value) return
  addedToReview.value = true
  const ex = currentExercise.value
  if (!session.token || !ex || !props.unit) return
  try {
    await addListeningReview({
      unitId: props.unit.id,
      exerciseId: ex.id,
      prompt: ex.prompt || '听力细节辨析',
      answer: ex.audioText || ex.answer || (ex.blanks || []).join(' / '),
      note: ex.tip || '',
      contextText: ex.zhText || ''
    })
  } catch {
    // 忽略重复或网络错误
  }
}

function skipExercise() {
  combo.value = 0
  nextExercise()
}

async function nextExercise() {
  if (currentIndex.value + 1 >= totalCount.value) {
    stopAudio()
    finished.value = true
    if (session.token) {
      try {
        const { data } = await completeListeningUnit(props.unit.id)
        applyXpSnapshot(data)
        await syncGlobalXpProfile()
        emit('completed')
      } catch {
        addGlobalXp(props.unit.xp)
      }
    } else {
      addGlobalXp(props.unit.xp)
    }
  } else {
    currentIndex.value += 1
    initExerciseState()
  }
}

onBeforeUnmount(() => {
  stopAudio()
  stopMockTimer()
})
</script>

<style scoped>
.primary-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 18px;
  border: 2px solid #8067d1;
  border-bottom: 4px solid #6951b8;
  border-radius: 13px;
  background: #8b73dd;
  color: #ffffff;
  font-size: 13.5px;
  font-weight: 700;
  transition: transform 0.14s, background 0.14s;
}

.primary-button:hover:not(:disabled) {
  background: #7d64d1;
  transform: translateY(-1px);
}

.primary-button:disabled {
  border-color: #d6d2e8;
  border-bottom-color: #c8c3de;
  background: #dcd8ee;
  color: #ffffff;
}

.ghost-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 40px;
  padding: 0 16px;
  border: 2px solid #e4def5;
  border-bottom: 4px solid #ddd5f2;
  border-radius: 13px;
  background: #ffffff;
  color: #554c72;
  font-size: 13.5px;
  font-weight: 700;
}

.runner-wrap {
  max-width: 800px;
  margin: 0 auto;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.runner-header {
  display: flex;
  align-items: center;
  gap: 14px;
}

.icon-close-btn {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border: 2px solid #e4def5;
  border-bottom: 4px solid #ddd5f2;
  border-radius: 11px;
  background: #ffffff;
  color: #6b6584;
}

.progress-track {
  flex: 1;
  height: 12px;
  border-radius: 999px;
  background: #efeafc;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #8b73dd;
  border-radius: 999px;
  transition: width 0.25s ease;
}

.runner-badges {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mock-timer-badge {
  display: inline-flex;
  align-items: center;
  padding: 5px 11px;
  border-radius: 999px;
  background: #fff4e5;
  color: #b45309;
  font-size: 12px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.mock-timer-badge.urgent {
  background: #fde8ec;
  color: #be123c;
}

.combo-badge {
  padding: 4px 10px;
  border-radius: 999px;
  background: #fef3c7;
  color: #b45309;
  font-size: 12px;
  font-weight: 700;
}

.track-mode-badge {
  padding: 4px 11px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.track-mode-badge.independent {
  background: #eff9f2;
  color: #2f855a;
}

.track-mode-badge.assisted {
  background: #f3f1fa;
  color: #706d85;
}

.exercise-stage {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.exercise-card {
  padding: 24px 26px;
  border: 2px solid #eae7f2;
  border-bottom: 5px solid #e3dfed;
  border-radius: 22px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.exercise-type-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.type-pill {
  padding: 4px 11px;
  border-radius: 8px;
  background: #efeafc;
  color: #654ab8;
  font-size: 12px;
  font-weight: 700;
}

.step-counter {
  font-size: 12.5px;
  color: #858195;
  font-weight: 600;
}

.exercise-prompt {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  color: #29283e;
}

.audio-player-box {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 2px solid #ebe7f6;
  border-radius: 16px;
  background: #f8f5ff;
}

.play-btn,
.runner-footer .primary-button {
  width: auto;
  height: 40px;
  flex: 0 0 auto;
  justify-content: center;
  gap: 8px;
  min-width: 124px;
  margin-top: 0;
  padding: 0 18px;
  border-radius: 12px;
  font-weight: 700;
}

.runner-footer .primary-button:disabled {
  cursor: not-allowed;
}

.slow-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 40px;
  padding: 0 14px;
  border: 2px solid #e4def5;
  border-bottom: 4px solid #ddd5f2;
  border-radius: 13px;
  background: #ffffff;
  color: #554c72;
  font-size: 13px;
  font-weight: 700;
}

.slow-button.playing {
  border-color: #8b73dd;
  color: #654ab8;
}

.slow-button:disabled {
  opacity: 0.45;
}

.wave-bars {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 24px;
  margin-left: auto;
}

.wave-bars i {
  display: block;
  width: 3px;
  height: 8px;
  border-radius: 3px;
  background: #d5cdee;
}

.wave-bars.active i {
  background: #8b73dd;
  animation: wave-pulse 0.8s ease-in-out infinite alternate;
  animation-delay: calc(var(--i) * 0.06s);
}

@keyframes wave-pulse {
  from { height: 6px; }
  to { height: 22px; }
}

.hint-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hint-btn {
  padding: 6px 12px;
  border: 1.5px dashed #d3c8ef;
  border-radius: 10px;
  background: transparent;
  color: #6b6584;
  font-size: 12.5px;
  font-weight: 600;
}

.hint-btn.active {
  border-style: solid;
  border-color: #8b73dd;
  background: #efeafc;
  color: #654ab8;
}

.hint-drawer {
  padding: 12px 14px;
  border-radius: 12px;
  background: #f8f5ff;
  border: 1.5px solid #e4def5;
  font-size: 13.5px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hint-line {
  margin: 0;
  color: #4e4963;
}

.kw-chip {
  display: inline-block;
  margin-right: 6px;
  padding: 2px 8px;
  border-radius: 6px;
  background: #ffffff;
  border: 1px solid #e4def5;
  font-size: 12.5px;
}

.answer-tray {
  min-height: 58px;
  padding: 10px 12px;
  border: 2px solid #eae7f2;
  border-radius: 14px;
  background: #fbfaff;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.tray-placeholder {
  color: #9e9aad;
  font-size: 13.5px;
}

.bank-pool {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.word-tile {
  padding: 8px 14px;
  border: 2px solid #e4def5;
  border-bottom: 4px solid #d6cef0;
  border-radius: 12px;
  background: #ffffff;
  color: #29283e;
  font-size: 14px;
  font-weight: 600;
}

.word-tile.used {
  background: #f0edf8;
  color: transparent;
  border-color: #eae7f2;
  border-bottom-color: #eae7f2;
}

.word-tile.selected {
  border-color: #8b73dd;
  border-bottom-color: #6951b8;
  background: #efeafc;
  color: #654ab8;
}

.choice-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.choice-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 13px 16px;
  border: 2px solid #eae7f2;
  border-bottom: 4px solid #e3dfed;
  border-radius: 14px;
  background: #ffffff;
  text-align: left;
  font-size: 14.5px;
  color: #29283e;
  font-weight: 500;
}

.choice-item.selected {
  border-color: #8b73dd;
  border-bottom-color: #6951b8;
  background: #f8f5ff;
}

.choice-item.correct {
  border-color: #35a876;
  background: #eff9f2;
}

.choice-item.wrong {
  border-color: #d95367;
  background: #fdf2f4;
}

.choice-key {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: #fbfaff;
  border: 1.5px solid #e4def5;
  font-size: 12.5px;
  font-weight: 700;
  color: #654ab8;
}

.cloze-sentence {
  margin: 0;
  font-size: 16.5px;
  line-height: 2.1;
}

.cloze-input {
  width: 136px;
  margin: 0 6px;
  padding: 3px 10px;
  border: 2px solid #dcd6ef;
  border-radius: 10px;
  background: #fbfaff;
  font-size: 15px;
  text-align: center;
  font-weight: 600;
}

.cloze-input.ok {
  border-color: #35a876;
  background: #eff9f2;
  color: #1f7a4c;
}

.cloze-input.err {
  border-color: #d95367;
  background: #fdf2f4;
  color: #b8485a;
}

.cloze-diff-hint {
  margin-top: 10px;
  font-size: 13.5px;
  color: #554c72;
}

.chunks-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chunk-pill {
  padding: 8px 13px;
  border-radius: 11px;
  background: #fbfaff;
  border: 1.5px solid #e4def5;
  font-size: 14.5px;
  font-weight: 600;
}

.record-box {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 14px;
}

.record-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border: 2px solid #8b73dd;
  border-bottom: 4px solid #6951b8;
  border-radius: 13px;
  background: #efeafc;
  color: #654ab8;
  font-size: 14px;
  font-weight: 700;
}

.record-btn.recording {
  background: #fdf2f4;
  border-color: #d95367;
  border-bottom-color: #b8485a;
  color: #b8485a;
}

.shadow-score-row {
  display: flex;
  gap: 14px;
  font-size: 13.5px;
  color: #554c72;
}

.runner-footer {
  padding: 12px 18px;
  border: 2px solid #eae7f2;
  border-bottom: 4px solid #e3dfed;
  border-radius: 16px;
  background: #ffffff;
}

.runner-footer.state-correct {
  border-color: #bce6cc;
  border-bottom-color: #a3dab8;
  background: #eff9f2;
}

.runner-footer.state-wrong {
  border-color: #f0c2c9;
  border-bottom-color: #e5abb4;
  background: #fdf2f4;
}

.footer-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.text-ghost-btn {
  padding: 8px 14px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: #858195;
  font-size: 13.5px;
  font-weight: 600;
}

.feedback-copy {
  flex: 1;
  min-width: 240px;
}

.feedback-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
}

.error-tag-chip {
  padding: 2px 9px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.75);
  font-size: 11.5px;
  font-weight: 700;
  color: #554c72;
}

.feedback-tip {
  margin: 5px 0 0;
  font-size: 13.5px;
  color: #4e4963;
}

.feedback-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.btn-review-add {
  padding: 9px 14px;
  border: 1.5px solid #e3b2ba;
  border-radius: 11px;
  background: #ffffff;
  color: #b8485a;
  font-size: 13px;
  font-weight: 700;
}

.btn-review-add.added {
  border-color: #35a876;
  color: #2f855a;
}

.btn-next {
  min-height: 40px;
  padding: 0 22px;
  border: 0;
  border-radius: 12px;
  background: #8b73dd;
  color: #ffffff;
  font-size: 14px;
  font-weight: 700;
}

.state-correct .btn-next {
  background: #35a876;
}

.state-wrong .btn-next {
  background: #b8485a;
}

.summary-card {
  padding: 32px 28px;
  border: 2px solid #eae7f2;
  border-bottom: 5px solid #e3dfed;
  border-radius: 22px;
  background: #ffffff;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
}

.summary-icon {
  display: grid;
  place-items: center;
  width: 58px;
  height: 58px;
  border-radius: 20px;
  background: #eff9f2;
  color: #35a876;
}

.summary-card h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
}

.summary-sub {
  margin: 0;
  max-width: 480px;
  font-size: 13.5px;
  color: #7f7c90;
}

.summary-metrics {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
  margin-top: 6px;
}

.metric-box {
  min-width: 140px;
  padding: 12px 16px;
  border: 2px solid #eae7f2;
  border-radius: 14px;
  background: #fbfaff;
}

.metric-box span {
  display: block;
  font-size: 12px;
  color: #7f7c90;
}

.metric-box strong {
  display: block;
  margin-top: 4px;
  font-size: 18px;
  font-weight: 800;
}

.weak-box {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #554c72;
}

.weak-tag {
  padding: 3px 10px;
  border-radius: 999px;
  background: #fdf2f4;
  color: #b8485a;
  font-size: 12px;
  font-weight: 700;
}

.summary-actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}
</style>

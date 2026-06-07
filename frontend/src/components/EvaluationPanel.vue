<template>
  <div class="eval-panel" :class="{ 'eval-compact': compact }">
    <!-- 标题 -->
    <h3 v-if="title && !compact" class="eval-title">{{ title }}</h3>

    <!-- 空状态 -->
    <div v-if="!turn" class="eval-empty">
      <el-icon class="eval-empty-icon"><InfoFilled /></el-icon>
      <p>{{ emptyText }}</p>
    </div>

    <div v-else class="eval-content">
      <!-- 加载中 -->
      <div v-if="isEvaluating" class="eval-loading glass-card" v-loading="true"
        :element-loading-text="loadingText" element-loading-background="rgba(17, 24, 39, 0.4)"
        :style="{ height: compact ? '220px' : '380px' }">
      </div>

      <template v-else>
        <!-- 发音雷达图 -->
        <div v-if="turn.pronunciation_score" class="eval-sec">
          <div class="eval-sec-title">发音能力五维雷达图</div>
          <div class="radar-area">
            <EChartsRadar :score-data="turn.pronunciation_score" :height="compact ? '200px' : '260px'" />
          </div>
        </div>

        <!-- 六维数字评分 -->
        <div v-if="turn.pronunciation_score" class="eval-sec">
          <div class="eval-sec-title">评分详情</div>
          <div class="score-grid">
            <div class="score-cell" v-for="item in scoreItems" :key="item.label">
              <span class="score-label">{{ item.label }}</span>
              <span class="score-value font-display" :class="{'gradient-text': item.highlight}">{{ getScore(item.key, item.fallback) }}</span>
            </div>
          </div>
        </div>

        <!-- 单词级发音 -->
        <div v-if="turn.pronunciation_score && lowWords.length > 0" class="eval-sec">
          <div class="eval-sec-title">发音待改进单词</div>
          <div class="word-list glass-card">
            <span v-for="(w, i) in lowWords" :key="i"
              :class="['word-tag', wordClass(w)]"
              @click="$emit('word-click', w.word)"
            >{{ w.word }}<span class="word-score">{{ Math.round(w.score) }}分</span></span>
          </div>
        </div>

        <div v-else-if="turn.pronunciation_score && turn.pronunciation_score.words && turn.pronunciation_score.words.length > 0 && !compact" class="eval-sec">
          <div class="all-perfect">
            <el-icon><SuccessFilled /></el-icon>
            <span>太棒了！该句中所有单词发音均达到优秀标准 (≥80分)！🎉</span>
          </div>
        </div>

        <!-- 语速与停顿诊断 -->
        <div v-if="showRhythm && rhythmData" class="eval-sec">
          <div class="eval-sec-title">语速与停顿节奏诊断</div>
          <div class="rhythm-card glass-card">
            <div class="rhythm-speed">
              <span>语速：</span>
              <span :class="['speed-val font-display', rhythmData.speedClass]">{{ rhythmData.wpm }} WPM ({{ rhythmData.speedEval }})</span>
            </div>
            <p class="rhythm-advice">{{ rhythmData.speedAdvice }}</p>
            <div v-if="rhythmData.longPauses.length > 0" class="rhythm-pauses">
              <span class="pause-title">检测到的较长停顿：</span>
              <ul>
                <li v-for="(p, i) in rhythmData.longPauses" :key="i">在 <strong>"{{ p.word1 }}"</strong> 与 <strong>"{{ p.word2 }}"</strong> 之间停顿了 {{ p.duration }} 秒</li>
              </ul>
            </div>
            <div v-else class="rhythm-ok">
              <el-icon><SuccessFilled /></el-icon>
              <span>整句发音一气呵成，没有检测到不自然的长停顿！</span>
            </div>
          </div>
        </div>

        <!-- 语法纠错 -->
        <div v-if="turn.grammar_correction" class="eval-sec">
          <div class="eval-sec-title">语法及表达优化建议</div>
          <div class="grammar-card glass-card">
            <div v-if="turn.grammar_correction.original === turn.grammar_correction.corrected" class="grammar-ok">
              <el-icon class="correct-icon"><SuccessFilled /></el-icon>
              <p class="correct-desc">{{ turn.grammar_correction.explanation }}</p>
            </div>
            <div v-else>
              <div class="fix-row">
                <div class="badge badge-red">原文 (Original)</div>
                <p class="fix-text red-text">{{ turn.grammar_correction.original }}</p>
              </div>
              <div class="fix-row">
                <div class="badge badge-green">优化 (Polished)</div>
                <p class="fix-text green-text">{{ turn.grammar_correction.corrected }}</p>
              </div>
              <div class="explanation">
                <span class="exp-title">综合修改说明 (Explanation):</span>
                <p class="exp-text">{{ turn.grammar_correction.explanation }}</p>
              </div>
              <div v-if="turn.grammar_correction.suggestions" class="suggestions">
                <div v-if="turn.grammar_correction.suggestions.grammar" class="sug-card grammar-sug">
                  <span class="sug-title"><el-icon><CircleCheck /></el-icon> 语法纠错剖析 (Grammar)</span>
                  <p>{{ turn.grammar_correction.suggestions.grammar }}</p>
                </div>
                <div v-if="turn.grammar_correction.suggestions.vocabulary" class="sug-card vocab-sug">
                  <span class="sug-title"><el-icon><Reading /></el-icon> 地道词汇表达升级 (Vocabulary)</span>
                  <p>{{ turn.grammar_correction.suggestions.vocabulary }}</p>
                </div>
                <div v-if="turn.grammar_correction.suggestions.pronunciation" class="sug-card pron-sug">
                  <span class="sug-title"><el-icon><Headset /></el-icon> 连读与语音技巧 (Pronunciation)</span>
                  <p>{{ turn.grammar_correction.suggestions.pronunciation }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import EChartsRadar from './EChartsRadar.vue'

const props = defineProps({
  turn: { type: Object, default: null },
  title: { type: String, default: '' },
  isEvaluating: { type: Boolean, default: false },
  compact: { type: Boolean, default: false },
  showRhythm: { type: Boolean, default: false },
  emptyText: { type: String, default: '点击语音胶囊即可查看发音评估与语法纠错' },
  loadingText: { type: String, default: '正在评估发音表现...' }
})
defineEmits(['word-click'])

const scoreItems = [
  { key: 'total_score', label: '综合总分', fallback: null, highlight: true },
  { key: 'accuracy_score', label: '准确度', fallback: null },
  { key: 'fluency_score', label: '流利度', fallback: null },
  { key: 'integrity_score', label: '完整度', fallback: null },
  { key: 'intonation_score', label: '语调重音', fallback: 'fluency_score' },
  { key: 'liaison_score', label: '连读爆破', fallback: 'accuracy_score' },
]

const getScore = (key, fallbackKey) => {
  if (!props.turn?.pronunciation_score) return '--'
  const val = props.turn.pronunciation_score[key]
  if (val != null && val > 0) return val
  if (fallbackKey) {
    const fb = props.turn.pronunciation_score[fallbackKey]
    if (fb != null && fb > 0) return fb
  }
  return '--'
}

const wordClass = (w) => {
  if (w.dp_message === 16) return 'tag-missing'
  if (w.score >= 80) return 'tag-good'
  if (w.score >= 60) return 'tag-avg'
  return 'tag-bad'
}

const lowWords = computed(() => {
  if (!props.turn?.pronunciation_score?.words) return []
  const raw = props.turn.pronunciation_score.words.filter(w => w.score < 80 || w.dp_message !== 0)
  const seen = new Set()
  return raw.filter(w => {
    const key = w.word.toLowerCase().trim()
    if (seen.has(key)) return false; seen.add(key); return true
  })
})

const rhythmData = computed(() => {
  if (!props.showRhythm) return null
  const words = props.turn?.pronunciation_score?.words
  if (!words || words.length < 2) return null
  const first = words[0], last = words[words.length - 1]
  const durFrames = last.end_pos - first.beg_pos
  const durSec = durFrames > 0 ? durFrames * 0.01 : 1.0
  const wpm = Math.round((words.length / durSec) * 60)
  let speedEval = '语速适中', speedClass = 'success-text', speedAdvice = '你的语速非常自然，契合标准的英文口语对话节奏！'
  if (wpm < 95) { speedEval = '语速偏慢'; speedClass = 'warning-text'; speedAdvice = '朗读节奏较慢或略有迟疑，建议多尝试流畅、连贯地阅读整句。' }
  else if (wpm > 175) { speedEval = '语速过快'; speedClass = 'warning-text'; speedAdvice = '说话速度有些急促，可能导致单词发音吞音，建议稍微放缓速度。' }
  const pauses = []
  for (let i = 0; i < words.length - 1; i++) {
    if (words[i].end_pos === 0 || words[i + 1].beg_pos === 0) continue
    const gap = words[i + 1].beg_pos - words[i].end_pos
    if (gap > 80) pauses.push({ word1: words[i].word, word2: words[i + 1].word, duration: (gap * 0.01).toFixed(1) })
  }
  return { wpm, speedEval, speedClass, speedAdvice, longPauses: pauses }
})
</script>

<style scoped>
.eval-panel { display: flex; flex-direction: column; flex: 1; min-height: 0; }

.eval-title { font-size: 1.15rem; font-weight: 700; color: var(--text-primary); margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 12px; }

.eval-empty { flex-grow: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; color: var(--text-muted); gap: 16px; padding: 20px; }
.eval-empty-icon { font-size: 3rem; opacity: 0.5; }
.eval-empty p { font-size: 0.85rem; line-height: 1.5; max-width: 250px; }

.eval-content { display: flex; flex-direction: column; gap: 28px; overflow-y: auto; }

.eval-sec-title { font-size: 0.9rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 12px; }

.radar-area { display: flex; justify-content: center; align-items: center; background: rgba(0,0,0,0.12); border-radius: 10px; padding: 10px; }

.score-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.score-cell { background: rgba(17,24,39,0.4); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 10px 8px; text-align: center; display: flex; flex-direction: column; gap: 4px; }
.score-label { font-size: 0.7rem; color: var(--text-muted); }
.score-value { font-size: 1.1rem; font-weight: 700; color: var(--text-primary); }

.word-list { display: flex; flex-wrap: wrap; gap: 8px; padding: 12px; background: rgba(17,24,39,0.4) !important; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08); }
.word-tag { display: inline-flex; align-items: center; padding: 4px 8px; border-radius: 6px; font-size: 0.85rem; font-weight: 500; transition: all 0.2s ease; cursor: pointer; }
.word-tag:hover { transform: translateY(-1px); }
.word-tag .word-score { font-size: 0.65rem; margin-left: 4px; opacity: 0.8; background: rgba(0,0,0,0.2); padding: 1px 3px; border-radius: 3px; }
.tag-good { color: #34d399; background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.2); }
.tag-avg { color: #fbbf24; background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.2); }
.tag-bad { color: #f87171; background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.2); }
.tag-missing { color: #9ca3af; text-decoration: line-through; background: rgba(156,163,175,0.1); border: 1px solid rgba(156,163,175,0.2); }
.all-perfect { display: flex; align-items: center; gap: 8px; color: var(--accent-color); font-size: 0.82rem; padding: 8px 0; }

.rhythm-card { background: rgba(17,24,39,0.4) !important; border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 16px; }
.rhythm-speed { display: flex; gap: 6px; font-size: 0.95rem; margin-bottom: 8px; align-items: center; }
.rhythm-speed .speed-val { font-weight: 700; font-size: 1rem; }
.rhythm-advice { font-size: 0.82rem; color: var(--text-muted); line-height: 1.55; margin-bottom: 12px; }
.rhythm-pauses { font-size: 0.8rem; color: var(--text-muted); }
.rhythm-pauses ul { margin: 6px 0 0 16px; }
.rhythm-pauses li { margin-bottom: 4px; }
.rhythm-pauses strong { color: var(--text-secondary); }
.pause-title { font-weight: 600; display: block; margin-bottom: 4px; }
.rhythm-ok { display: flex; align-items: center; gap: 6px; font-size: 0.82rem; color: var(--accent-color); }

.grammar-card { background: rgba(17,24,39,0.4) !important; border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 16px; }
.grammar-ok { display: flex; align-items: center; gap: 8px; }
.correct-icon { font-size: 1.2rem; color: var(--accent-color); }
.correct-desc { font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5; margin: 0; }
.fix-row { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }
.badge { align-self: flex-start; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; }
.badge-red { background: rgba(239,68,68,0.15); color: #f87171; }
.badge-green { background: rgba(16,185,129,0.15); color: #34d399; }
.fix-text { padding: 8px 12px; border-radius: 8px; font-size: 0.85rem; line-height: 1.45; margin: 0; }
.red-text { background: rgba(239,68,68,0.04); color: #fca5a5; text-decoration: line-through rgba(239,68,68,0.3); }
.green-text { background: rgba(16,185,129,0.04); color: #a7f3d0; }
.explanation { border-top: 1px dotted rgba(255,255,255,0.06); padding-top: 12px; margin-top: 4px; }
.exp-title { font-size: 0.75rem; color: var(--text-muted); font-weight: 600; display: block; margin-bottom: 4px; }
.exp-text { font-size: 0.82rem; color: var(--text-secondary); line-height: 1.5; margin: 0; }

.suggestions { display: flex; flex-direction: column; gap: 10px; margin-top: 8px; }
.sug-card { border-radius: 8px; padding: 12px 14px; transition: background 0.2s; }
.sug-card:hover { filter: brightness(1.1); }
.sug-card p { font-size: 0.8rem; color: var(--text-secondary); line-height: 1.55; margin: 6px 0 0 0; }
.sug-title { display: flex; align-items: center; gap: 6px; font-size: 0.82rem; font-weight: 700; }
.grammar-sug { background: rgba(99,102,241,0.06); border: 1px solid rgba(99,102,241,0.12); border-left: 3px solid rgba(99,102,241,0.5); }
.vocab-sug { background: rgba(16,185,129,0.06); border: 1px solid rgba(16,185,129,0.12); border-left: 3px solid rgba(16,185,129,0.5); }
.pron-sug { background: rgba(235,179,188,0.06); border: 1px solid rgba(235,179,188,0.12); border-left: 3px solid rgba(235,179,188,0.5); }

.warning-text { color: var(--warning-color) !important; }
.gradient-text { background: linear-gradient(135deg,var(--primary-color),var(--secondary-color)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }

/* 紧凑模式 */
.eval-compact .eval-content { gap: 20px; }
.eval-compact .eval-sec-title { font-size: 0.85rem; margin-bottom: 10px; }
.eval-compact .score-grid { gap: 8px; }
.eval-compact .score-cell { padding: 10px 8px; }
.eval-compact .score-value { font-size: 1.05rem; }
.eval-compact .eval-empty p { font-size: 0.82rem; }

.eval-loading { display: flex; align-items: center; justify-content: center; border: 1px solid rgba(255,255,255,0.08); background: rgba(30,41,59,0.2); border-radius: 12px; margin-bottom: 24px; }
</style>

<template>
  <div class="analytics-container">
    <!-- Header -->
    <header class="analytics-header">
      <h1 class="text-gradient page-title">口语数据分析看板</h1>
      <p class="subtitle">追溯口语技能演变过程，量化并可视化您的每一次流利度与发音飞跃</p>
    </header>

    <!-- Loading State -->
    <div v-if="loading" v-loading="loading" element-loading-background="transparent" class="loading-wrapper"></div>

    <template v-else>
      <!-- KPI Stats Grid -->
      <div class="stats-grid">
        <div class="stat-card glass-card hover-glow">
          <div class="stat-icon-wrapper blue-icon">
            <el-icon><Compass /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-label">累计演练会话</span>
            <h2 class="stat-value font-display">{{ stats.totalSessions }} <span class="unit">次</span></h2>
          </div>
        </div>

        <div class="stat-card glass-card hover-glow">
          <div class="stat-icon-wrapper green-icon">
            <el-icon><ChatDotRound /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-label">累计练习句数</span>
            <h2 class="stat-value font-display">{{ stats.totalSentences }} <span class="unit">句</span></h2>
          </div>
        </div>

        <div class="stat-card glass-card hover-glow">
          <div class="stat-icon-wrapper orange-icon">
            <el-icon><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-label">口语总练习词数</span>
            <h2 class="stat-value font-display">{{ stats.totalWords }} <span class="unit">词</span></h2>
          </div>
        </div>

        <div class="stat-card glass-card hover-glow">
          <div class="stat-icon-wrapper purple-icon">
            <el-icon><Histogram /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-label">历史发音均分</span>
            <h2 class="stat-value font-display text-gradient">{{ stats.avgScore }} <span class="unit">分</span></h2>
          </div>
        </div>
      </div>

      <!-- Charts Grid -->
      <div class="charts-row">
        <!-- Growth Trend Chart -->
        <div class="chart-card glass-card trend-card">
          <h3 class="chart-title">口语核心维度成长曲线</h3>
          <div class="chart-container">
            <div ref="trendChartRef" class="echart-div trend-echart"></div>
          </div>
        </div>

        <!-- Scenario & Consistency Grid -->
        <div class="side-charts-col">
          <!-- Scenario distribution -->
          <div class="chart-card glass-card pie-card">
            <h3 class="chart-title">演练场景热度分布</h3>
            <div class="chart-container">
              <div ref="sceneChartRef" class="echart-div"></div>
            </div>
          </div>

          <!-- Practice calendar/heatmap -->
          <div class="chart-card glass-card calendar-card">
            <h3 class="chart-title">近30日口语坚持打卡</h3>
            <div class="calendar-grid">
              <div 
                v-for="day in calendarDays" 
                :key="day.dateStr" 
                :class="['calendar-cell', { 'has-practice': day.count > 0 }]"
                :title="`${day.dateStr}: 练习了 ${day.count} 次`"
              >
                <span class="cell-day">{{ day.dayNum }}</span>
              </div>
            </div>
            <div class="calendar-footer">
              <span class="legend-item"><span class="legend-dot empty-dot"></span> 未打卡</span>
              <span class="legend-item"><span class="legend-dot active-dot"></span> 已练习</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Row 2: Rhythm & Fluency Analysis -->
      <div class="charts-row secondary-charts-row">
        <!-- Speaking speed WPM Trend -->
        <div class="chart-card glass-card half-card">
          <h3 class="chart-title">平均语速演变趋势 (Speaking Speed)</h3>
          <div class="chart-container">
            <div ref="rhythmChartRef" class="echart-div"></div>
          </div>
        </div>

        <!-- Long pauses per sentence -->
        <div class="chart-card glass-card half-card">
          <h3 class="chart-title">均句不自然长停顿频率 (Long Pauses)</h3>
          <div class="chart-container">
            <div ref="pausesChartRef" class="echart-div"></div>
          </div>
        </div>
      </div>

      <!-- Row 3: Diagnosis & Review -->
      <div class="charts-row secondary-charts-row">
        <!-- Pronunciation Hard Words review wall -->
        <div class="chart-card glass-card half-card hard-words-card">
          <h3 class="chart-title">发音难词回顾与跟读攻坚墙 (Hard Words)</h3>
          <div class="hard-words-container" v-if="hardWords.length > 0">
            <div 
              v-for="(w, wIdx) in hardWords" 
              :key="wIdx"
              class="hard-word-badge clickable-badge hover-scale"
              @click="playWordTts(w.word)"
              title="点击播放标准音跟读"
            >
              <span class="word-name">{{ w.word }}</span>
              <div class="word-meta">
                <span class="word-score">{{ w.avgScore }}分</span>
                <span class="word-count">{{ w.count }}次</span>
              </div>
            </div>
          </div>
          <div class="hard-words-empty" v-else>
            <el-icon class="all-perfect-icon"><SuccessFilled /></el-icon>
            <span class="empty-text">太棒了！所有录音单词发音良好 (无评分 &lt; 75 分的单词)！🎉</span>
          </div>
        </div>

        <!-- AI Grammar Error distribution -->
        <div class="chart-card glass-card half-card">
          <h3 class="chart-title">AI 语法错误类别剖析 (Grammar Errors)</h3>
          <div class="chart-container">
            <div ref="grammarPieRef" class="echart-div"></div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'
import { useAppStore } from '../store/useAppStore'

const store = useAppStore()
const loading = ref(true)

const stats = ref({
  totalSessions: 0,
  totalSentences: 0,
  totalWords: 0,
  avgScore: 0
})

const calendarDays = ref([])
const trendChartRef = ref(null)
const sceneChartRef = ref(null)
const rhythmChartRef = ref(null)
const pausesChartRef = ref(null)
const grammarPieRef = ref(null)

const hardWords = ref([])

let trendChartInstance = null
let sceneChartInstance = null
let rhythmChartInstance = null
let pausesChartInstance = null
let grammarPieInstance = null
let historyData = []

// 获取场景友好名称
const getSceneName = (sceneId) => {
  const mapping = {
    'interview': '软件工程师面试',
    'ordering': '繁忙咖啡厅点餐',
    'meeting': '产品发布会同步会议'
  }
  return mapping[sceneId] || '自定义场景'
}

// 格式化日期
const formatDateShort = (dateStr) => {
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await axios.get(`${store.backendBaseUrl}/api/dialogues/`, {
      params: { user_id: 1 }
    })
    
    // 只要该会话包含至少一个有发音评分的用户轮次，就纳入统计，兼容未结算但已练习的会话
    historyData = res.data.filter(h => {
      return h.turns && h.turns.some(t => t.role === 'user' && t.pronunciation_score)
    })
    
    // Sort chronologically (oldest first for trend charts)
    historyData.sort((a, b) => new Date(a.start_time) - new Date(b.start_time))
    
    // 1. KPI 统计
    stats.value.totalSessions = historyData.length
    
    let totalSentencesCount = 0
    let totalWordsCount = 0
    let totalScoresSum = 0
    let scoresCount = 0

    historyData.forEach(session => {
      // 如果已结算，取 overall_score；如果未结算，则实时累加计算当前会话所有有效轮次的均分
      let sessionScore = session.overall_score
      if (!sessionScore) {
        const turnsWithScore = session.turns.filter(t => t.role === 'user' && t.pronunciation_score)
        if (turnsWithScore.length > 0) {
          const sum = turnsWithScore.reduce((acc, curr) => acc + (curr.pronunciation_score.total_score || 0), 0)
          sessionScore = roundOneDecimal(sum / turnsWithScore.length)
        }
      }

      if (sessionScore) {
        totalScoresSum += sessionScore
        scoresCount++
      }
      
      const userTurns = session.turns.filter(t => t.role === 'user')
      totalSentencesCount += userTurns.length
      
      userTurns.forEach(turn => {
        if (turn.text) {
          totalWordsCount += turn.text.split(/\s+/).filter(Boolean).length
        }
      })
    })

    stats.value.totalSentences = totalSentencesCount
    stats.value.totalWords = totalWordsCount
    stats.value.avgScore = scoresCount > 0 ? roundOneDecimal(totalScoresSum / scoresCount) : 0.0

    // 2. 近30天练习打卡计算
    generateCalendarData(historyData)

    // 3. 计算发音难词库 (< 75分)
    calculateHardWords(historyData)
  } catch (err) {
    console.error('获取成长看板数据失败:', err)
  } finally {
    loading.value = false
    // 必须在 loading.value = false 触发 DOM 挂载之后，在 nextTick 中进行 ECharts 初始化绑定，确保获取到非空的 DOM 容器引用
    nextTick(() => {
      initCharts()
    })
  }
}

const roundOneDecimal = (num) => {
  return Math.round(num * 10) / 10
}

// 生成近30天打卡分布
const generateCalendarData = (sessions) => {
  const days = []
  const today = new Date()
  
  // 建立一个日期计数哈希表
  const dateMap = {}
  sessions.forEach(s => {
    const dateKey = new Date(s.start_time).toDateString()
    dateMap[dateKey] = (dateMap[dateKey] || 0) + 1
  })

  // 生成从 29 天前到今天的全部日期
  for (let i = 29; i >= 0; i--) {
    const targetDate = new Date()
    targetDate.setDate(today.getDate() - i)
    
    const dateStr = targetDate.toLocaleDateString()
    const dateKey = targetDate.toDateString()
    days.push({
      dateStr: dateStr,
      dayNum: targetDate.getDate(),
      count: dateMap[dateKey] || 0
    })
  }
  calendarDays.value = days
}

// 单词跟读播放
const playWordTts = (word) => {
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(word)
  const targetLang = 'en-US'
  utterance.lang = targetLang
  
  if (window.speechSynthesis) {
    const voices = window.speechSynthesis.getVoices()
    let bestVoice = voices.find(v => v.lang === targetLang)
    if (!bestVoice) {
      bestVoice = voices.find(v => v.lang.startsWith(targetLang))
    }
    if (bestVoice) {
      utterance.voice = bestVoice
    }
  }
  window.speechSynthesis.speak(utterance)
}

// 汇总发音难词 (平均分 < 75 分且出现低分的单词)
const calculateHardWords = (sessions) => {
  const wordStats = {}
  sessions.forEach(s => {
    s.turns.filter(t => t.role === 'user' && t.pronunciation_score && t.pronunciation_score.words).forEach(t => {
      t.pronunciation_score.words.forEach(w => {
        const clean = w.word.toLowerCase().replace(/^[.,?!\"();:\[\]{}*#_`~']+|[.,?!\"();:\[\]{}*#_`~']+$/g, '').trim()
        if (!clean || w.score >= 75) return
        
        if (!wordStats[clean]) {
          wordStats[clean] = { word: clean, origCase: w.word, totalScore: 0, count: 0 }
        }
        wordStats[clean].totalScore += w.score
        wordStats[clean].count += 1
      })
    })
  })
  
  const list = Object.values(wordStats).map(o => ({
    word: o.origCase,
    avgScore: roundOneDecimal(o.totalScore / o.count),
    count: o.count
  }))
  
  // 先按低分次数排序，再按平均分排序（低分在前）
  list.sort((a, b) => b.count - a.count || a.avgScore - b.avgScore)
  hardWords.value = list.slice(0, 15) // 最多展示 15 个最难发音的单词
}

// 计算每会话的平均语速 WPM
const getSessionAvgWpm = (session) => {
  const userTurns = session.turns.filter(t => t.role === 'user' && t.pronunciation_score && t.pronunciation_score.words && t.pronunciation_score.words.length > 0)
  if (userTurns.length === 0) return 0
  
  let totalWpm = 0
  let validTurns = 0
  
  userTurns.forEach(turn => {
    const words = turn.pronunciation_score.words
    if (words.length >= 2) {
      const firstWord = words[0]
      const lastWord = words[words.length - 1]
      const durationFrames = lastWord.end_pos - firstWord.beg_pos
      if (durationFrames > 0) {
        const durationSeconds = durationFrames * 0.01
        const wpm = (words.length / durationSeconds) * 60
        totalWpm += wpm
        validTurns++
      }
    }
  })
  
  return validTurns > 0 ? Math.round(totalWpm / validTurns) : 0
}

// 计算每会话的平均长停顿（>0.8秒）次数
const getSessionAvgPauses = (session) => {
  const userTurns = session.turns.filter(t => t.role === 'user' && t.pronunciation_score && t.pronunciation_score.words && t.pronunciation_score.words.length > 0)
  if (userTurns.length === 0) return 0
  
  let totalPauses = 0
  let validTurns = 0
  
  userTurns.forEach(turn => {
    const words = turn.pronunciation_score.words
    let pauseCount = 0
    for (let i = 0; i < words.length - 1; i++) {
      const curWord = words[i]
      const nextWord = words[i + 1]
      if (curWord.end_pos > 0 && nextWord.beg_pos > 0) {
        const gap = nextWord.beg_pos - curWord.end_pos
        if (gap > 80) {
          pauseCount++
        }
      }
    }
    totalPauses += pauseCount
    validTurns++
  })
  
  return validTurns > 0 ? roundOneDecimal(totalPauses / validTurns) : 0
}

// 汇总统计语法错误的大类别分布比例
const getGrammarErrorDistribution = (sessions) => {
  const counts = {
    verb: 0,
    plural: 0,
    article: 0,
    preposition: 0,
    other: 0
  }
  
  sessions.forEach(s => {
    s.turns.filter(t => t.role === 'user' && t.grammar_correction).forEach(t => {
      const gc = t.grammar_correction
      if (gc.original.toLowerCase().trim() !== gc.corrected.toLowerCase().trim()) {
        const exp = (gc.explanation || "").toLowerCase()
        if (exp.includes("时态") || exp.includes("动词") || exp.includes("过去") || exp.includes("进行") || exp.includes("完成") || exp.includes("verb") || exp.includes("tense")) {
          counts.verb++
        } else if (exp.includes("单复") || exp.includes("复数") || exp.includes("单数") || exp.includes("plural")) {
          counts.plural++
        } else if (exp.includes("冠词") || exp.includes("article")) {
          counts.article++
        } else if (exp.includes("介词") || exp.includes("preposition")) {
          counts.preposition++
        } else {
          counts.other++
        }
      }
    })
  })
  
  return [
    { name: '时态动词 (Verb)', value: counts.verb },
    { name: '名词单复数 (Plural)', value: counts.plural },
    { name: '冠词偏误 (Article)', value: counts.article },
    { name: '介词错用 (Preposition)', value: counts.preposition },
    { name: '其它语法细节 (Others)', value: counts.other }
  ]
}

// 初始化图表
const initCharts = () => {
  if (historyData.length === 0) return

  // ---- (1) Growth Trend Chart ----
  if (trendChartRef.value) {
    if (trendChartInstance) trendChartInstance.dispose()
    trendChartInstance = echarts.init(trendChartRef.value)
    
    // 准备数据：X轴是时间，Y轴是各维度均分
    const dates = historyData.map(h => formatDateShort(h.start_time))
    
    // 折线维度提取
    const overallScores = historyData.map(h => {
      if (h.overall_score) return h.overall_score
      const turns = h.turns.filter(t => t.role === 'user' && t.pronunciation_score)
      if (turns.length === 0) return 0
      const sum = turns.reduce((acc, curr) => acc + (curr.pronunciation_score.total_score || 0), 0)
      return roundOneDecimal(sum / turns.length)
    })
    
    const accuracyScores = historyData.map(h => {
      const turns = h.turns.filter(t => t.role === 'user' && t.pronunciation_score)
      if (turns.length === 0) return h.overall_score || 0
      const sum = turns.reduce((acc, curr) => acc + (curr.pronunciation_score.accuracy_score || 0), 0)
      return roundOneDecimal(sum / turns.length)
    })

    const fluencyScores = historyData.map(h => {
      const turns = h.turns.filter(t => t.role === 'user' && t.pronunciation_score)
      if (turns.length === 0) return h.overall_score || 0
      const sum = turns.reduce((acc, curr) => acc + (curr.pronunciation_score.fluency_score || 0), 0)
      return roundOneDecimal(sum / turns.length)
    })

    const integrityScores = historyData.map(h => {
      const turns = h.turns.filter(t => t.role === 'user' && t.pronunciation_score)
      if (turns.length === 0) return h.overall_score || 0
      const sum = turns.reduce((acc, curr) => acc + (curr.pronunciation_score.integrity_score || 0), 0)
      return roundOneDecimal(sum / turns.length)
    })

    const intonationScores = historyData.map(h => {
      const turns = h.turns.filter(t => t.role === 'user' && t.pronunciation_score)
      if (turns.length === 0) return h.overall_score || 0
      const sum = turns.reduce((acc, curr) => acc + (curr.pronunciation_score.intonation_score !== undefined ? curr.pronunciation_score.intonation_score : (curr.pronunciation_score.fluency_score || 0)), 0)
      return roundOneDecimal(sum / turns.length)
    })

    const liaisonScores = historyData.map(h => {
      const turns = h.turns.filter(t => t.role === 'user' && t.pronunciation_score)
      if (turns.length === 0) return h.overall_score || 0
      const sum = turns.reduce((acc, curr) => acc + (curr.pronunciation_score.liaison_score !== undefined ? curr.pronunciation_score.liaison_score : (curr.pronunciation_score.accuracy_score || 0)), 0)
      return roundOneDecimal(sum / turns.length)
    })

    const trendOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(17, 24, 39, 0.95)',
        borderColor: 'rgba(99, 102, 241, 0.3)',
        borderWidth: 1,
        textStyle: { color: '#f3f4f6', fontSize: 12 }
      },
      legend: {
        data: ['综合发音分', '发音准确度', '发音流利度', '发音完整度', '语调与重音', '连读与爆破'],
        textStyle: { color: '#9ca3af', fontSize: 11 },
        top: 0
      },
      grid: {
        top: '12%',
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: dates,
        axisLabel: { color: '#9ca3af', fontSize: 10 },
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } }
      },
      yAxis: {
        type: 'value',
        min: 40,
        max: 100,
        axisLabel: { color: '#9ca3af', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } }
      },
      series: [
        {
          name: '综合发音分',
          type: 'line',
          data: overallScores,
          smooth: true,
          symbolSize: 6,
          lineStyle: { width: 3, color: '#6366f1' },
          itemStyle: { color: '#6366f1' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(99, 102, 241, 0.25)' },
              { offset: 1, color: 'rgba(99, 102, 241, 0.0)' }
            ])
          }
        },
        {
          name: '发音准确度',
          type: 'line',
          data: accuracyScores,
          smooth: true,
          symbol: 'circle',
          lineStyle: { width: 2, color: '#10b981' },
          itemStyle: { color: '#10b981' }
        },
        {
          name: '发音流利度',
          type: 'line',
          data: fluencyScores,
          smooth: true,
          lineStyle: { width: 2, color: '#f59e0b' },
          itemStyle: { color: '#f59e0b' }
        },
        {
          name: '发音完整度',
          type: 'line',
          data: integrityScores,
          smooth: true,
          lineStyle: { width: 2, color: '#ec4899' },
          itemStyle: { color: '#ec4899' }
        },
        {
          name: '语调与重音',
          type: 'line',
          data: intonationScores,
          smooth: true,
          lineStyle: { width: 2, color: '#c084fc' },
          itemStyle: { color: '#c084fc' }
        },
        {
          name: '连读与爆破',
          type: 'line',
          data: liaisonScores,
          smooth: true,
          lineStyle: { width: 2, color: '#f472b6' },
          itemStyle: { color: '#f472b6' }
        }
      ]
    }
    trendChartInstance.setOption(trendOption)
  }

  // ---- (2) Scenario Pie Chart ----
  if (sceneChartRef.value) {
    if (sceneChartInstance) sceneChartInstance.dispose()
    sceneChartInstance = echarts.init(sceneChartRef.value)

    const sceneCounts = {}
    historyData.forEach(h => {
      const name = getSceneName(h.scene_id)
      sceneCounts[name] = (sceneCounts[name] || 0) + 1
    })

    const pieData = Object.keys(sceneCounts).map(name => ({
      name: name,
      value: sceneCounts[name]
    }))

    const pieOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c}次 ({d}%)',
        backgroundColor: 'rgba(17, 24, 39, 0.95)',
        borderColor: 'rgba(99, 102, 241, 0.3)',
        borderWidth: 1,
        textStyle: { color: '#f3f4f6', fontSize: 12 }
      },
      legend: {
        orient: 'vertical',
        left: 'left',
        textStyle: { color: '#9ca3af', fontSize: 10 },
        top: 'middle'
      },
      series: [
        {
          name: '演练场景',
          type: 'pie',
          radius: ['45%', '70%'],
          center: ['65%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 6,
            borderColor: '#111827',
            borderWidth: 2
          },
          label: {
            show: false,
            position: 'center'
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 12,
              fontWeight: 'bold',
              color: '#fff'
            }
          },
          labelLine: {
            show: false
          },
          data: pieData,
          color: ['#6366f1', '#10b981', '#f59e0b', '#ec4899', '#3b82f6']
        }
      ]
    }
    sceneChartInstance.setOption(pieOption)
  }

  // ---- (3) WPM Trend Chart ----
  if (rhythmChartRef.value) {
    if (rhythmChartInstance) rhythmChartInstance.dispose()
    rhythmChartInstance = echarts.init(rhythmChartRef.value)

    const dates = historyData.map(h => formatDateShort(h.start_time))
    const wpmData = historyData.map(h => getSessionAvgWpm(h))

    const rhythmOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(17, 24, 39, 0.95)',
        borderColor: 'rgba(99, 102, 241, 0.3)',
        borderWidth: 1,
        textStyle: { color: '#f3f4f6', fontSize: 12 }
      },
      grid: {
        top: '15%',
        left: '4%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: dates,
        axisLabel: { color: '#9ca3af', fontSize: 10 },
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } }
      },
      yAxis: {
        type: 'value',
        min: 60,
        max: 200,
        axisLabel: { color: '#9ca3af', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } }
      },
      series: [
        {
          name: '平均语速 (WPM)',
          type: 'line',
          data: wpmData,
          smooth: true,
          symbolSize: 6,
          lineStyle: { width: 3, color: '#3b82f6' },
          itemStyle: { color: '#3b82f6' },
          markArea: {
            silent: true,
            itemStyle: {
              color: 'rgba(16, 185, 129, 0.04)'
            },
            data: [
              [
                { name: '推荐语速区间 (110-150 WPM)', yAxis: 110 },
                { yAxis: 150 }
              ]
            ],
            label: {
              position: 'insideRight',
              color: 'rgba(16, 185, 129, 0.4)',
              fontSize: 9
            }
          }
        }
      ]
    }
    rhythmChartInstance.setOption(rhythmOption)
  }

  // ---- (4) Pause Frequency Bar Chart ----
  if (pausesChartRef.value) {
    if (pausesChartInstance) pausesChartInstance.dispose()
    pausesChartInstance = echarts.init(pausesChartRef.value)

    const dates = historyData.map(h => formatDateShort(h.start_time))
    const pauseData = historyData.map(h => getSessionAvgPauses(h))

    const pausesOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(17, 24, 39, 0.95)',
        borderColor: 'rgba(99, 102, 241, 0.3)',
        borderWidth: 1,
        textStyle: { color: '#f3f4f6', fontSize: 12 }
      },
      grid: {
        top: '15%',
        left: '4%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { color: '#9ca3af', fontSize: 10 },
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } }
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#9ca3af', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } }
      },
      series: [
        {
          name: '均句长停顿次数',
          type: 'bar',
          barWidth: '35%',
          data: pauseData,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(245, 158, 11, 0.8)' },
              { offset: 1, color: 'rgba(245, 158, 11, 0.2)' }
            ]),
            borderRadius: [4, 4, 0, 0]
          }
        }
      ]
    }
    pausesChartInstance.setOption(pausesOption)
  }

  // ---- (5) Grammar Errors Donut Chart ----
  if (grammarPieRef.value) {
    if (grammarPieInstance) grammarPieInstance.dispose()
    grammarPieInstance = echarts.init(grammarPieRef.value)

    const gData = getGrammarErrorDistribution(historyData)
    const totalErrors = gData.reduce((acc, curr) => acc + curr.value, 0)
    const displayData = totalErrors > 0 ? gData : [
      { name: '暂无偏误分类记录', value: 1 }
    ]

    const grammarOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        formatter: totalErrors > 0 ? '{b}: {c}次 ({d}%)' : '暂无错误数据',
        backgroundColor: 'rgba(17, 24, 39, 0.95)',
        borderColor: 'rgba(99, 102, 241, 0.3)',
        borderWidth: 1,
        textStyle: { color: '#f3f4f6', fontSize: 12 }
      },
      legend: {
        orient: 'vertical',
        left: 'left',
        textStyle: { color: '#9ca3af', fontSize: 10 },
        top: 'middle'
      },
      series: [
        {
          name: '语法偏误',
          type: 'pie',
          radius: ['45%', '70%'],
          center: ['65%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 6,
            borderColor: '#111827',
            borderWidth: 2
          },
          label: {
            show: false,
            position: 'center'
          },
          emphasis: {
            label: {
              show: totalErrors > 0,
              fontSize: 11,
              fontWeight: 'bold',
              color: '#fff'
            }
          },
          labelLine: {
            show: false
          },
          data: displayData,
          color: totalErrors > 0 ? ['#f87171', '#fbbf24', '#60a5fa', '#a78bfa', '#9ca3af'] : ['rgba(255,255,255,0.06)']
        }
      ]
    }
    grammarPieInstance.setOption(grammarOption)
  }
}

const handleResize = () => {
  if (trendChartInstance) trendChartInstance.resize()
  if (sceneChartInstance) sceneChartInstance.resize()
  if (rhythmChartInstance) rhythmChartInstance.resize()
  if (pausesChartInstance) pausesChartInstance.resize()
  if (grammarPieInstance) grammarPieInstance.resize()
}

onMounted(() => {
  fetchData()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (trendChartInstance) trendChartInstance.dispose()
  if (sceneChartInstance) sceneChartInstance.dispose()
  if (rhythmChartInstance) rhythmChartInstance.dispose()
  if (pausesChartInstance) pausesChartInstance.dispose()
  if (grammarPieInstance) grammarPieInstance.dispose()
})
</script>

<style scoped>
.analytics-container {
  padding: 32px;
  height: calc(100vh - 64px);
  overflow-y: auto;
  background-color: var(--bg-color);
}

.analytics-header {
  margin-bottom: 28px;
}

.page-title {
  font-size: 2.2rem;
  font-family: var(--font-display);
  font-weight: 800;
  margin-bottom: 6px;
}

.subtitle {
  color: var(--text-muted);
  font-size: 1.02rem;
}

.loading-wrapper {
  height: 350px;
  display: flex;
  justify-content: center;
  align-items: center;
}

/* KPI Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 28px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px;
  border-radius: 12px;
}

.stat-icon-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 48px;
  height: 48px;
  border-radius: 10px;
  font-size: 1.4rem;
}

.blue-icon {
  background: rgba(99, 102, 241, 0.15);
  color: #818cf8;
  border: 1px solid rgba(99, 102, 241, 0.25);
}

.green-icon {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.25);
}

.orange-icon {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.25);
}

.purple-icon {
  background: rgba(139, 92, 246, 0.15);
  color: #a78bfa;
  border: 1px solid rgba(139, 92, 246, 0.25);
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 0.85rem;
  color: var(--text-muted);
  font-weight: 500;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.1;
}

.stat-value .unit {
  font-size: 0.82rem;
  color: var(--text-muted);
  font-weight: 500;
  margin-left: 2px;
}

/* Charts Grid */
.charts-row {
  display: flex;
  gap: 24px;
  margin-bottom: 28px;
}

.chart-card {
  padding: 24px;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
}

.trend-card {
  flex: 7;
}

.side-charts-col {
  flex: 5;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.chart-title {
  font-size: 1.08rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 18px;
  border-left: 3px solid var(--primary-color);
  padding-left: 8px;
}

.chart-container {
  flex-grow: 1;
  width: 100%;
  position: relative;
}

.echart-div {
  width: 100%;
  height: 280px;
}

.trend-echart {
  height: 480px !important;
}

/* Calendar styling */
.calendar-card {
  padding: 20px 24px;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.calendar-cell {
  aspect-ratio: 1;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: var(--transition-smooth);
}

.calendar-cell .cell-day {
  font-size: 0.72rem;
  color: var(--text-muted);
  font-weight: 500;
}

.calendar-cell.has-practice {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.3) 0%, rgba(16, 185, 129, 0.35) 100%);
  border: 1px solid rgba(16, 185, 129, 0.4);
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.15);
}

.calendar-cell.has-practice .cell-day {
  color: #34d399;
  font-weight: 700;
}

.calendar-cell:hover {
  transform: translateY(-2px);
  border-color: rgba(99, 102, 241, 0.4);
}

.calendar-footer {
  display: flex;
  gap: 16px;
  justify-content: flex-end;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.empty-dot {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.active-dot {
  background: #10b981;
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.5);
}

/* Secondary charts & widgets styling */
.secondary-charts-row {
  margin-top: 24px;
}

.half-card {
  flex: 1;
  min-width: 0; /* Prevents overflow in flexbox */
}

/* Hard words reviews wall */
.hard-words-card {
  display: flex;
  flex-direction: column;
}

.hard-words-container {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  max-height: 280px;
  overflow-y: auto;
  padding: 4px;
}

.hard-word-badge {
  background: rgba(239, 68, 68, 0.06);
  border: 1px solid rgba(239, 68, 68, 0.15);
  border-radius: 8px;
  padding: 8px 12px;
  display: inline-flex;
  flex-direction: column;
  gap: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 80px;
}

.hard-word-badge:hover {
  background: rgba(239, 68, 68, 0.12);
  border-color: rgba(239, 68, 68, 0.35);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.15);
}

.hard-word-badge .word-name {
  font-size: 0.85rem;
  font-weight: 700;
  color: #f87171;
}

.hard-word-badge .word-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.68rem;
  gap: 8px;
}

.hard-word-badge .word-score {
  color: #fbbf24;
  font-weight: 600;
}

.hard-word-badge .word-count {
  color: var(--text-muted);
}

.hard-words-empty {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  color: #34d399;
}

.hard-words-empty .all-perfect-icon {
  font-size: 2.2rem;
}

.hard-words-empty .empty-text {
  font-size: 0.85rem;
  text-align: center;
  opacity: 0.85;
}
</style>

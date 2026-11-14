<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { RadarChart, BarChart } from 'echarts/charts'
import { TooltipComponent, GridComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import AppIcon from '../AppIcon.vue'

echarts.use([RadarChart, BarChart, TooltipComponent, GridComponent, LegendComponent, CanvasRenderer])

const props = defineProps({
  open: { type: Boolean, default: false },
  report: { type: Object, default: null },
})
const emit = defineEmits(['close'])

const radarEl = ref(null)
const trendEl = ref(null)
let radarChart = null
let trendChart = null
let resizeObserver = null

function scoreTier(score) {
  const n = Number(score)
  if (!Number.isFinite(n)) return ''
  if (n >= 85) return 'is-high'
  if (n >= 70) return 'is-mid'
  return 'is-low'
}

function tierText(score) {
  const n = Number(score)
  if (!Number.isFinite(n)) return '待评估'
  if (n >= 85) return '表现优秀'
  if (n >= 70) return '稳步提升'
  return '建议巩固'
}

function rateLabel(level) {
  if (level === 'slow') return '偏慢'
  if (level === 'natural') return '自然适中'
  if (level === 'fast') return '偏快'
  return '适中'
}

const dimensions = computed(() => {
  const r = props.report
  if (!r) return []
  const p = r.pronunciation
  if (!p) {
    return [
      { label: '语法地道度', value: r.grammar_score ?? 0 },
      { label: '任务完成度', value: r.task_score ?? 0 },
    ]
  }
  return [
    { label: '发音准确度', value: p.accuracy_score ?? 0 },
    { label: '口语流利度', value: p.fluency_score ?? 0 },
    { label: '语调韵律', value: p.intonation_score ?? 0 },
    { label: '连读自然度', value: p.liaison_score ?? 0 },
    { label: '表达完整度', value: p.integrity_score ?? 0 },
    { label: '语法地道度', value: r.grammar_score ?? 0 },
  ]
})

function disposeCharts() {
  resizeObserver?.disconnect()
  resizeObserver = null
  radarChart?.dispose()
  radarChart = null
  trendChart?.dispose()
  trendChart = null
}

function renderCharts() {
  disposeCharts()
  if (!props.open || !props.report) return

  if (radarEl.value && dimensions.value.length >= 3) {
    radarChart = echarts.init(radarEl.value)
    radarChart.setOption({
      tooltip: {
        trigger: 'item',
        confine: true,
        backgroundColor: 'rgba(255, 255, 255, 0.96)',
        borderColor: '#e5dff2',
        borderWidth: 1,
        textStyle: { color: '#2d294b', fontSize: 13 },
        formatter: () => {
          const rows = dimensions.value
            .map(d => `<div style="display:flex;justify-content:space-between;gap:16px;line-height:1.7"><span>${d.label}</span><b>${d.value}</b></div>`)
            .join('')
          return `<div style="font-weight:700;margin-bottom:4px;color:#5b43b0">多维能力画像</div>${rows}`
        },
      },
      radar: {
        radius: '52%',
        center: ['50%', '52%'],
        splitNumber: 4,
        axisNameGap: 8,
        axisName: {
          color: '#4e476b',
          fontSize: 12,
          fontWeight: 600,
        },
        splitLine: { lineStyle: { color: '#ece7f7' } },
        splitArea: { areaStyle: { color: ['#fcfbff', '#f7f4fd'] } },
        axisLine: { lineStyle: { color: '#e2dbf3' } },
        indicator: dimensions.value.map(d => ({ name: d.label, max: 100 })),
      },
      series: [
        {
          type: 'radar',
          symbol: 'circle',
          symbolSize: 5,
          lineStyle: { color: '#7c62d2', width: 2 },
          itemStyle: { color: '#6b4ec7' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(124, 98, 210, 0.36)' },
              { offset: 1, color: 'rgba(124, 98, 210, 0.08)' },
            ]),
          },
          data: [
            {
              value: dimensions.value.map(d => d.value),
              name: '多维能力画像',
            },
          ],
        },
      ],
    })
  }

  const turns = props.report.turn_scores || []
  if (trendEl.value && turns.length) {
    trendChart = echarts.init(trendEl.value)
    trendChart.setOption({
      tooltip: {
        trigger: 'axis',
        confine: true,
        axisPointer: { type: 'shadow' },
      },
      legend: {
        top: 0,
        right: 0,
        itemWidth: 11,
        itemHeight: 11,
        textStyle: { fontSize: 12.5, color: '#6e6885' },
      },
      grid: { top: 32, left: 36, right: 12, bottom: 26 },
      xAxis: {
        type: 'category',
        data: turns.map(t => `第${t.turn}轮`),
        axisLine: { lineStyle: { color: '#e5dff2' } },
        axisLabel: { color: '#6e6885', fontSize: 12.5 },
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
        interval: 25,
        splitLine: { lineStyle: { color: '#f2effa', type: 'dashed' } },
        axisLabel: { color: '#8f88a8', fontSize: 11.5 },
      },
      series: [
        {
          name: '准确度',
          type: 'bar',
          barMaxWidth: 14,
          itemStyle: { color: '#8b73dd', borderRadius: [4, 4, 0, 0] },
          data: turns.map(t => t.accuracy),
        },
        {
          name: '流利度',
          type: 'bar',
          barMaxWidth: 14,
          itemStyle: { color: '#45b787', borderRadius: [4, 4, 0, 0] },
          data: turns.map(t => t.fluency),
        },
      ],
    })
  }

  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => {
      radarChart?.resize()
      trendChart?.resize()
    })
    if (radarEl.value) resizeObserver.observe(radarEl.value)
    if (trendEl.value) resizeObserver.observe(trendEl.value)
  }
}

watch(
  () => [props.open, props.report],
  async ([isOpen, rep]) => {
    if (isOpen && rep) {
      await nextTick()
      renderCharts()
    } else {
      disposeCharts()
    }
  },
  { immediate: true },
)

onBeforeUnmount(disposeCharts)
</script>

<template>
  <div v-if="open && report" class="modal-backdrop report-backdrop" @click.self="emit('close')">
    <div class="modal-card report-modal" role="dialog" aria-modal="true" aria-label="练习评测报告">
      <header class="report-head">
        <div class="report-head-left">
          <span class="report-badge"><AppIcon name="sparkles" :size="12" />多维口语练习报告</span>
          <h3>{{ report.scene_name }}</h3>
          <p class="report-sub">共 {{ report.turn_count }} 轮对话 · 目标完成 {{ report.goals_done }} / {{ report.goals_total }}</p>
        </div>
        <div class="report-overall" :class="scoreTier(report.overall_score)">
          <strong>{{ report.overall_score }}</strong>
          <span>{{ tierText(report.overall_score) }}</span>
        </div>
      </header>

      <div class="report-scroll">
        <div class="report-kpis">
          <div class="kpi-card">
            <span>语音总分</span>
            <b>{{ report.pronunciation?.total_score ?? '—' }}</b>
          </div>
          <div class="kpi-card">
            <span>平均语速</span>
            <b>{{ report.pronunciation ? `${report.pronunciation.avg_wpm} WPM` : '—' }}</b>
            <small v-if="report.pronunciation">{{ rateLabel(report.pronunciation.rate_level) }}</small>
          </div>
          <div class="kpi-card">
            <span>语法地道度</span>
            <b>{{ report.grammar_score }}</b>
          </div>
          <div class="kpi-card">
            <span>目标达成</span>
            <b>{{ report.task_score }}%</b>
          </div>
        </div>

        <section v-if="report.pronunciation" class="report-section">
          <div class="report-sec-head">
            <h4>科大讯飞语音多维画像</h4>
            <span>基于 {{ report.pronunciation.voice_turn_count }} 轮语音评测</span>
          </div>
          <div class="report-charts">
            <div class="chart-box">
              <div ref="radarEl" class="echart-canvas"></div>
            </div>
            <div v-if="report.turn_scores?.length" class="chart-box">
              <div ref="trendEl" class="echart-canvas"></div>
            </div>
          </div>
          <div class="report-dims">
            <div v-for="dim in dimensions" :key="dim.label" class="dim-item">
              <div class="dim-top"><span>{{ dim.label }}</span><b :class="scoreTier(dim.value)">{{ dim.value }}</b></div>
              <div class="dim-bar"><i :class="scoreTier(dim.value)" :style="{ width: `${Math.min(100, Math.max(0, dim.value))}%` }" /></div>
            </div>
          </div>
        </section>

        <section v-if="report.weak_words?.length || report.strong_words?.length" class="report-section">
          <h4>逐词发音诊断</h4>
          <div v-if="report.weak_words?.length" class="report-word-group">
            <small>需重点巩固</small>
            <span v-for="w in report.weak_words" :key="`weak-${w.word}`" class="fb-word is-low">{{ w.word }}<small>{{ Math.round(w.score) }}</small></span>
          </div>
          <div v-if="report.strong_words?.length" class="report-word-group">
            <small>发音亮点</small>
            <span v-for="w in report.strong_words" :key="`strong-${w.word}`" class="fb-word is-high">{{ w.word }}<small>{{ Math.round(w.score) }}</small></span>
          </div>
        </section>

        <section v-if="report.corrections?.length" class="report-section">
          <h4>表达优化清单（{{ report.corrections.length }} 处）</h4>
          <ul class="report-corr-list">
            <li v-for="c in report.corrections" :key="c.turn_number">
              <div class="rc-orig">第 {{ c.turn_number }} 轮 · <span>{{ c.original }}</span></div>
              <div class="rc-fix"><AppIcon name="arrow-right" :size="12" /><b>{{ c.corrected }}</b></div>
              <p v-if="c.explanation">{{ c.explanation }}</p>
            </li>
          </ul>
        </section>

        <section v-if="report.tips?.length" class="report-section report-tips">
          <h4>教练建议</h4>
          <ul><li v-for="(tip, idx) in report.tips" :key="idx">{{ tip }}</li></ul>
        </section>
      </div>

      <footer class="report-foot">
        <button class="confirm-button" type="button" @click="emit('close')">知道了</button>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.report-backdrop {
  position: fixed; inset: 0; z-index: 60;
  display: grid; place-items: center; padding: 18px;
  background: rgba(34, 37, 59, .32);
}
.report-modal {
  display: flex; flex-direction: column;
  width: min(680px, 100%); max-height: min(88vh, 800px);
  padding: 0; overflow: hidden;
  border: 1.5px solid #ebe7f5; border-bottom: 5px solid #e5def1; border-radius: 20px;
  background: #fff; text-align: left;
  box-shadow: 0 22px 60px rgba(45, 41, 75, .22);
}
.report-head {
  display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-shrink: 0;
  padding: 20px 26px 16px; border-bottom: 1px solid #f0ecf7; background: #fcfbff;
}
.report-head-left { min-width: 0; }
.report-badge {
  display: inline-flex; align-items: center; gap: 5px; padding: 3px 10px; margin-bottom: 7px;
  border-radius: 999px; background: #efeafc; color: #674bc4; font-size: 12px; font-weight: 650;
}
.report-head h3 { margin: 0; font-size: 18px; font-weight: 750; color: #2d294b; line-height: 1.35; }
.report-sub { margin: 4px 0 0; font-size: 13.5px; color: #7c7693; }
.report-overall {
  display: flex; flex-direction: column; align-items: center; justify-content: center; flex: 0 0 auto;
  min-width: 88px; padding: 10px 16px; border-radius: 14px; border: 1.5px solid #e7e1f5; background: #fff;
}
.report-overall strong { font-size: 30px; line-height: 1.05; font-weight: 800; font-variant-numeric: tabular-nums; }
.report-overall span { margin-top: 4px; font-size: 12px; font-weight: 650; color: #7c7693; }
.report-overall.is-high strong, .report-overall.is-high span { color: #1f7a4c; }
.report-overall.is-mid strong, .report-overall.is-mid span { color: #b45309; }
.report-overall.is-low strong, .report-overall.is-low span { color: #be123c; }

.report-scroll {
  flex: 1; min-height: 0; overflow-y: auto; padding: 18px 26px 10px;
  scrollbar-width: thin; scrollbar-color: #d8d0ec transparent;
}
.report-scroll::-webkit-scrollbar { width: 6px; }
.report-scroll::-webkit-scrollbar-thumb { background: #d8d0ec; border-radius: 999px; }
.report-scroll::-webkit-scrollbar-track { background: transparent; }

.report-kpis {
  display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-bottom: 16px;
}
.kpi-card {
  display: flex; flex-direction: column; gap: 3px;
  padding: 11px 13px; border: 1px solid #ede9f7; border-radius: 12px; background: #faf9fd;
}
.kpi-card span { font-size: 12.5px; color: #7c7693; }
.kpi-card b { font-size: 17px; font-weight: 750; color: #2d294b; font-variant-numeric: tabular-nums; }
.kpi-card small { font-size: 12px; color: #6c52c5; font-weight: 600; }

.report-section { padding: 16px 0; border-top: 1px solid #f0ecf7; }
.report-section h4 { margin: 0 0 11px; font-size: 14.5px; font-weight: 700; color: #2d294b; }
.report-sec-head { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 8px; margin-bottom: 12px; }
.report-sec-head h4 { margin: 0; }
.report-sec-head span { font-size: 12.5px; color: #7c7693; }

.report-charts {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px;
}
.chart-box {
  padding: 10px; border: 1px solid #ede9f7; border-radius: 12px; background: #fcfbff;
}
.echart-canvas { width: 100%; height: 228px; }

.report-dims { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px 18px; }
.dim-item { display: flex; flex-direction: column; gap: 5px; }
.dim-top { display: flex; justify-content: space-between; font-size: 13px; color: #595275; }
.dim-top b { font-weight: 700; font-variant-numeric: tabular-nums; }
.dim-top b.is-high { color: #1f7a4c; }
.dim-top b.is-mid { color: #b45309; }
.dim-top b.is-low { color: #be123c; }
.dim-bar { height: 6px; border-radius: 999px; background: #f1eef8; overflow: hidden; }
.dim-bar i { display: block; height: 100%; border-radius: 999px; background: #8b73dd; }
.dim-bar i.is-high { background: #2c8a5e; }
.dim-bar i.is-mid { background: #d97706; }
.dim-bar i.is-low { background: #e11d48; }

.report-word-group { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 8px; }
.report-word-group > small { font-size: 13px; color: #7c7693; margin-right: 2px; }
.fb-word {
  display: inline-flex; align-items: baseline; gap: 4px; font-size: 13.5px; font-weight: 600;
  color: #393451; padding: 3px 9px; border-radius: 8px; background: #faf9fd; border: 1px solid #ece8f5;
}
.fb-word small { font-size: 11px; font-weight: 650; color: #8c85a6; }
.fb-word.is-high { border-color: #bbf7d0; background: #f0fdf4; color: #166534; }
.fb-word.is-high small { color: #15803d; }
.fb-word.is-low { border-color: #fecdd3; background: #fff1f2; color: #be123c; }
.fb-word.is-low small { color: #e11d48; }

.report-corr-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 9px; }
.report-corr-list li { padding: 11px 13px; border-radius: 11px; background: #faf9fd; border: 1px solid #ece8f5; }
.rc-orig { font-size: 13px; color: #7c7693; }
.rc-orig span { text-decoration: line-through; text-decoration-color: #fda4af; }
.rc-fix { display: flex; align-items: center; gap: 6px; margin-top: 4px; font-size: 14px; color: #2d294b; }
.rc-fix b { font-weight: 650; }
.report-corr-list li p { margin: 5px 0 0; font-size: 13px; line-height: 1.6; color: #6e6885; }
.report-tips ul { margin: 0; padding-left: 18px; display: grid; gap: 6px; font-size: 13.5px; line-height: 1.65; color: #4f486c; }

.report-foot {
  display: flex; justify-content: flex-end; flex-shrink: 0;
  padding: 13px 26px 17px; border-top: 1px solid #f0ecf7; background: #fff;
}
.confirm-button {
  min-width: 100px; height: 38px; padding: 0 20px;
  border: 0; border-bottom: 4px solid #6951b8; border-radius: 11px;
  background: #8b73dd; color: #fff; font-size: 13.5px; font-weight: 700; cursor: pointer;
}
.confirm-button:hover { background: #7d64d1; }

@media (max-width: 600px) {
  .report-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .report-charts, .report-dims { grid-template-columns: 1fr; }
}
</style>

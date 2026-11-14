<template>
  <section class="analytics-page">
    <!-- 游客态：成长分析按账号聚合 -->
    <div v-if="!signedIn" class="analytics-guest">
      <span class="guest-icon"><AppIcon name="chart-line" :size="24" /></span>
      <h2>登录后查看成长分析</h2>
      <p>成长分析按账号聚合你的每一次语音评测、表达纠错与场景任务数据，帮助你看见长期进步。</p>
      <router-link class="primary-button slim" :to="{ name: 'login' }"><AppIcon name="user" :size="15" />去登录</router-link>
    </div>

    <template v-else>
      <!-- 顶部筛选栏 -->
      <header class="analytics-head">
        <div>
          <h2>学习成长轨迹</h2>
          <p>聚合发音多维表现、表达趋势、高频错因与场景分布</p>
        </div>
        <AppTabs v-model="rangeDays" :options="RANGE_TABS" aria-label="统计时间范围" />
      </header>

      <!-- 加载骨架 -->
      <div v-if="loading" class="analytics-skeleton" aria-busy="true" aria-label="正在加载成长分析">
        <div class="kpi-grid">
          <div v-for="n in 4" :key="n" class="kpi-card sk-card"><span class="sk-line w40"></span><span class="sk-line w60"></span></div>
        </div>
        <div class="chart-grid">
          <div v-for="n in 4" :key="n" class="panel sk-panel"><span class="sk-line w40"></span><div class="sk-block"></div></div>
        </div>
      </div>

      <!-- 加载失败 -->
      <div v-else-if="error" class="analytics-empty">
        <span class="empty-icon"><AppIcon name="x" :size="22" /></span>
        <h3>成长分析加载失败</h3>
        <p>{{ error }}</p>
        <button class="ghost-button" type="button" @click="load()"><AppIcon name="rotate" :size="14" />重试</button>
      </div>

      <!-- 空数据 -->
      <div v-else-if="!data || !data.summary?.session_count" class="analytics-empty">
        <span class="empty-icon"><AppIcon name="chart-line" :size="22" /></span>
        <h3>{{ rangeDays === 0 ? '还没有可用的练习数据' : `近 ${rangeDays} 天暂无练习记录` }}</h3>
        <p>完成至少一轮语音或文字场景对话后，这里会自动生成你的多维成长雷达与趋势图。</p>
        <div class="empty-actions">
          <button v-if="rangeDays !== 0" class="ghost-button" type="button" @click="rangeDays = 0">查看全部时间</button>
          <router-link class="primary-button slim" :to="{ name: 'practice' }"><AppIcon name="mic" :size="15" />开始练习</router-link>
        </div>
      </div>

      <!-- 正文看板 -->
      <template v-else>
        <!-- KPI 概览 -->
        <div class="kpi-grid">
          <div class="kpi-card">
            <div class="kpi-top">
              <span>平均发音表现</span>
              <span class="kpi-icon purple"><AppIcon name="mic" :size="15" /></span>
            </div>
            <strong>{{ data.summary.avg_pronunciation ?? '—' }}</strong>
            <small v-if="data.summary.voice_turn_count">
              {{ data.summary.voice_turn_count }} 轮语音 · {{ data.summary.avg_wpm ? `${data.summary.avg_wpm} WPM` : '语速统计中' }}
            </small>
            <small v-else>暂无语音评测轮次</small>
          </div>

          <div class="kpi-card">
            <div class="kpi-top">
              <span>表达地道度</span>
              <span class="kpi-icon mint"><AppIcon name="sparkles" :size="15" /></span>
            </div>
            <strong>{{ data.summary.avg_grammar ?? '—' }}</strong>
            <small>基于对话表达纠错统计</small>
          </div>

          <div class="kpi-card">
            <div class="kpi-top">
              <span>累计对话轮次</span>
              <span class="kpi-icon blue"><AppIcon name="messages" :size="15" /></span>
            </div>
            <strong>{{ data.summary.turn_count }}<em>轮</em></strong>
            <small>共 {{ data.summary.session_count }} 场 · 已完成 {{ data.summary.finished_count }} 场</small>
          </div>

          <div class="kpi-card">
            <div class="kpi-top">
              <span>任务目标完成率</span>
              <span class="kpi-icon amber"><AppIcon name="target" :size="15" /></span>
            </div>
            <strong>{{ data.summary.task_completion_rate !== null ? `${data.summary.task_completion_rate}%` : '—' }}</strong>
            <small v-if="data.summary.goals_total">已完成 {{ data.summary.goals_done }} / {{ data.summary.goals_total }} 个目标</small>
            <small v-else>当前场景暂无目标项</small>
          </div>
        </div>

        <!-- 2x2 图表网格 -->
        <div class="chart-grid">
          <section class="panel">
            <div class="panel-head">
              <h3>多维能力雷达</h3>
              <span>发音与语法综合画像</span>
            </div>
            <div v-if="data.radar?.has_pronunciation" ref="radarEl" class="chart-box" role="img" aria-label="多维能力雷达图"></div>
            <div v-else class="chart-placeholder">
              <AppIcon name="mic" :size="20" />
              <p>使用语音发送对话后，将展示发音准确度、流利度、语调与连读雷达图。</p>
            </div>
          </section>

          <section class="panel">
            <div class="panel-head">
              <h3>每日表现趋势</h3>
              <span>发音均分与表达地道度</span>
            </div>
            <div v-if="data.trend?.length" ref="trendEl" class="chart-box" role="img" aria-label="每日表现趋势折线图"></div>
            <div v-else class="chart-placeholder">
              <AppIcon name="chart-line" :size="20" />
              <p>暂无趋势数据</p>
            </div>
          </section>

          <section class="panel">
            <div class="panel-head">
              <h3>表达错因分布</h3>
              <span>高频优化类型统计</span>
            </div>
            <div v-if="data.error_distribution?.length" ref="errorEl" class="chart-box" role="img" aria-label="表达错因分布柱状图"></div>
            <div v-else class="chart-placeholder">
              <AppIcon name="check" :size="20" />
              <p>所选时段内暂无高频语法/表达错误，继续保持自然输出！</p>
            </div>
          </section>

          <section class="panel">
            <div class="panel-head">
              <h3>场景训练分布</h3>
              <span>各类型对话轮次占比</span>
            </div>
            <div v-if="data.category_distribution?.length" ref="categoryEl" class="chart-box" role="img" aria-label="场景训练分布环形图"></div>
            <div v-else class="chart-placeholder">
              <AppIcon name="compass" :size="20" />
              <p>暂无场景分布数据</p>
            </div>
          </section>
        </div>

        <!-- 高频薄弱发音词 -->
        <section v-if="data.weak_words?.length" class="panel weak-panel">
          <div class="panel-head">
            <h3>高频薄弱发音词</h3>
            <span>近期语音评测平均分低于 85 的单词</span>
          </div>
          <div class="weak-words-list">
            <span v-for="w in data.weak_words" :key="w.word" class="weak-word-chip">
              <b>{{ w.word }}</b>
              <small>{{ Math.round(w.avg_score) }} 分</small>
              <em v-if="w.count > 1">×{{ w.count }}</em>
            </span>
          </div>
        </section>

        <!-- 下一步建议 -->
        <section v-if="data.recommendations?.length" class="panel rec-panel">
          <div class="panel-head">
            <h3>接下来值得练什么</h3>
            <span>基于近期短板自动生成</span>
          </div>
          <div class="rec-grid">
            <div v-for="(rec, idx) in data.recommendations" :key="idx" class="rec-card">
              <div>
                <h4>{{ rec.title }}</h4>
                <p>{{ rec.detail }}</p>
              </div>
              <router-link class="rec-link" :to="{ name: rec.route_name }">
                {{ rec.action_label }} <AppIcon name="arrow-right" :size="14" />
              </router-link>
            </div>
          </div>
        </section>
      </template>
    </template>
  </section>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { RadarChart, LineChart, BarChart, PieChart } from 'echarts/charts'
import { TooltipComponent, GridComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import AppIcon from '../components/AppIcon.vue'
import AppTabs from '../components/AppTabs.vue'
import { getGrowthAnalytics } from '../api/sessions'
import { session } from '../auth/session'
import { usePageLoading } from '../app/loading'

echarts.use([RadarChart, LineChart, BarChart, PieChart, TooltipComponent, GridComponent, LegendComponent, CanvasRenderer])

const RANGE_TABS = [
  { value: 7, label: '近 7 天' },
  { value: 30, label: '近 30 天' },
  { value: 90, label: '近 90 天' },
  { value: 0, label: '全部' },
]

const signedIn = ref(Boolean(session.token))
const rangeDays = ref(30)
const data = ref(null)
const loading = ref(false)
const error = ref('')
const finishLoading = usePageLoading()

const radarEl = ref(null)
const trendEl = ref(null)
const errorEl = ref(null)
const categoryEl = ref(null)

let charts = []
let resizeObserver = null

function disposeCharts() {
  resizeObserver?.disconnect()
  resizeObserver = null
  charts.forEach((c) => c?.dispose())
  charts = []
}

function renderCharts() {
  disposeCharts()
  const d = data.value
  if (!d || !d.summary?.session_count) return

  const tooltipStyle = {
    confine: true,
    backgroundColor: 'rgba(255, 255, 255, 0.96)',
    borderColor: '#e5dff2',
    borderWidth: 1,
    textStyle: { color: '#2d294b', fontSize: 12 },
  }

  // 1. 多维能力雷达
  if (radarEl.value && d.radar?.has_pronunciation) {
    const r = d.radar
    const dims = [
      { name: '准确度', val: r.accuracy ?? 0 },
      { name: '流利度', val: r.fluency ?? 0 },
      { name: '语调', val: r.intonation ?? 0 },
      { name: '连读', val: r.liaison ?? 0 },
      { name: '完整度', val: r.integrity ?? 0 },
      { name: '地道度', val: r.grammar ?? 0 },
    ]
    const chart = echarts.init(radarEl.value)
    chart.setOption({
      tooltip: {
        ...tooltipStyle,
        trigger: 'item',
        formatter: () => dims.map((item) => `${item.name}: <b>${item.val}</b>`).join('<br/>'),
      },
      radar: {
        radius: '64%',
        splitNumber: 4,
        indicator: dims.map((item) => ({ name: item.name, max: 100 })),
        axisName: { color: '#5b5472', fontSize: 11.5, fontWeight: 600 },
        splitArea: { areaStyle: { color: ['#faf8ff', '#ffffff'] } },
        splitLine: { lineStyle: { color: '#ece7f6' } },
        axisLine: { lineStyle: { color: '#e5dff2' } },
      },
      series: [
        {
          type: 'radar',
          symbolSize: 5,
          data: [
            {
              value: dims.map((item) => item.val),
              name: '能力画像',
              lineStyle: { color: '#7a5fd0', width: 2 },
              itemStyle: { color: '#7a5fd0' },
              areaStyle: { color: 'rgba(122, 95, 208, 0.2)' },
            },
          ],
        },
      ],
    })
    charts.push(chart)
  }

  // 2. 每日表现趋势
  if (trendEl.value && d.trend?.length) {
    const chart = echarts.init(trendEl.value)
    chart.setOption({
      tooltip: { ...tooltipStyle, trigger: 'axis' },
      legend: {
        bottom: 0,
        icon: 'circle',
        itemWidth: 8,
        itemHeight: 8,
        textStyle: { color: '#6e6885', fontSize: 11.5 },
      },
      grid: { top: 16, right: 16, bottom: 34, left: 36 },
      xAxis: {
        type: 'category',
        data: d.trend.map((t) => t.date),
        axisLine: { lineStyle: { color: '#e8e4f3' } },
        axisTick: { show: false },
        axisLabel: { color: '#7c7693', fontSize: 11 },
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
        splitLine: { lineStyle: { color: '#f2eff9' } },
        axisLabel: { color: '#9a94b4', fontSize: 11 },
      },
      series: [
        {
          name: '发音均分',
          type: 'line',
          smooth: true,
          connectNulls: true,
          data: d.trend.map((t) => t.pronunciation),
          lineStyle: { color: '#7a5fd0', width: 2.5 },
          itemStyle: { color: '#7a5fd0' },
          areaStyle: { color: 'rgba(122, 95, 208, 0.12)' },
        },
        {
          name: '表达地道度',
          type: 'line',
          smooth: true,
          connectNulls: true,
          data: d.trend.map((t) => t.grammar),
          lineStyle: { color: '#3f8b68', width: 2.5 },
          itemStyle: { color: '#3f8b68' },
          areaStyle: { color: 'rgba(63, 139, 104, 0.1)' },
        },
      ],
    })
    charts.push(chart)
  }

  // 3. 表达错因分布
  if (errorEl.value && d.error_distribution?.length) {
    const list = [...d.error_distribution].reverse()
    const chart = echarts.init(errorEl.value)
    chart.setOption({
      tooltip: { ...tooltipStyle, trigger: 'axis', axisPointer: { type: 'none' } },
      grid: { top: 10, right: 24, bottom: 20, left: 76 },
      xAxis: {
        type: 'value',
        minInterval: 1,
        splitLine: { lineStyle: { color: '#f2eff9' } },
        axisLabel: { color: '#9a94b4', fontSize: 11 },
      },
      yAxis: {
        type: 'category',
        data: list.map((e) => e.label),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#4f486c', fontSize: 11.5 },
      },
      series: [
        {
          name: '出现次数',
          type: 'bar',
          barWidth: 14,
          data: list.map((e) => e.count),
          itemStyle: { color: '#a58ee9', borderRadius: [0, 6, 6, 0] },
        },
      ],
    })
    charts.push(chart)
  }

  // 4. 场景训练分布
  if (categoryEl.value && d.category_distribution?.length) {
    const palette = ['#8b73dd', '#59b98a', '#6489ee', '#e8a35e', '#d97b93', '#7c7693']
    const chart = echarts.init(categoryEl.value)
    chart.setOption({
      tooltip: {
        ...tooltipStyle,
        trigger: 'item',
        formatter: '{b}: {c} 轮 ({d}%)',
      },
      legend: {
        bottom: 0,
        icon: 'circle',
        itemWidth: 8,
        itemHeight: 8,
        textStyle: { color: '#6e6885', fontSize: 11.5 },
      },
      color: palette,
      series: [
        {
          name: '场景分布',
          type: 'pie',
          radius: ['44%', '68%'],
          center: ['50%', '43%'],
          itemStyle: { borderColor: '#fff', borderWidth: 2, borderRadius: 4 },
          label: { show: false },
          data: d.category_distribution.map((c) => ({
            name: c.label,
            value: c.turns,
          })),
        },
      ],
    })
    charts.push(chart)
  }

  if (charts.length && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => {
      charts.forEach((c) => c?.resize())
    })
    ;[radarEl.value, trendEl.value, errorEl.value, categoryEl.value]
      .filter(Boolean)
      .forEach((el) => resizeObserver.observe(el))
  }
}

async function load() {
  if (!signedIn.value) return
  loading.value = true
  error.value = ''
  try {
    const res = await getGrowthAnalytics(rangeDays.value)
    data.value = res.data
  } catch (err) {
    error.value = err?.message || '加载失败，请稍后重试。'
  } finally {
    loading.value = false
    finishLoading()
  }
  if (!error.value && data.value?.summary?.session_count) {
    await nextTick()
    renderCharts()
  }
}

watch(rangeDays, load)
onMounted(() => {
  if (!signedIn.value) {
    finishLoading()
    return
  }
  load()
})
onBeforeUnmount(disposeCharts)
</script>

<style scoped>
.analytics-page { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 14px; overflow-y: auto; padding: 22px clamp(18px, 2.4vw, 34px) 24px; background: #faf9ff; }

.analytics-head { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; }
.analytics-head h2 { margin: 0; color: #2d294b; font-size: 18px; font-weight: 800; }
.analytics-head p { margin: 3px 0 0; color: #7c7693; font-size: 12.5px; }

/* KPI 卡片 */
.kpi-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.kpi-card { padding: 14px 16px; border: 1.5px solid #ebe7f5; border-bottom: 3px solid #e5def1; border-radius: 16px; background: #fff; display: flex; flex-direction: column; gap: 6px; }
.kpi-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; color: #7c7693; font-size: 12px; font-weight: 650; }
.kpi-icon { display: grid; width: 28px; height: 28px; place-items: center; border-radius: 9px; }
.kpi-icon.purple { background: #f0eaff; color: #7a5fd0; }
.kpi-icon.mint { background: #e6f6ee; color: #3f8b68; }
.kpi-icon.blue { background: #e7efff; color: #45618c; }
.kpi-icon.amber { background: #fff3dd; color: #b6813a; }
.kpi-card strong { color: #2d294b; font-size: 24px; font-weight: 800; letter-spacing: -.02em; line-height: 1.15; }
.kpi-card strong em { margin-left: 3px; color: #9a94b4; font-size: 12px; font-style: normal; font-weight: 650; }
.kpi-card small { color: #9a94b4; font-size: 11.5px; }

/* 图表网格 */
.chart-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.panel { padding: 16px 18px; border: 1.5px solid #ebe7f5; border-bottom: 3px solid #e5def1; border-radius: 16px; background: #fff; min-width: 0; }
.panel-head { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; margin-bottom: 10px; }
.panel-head h3 { margin: 0; color: #2d294b; font-size: 14.5px; font-weight: 750; }
.panel-head span { color: #9a94b4; font-size: 11.5px; }
.chart-box { width: 100%; height: 240px; }
.chart-placeholder { height: 240px; display: grid; place-content: center; justify-items: center; gap: 8px; text-align: center; color: #9a94b4; padding: 0 20px; }
.chart-placeholder p { margin: 0; font-size: 12.5px; line-height: 1.6; max-width: 280px; }

/* 薄弱词 */
.weak-words-list { display: flex; flex-wrap: wrap; gap: 8px; }
.weak-word-chip { display: inline-flex; align-items: baseline; gap: 5px; padding: 5px 11px; border-radius: 999px; background: #fff5f7; border: 1px solid #f4d3db; color: #9c4056; font-size: 12.5px; }
.weak-word-chip b { font-weight: 700; }
.weak-word-chip small { font-size: 11px; color: #be123c; }
.weak-word-chip em { font-size: 11px; font-style: normal; color: #9a94b4; }

/* 建议卡片 */
.rec-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.rec-card { display: flex; flex-direction: column; justify-content: space-between; gap: 12px; padding: 14px; border-radius: 13px; background: #faf8ff; border: 1px solid #ece8f6; }
.rec-card h4 { margin: 0 0 6px; color: #393451; font-size: 13.5px; font-weight: 750; }
.rec-card p { margin: 0; color: #6e6885; font-size: 12px; line-height: 1.6; }
.rec-link { display: inline-flex; align-items: center; gap: 4px; align-self: flex-start; color: #654ab8; font-size: 12.5px; font-weight: 700; text-decoration: none; }
.rec-link:hover { text-decoration: underline; }

/* 游客/空态/错误态 */
.analytics-empty, .analytics-guest { display: grid; flex: 1 0 auto; place-content: center; justify-items: center; padding: 48px 20px; border: 2px dashed #d9d0ef; border-radius: 18px; background: #fff; text-align: center; }
.empty-icon, .guest-icon { display: grid; width: 54px; height: 54px; place-items: center; border-radius: 18px; background: #f0eaff; color: #8067d1; }
.analytics-empty h3, .analytics-guest h2 { margin: 14px 0 6px; color: #393451; font-size: 16px; font-weight: 750; }
.analytics-empty p, .analytics-guest p { max-width: 420px; margin: 0 0 16px; color: #8b859f; font-size: 13.5px; line-height: 1.7; text-wrap: pretty; }
.empty-actions { display: flex; align-items: center; gap: 10px; }
.primary-button.slim, .ghost-button { width: auto; height: 38px; margin-top: 0; padding: 0 18px; justify-content: center; gap: 7px; border-radius: 12px; font-weight: 650; }
.ghost-button { border: 1.5px solid #e9e5f1; border-bottom-width: 3px; }
.primary-button.slim { border: 1.5px solid #8067d1; border-bottom: 4px solid #6951b8; background: #8b73dd; }

/* 骨架 */
.analytics-skeleton { display: flex; flex-direction: column; gap: 14px; }
.sk-card { min-height: 98px; justify-content: center; }
.sk-panel { min-height: 290px; display: flex; flex-direction: column; gap: 12px; }
.sk-line { height: 12px; border-radius: 6px; background: linear-gradient(90deg, #f1eef9 25%, #f8f5ff 45%, #f1eef9 65%); background-size: 200% 100%; animation: shimmer 1.3s infinite; }
.sk-line.w40 { width: 40%; }
.sk-line.w60 { width: 60%; height: 22px; }
.sk-block { flex: 1; border-radius: 12px; background: linear-gradient(90deg, #f1eef9 25%, #f8f5ff 45%, #f1eef9 65%); background-size: 200% 100%; animation: shimmer 1.3s infinite; }
@keyframes shimmer { from { background-position: 200% 0; } to { background-position: -200% 0; } }

@media (max-width: 1080px) {
  .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .rec-grid { grid-template-columns: 1fr; }
}
@media (max-width: 780px) {
  .chart-grid { grid-template-columns: 1fr; }
}
</style>

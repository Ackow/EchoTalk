<template>
  <div ref="chartRef" :style="{ width: width, height: height }"></div>
</template>

<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  scoreData: {
    type: Object,
    required: true,
    default: () => ({
      total_score: 0,
      accuracy_score: 0,
      fluency_score: 0,
      integrity_score: 0,
      grammar_score: 100 // 可选，默认为 100 (无语法扣分)
    })
  },
  width: {
    type: String,
    default: '100%'
  },
  height: {
    type: String,
    default: '260px'
  }
})

const chartRef = ref(null)
let chartInstance = null

const initChart = () => {
  if (!chartRef.value) return
  
  if (chartInstance) {
    chartInstance.dispose()
  }
  
  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

const updateChart = () => {
  if (!chartInstance) return
  
  const data = props.scoreData || {}
  const total = data.total_score || 0
  const accuracy = data.accuracy_score || 0
  const fluency = data.fluency_score || 0
  const integrity = data.integrity_score || 0
  const grammar = data.grammar_score !== undefined ? data.grammar_score : total
  
  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      show: true,
      trigger: 'item',
      backgroundColor: 'rgba(17, 24, 39, 0.95)',
      borderColor: 'rgba(99, 102, 241, 0.3)',
      borderWidth: 1,
      textStyle: {
        color: '#f3f4f6',
        fontSize: 12
      },
      padding: [8, 12],
      confine: true
    },
    radar: {
      indicator: [
        { name: '发音准确度', max: 100 },
        { name: '发音流利度', max: 100 },
        { name: '发音完整度', max: 100 },
        { name: '语法规范度', max: 100 },
        { name: '综合发音分', max: 100 }
      ],
      shape: 'polygon',
      radius: '62%',
      center: ['50%', '50%'],
      axisName: {
        color: '#9ca3af',
        fontSize: 11,
        fontWeight: 'bold',
        fontFamily: 'Inter, sans-serif',
        padding: [-4, -4]
      },
      splitArea: {
        areaStyle: {
          color: [
            'rgba(99, 102, 241, 0.01)',
            'rgba(99, 102, 241, 0.02)',
            'rgba(99, 102, 241, 0.04)',
            'rgba(99, 102, 241, 0.06)',
            'rgba(99, 102, 241, 0.08)'
          ].reverse()
        }
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(255, 255, 255, 0.06)',
          width: 1
        }
      },
      axisLine: {
        lineStyle: {
          color: 'rgba(255, 255, 255, 0.06)'
        }
      }
    },
    series: [
      {
        name: '口语评分',
        type: 'radar',
        data: [
          {
            value: [accuracy, fluency, integrity, grammar, total],
            name: '能力得分',
            symbol: 'circle',
            symbolSize: 5,
            itemStyle: {
              color: '#818cf8'
            },
            lineStyle: {
              color: '#6366f1',
              width: 2,
              shadowColor: 'rgba(99, 102, 241, 0.6)',
              shadowBlur: 10
            },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(99, 102, 241, 0.55)' },
                { offset: 1, color: 'rgba(59, 130, 246, 0.12)' }
              ])
            }
          }
        ]
      }
    ]
  }
  
  chartInstance.setOption(option)
}

watch(
  () => props.scoreData,
  () => {
    updateChart()
  },
  { deep: true }
)

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (chartInstance) {
    chartInstance.dispose()
  }
})

const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}
</script>

<style scoped>
</style>

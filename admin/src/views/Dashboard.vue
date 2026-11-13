<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchDashboard } from '../api/admin'

const router = useRouter()
const loading = ref(false)
const stats = ref(null)

const maxTrend = computed(() => {
  const list = stats.value?.turn_trend || []
  return Math.max(1, ...list.map((i) => i.count))
})

function formatTime(val) {
  if (!val) return '-'
  return new Date(val).toLocaleString('zh-CN', { hour12: false })
}

async function loadData() {
  loading.value = true
  try {
    const { data } = await fetchDashboard()
    stats.value = data
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <div v-loading="loading" class="dashboard">
    <el-row :gutter="16" class="kpi-row">
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="never" class="kpi-card" @click="router.push('/users')">
          <div class="kpi-label">注册用户总数</div>
          <div class="kpi-value">{{ stats?.users.total ?? 0 }}</div>
          <div class="kpi-sub">
            管理员 {{ stats?.users.admins ?? 0 }} · 活跃令牌 {{ stats?.users.active_tokens ?? 0 }}
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="never" class="kpi-card" @click="router.push('/avatars')">
          <div class="kpi-label">数字人配置 / 自建角色</div>
          <div class="kpi-value">{{ stats?.avatars.preferences_total ?? 0 }} / {{ stats?.avatars.custom_count ?? 0 }}</div>
          <div class="kpi-sub">
            公开市场 {{ stats?.avatars.public_count ?? 0 }} · 音色 {{ stats?.avatars.voice_count ?? 0 }} 种
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="never" class="kpi-card" @click="router.push('/scenes')">
          <div class="kpi-label">场景包总数</div>
          <div class="kpi-value">{{ stats?.scenes.total ?? 0 }}</div>
          <div class="kpi-sub">
            内置 {{ stats?.scenes.builtin ?? 0 }} · 已发布 {{ stats?.scenes.published ?? 0 }} · 资料 {{ stats?.scenes.documents ?? 0 }}
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="never" class="kpi-card" @click="router.push('/sessions')">
          <div class="kpi-label">对话会话 / 总轮次</div>
          <div class="kpi-value">{{ stats?.sessions.total ?? 0 }} / {{ stats?.sessions.turns ?? 0 }}</div>
          <div class="kpi-sub">
            进行中 {{ stats?.sessions.active ?? 0 }} · 已完成 {{ stats?.sessions.finished ?? 0 }}
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :xs="24" :lg="14">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>近 7 日对话轮次趋势</span>
              <el-button text type="primary" size="small" @click="loadData">刷新</el-button>
            </div>
          </template>
          <div class="trend-chart">
            <div v-for="item in stats?.turn_trend || []" :key="item.date" class="trend-bar-col">
              <div class="trend-count">{{ item.count }}</div>
              <div class="trend-track">
                <div
                  class="trend-fill"
                  :style="{ height: `${Math.round((item.count / maxTrend) * 100)}%` }"
                />
              </div>
              <div class="trend-date">{{ item.date }}</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="10">
        <el-card shadow="never">
          <template #header>
            <span>数字人形象 & 音色热度</span>
          </template>
          <div class="dist-section">
            <div class="dist-title">形象分布</div>
            <el-empty v-if="!stats?.avatars.avatar_distribution?.length" description="暂无偏好数据" :image-size="48" />
            <div v-else class="dist-tags">
              <el-tag
                v-for="item in stats.avatars.avatar_distribution"
                :key="item.avatar_id"
                effect="light"
                size="large"
              >
                {{ item.avatar_id }}：{{ item.count }} 次
              </el-tag>
            </div>
          </div>
          <el-divider />
          <div class="dist-section">
            <div class="dist-title">音色分布</div>
            <el-empty v-if="!stats?.avatars.voice_distribution?.length" description="暂无音色数据" :image-size="48" />
            <div v-else class="dist-tags">
              <el-tag
                v-for="item in stats.avatars.voice_distribution"
                :key="item.voice_style"
                type="success"
                effect="light"
              >
                {{ item.voice_style }}：{{ item.count }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" style="margin-top: 16px">
      <template #header>
        <div class="card-header">
          <span>最近对话会话</span>
          <el-button text type="primary" size="small" @click="router.push('/sessions')">查看全部</el-button>
        </div>
      </template>
      <el-table :data="stats?.recent_sessions || []" stripe size="small">
        <el-table-column prop="username" label="用户" width="130" />
        <el-table-column prop="scene_name" label="场景" min-width="180" />
        <el-table-column prop="turn_count" label="轮次" width="80" align="center" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'finished' ? 'success' : 'warning'" size="small">
              {{ row.status === 'finished' ? '已完成' : '进行中' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最近活跃" width="180">
          <template #default="{ row }">{{ formatTime(row.last_active_at) }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.kpi-card {
  cursor: pointer;
  transition: transform 0.15s ease, border-color 0.15s ease;
}

.kpi-card:hover {
  transform: translateY(-2px);
  border-color: #93c5fd;
}

.kpi-label {
  font-size: 13px;
  color: #64748b;
}

.kpi-value {
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
  margin: 8px 0 4px;
}

.kpi-sub {
  font-size: 12px;
  color: #94a3b8;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.trend-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  height: 180px;
  padding: 8px 12px 0;
  gap: 12px;
}

.trend-bar-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
}

.trend-count {
  font-size: 12px;
  color: #475569;
  margin-bottom: 4px;
}

.trend-track {
  flex: 1;
  width: 100%;
  max-width: 36px;
  background: #f1f5f9;
  border-radius: 6px;
  display: flex;
  align-items: flex-end;
  overflow: hidden;
}

.trend-fill {
  width: 100%;
  background: linear-gradient(180deg, #3b82f6, #6366f1);
  border-radius: 6px;
  min-height: 2px;
  transition: height 0.3s ease;
}

.trend-date {
  font-size: 12px;
  color: #64748b;
  margin-top: 6px;
}

.dist-title {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 10px;
}

.dist-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>

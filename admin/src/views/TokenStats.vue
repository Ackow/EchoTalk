<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { fetchTokenStats, fetchUsers } from '../api/admin'

const loading = ref(false)
const data = ref(null)
const userOptions = ref([])

const query = reactive({
  days: 7,
  category: '',
  model: '',
  user_id: undefined,
  page: 1,
  page_size: 20,
})

const CATEGORY_MAP = {
  chat: '对话生成',
  embedding: '向量嵌入',
  lightrag_llm: '图谱抽取',
}

const maxDailyTokens = computed(() => {
  const list = data.value?.trend || []
  return Math.max(1, ...list.map((i) => i.total_tokens))
})

function fmtNum(n) {
  return Number(n || 0).toLocaleString('zh-CN')
}

function formatTime(val) {
  return val ? new Date(val).toLocaleString('zh-CN', { hour12: false }) : '-'
}

async function loadData() {
  loading.value = true
  try {
    const params = {
      days: query.days,
      category: query.category || undefined,
      model: query.model || undefined,
      user_id: query.user_id || undefined,
      page: query.page,
      page_size: query.page_size,
    }
    const res = await fetchTokenStats(params)
    data.value = res.data
  } finally {
    loading.value = false
  }
}

async function loadUsers() {
  try {
    const res = await fetchUsers({ page: 1, page_size: 100 })
    userOptions.value = res.data.items
  } catch {
    // 忽略用户列表加载失败
  }
}

function handleSearch() {
  query.page = 1
  loadData()
}

onMounted(() => {
  loadData()
  loadUsers()
})
</script>

<template>
  <div v-loading="loading">
    <!-- 筛选栏 -->
    <div class="page-card" style="margin-bottom: 16px">
      <div class="filter-bar" style="margin-bottom: 0">
        <el-radio-group v-model="query.days" @change="handleSearch">
          <el-radio-button :value="7">近 7 天</el-radio-button>
          <el-radio-button :value="14">近 14 天</el-radio-button>
          <el-radio-button :value="30">近 30 天</el-radio-button>
        </el-radio-group>
        <el-select v-model="query.category" placeholder="调用类型" clearable style="width: 140px" @change="handleSearch">
          <el-option v-for="(label, key) in CATEGORY_MAP" :key="key" :label="label" :value="key" />
        </el-select>
        <el-select v-model="query.user_id" placeholder="按用户筛选" clearable filterable style="width: 160px" @change="handleSearch">
          <el-option v-for="u in userOptions" :key="u.id" :label="u.username" :value="u.id" />
        </el-select>
        <el-input
          v-model="query.model"
          placeholder="模型名称"
          clearable
          style="width: 180px"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-button type="primary" icon="Search" @click="handleSearch">查询</el-button>
      </div>
    </div>

    <!-- 汇总 KPI -->
    <el-row :gutter="16">
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="never">
          <div class="kpi-label">累计消耗 Token</div>
          <div class="kpi-value">{{ fmtNum(data?.summary.total_tokens) }}</div>
          <div class="kpi-sub">调用次数 {{ fmtNum(data?.summary.total_calls) }} 次</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="never">
          <div class="kpi-label">今日消耗 Token</div>
          <div class="kpi-value" style="color: #2563eb">{{ fmtNum(data?.summary.today_tokens) }}</div>
          <div class="kpi-sub">UTC 自然日统计</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="never">
          <div class="kpi-label">输入 Token (Prompt)</div>
          <div class="kpi-value">{{ fmtNum(data?.summary.prompt_tokens) }}</div>
          <div class="kpi-sub">
            占比
            {{
              data?.summary.total_tokens
                ? ((data.summary.prompt_tokens / data.summary.total_tokens) * 100).toFixed(1)
                : '0.0'
            }}%
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="never">
          <div class="kpi-label">输出 Token (Completion)</div>
          <div class="kpi-value">{{ fmtNum(data?.summary.completion_tokens) }}</div>
          <div class="kpi-sub">
            占比
            {{
              data?.summary.total_tokens
                ? ((data.summary.completion_tokens / data.summary.total_tokens) * 100).toFixed(1)
                : '0.0'
            }}%
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 趋势 + 类型分布 -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :xs="24" :lg="15">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>每日 Token 消耗趋势（近 {{ query.days }} 天）</span>
            </div>
          </template>
          <div class="trend-chart">
            <el-tooltip
              v-for="item in data?.trend || []"
              :key="item.date"
              :content="`${item.date}: 总计 ${fmtNum(item.total_tokens)} (输入 ${fmtNum(item.prompt_tokens)} / 输出 ${fmtNum(item.completion_tokens)}, ${item.calls} 次)`"
              placement="top"
            >
              <div class="trend-bar-col">
                <div class="trend-count">{{ item.total_tokens ? fmtNum(item.total_tokens) : 0 }}</div>
                <div class="trend-track">
                  <div
                    class="trend-fill"
                    :style="{ height: `${Math.round((item.total_tokens / maxDailyTokens) * 100)}%` }"
                  />
                </div>
                <div class="trend-date">{{ item.date }}</div>
              </div>
            </el-tooltip>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="9">
        <el-card shadow="never" style="height: 100%">
          <template #header><span>按调用类型与模型统计</span></template>
          <div class="sub-block">
            <div class="sub-title">调用类型分布</div>
            <el-empty v-if="!data?.by_category?.length" description="暂无调用记录" :image-size="40" />
            <div v-else class="cat-list">
              <div v-for="c in data.by_category" :key="c.category" class="cat-row">
                <el-tag size="small">{{ CATEGORY_MAP[c.category] || c.category }}</el-tag>
                <span>{{ fmtNum(c.total_tokens) }} tokens · {{ fmtNum(c.calls) }} 次</span>
              </div>
            </div>
          </div>
          <el-divider />
          <div class="sub-block">
            <div class="sub-title">用户消耗排行 Top 10</div>
            <el-empty v-if="!data?.top_users?.length" description="暂无用户消耗记录" :image-size="40" />
            <div v-else class="cat-list">
              <div v-for="(u, idx) in data.top_users" :key="u.user_id" class="cat-row">
                <span>{{ idx + 1 }}. {{ u.username }}</span>
                <span style="font-weight: 600">{{ fmtNum(u.total_tokens) }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 模型明细 -->
    <el-card shadow="never" style="margin-top: 16px">
      <template #header><span>模型消耗汇总</span></template>
      <el-table :data="data?.by_model || []" stripe border size="small">
        <el-table-column prop="model" label="模型名称" min-width="200" />
        <el-table-column label="调用次数" width="120" align="right">
          <template #default="{ row }">{{ fmtNum(row.calls) }}</template>
        </el-table-column>
        <el-table-column label="输入 Token" width="140" align="right">
          <template #default="{ row }">{{ fmtNum(row.prompt_tokens) }}</template>
        </el-table-column>
        <el-table-column label="输出 Token" width="140" align="right">
          <template #default="{ row }">{{ fmtNum(row.completion_tokens) }}</template>
        </el-table-column>
        <el-table-column label="总 Token" width="140" align="right">
          <template #default="{ row }">
            <b>{{ fmtNum(row.total_tokens) }}</b>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 流水明细 -->
    <el-card shadow="never" style="margin-top: 16px">
      <template #header><span>API Token 消耗明细</span></template>
      <el-table :data="data?.logs.items || []" stripe border size="small">
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <el-table-column prop="username" label="用户" width="120" />
        <el-table-column label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ CATEGORY_MAP[row.category] || row.category }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="model" label="模型" min-width="170" show-overflow-tooltip />
        <el-table-column label="Prompt" width="100" align="right">
          <template #default="{ row }">{{ fmtNum(row.prompt_tokens) }}</template>
        </el-table-column>
        <el-table-column label="Completion" width="110" align="right">
          <template #default="{ row }">{{ fmtNum(row.completion_tokens) }}</template>
        </el-table-column>
        <el-table-column label="Total" width="100" align="right">
          <template #default="{ row }">
            <b>{{ fmtNum(row.total_tokens) }}</b>
          </template>
        </el-table-column>
        <el-table-column prop="call_count" label="次数" width="70" align="center" />
        <el-table-column prop="scene_id" label="场景" width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.scene_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="时间" width="175">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.page_size"
          :total="data?.logs.total || 0"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @current-change="loadData"
          @size-change="handleSearch"
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.kpi-label {
  font-size: 13px;
  color: #64748b;
}

.kpi-value {
  font-size: 26px;
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
  height: 190px;
  padding: 8px 8px 0;
  gap: 8px;
  overflow-x: auto;
}

.trend-bar-col {
  flex: 1;
  min-width: 32px;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
}

.trend-count {
  font-size: 11px;
  color: #475569;
  margin-bottom: 4px;
  white-space: nowrap;
}

.trend-track {
  flex: 1;
  width: 100%;
  max-width: 32px;
  background: #f1f5f9;
  border-radius: 6px;
  display: flex;
  align-items: flex-end;
  overflow: hidden;
}

.trend-fill {
  width: 100%;
  background: linear-gradient(180deg, #0ea5e9, #3b82f6);
  border-radius: 6px;
  min-height: 2px;
  transition: height 0.3s ease;
}

.trend-date {
  font-size: 11px;
  color: #64748b;
  margin-top: 6px;
  white-space: nowrap;
}

.sub-title {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 10px;
}

.cat-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cat-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  color: #334155;
}
</style>

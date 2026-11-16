<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  batchDeleteSessions,
  deleteAdminDebateSession,
  deleteSession,
  fetchAdminDebateSessionDetail,
  fetchAdminDebateSessions,
  fetchScenes,
  fetchSessionDetail,
  fetchSessions,
  fetchUsers,
} from '../api/admin'

const sessionMode = ref('practice')
const debateLoading = ref(false)
const debateItems = ref([])
const debateTotal = ref(0)
const debatePage = ref(1)
const debateDrawer = ref(false)
const debateDetail = ref(null)

async function loadDebateSessions() {
  debateLoading.value = true
  try {
    const { data } = await fetchAdminDebateSessions({ page: debatePage.value, page_size: 20 })
    debateItems.value = data.items
    debateTotal.value = data.total
  } finally {
    debateLoading.value = false
  }
}

async function openDebateDetail(row) {
  debateDrawer.value = true
  const { data } = await fetchAdminDebateSessionDetail(row.id)
  debateDetail.value = data
}

async function removeDebateSession(row) {
  await ElMessageBox.confirm(`确认删除多角色会话「${row.topic_title}」？`, '提示', { type: 'warning' })
  await deleteAdminDebateSession(row.id)
  ElMessage.success('已删除')
  loadDebateSessions()
}

const loading = ref(false)
const items = ref([])
const total = ref(0)
const selectedRows = ref([])

const userOptions = ref([])
const sceneOptions = ref([])

const query = reactive({
  q: '',
  user_id: undefined,
  scene_id: undefined,
  status: '',
  page: 1,
  page_size: 20,
})

const drawerVisible = ref(false)
const detailLoading = ref(false)
const detail = ref(null)

function formatTime(val) {
  return val ? new Date(val).toLocaleString('zh-CN', { hour12: false }) : '-'
}

async function loadSessions() {
  loading.value = true
  try {
    const params = {
      page: query.page,
      page_size: query.page_size,
      q: query.q || undefined,
      user_id: query.user_id || undefined,
      scene_id: query.scene_id || undefined,
      status: query.status || undefined,
    }
    const { data } = await fetchSessions(params)
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function loadOptions() {
  const [uRes, sRes] = await Promise.all([
    fetchUsers({ page: 1, page_size: 100 }),
    fetchScenes({ page: 1, page_size: 100 }),
  ])
  userOptions.value = uRes.data.items
  sceneOptions.value = sRes.data.items
}

function handleSearch() {
  query.page = 1
  loadSessions()
}

async function openDetail(row) {
  drawerVisible.value = true
  detailLoading.value = true
  try {
    const { data } = await fetchSessionDetail(row.id)
    detail.value = data
  } finally {
    detailLoading.value = false
  }
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确认删除用户「${row.username}」的这条对话记录吗？`, '删除确认', {
    type: 'warning',
  })
  await deleteSession(row.id)
  ElMessage.success('对话记录已删除')
  loadSessions()
}

async function handleBatchDelete() {
  const ids = selectedRows.value.map((r) => r.id)
  if (!ids.length) return
  await ElMessageBox.confirm(`确认批量删除选中的 ${ids.length} 条对话记录吗？其所有对话轮次将一并删除。`, '批量删除确认', {
    type: 'warning',
  })
  const { data } = await batchDeleteSessions(ids)
  ElMessage.success(`已删除 ${data.deleted} 条对话记录`)
  selectedRows.value = []
  loadSessions()
}

onMounted(() => {
  loadSessions()
  loadOptions()
})
</script>

<template>
  <div class="page-card">
    <el-tabs v-model="sessionMode" @tab-change="(m) => m === 'debate' && loadDebateSessions()">
      <el-tab-pane label="1v1 语音对话记录" name="practice" />
      <el-tab-pane label="1vN 多角色交锋记录" name="debate" />
    </el-tabs>

    <template v-if="sessionMode === 'practice'">
    <div class="filter-bar">
      <el-input
        v-model="query.q"
        placeholder="搜索会话 ID / 用户名 / 场景 ID"
        clearable
        style="width: 240px"
        @keyup.enter="handleSearch"
        @clear="handleSearch"
      />
      <el-select v-model="query.user_id" placeholder="按用户筛选" clearable filterable style="width: 160px" @change="handleSearch">
        <el-option v-for="u in userOptions" :key="u.id" :label="u.username" :value="u.id" />
      </el-select>
      <el-select v-model="query.scene_id" placeholder="按场景筛选" clearable filterable style="width: 190px" @change="handleSearch">
        <el-option v-for="s in sceneOptions" :key="s.id" :label="s.name" :value="s.id" />
      </el-select>
      <el-select v-model="query.status" placeholder="状态" clearable style="width: 120px" @change="handleSearch">
        <el-option label="进行中" value="active" />
        <el-option label="已完成" value="finished" />
      </el-select>
      <el-button type="primary" icon="Search" @click="handleSearch">查询</el-button>
      <el-button
        v-if="selectedRows.length"
        type="danger"
        icon="Delete"
        @click="handleBatchDelete"
      >
        批量删除 ({{ selectedRows.length }})
      </el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="items"
      stripe
      border
      @selection-change="(val) => (selectedRows = val)"
    >
      <el-table-column type="selection" width="48" />
      <el-table-column prop="id" label="会话 ID" width="140" show-overflow-tooltip />
      <el-table-column prop="username" label="用户" width="120" />
      <el-table-column prop="scene_name" label="场景" min-width="180" show-overflow-tooltip />
      <el-table-column prop="turn_count" label="轮次" width="80" align="center" />
      <el-table-column label="目标进度" width="110" align="center">
        <template #default="{ row }">{{ row.goals_done }} / {{ row.goals_total }}</template>
      </el-table-column>
      <el-table-column label="当前阶段" width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.stage_name || '-' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.status === 'finished' ? 'success' : 'warning'" size="small">
            {{ row.status === 'finished' ? '已完成' : '进行中' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="最近活跃" width="175">
        <template #default="{ row }">{{ formatTime(row.last_active_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right" align="center">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="openDetail(row)">查看对话</el-button>
          <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.page_size"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @current-change="loadSessions"
        @size-change="handleSearch"
      />
    </div>
    </template>

    <template v-else>
      <el-table v-loading="debateLoading" :data="debateItems" stripe>
        <el-table-column prop="username" label="用户" width="120" />
        <el-table-column prop="topic_title" label="多角色场景" min-width="200" />
        <el-table-column label="子模式" width="110">
          <template #default="{ row }">
            <el-tag :type="row.scene_type === 'panel' ? 'success' : 'primary'" size="small">
              {{ row.scene_type === 'panel' ? '群面/圆桌' : '辩论' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="turn_count" label="轮次" width="80" />
        <el-table-column prop="win_rate" label="认可度/胜率" width="110">
          <template #default="{ row }">{{ row.win_rate }}%</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" />
        <el-table-column label="时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openDebateDetail(row)">详情</el-button>
            <el-button type="danger" link size="small" @click="removeDebateSession(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="debatePage"
          :page-size="20"
          :total="debateTotal"
          layout="total, prev, pager, next"
          @current-change="loadDebateSessions"
        />
      </div>
    </template>

    <el-drawer v-model="debateDrawer" title="多角色交锋详情" size="560px">
      <template v-if="debateDetail">
        <p><b>议题：</b>{{ debateDetail.session.topic_title }}</p>
        <p><b>用户：</b>{{ debateDetail.session.username }} · <b>状态：</b>{{ debateDetail.session.status }} · <b>认可度/胜率：</b>{{ debateDetail.session.win_rate }}%</p>
        <el-divider />
        <div v-for="t in debateDetail.turns" :key="t.id" style="margin-bottom: 12px; padding: 10px; background: #f8fafc; border-radius: 8px">
          <div style="font-size: 12px; color: #64748b; margin-bottom: 4px">
            #{{ t.turn_number }} [{{ t.stage_label }}] · <b>{{ t.speaker }}</b> ({{ t.role_title || t.role }})
          </div>
          <div style="font-size: 13px; color: #1e293b">{{ t.en_text }}</div>
        </div>
      </template>
    </el-drawer>

    <!-- 对话详情抽屉 -->
    <el-drawer v-model="drawerVisible" :title="`对话记录详情（${detail?.username || ''} · ${detail?.scene_name || ''}）`" size="680px">
      <div v-loading="detailLoading" v-if="detail">
        <el-descriptions :column="2" border size="small" style="margin-bottom: 16px">
          <el-descriptions-item label="会话 ID">{{ detail.id }}</el-descriptions-item>
          <el-descriptions-item label="用户">{{ detail.username }} (ID: {{ detail.user_id }})</el-descriptions-item>
          <el-descriptions-item label="场景">{{ detail.scene_name }} ({{ detail.scene_id }})</el-descriptions-item>
          <el-descriptions-item label="当前状态">
            <el-tag :type="detail.state?.status === 'finished' ? 'success' : 'warning'" size="small">
              {{ detail.state?.status === 'finished' ? '已完成' : '进行中' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <div class="chat-timeline">
          <div v-if="detail.greeting" class="msg-block msg-ai">
            <div class="msg-meta">AI 开场白</div>
            <div class="msg-body">{{ detail.greeting }}</div>
          </div>

          <template v-for="turn in detail.turns" :key="turn.id">
            <div class="msg-block msg-user">
              <div class="msg-meta">
                第 {{ turn.number }} 轮 · 用户输入
                <span class="msg-time">{{ formatTime(turn.created_at) }}</span>
              </div>
              <div class="msg-body">{{ turn.input_text }}</div>
            </div>

            <div class="msg-block msg-ai">
              <div class="msg-meta">
                第 {{ turn.number }} 轮 · AI 回复
                <el-tag v-if="turn.response?.stage" size="small" effect="plain" style="margin-left: 8px">
                  阶段: {{ turn.response.stage }}
                </el-tag>
              </div>
              <div class="msg-body">{{ turn.response?.text || '-' }}</div>
              <el-collapse style="margin-top: 8px">
                <el-collapse-item title="查看内部 Trace 轨迹">
                  <pre class="trace-pre">{{ JSON.stringify(turn.trace, null, 2) }}</pre>
                </el-collapse-item>
              </el-collapse>
            </div>
          </template>

          <el-empty v-if="!detail.turns?.length" description="该会话暂无用户发言轮次" :image-size="60" />
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.chat-timeline {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.msg-block {
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
}

.msg-user {
  background: #eff6ff;
  border-color: #bfdbfe;
}

.msg-ai {
  background: #f8fafc;
}

.msg-meta {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
}

.msg-time {
  margin-left: auto;
  font-weight: 400;
  color: #94a3b8;
}

.msg-body {
  font-size: 14px;
  line-height: 1.6;
  color: #0f172a;
  white-space: pre-wrap;
}

.trace-pre {
  margin: 0;
  font-size: 12px;
  background: #0f172a;
  color: #e2e8f0;
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
  max-height: 240px;
}
</style>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  batchDeleteScenes,
  batchUpdateScenesStatus,
  deleteScene,
  fetchSceneDetail,
  fetchScenes,
  updateScene,
} from '../api/admin'

const loading = ref(false)
const items = ref([])
const total = ref(0)
const selectedRows = ref([])

const query = reactive({
  q: '',
  category: '',
  mode: '',
  source: '',
  status: '',
  page: 1,
  page_size: 20,
})

const drawerVisible = ref(false)
const detailLoading = ref(false)
const detail = ref(null)
const editForm = reactive({
  id: '',
  name: '',
  description: '',
  category: 'custom',
  mode: 'conversation',
  difficulty: 'normal',
  status: 'private',
  packageJsonText: '',
})

const CATEGORY_MAP = {
  daily: '日常交流',
  business: '商务职场',
  career: '求职面试',
  academic: '学术讨论',
  custom: '自定义',
}

const MODE_MAP = {
  conversation: '自由对话',
  interview: '模拟面试',
  debate: '多角色辩论',
}

const SOURCE_MAP = {
  builtin: '系统内置',
  custom: '用户自建',
  imported: '导入',
}

function formatTime(val) {
  return val ? new Date(val).toLocaleString('zh-CN', { hour12: false }) : '-'
}

async function loadScenes() {
  loading.value = true
  try {
    const params = {
      page: query.page,
      page_size: query.page_size,
      q: query.q || undefined,
      category: query.category || undefined,
      mode: query.mode || undefined,
      source: query.source || undefined,
      status: query.status || undefined,
    }
    const { data } = await fetchScenes(params)
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  query.page = 1
  loadScenes()
}

async function togglePublish(row) {
  const nextStatus = row.status === 'published' ? 'private' : 'published'
  await updateScene(row.id, { status: nextStatus })
  ElMessage.success(nextStatus === 'published' ? '已发布到社区' : '已设为私有')
  loadScenes()
}

async function openDetail(row) {
  drawerVisible.value = true
  detailLoading.value = true
  try {
    const { data } = await fetchSceneDetail(row.id)
    detail.value = data
    editForm.id = data.id
    editForm.name = data.name
    editForm.description = data.description
    editForm.category = data.category
    editForm.mode = data.mode
    editForm.difficulty = data.difficulty || 'normal'
    editForm.status = data.status
    editForm.packageJsonText = JSON.stringify(data.package_json, null, 2)
  } finally {
    detailLoading.value = false
  }
}

async function saveDetail() {
  let parsedPkg = null
  try {
    parsedPkg = JSON.parse(editForm.packageJsonText)
  } catch {
    ElMessage.error('package_json 不是合法的 JSON 格式')
    return
  }

  await updateScene(editForm.id, {
    name: editForm.name,
    description: editForm.description,
    category: editForm.category,
    mode: editForm.mode,
    difficulty: editForm.difficulty,
    status: editForm.status,
    package_json: parsedPkg,
  })
  ElMessage.success('场景更新成功')
  drawerVisible.value = false
  loadScenes()
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确认删除场景「${row.name}」吗？该操作不可恢复。`, '删除确认', {
    type: 'warning',
  })
  await deleteScene(row.id)
  ElMessage.success('场景已删除')
  loadScenes()
}

async function handleBatchStatus(status) {
  const ids = selectedRows.value.map((r) => r.id)
  if (!ids.length) return
  const label = status === 'published' ? '发布' : '下架'
  await ElMessageBox.confirm(`确认批量${label}选中的 ${ids.length} 个场景吗？`, `批量${label}确认`, {
    type: 'warning',
  })
  const { data } = await batchUpdateScenesStatus(ids, status)
  ElMessage.success(`已${label} ${data.updated} 个场景`)
  selectedRows.value = []
  loadScenes()
}

async function handleBatchDelete() {
  const ids = selectedRows.value.map((r) => r.id)
  if (!ids.length) return
  await ElMessageBox.confirm(`确认批量删除选中的 ${ids.length} 个场景吗？（系统内置场景将自动跳过）`, '批量删除确认', {
    type: 'warning',
  })
  const { data } = await batchDeleteScenes(ids)
  const msg = data.skipped_builtin
    ? `已删除 ${data.deleted} 个场景，跳过 ${data.skipped_builtin} 个内置场景`
    : `已删除 ${data.deleted} 个场景`
  ElMessage.success(msg)
  selectedRows.value = []
  loadScenes()
}

onMounted(loadScenes)
</script>

<template>
  <div class="page-card">
    <div class="filter-bar">
      <el-input
        v-model="query.q"
        placeholder="搜索场景 ID / 名称 / 描述"
        clearable
        style="width: 220px"
        @keyup.enter="handleSearch"
        @clear="handleSearch"
      />
      <el-select v-model="query.category" placeholder="分类" clearable style="width: 130px" @change="handleSearch">
        <el-option v-for="(label, key) in CATEGORY_MAP" :key="key" :label="label" :value="key" />
      </el-select>
      <el-select v-model="query.mode" placeholder="模式" clearable style="width: 130px" @change="handleSearch">
        <el-option v-for="(label, key) in MODE_MAP" :key="key" :label="label" :value="key" />
      </el-select>
      <el-select v-model="query.source" placeholder="来源" clearable style="width: 120px" @change="handleSearch">
        <el-option v-for="(label, key) in SOURCE_MAP" :key="key" :label="label" :value="key" />
      </el-select>
      <el-select v-model="query.status" placeholder="状态" clearable style="width: 120px" @change="handleSearch">
        <el-option label="已发布" value="published" />
        <el-option label="私有" value="private" />
      </el-select>
      <el-button type="primary" icon="Search" @click="handleSearch">查询</el-button>
      <template v-if="selectedRows.length">
        <el-button type="success" @click="handleBatchStatus('published')">批量发布 ({{ selectedRows.length }})</el-button>
        <el-button type="warning" @click="handleBatchStatus('private')">批量下架 ({{ selectedRows.length }})</el-button>
        <el-button type="danger" icon="Delete" @click="handleBatchDelete">批量删除 ({{ selectedRows.length }})</el-button>
      </template>
    </div>

    <el-table
      v-loading="loading"
      :data="items"
      stripe
      border
      @selection-change="(val) => (selectedRows = val)"
    >
      <el-table-column type="selection" width="48" />
      <el-table-column prop="id" label="场景 ID" width="160" show-overflow-tooltip />
      <el-table-column prop="name" label="名称" min-width="180" show-overflow-tooltip />
      <el-table-column label="分类" width="100" align="center">
        <template #default="{ row }">{{ CATEGORY_MAP[row.category] || row.category }}</template>
      </el-table-column>
      <el-table-column label="模式" width="110" align="center">
        <template #default="{ row }">{{ MODE_MAP[row.mode] || row.mode }}</template>
      </el-table-column>
      <el-table-column label="来源" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.source === 'builtin' ? 'primary' : 'info'" size="small">
            {{ SOURCE_MAP[row.source] || row.source }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="author_name" label="作者" width="120" />
      <el-table-column label="发布状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.status === 'published' ? 'success' : 'warning'" size="small">
            {{ row.status === 'published' ? '已发布' : '私有' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="互动 / 资料 / 会话" width="170" align="center">
        <template #default="{ row }">
          赞 {{ row.likes }} · 资料 {{ row.document_count }} · 对话 {{ row.session_count }}
        </template>
      </el-table-column>
      <el-table-column label="更新时间" width="170">
        <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="190" fixed="right" align="center">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="openDetail(row)">详情/编辑</el-button>
          <el-button
            type="warning"
            link
            size="small"
            :disabled="row.source === 'builtin' && row.status === 'published'"
            @click="togglePublish(row)"
          >
            {{ row.status === 'published' ? '下架' : '发布' }}
          </el-button>
          <el-button
            type="danger"
            link
            size="small"
            :disabled="row.source === 'builtin'"
            @click="handleDelete(row)"
          >
            删除
          </el-button>
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
        @current-change="loadScenes"
        @size-change="handleSearch"
      />
    </div>

    <!-- 场景详情与编辑抽屉 -->
    <el-drawer v-model="drawerVisible" :title="`场景详情：${editForm.name || editForm.id}`" size="640px">
      <div v-loading="detailLoading">
        <el-form label-width="90px" size="small">
          <el-form-item label="场景 ID">
            <el-input :model-value="editForm.id" disabled />
          </el-form-item>
          <el-form-item label="名称">
            <el-input v-model="editForm.name" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="editForm.description" type="textarea" :rows="2" />
          </el-form-item>
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="分类">
                <el-select v-model="editForm.category" style="width: 100%">
                  <el-option v-for="(label, key) in CATEGORY_MAP" :key="key" :label="label" :value="key" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="发布状态">
                <el-select v-model="editForm.status" style="width: 100%">
                  <el-option label="已发布" value="published" />
                  <el-option label="私有" value="private" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="知识资料">
            <el-tag v-for="doc in detail?.documents || []" :key="doc.id" style="margin-right: 6px; margin-bottom: 4px">
              {{ doc.filename }} ({{ doc.chunk_count }} 块)
            </el-tag>
            <span v-if="!detail?.documents?.length" style="color: #94a3b8">暂无关联资料</span>
          </el-form-item>
          <el-form-item label="场景包 JSON">
            <el-input
              v-model="editForm.packageJsonText"
              type="textarea"
              :rows="16"
              style="font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px"
            />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="drawerVisible = false">关闭</el-button>
        <el-button type="primary" @click="saveDetail">保存场景包</el-button>
      </template>
    </el-drawer>
  </div>
</template>

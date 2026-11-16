<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteAdminKnowledge, fetchAdminKnowledge, fetchLightragConfig, updateLightragConfig } from '../api/admin'

const loading = ref(false)
const scope = ref('scene')
const items = ref([])
const total = ref(0)
const query = reactive({ q: '', page: 1, page_size: 20 })
const lightrag = reactive({ enabled: false, available: false, has_llm_key: false, has_embedding_key: false })

async function loadLightrag() {
  try {
    const { data } = await fetchLightragConfig()
    Object.assign(lightrag, data)
  } catch {
    // 忽略
  }
}

async function toggleLightrag(val) {
  const { data } = await updateLightragConfig({ enabled: val })
  Object.assign(lightrag, data)
  ElMessage.success(val ? '已开启 LightRAG 后台图谱索引与检索' : '已关闭 LightRAG 后台执行')
}

async function loadData() {
  loading.value = true
  try {
    const { data } = await fetchAdminKnowledge({
      scope: scope.value,
      q: query.q || undefined,
      page: query.page,
      page_size: query.page_size,
    })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确认删除文档「${row.title}」及其全部向量切片？`, '警告', { type: 'warning' })
  await deleteAdminKnowledge(row.scope, row.id)
  ElMessage.success('已清理文档及切片')
  loadData()
}

onMounted(() => {
  loadData()
  loadLightrag()
})
</script>

<template>
  <el-card shadow="never">
    <div class="lightrag-bar">
      <div>
        <strong>LightRAG 知识图谱后台执行开关</strong>
        <span class="lr-status">
          状态：{{ lightrag.available ? '后台循环就绪' : '未就绪（请检查开关与模型 Key）' }}
        </span>
      </div>
      <el-switch
        :model-value="lightrag.enabled"
        active-text="后台开启"
        inactive-text="已关闭"
        @change="toggleLightrag"
      />
    </div>

    <el-tabs v-model="scope" @tab-change="() => { query.page = 1; loadData() }">
      <el-tab-pane label="场景知识库文档" name="scene" />
      <el-tab-pane label="用户私有知识库" name="personal" />
    </el-tabs>

    <div class="toolbar">
      <el-input v-model="query.q" placeholder="搜索文档标题或场景 ID" clearable style="width: 260px" @keyup.enter="loadData" />
      <el-button type="primary" @click="loadData">搜索</el-button>
    </div>

    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="title" label="文档名称" min-width="220" />
      <el-table-column prop="owner" label="归属" width="140" />
      <el-table-column prop="scene_id" label="关联场景" width="160" />
      <el-table-column prop="chunk_count" label="切片数量" width="100" />
      <el-table-column prop="created_at" label="上传时间" width="180">
        <template #default="{ row }">{{ new Date(row.created_at).toLocaleString('zh-CN', { hour12: false }) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <el-pagination
        v-model:current-page="query.page"
        :page-size="query.page_size"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadData"
      />
    </div>
  </el-card>
</template>

<style scoped>
.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}
.lightrag-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  margin-bottom: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}
.lr-status {
  margin-left: 12px;
  font-size: 12px;
  color: #64748b;
}
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>

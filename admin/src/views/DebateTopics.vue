<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteAdminDebate, fetchAdminDebates, updateAdminDebate } from '../api/admin'

const loading = ref(false)
const items = ref([])
const total = ref(0)
const query = reactive({ q: '', scene_type: '', status: '', page: 1, page_size: 20 })

async function loadData() {
  loading.value = true
  try {
    const { data } = await fetchAdminDebates({
      q: query.q || undefined,
      scene_type: query.scene_type || undefined,
      status: query.status || undefined,
      page: query.page,
      page_size: query.page_size,
    })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function changeStatus(row, status) {
  await updateAdminDebate(row.id, { status })
  ElMessage.success('状态已更新')
  loadData()
}

async function changeTier(row, required_tier) {
  await updateAdminDebate(row.id, { required_tier })
  ElMessage.success('会员门禁已更新')
  loadData()
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确认删除多角色场景「${row.title_zh}」？`, '提示', { type: 'warning' })
  await deleteAdminDebate(row.id)
  ElMessage.success('已删除')
  loadData()
}

onMounted(loadData)
</script>

<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-input v-model="query.q" placeholder="搜索场景标题或英文议题" clearable style="width: 240px" @keyup.enter="loadData" />
      <el-select v-model="query.scene_type" placeholder="子模式" clearable style="width: 150px" @change="loadData">
        <el-option label="正反辩论 (debate)" value="debate" />
        <el-option label="群面/圆桌 (panel)" value="panel" />
      </el-select>
      <el-select v-model="query.status" placeholder="发布状态" clearable style="width: 130px" @change="loadData">
        <el-option label="已发布" value="published" />
        <el-option label="私有" value="private" />
      </el-select>
      <el-button type="primary" @click="loadData">查询</el-button>
    </div>

    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column prop="title_zh" label="场景名称" min-width="180" />
      <el-table-column label="子模式" width="120">
        <template #default="{ row }">
          <el-tag :type="row.scene_type === 'panel' ? 'success' : 'primary'" size="small">
            {{ row.scene_type === 'panel' ? '群面/圆桌' : '辩论对抗' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="roles_count" label="AI角色数" width="90" />
      <el-table-column prop="owner_username" label="归属" width="110" />
      <el-table-column label="会员门禁" width="130">
        <template #default="{ row }">
          <el-select :model-value="row.required_tier" size="small" @change="(v) => changeTier(row, v)">
            <el-option label="Free 免费" value="free" />
            <el-option label="Pro 会员" value="pro" />
            <el-option label="Enterprise" value="enterprise" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-select :model-value="row.status" size="small" @change="(v) => changeStatus(row, v)">
            <el-option label="published" value="published" />
            <el-option label="private" value="private" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button type="danger" link :disabled="row.is_builtin" @click="handleDelete(row)">删除</el-button>
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
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>

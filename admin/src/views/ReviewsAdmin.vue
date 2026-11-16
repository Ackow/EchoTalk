<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteAdminReview, fetchAdminListeningAttempts, fetchAdminReviews } from '../api/admin'

const tab = ref('reviews')
const loading = ref(false)
const items = ref([])
const total = ref(0)
const query = reactive({ q: '', page: 1, page_size: 20 })

async function loadData() {
  loading.value = true
  try {
    if (tab.value === 'reviews') {
      const { data } = await fetchAdminReviews({ q: query.q || undefined, page: query.page, page_size: query.page_size })
      items.value = data.items
      total.value = data.total
    } else {
      const { data } = await fetchAdminListeningAttempts({ page: query.page, page_size: query.page_size })
      items.value = data.items
      total.value = data.total
    }
  } finally {
    loading.value = false
  }
}

async function removeReview(row) {
  await ElMessageBox.confirm('确认删除该复习卡片？', '提示', { type: 'warning' })
  await deleteAdminReview(row.id)
  ElMessage.success('已删除')
  loadData()
}

onMounted(loadData)
</script>

<template>
  <el-card shadow="never">
    <el-tabs v-model="tab" @tab-change="() => { query.page = 1; loadData() }">
      <el-tab-pane label="SM-2 复习卡片" name="reviews" />
      <el-tab-pane label="听力闯关提交记录" name="attempts" />
    </el-tabs>

    <template v-if="tab === 'reviews'">
      <div class="toolbar">
        <el-input v-model="query.q" placeholder="搜索正面英文或背面释义" clearable style="width: 260px" @keyup.enter="loadData" />
        <el-button type="primary" @click="loadData">搜索</el-button>
      </div>
      <el-table v-loading="loading" :data="items" stripe>
        <el-table-column prop="username" label="用户" width="120" />
        <el-table-column prop="source_type" label="来源" width="110" />
        <el-table-column prop="front_text" label="正面内容" min-width="200" show-overflow-tooltip />
        <el-table-column prop="back_text" label="释义/纠错" min-width="200" show-overflow-tooltip />
        <el-table-column prop="repetitions" label="复习次数" width="90" />
        <el-table-column prop="interval_days" label="间隔(天)" width="90" />
        <el-table-column label="操作" width="90">
          <template #default="{ row }">
            <el-button type="danger" link @click="removeReview(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <template v-else>
      <el-table v-loading="loading" :data="items" stripe>
        <el-table-column prop="username" label="用户" width="130" />
        <el-table-column prop="unit_id" label="听力单元" min-width="180" />
        <el-table-column prop="exercise_type" label="题型" width="120" />
        <el-table-column label="结果" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_correct ? 'success' : 'danger'" size="small">
              {{ row.is_correct ? '正确' : '错误' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="hints_used" label="提示次数" width="100" />
        <el-table-column label="提交时间" width="180">
          <template #default="{ row }">{{ new Date(row.created_at).toLocaleString('zh-CN', { hour12: false }) }}</template>
        </el-table-column>
      </el-table>
    </template>

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
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>

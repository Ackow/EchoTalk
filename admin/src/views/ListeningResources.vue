<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteListeningUnit, fetchListeningUnits, importListeningUnits } from '../api/admin'

const loading = ref(false)
const items = ref([])
const filterChannel = ref('all')
const importDialogVisible = ref(false)
const importing = ref(false)
const rawJson = ref('')
const fileInput = ref(null)

const filteredItems = computed(() => {
  if (filterChannel.value === 'all') return items.value
  return items.value.filter((u) => u.channel === filterChannel.value)
})

async function loadUnits() {
  loading.value = true
  try {
    const { data } = await fetchListeningUnits()
    items.value = data.items || []
  } catch (err) {
    ElMessage.error(err?.message || '加载听力资源失败')
  } finally {
    loading.value = false
  }
}

function triggerFileImport() {
  fileInput.value?.click()
}

async function handleFileChange(event) {
  const file = event.target?.files?.[0]
  if (!file) return
  try {
    const text = await file.text()
    const parsed = JSON.parse(text)
    const payload = Array.isArray(parsed) ? { units: parsed } : parsed
    const { data } = await importListeningUnits(payload)
    ElMessage.success(`成功导入 ${data.imported || 1} 个听力单元`)
    await loadUnits()
  } catch (err) {
    ElMessage.error(err?.message || 'JSON 解析或导入失败')
  } finally {
    event.target.value = ''
  }
}

async function handlePasteImport() {
  if (!rawJson.value.trim()) {
    ElMessage.warning('请输入单元 JSON 数据')
    return
  }
  importing.value = true
  try {
    const parsed = JSON.parse(rawJson.value)
    const payload = Array.isArray(parsed) ? { units: parsed } : parsed
    const { data } = await importListeningUnits(payload)
    ElMessage.success(`成功导入 ${data.imported || 1} 个听力单元`)
    importDialogVisible.value = false
    rawJson.value = ''
    await loadUnits()
  } catch (err) {
    ElMessage.error(err?.message || 'JSON 解析或导入失败')
  } finally {
    importing.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除听力单元「${row.title}」吗？相关学习进度也会一并移除。`, '删除确认', {
      type: 'warning',
    })
    await deleteListeningUnit(row.id)
    ElMessage.success('已删除')
    await loadUnits()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(err?.message || '删除失败')
    }
  }
}

onMounted(loadUnits)
</script>

<template>
  <div class="listening-admin">
    <el-card shadow="never">
      <template #header>
        <div class="toolbar">
          <div class="toolbar-left">
            <span class="title">听力资源与四六级真题包</span>
            <el-radio-group v-model="filterChannel" size="small">
              <el-radio-button label="all">全部</el-radio-button>
              <el-radio-button label="cet">四六级真题</el-radio-button>
              <el-radio-button label="daily">日常对话</el-radio-button>
              <el-radio-button label="radio">新闻电台</el-radio-button>
              <el-radio-button label="talks">真实访谈</el-radio-button>
            </el-radio-group>
          </div>
          <div class="toolbar-right">
            <el-button @click="loadUnits">刷新</el-button>
            <el-button @click="importDialogVisible = true">粘贴 JSON 导入</el-button>
            <el-button type="primary" @click="triggerFileImport">上传 JSON 真题包</el-button>
            <input ref="fileInput" type="file" accept=".json" class="hidden-file" @change="handleFileChange" />
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="filteredItems" stripe style="width: 100%">
        <el-table-column prop="title" label="单元标题" min-width="220" />
        <el-table-column prop="channelLabel" label="频道" width="150" />
        <el-table-column prop="level" label="难度 / 类型" width="120" />
        <el-table-column label="题数" width="80" align="center">
          <template #default="{ row }">{{ row.exerciseCount }}</template>
        </el-table-column>
        <el-table-column prop="xp" label="奖励 XP" width="90" align="center" />
        <el-table-column label="来源" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.isBuiltin ? 'info' : 'success'" size="small">
              {{ row.isBuiltin ? '内置' : '导入' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="importDialogVisible" title="粘贴听力单元 JSON 导入" width="640px">
      <p class="dialog-tip">
        支持单个单元 JSON 对象或单元数组（可使用 <code>backend/scripts/import_cet_paper.py</code> 从 LRC + MP3 或真题文本生成）。
      </p>
      <el-input
        v-model="rawJson"
        type="textarea"
        :rows="12"
        placeholder='{"title": "2024年6月四级真题 Section A", "channel": "cet", "cetLevel": "cet4", "exercises": [...]}'
      />
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="handlePasteImport">确认导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.title {
  font-size: 16px;
  font-weight: 600;
}

.hidden-file {
  display: none;
}

.dialog-tip {
  margin: 0 0 12px;
  color: #64748b;
  font-size: 13px;
}
</style>

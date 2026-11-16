<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createAdminCampaign,
  deleteAdminCampaign,
  fetchAdminCampaigns,
  fetchAdminTasks,
  updateAdminCampaign,
  updateAdminTask,
} from '../api/admin'

const tasks = ref([])
const campaigns = ref([])
const loading = ref(false)
const campVisible = ref(false)
const campForm = reactive({
  name: '',
  description: '',
  bonus_multiplier: 2.0,
  free_actions_json: [],
  range: [],
})

const actionOptions = [
  { value: 'practice_turn', label: '1v1 语音对话' },
  { value: 'debate_turn', label: '1vN 多角色辩论/群面' },
  { value: 'listening_explain', label: '听力划词解释' },
  { value: 'scene_ai_draft', label: 'AI 生成场景草稿' },
]

async function loadData() {
  loading.value = true
  try {
    const [tRes, cRes] = await Promise.all([fetchAdminTasks(), fetchAdminCampaigns()])
    tasks.value = tRes.data.items || []
    campaigns.value = cRes.data.items || []
  } finally {
    loading.value = false
  }
}

async function saveTask(row) {
  await updateAdminTask(row.task_code, {
    reward_credits: row.reward_credits,
    target_count: row.target_count,
    daily_limit: row.daily_limit,
    enabled: row.enabled,
  })
  ElMessage.success(`任务「${row.title}」已更新`)
}

async function submitCampaign() {
  if (!campForm.name || !campForm.range || campForm.range.length !== 2) {
    ElMessage.warning('请填写活动名称与起止时间')
    return
  }
  await createAdminCampaign({
    name: campForm.name,
    description: campForm.description,
    bonus_multiplier: campForm.bonus_multiplier,
    free_actions_json: campForm.free_actions_json,
    starts_at: campForm.range[0].toISOString(),
    ends_at: campForm.range[1].toISOString(),
    enabled: true,
  })
  ElMessage.success('限时活动已创建')
  campVisible.value = false
  loadData()
}

async function toggleCampaign(row, enabled) {
  await updateAdminCampaign(row.id, { enabled })
  ElMessage.success('活动状态已更新')
  loadData()
}

async function removeCampaign(row) {
  await ElMessageBox.confirm(`确认删除活动「${row.name}」？`, '提示', { type: 'warning' })
  await deleteAdminCampaign(row.id)
  ElMessage.success('已删除')
  loadData()
}

onMounted(loadData)
</script>

<template>
  <div v-loading="loading">
    <el-card shadow="never" style="margin-bottom: 16px">
      <template #header><strong>每日与新手积分任务配置</strong></template>
      <el-table :data="tasks" stripe>
        <el-table-column prop="title" label="任务名称" width="160" />
        <el-table-column prop="description" label="描述" min-width="220" />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.category === 'daily' ? 'primary' : 'warning'" size="small">
              {{ row.category === 'daily' ? '每日' : '新手' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="目标次数" width="130">
          <template #default="{ row }"><el-input-number v-model="row.target_count" :min="1" size="small" /></template>
        </el-table-column>
        <el-table-column label="奖励积分" width="130">
          <template #default="{ row }"><el-input-number v-model="row.reward_credits" :min="0" size="small" /></template>
        </el-table-column>
        <el-table-column label="启用" width="80">
          <template #default="{ row }"><el-switch v-model="row.enabled" /></template>
        </el-table-column>
        <el-table-column label="操作" width="90">
          <template #default="{ row }">
            <el-button type="primary" link @click="saveTask(row)">保存</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="hd">
          <strong>限时运营活动（积分翻倍 / 功能限免）</strong>
          <el-button type="primary" size="small" @click="campVisible = true">新建活动</el-button>
        </div>
      </template>
      <el-table :data="campaigns" stripe>
        <el-table-column prop="name" label="活动名称" width="180" />
        <el-table-column prop="bonus_multiplier" label="任务/签到倍率" width="120">
          <template #default="{ row }">{{ row.bonus_multiplier }}x</template>
        </el-table-column>
        <el-table-column label="限免功能" min-width="180">
          <template #default="{ row }">
            <el-tag v-for="a in row.free_actions_json" :key="a" size="small" style="margin-right: 4px">{{ a }}</el-tag>
            <span v-if="!row.free_actions_json?.length">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-switch :model-value="row.enabled" @change="(v) => toggleCampaign(row, v)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90">
          <template #default="{ row }">
            <el-button type="danger" link @click="removeCampaign(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="campVisible" title="新建限时活动" width="480px">
      <el-form label-width="110px">
        <el-form-item label="活动名称"><el-input v-model="campForm.name" /></el-form-item>
        <el-form-item label="活动描述"><el-input v-model="campForm.description" /></el-form-item>
        <el-form-item label="积分倍率"><el-input-number v-model="campForm.bonus_multiplier" :min="1" :max="10" :step="0.5" /></el-form-item>
        <el-form-item label="限免功能">
          <el-select v-model="campForm.free_actions_json" multiple style="width: 100%">
            <el-option v-for="o in actionOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="起止时间">
          <el-date-picker v-model="campForm.range" type="datetimerange" start-placeholder="开始" end-placeholder="结束" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="campVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCampaign">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

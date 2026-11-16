<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchAdminLedger, fetchAdminOrders, fetchAdminRedeemCodes, generateAdminRedeemCodes } from '../api/admin'

const tab = ref('orders')
const loading = ref(false)
const orders = ref([])
const ledger = ref([])
const codes = ref([])
const genVisible = ref(false)
const genForm = reactive({
  count: 5,
  reward_type: 'credits',
  reward_credits: 200,
  reward_tier: 'pro',
  reward_days: 7,
  prefix: 'ECHO',
  note: '',
})

async function loadData() {
  loading.value = true
  try {
    if (tab.value === 'orders') {
      const { data } = await fetchAdminOrders({ page: 1, page_size: 50 })
      orders.value = data.items || []
    } else if (tab.value === 'ledger') {
      const { data } = await fetchAdminLedger({ page: 1, page_size: 50 })
      ledger.value = data.items || []
    } else {
      const { data } = await fetchAdminRedeemCodes({ page: 1, page_size: 50 })
      codes.value = data.items || []
    }
  } finally {
    loading.value = false
  }
}

async function submitGenerate() {
  const { data } = await generateAdminRedeemCodes({ ...genForm })
  ElMessage.success(`成功生成 ${data.codes.length} 个兑换码`)
  genVisible.value = false
  loadData()
}

onMounted(loadData)
</script>

<template>
  <el-card shadow="never">
    <el-tabs v-model="tab" @tab-change="loadData">
      <el-tab-pane label="模拟订阅订单" name="orders" />
      <el-tab-pane label="全站积分流水账本" name="ledger" />
      <el-tab-pane label="兑换码管理" name="codes" />
    </el-tabs>

    <template v-if="tab === 'orders'">
      <el-table v-loading="loading" :data="orders" stripe>
        <el-table-column prop="order_no" label="订单号" width="210" />
        <el-table-column prop="username" label="用户" width="120" />
        <el-table-column prop="order_type" label="类型" width="130" />
        <el-table-column prop="target_tier" label="目标等级" width="110" />
        <el-table-column prop="credits_granted" label="赠送积分" width="100" />
        <el-table-column prop="amount_yuan" label="金额 (¥)" width="100" />
        <el-table-column label="时间" width="180">
          <template #default="{ row }">{{ new Date(row.created_at).toLocaleString('zh-CN', { hour12: false }) }}</template>
        </el-table-column>
      </el-table>
    </template>

    <template v-else-if="tab === 'ledger'">
      <el-table v-loading="loading" :data="ledger" stripe>
        <el-table-column prop="username" label="用户" width="120" />
        <el-table-column label="变动" width="100">
          <template #default="{ row }">
            <el-tag :type="row.delta >= 0 ? 'success' : 'danger'" size="small">
              {{ row.delta >= 0 ? `+${row.delta}` : row.delta }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="balance_after" label="变动后余额" width="110" />
        <el-table-column prop="source_type" label="来源类型" width="140" />
        <el-table-column prop="remark" label="备注说明" min-width="220" />
        <el-table-column label="时间" width="180">
          <template #default="{ row }">{{ new Date(row.created_at).toLocaleString('zh-CN', { hour12: false }) }}</template>
        </el-table-column>
      </el-table>
    </template>

    <template v-else>
      <div style="margin-bottom: 14px">
        <el-button type="primary" @click="genVisible = true">批量生成兑换码</el-button>
      </div>
      <el-table v-loading="loading" :data="codes" stripe>
        <el-table-column prop="code" label="兑换码" width="190" />
        <el-table-column prop="reward_type" label="奖励类型" width="110" />
        <el-table-column prop="reward_credits" label="积分" width="90" />
        <el-table-column label="会员天数" width="120">
          <template #default="{ row }">{{ row.reward_tier ? `${row.reward_tier} (${row.reward_days}天)` : '-' }}</template>
        </el-table-column>
        <el-table-column label="核销状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.is_used ? 'info' : 'success'" size="small">{{ row.is_used ? '已核销' : '未使用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="used_by_username" label="核销用户" width="120" />
        <el-table-column prop="note" label="备注" min-width="150" />
      </el-table>
    </template>

    <el-dialog v-model="genVisible" title="批量生成兑换码" width="420px">
      <el-form label-width="100px">
        <el-form-item label="生成数量"><el-input-number v-model="genForm.count" :min="1" :max="50" /></el-form-item>
        <el-form-item label="前缀"><el-input v-model="genForm.prefix" /></el-form-item>
        <el-form-item label="奖励类型">
          <el-radio-group v-model="genForm.reward_type">
            <el-radio value="credits">纯积分码</el-radio>
            <el-radio value="plan_days">会员体验码</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="赠送积分"><el-input-number v-model="genForm.reward_credits" :min="0" :step="50" /></el-form-item>
        <template v-if="genForm.reward_type === 'plan_days'">
          <el-form-item label="体验等级">
            <el-select v-model="genForm.reward_tier">
              <el-option label="Pro 专业版" value="pro" />
              <el-option label="Enterprise 企业版" value="enterprise" />
            </el-select>
          </el-form-item>
          <el-form-item label="有效天数"><el-input-number v-model="genForm.reward_days" :min="1" :max="365" /></el-form-item>
        </template>
        <el-form-item label="备注"><el-input v-model="genForm.note" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="genVisible = false">取消</el-button>
        <el-button type="primary" @click="submitGenerate">生成</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

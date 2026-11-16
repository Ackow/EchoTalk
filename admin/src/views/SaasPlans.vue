<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchAdminSaasPlans, updateAdminSaasPlan } from '../api/admin'

const loading = ref(false)
const plans = ref([])
const actionMeta = ref({})
const saving = ref('')

async function loadPlans() {
  loading.value = true
  try {
    const { data } = await fetchAdminSaasPlans()
    plans.value = data.plans || []
    actionMeta.value = data.action_meta || {}
  } finally {
    loading.value = false
  }
}

async function savePlan(plan) {
  saving.value = plan.tier
  try {
    await updateAdminSaasPlan(plan.tier, {
      name: plan.name,
      monthly_price_yuan: plan.monthly_price_yuan,
      yearly_price_yuan: plan.yearly_price_yuan,
      monthly_grant_credits: plan.monthly_grant_credits,
      daily_free_credits: plan.daily_free_credits,
      max_custom_scenes: plan.max_custom_scenes,
      max_custom_debates: plan.max_custom_debates,
      max_knowledge_docs: plan.max_knowledge_docs,
      allow_zip_import: plan.allow_zip_import,
      allow_zip_export: plan.allow_zip_export,
      checkin_multiplier: plan.checkin_multiplier,
      credit_discount_rate: plan.credit_discount_rate,
      quotas_json: plan.quotas_json,
    })
    ElMessage.success(`已保存 ${plan.name} 配置并热更新生效`)
  } finally {
    saving.value = ''
  }
}

onMounted(loadPlans)
</script>

<template>
  <div v-loading="loading" class="plans-wrap">
    <el-alert
      title="统一共享额度池说明：daily_free_credits 为每日共享免费积分额度（-1 表示无限）；下方可设定各功能单次消耗积分点数及超额积分抵扣开关。"
      type="info"
      show-icon
      :closable="false"
      style="margin-bottom: 16px"
    />

    <el-row :gutter="16">
      <el-col v-for="p in plans" :key="p.tier" :xs="24" :lg="8">
        <el-card shadow="never" class="plan-box">
          <template #header>
            <div class="card-hd">
              <strong>{{ p.name }} ({{ p.tier.toUpperCase() }})</strong>
              <el-button type="primary" size="small" :loading="saving === p.tier" @click="savePlan(p)">保存配置</el-button>
            </div>
          </template>

          <el-form label-width="135px" size="small">
            <el-form-item label="月付价格 (元)">
              <el-input-number v-model="p.monthly_price_yuan" :min="0" />
            </el-form-item>
            <el-form-item label="年付价格 (元)">
              <el-input-number v-model="p.yearly_price_yuan" :min="0" />
            </el-form-item>
            <el-form-item label="每月赠送积分">
              <el-input-number v-model="p.monthly_grant_credits" :min="0" :step="100" />
            </el-form-item>
            <el-form-item label="每日免费池 (-1无限)">
              <el-input-number v-model="p.daily_free_credits" :min="-1" :step="10" />
            </el-form-item>
            <el-form-item label="签到积分倍率">
              <el-input-number v-model="p.checkin_multiplier" :min="1" :max="10" />
            </el-form-item>
            <el-form-item label="超额积分折扣">
              <el-input-number v-model="p.credit_discount_rate" :min="0.1" :max="1" :step="0.1" />
            </el-form-item>
            <el-form-item label="1v1 场景上限 (-1无限)">
              <el-input-number v-model="p.max_custom_scenes" :min="-1" />
            </el-form-item>
            <el-form-item label="知识库文档上限">
              <el-input-number v-model="p.max_knowledge_docs" :min="-1" />
            </el-form-item>
            <el-form-item label="允许导入场景包 ZIP">
              <el-switch v-model="p.allow_zip_import" />
            </el-form-item>
            <el-form-item label="允许导出场景包 ZIP">
              <el-switch v-model="p.allow_zip_export" />
            </el-form-item>
          </el-form>

          <el-divider content-position="left">各功能单次消耗积分 &amp; 超额抵扣开关</el-divider>
          <div v-for="(meta, key) in actionMeta" :key="key" class="quota-row">
            <span class="q-label">{{ meta.label }}</span>
            <div class="q-controls" v-if="p.quotas_json[key]">
              <el-input-number v-model="p.quotas_json[key].credit_cost" :min="0" size="small" style="width: 96px" title="单次消耗积分点数" />
              <el-switch v-model="p.quotas_json[key].allow_overage_credits" size="small" title="池满后允许用个人积分抵扣" />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.card-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.plan-box {
  margin-bottom: 16px;
}
.quota-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px dashed #e2e8f0;
  gap: 8px;
}
.q-label {
  font-size: 12px;
  color: #334155;
  flex: 1;
}
.q-controls {
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { batchDeleteUsers, createUser, deleteUser, fetchRegistrationSetting, fetchUsers, grantUserSaas, updateRegistrationSetting, updateUser } from '../api/admin'
import { apiUrl } from '../api/http'
import { adminSession } from '../auth/session'

const loading = ref(false)
const items = ref([])
const total = ref(0)
const selectedRows = ref([])

const query = reactive({
  q: '',
  is_admin: '',
  page: 1,
  page_size: 20,
})

const createVisible = ref(false)
const createFormRef = ref()
const createForm = reactive({ username: '', password: '', is_admin: false })
const createRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '长度为 3 到 50 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 128, message: '密码至少 8 位', trigger: 'blur' },
  ],
}

const editVisible = ref(false)
const editForm = reactive({ id: null, username: '', is_admin: false, password: '' })

const grantVisible = ref(false)
const grantForm = reactive({ id: null, username: '', plan_tier: 'free', plan_days: 30, credits_delta: 0, remark: '管理员手动调整' })

function openGrant(row) {
  grantForm.id = row.id
  grantForm.username = row.username
  grantForm.plan_tier = row.plan_tier || 'free'
  grantForm.plan_days = 30
  grantForm.credits_delta = 0
  grantForm.remark = '管理员手动调整'
  grantVisible.value = true
}

async function submitGrant() {
  await grantUserSaas(grantForm.id, {
    plan_tier: grantForm.plan_tier,
    plan_days: grantForm.plan_days,
    credits_delta: grantForm.credits_delta,
    remark: grantForm.remark,
  })
  ElMessage.success('会员权益与积分已更新')
  grantVisible.value = false
  loadUsers()
}

function formatTime(val) {
  return val ? new Date(val).toLocaleString('zh-CN', { hour12: false }) : '-'
}

async function loadUsers() {
  loading.value = true
  try {
    const params = {
      page: query.page,
      page_size: query.page_size,
      q: query.q || undefined,
      is_admin: query.is_admin === '' ? undefined : query.is_admin,
    }
    const { data } = await fetchUsers(params)
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  query.page = 1
  loadUsers()
}

function openCreate() {
  createForm.username = ''
  createForm.password = ''
  createForm.is_admin = false
  createVisible.value = true
}

async function submitCreate() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return
  await createUser({ ...createForm })
  ElMessage.success('用户创建成功')
  createVisible.value = false
  loadUsers()
}

function openEdit(row) {
  editForm.id = row.id
  editForm.username = row.username
  editForm.is_admin = row.is_admin
  editForm.password = ''
  editVisible.value = true
}

async function submitEdit() {
  const payload = { is_admin: editForm.is_admin }
  if (editForm.password.trim()) {
    if (editForm.password.trim().length < 8) {
      ElMessage.warning('新密码至少需要 8 位')
      return
    }
    payload.password = editForm.password.trim()
  }
  await updateUser(editForm.id, payload)
  ElMessage.success('用户信息已更新')
  editVisible.value = false
  loadUsers()
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确认删除用户「${row.username}」吗？其对话记录与偏好也将一并清理。`, '删除确认', {
    type: 'warning',
    confirmButtonText: '确认删除',
    cancelButtonText: '取消',
  })
  await deleteUser(row.id)
  ElMessage.success('用户已删除')
  loadUsers()
}

async function handleBatchDelete() {
  const ids = selectedRows.value.map((r) => r.id)
  if (!ids.length) return
  await ElMessageBox.confirm(`确认批量删除选中的 ${ids.length} 个用户吗？其关联对话与偏好也将一并清理。`, '批量删除确认', {
    type: 'warning',
    confirmButtonText: '确认删除',
    cancelButtonText: '取消',
  })
  const { data } = await batchDeleteUsers(ids)
  ElMessage.success(`已删除 ${data.deleted} 个用户`)
  selectedRows.value = []
  loadUsers()
}

const registrationRestricted = ref(false)
const savingRegSetting = ref(false)

async function loadRegistrationSetting() {
  try {
    const { data } = await fetchRegistrationSetting()
    registrationRestricted.value = Boolean(data?.registration_restricted)
  } catch {
    // 忽略加载失败，保持默认
  }
}

async function handleToggleRegistration(val) {
  savingRegSetting.value = true
  try {
    const { data } = await updateRegistrationSetting(val)
    registrationRestricted.value = Boolean(data?.registration_restricted)
    ElMessage.success(
      registrationRestricted.value
        ? '已开启限制注册：仅管理端可新增用户'
        : '已关闭限制注册：允许用户自主注册'
    )
  } catch (err) {
    registrationRestricted.value = !val
    ElMessage.error(err?.response?.data?.detail || '更新注册限制开关失败')
  } finally {
    savingRegSetting.value = false
  }
}

onMounted(() => {
  loadUsers()
  loadRegistrationSetting()
})
</script>

<template>
  <div class="page-card">
    <div class="filter-bar">
      <el-input
        v-model="query.q"
        placeholder="搜索用户名"
        clearable
        style="width: 240px"
        @keyup.enter="handleSearch"
        @clear="handleSearch"
      />
      <el-select v-model="query.is_admin" placeholder="账号角色" clearable style="width: 140px" @change="handleSearch">
        <el-option label="全部角色" value="" />
        <el-option label="管理员" :value="true" />
        <el-option label="普通用户" :value="false" />
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
      <div style="margin-left: auto; display: flex; align-items: center; gap: 14px">
        <div style="display: flex; align-items: center; gap: 8px; padding: 4px 10px; border-radius: 8px; background: #f8fafc; border: 1px solid #e2e8f0">
          <span style="font-size: 13px; color: #475569">限制自主注册</span>
          <el-switch
            v-model="registrationRestricted"
            :loading="savingRegSetting"
            inline-prompt
            active-text="内测"
            inactive-text="开放"
            @change="handleToggleRegistration"
          />
        </div>
        <el-button type="success" icon="Plus" @click="openCreate">新建用户</el-button>
      </div>
    </div>

    <el-table
      v-loading="loading"
      :data="items"
      stripe
      border
      @selection-change="(val) => (selectedRows = val)"
    >
      <el-table-column type="selection" width="48" :selectable="(row) => row.id !== adminSession.user?.id" />
      <el-table-column prop="id" label="ID" width="70" align="center" />
      <el-table-column label="用户名" min-width="160">
        <template #default="{ row }">
          <div style="display: flex; align-items: center; gap: 10px">
            <el-avatar :size="30" :src="row.avatar_path ? apiUrl(`/api/auth/avatar/${row.id}`) : ''">
              {{ row.username[0]?.toUpperCase() }}
            </el-avatar>
            <span>{{ row.username }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="角色" width="110" align="center">
        <template #default="{ row }">
          <el-tag :type="row.is_admin ? 'danger' : 'info'" size="small">
            {{ row.is_admin ? '管理员' : '普通用户' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="会员等级" width="110" align="center">
        <template #default="{ row }">
          <el-tag :type="row.plan_tier === 'enterprise' ? 'warning' : row.plan_tier === 'pro' ? 'primary' : 'info'" size="small">
            {{ (row.plan_tier || 'free').toUpperCase() }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="credits_balance" label="回声积分" width="100" align="center" />
      <el-table-column prop="session_count" label="对话会话" width="100" align="center" />
      <el-table-column prop="scene_count" label="自建场景" width="100" align="center" />
      <el-table-column prop="avatar_pref_count" label="数字人配置" width="110" align="center" />
      <el-table-column prop="personal_doc_count" label="个人资料" width="100" align="center" />
      <el-table-column label="注册时间" width="180">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="210" fixed="right" align="center">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="openEdit(row)">编辑</el-button>
          <el-button type="warning" link size="small" @click="openGrant(row)">调账/会员</el-button>
          <el-button
            type="danger"
            link
            size="small"
            :disabled="row.id === adminSession.user?.id"
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
        @current-change="loadUsers"
        @size-change="handleSearch"
      />
    </div>

    <!-- 新建用户弹窗 -->
    <el-dialog v-model="createVisible" title="新建用户" width="420px">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="90px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="createForm.username" placeholder="3~50 个字符" />
        </el-form-item>
        <el-form-item label="初始密码" prop="password">
          <el-input v-model="createForm.password" type="password" show-password placeholder="至少 8 位" />
        </el-form-item>
        <el-form-item label="管理员">
          <el-switch v-model="createForm.is_admin" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCreate">确定创建</el-button>
      </template>
    </el-dialog>

    <!-- 编辑用户弹窗 -->
    <el-dialog v-model="editVisible" :title="`编辑用户：${editForm.username}`" width="420px">
      <el-form label-width="90px">
        <el-form-item label="管理员权限">
          <el-switch v-model="editForm.is_admin" :disabled="editForm.id === adminSession.user?.id" />
        </el-form-item>
        <el-form-item label="重置密码">
          <el-input
            v-model="editForm.password"
            type="password"
            show-password
            placeholder="留空则不修改（至少 8 位）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="submitEdit">保存修改</el-button>
      </template>
    </el-dialog>

    <!-- 会员与积分调账弹窗 -->
    <el-dialog v-model="grantVisible" :title="`权益与积分调账：${grantForm.username}`" width="440px">
      <el-form label-width="100px">
        <el-form-item label="会员等级">
          <el-select v-model="grantForm.plan_tier" style="width: 100%">
            <el-option label="Free 免费版" value="free" />
            <el-option label="Pro 专业版" value="pro" />
            <el-option label="Enterprise 企业版" value="enterprise" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="grantForm.plan_tier !== 'free'" label="延长天数">
          <el-input-number v-model="grantForm.plan_days" :min="0" :max="3650" />
        </el-form-item>
        <el-form-item label="积分增减">
          <el-input-number v-model="grantForm.credits_delta" :min="-10000" :max="100000" :step="50" />
        </el-form-item>
        <el-form-item label="调账备注">
          <el-input v-model="grantForm.remark" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="grantVisible = false">取消</el-button>
        <el-button type="primary" @click="submitGrant">确认下发</el-button>
      </template>
    </el-dialog>
  </div>
</template>

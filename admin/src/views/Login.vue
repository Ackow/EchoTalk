<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import brandLogo from '../assets/echotalk-brand.png'
import { adminLogin } from '../api/admin'
import { setAdminSession } from '../auth/session'

const router = useRouter()
const formRef = ref()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入管理员用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const { data } = await adminLogin(form.username.trim(), form.password)
    setAdminSession(data.access_token, data.user)
    ElMessage.success('登录成功')
    router.replace('/dashboard')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <el-card class="login-card" shadow="always">
      <div class="login-header">
        <img :src="brandLogo" alt="EchoTalk" class="login-logo-img" />
        <h2>EchoTalk 管理端</h2>
        <p>用户 · 数字人 · 场景 · 对话记录统一控制台</p>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @keyup.enter="handleSubmit">
        <el-form-item label="管理员账号" prop="username">
          <el-input v-model="form.username" prefix-icon="User" placeholder="请输入管理员用户名" size="large" />
        </el-form-item>
        <el-form-item label="登录密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            prefix-icon="Lock"
            placeholder="请输入密码"
            size="large"
          />
        </el-form-item>
        <el-button type="primary" size="large" :loading="loading" class="submit-btn" @click="handleSubmit">
          登录管理后台
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at top left, #eff6ff, #e2e8f0);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 400px;
  border-radius: 14px;
}

.login-header {
  text-align: center;
  margin-bottom: 24px;
}

.login-logo-img {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  object-fit: cover;
  margin-bottom: 12px;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12);
}

.login-header h2 {
  margin: 0 0 6px;
  font-size: 20px;
  color: #0f172a;
}

.login-header p {
  margin: 0;
  font-size: 13px;
  color: #64748b;
}

.submit-btn {
  width: 100%;
  margin-top: 8px;
}
</style>

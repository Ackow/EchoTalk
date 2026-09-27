<template>
  <main class="auth-page">
    <section class="auth-brand-panel">
      <div class="auth-brand-lockup">
        <span class="auth-brand-mark"><AppIcon name="logo" :size="18" /></span>
        <span>EchoTalk <small>2.0</small></span>
      </div>

      <div class="brand-art" aria-hidden="true">
        <div class="brand-orbit orbit-one"></div>
        <div class="brand-orbit orbit-two"></div>
        <div class="brand-disc"><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div>
      </div>

      <div class="auth-brand-copy">
        <p class="eyebrow">YOUR PERSONAL SPEAKING SPACE</p>
        <h1>让表达<br />更有自信。</h1>
        <p>在自己的节奏里，练习每一次开口。</p>
      </div>
      <div class="brand-footer"><span class="status-light"></span> 你的 EchoTalk 个人工作区</div>
    </section>

    <section class="auth-panel">
      <div class="auth-panel-top">
        <button class="back-button" type="button" @click="router.push({ name: 'workspace' })">
          <AppIcon name="chevron-left" :size="14" />返回工作区
        </button> <!-- 桌面端惯例：左上角返回入口 -->
        <span class="secure-label">个人工作区</span>
      </div>
      <div class="auth-form-wrap">
        <p class="auth-kicker">ECHOTALK ACCOUNT</p>
        <h2>{{ registering ? '创建你的账户' : '欢迎回来' }}</h2>
        <p class="description">{{ registering ? '建立账户，开启专属练习空间。' : '登录后继续使用你的 EchoTalk 工作区。' }}</p>

        <form @submit.prevent="submit">
          <label>用户名
            <input v-model.trim="username" autofocus autocomplete="username" placeholder="输入用户名" minlength="3" maxlength="50" required />
          </label>
          <label>密码
            <input v-model="password" type="password" :autocomplete="registering ? 'new-password' : 'current-password'" placeholder="至少 8 位密码" minlength="8" maxlength="128" required />
          </label>
          <label v-if="registering">确认密码
            <input v-model="confirmation" type="password" autocomplete="new-password" placeholder="再次输入密码" required />
          </label>
          <p v-if="error" class="error-message" role="alert">{{ error }}</p>
          <button class="primary-button" type="submit" :disabled="busy">
            <span>{{ busy ? '正在连接…' : (registering ? '创建' : '登录') }}</span>
            <AppIcon name="arrow-right" :size="17" />
          </button>
        </form>
        <p class="mode-prompt">{{ registering ? '已经有账户？' : '第一次使用 EchoTalk？' }}
          <button class="mode-button" type="button" @click="toggleMode">{{ registering ? '返回登录' : '创建账户' }}</button>
        </p>
      </div>
      <footer class="auth-legal">EchoTalk 2.0 · 账户登录</footer>
    </section>
  </main>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { login, register } from '../api/auth'
import { saveSession, session } from '../auth/session'

const router = useRouter()
const username = ref('')
const password = ref('')
const confirmation = ref('')
const registering = ref(false)
const busy = ref(false)
const error = ref('')

function handleEscKey(event) {
  // 桌面端惯例：Esc 取消登录流程返回工作区，已输入内容保留。
  if (event.key === 'Escape') router.push({ name: 'workspace' })
}
onMounted(() => window.addEventListener('keydown', handleEscKey))
onBeforeUnmount(() => window.removeEventListener('keydown', handleEscKey))

function toggleMode() {
  // 注册与登录使用同一表单，切换时清除上次操作的提示信息。
  registering.value = !registering.value
  error.value = ''
}

async function submit() {
  error.value = ''
  if (registering.value && password.value !== confirmation.value) {
    error.value = '两次输入的密码不一致'
    return
  }
  busy.value = true
  try {
    const action = registering.value ? register : login
    const { data } = await action({ username: username.value, password: password.value })
    saveSession(data.access_token, data.user)
    session.user = data.user
    await router.replace({ name: 'workspace' })
  } catch (requestError) {
    error.value = requestError.message || '无法连接账户服务，请检查网络后重试。' // 错误已在 http.js 中规范化为可读文案
  } finally {
    busy.value = false
  }
}
</script>

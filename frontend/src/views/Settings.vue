<template>
  <div class="settings-container">
    <!-- Header -->
    <header class="settings-header">
      <h1 class="text-gradient page-title">设置与管理</h1>
      <p class="subtitle">配置大语言模型及发音评测秘钥，管理本地录音缓存与系统偏好</p>
    </header>

    <div class="settings-layout-grid">
      <!-- Left Column: API Configurations (Form Card) -->
      <div class="settings-config-col">
        <div class="settings-card glass-card config-card">
          <h3 class="card-title">
            <el-icon><Setting /></el-icon>
            <span>系统 API 秘钥配置</span>
          </h3>
          <p class="card-desc">配置大语言模型及发音评测/语音转译接口秘钥。此配置保存在安装目录下的 <code>settings.json</code> 文件中，实时应用生效。</p>

          <el-tabs v-model="activeTab" class="config-tabs">
            <el-tab-pane label="LLM 智能对话" name="llm">
              <el-form label-position="top" :model="configForm" size="default">
                <!-- DeepSeek -->
                <div class="service-group-title">DeepSeek LLM (首选推荐)</div>
                <div class="form-row">
                  <el-form-item label="API Key" class="flex-item">
                    <el-input v-model="configForm.DEEPSEEK_API_KEY" type="password" show-password placeholder="请输入 DeepSeek API Key" />
                  </el-form-item>
                  <el-form-item label="API Base URL" class="flex-item">
                    <el-input v-model="configForm.DEEPSEEK_BASE_URL" placeholder="https://api.deepseek.com/v1" />
                  </el-form-item>
                  <el-form-item label="模型名称" class="flex-item">
                    <el-input v-model="configForm.DEEPSEEK_MODEL" placeholder="deepseek-chat" />
                  </el-form-item>
                </div>

                <el-divider class="group-divider"></el-divider>

                <!-- OpenAI -->
                <div class="service-group-title">OpenAI LLM</div>
                <div class="form-row">
                  <el-form-item label="API Key" class="flex-item">
                    <el-input v-model="configForm.OPENAI_API_KEY" type="password" show-password placeholder="请输入 OpenAI API Key" />
                  </el-form-item>
                  <el-form-item label="API Base URL" class="flex-item">
                    <el-input v-model="configForm.OPENAI_BASE_URL" placeholder="https://api.openai.com/v1" />
                  </el-form-item>
                  <el-form-item label="模型名称" class="flex-item">
                    <el-input v-model="configForm.OPENAI_MODEL" placeholder="gpt-4o-mini" />
                  </el-form-item>
                </div>

                <el-divider class="group-divider"></el-divider>

                <!-- Xiaomi MiMo -->
                <div class="service-group-title">Xiaomi MiMo LLM</div>
                <div class="form-row">
                  <el-form-item label="API Key" class="flex-item">
                    <el-input v-model="configForm.XIAOMI_API_KEY" type="password" show-password placeholder="请输入 Xiaomi MiMo API Key" />
                  </el-form-item>
                  <el-form-item label="API Base URL" class="flex-item">
                    <el-input v-model="configForm.XIAOMI_BASE_URL" placeholder="https://api.ai.mi.com/v1" />
                  </el-form-item>
                  <el-form-item label="模型名称" class="flex-item">
                    <el-input v-model="configForm.XIAOMI_MODEL" placeholder="mimo-chat" />
                  </el-form-item>
                </div>
              </el-form>
            </el-tab-pane>

            <el-tab-pane label="语音识别与评测" name="speech">
              <el-form label-position="top" :model="configForm" size="default">
                <!-- Xunfei ISE -->
                <div class="service-group-title">科大讯飞 ISE (流式口语评测)</div>
                <div class="form-row-3">
                  <el-form-item label="App ID" class="flex-item">
                    <el-input v-model="configForm.XFYUN_APP_ID" placeholder="请输入讯飞 APP ID" />
                  </el-form-item>
                  <el-form-item label="API Key" class="flex-item">
                    <el-input v-model="configForm.XFYUN_API_KEY" type="password" show-password placeholder="请输入讯飞 API Key" />
                  </el-form-item>
                  <el-form-item label="API Secret" class="flex-item">
                    <el-input v-model="configForm.XFYUN_API_SECRET" type="password" show-password placeholder="请输入讯飞 API Secret" />
                  </el-form-item>
                </div>

                <el-divider class="group-divider"></el-divider>

                <!-- Baidu STT -->
                <div class="service-group-title">百度智能云 (语音识别 STT)</div>
                <div class="form-row">
                  <el-form-item label="API Key (Client ID)" class="flex-item">
                    <el-input v-model="configForm.BAIDU_API_KEY" type="password" show-password placeholder="请输入百度 API Key" />
                  </el-form-item>
                  <el-form-item label="Secret Key (Client Secret)" class="flex-item">
                    <el-input v-model="configForm.BAIDU_SECRET_KEY" type="password" show-password placeholder="请输入百度 Secret Key" />
                  </el-form-item>
                </div>
              </el-form>
            </el-tab-pane>

            <el-tab-pane label="云端文件存储" name="storage">
              <el-form label-position="top" :model="configForm" size="default">
                <!-- Qiniu Cloud -->
                <div class="service-group-title">七牛云 Kodo (音频文件托管)</div>
                <div class="form-row">
                  <el-form-item label="Access Key (公钥)" class="flex-item">
                    <el-input v-model="configForm.QINIU_ACCESS_KEY" type="password" show-password placeholder="请输入七牛云 Access Key" />
                  </el-form-item>
                  <el-form-item label="Secret Key (私钥)" class="flex-item">
                    <el-input v-model="configForm.QINIU_SECRET_KEY" type="password" show-password placeholder="请输入七牛云 Secret Key" />
                  </el-form-item>
                </div>
                <div class="form-row">
                  <el-form-item label="空间名称 (Bucket Name)" class="flex-item">
                    <el-input v-model="configForm.QINIU_BUCKET_NAME" placeholder="请输入存储空间名称" />
                  </el-form-item>
                  <el-form-item label="外链域名 (Domain)" class="flex-item">
                    <el-input v-model="configForm.QINIU_DOMAIN" placeholder="http://xxxx.qiniudn.com" />
                  </el-form-item>
                </div>
              </el-form>
            </el-tab-pane>
          </el-tabs>

          <div class="save-actions">
            <el-button type="primary" class="save-btn hover-scale" :loading="savingConfig" @click="handleSaveConfig">
              <el-icon><Check /></el-icon>
              <span>保存接口配置</span>
            </el-button>
          </div>
        </div>
      </div>

      <!-- Right Column: Operations & Preferences -->
      <div class="settings-ops-col">
        <!-- Audio Cache Card -->
        <div class="settings-card glass-card">
          <h3 class="card-title">
            <el-icon><Folder /></el-icon>
            <span>录音缓存管理</span>
          </h3>
          <p class="card-desc">用户每次说话的原始录音以及 AI 合成的语音都保存在本机的静态目录下。您可以一键释放这些缓存占用的存储空间。</p>
          
          <div class="cache-status-box">
            <div class="status-item">
              <span class="label">缓存文件数量:</span>
              <span class="value font-display">{{ cacheInfo.file_count }} 个</span>
            </div>
            <div class="status-item">
              <span class="label">占用硬盘空间:</span>
              <span class="value font-display text-gradient">{{ formatBytes(cacheInfo.total_size_bytes) }}</span>
            </div>
          </div>

          <div class="card-actions">
            <el-button 
              type="primary" 
              class="action-btn hover-scale" 
              @click="handleClearCache"
              :loading="clearingCache"
              :disabled="cacheInfo.file_count === 0"
            >
              <el-icon><Delete /></el-icon>
              <span>一键清理缓存文件</span>
            </el-button>
          </div>
        </div>

        <!-- Preferences Card -->
        <div class="settings-card glass-card">
          <h3 class="card-title">
            <el-icon><Operation /></el-icon>
            <span>系统偏好配置</span>
          </h3>
          <p class="card-desc">修改本地偏好设置，保存后将自动应用在后续的会话练习中。</p>
          
          <div class="preference-form">
            <div class="pref-item">
              <span class="pref-label">默认播放语速:</span>
              <el-radio-group v-model="playbackRate" size="default" @change="savePlaybackRate">
                <el-radio-button :value="0.8">0.8x (较慢)</el-radio-button>
                <el-radio-button :value="1.0">1.0x (正常)</el-radio-button>
                <el-radio-button :value="1.2">1.2x (较快)</el-radio-button>
              </el-radio-group>
            </div>

            <div class="pref-item">
              <span class="pref-label">录音提示音效:</span>
              <el-switch 
                v-model="playSoundEffects" 
                active-text="开启提示音" 
                inactive-text="静音"
                @change="saveSoundEffects"
              />
            </div>
          </div>
        </div>

        <!-- Database Reset Card -->
        <div class="settings-card glass-card">
          <h3 class="card-title danger-title">
            <el-icon><Warning /></el-icon>
            <span>数据库历史管理</span>
          </h3>
          <p class="card-desc">永久删除所有在 EchoTalk 中练习的历史记录和每次会话的文本与音频关联，此操作不可逆，请谨慎操作！</p>
          
          <div class="card-actions">
            <el-button 
              type="danger" 
              class="action-btn hover-scale danger-btn" 
              @click="handleClearDatabase"
              :loading="clearingDb"
            >
              <el-icon><CircleClose /></el-icon>
              <span>清空所有练习记录</span>
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAppStore } from '../store/useAppStore'

const store = useAppStore()

const cacheInfo = ref({
  file_count: 0,
  total_size_bytes: 0
})

const apiStatus = ref({
  deepseek_configured: false,
  openai_configured: false,
  xiaomi_configured: false,
  xunfei_configured: false,
  qiniu_configured: false
})

const clearingCache = ref(false)
const clearingDb = ref(false)

// 偏好设置
const playbackRate = ref(1.0)
const playSoundEffects = ref(true)

// API 接口配置相关变量
const activeTab = ref('llm')
const savingConfig = ref(false)
const configForm = ref({
  DEEPSEEK_API_KEY: '',
  DEEPSEEK_BASE_URL: '',
  DEEPSEEK_MODEL: '',
  OPENAI_API_KEY: '',
  OPENAI_BASE_URL: '',
  OPENAI_MODEL: '',
  XIAOMI_API_KEY: '',
  XIAOMI_BASE_URL: '',
  XIAOMI_MODEL: '',
  XFYUN_APP_ID: '',
  XFYUN_API_KEY: '',
  XFYUN_API_SECRET: '',
  BAIDU_API_KEY: '',
  BAIDU_SECRET_KEY: '',
  QINIU_ACCESS_KEY: '',
  QINIU_SECRET_KEY: '',
  QINIU_BUCKET_NAME: '',
  QINIU_DOMAIN: ''
})

// 字节大小单位转换
const formatBytes = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const fetchCacheInfo = async () => {
  try {
    const res = await axios.get(`${store.backendBaseUrl}/api/settings/cache-info`)
    cacheInfo.value = res.data
  } catch (err) {
    console.error('获取缓存空间失败:', err)
  }
}

const fetchApiStatus = async () => {
  try {
    const res = await axios.get(`${store.backendBaseUrl}/api/settings/config-status`)
    apiStatus.value = res.data
  } catch (err) {
    console.error('获取后端 API 秘钥配置状态失败:', err)
  }
}

const fetchConfig = async () => {
  try {
    const res = await axios.get(`${store.backendBaseUrl}/api/settings/config`)
    configForm.value = res.data
  } catch (err) {
    console.error('获取 API 配置失败:', err)
  }
}

const handleClearCache = async () => {
  try {
    clearingCache.value = true
    const res = await axios.post(`${store.backendBaseUrl}/api/settings/clear-cache`)
    ElMessage.success({
      message: `缓存文件清理完毕！共删除 ${res.data.cleared_count} 个多余音频，释放空间 ${formatBytes(res.data.freed_bytes)}。`,
      duration: 5000
    })
    await fetchCacheInfo()
  } catch (err) {
    ElMessage.error('清理音频缓存失败，请检查后端运行状态')
  } finally {
    clearingCache.value = false
  }
}

const handleClearDatabase = () => {
  ElMessageBox.confirm(
    '此操作将永久清空 SQLite 数据库中所有的历史对话明细和成绩单，清空后无法找回，是否确定清空？',
    '危险操作警告',
    {
      confirmButtonText: '确定彻底清空',
      cancelButtonText: '取消操作',
      type: 'warning',
      customClass: 'custom-danger-messagebox'
    }
  ).then(async () => {
    try {
      clearingDb.value = true
      const res = await axios.post(`${store.backendBaseUrl}/api/settings/clear-db`)
      ElMessage.success(`历史数据库已重置！共清理 ${res.data.deleted_histories} 条练习会话及相关数据。`)
      await fetchCacheInfo()
    } catch (err) {
      ElMessage.error('清空数据库记录失败')
    } finally {
      clearingDb.value = false
    }
  }).catch(() => {})
}

// 偏好设置保存
const savePlaybackRate = (val) => {
  localStorage.setItem('playback_rate', val.toString())
  ElMessage.success(`播放语速偏好已设为 ${val}x`)
}

const saveSoundEffects = (val) => {
  localStorage.setItem('play_sounds', val.toString())
  ElMessage.success(`录音提示音效已${val ? '开启' : '关闭'}`)
}

const handleSaveConfig = async () => {
  try {
    savingConfig.value = true
    const res = await axios.post(`${store.backendBaseUrl}/api/settings/config`, configForm.value)
    ElMessage.success(res.data.message || '配置已成功保存并应用！')
    await fetchApiStatus()
    await fetchConfig()
  } catch (err) {
    const errMsg = err.response?.data?.detail || '保存配置失败，请检查后端状态'
    ElMessage.error(errMsg)
  } finally {
    savingConfig.value = false
  }
}

onMounted(() => {
  fetchCacheInfo()
  fetchApiStatus()
  fetchConfig()

  // 载入本地偏好
  const savedRate = localStorage.getItem('playback_rate')
  if (savedRate) {
    playbackRate.value = parseFloat(savedRate)
  }
  const savedSounds = localStorage.getItem('play_sounds')
  if (savedSounds !== null) {
    playSoundEffects.value = savedSounds === 'true'
  }
})
</script>

<style scoped>
.settings-container {
  padding: 32px;
  height: calc(100vh - 64px);
  overflow-y: auto;
  background-color: var(--bg-color);
}

.settings-header {
  margin-bottom: 28px;
}

.page-title {
  font-size: 2.2rem;
  font-family: var(--font-display);
  font-weight: 800;
  margin-bottom: 6px;
}

.subtitle {
  color: var(--text-muted);
  font-size: 1.02rem;
}

.settings-layout-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 24px;
  align-items: start;
  margin-bottom: 28px;
}

.settings-config-col {
  width: 100%;
}

.settings-ops-col {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

@media (max-width: 1024px) {
  .settings-layout-grid {
    grid-template-columns: 1fr;
  }
}

.settings-card {
  padding: 28px;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
}

.card-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  border-left: 3px solid var(--primary-color);
  padding-left: 8px;
}

.danger-title {
  border-left-color: var(--danger-color);
}

.card-desc {
  font-size: 0.9rem;
  color: var(--text-muted);
  line-height: 1.6;
  margin-bottom: 24px;
}

/* Cache status style */
.cache-status-box {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.92rem;
}

.status-item .label {
  color: var(--text-secondary);
}

.status-item .value {
  font-weight: 700;
  color: var(--text-primary);
}

.card-actions {
  display: flex;
  gap: 16px;
}

.action-btn {
  padding: 12px 20px;
  font-weight: 600;
  border-radius: 8px;
}

.danger-btn {
  background: rgba(239, 68, 68, 0.15) !important;
  border: 1px solid rgba(239, 68, 68, 0.3) !important;
  color: #f87171 !important;
}

.danger-btn:hover {
  background: #ef4444 !important;
  border-color: #ef4444 !important;
  color: #fff !important;
}

/* API status list */
.api-status-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.api-status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(255, 255, 255, 0.01);
  border: 1px solid rgba(255, 255, 255, 0.04);
  padding: 12px 18px;
  border-radius: 8px;
}

.api-name-col {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.api-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary);
}

.api-model {
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* Preference items */
.preference-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.pref-item {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.pref-label {
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--text-secondary);
}

:deep(.el-radio-group .el-radio-button__inner) {
  background: rgba(17, 24, 39, 0.6) !important;
  border-color: rgba(255, 255, 255, 0.08) !important;
  color: var(--text-secondary) !important;
}

:deep(.el-radio-group .el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: var(--primary-color) !important;
  color: #fff !important;
}

/* Config Card Styles */
.config-card {
  margin-top: 0;
  width: 100%;
}

.config-tabs {
  margin-top: 16px;
}

/* Service grouping */
.service-group-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--primary-color);
  margin: 16px 0 12px 0;
  display: flex;
  align-items: center;
}

.service-group-title::before {
  content: "";
  display: inline-block;
  width: 4px;
  height: 14px;
  background-color: var(--primary-color);
  margin-right: 8px;
  border-radius: 2px;
}

/* Form row layouts */
.form-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.form-row-3 {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.form-row .flex-item {
  flex: 1;
  min-width: 200px;
}

.form-row-3 .flex-item {
  flex: 1;
  min-width: 180px;
}

.group-divider {
  margin: 20px 0 !important;
  border-top-color: rgba(255, 255, 255, 0.05) !important;
}

.save-actions {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
}

.save-btn {
  padding: 12px 28px;
  font-weight: 600;
  border-radius: 8px;
}

/* Form inputs styling override for glass theme */
:deep(.el-form-item__label) {
  color: var(--text-secondary) !important;
  font-weight: 600;
  font-size: 0.85rem;
  padding-bottom: 4px !important;
}

:deep(.el-input__wrapper) {
  background: rgba(17, 24, 39, 0.45) !important;
  border: 1px solid rgba(255, 255, 255, 0.06) !important;
  box-shadow: none !important;
  border-radius: 8px !important;
  padding: 4px 12px !important;
  transition: all 0.3s ease;
}

:deep(.el-input__wrapper:hover),
:deep(.el-input__wrapper.is-focus) {
  border-color: var(--primary-color) !important;
  background: rgba(17, 24, 39, 0.6) !important;
}

:deep(.el-input__inner) {
  color: var(--text-primary) !important;
}

:deep(.el-tabs__item) {
  color: var(--text-secondary) !important;
  font-weight: 600;
}

:deep(.el-tabs__item.is-active) {
  color: var(--primary-color) !important;
}

:deep(.el-tabs__active-bar) {
  background-color: var(--primary-color) !important;
}

:deep(.el-tabs__nav-wrap::after) {
  background-color: rgba(255, 255, 255, 0.05) !important;
}
</style>

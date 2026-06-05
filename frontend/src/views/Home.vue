<template>
  <div class="home-container">
    <!-- Hero Header -->
    <header class="hero-section">
      <h1 class="text-gradient logo-text">口语演练场景大厅</h1>
      <p class="subtitle">选择或定制专属英语角色与演练背景，开启沉浸式口语会话</p>
      <div class="actions-header">
        <el-button type="primary" size="large" class="create-btn hover-scale" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          <span>新建自定义场景</span>
        </el-button>
        <el-upload
          action="#"
          :http-request="handleImportScene"
          :show-file-list="false"
          accept=".zip"
          class="import-uploader-inline"
        >
          <el-button size="large" class="import-btn hover-scale">
            <el-icon><Upload /></el-icon>
            <span>导入场景包</span>
          </el-button>
        </el-upload>
      </div>
    </header>

    <!-- Scenes Grid -->
    <div v-loading="loading" class="scenes-grid">
      <div v-for="scene in scenes" :key="scene.id" class="scene-card glass-card">
        <div class="card-header">
          <span class="category-tag">{{ formatCategory(scene.category) }}</span>
          <div class="header-actions">
            <el-button 
              type="primary" 
              link 
              class="export-btn hover-scale" 
              @click.stop="exportScene(scene)"
            >
              <el-icon><Download /></el-icon>
              <span>导出包</span>
            </el-button>
            <el-button 
              type="primary" 
              link 
              class="config-btn hover-scale" 
              @click.stop="openConfigDialog(scene)"
            >
              <el-icon><Setting /></el-icon>
              <span>配置</span>
            </el-button>
          </div>
        </div>
        
        <h3 class="scene-title">{{ scene.name }}</h3>
        <p class="scene-desc">{{ scene.description }}</p>
        
        <!-- Parameter Badges -->
        <div class="param-badges" v-if="scene.default_params && Object.keys(scene.default_params).length > 0">
          <div 
            v-for="(val, key) in scene.default_params" 
            :key="key" 
            class="param-badge"
          >
            <span class="badge-key">{{ translateKey(key) }}:</span>
            <span class="badge-val">{{ val }}</span>
          </div>
        </div>

        <div class="rag-info" v-if="scene.rag_metadata && scene.rag_metadata.length > 0">
          <el-icon><FolderOpened /></el-icon>
          <span>已挂载 {{ scene.rag_metadata.length }} 个场景知识库文档</span>
        </div>
        
        <div class="card-footer">
          <el-button 
            type="primary" 
            class="start-btn hover-scale" 
            @click="startPractice(scene)"
          >
            <el-icon><ChatDotRound /></el-icon>
            <span>开始练习</span>
          </el-button>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="scenes.length === 0 && !loading" class="empty-state glass-card">
        <el-icon class="empty-icon"><Compass /></el-icon>
        <p>暂无场景，点击上方按钮创建一个吧！</p>
      </div>
    </div>

    <!-- Configure Scene Dialog -->
    <el-dialog
      v-model="configVisible"
      title="配置场景参数及知识库"
      width="650px"
      destroy-on-close
      class="custom-dialog"
      top="5vh"
    >
      <el-tabs v-model="activeTab" class="dialog-tabs">
        <!-- Tab 1: Parameter & Prompt Config -->
        <el-tab-pane label="参数与提示词配置" name="params">
          <el-form :model="configForm" label-position="top">
            <el-form-item label="场景名称">
              <el-input v-model="configForm.name" placeholder="例如: 繁忙咖啡厅点餐" />
            </el-form-item>
            <el-form-item label="场景描述">
              <el-input 
                v-model="configForm.description" 
                type="textarea" 
                :rows="2" 
                placeholder="简述场景，展示在主页卡片上..." 
              />
            </el-form-item>
            <el-form-item label="系统提示词 (System Prompt)">
              <el-input 
                v-model="configForm.system_prompt" 
                type="textarea" 
                :rows="4" 
                placeholder="设定 AI 角色性格、开场白及背景规则..." 
              />
            </el-form-item>
            <el-form-item label="首轮问候语 (Greeting Text)">
              <el-input 
                v-model="configForm.greeting_text" 
                type="textarea" 
                :rows="3" 
                placeholder="会话启动时由 AI 角色主动发出打招呼的语音和文字。支持变量插值（例如 {interviewer_name}）" 
              />
            </el-form-item>
            
            <div class="params-section">
              <div class="section-title">
                <span>个性化变量参数</span>
                <el-button type="primary" link size="small" @click="addConfigParam">
                  <el-icon><Plus /></el-icon>
                  <span>添加参数</span>
                </el-button>
              </div>
              
              <div v-for="(param, index) in configParams" :key="index" class="param-edit-row">
                <el-input v-model="param.key" placeholder="参数Key (如 weather)" class="param-input" />
                <el-input v-model="param.value" placeholder="参数值 (如 rainy)" class="param-input" />
                <el-button type="danger" link @click="removeConfigParam(index)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
          </el-form>
        </el-tab-pane>

        <!-- Tab 2: RAG Documents Config -->
        <el-tab-pane label="RAG 场景知识库文档" name="rag">
          <div class="rag-tab-content">
            <div class="rag-info-box">
              <p class="rag-tip">上传特定场景背景资料（如公司产品信息、面试秘籍、咖啡厅菜单等），AI 会结合这些背景来回答你的提问，且会自动屏蔽个人隐私信息。</p>
            </div>

            <!-- Upload Zone -->
            <el-upload
              drag
              multiple
              action="#"
              :http-request="handleUpload"
              :show-file-list="false"
              class="rag-uploader"
              accept=".pdf,.txt,.md,.markdown"
            >
              <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
              <div class="el-upload__text">
                将文件拖到此处，或 <em>点击上传</em>
                <div class="el-upload__tip">支持 PDF、TXT 或 Markdown 格式</div>
              </div>
            </el-upload>

            <!-- File List -->
            <div class="rag-file-list" v-if="activeScene && activeScene.rag_metadata && activeScene.rag_metadata.length > 0">
              <div class="file-list-header">
                <span>已上传文档 ({{ activeScene.rag_metadata.length }})</span>
                <el-button type="danger" link size="small" @click="clearRagDocs">
                  <el-icon><Delete /></el-icon>
                  <span>清空知识库</span>
                </el-button>
              </div>
              <div class="file-items">
                <div v-for="(file, idx) in activeScene.rag_metadata" :key="idx" class="file-item">
                  <div class="file-info">
                    <span class="file-name">{{ file.filename }}</span>
                    <span class="file-meta">拆分为 {{ file.chunk_count }} 个特征文本分块</span>
                  </div>
                  <span class="file-date">{{ formatDate(file.uploaded_at) }}</span>
                </div>
              </div>
            </div>
            <div v-else class="rag-empty-files">
              <p>当前场景暂未关联任何背景知识库文档</p>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <div class="dialog-footer-layout">
          <el-button 
            type="danger" 
            plain 
            class="dialog-delete-btn"
            @click="deleteScene(activeScene)"
          >
            <el-icon><Delete /></el-icon>
            <span>彻底删除此场景</span>
          </el-button>
          <div class="footer-right-actions">
            <el-button @click="configVisible = false">取消</el-button>
            <el-button type="primary" @click="saveConfig" :loading="savingConfig">保存配置</el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- Create Custom Scene Dialog -->
    <el-dialog
      v-model="createVisible"
      title="创建自定义口语练习场景"
      width="600px"
      class="custom-dialog"
      top="5vh"
    >
      <el-form :model="createForm" :rules="createRules" ref="createFormRef" label-position="top">
        <el-form-item label="场景 ID (唯一英文标识)" prop="id">
          <el-input v-model="createForm.id" placeholder="例如: cafe-cashier, daily-meeting" />
        </el-form-item>
        <el-form-item label="场景名称" prop="name">
          <el-input v-model="createForm.name" placeholder="例如: 咖啡厅收银员角色扮演" />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-select v-model="createForm.category" placeholder="请选择场景分类" style="width: 100%;">
            <el-option label="职场面试" value="interview" />
            <el-option label="日常点餐" value="ordering" />
            <el-option label="商务会议" value="meeting" />
            <el-option label="自定义演练" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="场景描述" prop="description">
          <el-input v-model="createForm.description" type="textarea" :rows="2" placeholder="展示在首页卡片上的一句话场景描述..." />
        </el-form-item>
        <el-form-item label="系统提示词 (System Prompt)" prop="system_prompt">
          <el-input v-model="createForm.system_prompt" type="textarea" :rows="4" placeholder="You are Leo, a cashier... 设定AI扮演的人物性格和场景规则。" />
        </el-form-item>
        <el-form-item label="首轮问候语 (Greeting Text)" prop="greeting_text">
          <el-input v-model="createForm.greeting_text" type="textarea" :rows="3" placeholder="例如: Welcome to our hotel! I am Emily. 开启对话时 AI 主动播报的首句英文问候语。" />
        </el-form-item>
        
        <div class="params-section">
          <div class="section-title">
            <span>开场默认变量参数</span>
            <el-button type="primary" link size="small" @click="addCreateParam">
              <el-icon><Plus /></el-icon>
              <span>添加参数</span>
            </el-button>
          </div>
          
          <div v-for="(param, index) in createParams" :key="index" class="param-edit-row">
            <el-input v-model="param.key" placeholder="参数Key (如 character_name)" class="param-input" />
            <el-input v-model="param.value" placeholder="参数值 (如 Leo)" class="param-input" />
            <el-button type="danger" link @click="removeCreateParam(index)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="createVisible = false">取消</el-button>
          <el-button type="primary" @click="handleCreateScene" :loading="creatingScene">确认创建</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '../store/useAppStore'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const store = useAppStore()

// State
const scenes = ref([])
const loading = ref(false)
const configVisible = ref(false)
const createVisible = ref(false)
const activeTab = ref('params')
const activeScene = ref(null)

const savingConfig = ref(false)
const creatingScene = ref(false)

// Config Form
const configForm = reactive({
  name: '',
  description: '',
  system_prompt: '',
  greeting_text: ''
})
const configParams = ref([])

// Create Form
const createFormRef = ref(null)
const createForm = reactive({
  id: '',
  name: '',
  description: '',
  category: 'custom',
  system_prompt: '',
  greeting_text: ''
})
const createParams = ref([
  { key: 'character_name', value: 'AI Assistant' }
])

const createRules = {
  id: [
    { required: true, message: '请输入场景唯一英文 ID', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_-]+$/, message: '只能包含英文字母、数字、短横线-和下划线_', trigger: 'blur' }
  ],
  name: [{ required: true, message: '请输入场景名称', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  system_prompt: [{ required: true, message: '请输入系统提示词', trigger: 'blur' }]
}

// Lifecycle
onMounted(() => {
  fetchScenes()
})

// Fetch Scenes
const fetchScenes = async () => {
  loading.value = true
  try {
    const res = await axios.get(`${store.backendBaseUrl}/api/scenes`)
    scenes.value = res.data
  } catch (err) {
    ElMessage.error('获取练习场景列表失败，请检查后端服务是否启动。')
  } finally {
    loading.value = false
  }
}

// Formats
const formatCategory = (category) => {
  const mapping = {
    interview: '职场面试',
    ordering: '日常点餐',
    meeting: '商务会议',
    custom: '自定义练习'
  }
  return mapping[category] || '练习场景'
}

const translateKey = (key) => {
  const mapping = {
    personality: '性格/特质',
    company_name: '公司名称',
    job_title: '面试岗位',
    interviewer_name: '面试官',
    store_name: '店铺名称',
    cashier_name: '服务员',
    chairperson_name: '会议主持',
    topic: '会议议题',
    character_name: '角色名称'
  }
  return mapping[key] || key
}

const formatDate = (isoStr) => {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  } catch {
    return isoStr
  }
}

// Config Actions
const openConfigDialog = (scene) => {
  activeScene.value = scene
  configForm.name = scene.name
  configForm.description = scene.description
  configForm.system_prompt = scene.system_prompt
  configForm.greeting_text = scene.greeting_text || ''
  
  // Transform dict parameter to list for rendering
  configParams.value = Object.entries(scene.default_params || {}).map(([key, val]) => ({
    key,
    value: String(val)
  }))
  
  activeTab.value = 'params'
  configVisible.value = true
}

const addConfigParam = () => {
  configParams.value.push({ key: '', value: '' })
}

const removeConfigParam = (index) => {
  configParams.value.splice(index, 1)
}

const saveConfig = async () => {
  if (!activeScene.value) return
  savingConfig.value = true
  
  // Assemble parameters dict
  const default_params = {}
  configParams.value.forEach(item => {
    if (item.key.trim()) {
      default_params[item.key.trim()] = item.value
    }
  })
  
  const payload = {
    name: configForm.name,
    description: configForm.description,
    system_prompt: configForm.system_prompt,
    greeting_text: configForm.greeting_text,
    default_params
  }
  
  try {
    const res = await axios.put(
      `${store.backendBaseUrl}/api/scenes/${activeScene.value.id}`,
      payload
    )
    ElMessage.success('场景配置更新成功！')
    
    // Update local state
    const idx = scenes.value.findIndex(s => s.id === activeScene.value.id)
    if (idx !== -1) {
      scenes.value[idx] = res.data
    }
    configVisible.value = false
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '保存配置失败')
  } finally {
    savingConfig.value = false
  }
}

// Upload RAG docs
const handleUpload = async (options) => {
  if (!activeScene.value) return
  const { file, onProgress, onSuccess, onError } = options
  const formData = new FormData()
  formData.append('file', file)
  
  try {
    const res = await axios.post(
      `${store.backendBaseUrl}/api/scenes/${activeScene.value.id}/upload`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (e.total) {
            const percent = Math.round((e.loaded * 100) / e.total)
            onProgress({ percent })
          }
        }
      }
    )
    ElMessage.success('知识库文档上传并向量化成功！')
    activeScene.value = res.data
    
    // Update state
    const idx = scenes.value.findIndex(s => s.id === activeScene.value.id)
    if (idx !== -1) {
      scenes.value[idx] = res.data
    }
    onSuccess(res.data)
  } catch (err) {
    const errMsg = err.response?.data?.detail || '文档上传失败，请确保格式合规且文本可提取'
    ElMessage.error(errMsg)
    onError(err)
  }
}

const clearRagDocs = () => {
  if (!activeScene.value) return
  ElMessageBox.confirm(
    '确定清空该场景所有的 RAG 背景知识库文档吗？清空后 AI 回复将失去相关背景知识参考。',
    '警告',
    {
      confirmButtonText: '确定清空',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      const res = await axios.delete(
        `${store.backendBaseUrl}/api/scenes/${activeScene.value.id}/documents`
      )
      ElMessage.success('知识库清除成功！')
      activeScene.value = res.data
      
      // Update state
      const idx = scenes.value.findIndex(s => s.id === activeScene.value.id)
      if (idx !== -1) {
        scenes.value[idx] = res.data
      }
    } catch (err) {
      ElMessage.error('清空知识库失败')
    }
  }).catch(() => {})
}

// Create Custom Scene
const openCreateDialog = () => {
  createForm.id = ''
  createForm.name = ''
  createForm.description = ''
  createForm.category = 'custom'
  createForm.system_prompt = ''
  createForm.greeting_text = ''
  createParams.value = [{ key: 'character_name', value: 'AI Assistant' }]
  createVisible.value = true
}

const addCreateParam = () => {
  createParams.value.push({ key: '', value: '' })
}

const removeCreateParam = (index) => {
  createParams.value.splice(index, 1)
}

const handleCreateScene = async () => {
  if (!createFormRef.value) return
  
  createFormRef.value.validate(async (valid) => {
    if (!valid) return
    creatingScene.value = true
    
    // Assemble parameters
    const default_params = {}
    createParams.value.forEach(item => {
      if (item.key.trim()) {
        default_params[item.key.trim()] = item.value
      }
    })
    
    const payload = {
      id: createForm.id.trim(),
      name: createForm.name.trim(),
      description: createForm.description.trim(),
      category: createForm.category,
      default_params,
      system_prompt: createForm.system_prompt.trim(),
      greeting_text: createForm.greeting_text.trim()
    }
    
    try {
      const res = await axios.post(`${store.backendBaseUrl}/api/scenes`, payload)
      ElMessage.success('自定义练习场景创建成功！')
      scenes.value.push(res.data)
      createVisible.value = false
    } catch (err) {
      ElMessage.error(err.response?.data?.detail || '创建场景失败，可能 ID 已被占用。')
    } finally {
      creatingScene.value = false
    }
  })
}

// Start Practice
const startPractice = (scene) => {
  store.setCurrentScene(scene)
  router.push({ name: 'Practice', params: { sceneId: scene.id } })
}

// Delete Scene
const deleteScene = (scene) => {
  ElMessageBox.confirm(
    `确定要彻底删除场景【${scene.name}】吗？这将会永久清除该场景的数据库配置、本地 RAG 知识库文档、向量索引，以及该场景下的所有练习历史与发音得分记录，此操作不可恢复！`,
    '严重的警告',
    {
      confirmButtonText: '确定彻底删除',
      cancelButtonText: '取消',
      type: 'error',
      confirmButtonClass: 'el-button--danger'
    }
  ).then(async () => {
    try {
      await axios.delete(`${store.backendBaseUrl}/api/scenes/${scene.id}`)
      ElMessage.success(`场景【${scene.name}】已成功彻底删除。`)
      scenes.value = scenes.value.filter(s => s.id !== scene.id)
      configVisible.value = false
    } catch (err) {
      ElMessage.error(err.response?.data?.detail || '删除场景失败')
    }
  }).catch(() => {})
}

// Export Scene Package (.zip)
const exportScene = (scene) => {
  const exportUrl = `${store.backendBaseUrl}/api/scenes/${scene.id}/export`
  // 直接通过新窗口触发浏览器原生的下载保存
  window.open(exportUrl, '_blank')
  ElMessage.success(`正在打包生成场景包【scene_${scene.id}.zip】，即将开始下载...`)
}

// Import Scene Package (.zip)
const handleImportScene = async (options) => {
  const { file, onSuccess, onError } = options
  const formData = new FormData()
  formData.append('file', file)
  
  try {
    const res = await axios.post(
      `${store.backendBaseUrl}/api/scenes/import`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' }
      }
    )
    
    ElMessage.success(`场景【${res.data.name}】一键解包并导入成功！向量知识库已完美还原。`)
    
    // 更新或追加本地场景大厅列表
    const idx = scenes.value.findIndex(s => s.id === res.data.id)
    if (idx !== -1) {
      scenes.value[idx] = res.data
    } else {
      scenes.value.push(res.data)
    }
    
    onSuccess(res.data)
  } catch (err) {
    const errMsg = err.response?.data?.detail || '导入场景包失败，请确保 ZIP 压缩包内容合法'
    ElMessage.error(errMsg)
    onError(err)
  }
}
</script>

<style scoped>
.home-container {
  padding: 40px 60px;
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.hero-section {
  text-align: center;
  margin-bottom: 50px;
}

.logo-text {
  font-size: 3.6rem;
  font-family: var(--font-display);
  font-weight: 800;
  margin-bottom: 8px;
}

.subtitle {
  font-size: 1.15rem;
  color: var(--text-secondary);
  letter-spacing: 0.05em;
  margin-bottom: 24px;
}

.actions-header {
  display: flex;
  justify-content: center;
  gap: 16px;
}

.create-btn {
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%) !important;
  border: none !important;
  font-weight: 600;
  border-radius: 8px;
  padding: 12px 24px;
  box-shadow: 0 4px 14px 0 rgba(99, 102, 241, 0.3);
}

.scenes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 30px;
  width: 100%;
}

.scene-card {
  padding: 24px;
  display: flex;
  flex-direction: column;
  height: 330px;
  position: relative;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.category-tag {
  font-size: 0.75rem;
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.25);
  color: #818cf8;
  padding: 3px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.config-btn {
  background: rgba(255, 255, 255, 0.03) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  color: var(--text-secondary) !important;
  font-size: 0.78rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px !important;
  height: auto !important;
  border-radius: 20px !important;
  transition: var(--transition-smooth);
}

.config-btn:hover {
  background: rgba(99, 102, 241, 0.1) !important;
  border-color: rgba(99, 102, 241, 0.3) !important;
  color: #818cf8 !important;
  filter: drop-shadow(0 0 6px rgba(99, 102, 241, 0.35));
}

.export-btn {
  background: rgba(255, 255, 255, 0.03) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  color: var(--text-secondary) !important;
  font-size: 0.78rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px !important;
  height: auto !important;
  border-radius: 20px !important;
  transition: var(--transition-smooth);
}

.export-btn:hover {
  background: rgba(16, 185, 129, 0.08) !important;
  border-color: rgba(16, 185, 129, 0.25) !important;
  color: #34d399 !important;
  filter: drop-shadow(0 0 6px rgba(16, 185, 129, 0.35));
}

.dialog-footer-layout {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.dialog-delete-btn {
  background: rgba(239, 68, 68, 0.08) !important;
  border: 1px solid rgba(239, 68, 68, 0.25) !important;
  color: #f87171 !important;
  border-radius: 20px !important;
  font-weight: 600 !important;
  padding: 8px 16px !important;
  height: auto !important;
  transition: var(--transition-smooth);
}

.dialog-delete-btn:hover {
  background: rgba(239, 68, 68, 0.15) !important;
  border-color: rgba(239, 68, 68, 0.4) !important;
  color: #fca5a5 !important;
  filter: drop-shadow(0 0 6px rgba(239, 68, 68, 0.3));
}

.footer-right-actions {
  display: flex;
  gap: 12px;
}

.import-uploader-inline {
  display: inline-block;
}

.import-btn {
  background: rgba(255, 255, 255, 0.03) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  color: var(--text-secondary) !important;
  font-weight: 600;
  border-radius: 8px;
  padding: 12px 24px;
  transition: var(--transition-smooth);
}

.import-btn:hover {
  background: rgba(255, 255, 255, 0.08) !important;
  border-color: rgba(255, 255, 255, 0.15) !important;
  color: var(--text-primary) !important;
}

.scene-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 10px;
  line-height: 1.4;
}

.scene-desc {
  color: var(--text-secondary);
  font-size: 0.85rem;
  line-height: 1.5;
  margin-bottom: 18px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex-grow: 1;
}

.param-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.param-badge {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  padding: 4px 8px;
  font-size: 0.75rem;
  display: flex;
  gap: 4px;
}

.badge-key {
  color: var(--text-muted);
  font-weight: 500;
}

.badge-val {
  color: var(--text-secondary);
  font-weight: 600;
}

.rag-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  color: var(--accent-color);
  margin-bottom: 16px;
  font-weight: 500;
}

.card-footer {
  margin-top: auto;
}

.start-btn {
  width: 100%;
  font-weight: 600;
  border-radius: 8px;
  background: #1f2937 !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  color: var(--text-primary) !important;
}

.start-btn:hover {
  background: var(--primary-color) !important;
  border-color: var(--primary-color) !important;
  box-shadow: 0 4px 12px 0 rgba(99, 102, 241, 0.25);
}

.empty-state {
  grid-column: 1 / -1;
  padding: 60px;
  text-align: center;
  color: var(--text-muted);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.empty-icon {
  font-size: 3rem;
  color: var(--text-muted);
}

/* Dialog Styling to match Sleek Dark Theme */
:deep(.custom-dialog) {
  background: #111827 !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-radius: 12px !important;
}

:deep(.custom-dialog .el-dialog__title) {
  color: var(--text-primary) !important;
  font-weight: 700;
}

:deep(.custom-dialog .el-dialog__headerbtn .el-dialog__close) {
  color: var(--text-muted) !important;
}

:deep(.custom-dialog .el-form-item__label) {
  color: var(--text-secondary) !important;
  font-weight: 600;
  padding-bottom: 4px;
}

.params-section {
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  margin-top: 20px;
  padding-top: 16px;
}

.section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--text-primary);
  font-size: 0.9rem;
  font-weight: 600;
  margin-bottom: 12px;
}

.param-edit-row {
  display: flex;
  gap: 12px;
  margin-bottom: 10px;
}

.param-input {
  flex-grow: 1;
}

.rag-tab-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.rag-info-box {
  background: rgba(99, 102, 241, 0.05);
  border: 1px dashed rgba(99, 102, 241, 0.2);
  padding: 12px 16px;
  border-radius: 8px;
}

.rag-tip {
  font-size: 0.8rem;
  color: #a5b4fc;
  line-height: 1.5;
}

.rag-uploader :deep(.el-upload-dragger) {
  background: rgba(17, 24, 39, 0.6) !important;
  border: 1px dashed rgba(255, 255, 255, 0.12) !important;
  border-radius: 10px;
  transition: var(--transition-smooth);
}

.rag-uploader :deep(.el-upload-dragger:hover) {
  border-color: var(--primary-color) !important;
}

.rag-uploader :deep(.el-upload__text) {
  color: var(--text-secondary) !important;
  font-size: 0.85rem;
}

.rag-uploader :deep(.el-upload__text em) {
  color: var(--primary-color) !important;
  font-style: normal;
  font-weight: 600;
}

.rag-uploader :deep(.el-upload__tip) {
  color: var(--text-muted);
  margin-top: 6px;
  font-size: 0.75rem;
}

.rag-file-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.file-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
  color: var(--text-primary);
  font-weight: 600;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding-bottom: 8px;
}

.file-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.file-item {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 6px;
  padding: 10px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.file-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-name {
  font-size: 0.85rem;
  color: var(--text-primary);
  font-weight: 500;
  word-break: break-all;
}

.file-meta {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.file-date {
  font-size: 0.75rem;
  color: var(--text-muted);
  flex-shrink: 0;
}

.rag-empty-files {
  text-align: center;
  padding: 30px;
  color: var(--text-muted);
  font-size: 0.85rem;
}
</style>

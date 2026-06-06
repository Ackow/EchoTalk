<template>
  <el-dialog
    v-model="visible"
    :title="sceneName + ' — 背景知识参考'"
    width="680px"
    class="knowledge-dialog"
    top="5vh"
    :close-on-click-modal="true"
    destroy-on-close
  >
    <!-- Loading State -->
    <div v-if="loading" class="knowledge-loading" v-loading="true" element-loading-text="正在获取场景知识..." style="height: 300px"></div>

    <!-- Error State -->
    <div v-else-if="error" class="knowledge-empty">
      <el-icon class="empty-icon"><WarningFilled /></el-icon>
      <p>{{ error }}</p>
    </div>

    <!-- Empty (no knowledge available) -->
    <div v-else-if="!hasKnowledge" class="knowledge-empty">
      <el-icon class="empty-icon"><Reading /></el-icon>
      <p>该场景暂无对用户可见的背景知识。</p>
      <p class="empty-hint">管理员可以在「场景配置→RAG知识库」中上传文档，并设置分节可见性。</p>
    </div>

    <!-- Knowledge Content -->
    <div v-else class="knowledge-content">
      <div v-for="(section, idx) in knowledgeSections" :key="idx" class="knowledge-section-card">
        <!-- Section Header -->
        <div class="section-header">
          <el-icon><Reading /></el-icon>
          <h3 class="section-title">{{ getSectionTitle(section.section) }}</h3>
        </div>
        <!-- Section Body as formatted text -->
        <pre class="section-body">{{ cleanContent(section.content) }}</pre>
      </div>
      <p class="knowledge-footer-note">💡 练习时点击右上角「场景参考」按钮也可随时查看此内容。</p>
    </div>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <el-button type="primary" @click="startPractice">
        <el-icon><ChatDotRound /></el-icon>
        开始练习
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '../store/useAppStore'
import axios from 'axios'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  sceneId: { type: String, default: '' },
  sceneName: { type: String, default: '' },
  sceneData: { type: Object, default: null }
})

const emit = defineEmits(['update:modelValue', 'start-practice'])

const router = useRouter()
const store = useAppStore()

const visible = ref(false)
const loading = ref(false)
const error = ref('')
const hasKnowledge = ref(false)
const knowledgeSections = ref([])

watch(() => props.modelValue, (val) => {
  visible.value = val
  if (val && props.sceneId) {
    fetchKnowledge()
  }
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

const fetchKnowledge = async () => {
  loading.value = true
  error.value = ''
  hasKnowledge.value = false
  knowledgeSections.value = []

  try {
    const res = await axios.get(`${store.backendBaseUrl}/api/scenes/${props.sceneId}/knowledge`)
    const data = res.data
    hasKnowledge.value = data.has_knowledge
    knowledgeSections.value = data.sections || []
  } catch (err) {
    error.value = err.response?.data?.detail || '获取场景知识失败，请检查后端服务'
  } finally {
    loading.value = false
  }
}

const startPractice = () => {
  visible.value = false
  if (props.sceneData) {
    store.setCurrentScene(props.sceneData)
    router.push({ name: 'practice', params: { sceneId: props.sceneData.id } })
  }
}

// ── Display helpers ──

const sectionTitles = {
  menu:           '☕ 菜单与价格',
  customization:  '⚙️ 定制选项',
  vocabulary:     '📖 常用口语表达',
  interview:      '💼 面试指南',
  meeting:        '📋 会议议程',
  general:        '📄 通用知识',
  barista_workflow: '🔧 服务流程',
}

const getSectionTitle = (section) => {
  return sectionTitles[section] || section
}

const cleanContent = (text) => {
  // Strip markdown bold/italic markers for cleaner display
  return text.replace(/\*{1,2}([^*]+)\*{1,2}/g, '$1')
             .replace(/`([^`]+)`/g, '$1')
             .replace(/^##+\s+/gm, '')
             .trim()
}
</script>

<style scoped>
.knowledge-dialog :deep(.el-dialog__body) {
  padding: 16px 24px 12px;
  max-height: 65vh;
  overflow-y: auto;
}

.knowledge-loading,
.knowledge-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
  gap: 12px;
  color: var(--text-secondary);
}

.empty-icon {
  font-size: 2.5rem;
  color: var(--text-muted);
}

.empty-hint {
  font-size: 0.85rem;
  color: var(--text-muted);
  max-width: 360px;
}

.knowledge-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.knowledge-section-card {
  background: rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  padding: 14px 16px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.section-title {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.section-body {
  font-size: 0.9rem;
  line-height: 1.65;
  color: var(--text-secondary);
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: inherit;
  margin: 0;
}

.knowledge-footer-note {
  text-align: center;
  font-size: 0.82rem;
  color: var(--text-muted);
  margin: 4px 0 0;
}
</style>

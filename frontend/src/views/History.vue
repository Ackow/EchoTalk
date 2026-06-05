<template>
  <div class="history-container">
    <!-- Header -->
    <header class="history-header">
      <h1 class="text-gradient page-title">练习历史</h1>
      <p class="subtitle">追溯练习足迹，回放历史音频，感受你的发音与语法蜕变</p>
    </header>

    <!-- History List Grid -->
    <div v-loading="loading" class="history-grid">
      <div v-for="item in historyList" :key="item.id" class="history-card glass-card hover-glow" @click="openDetailDrawer(item)">
        <div class="card-top">
          <span class="category-tag">{{ formatCategory(item.scene_id) }}</span>
          <div class="card-top-right">
            <span class="time-badge">{{ formatDate(item.start_time) }}</span>
            <el-button 
              type="danger" 
              link 
              class="delete-history-btn" 
              @click.stop="handleDeleteHistory(item)"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>
        
        <h3 class="scene-title">{{ getSceneName(item.scene_id) }}</h3>
        
        <div class="card-stats">
          <div class="stat-item">
            <span class="stat-label">对话轮次</span>
            <span class="stat-val">{{ item.turns ? Math.floor(item.turns.length / 2) : 0 }}轮</span>
          </div>
          <div class="stat-item score-stat" v-if="item.overall_score">
            <span class="stat-label">发音平均分</span>
            <span class="stat-val text-gradient font-display">{{ item.overall_score }}</span>
          </div>
          <div class="stat-item score-stat" v-else>
            <span class="stat-label">发音平均分</span>
            <span class="stat-val text-muted">未结算</span>
          </div>
        </div>

        <div class="card-action">
          <span>查看详情与回放</span>
          <el-icon><ArrowRight /></el-icon>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="historyList.length === 0 && !loading" class="empty-state glass-card">
        <el-icon class="empty-icon"><Clock /></el-icon>
        <p>这里静悄悄的，快去场景大厅开启你的第一次口语演练吧！</p>
        <el-button type="primary" class="go-practice-btn hover-scale" @click="$router.push('/')">去大厅练习</el-button>
      </div>
    </div>

    <!-- Detail Drawer -->
    <el-drawer
      v-model="drawerVisible"
      title="口语演练历史详情"
      size="720px"
      destroy-on-close
      class="history-drawer"
      @close="handleDrawerClose"
    >
      <div v-loading="detailLoading" class="drawer-content">
        <!-- Scene Title inside Drawer -->
        <div class="drawer-header-meta" v-if="selectedHistory">
          <h3>{{ getSceneName(selectedHistory.scene_id) }}</h3>
          <div class="meta-row">
            <el-tag size="small" type="info">{{ formatDate(selectedHistory.start_time) }}</el-tag>
            <el-tag size="small" type="success" v-if="selectedHistory.overall_score">{{ selectedHistory.overall_score }}分</el-tag>
          </div>
        </div>

        <!-- Dialogue Bubble History -->
        <div class="chat-history-drawer">
          <div v-for="(turn, idx) in detailTurns" :key="turn.id || idx" class="turn-block">
            <div :class="['message-row-drawer', turn.role === 'user' ? 'user-row' : 'ai-row']">
              <!-- AI Message -->
              <template v-if="turn.role === 'assistant'">
                <div class="avatar ai-avatar">AI</div>
                <div class="bubble-wrapper-drawer">
                  <div class="bubble ai-bubble glass-card">
                    <p class="message-text">{{ turn.text }}</p>
                    <div class="bubble-actions">
                      <el-button type="primary" link class="audio-play-btn" @click="playAudio(turn.audio_url, turn.id || idx)">
                        <el-icon v-if="playingTurnId === (turn.id || idx)"><VideoPlay /></el-icon>
                        <el-icon v-else><Headset /></el-icon>
                        <span>{{ playingTurnId === (turn.id || idx) ? '播放中...' : '回放AI语音' }}</span>
                      </el-button>
                    </div>
                  </div>
                </div>
              </template>

              <!-- User Message -->
              <template v-else>
                <div class="bubble-wrapper-drawer" @click="toggleEvaluatePanel(idx)">
                  <div :class="['bubble user-bubble glass-card', { 'active-user-bubble': expandedTurnIndex === idx }]">
                    <p class="message-text">{{ turn.text }}</p>
                    
                    <!-- 语法纠错常驻简易对比气泡 (解决漏看修改评语的UX痛点) -->
                    <div 
                      class="bubble-correction-snippet" 
                      v-if="turn.grammar_correction && turn.grammar_correction.original !== turn.grammar_correction.corrected"
                    >
                      <el-icon class="warning-icon"><Warning /></el-icon>
                      <span class="polished-hint">优化建议: "{{ turn.grammar_correction.corrected }}"</span>
                    </div>

                    <div class="bubble-score" v-if="turn.pronunciation_score">
                      <el-tag size="small" type="success" effect="dark" class="score-tag">
                        {{ turn.pronunciation_score.total_score }}分
                      </el-tag>
                    </div>
                  </div>
                  <div class="bubble-actions-left">
                    <el-button type="primary" link class="audio-play-btn user-play-btn" @click.stop="playAudio(turn.audio_url, turn.id || idx)">
                      <el-icon v-if="playingTurnId === (turn.id || idx)"><VideoPlay /></el-icon>
                      <el-icon v-else><Mic /></el-icon>
                      <span>{{ playingTurnId === (turn.id || idx) ? '播放中...' : '回放原声' }}</span>
                    </el-button>
                    <span class="details-toggle-btn">
                      {{ expandedTurnIndex === idx ? '收起详情 ▲' : '发音五维/纠错原因 ▼' }}
                    </span>
                  </div>
                </div>
                <div class="avatar user-avatar">ME</div>
              </template>
            </div>

            <!-- Expandable Evaluation Panel (Inline) -->
            <el-collapse-transition>
              <div v-if="turn.role === 'user' && expandedTurnIndex === idx" class="inline-eval-panel glass-card">
                <!-- Radar -->
                <div class="inline-section-title">口语发音分析</div>
                <div class="radar-container" v-if="turn.pronunciation_score">
                  <EChartsRadar :score-data="turn.pronunciation_score" height="200px" />
                </div>
                
                <!-- Grammar -->
                <div class="inline-section-title" style="margin-top: 16px;">语法建议详情</div>
                <div class="grammar-container" v-if="turn.grammar_correction">
                  <!-- No corrections needed -->
                  <div v-if="turn.grammar_correction.original === turn.grammar_correction.corrected" class="grammar-ok">
                    <el-icon class="ok-icon"><SuccessFilled /></el-icon>
                    <span>{{ turn.grammar_correction.explanation }}</span>
                  </div>
                  <!-- Has suggestions -->
                  <div v-else class="grammar-needs-fix">
                    <div class="fix-row">
                      <div class="badge-tag tag-red">原文 (Original)</div>
                      <p class="text-block red-text">{{ turn.grammar_correction.original }}</p>
                    </div>
                    <div class="fix-row">
                      <div class="badge-tag tag-green">优化 (Polished)</div>
                      <p class="text-block green-text">{{ turn.grammar_correction.corrected }}</p>
                    </div>
                    <div class="explanation-box">
                      <span class="exp-title">修改说明 (Chinese Explanation):</span>
                      <p class="exp-content">{{ turn.grammar_correction.explanation }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </el-collapse-transition>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '../store/useAppStore'
import EChartsRadar from '../components/EChartsRadar.vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

const store = useAppStore()

// State
const historyList = ref([])
const loading = ref(false)

const drawerVisible = ref(false)
const detailLoading = ref(false)
const selectedHistory = ref(null)
const detailTurns = ref([])
const expandedTurnIndex = ref(null)

const playingTurnId = ref(null)
const activeAudio = ref(null)

// Predefined scene metadata mappings
const sceneMetaMap = ref({
  interview: { name: '软件工程师面试', category: 'interview' },
  ordering: { name: '咖啡厅英文点餐', category: 'ordering' },
  meeting: { name: '项目同步会议', category: 'meeting' }
})

// Lifecycle
onMounted(() => {
  fetchHistory()
})

onUnmounted(() => {
  stopAudio()
})

// Fetch history from backend
const fetchHistory = async () => {
  loading.value = true
  try {
    const res = await axios.get(`${store.backendBaseUrl}/api/dialogues/`, {
      params: { user_id: 1 } // default_user
    })
    historyList.value = res.data
    
    // Register custom scenes from history records
    registerCustomSceneNames(res.data)
  } catch (err) {
    ElMessage.error('拉取历史记录失败，请确保后端服务正常')
  } finally {
    loading.value = false
  }
}

// Fetch dialogue detail for drawer
const fetchHistoryDetail = async (id) => {
  detailLoading.value = true
  try {
    const res = await axios.get(`${store.backendBaseUrl}/api/dialogues/${id}`)
    detailTurns.value = res.data.turns || []
  } catch (err) {
    ElMessage.error('加载会话详情失败')
  } finally {
    detailLoading.value = false
  }
}

// Drawer Actions
const openDetailDrawer = (historyItem) => {
  selectedHistory.value = historyItem
  detailTurns.value = []
  expandedTurnIndex.value = null
  stopAudio()
  
  drawerVisible.value = true
  fetchHistoryDetail(historyItem.id)
}

const handleDrawerClose = () => {
  stopAudio()
}

const handleDeleteHistory = (item) => {
  ElMessageBox.confirm(
    '确定要删除这一条练习历史记录吗？删除后将无法找回。',
    '删除确认',
    {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning',
      customClass: 'custom-message-box'
    }
  ).then(async () => {
    try {
      await axios.delete(`${store.backendBaseUrl}/api/dialogues/${item.id}`)
      ElMessage.success('历史记录删除成功')
      fetchHistory()
    } catch (err) {
      ElMessage.error('删除历史记录失败，请检查网络')
    }
  }).catch(() => {})
}

const toggleEvaluatePanel = (idx) => {
  if (expandedTurnIndex.value === idx) {
    expandedTurnIndex.value = null
  } else {
    expandedTurnIndex.value = idx
  }
}

// Audio Playback
const playAudio = (url, turnId) => {
  stopAudio()
  
  if (!url) {
    ElMessage.info('未生成回放音频。')
    return
  }
  
  if (playingTurnId.value === turnId) {
    playingTurnId.value = null
    return
  }
  
  let fullUrl = url
  if (!url.startsWith('http')) {
    fullUrl = `${store.backendBaseUrl}${url}`
  }
  
  const audio = new Audio(fullUrl)
  
  audio.onended = () => {
    playingTurnId.value = null
    activeAudio.value = null
  }
  
  audio.onerror = () => {
    ElMessage.error('历史音频加载失败')
    playingTurnId.value = null
    activeAudio.value = null
  }
  
  playingTurnId.value = turnId
  activeAudio.value = audio
  audio.play()
}

const stopAudio = () => {
  if (activeAudio.value) {
    activeAudio.value.pause()
    activeAudio.value = null
  }
  playingTurnId.value = null
}

// Formatting helpers
const formatCategory = (sceneId) => {
  const meta = sceneMetaMap.value[sceneId]
  const mapping = {
    interview: '职场面试',
    ordering: '日常点餐',
    meeting: '商务会议',
    custom: '自定义练习'
  }
  return mapping[meta?.category] || '练习演练'
}

const getSceneName = (sceneId) => {
  return sceneMetaMap.value[sceneId]?.name || sceneId
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

// Dynamic register custom scene names in mapping
const registerCustomSceneNames = async (histories) => {
  const uniqueSceneIds = [...new Set(histories.map(h => h.scene_id))].filter(
    id => !sceneMetaMap.value[id]
  )
  
  for (const id of uniqueSceneIds) {
    try {
      const res = await axios.get(`${store.backendBaseUrl}/api/scenes/${id}`)
      sceneMetaMap.value[id] = {
        name: res.data.name,
        category: res.data.category
      }
    } catch {
      sceneMetaMap.value[id] = {
        name: `自定义场景 (${id})`,
        category: 'custom'
      }
    }
  }
}
</script>

<style scoped>
.history-container {
  padding: 40px 60px;
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.history-header {
  margin-bottom: 40px;
}

.page-title {
  font-size: 2.5rem;
  font-family: var(--font-display);
  font-weight: 800;
  margin-bottom: 8px;
}

.subtitle {
  font-size: 1.05rem;
  color: var(--text-secondary);
}

/* Grid layout */
.history-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 24px;
  width: 100%;
}

.history-card {
  padding: 22px;
  display: flex;
  flex-direction: column;
  height: 200px;
  cursor: pointer;
  position: relative;
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.card-top-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.delete-history-btn {
  color: var(--text-muted) !important;
  font-size: 0.95rem;
  padding: 0 !important;
  margin-left: 4px;
  transition: color 0.2s ease, transform 0.2s ease;
}

.delete-history-btn:hover {
  color: var(--danger-color) !important;
  transform: scale(1.15);
}

.category-tag {
  font-size: 0.72rem;
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.2);
  color: #818cf8;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.time-badge {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.scene-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: auto;
  line-height: 1.3;
}

.card-stats {
  display: flex;
  gap: 20px;
  margin-top: 12px;
  margin-bottom: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 0.7rem;
  color: var(--text-muted);
  margin-bottom: 2px;
}

.stat-val {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.score-stat .stat-val {
  font-size: 1.15rem;
  font-weight: 800;
}

.card-action {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8rem;
  color: var(--primary-color);
  font-weight: 600;
  margin-top: auto;
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
}

.go-practice-btn {
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%) !important;
  border: none !important;
  font-weight: 600;
  border-radius: 8px;
  margin-top: 10px;
}

/* Drawer & Collapsible styles */
:deep(.history-drawer) {
  background-color: #111827 !important;
  border-left: 1px solid rgba(255, 255, 255, 0.08);
}

:deep(.history-drawer .el-drawer__title) {
  color: var(--text-primary) !important;
  font-weight: 700;
}

:deep(.history-drawer .el-drawer__body) {
  padding: 0 !important;
}

.drawer-content {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.drawer-header-meta {
  padding: 20px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(17, 24, 39, 0.4);
}

.drawer-header-meta h3 {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.meta-row {
  display: flex;
  gap: 8px;
}

.chat-history-drawer {
  flex-grow: 1;
  padding: 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.turn-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.message-row-drawer {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  width: 100%;
}

.user-row {
  justify-content: flex-end;
}

.ai-row {
  justify-content: flex-start;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 700;
  flex-shrink: 0;
  margin-top: 2px;
}

.ai-avatar {
  background: var(--primary-color);
  color: #fff;
}

.user-avatar {
  background: var(--accent-color);
  color: #fff;
}

.bubble-wrapper-drawer {
  max-width: 78%;
  display: flex;
  flex-direction: column;
  cursor: pointer;
}

.bubble {
  padding: 10px 14px;
  border-radius: 12px;
  position: relative;
}

.ai-bubble {
  background: rgba(31, 41, 55, 0.4) !important;
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-top-left-radius: 2px;
}

.user-bubble {
  background: rgba(99, 102, 241, 0.1) !important;
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-top-right-radius: 2px;
}

.active-user-bubble {
  border-color: var(--primary-color) !important;
  background: rgba(99, 102, 241, 0.15) !important;
}

.message-text {
  font-size: 0.9rem;
  line-height: 1.5;
  color: var(--text-primary);
  word-wrap: break-word;
  white-space: pre-wrap;
}

.bubble-correction-snippet {
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed rgba(239, 68, 68, 0.2);
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  color: #34d399; /* 浅绿色 */
  font-weight: 500;
}

.warning-icon {
  color: #f87171;
  font-size: 0.9rem;
}

.bubble-actions {
  margin-top: 6px;
  display: flex;
  justify-content: flex-end;
}

.bubble-actions-left {
  margin-top: 4px;
  padding: 0 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.audio-play-btn {
  color: #818cf8 !important;
  font-size: 0.75rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
}

.details-toggle-btn {
  font-size: 0.72rem;
  color: var(--text-muted);
  font-weight: 500;
  cursor: pointer;
}

.details-toggle-btn:hover {
  color: var(--primary-color);
}

.bubble-score {
  position: absolute;
  bottom: -8px;
  right: 10px;
}

.score-tag {
  background-color: var(--accent-color) !important;
  border: none !important;
  font-weight: 700;
  font-size: 0.7rem;
}

/* Inline evaluation panel inside drawer */
.inline-eval-panel {
  margin-left: 42px;
  margin-right: 42px;
  background: rgba(0, 0, 0, 0.2) !important;
  border: 1px dashed rgba(255, 255, 255, 0.06);
  padding: 16px;
  border-radius: 8px;
}

.inline-section-title {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-secondary);
  border-left: 2.5px solid var(--primary-color);
  padding-left: 6px;
  margin-bottom: 8px;
}

.radar-container {
  display: flex;
  justify-content: center;
  background: rgba(0, 0, 0, 0.15);
  border-radius: 6px;
}

.grammar-ok {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  color: var(--accent-color);
}

.ok-icon {
  font-size: 1.1rem;
}

.grammar-needs-fix {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.fix-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.badge-tag {
  align-self: flex-start;
  font-size: 0.65rem;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 3px;
}

.tag-red {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}

.tag-green {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
}

.text-block {
  font-size: 0.8rem;
  line-height: 1.35;
  padding: 6px 8px;
  border-radius: 4px;
}

.red-text {
  background: rgba(239, 68, 68, 0.03);
  color: #fca5a5;
  text-decoration: line-through rgba(239, 68, 68, 0.25);
}

.green-text {
  background: rgba(16, 185, 129, 0.03);
  color: #a7f3d0;
}

.explanation-box {
  border-top: 1px dotted rgba(255, 255, 255, 0.05);
  padding-top: 8px;
}

.exp-title {
  font-size: 0.7rem;
  color: var(--text-muted);
  font-weight: 600;
  display: block;
}

.exp-content {
  font-size: 0.78rem;
  color: var(--text-secondary);
  line-height: 1.4;
  margin-top: 2px;
}
</style>

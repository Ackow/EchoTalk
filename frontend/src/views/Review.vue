<template>
  <!-- 复习计划：基于已有对话记录的间隔重复队列 + 沉浸抽认卡复习 -->
  <section class="review-page">
    <!-- 游客态：复习队列与历史对话均按账号隔离 -->
    <div v-if="!signedIn" class="review-guest">
      <span class="guest-icon"><AppIcon name="calendar-check" :size="24" /></span>
      <h2>登录后开启专属复习计划</h2>
      <p>系统会自动从你的历史对话记录中提取语法纠错、发音低分词与重点表达，并按遗忘曲线安排每日复习。</p>
      <router-link class="primary-button slim" :to="{ name: 'login', query: { redirect: $route.fullPath } }"><AppIcon name="user" :size="15" />去登录</router-link>
    </div>

    <template v-else>
      <!-- 顶部概览与主行动按钮 -->
      <div class="review-overview">
        <div class="ov-item">
          <span class="ov-icon purple"><AppIcon name="calendar-check" :size="17" /></span>
          <div><small>今日待复习</small><b>{{ dueItems.length }}<em>项</em></b></div>
        </div>
        <div class="ov-item">
          <span class="ov-icon amber"><AppIcon name="sparkles" :size="17" /></span>
          <div><small>连续坚持</small><b>{{ streakDays }}<em>天</em></b></div>
        </div>
        <div class="ov-item">
          <span class="ov-icon mint"><AppIcon name="check" :size="17" /></span>
          <div><small>已掌握</small><b>{{ masteredCount }}<em>项</em></b></div>
        </div>
        <div class="ov-rate">
          <div class="ov-rate-head"><small>整体掌握率</small><b>{{ masteryRate }}%</b></div>
          <div class="ov-bar" role="img" :aria-label="`整体掌握率 ${masteryRate}%`"><i :style="{ width: `${masteryRate}%` }"></i></div>
        </div>
        <button
          class="primary-button slim start-review-btn"
          type="button"
          :disabled="loading || !activeItems.length"
          @click="startSession()"
        >
          <AppIcon name="sparkles" :size="15" />
          {{ dueItems.length ? `开始今日复习 (${dueItems.length})` : activeItems.length ? '自由抽查全部' : '暂无待复习项' }}
        </button>
      </div>

      <!-- 工具行：状态 Tab + 类型筛选 + 搜索 -->
      <div class="review-toolbar">
        <AppTabs v-model="statusTab" :options="statusTabs" aria-label="复习状态筛选" />
        <div class="toolbar-right">
          <AppSelect v-model="kindFilter" :options="KIND_OPTIONS" label="类型" aria-label="按类型筛选" />
          <label class="search-box">
            <AppIcon name="search" :size="14" />
            <input v-model="keyword" type="search" placeholder="搜索表达、语境或场景" aria-label="搜索复习项" />
            <button v-if="keyword" class="search-clear" type="button" aria-label="清空搜索" @click="keyword = ''">
              <AppIcon name="x" :size="12" />
            </button>
          </label>
          <button class="ghost-button slim add-card-btn" type="button" @click="openCreateModal">
            <AppIcon name="plus" :size="14" />手动添加
          </button>
        </div>
      </div>

      <!-- 加载骨架 -->
      <div v-if="loading" class="review-list" aria-busy="true" aria-label="正在加载复习计划">
        <div v-for="n in 4" :key="n" class="review-card skeleton">
          <div class="sk-group">
            <span class="sk-line w30"></span>
            <span class="sk-line w70"></span>
            <span class="sk-line w50"></span>
          </div>
        </div>
      </div>

      <!-- 加载失败 -->
      <div v-else-if="error" class="review-empty">
        <span class="empty-icon"><AppIcon name="x" :size="22" /></span>
        <h3>复习计划加载失败</h3>
        <p>{{ error }}</p>
        <button class="ghost-button" type="button" @click="load()"><AppIcon name="rotate" :size="14" />重试</button>
      </div>

      <!-- 复习队列列表 -->
      <div v-else-if="pagedItems.length" class="review-list">
        <article v-for="item in pagedItems" :key="item.id" class="review-card" :class="{ mastered: item.status === 'mastered' }">
          <div class="card-main">
            <div class="card-badges">
              <span class="kind-chip" :class="item.kind">{{ kindLabel(item.kind) }}</span>
              <span class="due-chip" :class="dueMeta(item).tone">{{ dueMeta(item).text }}</span>
              <span v-if="item.scene_name" class="scene-chip">
                <AppIcon name="messages" :size="12" />{{ item.scene_name }}
              </span>
              <button
                v-if="item.source_session_id"
                class="source-link"
                type="button"
                @click="openSourceSession(item)"
              >
                回看原对话<AppIcon name="arrow-up-right" :size="12" />
              </button>
            </div>
            <p v-if="item.context_text" class="card-context">{{ item.context_text }}</p>
            <h3 class="card-prompt">{{ item.prompt }}</h3>
            <p class="card-answer">
              <span>{{ item.answer }}</span>
              <button
                class="speak-btn"
                type="button"
                :class="{ speaking: speakingId === item.id }"
                title="朗读英文表达"
                aria-label="朗读英文表达"
                @click="speakText(item.answer, item.id)"
              >
                <AppIcon name="volume" :size="14" />
              </button>
            </p>
            <p v-if="item.note" class="card-note">{{ item.note }}</p>
          </div>

          <div class="card-side">
            <div class="mastery-box">
              <div class="mastery-head">
                <span>熟练度</span>
                <b>Lv.{{ item.mastery }} / 5</b>
              </div>
              <div class="mastery-dots" :aria-label="`熟练度 ${item.mastery} / 5`">
                <i v-for="n in 5" :key="n" :class="{ on: n <= item.mastery }"></i>
              </div>
            </div>

            <div class="card-actions">
              <button class="action-btn primary" type="button" @click="startSession([item])">
                <AppIcon name="sparkles" :size="13" />抽查
              </button>
              <button
                class="action-btn"
                type="button"
                :title="item.status === 'mastered' ? '放回复习队列' : '标为已掌握'"
                @click="toggleMastered(item)"
              >
                <AppIcon :name="item.status === 'mastered' ? 'rotate' : 'check'" :size="13" />
              </button>
              <button class="action-btn danger" type="button" title="删除" @click="deleteTarget = item">
                <AppIcon name="trash" :size="13" />
              </button>
            </div>
          </div>
        </article>
      </div>

      <div v-else class="review-empty">
        <span class="empty-icon"><AppIcon name="calendar-check" :size="22" /></span>
        <h3>{{ emptyCopy.title }}</h3>
        <p>{{ emptyCopy.desc }}</p>
        <div class="empty-actions">
          <button v-if="keyword || kindFilter !== 'all'" class="ghost-button" type="button" @click="keyword = ''; kindFilter = 'all'">
            清空筛选
          </button>
          <router-link v-else-if="statusTab === 'active' || statusTab === 'due'" class="primary-button slim" :to="{ name: 'practice' }">
            <AppIcon name="messages" :size="14" />去语音对话
          </router-link>
        </div>
      </div>

      <!-- 分页栏：常驻最底部 -->
      <nav v-if="!loading && filteredItems.length" class="pagination" aria-label="复习队列分页">
        <span class="page-info">共 {{ filteredItems.length }} 项 · 第 {{ page }} / {{ totalPages }} 页</span>
        <button class="page-btn" type="button" :disabled="page === 1" @click="page -= 1">
          <AppIcon name="chevron-left" :size="14" />上一页
        </button>
        <button
          v-for="p in totalPages"
          :key="p"
          class="page-btn page-num"
          :class="{ active: p === page }"
          type="button"
          :aria-current="p === page ? 'page' : undefined"
          @click="page = p"
        >{{ p }}</button>
        <button class="page-btn" type="button" :disabled="page === totalPages" @click="page += 1">
          下一页<AppIcon name="arrow-right" :size="14" />
        </button>
      </nav>
    </template>

    <!-- 沉浸复习弹窗（抽认卡） -->
    <transition name="fade">
      <div v-if="sessionOpen" class="modal-backdrop" @click.self="closeSession()">
        <div class="flashcard-modal" role="dialog" aria-modal="true" aria-label="沉浸复习">
          <header class="fc-head">
            <div class="fc-progress-copy">
              <b>{{ sessionDone ? '本轮复习完成' : '沉浸抽认复习' }}</b>
              <span v-if="!sessionDone">第 {{ Math.min(sessionIndex + 1, sessionQueue.length) }} / {{ sessionQueue.length }} 题</span>
            </div>
            <button class="close-btn" type="button" aria-label="关闭复习" @click="closeSession()">
              <AppIcon name="x" :size="16" />
            </button>
          </header>

          <div class="fc-bar">
            <i :style="{ width: `${sessionDone ? 100 : Math.round((sessionIndex / Math.max(1, sessionQueue.length)) * 100)}%` }"></i>
          </div>

          <div v-if="sessionDone" class="fc-finish">
            <span class="finish-badge"><AppIcon name="check" :size="26" /></span>
            <h3>太棒了，本轮已复习 {{ sessionStats.reviewed }} 项！</h3>
            <p>其中 {{ sessionStats.remembered }} 项掌握良好，系统已按遗忘曲线安排下次复习时间。</p>
            <div class="finish-actions">
              <button class="primary-button slim" type="button" @click="closeSession()">返回复习计划</button>
            </div>
          </div>

          <div v-else-if="currentCard" class="fc-body">
            <div class="fc-meta">
              <span class="kind-chip" :class="currentCard.kind">{{ kindLabel(currentCard.kind) }}</span>
              <span v-if="currentCard.scene_name" class="scene-chip">
                <AppIcon name="messages" :size="12" />{{ currentCard.scene_name }}
              </span>
            </div>

            <div class="fc-prompt-box">
              <p v-if="currentCard.context_text" class="fc-context">{{ currentCard.context_text }}</p>
              <small>回想或尝试开口表达</small>
              <h2>{{ currentCard.prompt }}</h2>
            </div>

            <div v-if="!revealed" class="fc-reveal-area">
              <button class="primary-button slim" type="button" @click="revealed = true">
                显示标准表达与解析（空格）
              </button>
            </div>

            <div v-else class="fc-answer-box">
              <div class="fc-answer-head">
                <small>地道表达 / 参考答案</small>
                <button
                  class="speak-pill"
                  type="button"
                  :class="{ speaking: speakingId === currentCard.id }"
                  @click="speakText(currentCard.answer, currentCard.id)"
                >
                  <AppIcon name="volume" :size="14" />朗读示范
                </button>
              </div>
              <p class="fc-answer-text">{{ currentCard.answer }}</p>
              <p v-if="currentCard.phonetic" class="fc-phonetic">{{ currentCard.phonetic }}</p>
              <p v-if="currentCard.note" class="fc-note">{{ currentCard.note }}</p>

              <div class="fc-ratings" role="group" aria-label="记忆反馈">
                <button class="rate-btn again" type="button" :disabled="submitting" @click="rateCard('again')">
                  <b>没记住</b><span>10 分钟后</span>
                </button>
                <button class="rate-btn hard" type="button" :disabled="submitting" @click="rateCard('hard')">
                  <b>有点模糊</b><span>1 天后</span>
                </button>
                <button class="rate-btn good" type="button" :disabled="submitting" @click="rateCard('good')">
                  <b>记住了</b><span>3 天后</span>
                </button>
                <button class="rate-btn easy" type="button" :disabled="submitting" @click="rateCard('easy')">
                  <b>很熟练</b><span>7 天+</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 轻提示 -->
    <transition name="toast">
      <div v-if="toast" class="toast" role="status">{{ toast }}</div>
    </transition>

    <!-- 手动添加复习卡弹窗 -->
    <transition name="modal-fade">
      <div v-if="createModalOpen" class="flashcard-backdrop" @click.self="createModalOpen = false">
        <div class="editor-modal" role="dialog" aria-modal="true" aria-label="手动添加复习卡">
          <div class="fc-top">
            <span class="fc-progress">新建复习卡</span>
            <button class="fc-close" type="button" aria-label="关闭" @click="createModalOpen = false">
              <AppIcon name="x" :size="16" />
            </button>
          </div>
          <form class="editor-form" @submit.prevent="submitCreate">
            <label class="editor-field">
              <span>类型</span>
              <select v-model="createForm.kind">
                <option value="expression">表达与生词</option>
                <option value="grammar">语法改进</option>
                <option value="pronunciation">发音纠偏</option>
                <option value="listening">听力错题</option>
                <option value="debate">多角色表达</option>
              </select>
            </label>
            <label class="editor-field">
              <span>提示 / 问题（正面）</span>
              <input v-model="createForm.prompt" type="text" required maxlength="200" placeholder="例如：如何礼貌地请服务员推荐饮品？" />
            </label>
            <label class="editor-field">
              <span>地道表达 / 答案（背面）</span>
              <input v-model="createForm.answer" type="text" required maxlength="240" placeholder="例如：Could you recommend something light?" />
            </label>
            <label class="editor-field">
              <span>补充笔记（可选）</span>
              <textarea v-model="createForm.note" rows="2" maxlength="300" placeholder="语法点、连读或使用场景说明" />
            </label>
            <div class="editor-actions">
              <button class="ghost-button slim" type="button" @click="createModalOpen = false">取消</button>
              <button class="primary-button slim" type="submit" :disabled="creating">
                {{ creating ? '保存中...' : '添加到复习计划' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </transition>

    <!-- 删除确认弹窗 -->
    <transition name="modal-fade">
      <div v-if="deleteTarget" class="flashcard-backdrop" @click.self="deleteTarget = null">
        <div class="editor-modal confirm-modal" role="dialog" aria-modal="true" aria-label="确认删除复习卡">
          <h3>确认删除这张复习卡？</h3>
          <p class="confirm-desc">删除后将从复习队列中永久移除「{{ deleteTarget.prompt }}」。</p>
          <div class="editor-actions">
            <button class="ghost-button slim" type="button" @click="deleteTarget = null">取消</button>
            <button class="danger-button slim" type="button" :disabled="deleting" @click="confirmDelete">
              {{ deleting ? '删除中...' : '确认删除' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import AppSelect from '../components/AppSelect.vue'
import AppTabs from '../components/AppTabs.vue'
import { session } from '../auth/session'
import { usePageLoading } from '../app/loading'
import { syncGlobalXpProfile } from '../app/xp'
import { synthesizeSpeech } from '../api/avatar'
import {
  createReviewItem,
  deleteReviewItem,
  listReviewItems,
  submitReviewResult,
  updateReviewItem,
} from '../api/review'

const router = useRouter()
const signedIn = computed(() => Boolean(session.token))
const finishLoading = usePageLoading()

const KIND_META = {
  expression: '表达与生词',
  pronunciation: '发音纠偏',
  grammar: '语法改进',
  listening: '听力错题',
  debate: '多角色表达',
}
const KIND_OPTIONS = [
  { value: 'all', label: '全部类型' },
  { value: 'expression', label: '表达与生词' },
  { value: 'pronunciation', label: '发音纠偏' },
  { value: 'grammar', label: '语法改进' },
  { value: 'listening', label: '听力错题' },
  { value: 'debate', label: '多角色表达' },
]

const items = ref([])
const streakDays = ref(0)
const loading = ref(false)
const submitting = ref(false)
const error = ref('')
const statusTab = ref('due')
const kindFilter = ref('all')
const keyword = ref('')

const isDue = (item) => item.status !== 'mastered' && new Date(item.due_at).getTime() <= Date.now()
const activeItems = computed(() => items.value.filter((it) => it.status !== 'mastered'))
const dueItems = computed(() => activeItems.value.filter(isDue))
const masteredCount = computed(() => items.value.filter((it) => it.status === 'mastered').length)
const masteryRate = computed(() => {
  if (!items.value.length) return 0
  return Math.round((masteredCount.value / items.value.length) * 100)
})

const statusTabs = computed(() => [
  { value: 'due', label: '今日到期', count: dueItems.value.length },
  { value: 'active', label: '全部待学', count: activeItems.value.length },
  { value: 'mastered', label: '已掌握', count: masteredCount.value },
])

const filteredItems = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  const base = statusTab.value === 'due'
    ? dueItems.value
    : statusTab.value === 'active'
      ? activeItems.value
      : items.value.filter((it) => it.status === 'mastered')

  return base
    .filter((it) => kindFilter.value === 'all' || it.kind === kindFilter.value)
    .filter((it) => {
      if (!kw) return true
      return [it.prompt, it.answer, it.note, it.context_text, it.scene_name].some((f) => String(f || '').toLowerCase().includes(kw))
    })
    .slice()
    .sort((a, b) => new Date(a.due_at).getTime() - new Date(b.due_at).getTime())
})

const PAGE_SIZE = 6
const page = ref(1)
const totalPages = computed(() => Math.max(1, Math.ceil(filteredItems.value.length / PAGE_SIZE)))
const pagedItems = computed(() => filteredItems.value.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE))
watch([statusTab, kindFilter, keyword], () => { page.value = 1 })
watch(totalPages, (total) => { if (page.value > total) page.value = total })

const kindLabel = (kind) => KIND_META[kind] || '表达与生词'

function dueMeta(item) {
  if (item.status === 'mastered') return { text: '已掌握', tone: 'mint' }
  const diff = new Date(item.due_at).getTime() - Date.now()
  if (diff <= -3600 * 1000) return { text: '已逾期', tone: 'danger' }
  if (diff <= 0) return { text: '今日到期', tone: 'brand' }
  const days = Math.ceil(diff / (24 * 3600 * 1000))
  return { text: `${days} 天后复习`, tone: 'muted' }
}

const emptyCopy = computed(() => {
  if (keyword.value || kindFilter.value !== 'all') {
    return { title: '没有匹配的复习项', desc: '换个关键词或类型试试，也可以清空筛选查看当前队列。' }
  }
  if (statusTab.value === 'due') {
    return { title: '今日待复习已清零', desc: '当前没有到期项，可切换查看「全部待学」或「已掌握」。' }
  }
  if (statusTab.value === 'mastered') {
    return { title: '还没有已掌握的条目', desc: '完成抽认复习或将熟悉的表达标为已掌握后，会归档到这里。' }
  }
  return { title: '复习队列还是空的', desc: '去「语音对话」练习后，系统会自动从你的对话记录提取重点加入这里。' }
})

async function load() {
  if (!signedIn.value) {
    finishLoading()
    return
  }
  loading.value = true
  error.value = ''
  try {
    const { data } = await listReviewItems(true)
    items.value = data.items || []
    streakDays.value = data.stats?.streak_days || 0
  } catch (err) {
    error.value = err?.response?.data?.detail || '请检查网络或重新登录后重试。'
  } finally {
    loading.value = false
    finishLoading()
  }
}

function openSourceSession(item) {
  const sessionId = typeof item === 'string' ? item : item?.source_session_id
  if (!sessionId) return
  if (typeof item === 'object' && (item?.source_type === 'debate' || item?.kind === 'debate')) {
    router.push({ name: 'debate', query: { session: sessionId } })
    return
  }
  router.push({ name: 'practice', query: { session: sessionId } })
}

// ---- 语音朗读（复用后端 TTS 接口，失败时回落浏览器 SpeechSynthesis） ----
const speakingId = ref(null)
let currentAudio = null
const audioCache = new Map()

function stopSpeak() {
  if (currentAudio) {
    currentAudio.pause()
    currentAudio.onended = currentAudio.onerror = null
    currentAudio = null
  }
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    window.speechSynthesis.cancel()
  }
  speakingId.value = null
}

async function speakText(text, id) {
  if (!text) return
  if (speakingId.value === id) {
    stopSpeak()
    return
  }
  stopSpeak()
  speakingId.value = id
  const cacheKey = `${id}:${text}`
  try {
    let url = audioCache.get(cacheKey)
    if (!url) {
      const blob = await synthesizeSpeech(text, undefined, 0.95)
      if (speakingId.value !== id) return
      url = URL.createObjectURL(blob)
      audioCache.set(cacheKey, url)
    }
    const audio = new Audio(url)
    currentAudio = audio
    audio.onended = () => {
      if (speakingId.value === id) speakingId.value = null
      if (currentAudio === audio) currentAudio = null
    }
    audio.onerror = () => {
      if (speakingId.value === id) speakingId.value = null
      if (currentAudio === audio) currentAudio = null
      notify('音频播放失败，请重试')
    }
    await audio.play()
  } catch {
    if (speakingId.value !== id) return
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      const utter = new SpeechSynthesisUtterance(text)
      utter.lang = 'en-US'
      utter.rate = 0.94
      utter.onend = utter.onerror = () => {
        if (speakingId.value === id) speakingId.value = null
      }
      window.speechSynthesis.speak(utter)
    } else {
      speakingId.value = null
      notify('语音合成暂不可用，请稍后重试')
    }
  }
}

// ---- 沉浸抽认卡复习 ----
const sessionOpen = ref(false)
const sessionQueue = ref([])
const sessionIndex = ref(0)
const revealed = ref(false)
const sessionDone = ref(false)
const sessionStats = ref({ reviewed: 0, remembered: 0 })
const currentCard = computed(() => sessionQueue.value[sessionIndex.value] || null)

function startSession(customQueue) {
  const queue = customQueue?.length
    ? customQueue
    : (dueItems.value.length ? dueItems.value : activeItems.value)
  if (!queue.length) return
  sessionQueue.value = queue.slice()
  sessionIndex.value = 0
  revealed.value = false
  sessionDone.value = false
  sessionStats.value = { reviewed: 0, remembered: 0 }
  sessionOpen.value = true
}

function closeSession() {
  stopSpeak()
  sessionOpen.value = false
}

async function rateCard(rating) {
  const card = currentCard.value
  if (!card || submitting.value) return
  submitting.value = true
  try {
    const { data } = await submitReviewResult(card.id, rating)
    void syncGlobalXpProfile()
    if (data?.item) {
      items.value = items.value.map((it) => (it.id === card.id ? data.item : it))
    }
    if (data?.stats) {
      streakDays.value = data.stats.streak_days || 0
    }
    sessionStats.value.reviewed += 1
    if (rating === 'good' || rating === 'easy') sessionStats.value.remembered += 1

    if (rating === 'again') {
      sessionQueue.value.push(data?.item || card)
    }
    if (sessionIndex.value + 1 >= sessionQueue.value.length) {
      sessionDone.value = true
    } else {
      sessionIndex.value += 1
      revealed.value = false
    }
    stopSpeak()
  } catch (err) {
    notify(err?.response?.data?.detail || '提交复习结果失败')
  } finally {
    submitting.value = false
  }
}

function onKeydown(e) {
  if (!sessionOpen.value || sessionDone.value) return
  if (e.code === 'Space' && !revealed.value) {
    e.preventDefault()
    revealed.value = true
  } else if (revealed.value) {
    const map = { Digit1: 'again', Digit2: 'hard', Digit3: 'good', Digit4: 'easy' }
    if (map[e.code]) {
      e.preventDefault()
      void rateCard(map[e.code])
    }
  }
}

// ---- 队列 CRUD ----
async function toggleMastered(item) {
  const nextStatus = item.status === 'mastered' ? 'active' : 'mastered'
  try {
    const { data } = await updateReviewItem(item.id, {
      status: nextStatus,
      mastery: nextStatus === 'mastered' ? 5 : Math.min(item.mastery, 3),
    })
    if (data?.item) {
      items.value = items.value.map((it) => (it.id === item.id ? data.item : it))
    }
    notify(nextStatus === 'mastered' ? '已标为掌握' : '已放回复习队列')
  } catch (err) {
    notify(err?.response?.data?.detail || '状态更新失败')
  }
}

const deleteTarget = ref(null)
const deleting = ref(false)
const createModalOpen = ref(false)
const creating = ref(false)
const createForm = ref({ kind: 'expression', prompt: '', answer: '', note: '' })

function openCreateModal() {
  createForm.value = { kind: 'expression', prompt: '', answer: '', note: '' }
  createModalOpen.value = true
}

async function submitCreate() {
  const prompt = createForm.value.prompt.trim()
  const answer = createForm.value.answer.trim()
  if (!prompt || !answer || creating.value) return
  creating.value = true
  try {
    const { data } = await createReviewItem({
      kind: createForm.value.kind,
      prompt,
      answer,
      note: createForm.value.note.trim() || undefined,
    })
    if (data?.id) items.value.unshift(data)
    else await load()
    createModalOpen.value = false
    notify('已添加到复习计划')
  } catch (err) {
    notify(err?.response?.data?.detail || '添加失败，请稍后重试')
  } finally {
    creating.value = false
  }
}

async function confirmDelete() {
  const item = deleteTarget.value
  if (!item || deleting.value) return
  deleting.value = true
  try {
    await deleteReviewItem(item.id)
    items.value = items.value.filter((it) => it.id !== item.id)
    deleteTarget.value = null
    notify('已删除该复习项')
  } catch (err) {
    notify(err?.response?.data?.detail || '删除失败')
  } finally {
    deleting.value = false
  }
}

const toast = ref('')
let toastTimer = null
function notify(msg) {
  clearTimeout(toastTimer)
  toast.value = msg
  toastTimer = setTimeout(() => { toast.value = '' }, 2400)
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  void load()
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  clearTimeout(toastTimer)
  stopSpeak()
  for (const url of audioCache.values()) URL.revokeObjectURL(url)
  audioCache.clear()
})
</script>

<style scoped>
.review-page { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow-y: auto; padding: 22px 28px 32px; }

/* 游客态 */
.review-guest { display: grid; flex: 1; place-content: center; justify-items: center; padding: 40px 20px; text-align: center; }
.guest-icon { display: grid; width: 56px; height: 56px; place-items: center; border-radius: 16px; background: #efeafe; color: #7156cc; }
.review-guest h2 { margin: 16px 0 8px; font-size: 18px; }
.review-guest p { margin: 0 0 18px; max-width: 420px; color: var(--muted); font-size: 13.5px; line-height: 1.65; }

/* 概览条 */
.review-overview { display: flex; flex: 0 0 auto; flex-wrap: wrap; align-items: center; gap: 14px; margin-bottom: 18px; padding: 14px 18px; border: 1.5px solid #ebe7f5; border-bottom: 4px solid #e5def1; border-radius: 16px; background: #fff; }
.ov-item { display: flex; align-items: center; gap: 11px; padding-right: 16px; border-right: 1px solid #f0edf7; }
.ov-item small { display: block; color: var(--muted); font-size: 12px; }
.ov-item b { display: block; margin-top: 2px; font-size: 19px; font-weight: 700; color: var(--ink); line-height: 1.1; }
.ov-item em { margin-left: 3px; font-style: normal; font-size: 12px; font-weight: 500; color: var(--muted); }
.ov-icon { display: grid; width: 38px; height: 38px; place-items: center; border-radius: 11px; }
.ov-icon.purple { background: #efeafe; color: #7156cc; }
.ov-icon.amber { background: #fef4e3; color: #c77b20; }
.ov-icon.mint { background: #e6f6ef; color: #268259; }
.ov-rate { flex: 1; min-width: 150px; }
.ov-rate-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px; }
.ov-rate-head small { color: var(--muted); font-size: 12px; }
.ov-rate-head b { font-size: 13.5px; color: var(--brand); }
.ov-bar { height: 7px; overflow: hidden; border-radius: 999px; background: #f0edf7; }
.ov-bar i { display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg, #8b73dd, #6265e8); transition: width .25s ease; }
.start-review-btn { margin-left: auto; }

/* 工具栏 */
.review-toolbar { display: flex; flex: 0 0 auto; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.toolbar-right { display: flex; flex-wrap: wrap; align-items: center; gap: 9px; }
.search-box { position: relative; display: inline-flex; align-items: center; gap: 7px; width: 220px; height: 34px; padding: 0 10px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--faint); transition: border-color .15s, box-shadow .15s; }
.search-box:focus-within { border-color: var(--brand); box-shadow: 0 0 0 3px rgba(98, 101, 232, .12); }
.search-box input { flex: 1; min-width: 0; border: 0; outline: none; background: transparent; color: var(--ink); font-size: 13.5px; }
.search-box input::placeholder { color: var(--faint); }
.search-box input::-webkit-search-cancel-button { -webkit-appearance: none; appearance: none; display: none; }
.search-clear { display: grid; place-items: center; width: 18px; height: 18px; border: 0; border-radius: 50%; background: #eef0f5; color: var(--muted); }
.ghost-button {
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  height: 36px; padding: 0 14px;
  border: 1.5px solid #e1daf3; border-bottom: 3px solid #d4cbe9; border-radius: 12px;
  background: #fff; color: #5b527c; font-size: 13px; font-weight: 700; cursor: pointer;
  transition: border-color .15s, color .15s, background .15s, transform .12s;
}
.ghost-button.slim { height: 34px; padding: 0 13px; font-size: 12.5px; }
.ghost-button:hover:not(:disabled) { border-color: #c5b8eb; color: #43376c; background: #f8f5ff; }
.ghost-button:active:not(:disabled) { transform: translateY(1px); border-bottom-width: 2px; }
.ghost-button:disabled { opacity: .55; cursor: not-allowed; }
.primary-button.slim {
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  width: auto; height: 36px; margin-top: 0; padding: 0 16px;
  border: 1.5px solid #7d64d1; border-bottom: 3.5px solid #654eb6; border-radius: 12px;
  background: #8b73dd; color: #fff; font-size: 13px; font-weight: 750;
  text-decoration: none; cursor: pointer;
  transition: background .15s, transform .12s;
}
.primary-button.slim:hover:not(:disabled) { background: #7d64d1; }
.primary-button.slim:active:not(:disabled) { transform: translateY(1px); border-bottom-width: 2px; }
.primary-button.slim:disabled { opacity: .55; cursor: not-allowed; }

/* 队列列表 */
.review-list { display: flex; flex: 1 0 auto; flex-direction: column; gap: 11px; }
.review-card { display: flex; align-items: stretch; justify-content: space-between; gap: 18px; padding: 15px 18px; border: 1.5px solid #ebe7f5; border-bottom: 4px solid #e5def1; border-radius: 15px; background: #fff; transition: border-color .15s; }
.review-card:hover { border-color: #d4cbf0; }
.review-card.mastered { opacity: .88; }
.card-main { flex: 1; min-width: 0; }
.card-badges { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-bottom: 8px; }
.kind-chip, .due-chip, .scene-chip { display: inline-flex; align-items: center; gap: 4px; height: 22px; padding: 0 9px; border-radius: 6px; font-size: 11.5px; font-weight: 600; }
.kind-chip.expression { background: #efeafe; color: #694fc1; }
.kind-chip.pronunciation { background: #e6f6ef; color: #257a55; }
.kind-chip.grammar { background: #e6eefc; color: #3460a1; }
.kind-chip.listening { background: #fef4e3; color: #b56d1c; }
.due-chip.danger { background: #fdecec; color: #c03b3b; }
.due-chip.brand { background: var(--brand-soft); color: var(--brand-deep, var(--brand)); }
.due-chip.mint { background: #e3f2ea; color: #2f7a52; }
.due-chip.muted { background: #f2f3f8; color: var(--muted); font-weight: 500; }
.scene-chip { background: #f5f4fa; color: var(--ink-soft); font-weight: 500; }
.source-link { display: inline-flex; align-items: center; gap: 3px; height: 22px; padding: 0 8px; border: 0; border-radius: 6px; background: transparent; color: var(--brand); font-size: 11.5px; font-weight: 600; }
.source-link:hover { background: var(--brand-soft); }
.card-context { margin: 0 0 4px; color: var(--muted); font-size: 12.5px; line-height: 1.45; }
.card-prompt { margin: 0 0 6px; font-size: 15px; font-weight: 600; color: var(--ink); line-height: 1.45; }
.card-answer { display: flex; align-items: center; gap: 8px; margin: 0; font-size: 14px; font-weight: 500; color: #4a4563; line-height: 1.5; }
.speak-btn { display: grid; flex: 0 0 auto; width: 26px; height: 26px; place-items: center; border: 1px solid #e6e2f3; border-radius: 7px; background: #faf9fe; color: #7156cc; transition: background .15s, color .15s; }
.speak-btn:hover, .speak-btn.speaking { background: #efeafe; border-color: #cabdf2; }
.card-note { margin: 6px 0 0; color: var(--muted); font-size: 12.5px; line-height: 1.55; white-space: pre-line; }

.card-side { display: flex; flex: 0 0 auto; flex-direction: column; align-items: flex-end; justify-content: space-between; gap: 12px; min-width: 156px; }
.mastery-box { width: 100%; }
.mastery-head { display: flex; justify-content: space-between; font-size: 11.5px; color: var(--muted); margin-bottom: 5px; }
.mastery-head b { color: var(--ink-soft); font-weight: 600; }
.mastery-dots { display: grid; grid-template-columns: repeat(5, 1fr); gap: 4px; }
.mastery-dots i { display: block; height: 5px; border-radius: 999px; background: #ece9f6; }
.mastery-dots i.on { background: #7f65d4; }
.card-actions { display: flex; align-items: center; gap: 6px; }
.action-btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 4px;
  height: 32px; min-width: 32px; padding: 0 10px;
  border: 1.5px solid #e1daf3; border-bottom: 3px solid #d4cbe9; border-radius: 10px;
  background: #fff; color: #5b527c; font-size: 12px; font-weight: 600; cursor: pointer;
  transition: border-color .15s, color .15s, background .15s, transform .12s;
}
.action-btn:hover { border-color: #c5b8eb; color: #43376c; background: #f8f5ff; }
.action-btn:active { transform: translateY(1px); border-bottom-width: 2px; }
.action-btn.primary { border-color: #d6cbf2; border-bottom-color: #c2b2ea; background: #f4f0ff; color: #694fc1; font-weight: 700; }
.action-btn.primary:hover { background: #ebe4ff; }
.action-btn.danger:hover { border-color: #f3c6c6; border-bottom-color: #e5a8a8; background: #fbf1f2; color: var(--danger); }

/* 骨架屏 */
.review-card.skeleton { min-height: 92px; }
.sk-group { display: flex; flex: 1; flex-direction: column; gap: 10px; }
.sk-line { display: block; height: 12px; border-radius: 5px; background: linear-gradient(90deg, #eef0f5 25%, #f6f7fa 45%, #eef0f5 65%); background-size: 200% 100%; animation: shimmer 1.3s infinite; }
.sk-line.w30 { width: 30%; }
.sk-line.w50 { width: 50%; }
.sk-line.w70 { width: 70%; height: 14px; }
@keyframes shimmer { from { background-position: 200% 0; } to { background-position: -200% 0; } }

/* 空状态 */
.review-empty { display: grid; flex: 1 0 auto; place-content: center; justify-items: center; padding: 48px 20px; border: 2px dashed #d9d0ef; border-radius: 18px; background: #fff; text-align: center; }
.empty-icon { display: grid; width: 52px; height: 52px; place-items: center; border-radius: 16px; background: #f0eaff; color: #7c62d2; }
.review-empty h3 { margin: 14px 0 6px; font-size: 16px; font-weight: 600; }
.review-empty p { margin: 0 0 16px; max-width: 400px; color: var(--muted); font-size: 13.5px; line-height: 1.65; }
.empty-actions { display: flex; gap: 10px; }

/* 分页栏：常驻最底部 */
.pagination { display: flex; flex-wrap: wrap; flex: 0 0 auto; justify-content: flex-end; align-items: center; gap: 6px; margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--line); }
.page-info { color: var(--muted); font-size: 12.5px; margin-right: 8px; }
.page-btn { display: inline-flex; align-items: center; gap: 4px; height: 31px; padding: 0 11px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--ink-soft); font-size: 13px; transition: border-color .15s, color .15s, background .15s; }
.page-btn:hover:not(:disabled):not(.active) { border-color: #d5d7e6; color: var(--ink); }
.page-btn:disabled { opacity: .45; cursor: default; }
.page-num { width: 31px; justify-content: center; padding: 0; }
.page-num.active { border-color: var(--brand); background: var(--brand-soft); color: var(--brand-deep, var(--brand)); font-weight: 500; }

/* 弹窗 */
.modal-backdrop { position: fixed; inset: 0; z-index: 40; display: grid; place-items: center; background: var(--scrim-bg, rgba(34, 37, 59, .28)); -webkit-backdrop-filter: var(--scrim-blur, blur(2px)); backdrop-filter: var(--scrim-blur, blur(2px)); }
.flashcard-modal, .editor-modal { width: min(560px, calc(100vw - 40px)); padding: 22px 24px; border-radius: 18px; background: #fff; box-shadow: 0 24px 64px rgba(34, 37, 59, .22); }
.editor-form { display: grid; gap: 12px; margin-top: 12px; }
.editor-field { display: grid; gap: 5px; }
.editor-field span { font-size: 12px; font-weight: 700; color: #5b5478; }
.editor-field input, .editor-field select, .editor-field textarea { padding: 8px 11px; border: 1.5px solid #e2dcf2; border-radius: 10px; background: #faf9ff; color: #2d294b; font-size: 13px; outline: none; font-family: inherit; }
.editor-field input:focus, .editor-field select:focus, .editor-field textarea:focus { border-color: #8b73dd; background: #fff; }
.editor-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 8px; }
.confirm-modal h3 { margin: 0 0 8px; font-size: 16px; color: #29283e; }
.confirm-desc { margin: 0 0 14px; font-size: 13px; color: #6e6a82; line-height: 1.6; }
.danger-button { display: inline-flex; align-items: center; justify-content: center; height: 36px; padding: 0 14px; border-radius: 12px; border: 1.5px solid #dc2626; border-bottom: 3px solid #b91c1c; background: #ef4444; color: #fff; font-size: 13px; font-weight: 700; cursor: pointer; transition: background .15s, transform .12s; }
.danger-button.slim { height: 34px; padding: 0 13px; font-size: 12.5px; }
.danger-button:hover:not(:disabled) { background: #dc2626; }
.danger-button:active:not(:disabled) { transform: translateY(1px); border-bottom-width: 2px; }
.fc-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.fc-progress-copy { display: flex; align-items: baseline; gap: 10px; }
.fc-progress-copy b { font-size: 16px; }
.fc-progress-copy span { color: var(--muted); font-size: 12.5px; }
.close-btn { display: grid; width: 30px; height: 30px; place-items: center; border: 0; border-radius: 8px; background: #f4f3f9; color: var(--muted); }
.close-btn:hover { background: #eae7f5; color: var(--ink); }
.fc-bar { height: 5px; overflow: hidden; margin-bottom: 18px; border-radius: 999px; background: #f0edf7; }
.fc-bar i { display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg, #8b73dd, #6265e8); transition: width .2s ease; }

.fc-meta { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.fc-prompt-box { padding: 18px; border: 1.5px solid #ebe7f5; border-radius: 14px; background: #faf9fe; }
.fc-context { margin: 0 0 8px; padding-bottom: 8px; border-bottom: 1px dashed #e2ddf2; color: #5b5575; font-size: 13px; line-height: 1.5; }
.fc-prompt-box small { color: var(--muted); font-size: 12px; }
.fc-prompt-box h2 { margin: 6px 0 0; font-size: 18px; line-height: 1.5; color: var(--ink); }
.fc-reveal-area { display: flex; justify-content: center; margin-top: 20px; }

.fc-answer-box { margin-top: 14px; padding-top: 14px; border-top: 1px dashed #e4dff2; }
.fc-answer-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.fc-answer-head small { color: var(--muted); font-size: 12px; }
.speak-pill { display: inline-flex; align-items: center; gap: 5px; height: 28px; padding: 0 10px; border: 1px solid #d9d1f2; border-radius: 999px; background: #f6f3ff; color: #694fc1; font-size: 12px; font-weight: 600; }
.speak-pill.speaking { background: #ebe4ff; }
.fc-answer-text { margin: 0; font-size: 16px; font-weight: 600; color: var(--ink); line-height: 1.5; }
.fc-phonetic { margin: 6px 0 0; font-size: 12.5px; color: #6e6592; }
.fc-note { margin: 8px 0 0; padding: 10px 12px; border-radius: 10px; background: #f8f8fc; color: var(--ink-soft); font-size: 12.5px; line-height: 1.55; white-space: pre-line; }

.fc-ratings { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 18px; }
.rate-btn { display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 10px 6px; border: 1.5px solid var(--line); border-radius: 12px; background: #fff; transition: transform .1s, border-color .15s, background .15s; }
.rate-btn:hover:not(:disabled) { transform: translateY(-1px); }
.rate-btn b { font-size: 13px; }
.rate-btn span { font-size: 11px; color: var(--muted); }
.rate-btn.again:hover:not(:disabled) { border-color: #efb8b8; background: #fdf3f3; color: #c03b3b; }
.rate-btn.hard:hover:not(:disabled) { border-color: #f0d3a5; background: #fef8ee; color: #b56d1c; }
.rate-btn.good:hover:not(:disabled) { border-color: #b9d7fb; background: #f2f7fe; color: #2d5fa8; }
.rate-btn.easy:hover:not(:disabled) { border-color: #b4e1cb; background: #eefaf4; color: #257a55; }

.fc-finish { display: grid; justify-items: center; padding: 24px 12px 12px; text-align: center; }
.finish-badge { display: grid; width: 54px; height: 54px; place-items: center; border-radius: 50%; background: #e6f6ef; color: #257a55; }
.fc-finish h3 { margin: 14px 0 6px; font-size: 18px; }
.fc-finish p { margin: 0 0 18px; color: var(--muted); font-size: 13.5px; }

/* 编辑表单 */
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }
.field span { font-size: 12.5px; font-weight: 600; color: var(--ink-soft); }
.field input, .field select, .field textarea { width: 100%; box-sizing: border-box; padding: 9px 11px; border: 1px solid var(--line); border-radius: 9px; background: #fff; color: var(--ink); font: inherit; font-size: 13.5px; }
.field input:focus, .field select:focus, .field textarea:focus { outline: none; border-color: var(--brand); box-shadow: 0 0 0 3px rgba(98, 101, 232, .12); }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 6px; }

.toast { position: fixed; left: 50%; bottom: 26px; z-index: 60; transform: translateX(-50%); padding: 9px 18px; border-radius: 999px; background: #2c2746; color: #fff; font-size: 13px; box-shadow: 0 10px 28px rgba(28, 24, 48, .25); }

@media (max-width: 780px) {
  .review-card { flex-direction: column; }
  .card-side { flex-direction: row; align-items: center; width: 100%; min-width: 0; }
  .mastery-box { max-width: 160px; }
  .fc-ratings { grid-template-columns: repeat(2, 1fr); }
  .form-grid { grid-template-columns: 1fr; }
}
</style>

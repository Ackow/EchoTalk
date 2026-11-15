<template>
  <!-- 历史记录：本人练习会话的时间线，支持状态/场景筛选、分页与继续练习 -->
  <section class="history-page">
    <!-- 游客态：历史记录需要登录后按用户隔离 -->
    <div v-if="!signedIn" class="history-guest">
      <span class="guest-icon"><AppIcon name="clock" :size="24" /></span>
      <h2>登录后查看练习历史</h2>
      <p>历史记录按账号保存。登录后可回看每一次场景对话，并接着上次的进度继续练习。</p>
      <router-link class="primary-button slim" :to="{ name: 'login' }"><AppIcon name="user" :size="15" />去登录</router-link>
    </div>

    <template v-else>
      <!-- 概览：全局统计，不随筛选变化 -->
      <div class="history-overview">
        <div class="ov-item">
          <span class="ov-icon purple"><AppIcon name="messages" :size="17" /></span>
          <div><small>练习场次</small><b>{{ stats.sessions }}<em>场</em></b></div>
        </div>
        <div class="ov-item">
          <span class="ov-icon mint"><AppIcon name="mic" :size="17" /></span>
          <div><small>对话轮次</small><b>{{ stats.turns }}<em>轮</em></b></div>
        </div>
        <div class="ov-item">
          <span class="ov-icon amber"><AppIcon name="check" :size="17" /></span>
          <div><small>已完成</small><b>{{ stats.finished }}<em>场</em></b></div>
        </div>
        <div class="ov-rate">
          <div class="ov-rate-head"><small>场景完成率</small><b>{{ finishRate }}%</b></div>
          <div class="ov-bar" role="img" :aria-label="`场景完成率 ${finishRate}%`"><i :style="{ width: `${finishRate}%` }"></i></div>
        </div>
      </div>

      <!-- 工具行：状态筛选 + 模式/场景筛选 -->
      <div class="history-toolbar">
        <AppTabs v-model="statusFilter" :options="STATUS_TABS" aria-label="练习状态筛选" />
        <div class="toolbar-right">
          <AppSelect v-model="modeFilter" :options="MODE_OPTIONS" label="模块" aria-label="按模块筛选" />
          <AppSelect v-model="sceneFilter" :options="sceneOptions" label="场景" aria-label="按场景筛选" />
          <span class="history-count">共 {{ total }} 条记录</span>
        </div>
      </div>

      <!-- 列表 -->
      <div v-if="loading" class="history-list" aria-busy="true" aria-label="正在加载历史记录">
        <div v-for="n in 5" :key="n" class="history-row skeleton">
          <span class="sk-badge"></span>
          <div class="sk-group"><span class="sk-line w40"></span><span class="sk-line w70"></span><span class="sk-line w30"></span></div>
        </div>
      </div>

      <div v-else-if="error" class="history-empty">
        <span class="empty-icon"><AppIcon name="x" :size="22" /></span>
        <h3>历史记录加载失败</h3>
        <p>{{ error }}</p>
        <button class="ghost-button" type="button" @click="load()"><AppIcon name="rotate" :size="14" />重试</button>
      </div>

      <template v-else-if="items.length">
        <div class="history-list">
          <article
            v-for="item in items"
            :key="item.id"
            class="history-row"
            role="link"
            tabindex="0"
            :aria-label="`${item.scene_name}，${item.turn_count} 轮对话，${item.status === 'finished' ? '已完成' : '进行中'}`"
            @click="openSession(item)"
            @keydown.enter.prevent="openSession(item)"
            @keydown.space.prevent="openSession(item)"
            @pointerenter="preloadPractice"
            @focus="preloadPractice"
          >
            <span class="row-badge" :class="`tone-${sceneTone(item)}`"><AppIcon :name="sceneIcon(item)" :size="19" /></span>
            <div class="row-main">
              <div class="row-title">
                <h3>{{ item.scene_name }}</h3>
                <span class="row-chip">{{ categoryLabel(item.category) }}</span>
                <span class="row-chip" :class="`diff-${diffClass(item.difficulty)}`">{{ diffLabel(item.difficulty) }}</span>
                <span class="row-state" :class="item.status === 'finished' ? 'done' : 'live'">
                  <i></i>{{ item.status === 'finished' ? '已完成' : '进行中' }}
                </span>              </div>
              <p class="row-preview">{{ item.preview || '这次练习还没有留下发言记录。' }}</p>
              <div class="row-meta">
                <span><AppIcon name="messages" :size="12" />{{ item.turn_count }} 轮</span>
                <span v-if="item.stage_name"><AppIcon name="compass" :size="12" />{{ item.stage_name }} {{ item.stage_index }}/{{ item.stage_total }}</span>
                <span v-if="item.goals_total"><AppIcon name="target" :size="12" />目标 {{ item.goals_done }}/{{ item.goals_total }}</span>
                <span v-if="item.goals_total && item.goals_done" class="goal-bar" aria-hidden="true"><i :style="{ width: `${goalPercent(item)}%` }"></i></span>
              </div>
            </div>
            <div class="row-side">
              <time :datetime="item.last_active_at">{{ formatWhen(item.last_active_at) }}</time>
              <div class="row-actions">
                <button
                  v-if="item.turn_count > 0 && (!item.record_type || item.record_type === 'conversation')"
                  class="row-report-btn"
                  type="button"
                  :disabled="reportLoadingId === item.id"
                  @click.stop="openReport(item)"
                  @keydown.enter.stop
                  @keydown.space.stop
                >
                  <AppIcon name="file-text" :size="13" />
                  <span>{{ reportLoadingId === item.id ? '加载中…' : '查看报告' }}</span>
                </button>
                <span class="row-action">{{ item.status === 'finished' ? '查看记录' : '继续练习' }}<AppIcon name="arrow-right" :size="14" /></span>
              </div>
            </div>
          </article>
        </div>

        <nav class="pagination" aria-label="历史记录分页">
          <span class="page-info">第 {{ page }} / {{ totalPages }} 页</span>
          <button class="page-btn" type="button" :disabled="page === 1" @click="page -= 1"><AppIcon name="chevron-left" :size="14" />上一页</button>
          <button
            v-for="p in pageNumbers"
            :key="p"
            class="page-btn page-num"
            :class="{ active: p === page }"
            type="button"
            :aria-current="p === page ? 'page' : undefined"
            @click="page = p"
          >{{ p }}</button>
          <button class="page-btn" type="button" :disabled="page === totalPages" @click="page += 1">下一页<AppIcon name="arrow-right" :size="14" /></button>
        </nav>
      </template>

      <div v-else class="history-empty">
        <span class="empty-icon"><AppIcon name="clock" :size="22" /></span>
        <h3>{{ filtered ? '没有符合条件的记录' : '还没有练习记录' }}</h3>
        <p>{{ filtered ? '换个状态或场景再看看。' : '去语音对话选一个场景，练习结束后这里会留下完整回顾。' }}</p>
        <button v-if="filtered" class="ghost-button" type="button" @click="resetFilters">清除筛选</button>
        <router-link v-else class="primary-button slim" :to="{ name: 'practice' }"><AppIcon name="mic" :size="15" />开始第一次练习</router-link>
      </div>

      <div v-if="reportError" class="report-error-banner" role="alert">
        <span>{{ reportError }}</span>
        <button type="button" @click="reportError = ''" aria-label="关闭提示"><AppIcon name="x" :size="13" /></button>
      </div>
    </template>

    <Teleport to="body">
      <PracticeReportModal :open="reportOpen" :report="sessionReport" @close="reportOpen = false" />
    </Teleport>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import AppSelect from '../components/AppSelect.vue'
import AppTabs from '../components/AppTabs.vue'
import PracticeReportModal from '../components/practice/PracticeReportModal.vue'
import { getSessionReport, listSessions } from '../api/sessions'
import { listScenes } from '../api/scenes'
import { session } from '../auth/session'
import { usePageLoading } from '../app/loading'
import { categoryLabel, diffClass, diffLabel, sceneIcon, sceneTone } from '../constants/sceneMeta'

const PAGE_SIZE = 8
const STATUS_TABS = [
  { value: '', label: '全部' },
  { value: 'active', label: '进行中' },
  { value: 'finished', label: '已完成' },
]
const MODE_OPTIONS = [
  { value: 'all', label: '全部模块' },
  { value: 'conversation', label: '语音对话' },
  { value: 'listening', label: '听力工作室' },
  { value: 'debate', label: '多角色对话' },
]

const router = useRouter()
const signedIn = ref(Boolean(session.token))
const items = ref([])
const total = ref(0)
const page = ref(1)
const statusFilter = ref('')
const modeFilter = ref('all')
const sceneFilter = ref('')
const sceneOptions = ref([{ value: '', label: '全部场景' }])
const stats = ref({ sessions: 0, turns: 0, finished: 0 })
const loading = ref(false)
const error = ref('')
const reportOpen = ref(false)
const reportLoadingId = ref(null)
const sessionReport = ref(null)
const reportError = ref('')
const finishLoading = usePageLoading() // 首屏记录返回前沿用路由遮罩，翻页/筛选只走列表骨架

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))
const filtered = computed(() => Boolean(statusFilter.value || sceneFilter.value || modeFilter.value !== 'all'))
const finishRate = computed(() => stats.value.sessions ? Math.round((stats.value.finished / stats.value.sessions) * 100) : 0)

// 页码窗口：最多 5 个，始终包含首尾附近，避免记录多时页码铺满一行
const pageNumbers = computed(() => {
  const count = totalPages.value
  if (count <= 5) return Array.from({ length: count }, (_, i) => i + 1)
  const start = Math.min(Math.max(page.value - 2, 1), count - 4)
  return Array.from({ length: 5 }, (_, i) => start + i)
})

const goalPercent = (item) => item.goals_total ? Math.round((item.goals_done / item.goals_total) * 100) : 0

const pad = (value) => String(value).padStart(2, '0')

// 后端时间为北京时间 naive（如 2026-11-12T20:15:15），直接按本地时区解析
function formatWhen(iso) {
  if (!iso) return ''
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  const now = new Date()
  const startOfDay = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
  const days = Math.round((startOfDay(now) - startOfDay(date)) / 86400000)
  const time = `${pad(date.getHours())}:${pad(date.getMinutes())}`
  if (days <= 0) return `今天 ${time}`
  if (days === 1) return `昨天 ${time}`
  if (days < 7) return `${['周日', '周一', '周二', '周三', '周四', '周五', '周六'][date.getDay()]} ${time}`
  if (date.getFullYear() === now.getFullYear()) return `${date.getMonth() + 1}月${date.getDate()}日`
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`
}

function openSession(item) {
  if (item.record_type === 'debate') {
    router.push({ name: 'debate', query: { session: item.id } })
    return
  }
  if (item.record_type === 'listening') {
    router.push({ name: 'listening', query: { unit: item.scene_id } })
    return
  }
  router.push({ name: 'practice', query: { session: item.id } }) // 对话页按 session 恢复历史会话
}

async function openReport(item) {
  if (!item?.id || reportLoadingId.value) return
  reportLoadingId.value = item.id
  reportError.value = ''
  try {
    const { data } = await getSessionReport(item.id)
    sessionReport.value = data
    reportOpen.value = true
  } catch (err) {
    reportError.value = err?.message || '获取练习报告失败，请稍后重试'
  } finally {
    reportLoadingId.value = null
  }
}

// 预取对话页分包：路由是按需加载，提前拉一次代码，点击记录时不再等分包下载（否则内容区会空一瞬）
let practiceChunk = null
function preloadPractice() {
  practiceChunk = practiceChunk || import('../views/Practice.vue')
}

function resetFilters() {
  statusFilter.value = ''
  modeFilter.value = 'all'
  sceneFilter.value = ''
}

async function load() {
  if (!signedIn.value) return
  loading.value = true
  error.value = ''
  try {
    const { data } = await listSessions({
      page: page.value, page_size: PAGE_SIZE,
      status: statusFilter.value || undefined,
      mode: modeFilter.value !== 'all' ? modeFilter.value : undefined,
      scene_id: sceneFilter.value || undefined,
    })
    items.value = data.items || []
    total.value = data.total || 0
    stats.value = data.stats || stats.value
    if (page.value > totalPages.value) page.value = totalPages.value // 删除/筛选后页码越界时回退
  } catch (err) {
    error.value = err.message || '加载失败，请稍后重试。'
    items.value = []
  } finally {
    loading.value = false
    finishLoading()
  }
}

// 场景下拉：用场景列表填充，便于按场景回看
async function loadScenes() {
  try {
    const { data } = await listScenes()
    sceneOptions.value = [{ value: '', label: '全部场景' }, ...(data?.items || []).map((scene) => ({ value: scene.id, label: scene.name }))]
  } catch { /* 场景列表失败不影响历史记录本身 */ }
}

// 筛选变化回到第一页；分页变化只重新取数
watch([statusFilter, modeFilter, sceneFilter], () => { page.value = 1; load() })
watch(page, load)
onMounted(() => {
  if (!signedIn.value) { finishLoading(); return } // 游客没有可查的记录：直接撤遮罩，展示登录引导
  load()
  loadScenes()
  // 空闲时预取对话页代码，缩短点击记录后的等待
  if (window.requestIdleCallback) window.requestIdleCallback(preloadPractice, { timeout: 2000 })
  else setTimeout(preloadPractice, 600)
})
</script>

<style scoped>
.history-page { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow-y: auto; padding: 22px clamp(18px, 2.4vw, 34px) 14px; background: #faf9ff; }

/* 概览条：三段统计 + 完成率，紧凑一行 */
.history-overview { display: flex; align-items: center; gap: 10px; flex: 0 0 auto; margin-bottom: 16px; }
.ov-item { display: flex; align-items: center; gap: 10px; min-width: 0; padding: 11px 16px; border: 1.5px solid #ebe7f5; border-bottom: 3px solid #e5def1; border-radius: 16px; background: #fff; }
.ov-icon { display: grid; width: 34px; height: 34px; flex: 0 0 34px; place-items: center; border-radius: 12px; }
.ov-icon.purple { background: #f0eaff; color: #7a5fd0; }
.ov-icon.mint { background: #e6f6ee; color: #3f8b68; }
.ov-icon.amber { background: #fff3dd; color: #b6813a; }
.ov-item small { display: block; color: #9a94b4; font-size: 11.5px; }
.ov-item b { display: inline-flex; align-items: baseline; gap: 3px; color: #393451; font-size: 20px; font-weight: 800; letter-spacing: -.02em; }
.ov-item em { color: #b3adc4; font-size: 11.5px; font-style: normal; font-weight: 600; }
.ov-rate { flex: 1; min-width: 140px; max-width: 260px; margin-left: auto; padding: 11px 16px; border: 1.5px solid #ebe7f5; border-bottom: 3px solid #e5def1; border-radius: 16px; background: #fff; }
.ov-rate-head { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }
.ov-rate-head small { color: #9a94b4; font-size: 11.5px; }
.ov-rate-head b { color: #654ab8; font-size: 15px; font-weight: 800; }
.ov-bar { height: 6px; margin-top: 7px; overflow: hidden; border-radius: 99px; background: #f1eef9; }
.ov-bar i { display: block; height: 100%; border-radius: 99px; background: linear-gradient(90deg, #b9a4f0, #8b73dd); transition: width .3s ease; }

/* 工具行 */
.history-toolbar { display: flex; flex-wrap: wrap; flex: 0 0 auto; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 12px; }
.seg-filter { display: inline-flex; gap: 4px; padding: 4px; border: 1.5px solid #e9e5f1; border-radius: 13px; background: #fff; }
.seg-item { height: 34px; padding: 0 14px; border: 0; border-radius: 10px; background: transparent; color: var(--ink-soft); font-size: 13.5px; font-weight: 600; white-space: nowrap; transition: background .15s, color .15s; }
.seg-item:hover { color: var(--ink); }
.seg-item.active { background: #eee8ff; color: #694fc1; }
.toolbar-right { display: flex; align-items: center; gap: 10px; }
.history-count { color: #9a94b4; font-size: 12px; white-space: nowrap; }

/* 列表行：左侧色调徽标 + 主信息 + 右侧时间与动作 */
.history-list { display: flex; flex-direction: column; gap: 8px; flex: 0 0 auto; }
.history-row { display: flex; align-items: center; gap: 14px; padding: 12px 16px; border: 1.5px solid #ebe7f5; border-bottom: 3px solid #e5def1; border-radius: 16px; background: #fff; cursor: pointer; transition: border-color .16s, transform .16s, box-shadow .16s; animation: row-in .32s cubic-bezier(.22, .8, .32, 1) backwards; }
.history-row:hover { border-color: #cfc1f1; border-bottom-color: #d5c8ef; transform: translateY(-2px); box-shadow: 0 8px 18px #51408412; }
.history-row:focus-visible { outline: 2px solid #a58ee9; outline-offset: 2px; }
.row-badge { display: grid; width: 42px; height: 42px; flex: 0 0 42px; place-items: center; border-radius: 14px; }
.row-badge.tone-daily { background: #fff0dc; color: #7a5c40; }
.row-badge.tone-travel { background: #e7efff; color: #45618c; }
.row-badge.tone-business { background: #e5f3eb; color: #3a6b55; }
.row-badge.tone-career { background: #eee9ff; color: #56447f; }
.row-badge.tone-academic { background: #e8efff; color: #45618c; }
.row-badge.tone-custom { background: #f5eaf1; color: #735467; }
.row-main { flex: 1; min-width: 0; }
.row-title { display: flex; align-items: center; gap: 6px; min-width: 0; }
.row-title h3 { flex: 0 1 auto; min-width: 0; overflow: hidden; margin: 0; color: #393451; font-size: 14.5px; font-weight: 750; text-overflow: ellipsis; white-space: nowrap; }
.row-chip { display: inline-flex; flex: 0 0 auto; align-items: center; height: 20px; padding: 0 8px; border-radius: 999px; background: #f2eff8; color: #655e78; font-size: 11px; font-weight: 600; }
.row-chip.diff-hard { background: #fdf0e8; color: #a4632f; }
.row-chip.diff-expert { background: #fbeaee; color: #9c4056; }
.row-chip.diff-easy, .row-chip.diff-entry { background: #e9f6ef; color: #3a7d5c; }
.row-state { display: inline-flex; flex: 0 0 auto; align-items: center; gap: 5px; color: #6f6a85; font-size: 11.5px; font-weight: 700; white-space: nowrap; }
.row-state i { width: 6px; height: 6px; border-radius: 50%; background: #c9c4da; }
.row-state.live i { background: #59b98a; box-shadow: 0 0 0 3px #59b98a22; }
.row-state.done { color: #7a5fd0; }
.row-state.done i { background: #8b73dd; }
.row-preview { display: block; max-width: 100%; overflow: hidden; margin: 5px 0 2px; color: #6b6580; font-size: 12.5px; line-height: 1.5; text-overflow: ellipsis; white-space: nowrap; }
.row-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 12px; margin-top: 4px; color: #9a94b4; font-size: 11.5px; }
.row-meta span { display: inline-flex; align-items: center; gap: 4px; }
.goal-bar { width: 44px; height: 4px; overflow: hidden; border-radius: 99px; background: #f1eef9; }
.goal-bar i { display: block; height: 100%; border-radius: 99px; background: #a58ee9; }
.row-side { display: flex; flex-direction: column; align-items: flex-end; justify-content: center; gap: 7px; flex: 0 0 auto; }
.row-side time { color: #9a94b4; font-size: 11.5px; white-space: nowrap; font-variant-numeric: tabular-nums; }
.row-actions { display: flex; align-items: center; gap: 6px; }
.row-report-btn { display: inline-flex; align-items: center; gap: 4px; padding: 5px 10px; border: 1.5px solid #ebe7f5; border-bottom-width: 2px; border-radius: 11px; background: #fff; color: #5b5472; font-size: 12px; font-weight: 650; white-space: nowrap; cursor: pointer; transition: background .15s, border-color .15s, color .15s; }
.row-report-btn:hover:not(:disabled) { border-color: #c9b8ee; background: #f6f3ff; color: #654ab8; }
.row-report-btn:disabled { opacity: .6; cursor: wait; }
.row-action { display: inline-flex; align-items: center; gap: 4px; padding: 5px 12px; border: 1.5px solid #ebe7f5; border-bottom-width: 2px; border-radius: 11px; background: #faf8ff; color: #654ab8; font-size: 12px; font-weight: 700; white-space: nowrap; transition: background .15s, border-color .15s; }
.history-row:hover .row-action { border-color: #c9b8ee; background: #f0eaff; }
.report-error-banner { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-top: 10px; padding: 9px 14px; border: 1px solid #f2cbd4; border-radius: 12px; background: #fff5f7; color: #9c4056; font-size: 12.5px; }
.report-error-banner button { display: grid; place-items: center; padding: 2px; border: 0; background: transparent; color: inherit; cursor: pointer; }

/* 空态与游客态 */
.history-empty, .history-guest { display: grid; flex: 1 0 auto; place-content: center; justify-items: center; padding: 46px 20px; border: 2px dashed #d9d0ef; border-radius: 18px; background: #fff; text-align: center; }
.empty-icon { display: grid; width: 54px; height: 54px; place-items: center; border-radius: 18px; background: #f0eaff; color: #8067d1; }
.history-empty h3, .history-guest h2 { margin: 14px 0 6px; color: #393451; font-size: 16px; font-weight: 750; }
.history-empty p, .history-guest p { max-width: 420px; margin: 0 0 16px; color: #8b859f; font-size: 13.5px; line-height: 1.7; text-wrap: pretty; }
.guest-icon { display: grid; width: 54px; height: 54px; place-items: center; border-radius: 18px; background: #f0eaff; color: #8067d1; }

/* 骨架 */
.history-row.skeleton { cursor: default; animation: none; }
.sk-badge { width: 42px; height: 42px; flex: 0 0 42px; border-radius: 14px; background: #f1eef9; }
.sk-group { display: flex; flex: 1; flex-direction: column; gap: 7px; }
.sk-line { height: 10px; border-radius: 5px; background: linear-gradient(90deg, #f1eef9 25%, #f8f5ff 45%, #f1eef9 65%); background-size: 200% 100%; animation: shimmer 1.3s infinite; }
.sk-line.w40 { width: 40%; height: 13px; }
.sk-line.w70 { width: 70%; }
.sk-line.w30 { width: 30%; }

/* 分页：贴内容区底部（记录不足一屏时 margin-top:auto 把它压到底），记录超长时自然跟随滚动 */
.pagination { display: flex; flex-wrap: wrap; flex: 0 0 auto; justify-content: flex-end; align-items: center; gap: 6px; margin-top: auto; padding: 12px 2px 2px; }
.page-info { margin-right: 8px; color: #9a94b4; font-size: 12.5px; }
.page-btn { display: inline-flex; align-items: center; gap: 4px; height: 31px; padding: 0 11px; border: 1.5px solid #ebe7f5; border-bottom-width: 3px; border-radius: 11px; background: #fff; color: var(--ink-soft); font-size: 13px; font-weight: 600; transition: border-color .15s, color .15s, background .15s; }
.page-btn:hover:not(:disabled):not(.active) { border-color: #d5c8ef; color: var(--ink); }
.page-btn:disabled { opacity: .45; cursor: default; }
.page-num { width: 31px; justify-content: center; padding: 0; }
.page-num.active { border-color: #a58ee9; border-bottom-color: #8067d1; background: #f0eaff; color: #654ab8; }
.primary-button.slim, .ghost-button { min-height: 38px; border-radius: 12px; font-weight: 650; }
/* 空态/游客态里按钮按内容宽度居中，不继承全局 100% 宽与两端对齐 */
.history-empty .primary-button.slim, .history-guest .primary-button.slim,
.history-empty .ghost-button { width: auto; height: 38px; margin-top: 0; padding: 0 18px; justify-content: center; gap: 7px; }
.ghost-button { border: 1.5px solid #e9e5f1; border-bottom-width: 3px; }
.primary-button.slim { border: 1.5px solid #8067d1; border-bottom: 4px solid #6951b8; background: #8b73dd; }

@keyframes row-in { from { opacity: 0; transform: translateY(6px); } }
@keyframes shimmer { from { background-position: 200% 0; } to { background-position: -200% 0; } }

@media (max-height: 700px) {
  .history-page { padding-top: 14px; }
  .history-overview { margin-bottom: 12px; }
  .ov-item, .ov-rate { padding: 8px 12px; }
  .history-row { padding: 9px 14px; }
  .row-badge { width: 38px; height: 38px; flex-basis: 38px; }
}
@media (max-width: 1080px) {
  .ov-rate { display: none; } /* 窄内容区优先保留列表宽度 */
  .seg-item { padding: 0 10px; font-size: 12.5px; }
}
@media (max-width: 760px) {
  .row-side { display: none; } /* 极窄时时间与动作并入主信息，避免挤压标题 */
  .history-count { display: none; }
}
@media (prefers-reduced-motion: reduce) { .history-row, .history-row:hover { transition: none; transform: none; animation: none; } }
</style>

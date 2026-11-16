<template>
  <div class="page-scroll" :class="{ 'is-embedded-only': embeddedOnly }">
    <template v-if="!embeddedOnly">
      <div class="pick-toolbar">
      <AppTabs
        v-model="pickCategory"
        :options="pickCategories.map((c) => ({ value: c.key, label: c.label, count: countFor(c.key) }))"
        aria-label="场景分类筛选"
      />
      <div class="toolbar-right">
        <label class="search-box">
          <AppIcon name="search" :size="14" />
          <input v-model="keyword" type="search" placeholder="搜索场景名称或描述" />
          <button v-if="keyword" class="search-clear" type="button" aria-label="清空搜索" @click="keyword = ''">
            <AppIcon name="x" :size="12" />
          </button>
        </label>
        <router-link :to="{ name: 'scenes' }" class="ghost-button"><AppIcon name="compass" :size="14" />探索全部场景</router-link>
      </div>
    </div>

    <p v-if="!signedIn" class="login-hint"><AppIcon name="info" :size="14" />开始练习前，请先<router-link :to="{ name: 'login', query: { redirect: $route.fullPath } }">登录</router-link>，保存你的对话进度。</p>
    <p v-if="error" class="page-error" role="alert"><AppIcon name="alert" :size="14" />{{ error }}</p>

    <div v-if="!loadingScenes" class="scene-grid">
      <article
        v-for="(scene, index) in pagedScenes"
        :key="scene.id"
        class="scene-card"
        :class="{ busy: starting }"
        role="button"
        tabindex="0"
        :aria-disabled="starting"
        :style="{ animationDelay: `${Math.min(index, 8) * 45}ms` }"
        @click="emit('choose', scene)"
        @keydown.enter.prevent="emit('choose', scene)"
        @keydown.space.prevent="emit('choose', scene)"
      >
        <SceneCover :scene="scene" :category-label="coverLabel(scene.category)" mark-icon="arrow-right" />
        <div class="card-body">
          <div class="card-head">
            <span class="mode-chip"><AppIcon :name="modeIcon(scene.mode)" :size="13" />{{ modeLabel(scene.mode) }}</span>
            <span v-if="scene.difficulty" class="diff-chip" :class="diffClass(scene.difficulty)">{{ diffLabel(scene.difficulty) }}</span>
          </div>
          <p class="scene-desc">{{ scene.description || '在真实情境中练习英语表达。' }}</p>
          <div class="scene-foot">
            <span class="scene-meta">
              <span v-if="scene.objective_count"><AppIcon name="target" :size="12" />{{ scene.objective_count }} 个目标</span>
              <span v-if="scene.stage_count"><AppIcon name="chart-line" :size="12" />{{ scene.stage_count }} 阶段</span>
              <span v-if="scene.knowledge_count"><AppIcon name="book-open" :size="12" />{{ scene.knowledge_count }} 份资料</span>
            </span>
            <span class="scene-go">{{ starting ? '准备中…' : '开始对话' }}<AppIcon name="arrow-right" :size="14" /></span>
          </div>
        </div>
      </article>

      <div v-if="!filteredScenes.length" class="scenes-empty">
        <div class="empty-icon"><AppIcon name="messages" :size="20" /></div>
        <h3>{{ keyword || pickCategory !== 'all' ? '没有匹配的场景' : '训练台暂无对话场景' }}</h3>
        <p>{{ keyword || pickCategory !== 'all' ? '换个关键词或分类再试试。' : '在场景探索页收藏内置/社区场景，或新建你的专属场景后，即可在这里开始练习。' }}</p>
        <router-link
          v-if="!keyword && pickCategory === 'all'"
          :to="{ name: 'scenes', query: { tab: 'conversation' } }"
          class="confirm-button empty-cta"
        >
          <AppIcon name="compass" :size="14" />前往场景探索收藏场景
        </router-link>
      </div>
    </div>

    <nav v-if="!loadingScenes && filteredScenes.length" class="pagination" aria-label="场景分页">
      <span class="page-info">共 {{ filteredScenes.length }} 个场景 · 第 {{ page }} / {{ totalPages }} 页</span>
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

    <div v-if="loadingScenes" class="scene-grid" aria-busy="true" aria-label="正在加载场景">
      <div v-for="n in 4" :key="n" class="scene-card skeleton">
        <div class="sk-cover"></div>
        <div class="sk-body">
          <div class="sk-line w40"></div>
          <div class="sk-line w80"></div>
          <div class="sk-line w60"></div>
          <div class="sk-line w70"></div>
        </div>
      </div>
    </div>
    </template>

    <!-- 进入对话确认弹窗 -->
    <div v-if="confirmScene" class="modal-backdrop" @click.self="emit('cancel-confirm')">
      <div class="modal-card" role="alertdialog" aria-modal="true" :aria-label="`开始场景 ${confirmScene.name}`">
        <div class="modal-icon"><AppIcon name="messages" :size="18" /></div>
        <h3>「{{ confirmScene.name }}」</h3>
        <p v-if="checkingHistory">正在查找练习记录…</p>
        <p v-else-if="historyError" class="history-error" role="alert">{{ historyError }}</p>
        <p v-else-if="latestHistory">你有一条未结束的练习记录，要继续上次练习还是新开一场？</p>
        <p v-else>将创建一条新的练习会话，与场景角色从开场白开始对话。</p>
        <ul v-if="!latestHistory && !checkingHistory && !historyError" class="modal-facts">
          <li v-if="confirmScene.objective_count"><span>训练目标</span><b>{{ confirmScene.objective_count }} 个</b></li>
          <li v-if="confirmScene.stage_count"><span>对话阶段</span><b>{{ confirmScene.stage_count }} 个</b></li>
          <li v-if="confirmScene.difficulty"><span>难度</span><b>{{ diffLabel(confirmScene.difficulty) }}</b></li>
        </ul>
        <div class="modal-actions">
          <button class="ghost-button" type="button" :disabled="starting" @click="emit('cancel-confirm')">取消</button>
          <button v-if="historyError" class="ghost-button" type="button" :disabled="checkingHistory" @click="emit('choose', confirmScene)">重试</button>
          <template v-if="latestHistory">
            <button class="ghost-button" type="button" :disabled="starting || checkingHistory || !!historyError" @click="emit('confirm-start')">
              <span v-if="starting" class="ui-spinner" aria-hidden="true" />
              <span>{{ starting ? '准备中…' : '新开练习' }}</span>
            </button>
            <button class="confirm-button" type="button" :disabled="starting || checkingHistory" @click="emit('resume-scene', confirmScene, latestHistory.id)">
              <span v-if="starting" class="ui-spinner send-spinner" aria-hidden="true" />
              <AppIcon v-else name="arrow-right" :size="14" />
              <span>继续练习</span>
            </button>
          </template>
          <button v-else class="confirm-button" type="button" :disabled="starting || checkingHistory || !!historyError" @click="emit('confirm-start')">
            <span v-if="starting" class="ui-spinner send-spinner" aria-hidden="true" />
            <AppIcon v-else name="arrow-right" :size="14" />
            <span>{{ starting ? '准备中…' : '确认开始' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import AppIcon from '../AppIcon.vue'
import AppTabs from '../AppTabs.vue'
import SceneCover from '../scene/SceneCover.vue'

const CATEGORY_LABELS = { daily: '日常', interview: '面试', career: '职业', academic: '学术', custom: '自定义', travel: '旅行', business: '商务', campus: '校园', debate: '辩论' }
const COVER_LABELS = { daily: '日常沟通', business: '职场沟通', career: '求职训练', academic: '学术场景', custom: '自定义' }
const MODE_META = { conversation: { icon: 'messages', label: '对话' }, interview: { icon: 'briefcase', label: '面试' }, debate: { icon: 'messages', label: '辩论' } }
const PAGE_SIZE = 9

const props = defineProps({
  embeddedOnly: { type: Boolean, default: false },
  scenes: { type: Array, default: () => [] },
  loadingScenes: { type: Boolean, default: false },
  starting: { type: Boolean, default: false },
  error: { type: String, default: '' },
  signedIn: { type: Boolean, default: false },
  confirmScene: { type: Object, default: null },
  latestHistory: { type: Object, default: null },
  checkingHistory: { type: Boolean, default: false },
  historyError: { type: String, default: '' },
})
const emit = defineEmits(['choose', 'cancel-confirm', 'confirm-start', 'resume-scene'])

const pickCategory = ref('all')
const keyword = ref('')
const page = ref(1)

const categoryLabel = (key) => CATEGORY_LABELS[key] || key || '通用'
const coverLabel = (key) => COVER_LABELS[key] || categoryLabel(key)
const diffLabel = (key) => ({ entry: '入门', easy: '简单', normal: '普通', hard: '困难', expert: '专家' }[key] || key)
const diffClass = (key) => ({ entry: 'entry', easy: 'easy', normal: 'normal', hard: 'hard', expert: 'expert' }[key] || 'normal')
const modeIcon = (mode) => MODE_META[mode]?.icon || 'messages'
const modeLabel = (mode) => MODE_META[mode]?.label || mode

const pickCategories = computed(() => {
  const seen = new Map()
  for (const scene of props.scenes) seen.set(scene.category, (seen.get(scene.category) || 0) + 1)
  return [
    { key: 'all', label: '全部', count: props.scenes.length },
    ...[...seen.keys()].map((key) => ({ key, label: categoryLabel(key), count: seen.get(key) })),
  ]
})
const countFor = (key) => pickCategories.value.find((cat) => cat.key === key)?.count || 0

const filteredScenes = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return props.scenes.filter((scene) => {
    if (pickCategory.value !== 'all' && scene.category !== pickCategory.value) return false
    if (!text) return true
    return [scene.name, scene.description, ...(scene.tags || [])].some((field) => String(field || '').toLowerCase().includes(text))
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredScenes.value.length / PAGE_SIZE)))
const pagedScenes = computed(() => filteredScenes.value.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE))

watch([pickCategory, keyword], () => { page.value = 1 })
watch(totalPages, (total) => { if (page.value > total) page.value = total })
</script>

<style scoped>
.page-scroll { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: auto; padding: 22px 28px 32px; }
.pick-toolbar { display: flex; flex: 0 0 auto; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.toolbar-right { display: flex; align-items: center; gap: 9px; }
.search-box { position: relative; display: inline-flex; align-items: center; gap: 7px; width: 240px; height: 34px; padding: 0 10px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--faint); transition: border-color .15s, box-shadow .15s; }
.search-box:focus-within { border-color: var(--brand); box-shadow: 0 0 0 3px rgba(98, 101, 232, .12); }
.search-box input { flex: 1; min-width: 0; border: 0; outline: none; background: transparent; color: var(--ink); font-size: 13.5px; }
.search-box input::placeholder { color: var(--faint); }
.search-box input::-webkit-search-cancel-button { -webkit-appearance: none; appearance: none; display: none; }
.search-clear { display: grid; place-items: center; width: 18px; height: 18px; border: 0; border-radius: 50%; background: #eef0f5; color: var(--muted); transition: background .15s, color .15s; }
.search-clear:hover { background: #e3e5ee; color: var(--ink); }
.login-hint, .page-error { display: flex; flex-wrap: wrap; align-items: center; gap: 5px; margin: 0 0 18px; color: var(--muted); font-size: 13px; }
.login-hint a { color: var(--brand); }
.page-error { color: var(--danger); }
.scene-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(275px, 1fr)); gap: 14px; align-content: start; flex: 1 0 auto; }
.scene-card { display: flex; flex-direction: column; padding: 0; overflow: visible; border: 1.5px solid #ebe7f5; border-bottom: 4px solid #e5def1; border-radius: 19px; background: #fff; text-align: left; cursor: pointer; transition: border-color .18s, transform .18s, box-shadow .18s; animation: card-in .38s cubic-bezier(.22, .8, .32, 1) backwards; }
.scene-card:hover:not(.busy) { border-color: #cfc1f1; border-bottom-color: #d9cdef; transform: translateY(-3px); box-shadow: 0 8px 18px #51408412; }
.scene-card:active:not(.busy) { transform: translateY(0); }
.scene-card:focus-visible { outline: 2px solid var(--brand); outline-offset: 3px; }
.scene-card.busy { opacity: .6; pointer-events: none; }
.scene-card:hover :deep(.scene-cover-mark), .scene-card:focus-visible :deep(.scene-cover-mark) { opacity: 1; transform: translate(0, 0); }
.card-body { display: flex; flex-direction: column; flex: 1; padding: 13px 15px 15px; }
@keyframes card-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
.card-head { display: flex; align-items: center; gap: 7px; margin-bottom: 9px; }
.mode-chip { display: inline-flex; align-items: center; gap: 4px; height: 22px; padding: 0 9px; border-radius: 999px; background: var(--brand-soft); color: var(--brand-deep); font-size: 11.5px; font-weight: 600; }
.diff-chip { display: inline-flex; align-items: center; height: 22px; padding: 0 9px; border-radius: 999px; background: #f1f2f7; color: var(--ink-soft); font-size: 11.5px; font-weight: 600; }
.diff-chip.entry { background: #e3f2ea; color: #2f7a52; }
.diff-chip.easy { background: #e0f2ef; color: #257a6b; }
.diff-chip.normal { background: #e3ecfb; color: #33619f; }
.diff-chip.hard { background: #fdefe0; color: #b26a24; }
.diff-chip.expert { background: #fbe7e7; color: #b03a3a; }
.scene-desc { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; min-height: 42px; margin: 0; color: #6d6880; font-size: 13.5px; line-height: 1.55; text-wrap: pretty; }
.scene-foot { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: auto; padding-top: 12px; border-top: 1px solid #efedf5; }
.scene-meta { display: flex; flex-wrap: wrap; gap: 4px 8px; min-width: 0; }
.scene-meta span { display: inline-flex; align-items: center; gap: 3px; color: var(--muted); font-size: 11px; white-space: nowrap; }
.scene-go { display: inline-flex; align-items: center; gap: 4px; flex: 0 0 auto; color: var(--brand); font-size: 12.5px; font-weight: 600; white-space: nowrap; }
.scenes-empty { grid-column: 1 / -1; display: grid; justify-items: center; padding: 46px 20px; border: 2px dashed #d9d0ef; border-radius: 18px; background: #fff; text-align: center; }
.empty-icon { display: grid; width: 54px; height: 54px; place-items: center; border: 0; border-radius: 18px; background: #f0eaff; color: #8067d1; }
.scenes-empty h3 { margin: 14px 0 6px; font-size: 16px; font-weight: 600; }
.scenes-empty p { margin: 0; max-width: 400px; color: var(--muted); font-size: 13.5px; line-height: 1.65; text-wrap: pretty; }
.empty-cta { margin-top: 16px; text-decoration: none; }
.pagination { display: flex; flex-wrap: wrap; flex: 0 0 auto; justify-content: flex-end; align-items: center; gap: 6px; margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--line); }
.page-info { color: var(--muted); font-size: 12.5px; margin-right: 8px; }
.page-btn { display: inline-flex; align-items: center; gap: 4px; height: 31px; padding: 0 11px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--ink-soft); font-size: 13px; transition: border-color .15s, color .15s, background .15s; }
.page-btn:hover:not(:disabled):not(.active) { border-color: #d5d7e6; color: var(--ink); }
.page-btn:disabled { opacity: .45; cursor: default; }
.page-num { width: 31px; justify-content: center; padding: 0; }
.page-num.active { border-color: var(--brand); background: var(--brand-soft); color: var(--brand-deep, var(--brand)); font-weight: 500; }
.scene-card.skeleton { animation: none; cursor: default; }
.sk-cover { height: 100px; margin: -1.5px -1.5px 0; border-radius: 17px 17px 0 0; background: linear-gradient(90deg, #f0eef7 25%, #f8f7fc 45%, #f0eef7 65%); background-size: 200% 100%; animation: shimmer 1.3s infinite; }
.sk-body { padding: 13px 17px 17px; }
.sk-line { height: 12px; margin-top: 10px; border-radius: 5px; background: linear-gradient(90deg, #eef0f5 25%, #f6f7fa 45%, #eef0f5 65%); background-size: 200% 100%; animation: shimmer 1.3s infinite; }
.sk-line.w40 { width: 40%; margin-top: 0; }
.sk-line.w80 { width: 80%; height: 14px; }
.sk-line.w60 { width: 60%; }
.sk-line.w70 { width: 70%; }
@keyframes shimmer { from { background-position: 200% 0; } to { background-position: -200% 0; } }

.page-scroll.is-embedded-only { display: contents; }
.page-scroll.is-embedded-only .modal-backdrop { z-index: 60; }
.modal-backdrop { position: fixed; inset: 0; z-index: 40; display: grid; place-items: center; background: var(--scrim-bg, rgba(34, 37, 59, .28)); -webkit-backdrop-filter: var(--scrim-blur, blur(2px)); backdrop-filter: var(--scrim-blur, blur(2px)); animation: fade-in .18s ease; }
.modal-card { width: min(380px, calc(100vw - 48px)); padding: 24px; border: 1.5px solid #ebe7f5; border-bottom: 5px solid #e5def1; border-radius: 20px; background: var(--surface); box-shadow: 0 18px 48px rgba(34, 37, 59, .18); animation: pop-in .22s cubic-bezier(.22, .8, .32, 1); }
.modal-icon { display: grid; width: 38px; height: 38px; margin-bottom: 14px; place-items: center; border-radius: 14px; background: #f0eaff; color: #7158c4; }
.modal-card h3 { margin: 0 0 8px; font-size: 16.5px; font-weight: 600; }
.modal-card > p { margin: 0 0 14px; color: var(--muted); font-size: 13.5px; line-height: 1.65; text-wrap: pretty; }
.history-error { color: var(--danger); }
.modal-facts { display: flex; flex-direction: column; gap: 7px; margin: 0 0 18px; padding: 11px 13px; border: 1px solid var(--line); border-radius: 10px; background: #fbfbfd; list-style: none; }
.modal-facts li { display: flex; align-items: center; justify-content: space-between; font-size: 12.5px; }
.modal-facts span { color: var(--muted); }
.modal-facts b { font-weight: 500; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; }
.ghost-button { display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; gap: 7px; min-height: 38px; padding: 0 13px; border: 1.5px solid #e7e1f5; border-bottom: 3px solid #dcd3f0; border-radius: 12px; background: white; color: #5b5572; font-size: 13px; font-weight: 650; text-decoration: none; transition: border-color .15s, background .15s, color .15s, transform .12s; }
.ghost-button:hover { border-color: #c9bdf0; background: #f3effd; color: #5b43b0; }
.confirm-button { display: inline-flex; align-items: center; gap: 6px; min-height: 38px; padding: 0 16px; border: 1.5px solid #7960cc; border-bottom: 4px solid #6349b4; border-radius: 12px; background: #8b73dd; color: #fff; font-size: 13.5px; font-weight: 700; transition: background .15s, transform .12s; }
.confirm-button:hover:not(:disabled) { background: #7d64d1; transform: translateY(-1px); }
.confirm-button:disabled, .ghost-button:disabled { opacity: .6; cursor: not-allowed; }
@keyframes fade-in { from { opacity: 0; } }
@keyframes pop-in { from { opacity: 0; transform: translateY(8px) scale(.97); } }
</style>

<template>
  <!-- 场景探索：搜索 / 分类 / 来源筛选 / 场景卡（作者·封面） / 详情弹窗 / 导入导出与互动 -->
  <section class="scenes-page">
    <!-- 工具行：来源筛选 + 创建/导入 -->
    <div class="scenes-toolbar">
      <div class="seg-filter" role="tablist" aria-label="场景来源筛选">
        <button
          v-for="tab in filters"
          :key="tab.key"
          type="button"
          role="tab"
          class="seg-item"
          :class="{ active: filter === tab.key }"
          :aria-selected="filter === tab.key"
          @click="filter = tab.key"
        >
          {{ tab.label }}
          <span class="seg-count">{{ countFor(tab.key) }}</span>
        </button>
      </div>
      <div class="toolbar-actions">
        <button class="ghost-button" type="button" @click="pickImport">
          <AppIcon name="upload" :size="14" />导入场景包
        </button>
        <button class="primary-button slim" type="button" @click="goCreate">
          <AppIcon name="plus" :size="14" />新建场景
        </button>
        <input ref="importInput" type="file" accept=".zip" class="hidden-input" @change="handleImportFile" />
      </div>
    </div>

    <!-- 筛选行：分类 chips + 排序 + 搜索框 -->
    <div class="filter-row">
      <div class="cat-chips" role="group" aria-label="场景分类筛选">
        <button
          v-for="cat in CATEGORIES"
          :key="cat.key"
          type="button"
          class="cat-chip"
          :class="{ active: category === cat.key }"
          @click="category = cat.key"
        >{{ cat.label }}</button>
      </div>
      <div class="filter-right">
        <label class="sort-box">
          <span>排序</span>
          <select v-model="sortBy" aria-label="排序方式">
            <option value="hot">热度最高</option>
            <option value="newest">最新创建</option>
            <option value="downloads">下载最多</option>
            <option value="favorites">收藏最多</option>
          </select>
        </label>
        <label class="search-box">
          <AppIcon name="search" :size="14" />
          <input v-model="keyword" type="search" placeholder="搜索场景名称、描述或标签" />
          <button v-if="keyword" class="search-clear" type="button" aria-label="清空搜索" @click="keyword = ''">
            <AppIcon name="x" :size="12" />
          </button>
        </label>
      </div>
    </div>

    <!-- 卡片网格：入场 stagger 动画 -->
    <div v-if="!initializing" class="scene-grid" key="grid">
      <article
        v-for="(scene, index) in pagedItems"
        :key="scene.id"
        class="scene-card"
        :style="{ animationDelay: `${Math.min(index, 8) * 45}ms` }"
        @click="openDetail(scene)"
      >
        <div class="card-body">
          <header class="card-head">
            <span class="mode-chip" :data-mode="scene.mode">
              <AppIcon :name="modeIcon(scene.mode)" :size="13" />{{ modeLabel(scene.mode) }}
            </span>
            <span class="source-chip" :class="scene.source === 'builtin' ? 'builtin' : scene.status">
              <AppIcon :name="scene.source === 'builtin' ? 'check' : scene.status === 'published' ? 'globe' : 'lock'" :size="12" />
              {{ sourceLabel(scene) }}
            </span>
            <div class="card-menu-anchor">
              <button class="menu-trigger" type="button" :aria-label="`场景 ${scene.name} 的更多操作`" @click.stop="toggleMenu(scene)">
                <AppIcon name="dots" :size="15" />
              </button>
              <transition name="pop">
                <div v-if="menuFor === scene.id" class="card-menu" role="menu" @click.stop>
                  <button v-if="canEdit(scene)" class="menu-item" type="button" @click="goEdit(scene)">
                    <AppIcon name="pencil" :size="13" />编辑
                  </button>
                  <button v-if="session.token" class="menu-item" type="button" @click="doDuplicate(scene)">
                    <AppIcon name="copy" :size="13" />复制为我的场景
                  </button>
                  <button class="menu-item" type="button" @click="doExport(scene)">
                    <AppIcon name="download" :size="13" />导出 ZIP
                  </button>
                  <button v-if="canEdit(scene)" class="menu-item" type="button" @click="doPublishToggle(scene)">
                    <AppIcon :name="scene.status === 'published' ? 'lock' : 'send'" :size="13" />
                    {{ scene.status === 'published' ? '取消发布' : '发布到社区' }}
                  </button>
                  <div v-if="canEdit(scene)" class="menu-divider" aria-hidden="true"></div>
                  <button v-if="canEdit(scene)" class="menu-item danger" type="button" @click.stop="deleteTarget = scene">
                    <AppIcon name="trash" :size="13" />删除
                  </button>
                </div>
              </transition>
            </div>
          </header>

          <h3 class="card-title">{{ scene.name }}</h3>
          <p class="card-desc">{{ scene.description || '作者还没有填写场景描述。' }}</p>

          <div v-if="scene.tags.length" class="card-tags">
            <span v-for="tag in scene.tags.slice(0, 3)" :key="tag" class="tag-chip">{{ tag }}</span>
          </div>

          <!-- 作者行：头像（首字母） + 署名 + 难度 -->
          <div class="card-author">
            <span class="avatar" :style="{ background: avatarColor(scene.author_name) }">{{ avatarInitial(scene.author_name) }}</span>
            <span class="author-name">{{ scene.author_name || 'EchoTalk 官方' }}</span>
            <span v-if="scene.difficulty" class="diff-chip" :class="diffClass(scene.difficulty)">{{ diffLabel(scene.difficulty) }}</span>
          </div>

          <footer class="card-foot">
            <div class="card-meta">
              <span v-if="scene.objective_count" class="meta-item">
                <AppIcon name="target" :size="12" />{{ scene.objective_count }} 个目标
              </span>
              <span v-if="scene.knowledge_count" class="meta-item">
                <AppIcon name="book-open" :size="12" />{{ scene.knowledge_count }} 份资料
              </span>
            </div>
            <div class="card-stats">
              <button
                class="stat-button like"
                type="button"
                :class="{ on: scene.stats?.liked }"
                :aria-pressed="scene.stats?.liked"
                :title="session.token ? '点赞' : '登录后可点赞'"
                @click.stop="toggleLike(scene)"
              >
                <AppIcon name="heart" :size="13" />{{ scene.stats?.likes || 0 }}
              </button>
              <button
                class="stat-button fav"
                type="button"
                :class="{ on: scene.stats?.favorited }"
                :aria-pressed="scene.stats?.favorited"
                :title="session.token ? '收藏' : '登录后可收藏'"
                @click.stop="toggleFavorite(scene)"
              >
                <AppIcon name="star" :size="13" />{{ scene.stats?.favorites || 0 }}
              </button>
              <span class="stat-plain" title="下载次数"><AppIcon name="download" :size="12" />{{ scene.stats?.downloads || 0 }}</span>
            </div>
          </footer>
        </div>
      </article>

      <!-- 空状态：无匹配结果时引导调整筛选 -->
      <div v-if="!filteredItems.length" class="scenes-empty">
        <div class="empty-icon"><AppIcon name="package" :size="22" /></div>
        <h3>{{ emptyTitle }}</h3>
        <p>{{ emptyDesc }}</p>
        <button v-if="filter === 'mine' && !keyword && category === 'all'" class="primary-button slim" type="button" @click="goCreate">
          <AppIcon name="plus" :size="14" />创建第一个场景
        </button>
      </div>
    </div>

    <!-- 分页栏：常驻底部，展示总数与页码（单页时上下页按钮禁用） -->
    <nav v-if="!initializing && filteredItems.length" class="pagination" aria-label="场景分页">
      <span class="page-info">共 {{ filteredItems.length }} 个场景 · 第 {{ page }} / {{ totalPages }} 页</span>
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

    <!-- 全局骨架：首屏加载（独立条件，避免与分页器的 v-if 串联） -->
    <div v-if="initializing" class="scene-grid" aria-busy="true" aria-label="正在加载场景">
      <div v-for="n in 4" :key="n" class="scene-card skeleton">
        <div class="sk-line w40"></div>
        <div class="sk-line w80"></div>
        <div class="sk-line w60"></div>
        <div class="sk-line w70"></div>
      </div>
    </div>

    <!-- 场景详情弹窗：点击卡片打开，展示完整包信息与操作 -->
    <transition name="fade">
      <div v-if="detail" class="modal-backdrop" @click.self="detail = null">
        <div class="detail-card" role="dialog" aria-modal="true" :aria-label="`场景 ${detail.name} 详情`">
          <button class="detail-close" type="button" aria-label="关闭详情" @click="detail = null">
            <AppIcon name="x" :size="15" />
          </button>
          <div v-if="detail.cover_path" class="detail-cover">
            <img :src="coverUrl(detail.id)" alt="" @error="detail.cover_path = null" />
          </div>
          <div class="detail-content">
            <header class="detail-head">
              <h3>{{ detail.name }}</h3>
              <div class="detail-chips">
                <span class="mode-chip" :data-mode="detail.mode">
                  <AppIcon :name="modeIcon(detail.mode)" :size="13" />{{ modeLabel(detail.mode) }}
                </span>
                <span v-if="detail.difficulty" class="diff-chip" :class="diffClass(detail.difficulty)">{{ diffLabel(detail.difficulty) }}</span>
                <span class="cat-chip-static">{{ categoryLabel(detail.category) }}</span>
                <span class="source-chip" :class="detail.source === 'builtin' ? 'builtin' : detail.status">
                  <AppIcon :name="detail.source === 'builtin' ? 'check' : detail.status === 'published' ? 'globe' : 'lock'" :size="12" />
                  {{ sourceLabel(detail) }}
                </span>
              </div>
              <div class="card-author">
                <span class="avatar" :style="{ background: avatarColor(detail.author_name) }">{{ avatarInitial(detail.author_name) }}</span>
                <span class="author-name">{{ detail.author_name || 'EchoTalk 官方' }}</span>
                <span class="author-date" v-if="detail.created_at">创建于 {{ formatDate(detail.created_at) }}</span>
              </div>
            </header>

            <p class="detail-desc">{{ detail.description || '作者还没有填写场景描述。' }}</p>

            <div v-if="detail.tags?.length" class="card-tags">
              <span v-for="tag in detail.tags" :key="tag" class="tag-chip">{{ tag }}</span>
            </div>

            <!-- 角色列表：完整包加载后显示 -->
            <div v-if="detail.package?.roles?.length" class="detail-section">
              <h4>你在和谁对话</h4>
              <div class="role-grid">
                <div v-for="role in detail.package.roles" :key="role.id" class="role-item">
                  <span class="role-name">{{ role.display_name }}</span>
                  <span v-if="role.title" class="role-title">{{ role.title }}</span>
                </div>
              </div>
            </div>

            <!-- 训练目标 -->
            <div v-if="detail.package?.objectives?.length" class="detail-section">
              <h4>训练目标（{{ detail.package.objectives.length }}）</h4>
              <ul class="objective-list">
                <li v-for="objective in detail.package.objectives" :key="objective.id">
                  <AppIcon name="target" :size="13" />{{ objective.label }}
                </li>
              </ul>
            </div>

            <!-- 知识资料 -->
            <div v-if="detail.documents?.length" class="detail-section">
              <h4>场景资料（{{ detail.documents.length }}）</h4>
              <ul class="doc-brief">
                <li v-for="doc in detail.documents" :key="doc.id">
                  <AppIcon name="file-text" :size="13" />{{ doc.filename }}
                  <span class="doc-chunks">{{ doc.chunk_count }} 块</span>
                </li>
              </ul>
            </div>
          </div>

          <!-- 底部操作栏：滚动容器外层，固定贴底不随内容滚动 -->
          <footer class="detail-foot">
            <div class="detail-stats">
              <span class="stat-plain"><AppIcon name="heart" :size="13" />{{ detail.stats?.likes || 0 }}</span>
              <span class="stat-plain"><AppIcon name="star" :size="13" />{{ detail.stats?.favorites || 0 }}</span>
              <span class="stat-plain"><AppIcon name="download" :size="13" />{{ detail.stats?.downloads || 0 }}</span>
            </div>
            <div class="detail-actions">
              <button v-if="canEdit(detail)" class="ghost-button" type="button" @click="goEdit(detail); detail = null">
                <AppIcon name="pencil" :size="13" />编辑
              </button>
              <button v-if="session.token" class="ghost-button" type="button" @click="doDuplicate(detail); detail = null">
                <AppIcon name="copy" :size="13" />复制
              </button>
              <button class="ghost-button" type="button" @click="doExport(detail)">
                <AppIcon name="download" :size="13" />导出
              </button>
              <button class="primary-button slim" type="button" @click="startTraining(detail)">
                <AppIcon name="messages" :size="13" />开始训练
              </button>
            </div>
          </footer>
        </div>
      </div>
    </transition>

    <!-- 删除确认弹窗 -->
    <transition name="fade">
      <div v-if="deleteTarget" class="modal-backdrop" @click.self="deleteTarget = null">
        <div class="modal-card" role="alertdialog" aria-modal="true" aria-label="删除确认">
          <div class="modal-icon danger"><AppIcon name="trash" :size="18" /></div>
          <h3>删除「{{ deleteTarget.name }}」？</h3>
          <p>场景的配置与知识资料会被移除；已开始的训练记录保留快照，此操作无法撤销。</p>
          <div class="modal-actions">
            <button class="ghost-button" type="button" @click="deleteTarget = null">取消</button>
            <button class="danger-button" type="button" @click="doDelete">确认删除</button>
          </div>
        </div>
      </div>
    </transition>

    <!-- 导入冲突弹窗：覆盖 / 改名 / 取消 -->
    <transition name="fade">
      <div v-if="conflict" class="modal-backdrop" @click.self="conflict = null">
        <div class="modal-card" role="alertdialog" aria-modal="true" aria-label="导入冲突">
          <div class="modal-icon"><AppIcon name="package" :size="18" /></div>
          <h3>场景 ID 已存在</h3>
          <p>{{ conflict.message }}</p>
          <div class="modal-actions">
            <button class="ghost-button" type="button" @click="conflict = null">取消</button>
            <button class="ghost-button" type="button" @click="resolveImport('rename')">改名导入</button>
            <button class="primary-button slim" type="button" @click="resolveImport('overwrite')">覆盖现有</button>
          </div>
        </div>
      </div>
    </transition>

    <!-- 轻提示 -->
    <transition name="toast">
      <div v-if="toast" class="toast" role="status">{{ toast }}</div>
    </transition>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { session } from '../auth/session'
import {
  coverUrl, deleteScene, duplicateScene, exportScene, favoriteScene, getScene, importScene,
  likeScene, listScenes, publishScene, unpublishScene,
} from '../api/scenes'

// 场景模式 → 图标与中文标签（卡片左上角徽标）
const MODE_META = {
  conversation: { icon: 'messages', label: '对话' },
  interview: { icon: 'briefcase', label: '面试' },
  debate: { icon: 'messages', label: '辩论' },
}
const modeIcon = (mode) => MODE_META[mode]?.icon || 'messages'
const modeLabel = (mode) => MODE_META[mode]?.label || mode

// 场景分类（与创建向导一致）
const CATEGORIES = [
  { key: 'all', label: '全部' },
  { key: 'daily', label: '日常沟通' },
  { key: 'business', label: '职场沟通' },
  { key: 'career', label: '求职训练' },
  { key: 'academic', label: '学术场景' },
  { key: 'custom', label: '自定义' },
]
const categoryLabel = (key) => CATEGORIES.find((cat) => cat.key === key)?.label || key

const filters = [
  { key: 'all', label: '全部' },
  { key: 'builtin', label: '内置' },
  { key: 'mine', label: '我的' },
  { key: 'community', label: '社区' },
  { key: 'favorited', label: '收藏' },
]

const router = useRouter()
const items = ref([])
const initializing = ref(true)
const filter = ref('all')
const category = ref('all')
const keyword = ref('')
const menuFor = ref(null) // 当前展开菜单的场景 id
const deleteTarget = ref(null) // 删除确认目标
const conflict = ref(null) // { file, message }：导入 ID 冲突弹窗
const detail = ref(null) // 详情弹窗数据（初始为卡片摘要，完整包异步并入）
const toast = ref('')
let toastTimer = null

const notify = (message) => {
  toast.value = message
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.value = ''), 2600)
}

// 来源筛选：mine=本人（含私有）；community=他人已发布；favorited=我收藏的
const isMine = (scene) => session.user && scene.source !== 'builtin' && scene.author_id === session.user.id
const matchesSource = (scene, key) => {
  if (key === 'builtin') return scene.source === 'builtin'
  if (key === 'mine') return isMine(scene)
  if (key === 'community') return scene.source !== 'builtin' && !isMine(scene)
  if (key === 'favorited') return !!scene.stats?.favorited
  return true
}
// 每个 tab 的计数独立计算（修复：此前所有 tab 都显示当前筛选的数量）
const countFor = (key) => items.value.filter((scene) => matchesSource(scene, key)).length
const matchesKeyword = (scene) => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return true
  return [scene.name, scene.description, ...(scene.tags || [])]
    .filter(Boolean)
    .some((field) => String(field).toLowerCase().includes(text))
}
const filteredItems = computed(() =>
  items.value.filter((scene) =>
    matchesSource(scene, filter.value)
    && (category.value === 'all' || scene.category === category.value)
    && matchesKeyword(scene),
  ),
)

// 排序：热度为点赞/收藏/下载的加权综合；同分按创建时间新者优先
const hotScore = (scene) =>
  (scene.stats?.likes || 0) * 3 + (scene.stats?.favorites || 0) * 2 + (scene.stats?.downloads || 0)
const createdTs = (scene) => {
  const ts = new Date(scene.created_at || scene.updated_at || 0).getTime()
  return Number.isFinite(ts) ? ts : 0
}
const SORTERS = {
  hot: { label: '热度最高', fn: (a, b) => hotScore(b) - hotScore(a) || createdTs(b) - createdTs(a) },
  newest: { label: '最新创建', fn: (a, b) => createdTs(b) - createdTs(a) },
  downloads: { label: '下载最多', fn: (a, b) => (b.stats?.downloads || 0) - (a.stats?.downloads || 0) || hotScore(b) - hotScore(a) },
  favorites: { label: '收藏最多', fn: (a, b) => (b.stats?.favorites || 0) - (a.stats?.favorites || 0) || hotScore(b) - hotScore(a) },
}
const sortBy = ref('hot')
const sortedItems = computed(() => {
  const arr = [...filteredItems.value]
  arr.sort(SORTERS[sortBy.value].fn)
  return arr
})

// 分页：客户端分页，筛选/搜索/排序变化时回到第一页
const PAGE_SIZE = 9
const page = ref(1)
const totalPages = computed(() => Math.max(1, Math.ceil(sortedItems.value.length / PAGE_SIZE)))
const pagedItems = computed(() => sortedItems.value.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE))
watch([filter, category, keyword, sortBy], () => { page.value = 1 })
watch(totalPages, (total) => { if (page.value > total) page.value = total }) // 删除场景后收缩页码
const emptyTitle = computed(() => {
  if (keyword.value || category.value !== 'all') return '没有符合条件的内容'
  if (filter.value === 'favorited') return '还没有收藏的场景'
  if (filter.value === 'mine') return '还没有自己的场景'
  return '没有符合条件的内容'
})
const emptyDesc = computed(() => {
  if (keyword.value || category.value !== 'all') {
    return '换个关键词或分类试试，也可以清空筛选查看全部场景。'
  }
  if (filter.value === 'favorited') {
    return '在场景卡上点击收藏图标，常用的场景就会汇集在这里，方便快速开始训练。'
  }
  return '从内置模板复制一份，或从零创建属于你的训练场景；创建后默认仅本地可见，随时可发布。'
})

const canEdit = (scene) => scene.source !== 'builtin' && isMine(scene)
const sourceLabel = (scene) => {
  if (scene.source === 'builtin') return '内置'
  return scene.status === 'published' ? '已发布' : '本地'
}

// 作者头像：首字母 + 按名字哈希取底色（无用户系统头像字段时的轻量方案）
const AVATAR_COLORS = ['#6265e8', '#3d6bc4', '#3e7d5c', '#b8814a', '#b8485a', '#7059b8']
const avatarColor = (name) => {
  const sum = (name || '').split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  return AVATAR_COLORS[sum % AVATAR_COLORS.length]
}
const avatarInitial = (name) => (name || 'E').charAt(0).toUpperCase()
const formatDate = (iso) => new Date(iso).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })

// 难度五级（后端英文枚举存储，前端映射中文标签与配色）
const DIFFICULTIES = {
  entry: { label: '入门', cls: 'entry' },
  easy: { label: '简单', cls: 'easy' },
  normal: { label: '普通', cls: 'normal' },
  hard: { label: '困难', cls: 'hard' },
  expert: { label: '专家', cls: 'expert' },
}
const diffInfo = (value) => DIFFICULTIES[value] || DIFFICULTIES.normal
const diffLabel = (value) => diffInfo(value).label
const diffClass = (value) => diffInfo(value).cls

async function load() {
  initializing.value = true
  try {
    const { data } = await listScenes()
    items.value = data.items
  } catch (error) {
    notify(error.message)
  } finally {
    initializing.value = false
  }
}
onMounted(load)

// 卡片菜单：点击外部关闭
function toggleMenu(scene) {
  menuFor.value = menuFor.value === scene.id ? null : scene.id
}
function onGlobalClick() {
  menuFor.value = null
}
function onEscKey(event) {
  if (event.key === 'Escape') {
    detail.value = null
    deleteTarget.value = null
    conflict.value = null
  }
}
onMounted(() => {
  document.addEventListener('click', onGlobalClick)
  document.addEventListener('keydown', onEscKey)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', onGlobalClick)
  document.removeEventListener('keydown', onEscKey)
})

// 详情弹窗：先用卡片摘要渲染，完整包异步并入同一对象（保持与卡片的引用同步）
async function openDetail(scene) {
  menuFor.value = null
  detail.value = scene
  try {
    const { data } = await getScene(scene.id)
    if (detail.value?.id === scene.id) Object.assign(detail.value, data)
  } catch (error) {
    notify(error.message)
  }
}

function startTraining(scene) {
  notify(`「${scene.name}」的训练功能即将开放，敬请期待。`)
}

function goCreate() {
  if (!session.token) return notify('创建场景需要先登录，点击左下角账户卡片登录。')
  router.push({ name: 'scene-create' })
}
function goEdit(scene) {
  menuFor.value = null
  router.push({ name: 'scene-edit', params: { id: scene.id } })
}

// 导入：无冲突直接成功；冲突时弹窗让用户选覆盖或改名
function pickImport() {
  if (!session.token) return notify('导入场景需要先登录，导入后归入你的场景。')
  importInput.value.click()
}
const importInput = ref(null)
function handleImportFile(event) {
  const file = event.target.files?.[0]
  event.target.value = '' // 允许重复选择同一文件
  if (!file) return
  importScene(file)
    .then(({ data }) => {
      notify(data.action === 'renamed' ? `已改名导入为「${data.scene.name}」` : `导入成功：${data.scene.name}`)
      load()
    })
    .catch((error) => {
      if (error.code === 'SCENE_ID_CONFLICT') {
        conflict.value = { file, message: error.message }
      } else {
        notify(error.message)
      }
    })
}
function resolveImport(resolve) {
  const { file } = conflict.value
  conflict.value = null
  importScene(file, resolve)
    .then(({ data }) => {
      notify(data.action === 'overwritten' ? '已覆盖现有场景' : `已改名导入为「${data.scene.name}」`)
      load()
    })
    .catch((error) => notify(error.message))
}

async function doExport(scene) {
  menuFor.value = null
  try {
    await exportScene(scene.id)
    notify(`已导出「${scene.name}」`)
  } catch (error) {
    notify(error.message)
  }
}

async function doDuplicate(scene) {
  menuFor.value = null
  try {
    const { data } = await duplicateScene(scene.id)
    notify(`已复制为「${data.name}」，可自由编辑`)
    load()
  } catch (error) {
    notify(error.message)
  }
}

async function doDelete() {
  const scene = deleteTarget.value
  deleteTarget.value = null
  try {
    await deleteScene(scene.id)
    items.value = items.value.filter((item) => item.id !== scene.id)
    notify(`已删除「${scene.name}」`)
  } catch (error) {
    notify(error.message)
  }
}

async function doPublishToggle(scene) {
  menuFor.value = null
  try {
    if (scene.status === 'published') {
      await unpublishScene(scene.id)
      scene.status = 'private'
      notify('已取消发布，场景回到本地私有')
    } else {
      await publishScene(scene.id)
      scene.status = 'published'
      notify('已发布到社区，所有用户可查看与下载')
    }
  } catch (error) {
    notify(error.message)
  }
}

// 点赞 / 收藏：游客引导登录；已登录乐观更新，失败回滚
async function toggleLike(scene) {
  if (!session.token) return notify('点赞需要先登录。')
  const liked = scene.stats?.liked
  scene.stats.likes = Math.max(0, (scene.stats.likes || 0) + (liked ? -1 : 1))
  scene.stats.liked = !liked
  try {
    const { data } = await likeScene(scene.id)
    scene.stats.likes = data.likes
    scene.stats.liked = data.liked
  } catch (error) {
    scene.stats.likes = Math.max(0, (scene.stats.likes || 0) + (liked ? 1 : -1))
    scene.stats.liked = liked
    notify(error.message)
  }
}
async function toggleFavorite(scene) {
  if (!session.token) return notify('收藏需要先登录。')
  const favorited = scene.stats?.favorited
  scene.stats.favorites = Math.max(0, (scene.stats.favorites || 0) + (favorited ? -1 : 1))
  scene.stats.favorited = !favorited
  try {
    const { data } = await favoriteScene(scene.id)
    scene.stats.favorites = data.favorites
    scene.stats.favorited = data.favorited
  } catch (error) {
    scene.stats.favorites = Math.max(0, (scene.stats.favorites || 0) + (favorited ? 1 : -1))
    scene.stats.favorited = favorited
    notify(error.message)
  }
}
</script>

<style scoped>
/* 场景探索页样式：沿用全局设计令牌，卡片扁平克制 */
.scenes-page { flex: 1; min-height: 0; display: flex; flex-direction: column; padding: 22px 28px 32px; overflow-y: auto; }

.scenes-toolbar { display: flex; flex: 0 0 auto; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 12px; }
.seg-filter { display: inline-flex; gap: 3px; padding: 3px; border: 1px solid var(--line); border-radius: 9px; background: var(--surface); }
.seg-item { display: inline-flex; align-items: center; gap: 6px; height: 31px; padding: 0 13px; border: 0; border-radius: 7px; background: transparent; color: var(--ink-soft); font-size: 13.5px; transition: background .15s, color .15s; }
.seg-item:hover { color: var(--ink); }
.seg-item.active { background: var(--brand-soft); color: var(--brand-deep, var(--brand)); font-weight: 500; }
.seg-count { color: var(--muted); font-size: 11.5px; }
.seg-item.active .seg-count { color: var(--brand); }
.toolbar-actions { display: flex; align-items: center; gap: 9px; }
.hidden-input { display: none; }

/* 筛选行：分类 chips + 排序 + 搜索 */
.filter-row { display: flex; flex: 0 0 auto; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 16px; }
.filter-right { display: flex; align-items: center; gap: 8px; }
.sort-box { display: inline-flex; flex: 0 0 auto; align-items: center; gap: 7px; height: 34px; padding: 0 10px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--faint); font-size: 13px; transition: border-color .15s, box-shadow .15s; }
.sort-box:focus-within { border-color: var(--brand); box-shadow: 0 0 0 3px rgba(98, 101, 232, .12); }
.sort-box select { border: 0; outline: none; background: transparent; color: var(--ink); font-size: 13.5px; font-family: inherit; cursor: pointer; }
.cat-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.cat-chip { height: 29px; padding: 0 13px; border: 1px solid var(--line); border-radius: 15px; background: var(--surface); color: var(--ink-soft); font-size: 13px; transition: border-color .15s, background .15s, color .15s; }
.cat-chip:hover { border-color: #d5d7e6; color: var(--ink); }
.cat-chip.active { border-color: var(--brand); background: var(--brand-soft); color: var(--brand-deep, var(--brand)); font-weight: 500; }
.search-box { position: relative; display: inline-flex; align-items: center; gap: 7px; width: 260px; height: 34px; padding: 0 10px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--faint); transition: border-color .15s, box-shadow .15s; }
.search-box:focus-within { border-color: var(--brand); box-shadow: 0 0 0 3px rgba(98, 101, 232, .12); }
.search-box input { flex: 1; min-width: 0; border: 0; outline: none; background: transparent; color: var(--ink); font-size: 13.5px; }
.search-box input::placeholder { color: var(--faint); }
.search-box input::-webkit-search-cancel-button { -webkit-appearance: none; appearance: none; display: none; } /* 隐藏原生清除按钮：避免与自绘清除按钮出现两个叉 */
.search-clear { display: grid; place-items: center; width: 18px; height: 18px; border: 0; border-radius: 50%; background: #eef0f5; color: var(--muted); transition: background .15s, color .15s; }
.search-clear:hover { background: #e3e5ee; color: var(--ink); }

.ghost-button { display: inline-flex; align-items: center; gap: 6px; height: 34px; padding: 0 14px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--ink-soft); font-size: 13.5px; transition: border-color .15s, color .15s, background .15s; }
.ghost-button:hover { border-color: #d5d7e6; color: var(--ink); background: #fafafd; }
.primary-button.slim { width: auto; height: 34px; margin-top: 0; gap: 6px; padding: 0 15px; justify-content: center; }
.danger-button { display: inline-flex; align-items: center; height: 34px; padding: 0 15px; border: 0; border-radius: 8px; background: var(--danger); color: #fff; font-size: 13.5px; font-weight: 500; transition: opacity .15s; }
.danger-button:hover { opacity: .9; }

.scene-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; align-content: start; flex: 1 0 auto; }
/* 卡片不裁切（overflow 可见），卡片菜单才能溢出卡片边界显示 */
.scene-card { display: flex; flex-direction: column; border: 1px solid var(--line); border-radius: 12px; background: var(--surface); cursor: pointer; transition: border-color .18s, transform .18s, box-shadow .18s; animation: card-in .38s cubic-bezier(.22, .8, .32, 1) both; }
.scene-card:hover { border-color: #d8daea; transform: translateY(-2px); box-shadow: 0 6px 18px rgba(34, 37, 59, .06); }
@keyframes card-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

.card-body { display: flex; flex-direction: column; flex: 1; padding: 14px 16px 16px; }

.card-head { display: flex; align-items: center; gap: 7px; margin-bottom: 11px; }
.mode-chip, .source-chip { display: inline-flex; align-items: center; gap: 4px; height: 22px; padding: 0 9px; border-radius: 6px; font-size: 11.5px; font-weight: 500; }
.mode-chip { background: var(--brand-soft); color: var(--brand-deep, var(--brand)); }
.source-chip.builtin { background: #e3f2ea; color: #33684b; }
.source-chip.published { background: #e3ecfb; color: #33619f; }
.source-chip.private { background: #eeeff3; color: var(--ink-soft); }
.card-menu-anchor { position: relative; margin-left: auto; }
.menu-trigger { display: grid; width: 24px; height: 24px; place-items: center; border: 0; border-radius: 6px; background: transparent; color: var(--muted); transition: background .15s, color .15s; }
.menu-trigger:hover { background: #f0f1f6; color: var(--ink); }
.card-menu { position: absolute; top: calc(100% + 5px); right: 0; z-index: 12; min-width: 168px; padding: 5px; border: 1px solid var(--line); border-radius: 10px; background: var(--surface); box-shadow: 0 10px 28px rgba(34, 37, 59, .12); }
.menu-item { display: flex; width: 100%; height: 33px; align-items: center; gap: 8px; padding: 0 10px; border: 0; border-radius: 7px; background: transparent; color: var(--ink-soft); font-size: 13.5px; text-align: left; transition: background .12s, color .12s; }
.menu-item:hover { background: #f4f4f9; color: var(--ink); }
.menu-item.danger:hover { background: #fbf1f2; color: var(--danger); }
.menu-divider { height: 1px; margin: 4px 7px; background: var(--line); }

.card-title { margin: 0 0 6px; font-size: 15.5px; font-weight: 600; letter-spacing: -.01em; }
.card-desc { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; margin: 0; min-height: 40px; color: var(--muted); font-size: 13.5px; line-height: 1.55; text-wrap: pretty; }
.card-tags { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 10px; }
.tag-chip { padding: 3px 9px; border-radius: 5px; background: #edeff5; color: var(--ink-soft); font-size: 11.5px; }

/* 作者行 */
/* 作者行：margin-top:auto 与统计栏一起贴卡片底部，保证一排卡片底对齐 */
.card-author { display: flex; align-items: center; gap: 7px; margin-top: auto; padding-top: 12px; }
.avatar { display: grid; width: 22px; height: 22px; flex: 0 0 auto; place-items: center; border-radius: 50%; color: #fff; font-size: 11px; font-weight: 600; }
.author-name { color: var(--ink-soft); font-size: 12.5px; font-weight: 500; }
.author-date { margin-left: auto; color: var(--muted); font-size: 12px; }
.author-date { margin-left: 6px; }
/* 难度五级 chip：入门=绿 / 简单=青绿 / 普通=蓝 / 困难=橙 / 专家=红 */
.card-author .diff-chip { margin-left: auto; }
.diff-chip.entry { background: #e3f2ea; color: #2f7a52; }
.diff-chip.easy { background: #e0f2ef; color: #257a6b; }
.diff-chip.normal { background: #e3ecfb; color: #33619f; }
.diff-chip.hard { background: #fdefe0; color: #b26a24; }
.diff-chip.expert { background: #fbe7e7; color: #b03a3a; }

.card-foot { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 12px; padding-top: 11px; border-top: 1px solid var(--line); }
.card-meta { display: flex; flex-wrap: wrap; gap: 4px 10px; }
.meta-item { display: inline-flex; align-items: center; gap: 4px; color: var(--muted); font-size: 12px; }
.card-stats { display: inline-flex; align-items: center; gap: 3px; }
.stat-button { display: inline-flex; height: 25px; align-items: center; gap: 4px; padding: 0 7px; border: 0; border-radius: 6px; background: transparent; color: var(--muted); font-size: 12px; transition: background .15s, color .15s, transform .1s; }
.stat-button:hover { background: #f2f3f8; color: var(--ink); }
.stat-button:active { transform: scale(.92); }
.stat-button.on { color: var(--brand); }
.stat-button.on svg { fill: currentColor; }
/* 点赞=红 / 收藏=黄（激活态强化，详情统计图标常亮） */
.stat-button.on.like { color: #d6455d; }
.stat-button.on.fav { color: #d9930d; }
.detail-stats .stat-plain:nth-child(1) { color: #d6455d; }
.detail-stats .stat-plain:nth-child(2) { color: #d9930d; }
.stat-plain { display: inline-flex; align-items: center; gap: 4px; margin-left: 3px; color: var(--muted); font-size: 12px; }

.scenes-empty { grid-column: 1 / -1; display: grid; justify-items: center; padding: 46px 20px; border: 1px dashed var(--line); border-radius: 14px; background: rgba(255, 255, 255, .55); text-align: center; }
.empty-icon { display: grid; width: 48px; height: 48px; place-items: center; border: 1px solid #e3e4fb; border-radius: 12px; background: var(--brand-soft); color: var(--brand); }

/* 分页栏：贴底（卡片少时也被 flex 撑到底部），内容靠右集中 */
.pagination { display: flex; flex-wrap: wrap; flex: 0 0 auto; justify-content: flex-end; align-items: center; gap: 6px; margin-top: 20px; padding-top: 14px; border-top: 1px solid var(--line); }
.page-info { color: var(--muted); font-size: 12.5px; margin-right: 8px; }
.page-btn { display: inline-flex; align-items: center; gap: 4px; height: 31px; padding: 0 11px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--ink-soft); font-size: 13px; transition: border-color .15s, color .15s, background .15s; }
.page-btn:hover:not(:disabled):not(.active) { border-color: #d5d7e6; color: var(--ink); }
.page-btn:disabled { opacity: .45; cursor: default; }
.page-num { width: 31px; justify-content: center; padding: 0; }
.page-num.active { border-color: var(--brand); background: var(--brand-soft); color: var(--brand-deep, var(--brand)); font-weight: 500; }
.scenes-empty h3 { margin: 14px 0 6px; font-size: 16px; font-weight: 600; }
.scenes-empty p { margin: 0 0 16px; max-width: 400px; color: var(--muted); font-size: 13.5px; line-height: 1.65; text-wrap: pretty; }

/* 骨架屏 */
.scene-card.skeleton { animation: none; cursor: default; }
.sk-line { height: 12px; margin-top: 10px; border-radius: 5px; background: linear-gradient(90deg, #eef0f5 25%, #f6f7fa 45%, #eef0f5 65%); background-size: 200% 100%; animation: shimmer 1.3s infinite; }
.sk-line.w40 { width: 40%; margin-top: 0; }
.sk-line.w80 { width: 80%; height: 14px; }
.sk-line.w60 { width: 60%; }
.sk-line.w70 { width: 70%; }
@keyframes shimmer { from { background-position: 200% 0; } to { background-position: -200% 0; } }

/* 详情弹窗 */
.modal-backdrop { position: fixed; inset: 0; z-index: 40; display: grid; place-items: center; background: rgba(34, 37, 59, .28); animation: fade-in .18s ease; }
.modal-card { width: min(380px, calc(100vw - 48px)); padding: 24px; border-radius: 14px; background: var(--surface); box-shadow: 0 18px 48px rgba(34, 37, 59, .18); animation: pop-in .22s cubic-bezier(.22, .8, .32, 1); }
.modal-icon { display: grid; width: 38px; height: 38px; margin-bottom: 14px; place-items: center; border-radius: 10px; background: var(--brand-soft); color: var(--brand-deep, var(--brand)); }
.modal-icon.danger { background: #fbf1f2; color: var(--danger); }
.modal-card h3 { margin: 0 0 8px; font-size: 16.5px; font-weight: 600; }
.modal-card p { margin: 0 0 20px; color: var(--muted); font-size: 13.5px; line-height: 1.65; text-wrap: pretty; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; }

.detail-card { position: relative; display: flex; flex-direction: column; width: min(620px, calc(100vw - 48px)); max-height: min(720px, calc(100vh - 96px)); overflow: hidden; border-radius: 16px; background: var(--surface); box-shadow: 0 24px 64px rgba(34, 37, 59, .2); animation: pop-in .22s cubic-bezier(.22, .8, .32, 1); }
.detail-close { position: absolute; top: 12px; right: 12px; z-index: 2; display: grid; width: 28px; height: 28px; place-items: center; border: 0; border-radius: 50%; background: rgba(34, 37, 59, .5); color: #fff; transition: background .15s; }
.detail-close:hover { background: rgba(34, 37, 59, .7); }
.detail-cover { flex: 0 0 auto; aspect-ratio: 21 / 9; overflow: hidden; }
.detail-cover img { display: block; width: 100%; height: 100%; object-fit: cover; }
.detail-content { display: flex; flex-direction: column; flex: 1; min-height: 0; padding: 20px 24px; overflow-y: auto; }
.detail-head h3 { margin: 0 0 10px; font-size: 20px; font-weight: 600; letter-spacing: -.01em; }
.detail-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.diff-chip, .cat-chip-static { display: inline-flex; align-items: center; height: 22px; padding: 0 9px; border-radius: 6px; background: #f1f2f7; color: var(--ink-soft); font-size: 11.5px; font-weight: 500; }
.detail-head .card-author { margin-top: 0; }
.detail-desc { margin: 14px 0 0; color: var(--ink-soft); font-size: 14px; line-height: 1.7; text-wrap: pretty; }
.detail-content .card-tags { margin-top: 12px; }
.detail-section { margin-top: 18px; }
.detail-section h4 { margin: 0 0 9px; color: var(--ink); font-size: 13.5px; font-weight: 600; }
.role-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 8px; }
.role-item { display: flex; flex-direction: column; gap: 2px; padding: 10px 12px; border: 1px solid var(--line); border-radius: 9px; background: #fbfbfd; }
.role-name { color: var(--ink); font-size: 13.5px; font-weight: 600; }
.role-title { color: var(--muted); font-size: 12px; }
.objective-list { margin: 0; padding: 0; list-style: none; }
.objective-list li { display: flex; align-items: center; gap: 7px; padding: 6px 0; color: var(--ink-soft); font-size: 13.5px; }
.objective-list li svg { color: var(--brand); }
.doc-brief { margin: 0; padding: 0; list-style: none; }
.doc-brief li { display: flex; align-items: center; gap: 7px; padding: 5px 0; color: var(--ink-soft); font-size: 13.5px; }
.doc-chunks { margin-left: auto; color: var(--muted); font-size: 12px; }
/* 底部操作栏：位于滚动容器外，固定贴底；自带左右 padding 与分隔线 */
.detail-foot { flex: 0 0 auto; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 24px 16px; border-top: 1px solid var(--line); background: var(--surface); border-radius: 0 0 16px 16px; }
.detail-stats { display: inline-flex; gap: 14px; }
.detail-actions { display: inline-flex; gap: 7px; }

.toast { position: fixed; top: 58px; left: 50%; z-index: 50; max-width: min(460px, calc(100vw - 40px)); padding: 9px 16px; border-radius: 9px; background: #2b2d4e; color: #fff; font-size: 13.5px; box-shadow: 0 10px 28px rgba(34, 37, 59, .22); animation: toast-in .22s cubic-bezier(.22, .8, .32, 1); }
.fade-enter-active, .fade-leave-active { transition: opacity .18s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
@keyframes fade-in { from { opacity: 0; } }
@keyframes pop-in { from { opacity: 0; transform: translateY(8px) scale(.97); } }
@keyframes toast-in { from { opacity: 0; transform: translate(-50%, -6px); } }
.toast-enter-active, .toast-leave-active { transition: opacity .2s, transform .2s; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translate(-50%, -6px); }
.toast { transform: translate(-50%, 0); }

@media (max-width: 860px) {
  .filter-row { flex-direction: column; align-items: stretch; }
  .filter-right { flex-wrap: wrap; }
  .search-box { width: 100%; }
  .detail-foot { flex-direction: column; align-items: stretch; }
  .detail-actions { justify-content: flex-end; }
}
</style>

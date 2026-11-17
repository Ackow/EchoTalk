<template>
  <div class="community-page">
    <section class="page-hero">
      <span class="pill">ScenePackage v2 &amp; Multi-Role Packs</span>
      <h1>场景包社区</h1>
      <p>实时同步后端内置与社区发布的 1v1 场景包及 1vN 多角色群面/辩论包，点击卡片即可预览详情</p>

      <div class="controls">
        <input v-model="searchQuery" class="search-input" type="text" placeholder="搜索场景名称、描述或分类..." />
        <div class="filter-tags">
          <button
            v-for="ft in filterTags"
            :key="ft.key"
            type="button"
            class="filter-tag"
            :class="{ active: activeFilter === ft.key }"
            @click="activeFilter = ft.key"
          >
            {{ ft.label }}
          </button>
        </div>
      </div>
    </section>

    <section class="pack-section">
      <div v-if="loading" class="empty-hint">正在从后端加载场景包列表...</div>
      <div v-else-if="loadError" class="empty-hint">
        无法连接到后端场景服务，请检查服务状态或 <code>VITE_API_BASE_URL</code> 配置
        <div style="margin-top: 12px">
          <button type="button" class="dl-btn" @click="loadFromBackend">重新加载</button>
        </div>
      </div>
      <div v-else-if="filteredPacks.length === 0" class="empty-hint">没有找到匹配的场景包，试试更换筛选条件</div>
      <div v-else class="pack-grid">
        <div
          v-for="pack in filteredPacks"
          :key="`${pack.kind}-${pack.id}`"
          class="tactile-card pack-card"
          @click="openDetail(pack)"
        >
          <div class="pack-cover">
            <img
              v-if="pack.cover && !failedCovers.has(`${pack.kind}-${pack.id}`)"
              :src="pack.cover"
              :alt="pack.title"
              @error="failedCovers.add(`${pack.kind}-${pack.id}`)"
            />
            <div v-else class="cover-fallback">{{ pack.modeLabel }}</div>
            <span class="mode-badge" :class="pack.modeTone">{{ pack.modeLabel }}</span>
          </div>
          <div class="pack-body">
            <div class="pack-head">
              <h3>{{ pack.title }}</h3>
              <span class="tier-badge" :class="pack.tierClass">{{ pack.tier }}</span>
            </div>
            <span class="author">作者：{{ pack.author }} · 难度：{{ pack.difficultyLabel }}</span>
            <p class="card-desc">{{ pack.desc }}</p>
            <div class="card-footer">
              <div class="card-tags">
                <span v-for="tag in pack.tags" :key="tag" class="card-tag">{{ tag }}</span>
              </div>
              <button type="button" class="dl-btn" @click.stop="openDetail(pack)">查看详情</button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 场景详情弹窗 -->
    <div v-if="detailPack" class="modal-backdrop" @click.self="detailPack = null">
      <div class="tactile-card detail-modal">
        <div class="modal-head">
          <div>
            <span class="mode-pill" :class="detailPack.modeTone">{{ detailPack.modeLabel }}</span>
            <span class="tier-badge" :class="detailPack.tierClass" style="margin-left: 6px">{{ detailPack.tier }}</span>
          </div>
          <button type="button" class="close-btn" @click="detailPack = null">×</button>
        </div>

        <img
          v-if="detailPack.cover && !failedCovers.has(`${detailPack.kind}-${detailPack.id}`)"
          :src="detailPack.cover"
          :alt="detailPack.title"
          class="detail-cover"
        />

        <h2>{{ detailPack.title }}</h2>
        <p class="detail-meta">
          作者：{{ detailPack.author }} · 分类：{{ detailPack.categoryLabel }} · 难度：{{ detailPack.difficultyLabel }}
        </p>
        <p class="detail-desc">{{ detailPack.desc }}</p>

        <div v-if="detailLoading" class="detail-loading">正在加载完整配置详情...</div>

        <template v-else-if="detailExtra">
          <!-- 1v1 场景目标与开场白 -->
          <div v-if="detailPack.kind === '1v1'" class="detail-block">
            <div v-if="detailExtra.greeting">
              <h4>开场问候</h4>
              <p class="quote-box">{{ detailExtra.greeting }}</p>
            </div>
            <div v-if="detailExtra.goals?.length">
              <h4>训练目标（{{ detailExtra.goals.length }} 项）</h4>
              <ul class="detail-list">
                <li v-for="g in detailExtra.goals" :key="g.id || g.label">{{ g.label || g.description }}</li>
              </ul>
            </div>
          </div>

          <!-- 1vN 多角色议题与阵容 -->
          <div v-else class="detail-block">
            <div v-if="detailExtra.motionEn">
              <h4>英文核心议题 / 背景</h4>
              <p class="quote-box">{{ detailExtra.motionEn }}</p>
            </div>
            <div v-if="detailExtra.rolesConfig?.length">
              <h4>AI 角色阵容（{{ detailExtra.rolesConfig.length }} 位）</h4>
              <ul class="detail-list">
                <li v-for="r in detailExtra.rolesConfig" :key="r.id || r.name">
                  <b>{{ r.name }}</b>（{{ r.title }}）— {{ r.persona }}
                </li>
              </ul>
            </div>
          </div>
        </template>

        <div class="detail-actions">
          <router-link to="/pricing" class="btn-secondary sm">查看订阅权益</router-link>
          <button type="button" class="btn-primary sm" @click="detailPack = null">在客户端内一键开练</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { apiUrl } from '../config.js'

const searchQuery = ref('')
const activeFilter = ref('all')
const loading = ref(true)
const loadError = ref(false)
const packs = ref([])
const failedCovers = reactive(new Set())
const detailPack = ref(null)
const detailLoading = ref(false)
const detailExtra = ref(null)

const filterTags = [
  { key: 'all', label: '全部场景' },
  { key: '1v1', label: '1v1 语音对话' },
  { key: '1vN', label: '1vN 多角色群面/辩论' },
  { key: 'career', label: '求职面试' },
  { key: 'daily', label: '日常生活' },
]

const DIFF_MAP = {
  entry: '入门',
  easy: '简单',
  normal: '普通',
  hard: '困难',
  expert: '专家',
  beginner: '入门',
  intermediate: '进阶',
  advanced: '高阶',
}

const CAT_MAP = {
  daily: '日常沟通',
  business: '职场商务',
  career: '求职面试',
  academic: '学术研讨',
  tech: '科技伦理',
  workplace: '职场管理',
  custom: '自定义',
}

const filteredPacks = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return packs.value.filter((p) => {
    const matchFilter =
      activeFilter.value === 'all' ||
      p.kind === activeFilter.value ||
      p.category === activeFilter.value
    const matchQ = !q || p.title.toLowerCase().includes(q) || p.desc.toLowerCase().includes(q)
    return matchFilter && matchQ
  })
})

async function loadFromBackend() {
  loading.value = true
  loadError.value = false
  const list = []
  try {
    const [scenesRes, debatesRes] = await Promise.all([
      fetch(apiUrl('/api/scenes')).then((r) => (r.ok ? r.json() : null)),
      fetch(apiUrl('/api/debate/topics')).then((r) => (r.ok ? r.json() : null)),
    ])
    if (!scenesRes && !debatesRes) {
      loadError.value = true
    }

    if (scenesRes?.items?.length) {
      for (const s of scenesRes.items) {
        if (s.source !== 'builtin' && s.status !== 'published') continue
        const tier = (s.required_tier || 'free').toUpperCase()
        list.push({
          id: s.id,
          kind: '1v1',
          title: s.name,
          author: s.source === 'builtin' ? 'EchoTalk 官方' : (s.author?.username || '社区作者'),
          desc: s.description || '沉浸式 1v1 英语语音对话训练场景。',
          category: s.category || 'daily',
          categoryLabel: CAT_MAP[s.category] || s.category || '场景对话',
          difficultyLabel: DIFF_MAP[s.difficulty] || s.difficulty || '普通',
          modeLabel: s.mode === 'interview' ? '1v1 模拟面试' : '1v1 语音对话',
          modeTone: s.mode === 'interview' ? 'mint' : 'purple',
          tier: tier === 'ENTERPRISE' ? 'ENT' : tier,
          tierClass: `tier-${(s.required_tier || 'free').toLowerCase()}`,
          cover: s.source === 'builtin'
            ? `/images/covers/${s.id}.png`
            : (s.cover_path ? apiUrl(`/api/scenes/${s.id}/cover`) : ''),
          tags: [CAT_MAP[s.category] || '场景', `${s.knowledge_count || 0} 份资料`],
          raw: s,
        })
      }
    }

    if (debatesRes?.items?.length) {
      for (const d of debatesRes.items) {
        if (!d.isBuiltin && d.status !== 'published') continue
        const tier = (d.required_tier || 'free').toUpperCase()
        list.push({
          id: d.id,
          kind: '1vN',
          title: d.titleZh || d.title_zh,
          author: d.isBuiltin ? 'EchoTalk 官方' : d.ownerUsername || '社区作者',
          desc: d.motionEn || d.motion_en || '多角色协同交锋与圆桌评审场景。',
          category: d.category || 'career',
          categoryLabel: d.categoryLabel || CAT_MAP[d.category] || '多角色对话',
          difficultyLabel: d.difficultyLabel || DIFF_MAP[d.difficulty] || '进阶',
          modeLabel: d.sceneType === 'panel' ? '1vN 群面圆桌' : '1vN 正反辩论',
          modeTone: 'amber',
          tier: tier === 'ENTERPRISE' ? 'ENT' : tier,
          tierClass: `tier-${(d.required_tier || 'free').toLowerCase()}`,
          cover: d.isBuiltin
            ? `/images/covers/${d.id}.png`
            : apiUrl(d.coverUrl || `/api/debate/topics/${d.id}/cover`),
          tags: [d.sceneType === 'panel' ? '群面委员会' : '辩论对抗', `${(d.rolesConfig || []).length || 3} 位角色`],
          raw: d,
        })
      }
    }
  } catch {
    loadError.value = true
  }

  packs.value = list
  loading.value = false
}

async function openDetail(pack) {
  detailPack.value = pack
  detailExtra.value = null
  if (pack.kind === '1v1' && pack.raw) {
    detailLoading.value = true
    try {
      const res = await fetch(apiUrl(`/api/scenes/${pack.id}`))
      if (res.ok) {
        const data = await res.json()
        const pkg = data.package || {}
        detailExtra.value = {
          greeting: pkg.conversation?.greeting?.text || data.greeting_text || '',
          goals: pkg.goals || [],
        }
      }
    } catch {
      // ignore
    } finally {
      detailLoading.value = false
    }
  } else if (pack.kind === '1vN' && pack.raw) {
    detailExtra.value = {
      motionEn: pack.raw.motionEn || pack.raw.motion_en,
      rolesConfig: pack.raw.rolesConfig || pack.raw.roles_config || [],
    }
  }
}

onMounted(loadFromBackend)
</script>

<style scoped>
.community-page { max-width: 1180px; margin: 0 auto; padding: 104px 24px 64px; }
.page-hero { text-align: center; max-width: 740px; margin: 0 auto 36px; }
.pill { display: inline-block; padding: 4px 12px; border-radius: 999px; background: #eee9ff; color: var(--primary-ink); font-size: 12px; font-weight: 700; margin-bottom: 10px; }
.page-hero h1 { font-size: 34px; font-weight: 900; margin-bottom: 8px; }
.page-hero p { font-size: 14.5px; color: var(--text-muted); margin-bottom: 20px; }
.controls { display: flex; flex-direction: column; align-items: center; gap: 12px; }
.search-input { width: 100%; max-width: 440px; padding: 10px 16px; border-radius: 12px; border: 1.5px solid var(--border); background: #ffffff; font-size: 14px; outline: none; }
.search-input:focus { border-color: var(--primary); }
.filter-tags { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; }
.filter-tag { border: 1.5px solid var(--border); background: #ffffff; color: var(--text-soft); padding: 6px 14px; border-radius: 999px; font-size: 12.5px; font-weight: 600; cursor: pointer; }
.filter-tag.active { border-color: var(--primary); background: #eee9ff; color: var(--primary-ink); }

.pack-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; margin-bottom: 48px; }
.pack-card { overflow: hidden; display: flex; flex-direction: column; cursor: pointer; transition: transform 0.16s; }
.pack-card:hover { transform: translateY(-3px); }
@media (prefers-reduced-motion: reduce) {
  .pack-card { transition: none; }
  .pack-card:hover { transform: none; }
}
.pack-cover { position: relative; height: 156px; background: #f3eeff; }
.pack-cover img { width: 100%; height: 100%; object-fit: cover; }
.cover-fallback { height: 100%; display: grid; place-items: center; color: var(--primary-ink); font-weight: 700; font-size: 14px; }
.mode-badge { position: absolute; top: 10px; left: 10px; padding: 3px 9px; border-radius: 999px; font-size: 11px; font-weight: 800; background: rgba(255, 255, 255, 0.94); }
.mode-badge.purple { color: #6046b4; }
.mode-badge.mint { color: #2a8c5f; }
.mode-badge.amber { color: #b45309; }
.pack-body { padding: 18px; display: flex; flex-direction: column; flex: 1; }
.pack-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; margin-bottom: 4px; }
.pack-head h3 { font-size: 16px; line-height: 1.35; }
.tier-badge { padding: 2px 8px; border-radius: 999px; font-size: 10px; font-weight: 800; flex-shrink: 0; }
.tier-free { background: #eaf7f0; color: #2a8c5f; }
.tier-pro { background: #eee9ff; color: #6046b4; }
.tier-enterprise { background: #2f2a45; color: #ffd670; }
.author { font-size: 12px; color: var(--text-dim); margin-bottom: 8px; }
.card-desc { font-size: 13px; color: var(--text-muted); flex: 1; margin-bottom: 14px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.card-footer { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.card-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.card-tag { font-size: 11px; padding: 2px 8px; border-radius: 6px; background: #f5f3ff; color: var(--primary-ink); font-weight: 600; }
.dl-btn { border: none; padding: 6px 12px; border-radius: 9px; background: var(--primary); color: #ffffff; font-size: 12px; font-weight: 700; cursor: pointer; }
.empty-hint { text-align: center; padding: 48px; color: var(--text-muted); }

.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 120;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(34, 37, 59, 0.32);
  backdrop-filter: blur(3px);
}
.detail-modal { width: min(620px, 95vw); max-height: 88vh; overflow-y: auto; padding: 24px; }
.modal-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.mode-pill { padding: 3px 10px; border-radius: 999px; font-size: 11px; font-weight: 800; background: #eee9ff; color: #6046b4; }
.close-btn { border: 1px solid var(--border); background: #faf9fd; width: 30px; height: 30px; border-radius: 8px; font-size: 18px; cursor: pointer; }
.detail-cover { width: 100%; height: 200px; object-fit: cover; border-radius: 12px; margin-bottom: 14px; }
.detail-modal h2 { font-size: 22px; margin-bottom: 6px; }
.detail-meta { font-size: 12.5px; color: var(--text-dim); margin-bottom: 10px; }
.detail-desc { font-size: 14px; color: var(--text-soft); margin-bottom: 16px; }
.detail-loading { font-size: 13px; color: var(--text-muted); padding: 12px 0; }
.detail-block h4 { font-size: 13.5px; color: var(--primary-ink); margin: 12px 0 6px; }
.quote-box { background: #f6f3ff; border-radius: 10px; padding: 10px 14px; font-size: 13px; color: var(--text); }
.detail-list { padding-left: 18px; font-size: 13px; color: var(--text-soft); display: flex; flex-direction: column; gap: 4px; }
.detail-actions { margin-top: 20px; display: flex; justify-content: flex-end; gap: 10px; }
.btn-primary.sm, .btn-secondary.sm { padding: 8px 16px; font-size: 13px; border-radius: 10px; }

@media (max-width: 900px) { .pack-grid { grid-template-columns: 1fr; } }
</style>

<template>
  <div class="community-page">
    <!-- Hero -->
    <section class="page-hero">
      <div class="inner">
        <h1>📦 场景包社区</h1>
        <p>发现、下载、分享由社区贡献的场景包，拓展你的口语练习内容</p>
        <div class="search-bar">
          <input
            class="search-input"
            type="text"
            placeholder="搜索场景包..."
            v-model="searchQuery"
          />
        </div>
        <div class="filter-tags">
          <span
            v-for="ft in filterTags"
            :key="ft.key"
            class="filter-tag"
            :class="{ active: activeFilter === ft.key }"
            @click="setFilter(ft.key)"
          >{{ ft.label }}</span>
        </div>
      </div>
    </section>

    <!-- Pack Grid -->
    <section class="pack-section">
      <!-- 加载中占位 -->
      <div v-if="loading" class="loading-hint">
        <p>正在加载场景包列表...</p>
      </div>

      <!-- 无结果 -->
      <div v-else-if="filteredPacks.length === 0" class="empty-hint">
        <p>😕 没有找到匹配的场景包，试试换个关键词或筛选条件</p>
      </div>

      <!-- 场景包网格 -->
      <div v-else class="pack-grid">
        <div
          v-for="pack in filteredPacks"
          :key="pack.id"
          class="pack-card"
          :class="{ featured: pack.featured }"
        >
          <div class="card-header">
            <span class="card-emoji">{{ pack.emoji }}</span>
            <div class="card-meta">
              <h3>
                {{ pack.title }}
                <span v-if="pack.featured" class="featured-badge">内置</span>
              </h3>
              <span class="author">by {{ pack.author }}</span>
            </div>
          </div>
          <p class="card-desc">{{ pack.desc }}</p>
          <div class="card-footer">
            <div class="card-tags">
              <span
                v-for="tag in pack.tags"
                :key="tag"
                class="card-tag"
                :class="tag"
              >{{ tagLabels[tag] || tag }}</span>
            </div>
            <div class="card-stats">
              <span>⭐ {{ pack.rating }}</span>
              <span>📥 {{ pack.downloads }}</span>
              <a v-if="pack.downloadUrl" :href="pack.downloadUrl" class="dl-btn" @click.stop>下载</a>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA Banner -->
    <section class="cta-banner">
      <div class="cta-inner">
        <h3>📝 分享你的场景包</h3>
        <p>编写一个场景插件（Python），在 EchoTalk 中导出为 .zip 包，发布到社区，帮助更多人练习英语口语。</p>
        <div class="cta-actions">
          <router-link to="/docs#scene-dev" class="btn-primary">📖 开发指南</router-link>
          <a href="https://github.com/IceColaaa/EchoTalk" target="_blank" class="btn-secondary">🐙 GitHub 仓库</a>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const searchQuery = ref('')
const activeFilter = ref('all')
const packs = ref([])
const loading = ref(true)

const filterTags = [
  { key: 'all', label: '全部' },
  { key: 'daily', label: '日常对话' },
  { key: 'interview', label: '面试求职' },
  { key: 'business', label: '商务职场' },
  { key: 'travel', label: '旅行出行' },
  { key: 'food', label: '美食餐饮' },
  { key: 'tech', label: '科技行业' },
  { key: 'culture', label: '文化社交' },
]

const tagLabels = {
  interview: '面试',
  daily: '日常',
  business: '商务',
  travel: '旅行',
  food: '餐饮',
  tech: '技术',
  culture: '社交',
}

onMounted(async () => {
  try {
    const res = await fetch('/packages.json')
    if (res.ok) {
      packs.value = await res.json()
    }
  } catch (e) {
    console.warn('无法加载场景包列表，请检查 public/packages.json 是否存在')
  } finally {
    loading.value = false
  }
})

const filteredPacks = computed(() => {
  const query = searchQuery.value.toLowerCase().trim()
  return packs.value.filter(pack => {
    const matchTag = activeFilter.value === 'all' || pack.tags.includes(activeFilter.value)
    const matchSearch = !query || pack.title.toLowerCase().includes(query) || pack.desc.toLowerCase().includes(query)
    return matchTag && matchSearch
  })
})

function setFilter(key) {
  activeFilter.value = key
}
</script>

<style scoped>
.page-hero { padding: 120px 24px 60px; text-align: center; position: relative; }
.page-hero::before { content: ''; position: absolute; inset: 0; pointer-events: none; background: radial-gradient(ellipse 60% 40% at 50% 40%, rgba(99,102,241,0.08) 0%, transparent 70%); }
.page-hero .inner { position: relative; max-width: 640px; margin: 0 auto; }
.page-hero h1 { font-size: clamp(2.4rem, 4.5vw, 3.2rem); font-weight: 800; margin-bottom: 16px; }
.page-hero p { font-size: 1.15rem; color: var(--text-muted); margin-bottom: 28px; }

.search-bar { max-width: 560px; margin: 0 auto 16px; display: flex; gap: 12px; }
.search-input { flex: 1; padding: 14px 20px; border-radius: 10px; background: var(--bg-card); border: 1px solid var(--border); color: var(--text); font-size: 1rem; font-family: var(--font); outline: none; transition: border-color 0.2s; }
.search-input::placeholder { color: var(--text-dim); }
.search-input:focus { border-color: var(--primary); }

.filter-tags { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; margin-top: 16px; }
.filter-tag { padding: 8px 18px; border-radius: 99px; font-size: 0.9rem; font-weight: 600; background: var(--bg-card); border: 1px solid var(--border); color: var(--text-muted); cursor: pointer; transition: all 0.15s; user-select: none; }
.filter-tag:hover, .filter-tag.active { background: rgba(99,102,241,0.12); border-color: var(--primary); color: var(--primary); }

.pack-section { max-width: 1200px; margin: 0 auto; padding: 24px 24px 60px; }
.pack-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }

.pack-card { padding: 28px; border-radius: var(--radius); background: var(--bg-card); border: 1px solid var(--border); transition: transform 0.2s, border-color 0.2s, background 0.2s; position: relative; overflow: hidden; display: flex; flex-direction: column; text-align: center; }
.pack-card:hover { transform: translateY(-3px); border-color: rgba(99,102,241,0.2); background: var(--bg-card-hover); }
.pack-card .card-header { display: flex; flex-direction: column; align-items: center; gap: 10px; margin-bottom: 14px; }
.pack-card .card-emoji { font-size: 2.4rem; }
.pack-card .card-meta { }
.pack-card .card-meta h3 { font-size: 1.15rem; font-weight: 700; margin-bottom: 4px; display: flex; align-items: center; justify-content: center; gap: 8px; }
.pack-card .card-meta .author { font-size: 0.88rem; color: var(--text-dim); }
.pack-card .card-desc { font-size: 0.95rem; color: var(--text-muted); line-height: 1.65; margin-bottom: 16px; flex: 1; }
.pack-card .card-footer { display: flex; align-items: center; justify-content: center; gap: 16px; flex-wrap: wrap; margin-top: auto; }
.pack-card .card-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.pack-card .card-tag { padding: 4px 10px; border-radius: 6px; font-size: 0.78rem; font-weight: 600; }
.card-tag.interview { background: rgba(99,102,241,0.1); color: var(--primary); }
.card-tag.daily    { background: rgba(16,185,129,0.1); color: var(--green); }
.card-tag.business { background: rgba(59,130,246,0.1); color: var(--blue); }
.card-tag.travel   { background: rgba(245,158,11,0.1); color: var(--amber); }
.card-tag.food     { background: rgba(236,72,153,0.1); color: var(--pink); }
.card-tag.tech     { background: rgba(6,182,212,0.1); color: var(--cyan); }
.card-tag.culture  { background: rgba(168,85,247,0.1); color: #a855f7; }
.pack-card .card-stats { display: flex; align-items: center; gap: 14px; font-size: 0.88rem; color: var(--text-dim); }
.pack-card .card-stats span { display: flex; align-items: center; gap: 4px; }
.dl-btn { margin-left: 8px; padding: 5px 16px; border-radius: 6px; font-size: 0.85rem; font-weight: 600; background: rgba(99,102,241,0.15); color: var(--primary); transition: background 0.15s; }
.dl-btn:hover { background: rgba(99,102,241,0.25); }

.pack-card.featured { border-color: rgba(99,102,241,0.25); background: linear-gradient(135deg, rgba(99,102,241,0.06) 0%, rgba(59,130,246,0.03) 100%); }
.pack-card.featured::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, var(--primary), var(--blue)); }
.featured-badge { display: inline-block; padding: 3px 10px; border-radius: 4px; font-size: 0.72rem; font-weight: 700; background: rgba(99,102,241,0.15); color: var(--primary); text-transform: uppercase; letter-spacing: 0.08em; }

.loading-hint, .empty-hint { text-align: center; padding: 80px 24px; }
.loading-hint p, .empty-hint p { font-size: 1.1rem; color: var(--text-dim); }

.cta-banner { max-width: 1200px; margin: 0 auto; padding: 0 24px 80px; }
.cta-inner { padding: 52px; border-radius: var(--radius); background: linear-gradient(135deg, rgba(99,102,241,0.1) 0%, rgba(59,130,246,0.06) 100%); border: 1px solid rgba(99,102,241,0.15); text-align: center; }
.cta-inner h3 { font-size: 1.6rem; font-weight: 800; margin-bottom: 14px; }
.cta-inner p { font-size: 1.05rem; color: var(--text-muted); margin-bottom: 24px; max-width: 520px; margin-left: auto; margin-right: auto; }
.cta-inner .cta-actions { display: flex; gap: 12px; justify-content: center; }

@media (max-width: 768px) { .page-hero { padding: 100px 16px 40px; } .pack-grid { grid-template-columns: 1fr; } .cta-inner { padding: 32px 20px; } }
</style>

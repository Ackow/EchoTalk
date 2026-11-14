<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { marked } from 'marked'
import AppIcon from '../AppIcon.vue'
import { getPracticeKnowledge } from '../../api/scenes'

const props = defineProps({
  sceneId: { type: String, required: true },
  description: { type: String, default: '' },
  goals: { type: Array, default: () => [] },
})
const emit = defineEmits(['close'])

const THEMES = [
  { id: 'auto', label: '自动匹配' },
  { id: 'cafe_menu', label: '菜单看板' },
  { id: 'transit_board', label: '出行电子屏' },
  { id: 'job_brief', label: '职位简报' },
  { id: 'hotel_guide', label: '酒店指南' },
  { id: 'article', label: '文档阅读' },
]

const documents = ref([])
const activeDoc = ref(0)
const activeSection = ref('all')
const themeOverride = ref('auto')
const loading = ref(false)
const error = ref('')
const query = ref('')
let generation = 0
let request = null

const points = computed(() => documents.value.flatMap(doc => doc.sections))

const currentDoc = computed(() => documents.value[activeDoc.value] || null)

function detectTheme(doc) {
  if (!doc) return 'article'
  const fullText = doc.sections.map(s => `${s.name}\n${s.chunks.map(c => c.text).join('\n')}`).join('\n')
  const directive = fullText.match(/(?:<!--\s*theme:\s*([a-z_]+)\s*-->|^theme:\s*([a-z_]+))/im)
  const explicit = (directive?.[1] || directive?.[2] || '').toLowerCase()
  if (THEMES.some(t => t.id === explicit && t.id !== 'auto')) return explicit

  const hay = `${props.sceneId} ${doc.filename} ${fullText}`.toLowerCase()
  if (/menu|cafe|coffee|espresso|latte|croissant|pastry|drinks|barista/.test(hay)) return 'cafe_menu'
  if (/airport|flight|boarding|train|station|ticket|rebook|gate|platform|departure/.test(hay)) return 'transit_board'
  if (/interview|jd\.md|engineer|requirements|responsibilities|qualifications|tech_interview/.test(hay)) return 'job_brief'
  if (/hotel|check-?in|room|suite|concierge|breakfast|wifi/.test(hay)) return 'hotel_guide'
  return 'article'
}

const activeTheme = computed(() => {
  if (themeOverride.value !== 'auto') return themeOverride.value
  return detectTheme(currentDoc.value)
})

function escapeHtml(text) {
  return String(text || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function highlightText(text, term) {
  const safe = escapeHtml(text)
  if (!term) return safe
  const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return safe.replace(new RegExp(`(${escaped})`, 'gi'), '<mark>$1</mark>')
}

function stripMarkdown(line) {
  return line
    .replace(/^[-*+]\s+/, '')
    .replace(/^>\s*/, '')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/`(.*?)`/g, '$1')
    .trim()
}

// 解析菜单结构：自动合并 prices 节里的价格到对应饮品/糕点条目，并提取套餐提示（> 引用块）
const parsedCafeMenu = computed(() => {
  const doc = currentDoc.value
  if (!doc) return { title: 'Daily Menu', groups: [], combos: [] }
  const priceMap = new Map()
  const groups = []
  const combos = []
  let title = 'Daily Menu'

  for (const sec of doc.sections) {
    const rawLines = sec.chunks.flatMap(c => c.text.split('\n')).map(l => l.trim()).filter(Boolean)
    const secName = sec.name === '_' ? '' : sec.name
    if (secName.toLowerCase() === 'prices') {
      for (const line of rawLines) {
        if (line.startsWith('>')) {
          combos.push(stripMarkdown(line))
          continue
        }
        const cleaned = stripMarkdown(line)
        const m = cleaned.match(/^([^:：]+)[:：]\s*(.+)$/)
        if (m) {
          priceMap.set(m[1].trim().toLowerCase(), m[2].trim())
        }
      }
      continue
    }
    const items = []
    for (const line of rawLines) {
      if (line.startsWith('# ')) {
        title = line.replace(/^#\s+/, '').trim()
        continue
      }
      if (line.startsWith('>')) {
        combos.push(stripMarkdown(line))
        continue
      }
      if (!/^[-*+]/.test(line) && !line.includes('—') && !line.includes(':')) continue
      const cleaned = stripMarkdown(line)
      const parts = cleaned.split(/\s*[—–-]{1,2}\s*|\s*:\s*/)
      const name = (parts[0] || cleaned).trim()
      const desc = parts.slice(1).join(' · ').trim()
      const priceMatch = cleaned.match(/\$\d+(?:\.\d{2})?/)
      items.push({ name, desc, price: priceMatch ? priceMatch[0] : '' })
    }
    if (items.length) {
      groups.push({ name: secName || 'Menu', items })
    }
  }

  // 把 prices 映射回对应菜品
  for (const g of groups) {
    for (const item of g.items) {
      if (item.price) continue
      const lower = item.name.toLowerCase()
      for (const [k, v] of priceMap.entries()) {
        if (lower.includes(k) || k.includes(lower)) {
          item.price = v
          break
        }
      }
    }
  }

  const term = query.value.trim().toLowerCase()
  const secFilter = activeSection.value
  const filteredGroups = groups
    .filter(g => secFilter === 'all' || g.name === secFilter)
    .map(g => ({
      ...g,
      items: g.items.filter(it => !term || `${it.name} ${it.desc} ${it.price}`.toLowerCase().includes(term)),
    }))
    .filter(g => g.items.length > 0)

  return { title, groups: filteredGroups, combos }
})

function menuItemKind(name) {
  const n = name.toLowerCase()
  if (/iced|cold brew|juice|orange/.test(n)) return 'cold'
  if (/tea/.test(n)) return 'tea'
  if (/croissant|muffin|bread|cookie|cake|roll|pastry/.test(n)) return 'pastry'
  return 'coffee'
}

// 通用结构化条目（供 transit_board / job_brief / hotel_guide / article 使用，支持条目级搜索过滤）
const sectionNames = computed(() => {
  const doc = currentDoc.value
  if (!doc) return []
  return doc.sections.map(s => s.name).filter(n => n && n !== '_' && n.toLowerCase() !== 'prices')
})

const filteredSections = computed(() => {
  const doc = currentDoc.value
  if (!doc) return []
  const term = query.value.trim().toLowerCase()
  const secFilter = activeSection.value

  return doc.sections
    .filter(sec => secFilter === 'all' || sec.name === secFilter)
    .map(sec => {
      const rawText = sec.chunks.map(c => c.text).join('\n\n')
      const lines = rawText.split('\n').map(l => l.trim()).filter(Boolean)
      const matchedLines = term
        ? lines.filter(l => stripMarkdown(l).toLowerCase().includes(term) || sec.name.toLowerCase().includes(term))
        : lines
      if (term && !matchedLines.length) return null
      const mdSource = term ? matchedLines.join('\n') : rawText
      let html = marked.parse(mdSource, { breaks: true, async: false })
      if (term) {
        const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
        // 只高亮文本节点内容，避免破坏 HTML 标签
        html = html.replace(/(>[^<]+<)/g, seg => seg.replace(new RegExp(`(${escaped})`, 'gi'), '<mark>$1</mark>'))
      }
      return {
        key: `${doc.id}:${sec.name}`,
        name: sec.name,
        lines: matchedLines.map(stripMarkdown),
        html,
      }
    })
    .filter(Boolean)
})

function extractTagOrValue(line) {
  const statusMatch = line.match(/\b(ON TIME|BOARDING|DELAYED|GATE\s*[A-Z0-9]+|PLATFORM\s*[A-Z0-9]+)\b/i)
  const timeMatch = line.match(/\b\d{1,2}:\d{2}(?:\s*(?:AM|PM))?(?:\s*(?:->|→|-)\s*\d{1,2}:\d{2}(?:\s*(?:AM|PM))?)?/i)
  const priceMatch = line.match(/\$\d+(?:\.\d{2})?/)
  return {
    status: statusMatch ? statusMatch[0].toUpperCase() : '',
    time: timeMatch ? timeMatch[0] : '',
    price: priceMatch ? priceMatch[0] : '',
  }
}

async function load() {
  const current = ++generation
  request?.abort()
  request = new AbortController()
  documents.value = []
  activeDoc.value = 0
  activeSection.value = 'all'
  themeOverride.value = 'auto'
  error.value = ''
  loading.value = true
  try {
    const { data } = await getPracticeKnowledge(props.sceneId, request.signal)
    if (current === generation) documents.value = data.documents || []
  } catch (failure) {
    if (current === generation) error.value = failure.message || '知识点加载失败'
  } finally {
    if (current === generation) loading.value = false
  }
}

watch(() => props.sceneId, () => { query.value = ''; activeDoc.value = 0; activeSection.value = 'all'; load() }, { immediate: true })
watch(activeDoc, () => { activeSection.value = 'all' })
onBeforeUnmount(() => { generation += 1; request?.abort() })
</script>

<template>
  <aside class="knowledge-dock" :class="`theme-${activeTheme}`" aria-label="场景参考资料">
    <header class="k-head">
      <div class="k-title">
        <AppIcon name="book-open" :size="15" />
        <h3>场景参考板</h3>
        <span v-if="!loading && !error">{{ points.length }} 节</span>
      </div>
      <div class="k-head-actions">
        <select v-model="themeOverride" class="k-theme-select" aria-label="切换展示主题" title="切换参考板展示风格">
          <option v-for="t in THEMES" :key="t.id" :value="t.id">{{ t.label }}</option>
        </select>
        <button class="k-close" type="button" aria-label="收起参考板" @click="emit('close')">
          <AppIcon name="x" :size="15" />
        </button>
      </div>
    </header>

    <p v-if="description" class="k-desc">{{ description }}</p>

    <p v-if="loading" class="k-notice" role="status"><AppIcon name="loader" :size="14" />正在加载参考资料…</p>
    <div v-else-if="error" class="k-error" role="alert">
      <p>{{ error }}</p>
      <button type="button" @click="load"><AppIcon name="rotate" :size="13" />重新加载</button>
    </div>

    <template v-else-if="points.length">
      <nav v-if="documents.length > 1" class="k-tabs" aria-label="资料模块">
        <button
          v-for="(doc, index) in documents"
          :key="doc.id"
          type="button"
          :class="{ active: activeDoc === index }"
          @click="activeDoc = index"
        >
          {{ doc.filename.replace(/\.md$/i, '') }}
        </button>
      </nav>

      <div class="k-toolbar">
        <label class="k-search">
          <AppIcon name="search" :size="13" />
          <input v-model="query" type="search" aria-label="筛选条目" placeholder="搜索关键词（如 Latte、oat、$6.50）" />
        </label>
        <div v-if="sectionNames.length > 1" class="k-pills">
          <button type="button" :class="{ active: activeSection === 'all' }" @click="activeSection = 'all'">全部</button>
          <button
            v-for="secName in sectionNames"
            :key="secName"
            type="button"
            :class="{ active: activeSection === secName }"
            @click="activeSection = secName"
          >
            {{ secName }}
          </button>
        </div>
      </div>

      <div class="k-body">
        <!-- 主题 1：咖啡厅 / 餐厅仿真菜单 -->
        <div v-if="activeTheme === 'cafe_menu'" class="menu-board">
          <div class="menu-marquee">
            <span class="menu-kicker">TODAY'S MENU</span>
            <h4>{{ parsedCafeMenu.title }}</h4>
          </div>

          <div v-for="group in parsedCafeMenu.groups" :key="group.name" class="menu-group">
            <div class="menu-group-head">
              <span>{{ group.name }}</span>
            </div>
            <ul class="menu-items">
              <li v-for="item in group.items" :key="item.name" class="menu-item">
                <span class="menu-thumb" :class="`is-${menuItemKind(item.name)}`" aria-hidden="true">
                  <svg v-if="menuItemKind(item.name) === 'pastry'" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 16.5c0-4.5 3.5-8 7.5-8s7.5 3.5 7.5 8"/><path d="M3 16.5h18"/><path d="M8 8.5 7 5"/><path d="M16 8.5 17 5"/></svg>
                  <svg v-else-if="menuItemKind(item.name) === 'cold'" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M7 6h10l-1.2 14H8.2L7 6Z"/><path d="M10 6V3l3-1"/><path d="M7.5 11h9"/></svg>
                  <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17 8h1a4 4 0 1 1 0 8h-1"/><path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z"/><path d="M6 2v3"/><path d="M10 2v3"/></svg>
                </span>
                <div class="menu-item-main">
                  <div class="menu-item-top">
                    <b v-html="highlightText(item.name, query.trim())"></b>
                    <span class="menu-leader" aria-hidden="true"></span>
                    <strong v-if="item.price" class="menu-price" v-html="highlightText(item.price, query.trim())"></strong>
                  </div>
                  <p v-if="item.desc" v-html="highlightText(item.desc, query.trim())"></p>
                </div>
              </li>
            </ul>
          </div>

          <div v-for="(combo, idx) in parsedCafeMenu.combos" :key="idx" class="menu-combo">
            <AppIcon name="sparkles" :size="13" />
            <span v-html="highlightText(combo, query.trim())"></span>
          </div>

          <p v-if="!parsedCafeMenu.groups.length" class="k-notice">没有匹配的菜单项，试试其他关键词。</p>
        </div>

        <!-- 主题 2：车站 / 机场电子屏 & 车票卡片 -->
        <div v-else-if="activeTheme === 'transit_board'" class="transit-board">
          <div class="transit-screen">
            <div class="transit-screen-head">
              <span>DEPARTURES &amp; BOARDING</span>
              <span class="transit-live"><i />LIVE</span>
            </div>
            <div v-for="sec in filteredSections" :key="sec.key" class="transit-group">
              <div v-if="sec.name !== '_'" class="transit-sec-title">{{ sec.name }}</div>
              <div v-for="(line, i) in sec.lines" :key="i" class="transit-ticket">
                <div class="ticket-main" v-html="highlightText(line, query.trim())"></div>
                <div v-if="extractTagOrValue(line).time || extractTagOrValue(line).status" class="ticket-meta">
                  <span v-if="extractTagOrValue(line).time" class="ticket-time">{{ extractTagOrValue(line).time }}</span>
                  <span v-if="extractTagOrValue(line).status" class="ticket-status">{{ extractTagOrValue(line).status }}</span>
                </div>
              </div>
            </div>
          </div>
          <p v-if="!filteredSections.length" class="k-notice">没有匹配的车次/航班信息。</p>
        </div>

        <!-- 主题 3：求职面试简报 -->
        <div v-else-if="activeTheme === 'job_brief'" class="brief-board">
          <section v-for="sec in filteredSections" :key="sec.key" class="brief-card">
            <header v-if="sec.name !== '_'">
              <span class="brief-pill">{{ sec.name }}</span>
            </header>
            <div class="k-md" v-html="sec.html"></div>
          </section>
          <p v-if="!filteredSections.length" class="k-notice">没有匹配的职位要点。</p>
        </div>

        <!-- 主题 4：酒店入住指南 -->
        <div v-else-if="activeTheme === 'hotel_guide'" class="hotel-board">
          <section v-for="sec in filteredSections" :key="sec.key" class="hotel-card">
            <h4 v-if="sec.name !== '_'"><AppIcon name="sparkles" :size="12" />{{ sec.name }}</h4>
            <div class="k-md" v-html="sec.html"></div>
          </section>
          <p v-if="!filteredSections.length" class="k-notice">没有匹配的酒店信息。</p>
        </div>

        <!-- 主题 5：美化版通用文档阅读 -->
        <div v-else class="article-board">
          <section v-for="sec in filteredSections" :key="sec.key" class="article-card">
            <h4 v-if="sec.name !== '_'">{{ sec.name }}</h4>
            <div class="k-md" v-html="sec.html"></div>
          </section>
          <p v-if="!filteredSections.length" class="k-notice">没有匹配的知识点，试试其他关键词。</p>
        </div>
      </div>
    </template>

    <div v-else class="k-body k-empty">
      <h4>本场景练习目标</h4>
      <ul v-if="goals.length"><li v-for="goal in goals" :key="goal.id">{{ goal.label }}</li></ul>
      <p>这个场景暂未添加可供学习者查看的参考资料。</p>
    </div>
  </aside>
</template>

<style scoped>
.knowledge-dock {
  display: flex; flex-direction: column; min-height: 0; height: 100%;
  border: 1.5px solid #ebe7f5; border-bottom: 4px solid #e5def1; border-radius: 18px;
  background: #fff; overflow: hidden;
}

.k-head {
  display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-shrink: 0;
  padding: 13px 14px 10px; border-bottom: 1px solid #f1eef8; background: #fff;
}
.k-title { display: flex; align-items: center; gap: 6px; min-width: 0; color: #6c52c5; }
.k-title h3 { margin: 0; font-size: 13.5px; font-weight: 750; color: #2d294b; white-space: nowrap; }
.k-title span { font-size: 11px; color: #8c85a6; white-space: nowrap; }
.k-head-actions { display: flex; align-items: center; gap: 6px; }
.k-theme-select {
  height: 26px; padding: 0 7px; border: 1px solid #e6e1f4; border-radius: 8px;
  background: #faf9ff; color: #5b43b0; font-size: 11px; font-weight: 600; cursor: pointer;
}
.k-close {
  display: grid; place-items: center; width: 26px; height: 26px;
  border: 0; border-radius: 8px; background: transparent; color: #7c7693; cursor: pointer;
}
.k-close:hover { background: #f2effa; color: #2d294b; }

.k-desc {
  flex-shrink: 0; margin: 0; padding: 9px 14px 4px;
  font-size: 11.5px; line-height: 1.6; color: #7c7693;
}

.k-tabs {
  display: flex; flex-shrink: 0; gap: 4px; padding: 0 12px;
  border-bottom: 1px solid #f1eef8; overflow-x: auto; scrollbar-width: none;
}
.k-tabs button {
  flex-shrink: 0; padding: 8px 10px; border: 0; border-bottom: 2px solid transparent;
  background: transparent; color: #7c7693; font-size: 12px; font-weight: 600; cursor: pointer;
}
.k-tabs button.active { color: #6c52c5; border-bottom-color: #7c62d2; }

.k-toolbar {
  display: flex; flex-direction: column; gap: 8px; flex-shrink: 0;
  padding: 10px 14px 8px; border-bottom: 1px solid #f5f2fb; background: #fcfbff;
}
.k-search {
  display: flex; align-items: center; gap: 6px; padding: 6px 10px;
  border: 1px solid #e7e2f4; border-radius: 9px; background: #fff; color: #8c85a6;
}
.k-search:focus-within { border-color: #8b73dd; color: #6c52c5; }
.k-search input {
  width: 100%; min-width: 0; border: 0; outline: none; background: transparent;
  font: inherit; font-size: 12px; color: #2d294b;
}
.k-pills { display: flex; flex-wrap: wrap; gap: 5px; }
.k-pills button {
  padding: 3px 9px; border: 1px solid #e7e1f5; border-radius: 999px;
  background: #fff; color: #6e6885; font-size: 11px; font-weight: 600; cursor: pointer;
}
.k-pills button.active { border-color: #8b73dd; background: #efeafc; color: #5b43b0; }

.k-body {
  flex: 1; min-height: 0; overflow-y: auto; padding: 12px 14px 16px;
  scrollbar-width: thin; scrollbar-color: #dcd5ee transparent;
}
.k-notice { display: flex; align-items: center; gap: 6px; padding: 14px; font-size: 12px; color: #7c7693; }
.k-error { padding: 14px; font-size: 12px; color: #be123c; }
.k-error button {
  display: inline-flex; align-items: center; gap: 5px; margin-top: 6px; padding: 5px 10px;
  border: 1px solid #fecdd3; border-radius: 8px; background: #fff; color: #be123c; cursor: pointer;
}
.k-empty { font-size: 12.5px; line-height: 1.7; color: #595275; }
.k-empty h4 { margin: 0 0 6px; color: #2d294b; }
.k-empty ul { margin: 0 0 10px; padding-left: 18px; }

:deep(mark) { padding: 0 2px; border-radius: 3px; background: #fef08a; color: #2d294b; }

/* ===== 主题 1：咖啡厅 / 餐厅仿真菜单 ===== */
.theme-cafe_menu .k-body { background: #fdfaf4; }
.menu-board {
  padding: 14px; border: 1.5px solid #eadfcd; border-radius: 14px;
  background: #fffdf9; box-shadow: inset 0 0 0 3px #faf4e8;
}
.menu-marquee { text-align: center; padding-bottom: 10px; margin-bottom: 12px; border-bottom: 1.5px dashed #e2d5be; }
.menu-kicker { display: block; font-size: 9.5px; letter-spacing: 0.18em; font-weight: 700; color: #a17449; }
.menu-marquee h4 {
  margin: 3px 0 0; font-family: Georgia, 'Times New Roman', serif;
  font-size: 16px; font-weight: 700; color: #3c2817;
}
.menu-group + .menu-group { margin-top: 14px; }
.menu-group-head {
  display: flex; align-items: center; gap: 8px; margin-bottom: 8px;
  font-family: Georgia, serif; font-size: 12.5px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.08em; color: #8c5a2b;
}
.menu-group-head::after { content: ''; flex: 1; height: 1px; background: #eadfcd; }
.menu-items { list-style: none; margin: 0; padding: 0; display: grid; gap: 9px; }
.menu-item { display: flex; align-items: flex-start; gap: 9px; }
.menu-thumb {
  display: grid; place-items: center; width: 28px; height: 28px; flex: 0 0 28px; margin-top: 1px;
  border-radius: 9px; background: #f6efe2; color: #8c5a2b;
}
.menu-thumb.is-cold { background: #e8f4f8; color: #2b6cb0; }
.menu-thumb.is-pastry { background: #fdf0e1; color: #b45309; }
.menu-thumb.is-tea { background: #eaf5ec; color: #2c7a4b; }
.menu-item-main { flex: 1; min-width: 0; }
.menu-item-top { display: flex; align-items: baseline; gap: 6px; }
.menu-item-top b { font-size: 12.5px; font-weight: 700; color: #332316; }
.menu-leader { flex: 1; min-width: 12px; border-bottom: 1.5px dotted #dbcab0; }
.menu-price { flex-shrink: 0; font-size: 12px; font-weight: 750; color: #8c4a18; font-variant-numeric: tabular-nums; }
.menu-item-main p { margin: 2px 0 0; font-size: 11px; line-height: 1.45; color: #7c6753; }
.menu-combo {
  display: flex; align-items: flex-start; gap: 6px; margin-top: 14px; padding: 9px 11px;
  border-radius: 10px; border: 1px solid #ead2ad; background: #fbf2e3;
  font-size: 11.5px; line-height: 1.5; font-weight: 600; color: #744416;
}

/* ===== 主题 2：出行电子屏 ===== */
.transit-screen {
  padding: 12px; border-radius: 14px; background: #181c2b; color: #e2e8f0;
}
.transit-screen-head {
  display: flex; align-items: center; justify-content: space-between;
  padding-bottom: 8px; margin-bottom: 10px; border-bottom: 1px solid #2d344c;
  font-family: ui-monospace, SFMono-Regular, monospace; font-size: 10.5px; letter-spacing: 0.08em; color: #94a3b8;
}
.transit-live { display: inline-flex; align-items: center; gap: 5px; color: #34d399; font-weight: 700; }
.transit-live i { width: 6px; height: 6px; border-radius: 50%; background: #34d399; }
.transit-group + .transit-group { margin-top: 10px; }
.transit-sec-title {
  margin-bottom: 6px; font-size: 10.5px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.06em; color: #fbbf24;
}
.transit-ticket {
  padding: 8px 10px; margin-bottom: 6px; border-radius: 9px;
  background: #23293e; border-left: 3px solid #fbbf24;
}
.ticket-main { font-size: 12px; line-height: 1.55; color: #f1f5f9; }
.ticket-meta { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 5px; }
.ticket-time {
  padding: 1px 6px; border-radius: 5px; background: #111524;
  font-family: ui-monospace, monospace; font-size: 10.5px; color: #fde68a;
}
.ticket-status {
  padding: 1px 6px; border-radius: 5px; background: rgba(52, 211, 153, .16);
  font-size: 10px; font-weight: 700; color: #34d399;
}

/* ===== 主题 3 / 4 / 5：职位简报 / 酒店 / 文档 ===== */
.brief-board, .hotel-board, .article-board { display: grid; gap: 10px; }
.brief-card, .hotel-card, .article-card {
  padding: 12px 13px; border: 1px solid #ebe7f5; border-radius: 12px; background: #fcfcfe;
}
.brief-pill {
  display: inline-block; padding: 2px 9px; margin-bottom: 6px; border-radius: 999px;
  background: #efeafc; color: #5b43b0; font-size: 11px; font-weight: 700;
}
.hotel-card { border-color: #e2ebe6; background: #f9fcfb; }
.hotel-card h4 { display: flex; align-items: center; gap: 5px; margin: 0 0 6px; font-size: 12.5px; color: #1f5c43; }
.article-card h4 { margin: 0 0 6px; font-size: 12.5px; font-weight: 700; color: #2d294b; }

.k-md { font-size: 12px; line-height: 1.7; color: #4a4463; overflow-wrap: anywhere; }
.k-md :deep(p) { margin: 4px 0; }
.k-md :deep(ul), .k-md :deep(ol) { margin: 5px 0; padding-left: 17px; }
.k-md :deep(li) { margin: 3px 0; }
.k-md :deep(li::marker) { color: #8b73dd; }
.k-md :deep(strong) { color: #2d294b; font-weight: 650; }
.k-md :deep(blockquote) { margin: 6px 0; padding: 4px 10px; border-left: 3px solid #c9bce8; color: #6e6885; }
</style>

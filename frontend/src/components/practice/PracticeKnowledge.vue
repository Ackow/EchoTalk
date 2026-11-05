<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { marked } from 'marked'
import AppIcon from '../AppIcon.vue'
import { getPracticeKnowledge } from '../../api/scenes'

// 场景知识点弹窗：分资料模块 Tab + Markdown 正文（交互对齐 1.0 的独立知识面板）。
const props = defineProps({ sceneId: { type: String, required: true }, description: { type: String, default: '' } })
const emit = defineEmits(['close'])
const documents = ref([])
const activeDoc = ref(0) // 当前资料模块下标
const loading = ref(false)
const error = ref('')
const query = ref('')
let generation = 0
let request = null

// 分节总数（跨全部资料），用于标题计数。
const points = computed(() => documents.value.flatMap(document => document.sections))

// 当前资料模块下的分节；正文按 Markdown 渲染。
// 资料来自用户自己在知识工作区上传的内容，与 1.0 一致按可信来源渲染。
const docSections = computed(() => {
  const current = documents.value[activeDoc.value]
  if (!current) return []
  const term = query.value.trim().toLowerCase()
  return current.sections
    .map(section => ({
      key: `${current.id}:${section.name}`,
      name: section.name,
      filename: current.filename,
      html: marked.parse(section.chunks.map(chunk => chunk.text).join('\n\n'), { breaks: true, async: false }),
    }))
    .filter(section => !term || [section.name, section.filename, section.html].some(text => text.toLowerCase().includes(term)))
})

async function load() {
  // 切换场景、重试或关闭后，旧请求都不能覆盖当前弹窗。
  const current = ++generation
  request?.abort()
  request = new AbortController()
  documents.value = []
  activeDoc.value = 0
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

watch(() => props.sceneId, () => { query.value = ''; activeDoc.value = 0; load() }, { immediate: true })
onBeforeUnmount(() => { generation += 1; request?.abort() })
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <section class="modal-card knowledge-modal" role="dialog" aria-modal="true" aria-label="场景知识点">
      <header class="knowledge-head">
        <div class="knowledge-title"><AppIcon name="book-open" :size="16" /><h3>场景知识点</h3><span v-if="!loading && !error">{{ points.length }} 节</span></div>
        <button class="knowledge-close" type="button" aria-label="关闭知识点" @click="emit('close')"><AppIcon name="x" :size="15" /></button>
      </header>
      <p v-if="description" class="knowledge-description">{{ description }}</p>
      <p v-if="loading" class="knowledge-notice" role="status"><AppIcon name="loader" :size="14" />正在加载知识点…</p>
      <div v-else-if="error" class="knowledge-error" role="alert"><p>{{ error }}</p><button type="button" @click="load"><AppIcon name="rotate" :size="13" />重新加载</button></div>
      <template v-else-if="points.length">
        <nav v-if="documents.length > 1" class="knowledge-tabs" aria-label="知识点资料模块">
          <button v-for="(doc, index) in documents" :key="doc.id" type="button" :class="{ active: activeDoc === index }" @click="activeDoc = index">{{ doc.filename }}</button>
        </nav>
        <label class="knowledge-search"><AppIcon name="search" :size="13" /><input v-model="query" type="search" aria-label="搜索当前模块知识点" placeholder="搜索当前模块的标题或内容" /></label>
        <div class="knowledge-body">
          <section v-for="section in docSections" :key="section.key" class="knowledge-section">
            <h4 v-if="section.name !== '_'">{{ section.name }}</h4>
            <p class="knowledge-source"><AppIcon name="file-text" :size="11" />{{ section.filename }}</p>
            <div class="knowledge-md" v-html="section.html"></div>
          </section>
          <p v-if="!docSections.length" class="knowledge-notice">没有匹配的知识点，试试其他关键词。</p>
        </div>
      </template>
      <p v-else class="knowledge-notice knowledge-body">这个场景暂无可展示的知识点。可在知识工作区添加资料并设为用户可见。</p>
      <footer class="knowledge-foot"><router-link :to="{ name: 'knowledge' }" @click="emit('close')">前往知识工作区<AppIcon name="arrow-right" :size="13" /></router-link></footer>
    </section>
  </div>
</template>

<style scoped>
.modal-backdrop { position: fixed; inset: 0; z-index: 60; display: grid; place-items: center; padding: 24px; background: rgba(34, 37, 59, .32); animation: fade-in .18s ease; }
.knowledge-modal { display: flex; flex-direction: column; width: min(720px, 94vw); max-height: min(78vh, 660px); padding: 0; overflow: hidden; }
@keyframes fade-in { from { opacity: 0; } }

.knowledge-head { display: flex; flex-shrink: 0; align-items: center; justify-content: space-between; gap: 10px; padding: 16px 20px 12px; }
.knowledge-title { display: flex; align-items: center; gap: 7px; color: var(--brand); }
.knowledge-title h3 { margin: 0; color: var(--ink); font-size: 15px; font-weight: 600; }
.knowledge-title > span { color: var(--muted); font-size: 11.5px; }
.knowledge-close { display: grid; place-items: center; width: 30px; height: 30px; border: 0; border-radius: 8px; background: transparent; color: var(--muted); transition: background .15s, color .15s; }
.knowledge-close:hover { background: #f0f1f6; color: var(--ink); }
.knowledge-description { flex-shrink: 0; margin: 0; padding: 0 20px 10px; color: var(--muted); font-size: 12.5px; line-height: 1.8; }

.knowledge-tabs { display: flex; flex-shrink: 0; gap: 4px; padding: 0 14px; border-bottom: 1px solid var(--line); overflow-x: auto; scrollbar-width: thin; }
.knowledge-tabs button { flex-shrink: 0; max-width: 200px; overflow: hidden; padding: 10px 14px; border: 0; border-bottom: 2px solid transparent; background: transparent; color: var(--muted); font-size: 12.5px; text-overflow: ellipsis; white-space: nowrap; transition: color .15s; }
.knowledge-tabs button:hover { color: var(--ink-soft); }
.knowledge-tabs button.active { color: var(--brand); border-bottom-color: var(--brand); font-weight: 500; }

.knowledge-search { display: flex; flex-shrink: 0; align-items: center; gap: 7px; margin: 12px 20px 0; padding: 8px 10px; border: 1px solid var(--line); border-radius: 8px; color: var(--muted); transition: border-color .15s; }
.knowledge-search:focus-within { border-color: var(--brand); }
.knowledge-search input { width: 100%; min-width: 0; border: 0; outline: none; font: inherit; font-size: 12px; color: var(--ink); background: transparent; }

.knowledge-body { flex: 1; min-height: 120px; overflow-y: auto; scrollbar-width: thin; overscroll-behavior: contain; padding: 2px 20px 16px; }
.knowledge-section { margin-top: 12px; padding: 14px 16px; border: 1px solid var(--line); border-radius: 11px; background: #fcfcfe; }
.knowledge-section h4 { margin: 0 0 2px; color: var(--ink); font-size: 13px; font-weight: 600; }
.knowledge-source { display: flex; align-items: center; gap: 5px; margin: 0 0 4px; color: var(--faint); font-size: 10.5px; overflow-wrap: anywhere; }
.knowledge-notice { display: flex; gap: 6px; align-items: flex-start; color: var(--muted); font-size: 12.5px; line-height: 1.8; margin: 14px 0; }
.knowledge-error { color: var(--danger); font-size: 12.5px; line-height: 1.7; padding: 0 20px; }
.knowledge-error p { margin: 12px 0 8px; }
.knowledge-error button { display: flex; align-items: center; gap: 5px; padding: 6px 10px; border: 1px solid var(--line); border-radius: 7px; background: white; color: var(--ink-soft); cursor: pointer; }

/* Markdown 正文美化：v-html 内容不带 scoped 属性，统一用 :deep 穿透 */
.knowledge-md { color: var(--ink-soft); font-size: 13px; line-height: 1.9; overflow-wrap: anywhere; }
.knowledge-md :deep(h1), .knowledge-md :deep(h2), .knowledge-md :deep(h3), .knowledge-md :deep(h4) { margin: 14px 0 6px; color: var(--ink); font-size: 13.5px; font-weight: 600; line-height: 1.5; }
.knowledge-md :deep(h1), .knowledge-md :deep(h2) { font-size: 14.5px; }
.knowledge-md :deep(h1:first-child), .knowledge-md :deep(h2:first-child), .knowledge-md :deep(h3:first-child), .knowledge-md :deep(p:first-child) { margin-top: 2px; }
.knowledge-md :deep(p) { margin: 8px 0; }
.knowledge-md :deep(ul), .knowledge-md :deep(ol) { margin: 8px 0; padding-left: 20px; }
.knowledge-md :deep(li) { margin: 4px 0; }
.knowledge-md :deep(li::marker) { color: var(--brand); }
.knowledge-md :deep(strong) { color: var(--ink); font-weight: 600; }
.knowledge-md :deep(code) { padding: 1px 5px; border-radius: 5px; background: #eff0f7; color: var(--brand-deep); font-family: ui-monospace, Consolas, monospace; font-size: 12px; }
.knowledge-md :deep(pre) { margin: 10px 0; padding: 12px; border-radius: 9px; background: #f4f4f9; overflow-x: auto; }
.knowledge-md :deep(pre code) { padding: 0; background: transparent; color: var(--ink-soft); }
.knowledge-md :deep(blockquote) { margin: 10px 0; padding: 4px 12px; border-left: 3px solid #c9c6ec; color: var(--muted); }
.knowledge-md :deep(table) { width: 100%; margin: 10px 0; border-collapse: collapse; font-size: 12.5px; }
.knowledge-md :deep(th), .knowledge-md :deep(td) { padding: 6px 10px; border: 1px solid var(--line); text-align: left; }
.knowledge-md :deep(th) { background: #f7f7fb; color: var(--ink); font-weight: 600; }
.knowledge-md :deep(hr) { margin: 14px 0; border: 0; border-top: 1px solid var(--line); }
.knowledge-md :deep(a) { color: var(--brand); }

.knowledge-foot { display: flex; flex-shrink: 0; justify-content: flex-end; padding: 10px 20px 14px; border-top: 1px solid var(--line); }
.knowledge-foot a { display: flex; align-items: center; gap: 5px; color: var(--brand); font-size: 12px; text-decoration: none; }
.knowledge-foot a:hover { color: var(--brand-deep); }
.knowledge-close:focus-visible, .knowledge-tabs button:focus-visible, .knowledge-search:focus-within, .knowledge-foot a:focus-visible { outline: 2px solid var(--brand); outline-offset: 2px; }
</style>

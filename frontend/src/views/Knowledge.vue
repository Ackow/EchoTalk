<template>
  <!-- 知识工作区（一期）：场景资料上传 / 解析管理 / 分节可见性；布局对齐场景探索页的工具行结构。 -->
  <section class="kw-page">
    <!-- 工具行：资料范围切换 + 上传 -->
    <div class="kw-toolbar">
      <div class="seg-filter" role="tablist" aria-label="资料范围">
        <button class="seg-item" :class="{ active: scope === 'scene' }" type="button" role="tab" :aria-selected="scope === 'scene'" @click="scope = 'scene'">
          场景资料<span class="seg-count">{{ sceneDocTotal }}</span>
        </button>
        <button class="seg-item" :class="{ active: scope === 'personal' }" type="button" role="tab" :aria-selected="scope === 'personal'" @click="scope = 'personal'">
          个人资料<span class="seg-count">即将开放</span>
        </button>
      </div>
      <div class="toolbar-actions">
        <label v-if="scope === 'scene' && sceneWritable" class="ai-toggle" title="上传的资料默认仅 AI 可见（如 JD、考官备注）">
          <input v-model="uploadAiOnly" type="checkbox">
          <i></i>上传为仅 AI 资料
        </label>
        <button v-if="scope === 'scene'" class="primary-button slim" type="button" :disabled="!sceneWritable" :title="!session.token ? '登录后可上传资料' : sceneWritable ? '支持拖放 PDF / TXT / Markdown 到下方区域' : '内置场景只读，复制为自定义场景后可上传'" @click="pickFile">
          <AppIcon name="upload" :size="14" />上传资料
        </button>
        <input ref="fileInput" type="file" accept=".pdf,.txt,.md,.markdown" class="hidden-input" @change="onFileChange">
      </div>
    </div>

    <!-- 个人资料：二期占位（工作区级存储依赖后端 scope 扩展） -->
    <div v-if="scope === 'personal'" class="kw-placeholder">
      <div class="placeholder-glyph"><AppIcon name="lock" :size="20" /></div>
      <h3>个人工作区资料即将开放</h3>
      <p>简历、目标 JD、项目文档等跨场景资料，将在后端支持工作区级存储后开放（二期）。当前资料按场景隔离管理。</p>
    </div>

    <!-- 场景资料视图 -->
    <template v-else>
    <!-- 筛选行：场景 chips + 检索占位（场景未加载时不渲染，避免检索框独占一行） -->
    <div v-if="scenes.length" class="filter-row">
        <div class="cat-chips" role="group" aria-label="选择场景">
          <button
            v-for="s in scenes"
            :key="s.id"
            type="button"
            class="cat-chip"
            :class="{ active: s.id === activeSceneId }"
            @click="activeSceneId = s.id"
          >{{ s.name }}<span v-if="s.knowledge_count" class="chip-count">{{ s.knowledge_count }}</span></button>
        </div>
        <label class="search-box" title="资料检索将随 Hybrid RAG（阶段三）一起开放">
          <AppIcon name="search" :size="14" />
          <input type="text" disabled placeholder="资料检索将随阶段三开放">
        </label>
      </div>

      <p v-if="!session.token" class="guest-note">
        <AppIcon name="info" :size="13" />游客仅可浏览内置场景资料；登录后可上传与管理。
      </p>

      <!-- 拖放上传区 -->
      <div
        class="dropzone"
        :class="{ drag }"
        tabindex="0"
        role="button"
        aria-label="拖放或选择上传资料：支持 PDF、TXT、Markdown，单文件 10 MB 以内"
        :title="sceneWritable ? undefined : '内置场景只读，复制为自定义场景后可管理资料'"
        @click="pickFile"
        @keydown.enter="pickFile"
        @dragover.prevent
        @dragenter.prevent="drag = true"
        @dragleave="drag = false"
        @drop.prevent="onDrop"
      >
        <AppIcon name="upload" :size="16" />
        <span class="dz-text">拖放文件到此处，或点击上传</span>
        <span class="dz-hint">PDF、TXT、Markdown · 单文件 10 MB 以内</span>
      </div>

      <!-- 上传中 -->
      <div v-if="uploadProgress" class="doc-row uploading">
        <div class="doc-main">
          <span class="file-badge" data-type="new"><AppIcon name="upload" :size="14" /></span>
          <div class="doc-info">
            <div class="doc-name"><span class="name-text">{{ uploadProgress.name }}</span><span class="tag load">解析中…</span></div>
            <div class="progress"><i :style="{ width: uploadProgress.percent + '%' }"></i></div>
          </div>
        </div>
      </div>

      <!-- 资料文件列表 -->
      <div v-if="docsLoading" class="doc-skeleton" aria-busy="true" aria-label="正在加载资料">
        <div v-for="n in 2" :key="n" class="sk-row"><div class="sk-line w12"></div><div class="sk-grow"><div class="sk-line w60"></div><div class="sk-line w40"></div></div></div>
      </div>

      <div v-else-if="docs.length" class="doc-card">
        <div v-for="doc in docs" :key="doc.id" class="doc-row">
          <div class="doc-main">
            <span class="file-badge" :data-type="docType(doc.filename)">{{ docType(doc.filename) }}</span>
            <div class="doc-info">
              <div class="doc-name">
                <span class="name-text">{{ doc.filename }}</span>
                <span class="tag ok"><AppIcon name="check" :size="11" />{{ doc.chunk_count }} 块</span>
                <span class="tag" :class="doc.visibility === 'user' ? 'user' : 'ai'">
                  <AppIcon :name="doc.visibility === 'user' ? 'eye' : 'bot'" :size="11" />{{ doc.visibility === 'user' ? '用户可见' : '仅 AI' }}
                </span>
              </div>
              <p class="doc-desc">{{ doc.owner_id ? '我上传的' : '场景内置' }} · {{ doc.sections.length }} 个分节</p>
            </div>
            <div class="doc-actions">
              <button
                v-if="doc.sections.length"
                class="icon-btn"
                type="button"
                :aria-expanded="expanded.has(doc.id)"
                :title="expanded.has(doc.id) ? '收起分节' : '分节可见性'"
                @click="toggleExpand(doc.id)"
              >
                <AppIcon name="chevron-down" :size="15" :class="{ flip: expanded.has(doc.id) }" />
              </button>
              <button v-if="!doc.virtual && sceneWritable" class="icon-btn danger" type="button" title="删除资料" @click="confirming = confirming === doc.id ? null : doc.id">
                <AppIcon name="trash" :size="14" />
              </button>
            </div>
          </div>

          <!-- 分节可见性管理 -->
          <div v-if="expanded.has(doc.id)" class="sections">
            <div v-for="sec in doc.sections" :key="sec.section" class="section-row">
              <label class="switch" :title="!sceneWritable ? '内置场景只读' : sec.visibility === 'user' ? '对用户可见' : '仅 AI 可见'">
                <input
                  type="checkbox"
                  :checked="sec.visibility === 'user'"
                  :disabled="!sceneWritable"
                  :aria-label="`分节 ${sec.section} 对用户可见`"
                  @change="setSectionVisibility(doc, sec, $event)"
                >
                <i></i>
              </label>
              <span class="name">{{ sec.section }}</span>
              <span class="snippet">{{ sec.preview }}</span>
              <span class="tag" :class="sec.visibility === 'user' ? 'user' : 'ai'">{{ sec.visibility === 'user' ? '用户可见' : '仅 AI' }}</span>
            </div>
          </div>

          <!-- 删除确认 -->
          <div v-if="confirming === doc.id" class="confirm-bar" role="alertdialog" aria-label="确认删除资料">
            <AppIcon name="alert" :size="14" />
            <span class="confirm-text">删除「{{ doc.filename }}」将同步移除源文件与已解析内容，不可恢复。</span>
            <button class="btn-ghost-danger" type="button" @click="doDelete(doc)">确认删除</button>
            <button class="btn-ghost" type="button" @click="confirming = null">取消</button>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="kw-empty">
        <div class="placeholder-glyph"><AppIcon name="file-text" :size="20" /></div>
        <template v-if="activeSceneId">
          <h3>该场景暂无资料</h3>
          <p>上传 PDF、TXT 或 Markdown，解析分块后将作为场景对话与面试的背景知识。</p>
        </template>
        <template v-else>
          <h3>暂无可用场景</h3>
          <p>未获取到场景列表，请检查后端连接与登录状态后刷新重试。</p>
        </template>
      </div>
    </template>

    <!-- 轻提示 -->
    <transition name="pop">
      <div v-if="notice" class="toast" role="status">{{ notice }}</div>
    </transition>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import { session } from '../auth/session'
import { deleteKnowledge, getSectionOverview, listKnowledgeDocuments, listScenes, patchSectionVisibility, uploadKnowledge } from '../api/scenes'

// 场景资料支持类型与上限，与后端 knowledge.py 约定一致（§9.5）。
const ALLOWED_EXTENSIONS = ['pdf', 'txt', 'md', 'markdown']
const MAX_FILE_SIZE = 10 * 1024 * 1024

const scope = ref('scene') // 资料范围：scene（一期真实）/ personal（二期占位）
const scenes = ref([]) // 场景 chips 数据（含 knowledge_count）
const activeSceneId = ref('')
const docs = ref([]) // 当前场景的文件级资料列表
const docsLoading = ref(false)
const uploadAiOnly = ref(false) // 上传文件级可见性缺省
const uploadProgress = ref(null) // { name, percent } 上传进度
const drag = ref(false)
const expanded = ref(new Set()) // 展开分节管理的资料 id
const confirming = ref(null) // 待删除确认的资料 id
const notice = ref('')
const fileInput = ref(null)
let noticeTimer = null

const notify = (text) => {
  notice.value = text
  clearTimeout(noticeTimer)
  noticeTimer = setTimeout(() => (notice.value = ''), 2800)
}

/* ---- 数据加载 ---- */

async function loadScenes() {
  try {
    const { data } = await listScenes()
    scenes.value = data.items || data // 响应为 { items: [...] }，兼容裸数组
    // 缺省选中第一个有资料的内置场景，否则第一个场景
    const preferred = scenes.value.find((s) => s.knowledge_count > 0) || scenes.value[0]
    if (preferred) activeSceneId.value = preferred.id
  } catch (error) {
    notify(error.message || '场景列表加载失败')
  }
}

async function loadDocs() {
  if (!activeSceneId.value) return
  docsLoading.value = true
  confirming.value = null
  expanded.value = new Set()
  try {
    const { data } = await listKnowledgeDocuments(activeSceneId.value)
    docs.value = data.documents
  } catch (error) {
    // 兼容未部署文件级概览端点的旧版后端：退回分节概览，按单卡分节展示
    try {
      const { data } = await getSectionOverview(activeSceneId.value)
      if (data.sections?.length) {
        docs.value = [{
          id: 'sections',
          virtual: true,
          filename: '场景资料（按分节）',
          chunk_count: data.sections.reduce((sum, s) => sum + s.chunk_count, 0),
          visibility: 'user',
          owner_id: null,
          sections: data.sections,
        }]
      } else {
        docs.value = []
      }
    } catch {
      docs.value = []
      notify(error.message || '资料列表加载失败')
    }
  } finally {
    docsLoading.value = false
  }
}

watch(activeSceneId, loadDocs)

const sceneDocTotal = computed(() => scenes.value.reduce((sum, s) => sum + (s.knowledge_count || 0), 0))

// 内置场景只读（后端 SCENE_BUILTIN_READONLY 守卫）：上传/可见性/删除仅对自定义场景开放
const activeScene = computed(() => scenes.value.find((s) => s.id === activeSceneId.value))
const sceneWritable = computed(() => !!activeScene.value && activeScene.value.source !== 'builtin')

/* ---- 上传 ---- */

function pickFile() {
  if (!session.token) return notify('上传资料需要先登录，点击左下角账户卡片登录。')
  if (!sceneWritable.value) return notify('内置场景只读：可在场景探索页复制为自定义场景后管理资料。')
  fileInput.value?.click()
}

function docType(filename) {
  const suffix = filename.split('.').pop().toLowerCase()
  return suffix === 'markdown' ? 'md' : suffix
}

function validateFile(file) {
  const suffix = file.name.split('.').pop().toLowerCase()
  if (!ALLOWED_EXTENSIONS.includes(suffix)) return `不支持的文件类型 .${suffix}，仅支持 pdf / txt / md`
  if (file.size > MAX_FILE_SIZE) return '文件超过 10 MB 上限'
  return ''
}

async function uploadFile(file) {
  const problem = validateFile(file)
  if (problem) return notify(problem)
  uploadProgress.value = { name: file.name, percent: 0 }
  try {
    const { data } = await uploadKnowledge(activeSceneId.value, file, uploadAiOnly.value ? 'ai_only' : 'user', (event) => {
      if (event.total) uploadProgress.value.percent = Math.round((event.loaded / event.total) * 100)
    })
    notify(`「${data.filename}」解析完成 · ${data.chunk_count} 块已入库`)
    await loadDocs() // 重新拉取文件列表（后端同步解析，返回即已入库）
    scenes.value = scenes.value.map((s) => (s.id === activeSceneId.value ? { ...s, knowledge_count: (s.knowledge_count || 0) + 1 } : s))
  } catch (error) {
    notify(error.message || '上传失败，请重试')
  } finally {
    uploadProgress.value = null
    if (fileInput.value) fileInput.value.value = '' // 允许重复选择同一文件
  }
}

function onFileChange(event) {
  const file = event.target.files?.[0]
  if (file) uploadFile(file)
}

function onDrop(event) {
  drag.value = false
  if (!session.token) return notify('上传资料需要先登录，点击左下角账户卡片登录。')
  if (!sceneWritable.value) return notify('内置场景只读：可在场景探索页复制为自定义场景后管理资料。')
  const file = event.dataTransfer.files?.[0]
  if (file) uploadFile(file)
}

/* ---- 分节可见性 ---- */

function toggleExpand(id) {
  const next = new Set(expanded.value)
  next.has(id) ? next.delete(id) : next.add(id)
  expanded.value = next
}

async function setSectionVisibility(doc, sec, event) {
  const visibility = event.target.checked ? 'user' : 'ai_only'
  const previous = sec.visibility
  sec.visibility = visibility // 乐观更新：开关即时反馈
  try {
    await patchSectionVisibility(activeSceneId.value, sec.section, visibility)
    notify(`「${sec.section}」已${visibility === 'user' ? '对用户可见' : '设为仅 AI 可见'}`)
  } catch (error) {
    sec.visibility = previous // 失败回滚开关状态
    event.target.checked = previous === 'user'
    notify(error.message || '可见性修改失败')
  }
}

/* ---- 删除 ---- */

async function doDelete(doc) {
  try {
    await deleteKnowledge(activeSceneId.value, doc.id)
    notify(`已删除「${doc.filename}」，源文件与解析内容同步移除`)
    confirming.value = null
    await loadDocs()
    scenes.value = scenes.value.map((s) => (s.id === activeSceneId.value ? { ...s, knowledge_count: Math.max((s.knowledge_count || 1) - 1, 0) } : s))
  } catch (error) {
    notify(error.message || '删除失败，请重试')
  }
}

onMounted(loadScenes)
onBeforeUnmount(() => clearTimeout(noticeTimer))
</script>

<style scoped>
/* 布局与类名对齐 Scenes.vue：工具行 → 筛选行 → 内容列表 */
.kw-page { position: relative; flex: 1; min-height: 0; display: flex; flex-direction: column; padding: 22px 28px 32px; overflow-y: auto; }

/* ===== 工具行 ===== */
.kw-toolbar { display: flex; flex: 0 0 auto; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 12px; }
.seg-filter { display: inline-flex; gap: 3px; padding: 3px; border: 1px solid var(--line); border-radius: 9px; background: var(--surface); }
.seg-item { display: inline-flex; align-items: center; gap: 6px; height: 31px; padding: 0 13px; border: 0; border-radius: 7px; background: transparent; color: var(--ink-soft); font-size: 13.5px; transition: background .15s, color .15s; }
.seg-item:hover { color: var(--ink); }
.seg-item.active { background: var(--brand-soft); color: var(--brand-deep, var(--brand)); font-weight: 500; }
.seg-count { color: var(--muted); font-size: 11.5px; }
.seg-item.active .seg-count { color: var(--brand); }
.toolbar-actions { display: flex; align-items: center; gap: 10px; }
.hidden-input { display: none; }

/* 覆盖全局 .primary-button（width:100% / margin-top:25px），对齐 Scenes.vue 的写法 */
.primary-button.slim { width: auto; height: 34px; margin-top: 0; gap: 6px; padding: 0 15px; justify-content: center; display: inline-flex; }

.ai-toggle { display: inline-flex; align-items: center; gap: 7px; font-size: 12.5px; color: var(--ink-soft); cursor: pointer; user-select: none; white-space: nowrap; flex: 0 0 auto; }
.ai-toggle input { position: absolute; opacity: 0; }
.ai-toggle i { width: 30px; height: 18px; border-radius: 99px; background: #d4d6e6; position: relative; transition: background .18s; flex: 0 0 30px; }
.ai-toggle i::after { content: ""; position: absolute; top: 2px; left: 2px; width: 14px; height: 14px; border-radius: 50%; background: #fff; transition: transform .18s; box-shadow: 0 1px 3px rgba(0, 0, 0, .2); }
.ai-toggle input:checked + i { background: var(--brand); }
.ai-toggle input:checked + i::after { transform: translateX(12px); }
.ai-toggle input:focus-visible + i { outline: 2px solid var(--brand); outline-offset: 2px; }

/* ===== 筛选行 ===== */
.filter-row { display: flex; flex: 0 0 auto; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 14px; }
.cat-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.cat-chip { height: 29px; padding: 0 13px; border: 1px solid var(--line); border-radius: 15px; background: var(--surface); color: var(--ink-soft); font-size: 13px; transition: border-color .15s, background .15s, color .15s; }
.cat-chip:hover { border-color: #d5d7e6; color: var(--ink); }
.cat-chip.active { border-color: var(--brand); background: var(--brand-soft); color: var(--brand-deep, var(--brand)); font-weight: 500; }
.chip-count { margin-left: 5px; font-size: 11px; color: var(--muted); }
.cat-chip.active .chip-count { color: var(--brand); opacity: .75; }

.search-box { position: relative; display: inline-flex; align-items: center; gap: 7px; width: 250px; flex: 0 0 auto; height: 34px; padding: 0 10px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--faint, var(--muted)); }
.search-box input { flex: 1; min-width: 0; border: 0; outline: none; background: transparent; color: var(--ink); font-size: 13.5px; font-family: inherit; }
.search-box input:disabled { cursor: not-allowed; }
.search-box input::placeholder { color: var(--faint, #a6a9bd); }

.guest-note { display: flex; align-items: center; gap: 6px; color: var(--muted); font-size: 12.5px; margin: 0 0 10px; }

/* ===== 拖放上传区（紧凑单行） ===== */
.dropzone { display: flex; flex: 0 0 auto; align-items: center; gap: 10px; padding: 13px 16px; border: 1.5px dashed #cdd0e6; border-radius: 12px; background: var(--surface); color: var(--muted); cursor: pointer; transition: border-color .15s, background .15s; margin-bottom: 14px; }
.dropzone:hover, .dropzone.drag { border-color: var(--brand); background: var(--brand-soft); }
.dz-text { color: var(--ink-soft); font-size: 13.5px; font-weight: 500; }
.dz-hint { font-size: 12px; }
.dropzone:hover .dz-text, .dropzone.drag .dz-text { color: var(--brand-deep, var(--brand)); }

/* ===== 资料列表 ===== */
.doc-card { border: 1px solid var(--line); border-radius: 12px; background: var(--surface); padding: 4px 16px; }
.doc-row { border-bottom: 1px solid var(--line); padding: 12px 0; }
.doc-row:last-child { border-bottom: 0; }
.doc-row.uploading { pointer-events: none; }
.doc-main { display: flex; align-items: center; gap: 12px; }
.file-badge { flex: 0 0 38px; width: 38px; height: 44px; border-radius: 8px; display: grid; place-items: center; font-size: 10px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; }
.file-badge[data-type="pdf"] { background: #eceefb; color: #4b4dc7; }
.file-badge[data-type="md"] { background: #e6f4ec; color: #1f7a52; }
.file-badge[data-type="txt"] { background: #fdf0e4; color: #b06a1d; }
.file-badge[data-type="new"] { background: var(--bg); color: var(--muted); }
.doc-info { min-width: 0; flex: 1; }
.doc-name { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 13.5px; }
.name-text { font-weight: 600; overflow-wrap: anywhere; }
.doc-desc { color: var(--muted); font-size: 12px; margin: 2px 0 0; }
.doc-actions { display: flex; align-items: center; gap: 6px; flex: 0 0 auto; }
.icon-btn { width: 28px; height: 28px; display: grid; place-items: center; border: 0; border-radius: 7px; background: transparent; color: var(--muted); cursor: pointer; transition: all .15s; }
.icon-btn:hover { background: var(--bg); color: var(--ink); }
.icon-btn.danger:hover { background: var(--danger-soft, #fdeeee); color: var(--danger); }
.icon-btn .flip { transform: rotate(180deg); }

/* 状态徽标 */
.tag { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; border-radius: 99px; padding: 2px 9px; font-weight: 600; white-space: nowrap; }
.tag.user { background: var(--brand-soft); color: var(--brand-deep, var(--brand)); }
.tag.ai { background: #f0f1f6; color: var(--ink-soft); }
.tag.ok { background: var(--ok-soft, #e8f6f0); color: var(--ok, #1f9d6c); }
.tag.load { background: var(--bg); color: var(--muted); }

/* 上传进度 */
.progress { height: 4px; border-radius: 99px; background: var(--line); overflow: hidden; margin-top: 8px; max-width: 320px; }
.progress i { display: block; height: 100%; background: var(--brand); border-radius: 99px; transition: width .2s; }

/* 分节管理 */
.sections { margin-top: 10px; border: 1px solid var(--line); border-radius: 10px; background: var(--bg); padding: 4px 12px; }
.section-row { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px dashed var(--line); font-size: 12.5px; }
.section-row:last-child { border-bottom: 0; }
.section-row .name { font-weight: 600; white-space: nowrap; }
.section-row .snippet { color: var(--muted); flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 开关 */
.switch { position: relative; width: 34px; height: 20px; flex: 0 0 34px; }
.switch input { opacity: 0; width: 100%; height: 100%; position: absolute; cursor: pointer; margin: 0; }
.switch i { position: absolute; inset: 0; border-radius: 99px; background: #d4d6e6; transition: background .18s; }
.switch i::after { content: ""; position: absolute; top: 2px; left: 2px; width: 16px; height: 16px; border-radius: 50%; background: #fff; transition: transform .18s; box-shadow: 0 1px 3px rgba(0, 0, 0, .2); }
.switch input:checked + i { background: var(--brand); }
.switch input:checked + i::after { transform: translateX(14px); }
.switch input:focus-visible + i { outline: 2px solid var(--brand); outline-offset: 2px; }

/* 删除确认 */
.confirm-bar { display: flex; align-items: center; gap: 10px; margin-top: 10px; background: var(--danger-soft, #fdeeee); border: 1px solid #f3c8cc; border-radius: 10px; padding: 9px 12px; font-size: 12.5px; color: var(--danger); flex-wrap: wrap; }
.confirm-text { flex: 1; min-width: 200px; }
.btn-ghost-danger { border: 1px solid #eeb9be; border-radius: 8px; padding: 4px 12px; font-size: 12px; color: var(--danger); font-weight: 600; background: #fff; cursor: pointer; }
.btn-ghost { border: 1px solid var(--line); border-radius: 8px; padding: 4px 12px; font-size: 12px; color: var(--ink-soft); background: #fff; cursor: pointer; }

/* 占位 / 空状态 / 骨架：空状态紧跟内容流，不垂直撑开留大段空白 */
.kw-placeholder, .kw-empty { flex: 0 0 auto; display: flex; flex-direction: column; align-items: center; text-align: center; color: var(--muted); padding: 46px 20px 20px; }
.placeholder-glyph { width: 50px; height: 50px; margin-bottom: 12px; border-radius: 13px; background: var(--surface); border: 1px solid var(--line); display: grid; place-items: center; color: #a6a9bd; }
.kw-placeholder h3, .kw-empty h3 { color: var(--ink); font-size: 15px; margin: 0 0 5px; }
.kw-placeholder p, .kw-empty p { font-size: 13px; max-width: 400px; margin: 0; }
.doc-skeleton { border: 1px solid var(--line); border-radius: 12px; background: var(--surface); padding: 4px 16px; }
.sk-row { display: flex; gap: 12px; align-items: center; padding: 12px 0; border-bottom: 1px solid var(--line); }
.sk-row:last-child { border-bottom: 0; }
.sk-grow { flex: 1; }
.sk-line { height: 10px; border-radius: 99px; background: linear-gradient(90deg, #eef0f6 25%, #f6f7fb 45%, #eef0f6 65%); background-size: 200% 100%; animation: shimmer 1.2s infinite; margin-bottom: 7px; }
.sk-line:last-child { margin-bottom: 0; }
.w12 { width: 38px; height: 44px; border-radius: 8px; flex: 0 0 38px; }
.w40 { width: 40%; }
.w60 { width: 60%; }
@keyframes shimmer { to { background-position: -200% 0; } }

/* ===== 轻提示 ===== */
.toast { position: absolute; top: 14px; left: 50%; transform: translateX(-50%); z-index: 80; background: var(--ink); color: #fff; border-radius: 10px; padding: 9px 16px; font-size: 12.5px; box-shadow: 0 8px 24px rgba(34, 37, 59, .25); max-width: min(520px, 90vw); }
.pop-enter-active, .pop-leave-active { transition: all .2s ease; }
.pop-enter-from, .pop-leave-to { opacity: 0; transform: translate(-50%, -6px); }

@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
</style>

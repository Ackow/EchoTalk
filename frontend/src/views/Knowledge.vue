<template>
  <!-- 知识工作区：场景资料 + 个人资料（阶段二）+ 实体关系图谱（阶段三）。
       可见性约定：源文件标题行 [user] / [ai] 标注即事实源，界面不做开关。 -->
  <section class="kw-page">
    <!-- 工具行：资料范围切换 + 上传 -->
    <div class="kw-toolbar">
      <div class="seg-filter" role="tablist" aria-label="资料范围">
        <button class="seg-item" :class="{ active: scope === 'scene' }" type="button" role="tab" :aria-selected="scope === 'scene'" @click="scope = 'scene'">
          场景资料<span class="seg-count">{{ sceneDocTotal }}</span>
        </button>
        <button class="seg-item" :class="{ active: scope === 'personal' }" type="button" role="tab" :aria-selected="scope === 'personal'" @click="scope = 'personal'">
          个人资料<span class="seg-count">{{ personalDocs.length }}</span>
        </button>
      </div>
      <div class="toolbar-actions">
        <button
          class="primary-button slim"
          type="button"
          :disabled="!canUpload"
          :title="canUpload ? '支持拖放 PDF / TXT / Markdown 到下方区域' : session.token ? '请先选择场景' : '登录后可上传资料'"
          @click="pickFile"
        >
          <AppIcon name="upload" :size="14" />上传资料
        </button>
        <input ref="fileInput" type="file" accept=".pdf,.txt,.md,.markdown" class="hidden-input" @change="onFileChange">
      </div>
    </div>

    <!-- 空态：个人未登录 / 无自有场景 -->
    <div v-if="!showContent" class="kw-empty">
      <div class="placeholder-glyph"><AppIcon :name="session.token ? 'plus' : 'lock'" :size="20" /></div>
      <template v-if="scope === 'personal'">
        <h3>登录后使用个人工作区</h3>
        <p>个人资料（简历、目标 JD、项目文档等）跨场景复用，登录后即可上传与管理。</p>
      </template>
      <template v-else-if="!session.token">
        <h3>登录后管理场景资料</h3>
        <p>知识工作区用于管理你创建的场景的知识文件，登录后即可使用。</p>
      </template>
      <template v-else>
        <h3>还没有自己创建的场景</h3>
        <p>到「场景探索」创建一个场景，或复制内置场景后，即可在这里上传与管理资料。</p>
      </template>
    </div>

    <template v-else>
      <!-- 筛选行：左侧场景选择 + 右侧检索引擎与搜索框成组靠右 -->
      <div class="filter-row">
        <div class="filter-left">
          <AppSelect
            v-if="scope === 'scene'"
            v-model="activeSceneId"
            :options="sceneOptions"
            label="场景"
            aria-label="选择要管理的场景"
          />
          <span v-else class="search-scope-label">个人资料</span>
        </div>
        <div class="filter-right">
          <AppSelect
            v-model="searchEngine"
            :options="engineOptions"
            label="检索"
            aria-label="选择检索引擎"
          />
          <label class="search-box" :title="searchEngine === 'lightrag' ? '图谱检索：LightRAG 实体关系上下文（较慢）' : '混合检索：关键词 + 语义向量'">
            <AppIcon name="search" :size="14" />
            <input
              v-model="searchQuery"
              type="text"
              :placeholder="searchEngine === 'lightrag' ? '图谱检索，回车执行' : '搜索资料内容，回车检索'"
              @keyup.enter="runSearch"
            >
            <button v-if="searchQuery || searchState.active" class="search-clear" type="button" title="清除检索" @click="clearSearch">
              <AppIcon name="x" :size="13" />
            </button>
          </label>
        </div>
      </div>

      <!-- 双栏：左资料管理 + 右实体关系图谱 -->
      <div class="kw-columns">
        <div class="kw-main">
          <p v-if="scope === 'personal'" class="personal-hint">
            个人资料独立于场景存储、跨场景可用。
          </p>

          <!-- 拖放上传区 -->
          <div
            class="dropzone"
            :class="{ drag }"
            tabindex="0"
            role="button"
            aria-label="拖放或选择上传资料：支持 PDF、TXT、Markdown，单文件 10 MB 以内"
            @click="pickFile"
            @keydown.enter="pickFile"
            @dragover.prevent
            @dragenter.prevent="drag = true"
            @dragleave="drag = false"
            @drop.prevent="onDrop"
          >
            <AppIcon name="upload" :size="16" />
            <span class="dz-text">拖放文件到此处，或点击上传</span>
            <span class="dz-hint">{{ scope === 'personal' ? 'PDF、TXT、Markdown · 单文件 10 MB · 个人资料全部对您可见，无需可见性标注' : 'PDF、TXT、Markdown · 单文件 10 MB · 标题行标注 [ai] / [user] 控制分节可见性' }}</span>
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
          <div v-if="listLoading || searching" class="doc-skeleton" aria-busy="true" aria-label="正在加载资料">
            <div v-for="n in 2" :key="n" class="sk-row"><div class="sk-line w12"></div><div class="sk-grow"><div class="sk-line w60"></div><div class="sk-line w40"></div></div></div>
          </div>

          <!-- 检索结果：混合（关键词+向量 RRF）或 LightRAG 图谱上下文 -->
          <div v-else-if="searchState.active" class="doc-card search-results">
            <div class="search-meta">
              <span>「{{ searchState.q }}」的检索结果<template v-if="searchEngine !== 'lightrag'"> · {{ searchState.items.length }} 条</template></span>
              <span v-if="searchEngine === 'lightrag'" class="search-mode hybrid">LightRAG 图谱上下文</span>
              <span v-else-if="searchState.mode === 'hybrid'" class="search-mode hybrid">关键词 + 语义向量融合</span>
              <span v-else-if="searchState.mode === 'keyword'" class="search-mode">关键词模式 · 配置嵌入 API Key 后启用语义检索</span>
            </div>
            <template v-if="searchEngine === 'lightrag'">
              <pre class="lr-context">{{ searchState.context || '图谱索引为空或仍在后台构建，请稍后重试。' }}</pre>
            </template>
            <template v-else>
              <div
                v-for="item in searchState.items"
                :key="item.chunk_id"
                class="search-item"
                role="button"
                tabindex="0"
                @click="openResult(item)"
                @keydown.enter="openResult(item)"
              >
                <div class="si-head">
                  <span class="file-badge sm" :data-type="docType(item.filename)">{{ docType(item.filename) }}</span>
                  <span class="si-name">{{ item.filename }}</span>
                  <span class="si-section">{{ item.section }}</span>
                  <span v-if="scope === 'scene'" class="tag" :class="item.visibility === 'user' ? 'user' : 'ai'">{{ item.visibility === 'user' ? '用户可见' : '仅 AI' }}</span>
                </div>
                <p class="si-text" v-html="highlight(item.text)"></p>
              </div>
              <p v-if="!searchState.items.length" class="chunk-empty">没有匹配的内容，换个说法试试</p>
            </template>
          </div>

          <div v-else-if="displayDocs.length" class="doc-card">
            <div v-for="doc in displayDocs" :key="doc.id" class="doc-row">
              <div class="doc-main">
                <span class="file-badge" :data-type="docType(doc.filename)">{{ docType(doc.filename) }}</span>
                <div class="doc-info">
                  <div class="doc-name">
                    <span class="name-text">{{ doc.filename }}</span>
                    <span class="tag ok"><AppIcon name="check" :size="11" />{{ doc.chunk_count }} 块</span>
                    <span v-if="scope === 'scene'" class="tag" :class="doc.visibility === 'user' ? 'user' : 'ai'">
                      <AppIcon :name="doc.visibility === 'user' ? 'eye' : 'bot'" :size="11" />{{ doc.visibility === 'user' ? '用户可见' : '仅 AI' }}
                    </span>
                  </div>
                  <p class="doc-desc">{{ scope === 'personal' ? '个人工作区 · 跨场景可用' : (doc.owner_id ? '我上传的' : '随场景复制') }} · {{ doc.sections.length }} 个分节</p>
                </div>
                <div class="doc-actions">
                  <button
                    v-if="doc.sections.length && !doc.virtual"
                    class="icon-btn"
                    type="button"
                    :aria-expanded="expanded.has(docKey(doc.id))"
                    :title="expanded.has(docKey(doc.id)) ? '收起分节' : '分节可见性'"
                    @click="toggleExpand(doc)"
                  >
                    <AppIcon name="chevron-down" :size="15" :class="{ flip: expanded.has(docKey(doc.id)) }" />
                  </button>
                  <button v-if="canEdit(doc) && docEditable(doc)" class="icon-btn" type="button" title="编辑源文件" @click="openSourceEditor(doc)">
                    <AppIcon name="pencil" :size="14" />
                  </button>
                  <button v-if="canEdit(doc)" class="icon-btn danger" type="button" title="删除资料" @click="confirming = confirming === docKey(doc.id) ? null : docKey(doc.id)">
                    <AppIcon name="trash" :size="14" />
                  </button>
                </div>
              </div>

              <!-- 分节列表：可见性标签（由 [user]/[ai] 标注决定，只读）+ 分块查看入口 -->
              <div v-if="expanded.has(docKey(doc.id))" class="sections">
                <div v-for="sec in doc.sections" :key="sec.section" class="section-block">
                  <div class="section-row">
                    <span class="name">{{ sec.section }}</span>
                    <span class="snippet">{{ sec.preview }}</span>
                    <span v-if="scope === 'scene'" class="tag" :class="sec.visibility === 'user' ? 'user' : 'ai'">{{ sec.visibility === 'user' ? '用户可见' : '仅 AI' }}</span>
                    <button
                      v-if="!doc.virtual"
                      class="icon-btn"
                      type="button"
                      title="查看分块内容"
                      @click="openChunkModal(doc, sec)"
                    >
                      <AppIcon name="chevron-right" :size="14" />
                    </button>
                  </div>
                </div>
              </div>

              <!-- 删除确认 -->
              <div v-if="confirming === docKey(doc.id)" class="confirm-bar" role="alertdialog" aria-label="确认删除资料">
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
            <h3>{{ emptyTitle }}</h3>
            <p>{{ emptyDesc }}</p>
          </div>
        </div>

        <!-- 右栏：实体关系图谱（LightRAG 真实图谱优先，无索引时回退规则版） -->
        <aside class="kw-side" aria-label="实体关系图谱">
          <div class="side-card">
            <div class="side-head">
              <h4>实体关系</h4>
              <span class="side-tag">{{ graphBadge }}</span>
            </div>
            <div v-if="graphLoading" class="graph-note">图谱生成中…</div>
            <!-- 索引状态提示：后台构建对用户可见，完成后自动切换为 LightRAG 图谱 -->
            <div v-else-if="graphData?.index?.status === 'building'" class="graph-note">
              实体图谱正在后台生成（{{ graphData.index.done }}/{{ graphData.index.total }}），完成后自动切换，无需刷新
            </div>
            <div v-else-if="graphData?.index?.status === 'error'" class="graph-note">
              实体图谱生成失败：{{ graphData.index.error || '未知原因' }}；请检查抽取 LLM 配置后重新触发重建
            </div>
            <!-- LightRAG 版：实体-关系力导向图（节点大小 = 关联数，颜色 = 实体类型） -->
            <div v-else-if="lrLayout" ref="lrWrap" class="rag-graph-wrap lr">
              <svg
                ref="lrSvg"
                class="rag-graph lr-canvas"
                :viewBox="`${lrView.x} ${lrView.y} ${lrView.w} ${lrView.h}`"
                :style="{ height: lrLayout.height + 'px' }"
                aria-label="实体关系图"
                @wheel.prevent="onLrWheel"
                @mousedown="onLrDown"
                @mousemove="onLrMove"
                @mouseup="onLrUp"
                @mouseleave="onLrUp"
              >
                <g class="edges">
                  <path
                    v-for="e in lrLayout.edges"
                    :key="`lr:${e.source}:${e.target}`"
                    class="lr-edge"
                    :class="{ hot: isLrHot(e), dim: isLrDim(e) }"
                    :d="lrEdgePath(e)"
                  />
                </g>
                <g
                  v-for="n in lrLayout.nodes"
                  :key="n.id"
                  class="lr-node"
                  :class="{ dim: isLrDimNode(n), active: lrSelectedId === n.id }"
                  @click="toggleLrNode(n)"
                >
                  <circle :cx="n.x" :cy="n.y" :r="n.r" :fill="lrTypeColor(n.entity_type)" fill-opacity="0.16" :stroke="lrTypeColor(n.entity_type)" stroke-width="1.4" />
                  <circle :cx="n.x" :cy="n.y" :r="Math.min(n.r, 3.2)" :fill="lrTypeColor(n.entity_type)" />
                  <text :x="n.x" :y="n.y + n.r + 9">{{ shortName(n.label, 9) }}</text>
                  <title>{{ n.label }}（{{ lrTypeLabel(n.entity_type) }}）· {{ n.degree }} 条关联 · {{ n.description }}</title>
                </g>
              </svg>
              <div class="lr-zoom">
                <button type="button" title="放大" @click="lrZoomBy(1.3)">+</button>
                <button type="button" title="缩小" @click="lrZoomBy(0.77)">−</button>
                <button type="button" class="lr-zoom-reset" title="重置视图" @click="lrResetView">重置</button>
              </div>
            </div>
            <!-- 详情 / 截断提示 / 类型图例：放在滚动容器外，窗口再矮也完整显示 -->
            <template v-if="lrLayout">
              <div v-if="lrSelected" class="lr-detail">
                <p class="lr-detail-name">
                  <span class="lr-dot" :style="{ background: lrTypeColor(lrSelected.entity_type) }" />
                  {{ lrSelected.label }}
                  <span class="lr-detail-type">{{ lrTypeLabel(lrSelected.entity_type) }} · {{ lrSelected.degree }} 条关联</span>
                </p>
                <p class="lr-detail-desc">{{ lrSelected.description || '暂无描述' }}</p>
              </div>
              <p v-if="lrLayout.truncated > 0" class="graph-note">已展示关联最多的 {{ lrLayout.nodes.length }} 个实体，还有 {{ lrLayout.truncated }} 个未展示</p>
              <div class="lr-type-legend">
                <span v-for="t in lrLegendTypes" :key="t" class="lr-legend-item">
                  <span class="lr-dot" :style="{ background: lrTypeColor(t) }" />{{ lrTypeLabel(t) }}
                </span>
              </div>
            </template>
            <!-- 规则版回退：文件-分节双列图 -->
            <div v-else-if="graphLayout" class="rag-graph-wrap">
              <svg class="rag-graph" :viewBox="`0 0 296 ${graphLayout.height}`" aria-label="实体关系图">
                <g class="edges">
                  <template v-for="e in graphData.edges" :key="`${e.kind}:${e.source}:${e.target}`">
                    <path v-if="e.kind === 'contains' && layoutPos(e.source) && layoutPos(e.target)" class="contains" :d="containsPath(e)" :stroke="fileColor(e.source)" />
                    <path v-else-if="e.kind === 'related' && layoutPos(e.source) && layoutPos(e.target)" class="related" :d="relatedPath(e)" />
                  </template>
                </g>
                <g v-for="f in graphLayout.files" :key="f.id" class="node file">
                  <rect :x="graphLayout.pos[f.id].x" :y="graphLayout.pos[f.id].y" :width="graphLayout.pos[f.id].w" :height="graphLayout.pos[f.id].h" rx="6" :style="{ stroke: fileColor(f.id) }" />
                  <text :x="graphLayout.pos[f.id].x + 54" :y="graphLayout.pos[f.id].y + 19" :style="{ fill: fileColor(f.id) }">{{ shortName(f.label) }}</text>
                  <title>{{ f.label }} · {{ f.sections_count }} 个分节</title>
                </g>
                <g v-for="s in graphLayout.sections" :key="s.id" class="node section" :class="{ bridge: s.files.length > 1 }">
                  <rect :x="graphLayout.pos[s.id].x" :y="graphLayout.pos[s.id].y" :width="graphLayout.pos[s.id].w" :height="graphLayout.pos[s.id].h" rx="6" />
                  <circle v-if="s.visibility !== 'user'" class="ai-dot" :cx="graphLayout.pos[s.id].x + graphLayout.pos[s.id].w - 9" :cy="graphLayout.pos[s.id].y + graphLayout.pos[s.id].h / 2" r="3" />
                  <text :x="graphLayout.pos[s.id].x + graphLayout.pos[s.id].w / 2 - 3" :y="graphLayout.pos[s.id].y + 15">{{ shortName(s.label, 10) }}</text>
                  <title>{{ s.label }} · {{ s.files.length }} 个文件 · {{ s.chunk_count }} 块 · {{ visibilityLabel(s.visibility) }}</title>
                </g>
              </svg>
              <p v-if="graphLayout.truncated" class="graph-note">分节过多，仅展示前 {{ graphLayout.sections.length }} 个</p>
            </div>
            <p v-else class="graph-note">上传资料后自动生成实体关系图</p>
            <p class="side-desc">{{ graphData?.engine === 'lightrag'
              ? '颜色 = 实体类型，大小 = 关联数；点击聚焦，悬停看详情。'
              : '同名分节跨文件合并；虚线 = 内容相关。索引完成后切换。' }}</p>
          </div>
          <div class="side-card">
            <div class="side-head"><h4>可见性图例</h4></div>
            <div class="legend-row"><span class="tag user"><AppIcon name="eye" :size="11" />用户可见</span><span>对话参考面板中展示给学习者</span></div>
            <div class="legend-row"><span class="tag ai"><AppIcon name="bot" :size="11" />仅 AI</span><span>仅参与 AI 检索，不对外展示</span></div>
            <template v-if="scope === 'scene'">
              <div class="legend-row"><span class="legend-mark">[ai]</span><span>标题行内标注，该分节仅 AI 可见</span></div>
              <div class="legend-row"><span class="legend-mark">[user]</span><span>标题行声明用户可见；未标注默认用户可见</span></div>
            </template>
<!--            <p v-else class="legend-note">个人资料全部对您可见，不涉及 [ai] / [user] 标注。</p>-->
            <div class="legend-row"><span class="legend-mark">图谱</span><span>{{ graphData?.engine === 'lightrag'
              ? 'LightRAG 实体关系网络：颜色区分实体类型，圆点大小 = 关联数量'
              : '颜色区分资料文件；深色圆点 = 仅 AI 分节；虚线 = 跨文件内容相关' }}</span></div>
          </div>
        </aside>
      </div>
    </template>

    <!-- 分块内容弹窗：分块只读渲染 + 源文件编辑（milkdown 所见即所得） -->
    <transition name="fade">
      <div v-if="chunkModal" class="modal-backdrop" @mousedown.self="closeChunkModal">
        <div class="modal-card" role="dialog" aria-modal="true" :aria-label="chunkModal.sec ? `分块内容：${chunkModal.sec.section}` : `编辑源文件：${chunkModal.doc.filename}`">
          <header class="modal-head">
            <span class="file-badge sm" :data-type="docType(chunkModal.doc.filename)">{{ docType(chunkModal.doc.filename) }}</span>
            <div class="modal-titles">
              <h3>{{ chunkModal.doc.filename }}</h3>
              <p class="modal-sub">{{ sourceEdit ? '编辑源文件 · 保存后重新解析分块' : (chunkModal.sec?.section || '') }}</p>
            </div>
            <span v-if="chunkModal.sec" class="tag" :class="chunkModal.sec.visibility === 'user' ? 'user' : 'ai'">
              <AppIcon :name="chunkModal.sec.visibility === 'user' ? 'eye' : 'bot'" :size="11" />
              {{ chunkModal.sec.visibility === 'user' ? '用户可见' : '仅 AI' }}
            </span>
            <button v-if="!sourceEdit && canEdit(chunkModal.doc) && docEditable(chunkModal.doc)" class="icon-btn" type="button" title="编辑源文件" @click="startSourceEdit">
              <AppIcon name="pencil" :size="14" />
            </button>
            <button class="icon-btn" type="button" title="关闭" aria-label="关闭" @click="closeChunkModal">
              <AppIcon name="x" :size="15" />
            </button>
          </header>
          <div class="modal-body">
            <!-- 源文件编辑模式：整个文件一棵所见即所得文档树 -->
            <p v-if="sourceLoading" class="chunk-loading">正在读取源文件…</p>
            <template v-else-if="sourceEdit">
              <div :ref="setEditorHost" class="md-editor source-editor" aria-label="源文件编辑器"></div>
              <div class="chunk-actions">
                <span class="chunk-meta">所见即所得 · Markdown 源文件 · 保存后重新分块</span>
                <span class="chunk-btns">
                  <button class="btn-ghost" type="button" :disabled="sourceSaving" @click="cancelSourceEdit">取消</button>
                  <button class="btn-save" type="button" :disabled="sourceSaving" @click="saveSource">{{ sourceSaving ? '重新解析中…' : '保存并重新解析' }}</button>
                </span>
              </div>
            </template>
            <!-- 只读模式：分块 Markdown 渲染 -->
            <template v-else>
              <p v-if="chunksLoading === modalChunkKey" class="chunk-loading">正在加载分块内容…</p>
              <template v-else>
                <div v-for="ch in modalChunks" :key="ch.id" class="chunk-item">
                  <div class="md-view" v-html="renderMd(ch.text)"></div>
                  <div class="chunk-actions">
                    <span class="chunk-meta">分块 #{{ ch.ordinal }} · {{ ch.text.length }} 字</span>
                  </div>
                </div>
                <p v-if="!modalChunks.length" class="chunk-empty">该分节暂无分块内容</p>
              </template>
            </template>
          </div>
        </div>
      </div>
    </transition>

    <!-- 轻提示 -->
    <transition name="pop">
      <div v-if="notice" class="toast" role="status">{{ notice }}</div>
    </transition>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import AppSelect from '../components/AppSelect.vue'
import { session } from '../auth/session'
import {
  deleteKnowledge, deletePersonalDocument, getDocumentSource, getPersonalSource,
  getSectionOverview, lightragPersonalSearch, lightragSceneSearch, listDocumentChunks,
  listKnowledgeDocuments, listPersonalChunks,
  listPersonalDocuments, listScenes, personalGraph, reindexSceneKnowledge, sceneGraph,
  searchPersonalKnowledge, searchSceneKnowledge, updateDocumentSource, updatePersonalSource,
  uploadKnowledge, uploadPersonalKnowledge,
} from '../api/scenes'
import { marked } from 'marked'
// milkdown：基于 ProseMirror 的所见即所得 Markdown 编辑器，纯本地运行
import { Editor, rootCtx, defaultValueCtx } from '@milkdown/kit/core'
import { commonmark } from '@milkdown/kit/preset/commonmark'
import { getMarkdown } from '@milkdown/kit/utils'
import '@milkdown/kit/prose/view/style/prosemirror.css' // 编辑器基础结构样式

// 场景资料支持类型与上限，与后端 knowledge.py 约定一致（§9.5）。
const ALLOWED_EXTENSIONS = ['pdf', 'txt', 'md', 'markdown']
const MAX_FILE_SIZE = 10 * 1024 * 1024

const scope = ref('scene') // 资料范围：scene（按场景）/ personal（跨场景，阶段二）
const scenes = ref([]) // 本人创建的场景（含 knowledge_count）
const activeSceneId = ref('')
const docs = ref([]) // 当前场景的文件级资料列表
const docsLoading = ref(false)
const personalDocs = ref([]) // 个人工作区资料列表
const personalLoading = ref(false)
const personalLoaded = ref(false)
const uploadProgress = ref(null) // { name, percent } 上传进度
const drag = ref(false)
const expanded = ref(new Set()) // 展开分节的资料 key：scope:docId
const confirming = ref(null) // 待删除确认的资料 key
const chunkMap = ref({}) // `${scope}:${docId}` -> 分块明细数组（含正文全文）
const chunksLoading = ref(null) // 正在加载分块的 chunkMap key
const chunkModal = ref(null) // 弹窗上下文 { doc, sec | null, scope }
const sourceEdit = ref(false) // 弹窗是否处于源文件编辑模式
const sourceLoading = ref(false) // 正在读取源文件
const sourceSaving = ref(false) // 正在保存并重新解析
let milkdownEditor = null // milkdown 编辑器实例（无需响应式）
let editorHost = null // 编辑器挂载 DOM（函数 ref 赋值）
const graphData = ref(null) // 实体关系图谱（阶段三）
const graphLoading = ref(false)
const searchQuery = ref('') // 检索输入（回车触发）
const searching = ref(false) // 检索请求进行中
const searchEngine = ref('hybrid') // 检索引擎：hybrid（关键词+向量 RRF）/ lightrag（图谱上下文）
const engineOptions = [
  { value: 'hybrid', label: '混合检索', hint: '快' },
  { value: 'lightrag', label: '图谱检索', hint: 'LightRAG · 较慢' },
]
const searchState = ref({ active: false, q: '', mode: 'none', items: [], context: '' }) // 检索结果
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
    // 工作区只管理本人创建的场景（与场景探索页 isMine 判定一致）；内置/他人场景的资料在场景编辑器维护
    const all = data.items || data // 响应为 { items: [...] }，兼容裸数组
    scenes.value = all.filter((s) => s.source !== 'builtin' && s.author_id === session.user?.id)
    // 缺省选中第一个有资料的场景，否则第一个
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
  chunkMap.value = {}
  chunkModal.value = null
  sourceEdit.value = false
  clearSearch() // 资料集变化，旧结果作废
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

async function loadPersonal() {
  if (!session.token) return
  personalLoading.value = true
  confirming.value = null
  clearSearch() // 资料集变化，旧结果作废
  try {
    const { data } = await listPersonalDocuments()
    personalDocs.value = data.documents
    personalLoaded.value = true
  } catch (error) {
    notify(error.message || '个人资料加载失败')
  } finally {
    personalLoading.value = false
  }
}

async function loadGraph() {
  lrSelectedId.value = '' // 图谱数据源变化，清空聚焦的实体
  // 个人图谱不依赖场景选择；场景图谱需要先选中场景
  if (scope.value === 'personal') {
    if (!session.token) {
      graphData.value = null
      return
    }
  } else if (!activeSceneId.value) {
    return
  }
  graphLoading.value = true
  try {
    const { data } = scope.value === 'personal' ? await personalGraph() : await sceneGraph(activeSceneId.value)
    graphData.value = data
  } catch {
    graphData.value = null
  } finally {
    graphLoading.value = false
  }
}

watch(activeSceneId, () => {
  loadDocs()
  loadGraph()
})
watch(scope, (val) => {
  clearSearch() // 检索结果不跨范围保留
  graphData.value = null // 切换范围时清空图谱，避免展示上一范围的图
  if (val === 'personal') {
    if (!personalLoaded.value) loadPersonal()
    loadGraph()
  }
})

/* ---- 索引状态展示：构建中每 10s 轮询图谱端点，ready/error 后自动停止 ---- */

// 图谱右上角标签：优先反映索引状态（构建中 / 失败），其次按引擎区分
const graphBadge = computed(() => {
  const index = graphData.value?.index
  if (index?.status === 'building') return `索引构建中 ${index.done}/${index.total}`
  if (index?.status === 'error') return '索引失败'
  if (graphData.value?.engine === 'lightrag') return 'LightRAG · LLM 抽取'
  return '自动抽取 · 规则版'
})

let graphPollTimer = null
watch(graphData, (val) => {
  if (graphPollTimer) { clearInterval(graphPollTimer); graphPollTimer = null }
  if (val?.index?.status === 'building') {
    graphPollTimer = setInterval(() => { loadGraph() }, 10000)
  }
})

/* ---- 统一视图（场景 / 个人共用一套列表与弹窗） ---- */

const displayDocs = computed(() => (scope.value === 'personal' ? personalDocs.value : docs.value))
const listLoading = computed(() => (scope.value === 'personal' ? personalLoading.value : docsLoading.value))
const showContent = computed(() => (scope.value === 'personal' ? !!session.token : scenes.value.length > 0))
const emptyTitle = computed(() => (scope.value === 'personal' ? '还没有个人资料' : '该场景暂无资料'))
const emptyDesc = computed(() =>
  scope.value === 'personal'
    ? '上传简历、目标 JD 或项目文档，跨场景复用；资料全部对您可见，无需可见性标注。'
    : '上传 PDF、TXT 或 Markdown，解析分块后将作为场景对话与面试的背景知识。')

const sceneDocTotal = computed(() => scenes.value.reduce((sum, s) => sum + (s.knowledge_count || 0), 0))

// 列表已过滤为本人创建的场景，全部可写；保留 source 守卫以防权限模型变化
const activeScene = computed(() => scenes.value.find((s) => s.id === activeSceneId.value))
const sceneWritable = computed(() => !!activeScene.value && activeScene.value.source !== 'builtin')
const sceneOptions = computed(() => scenes.value.map((s) => ({ value: s.id, label: s.name, hint: `${s.knowledge_count || 0} 份资料` })))

const canUpload = computed(() => (scope.value === 'personal' ? !!session.token : sceneWritable.value))
const canEdit = (doc) => (scope.value === 'personal' || chunkModal.value?.scope === 'personal' ? true : sceneWritable.value && !doc.virtual)

const docKey = (docId) => `${scope.value}:${docId}`

function docType(filename) {
  const suffix = filename.split('.').pop().toLowerCase()
  return suffix === 'markdown' ? 'md' : suffix
}

// 文本类资料源文件可编辑（pdf 为提取文本，不支持回写）
const docEditable = (doc) => ['md', 'txt'].includes(docType(doc.filename))

/* ---- 上传 ---- */

function pickFile() {
  if (!session.token) return notify('上传资料需要先登录，点击左下角账户卡片登录。')
  if (scope.value === 'scene' && !activeSceneId.value) return notify('请先选择要管理资料的场景。')
  fileInput.value?.click()
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
  if (scope.value === 'scene' && !activeSceneId.value) return notify('请先选择要管理资料的场景。')
  uploadProgress.value = { name: file.name, percent: 0 }
  const onProgress = (event) => {
    if (event.total) uploadProgress.value.percent = Math.round((event.loaded / event.total) * 100)
  }
  try {
    if (scope.value === 'personal') {
      const { data } = await uploadPersonalKnowledge(file, onProgress)
      notify(`「${data.filename}」解析完成 · ${data.chunk_count} 块已入库`)
      await loadPersonal()
      loadGraph()
    } else {
      const { data } = await uploadKnowledge(activeSceneId.value, file, (event) => {
        if (event.total) uploadProgress.value.percent = Math.round((event.loaded / event.total) * 100)
      })
      notify(`「${data.filename}」解析完成 · ${data.chunk_count} 块已入库`)
      await loadDocs()
      loadGraph()
      scenes.value = scenes.value.map((s) => (s.id === activeSceneId.value ? { ...s, knowledge_count: (s.knowledge_count || 0) + 1 } : s))
    }
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
  const file = event.dataTransfer.files?.[0]
  if (file) uploadFile(file)
}

/* ---- 分节展开 / 删除 ---- */

function toggleExpand(doc) {
  const key = docKey(doc.id)
  const next = new Set(expanded.value)
  next.has(key) ? next.delete(key) : next.add(key)
  expanded.value = next
}

async function doDelete(doc) {
  try {
    if (scope.value === 'personal') {
      await deletePersonalDocument(doc.id)
      notify(`已删除「${doc.filename}」，源文件与解析内容同步移除`)
      confirming.value = null
      await loadPersonal()
      loadGraph()
    } else {
      await deleteKnowledge(activeSceneId.value, doc.id)
      notify(`已删除「${doc.filename}」，源文件与解析内容同步移除`)
      confirming.value = null
      await loadDocs()
      loadGraph()
      scenes.value = scenes.value.map((s) => (s.id === activeSceneId.value ? { ...s, knowledge_count: Math.max((s.knowledge_count || 1) - 1, 0) } : s))
    }
  } catch (error) {
    notify(error.message || '删除失败，请重试')
  }
}

/* ---- 分块弹窗（只读渲染）与源文件编辑（milkdown 所见即所得） ---- */

const modalChunkKey = computed(() => (chunkModal.value ? `${chunkModal.value.scope}:${chunkModal.value.doc.id}` : ''))
const modalChunks = computed(() => {
  if (!chunkModal.value) return []
  const key = modalChunkKey.value
  return (chunkMap.value[key] || []).filter((c) => c.section === chunkModal.value.sec?.section)
})

// 只读态 Markdown 渲染；内容来自用户自己上传的本地资料，桌面端离线使用
const renderMd = (text) => marked.parse(text || '', { async: false })

async function ensureChunks(docId) {
  const key = `${chunkModal.value.scope}:${docId}`
  if (chunkMap.value[key] || chunksLoading.value === key) return
  chunksLoading.value = key
  try {
    const { data } = chunkModal.value.scope === 'personal'
      ? await listPersonalChunks(docId)
      : await listDocumentChunks(activeSceneId.value, docId)
    chunkMap.value = { ...chunkMap.value, [key]: data.chunks }
  } catch (error) {
    notify(error.message || '分块内容加载失败')
  } finally {
    chunksLoading.value = null
  }
}

async function openChunkModal(doc, sec) {
  chunkModal.value = { doc, sec, scope: scope.value }
  document.body.style.overflow = 'hidden' // 弹窗打开时锁定页面滚动
  await ensureChunks(doc.id)
}

// 从资料行直接进入源文件编辑
function openSourceEditor(doc) {
  chunkModal.value = { doc, sec: null, scope: scope.value }
  document.body.style.overflow = 'hidden'
  startSourceEdit()
}

function destroyEditor() {
  if (milkdownEditor) {
    try { milkdownEditor.destroy() } catch { /* 实例可能已销毁 */ }
    milkdownEditor = null
  }
}

function closeChunkModal() {
  destroyEditor()
  sourceEdit.value = false
  chunkModal.value = null
  document.body.style.overflow = ''
}

function setEditorHost(el) {
  editorHost = el
}

async function startSourceEdit() {
  destroyEditor()
  const ctx = chunkModal.value
  if (!ctx) return
  sourceEdit.value = true
  sourceLoading.value = true
  let text = ''
  try {
    const { data } = ctx.scope === 'personal'
      ? await getPersonalSource(ctx.doc.id)
      : await getDocumentSource(activeSceneId.value, ctx.doc.id)
    if (!data.editable) {
      notify('该资料类型（PDF）不支持文本编辑，请删除后重新上传')
      closeChunkModal()
      return
    }
    text = data.text
  } catch {
    notify('源文件读取失败，请重试')
    sourceEdit.value = false
    return
  } finally {
    sourceLoading.value = false // 先解除 loading，编辑器挂载节点才会渲染
  }
  await nextTick() // loading 解除后再等一拍，确保 :ref 挂载点就位
  if (!editorHost) return
  try {
    milkdownEditor = await Editor.make()
      .config((c) => {
        c.set(rootCtx, editorHost)
        c.set(defaultValueCtx, text)
      })
      .use(commonmark)
      .create()
  } catch {
    notify('编辑器加载失败，请重试')
    sourceEdit.value = false
  }
}

function cancelSourceEdit() {
  destroyEditor()
  sourceEdit.value = false
}

async function saveSource() {
  if (!milkdownEditor) return
  let text = ''
  try {
    text = (await milkdownEditor.action(getMarkdown())).trim()
  } catch {
    text = ''
  }
  if (!text) return notify('源文件内容不能为空')
  sourceSaving.value = true
  const ctx = chunkModal.value
  try {
    const { data } = ctx.scope === 'personal'
      ? await updatePersonalSource(ctx.doc.id, text)
      : await updateDocumentSource(activeSceneId.value, ctx.doc.id, text)
    notify(`「${data.filename}」已保存并重新解析 · ${data.chunk_count} 块`)
    closeChunkModal()
    chunkMap.value = {} // 重新解析后分块全部重建，缓存作废
    if (ctx.scope === 'personal') {
      await loadPersonal()
      loadGraph()
    } else {
      await loadDocs()
      loadGraph()
      // 编辑不改变文件数，knowledge_count 不变
    }
  } catch (error) {
    notify(error.message || '保存失败，请重试')
  } finally {
    sourceSaving.value = false
  }
}

/* ---- 混合检索（Hybrid RAG）：关键词 + 语义向量，RRF 融合 ---- */

async function runSearch() {
  const q = searchQuery.value.trim()
  if (!q || searching.value) return
  if (scope.value === 'scene' && !activeSceneId.value) return notify('请先选择要检索的场景。')
  searching.value = true
  try {
    if (searchEngine.value === 'lightrag') {
      // LightRAG 图谱检索：含一次 LLM 关键词抽取调用，响应较慢（前端超时 120s）
      const { data } = scope.value === 'personal'
        ? await lightragPersonalSearch(q)
        : await lightragSceneSearch(activeSceneId.value, q)
      searchState.value = { active: true, q, mode: 'lightrag', items: [], context: data.context || '' }
    } else {
      const { data } = scope.value === 'personal'
        ? await searchPersonalKnowledge(q)
        : await searchSceneKnowledge(activeSceneId.value, q)
      searchState.value = { active: true, q, mode: data.mode, items: data.items, context: '' }
    }
  } catch (error) {
    notify(error.message || '检索失败，请重试')
  } finally {
    searching.value = false
  }
}

function clearSearch() {
  searchQuery.value = ''
  searching.value = false
  searchState.value = { active: false, q: '', mode: 'none', items: [], context: '' }
}

// 点击结果 → 打开该分块所在文件与分节的只读弹窗
function openResult(item) {
  openChunkModal(
    { id: item.document_id, filename: item.filename },
    { section: item.section, visibility: item.visibility },
  )
}

const escapeHtml = (value) =>
  String(value).replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]))

// 检索词高亮：先转义再包裹 <mark>（内容来自用户自己的本地资料，仍按不可信 HTML 处理）
function highlight(rawText) {
  const safe = escapeHtml(rawText || '')
  const q = searchState.value.q.trim()
  if (!q) return safe
  const terms = [...new Set([q, ...q.split(/\s+/)])].filter((t) => t.length >= 1)
    .sort((a, b) => b.length - a.length) // 长词优先，减少嵌套包裹
  let out = safe
  for (const term of terms) {
    const pattern = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    out = out.replace(new RegExp(pattern, 'gi'), (m) => `<mark>${m}</mark>`)
  }
  return out
}

/* ---- 实体关系图谱布局（阶段三） ---- */

const FILE_COLORS = ['#6265e8', '#1f9d6c', '#b06a1d', '#c2455e', '#0f7fa8', '#7a4bc7']
const fileColor = (fileId) => {
  const id = Number(String(fileId).replace('file:', ''))
  const idx = graphLayout.value?.files.findIndex((f) => f.id === fileId)
  return FILE_COLORS[(idx >= 0 ? idx : id) % FILE_COLORS.length]
}
const shortName = (label, max = 13) => (label.length > max ? `${label.slice(0, max - 1)}…` : label)
const visibilityLabel = (v) => (v === 'ai_only' ? '仅 AI' : v === 'mixed' ? '混合可见性' : '用户可见')

const graphLayout = computed(() => {
  if (!graphData.value || !graphData.value.nodes.length) return null
  const files = graphData.value.nodes.filter((n) => n.kind === 'file')
  const sectionsAll = graphData.value.nodes.filter((n) => n.kind === 'section')
  // 分节排序：按首个所属文件的顺序分组，减少连线交叉
  const fileIndex = new Map(files.map((f, i) => [f.id, i]))
  const ordered = [...sectionsAll].sort((a, b) => {
    const fa = Math.min(...a.files.map((id) => fileIndex.get(id) ?? 99))
    const fb = Math.min(...b.files.map((id) => fileIndex.get(id) ?? 99))
    return fa - fb || a.label.localeCompare(b.label)
  })
  const sections = ordered.slice(0, 26)
  const pos = {}
  files.forEach((f, i) => { pos[f.id] = { x: 4, y: 14 + i * 46, w: 108, h: 30 } })
  sections.forEach((s, j) => { pos[s.id] = { x: 176, y: 10 + j * 30, w: 116, h: 22 } })
  const height = Math.max(files.length * 46 + 16, sections.length * 30 + 14, 120)
  return { files, sections, pos, height, truncated: ordered.length > sections.length }
})

const layoutPos = (id) => graphLayout.value?.pos[id] || null

function containsPath(e) {
  const a = layoutPos(e.source)
  const b = layoutPos(e.target)
  if (!a || !b) return ''
  const x1 = a.x + a.w
  const y1 = a.y + a.h / 2
  const y2 = b.y + b.h / 2
  const mid = (x1 + b.x) / 2
  return `M ${x1} ${y1} C ${mid} ${y1}, ${mid} ${y2}, ${b.x} ${y2}`
}

function relatedPath(e) {
  const a = layoutPos(e.source)
  const b = layoutPos(e.target)
  if (!a || !b) return ''
  const x = a.x + a.w
  const y1 = a.y + a.h / 2
  const y2 = b.y + b.h / 2
  return `M ${x} ${y1} C ${x + 28} ${y1}, ${x + 28} ${y2}, ${x} ${y2}`
}

/* ---- LightRAG 实体关系网络（LLM 抽取版图谱） ---- */

// 实体类型 → 颜色/中文名（LightRAG 常见类型；未识别类型归 other）
const LR_TYPE_STYLE = {
  person: { color: '#c2455e', label: '人物' },
  organization: { color: '#6265e8', label: '组织' },
  concept: { color: '#7a4bc7', label: '概念' },
  method: { color: '#1f9d6c', label: '方法' },
  event: { color: '#b06a1d', label: '事件' },
  location: { color: '#0f7fa8', label: '地点' },
  technology: { color: '#0f7fa8', label: '技术' },
}
const lrTypeColor = (type) => (LR_TYPE_STYLE[type] || { color: '#8a8da3' }).color
const lrTypeLabel = (type) => (LR_TYPE_STYLE[type] || { label: '实体' }).label
const lrLegendTypes = computed(() => {
  if (graphData.value?.engine !== 'lightrag') return []
  const present = new Set(graphData.value.nodes.map((n) => n.entity_type))
  const known = Object.keys(LR_TYPE_STYLE).filter((t) => present.has(t))
  return present.has('other') || known.length === 0 ? [...known, 'other'] : known
})

const LR_SHOW = 26 // 默认展示关联数最多的前 N 个实体（防止全图连线过密）
const lrSelectedId = ref('')

// 画布宽度跟随右栏实际宽度：窗口拉宽后画布同步加高，图不再挤在小区域
const lrWrap = ref(null)
const lrWrapWidth = ref(296)
// 画布可用高度跟随窗口高度：窗口越高，图谱画布越高
const lrWinHeight = ref(window.innerHeight)
let lrResizeObserver = null
let lrResizeTimer = null

watch(lrWrap, (el, old) => {
  if (old && lrResizeObserver) lrResizeObserver.unobserve(old)
  if (el && lrResizeObserver) lrResizeObserver.observe(el)
})

function onWindowResize() {
  lrWinHeight.value = window.innerHeight
}

const lrSelected = computed(() => lrLayout.value?.nodes.find((n) => n.id === lrSelectedId.value) || null)

function toggleLrNode(node) {
  if (lrMovedPx > 5) return // 拖拽平移后的松手不算点击，避免误聚焦
  lrSelectedId.value = lrSelectedId.value === node.id ? '' : node.id
}

/* ---- 图谱缩放与平移：viewBox 驱动；滚轮以鼠标位置为中心缩放，按住拖拽平移 ---- */
const lrSvg = ref(null)
const lrView = ref({ x: 0, y: 0, w: 0, h: 0 })
let lrDrag = null // { sx, sy, view } 拖拽起点
let lrMovedPx = 0 // 本次按下的累计位移（区分拖拽与点击）

function lrClampWidth(w) {
  const base = lrLayout.value
  return Math.min(base.width * 2.5, Math.max(base.width * 0.35, w))
}

// 屏幕坐标 → viewBox 坐标
function lrSvgPoint(evt) {
  const rect = lrSvg.value.getBoundingClientRect()
  const v = lrView.value
  return {
    x: v.x + (evt.clientX - rect.left) * (v.w / rect.width),
    y: v.y + (evt.clientY - rect.top) * (v.h / rect.height),
  }
}

function onLrWheel(evt) {
  if (!lrLayout.value || !lrSvg.value) return
  const p = lrSvgPoint(evt)
  const v = lrView.value
  const nw = lrClampWidth(v.w * (evt.deltaY < 0 ? 0.87 : 1.15))
  const k = nw / v.w
  lrView.value = { w: nw, h: v.h * k, x: p.x - (p.x - v.x) * k, y: p.y - (p.y - v.y) * k }
}

function lrZoomBy(factor) {
  if (!lrLayout.value) return
  const v = lrView.value
  const cx = v.x + v.w / 2
  const cy = v.y + v.h / 2
  const nw = lrClampWidth(v.w / factor)
  const k = nw / v.w
  lrView.value = { w: nw, h: v.h * k, x: cx - (cx - v.x) * k, y: cy - (cy - v.y) * k }
}

function lrResetView() {
  const layout = lrLayout.value
  if (layout) lrView.value = { x: 0, y: 0, w: layout.width, h: layout.height }
}

function onLrDown(evt) {
  lrDrag = { sx: evt.clientX, sy: evt.clientY, view: { ...lrView.value } }
  lrMovedPx = 0
}

function onLrMove(evt) {
  if (!lrDrag || !lrSvg.value) return
  const rect = lrSvg.value.getBoundingClientRect()
  const dx = (evt.clientX - lrDrag.sx) * (lrDrag.view.w / rect.width)
  const dy = (evt.clientY - lrDrag.sy) * (lrDrag.view.h / rect.height)
  lrMovedPx = Math.max(lrMovedPx, Math.abs(evt.clientX - lrDrag.sx) + Math.abs(evt.clientY - lrDrag.sy))
  lrView.value = { ...lrDrag.view, x: lrDrag.view.x - dx, y: lrDrag.view.y - dy }
}

function onLrUp() {
  lrDrag = null
}

// 选中节点的邻居集合（高亮其邻边、淡化无关节点）；未选中时为 null 表示全部常态显示
const lrNeighborSet = computed(() => {
  if (!lrSelectedId.value) return null
  const neighbors = new Set()
  for (const e of graphData.value.edges) {
    if (e.source === lrSelectedId.value) neighbors.add(e.target)
    if (e.target === lrSelectedId.value) neighbors.add(e.source)
  }
  return neighbors
})

const isLrHot = (e) => lrSelectedId.value && (e.source === lrSelectedId.value || e.target === lrSelectedId.value)
const isLrDim = (e) => lrSelectedId.value && !isLrHot(e)
const isLrDimNode = (n) => {
  if (!lrNeighborSet.value || n.id === lrSelectedId.value) return false
  return !lrNeighborSet.value.has(n.id)
}

function lrEdgePath(e) {
  const pos = lrLayout.value?.pos
  const a = pos?.[e.source]
  const b = pos?.[e.target]
  if (!a || !b) return ''
  // 从圆边缘起止，避免连线压住圆点
  const dx = b.x - a.x
  const dy = b.y - a.y
  const d = Math.hypot(dx, dy) || 1
  const x1 = a.x + (dx / d) * a.r
  const y1 = a.y + (dy / d) * a.r
  const x2 = b.x - (dx / d) * b.r
  const y2 = b.y - (dy / d) * b.r
  return `M ${x1} ${y1} L ${x2} ${y2}`
}

// 简易力导向布局（Fruchterman-Reingold 简化版）：斥力 + 边弹簧 + 向心力，预计算坐标
function lrForceSim(nodes, edges, width, height) {
  const cx = width / 2
  const cy = height / 2
  const radius = Math.min(width, height) * 0.34
  nodes.forEach((n, i) => {
    const angle = (2 * Math.PI * i) / nodes.length
    n.x = cx + radius * Math.cos(angle)
    n.y = cy + radius * Math.sin(angle)
  })
  const repulsion = 2600 // 斥力系数
  const spring = 0.045 // 边弹簧刚度
  const restLength = 52 // 边理想长度
  const gravity = 0.028 // 向心力
  const byId = new Map(nodes.map((n) => [n.id, n])) // 边端点 O(1) 查找
  for (let iter = 0; iter < 300; iter++) {
    const cooling = 1 - iter / 320 // 降温：位移逐步收敛
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i]
        const b = nodes[j]
        let dx = a.x - b.x
        let dy = a.y - b.y
        let d2 = dx * dx + dy * dy
        if (d2 < 1) { dx = (Math.random() - 0.5); dy = (Math.random() - 0.5); d2 = dx * dx + dy * dy || 1 }
        const d = Math.sqrt(d2)
        const force = repulsion / d2
        const fx = (dx / d) * force
        const fy = (dy / d) * force
        a.fx = (a.fx || 0) + fx
        a.fy = (a.fy || 0) + fy
        b.fx = (b.fx || 0) - fx
        b.fy = (b.fy || 0) - fy
      }
    }
    for (const e of edges) {
      const a = byId.get(e.source)
      const b = byId.get(e.target)
      if (!a || !b) continue
      const dx = b.x - a.x
      const dy = b.y - a.y
      const d = Math.hypot(dx, dy) || 1
      const force = (d - restLength) * spring
      const fx = (dx / d) * force
      const fy = (dy / d) * force
      a.fx = (a.fx || 0) + fx
      a.fy = (a.fy || 0) + fy
      b.fx = (b.fx || 0) - fx
      b.fy = (b.fy || 0) - fy
    }
    for (const n of nodes) {
      n.fx += (cx - n.x) * gravity
      n.fy += (cy - n.y) * gravity
      n.x = Math.min(width - 16, Math.max(16, n.x + Math.max(-8, Math.min(8, (n.fx || 0) * cooling))))
      n.y = Math.min(height - 16, Math.max(16, n.y + Math.max(-8, Math.min(8, (n.fy || 0) * cooling))))
      n.fx = 0
      n.fy = 0
    }
  }
  // 边查找表缓存到节点上，供模板聚焦判断复用
  return nodes
}

const lrLayout = computed(() => {
  if (!graphData.value || graphData.value.engine !== 'lightrag' || !graphData.value.nodes.length) return null
  // 实体度数：出现的边数（决定展示优先级与节点大小）
  const degree = new Map()
  for (const e of graphData.value.edges) {
    degree.set(e.source, (degree.get(e.source) || 0) + 1)
    degree.set(e.target, (degree.get(e.target) || 0) + 1)
  }
  const ranked = [...graphData.value.nodes]
    .map((n) => ({ ...n, degree: degree.get(n.id) || 0 }))
    .sort((a, b) => b.degree - a.degree || a.label.localeCompare(b.label))
  // 画布尺寸：宽度随容器、高度随窗口高度（扣除页面顶部、卡片说明与可见性图例的空间，保证右栏一屏内）
  const width = Math.round(Math.min(760, Math.max(240, lrWrapWidth.value)))
  const usable = Math.max(240, lrWinHeight.value - 530)
  const height = Math.round(Math.max(240, Math.min(width * 1.05, usable, 760)))
  // 展示实体数随画布高度收缩：窗口矮时自动少展示几个实体，保证右栏整体一屏内、图例完整可见
  const show = Math.max(8, Math.min(LR_SHOW, Math.floor(height / 15)))
  const picked = ranked.slice(0, show)
  const keep = new Set(picked.map((n) => n.id))
  const edges = graphData.value.edges.filter((e) => keep.has(e.source) && keep.has(e.target))
  const nodes = picked.map((n) => ({ ...n, r: Math.min(10, 3 + Math.sqrt(n.degree) * 1.5), fx: 0, fy: 0 }))
  lrForceSim(nodes, edges, width, height)
  const pos = {}
  nodes.forEach((n) => { pos[n.id] = { x: n.x, y: n.y, r: n.r } })
  return { nodes, edges, pos, width, height, truncated: ranked.length - picked.length }
})

// 画布尺寸或数据变化时重置缩放视图，避免残留错位（须在 lrLayout 声明之后注册）
watch(lrLayout, (layout) => {
  if (layout) lrView.value = { x: 0, y: 0, w: layout.width, h: layout.height }
})

/* ---- 生命周期 ---- */

function onGlobalKeydown(event) {
  if (event.key === 'Escape' && chunkModal.value) closeChunkModal()
}

onMounted(() => {
  loadScenes()
  document.addEventListener('keydown', onGlobalKeydown)
  // 监听图谱容器宽度变化（防抖 150ms：拖拽窗口时避免频繁重算力导向）
  lrResizeObserver = new ResizeObserver((entries) => {
    const width = entries[0]?.contentRect?.width
    if (!width) return
    clearTimeout(lrResizeTimer)
    lrResizeTimer = setTimeout(() => {
      if (Math.abs(width - lrWrapWidth.value) > 6) lrWrapWidth.value = width
    }, 150)
  })
  if (lrWrap.value) lrResizeObserver.observe(lrWrap.value)
  window.addEventListener('resize', onWindowResize)
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onGlobalKeydown)
  destroyEditor()
  clearTimeout(noticeTimer)
  lrResizeObserver?.disconnect()
  clearTimeout(lrResizeTimer)
  if (graphPollTimer) clearInterval(graphPollTimer)
  window.removeEventListener('resize', onWindowResize)
})
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

/* ===== 筛选行 ===== */
.filter-row { display: flex; flex: 0 0 auto; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 14px; }
/* 左右分组：场景选择靠左；检索引擎与搜索框成组靠右 */
.filter-left { display: flex; align-items: center; gap: 10px; min-width: 0; }
.filter-right { display: flex; align-items: center; gap: 10px; flex: 0 0 auto; }

.personal-hint { margin: 0 0 12px; font-size: 12.5px; color: var(--muted); line-height: 1.6; }

.search-box { position: relative; display: inline-flex; align-items: center; gap: 7px; width: 250px; flex: 0 0 auto; height: 34px; padding: 0 10px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--faint, var(--muted)); }
.search-box input { flex: 1; min-width: 0; border: 0; outline: none; background: transparent; color: var(--ink); font-size: 13.5px; font-family: inherit; }
.search-box input:disabled { cursor: not-allowed; }
.search-box input::placeholder { color: var(--faint, #a6a9bd); }
.search-scope-label { flex: 0 0 auto; font-size: 13px; color: var(--muted); }
.search-box .search-clear { display: grid; place-items: center; padding: 0; border: 0; background: transparent; color: var(--muted); cursor: pointer; }
.search-box .search-clear:hover { color: var(--ink); }

/* ===== 检索结果（Hybrid RAG） ===== */
.search-results { display: flex; flex-direction: column; }
/* LightRAG 图谱上下文：实体/关系/分块三段原始文本，等宽排版便于阅读 */
.lr-context { margin: 0; padding: 10px 2px; white-space: pre-wrap; word-break: break-word; font-family: ui-monospace, 'Cascadia Code', Consolas, monospace; font-size: 12px; line-height: 1.65; color: var(--ink); }
.search-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; padding: 10px 0 8px; border-bottom: 1px solid var(--line); font-size: 12px; color: var(--muted); }
.search-mode { font-size: 11px; border-radius: 99px; padding: 1px 8px; background: var(--bg); color: var(--muted); }
.search-mode.hybrid { background: var(--brand-soft); color: var(--brand-deep, var(--brand)); }
.search-item { padding: 10px 0; border-bottom: 1px dashed var(--line); cursor: pointer; }
.search-item:last-of-type { border-bottom: 0; }
.search-item:hover .si-name { color: var(--brand-deep, var(--brand)); }
.si-head { display: flex; align-items: center; gap: 8px; min-width: 0; }
.si-name { flex: 0 0 auto; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; font-weight: 600; color: var(--ink); }
.si-section { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11.5px; color: var(--muted); }
.si-text { margin: 5px 0 0; font-size: 12px; line-height: 1.65; color: var(--ink-soft); display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.si-text :deep(mark) { background: var(--brand-soft); color: var(--brand-deep, var(--brand)); border-radius: 3px; padding: 0 1px; }

/* ===== 双栏：左资料管理 + 右实体关系图谱 ===== */
.kw-columns { display: flex; gap: 16px; align-items: flex-start; flex: 1 0 auto; min-width: 0; }
.kw-main { flex: 1; min-width: 0; }
.kw-side { flex: 0 0 420px; display: flex; flex-direction: column; gap: 12px; }
.side-card { border: 1px solid var(--line); border-radius: 12px; background: var(--surface); padding: 14px 16px; }
.side-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 8px; }
.side-head h4 { margin: 0; font-size: 13.5px; color: var(--ink); }
.side-tag { font-size: 11px; color: var(--brand); background: var(--brand-soft); border-radius: 99px; padding: 2px 9px; font-weight: 600; white-space: nowrap; }
.side-desc { color: var(--muted); font-size: 12px; line-height: 1.65; margin: 8px 0 0; }
.rag-graph-wrap { max-height: 300px; overflow-y: auto; margin-top: 2px; }
/* LightRAG 力导向图：画布高度随窗口高度联动（与 JS 侧 usable 公式一致），过长滚动；详情与图例在容器外始终可见 */
.rag-graph-wrap.lr { max-height: calc(100vh - 530px); overflow: hidden; position: relative; }
.rag-graph.lr-canvas { cursor: grab; touch-action: none; }
.rag-graph.lr-canvas:active { cursor: grabbing; }
.lr-zoom { position: absolute; top: 6px; right: 8px; display: flex; gap: 4px; z-index: 1; }
.lr-zoom button { height: 22px; padding: 0 8px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: var(--ink-soft); font-size: 12px; line-height: 1; cursor: pointer; }
.lr-zoom button:hover { color: var(--ink); border-color: var(--brand, #6265e8); }
.rag-graph { width: 100%; height: auto; display: block; }
.rag-graph .edges path { fill: none; stroke-width: 1.2; opacity: .55; }
.rag-graph .edges path.contains { opacity: .45; }
.rag-graph .edges path.related { stroke: #b3b6cf; stroke-dasharray: 4 3; }
.rag-graph .node rect { fill: #fff; stroke: #cdd0e6; stroke-width: 1.2; }
.rag-graph .node.file rect { fill-opacity: .12; stroke-width: 1.4; }
.rag-graph .node.file text { font-weight: 600; }
.rag-graph .node.section.bridge rect { stroke: var(--brand); stroke-width: 1.8; }
.rag-graph .node.section.bridge text { fill: var(--brand-deep, var(--brand)); font-weight: 600; }
.rag-graph .node .ai-dot { fill: var(--ink); }
.rag-graph text { font-size: 9.5px; fill: var(--ink-soft); text-anchor: middle; }
.graph-note { margin: 6px 0 0; font-size: 11px; color: var(--faint, #a6a9bd); }

/* ===== LightRAG 实体关系网络 ===== */
.rag-graph .lr-edge { stroke: #b9bcd4; fill: none; stroke-width: 1; opacity: .4; transition: opacity .15s, stroke-width .15s; }
.rag-graph .lr-edge.hot { stroke: var(--brand, #6265e8); opacity: .95; stroke-width: 1.8; }
.rag-graph .lr-edge.dim { opacity: .08; }
.rag-graph .lr-node { cursor: pointer; }
.rag-graph .lr-node text { pointer-events: none; font-size: 8.5px; }
.rag-graph .lr-node.dim { opacity: .16; }
.rag-graph .lr-node.active text { fill: var(--ink); font-weight: 600; }
.lr-detail { margin-top: 8px; padding: 8px 10px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface-2, #fafafd); }
.lr-detail-name { display: flex; align-items: center; gap: 6px; margin: 0; font-size: 12.5px; font-weight: 600; color: var(--ink); }
.lr-detail-type { font-weight: 400; font-size: 11px; color: var(--muted); }
.lr-detail-desc { margin: 5px 0 0; font-size: 11.5px; line-height: 1.6; color: var(--ink-soft); }
.lr-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; flex: 0 0 auto; }
.lr-type-legend { display: flex; flex-wrap: wrap; gap: 4px 10px; margin-top: 8px; }
.lr-legend-item { display: inline-flex; align-items: center; gap: 4px; font-size: 10.5px; color: var(--muted); }
.legend-row { display: flex; align-items: flex-start; gap: 8px; margin: 7px 0; font-size: 12px; color: var(--muted); line-height: 1.5; }
.legend-row .tag { flex: 0 0 auto; margin-top: 1px; }
.legend-mark { flex: 0 0 auto; font-size: 11px; font-weight: 600; color: var(--brand-deep, var(--brand)); background: var(--brand-soft); border-radius: 5px; padding: 1px 6px; margin-top: 1px; }
.legend-note { margin: 7px 0; font-size: 12px; color: var(--muted); line-height: 1.5; }
@media (max-width: 1180px) { .kw-columns { flex-direction: column; } .kw-side { flex: 1 1 auto; flex-direction: row; } .kw-side .side-card { flex: 1; } }

/* ===== 拖放上传区（紧凑单行） ===== */
.dropzone { display: flex; flex: 0 0 auto; align-items: center; gap: 10px; padding: 13px 16px; border: 1.5px dashed #cdd0e6; border-radius: 12px; background: var(--surface); color: var(--muted); cursor: pointer; transition: border-color .15s, background .15s; margin-bottom: 14px; }
.dropzone:hover, .dropzone.drag { border-color: var(--brand); background: var(--brand-soft); }
.dz-text { color: var(--ink-soft); font-size: 13.5px; font-weight: 500; white-space: nowrap; }
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

/* 分节列表：可见性标签由 [user]/[ai] 标注决定，只读展示 */
.sections { margin-top: 10px; border: 1px solid var(--line); border-radius: 10px; background: var(--bg); padding: 4px 12px; }
.section-block { border-bottom: 1px dashed var(--line); }
.section-block:last-child { border-bottom: 0; }
.section-row { display: flex; align-items: center; gap: 10px; padding: 8px 0; font-size: 12.5px; }
.section-row .name { font-weight: 600; white-space: nowrap; }
.section-row .snippet { color: var(--muted); flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 分块弹窗（查看 = md 渲染 / 编辑 = milkdown 所见即所得） */
.chunk-item { border: 1px solid var(--line); border-radius: 8px; background: var(--surface); padding: 9px 11px; }
.chunk-actions { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 6px; }
.chunk-btns { display: inline-flex; align-items: center; gap: 6px; }
.chunk-meta { font-size: 11px; color: var(--faint, #a6a9bd); }
.chunk-loading, .chunk-empty { margin: 0; font-size: 12px; color: var(--muted); padding: 4px 0 8px; }
.btn-save { border: 0; border-radius: 7px; padding: 4px 12px; font-size: 12px; font-weight: 600; color: #fff; background: var(--brand); cursor: pointer; transition: background .15s; }
.btn-save:hover { background: var(--brand-deep, var(--brand)); }
.btn-save:disabled { opacity: .6; cursor: not-allowed; }

/* 只读态 Markdown 渲染 */
.md-view { font-size: 12.5px; line-height: 1.75; color: var(--ink-soft); overflow-wrap: break-word; }
.md-view :deep(h1), .md-view :deep(h2), .md-view :deep(h3), .md-view :deep(h4) { margin: 8px 0 4px; color: var(--ink); line-height: 1.4; }
.md-view :deep(h1:first-child), .md-view :deep(h2:first-child), .md-view :deep(h3:first-child) { margin-top: 0; }
.md-view :deep(h1) { font-size: 15px; }
.md-view :deep(h2) { font-size: 14px; }
.md-view :deep(h3), .md-view :deep(h4) { font-size: 13px; }
.md-view :deep(p) { margin: 5px 0; }
.md-view :deep(ul), .md-view :deep(ol) { margin: 5px 0; padding-left: 20px; }
.md-view :deep(li) { margin: 2px 0; }
.md-view :deep(code) { background: var(--bg); border: 1px solid var(--line); border-radius: 4px; padding: 1px 5px; font-size: 11.5px; font-family: ui-monospace, Consolas, monospace; }
.md-view :deep(pre) { background: var(--bg); border: 1px solid var(--line); border-radius: 7px; padding: 8px 10px; overflow-x: auto; }
.md-view :deep(pre code) { border: 0; background: transparent; padding: 0; }
.md-view :deep(blockquote) { margin: 6px 0; padding: 2px 10px; border-left: 3px solid var(--brand); color: var(--muted); background: var(--bg); border-radius: 0 6px 6px 0; }
.md-view :deep(table) { border-collapse: collapse; margin: 6px 0; }
.md-view :deep(th), .md-view :deep(td) { border: 1px solid var(--line); padding: 3px 8px; font-size: 12px; }
.md-view :deep(hr) { border: 0; border-top: 1px solid var(--line); margin: 8px 0; }
.md-view :deep(a) { color: var(--brand); }

/* ===== 分块内容弹窗 ===== */
.modal-backdrop { position: fixed; inset: 0; z-index: 90; display: grid; place-items: center; padding: 24px; background: rgba(28, 30, 45, .42); backdrop-filter: blur(2px); }
.modal-card { display: flex; flex-direction: column; width: min(720px, 100%); max-height: min(80vh, 680px); border: 1px solid var(--line); border-radius: 14px; background: var(--surface); box-shadow: 0 24px 64px rgba(20, 22, 38, .3); overflow: hidden; }
.modal-head { display: flex; align-items: center; gap: 10px; padding: 13px 16px; border-bottom: 1px solid var(--line); flex: 0 0 auto; }
.modal-head h3 { margin: 0; font-size: 13.5px; color: var(--ink); overflow-wrap: anywhere; }
.modal-titles { flex: 1; min-width: 0; }
.modal-sub { margin: 1px 0 0; font-size: 11.5px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-badge.sm { flex: 0 0 30px; width: 30px; height: 36px; font-size: 9px; border-radius: 7px; }
.modal-body { flex: 1; min-height: 0; overflow-y: auto; padding: 12px 16px 14px; display: flex; flex-direction: column; gap: 8px; }

/* milkdown 编辑区：贴合浅色主题 */
.md-editor { border: 1px solid var(--line); border-radius: 7px; overflow: auto; max-height: 46vh; }
.md-editor.source-editor { max-height: 56vh; } /* 整文件编辑，给更高的可视区域 */
.md-editor :deep(.milkdown) { background: #fff; padding: 10px 12px; font-size: 12.5px; line-height: 1.75; color: var(--ink); outline: none; }
.md-editor :deep(.milkdown h1) { font-size: 16px; }
.md-editor :deep(.milkdown h2) { font-size: 14.5px; }
.md-editor :deep(.milkdown h3) { font-size: 13.5px; }
.md-editor :deep(.milkdown p) { margin: 4px 0; }
.md-editor :deep(.milkdown ul), .md-editor :deep(.milkdown ol) { padding-left: 20px; margin: 4px 0; }
.md-editor :deep(.milkdown code) { background: var(--bg); border-radius: 4px; padding: 1px 5px; font-size: 11.5px; }
.md-editor :deep(.milkdown pre) { background: var(--bg); border-radius: 7px; padding: 8px 10px; overflow-x: auto; }
.md-editor :deep(.milkdown blockquote) { margin: 6px 0; padding: 2px 10px; border-left: 3px solid var(--brand); color: var(--muted); }
.md-editor :deep(.ProseMirror-selectednode), .md-editor :deep(.ProseMirror-selectednode *) { outline: 2px solid var(--brand); }

/* 开关（删除确认区按钮） */
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
.fade-enter-active, .fade-leave-active { transition: opacity .18s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
</style>

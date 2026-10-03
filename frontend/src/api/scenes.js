// 场景包 API 客户端：列表/详情/创建/编辑/复制/删除/导入导出/资料/封面/发布与社区互动。
import { baseUrl, http } from './http'

export const listScenes = () => http.get('/scenes')

export const listTemplates = () => http.get('/scenes/templates')

export const getScene = (id) => http.get(`/scenes/${id}`)

export const createScene = (pkg) => http.post('/scenes', pkg)

export const updateScene = (id, pkg) => http.put(`/scenes/${id}`, pkg)

export const validateScene = (pkg) => http.post('/scenes/validate', pkg)

export const createFromTemplate = (templateId) =>
  http.post('/scenes/from-template', { template_id: templateId })

export const duplicateScene = (id) => http.post(`/scenes/${id}/duplicate`)

export const deleteScene = (id) => http.delete(`/scenes/${id}`)

// 导入：resolve 用于 ID 冲突时的显式选择（overwrite / rename）
export const importScene = (file, resolve) => {
  const form = new FormData()
  form.append('file', file)
  const params = resolve ? { resolve } : {}
  return http.post('/scenes/import', form, { params, timeout: 60000 })
}

// 导出：取二进制流交给浏览器保存
export const exportScene = async (id, filename) => {
  const { data } = await http.get(`/scenes/${id}/export`, { responseType: 'blob', timeout: 60000 })
  const url = URL.createObjectURL(data)
  const link = document.createElement('a')
  link.href = url
  link.download = filename || `echotalk_scene_${id}.zip`
  link.click()
  URL.revokeObjectURL(url)
}

// 知识资料
export const uploadKnowledge = (id, file, visibility = 'user', onProgress) => {
  const form = new FormData()
  form.append('file', file)
  return http.post(`/scenes/${id}/knowledge`, form, {
    params: { visibility },
    timeout: 60000,
    onUploadProgress: onProgress, // 上传进度回调（可选）
  })
}

export const deleteKnowledge = (id, documentId) => http.delete(`/scenes/${id}/knowledge/${documentId}`)

// 文件级资料概览（含每文件分节分组）：知识工作区列表数据源
export const listKnowledgeDocuments = (id) => http.get(`/scenes/${id}/knowledge/documents`)
// 资料的分块明细（含正文全文，只读）：知识工作区查看数据源
export const listDocumentChunks = (id, documentId) => http.get(`/scenes/${id}/knowledge/documents/${documentId}/chunks`)
// 资料源文件全文（文本类可编辑，pdf 返回 editable=false）
export const getDocumentSource = (id, documentId) => http.get(`/scenes/${id}/knowledge/documents/${documentId}/source`)
// 保存源文件：后端重新解析并重建分块
export const updateDocumentSource = (id, documentId, text) =>
  http.put(`/scenes/${id}/knowledge/documents/${documentId}/source`, { text }, { timeout: 30000 })
// 实体关系图谱（阶段三，规则抽取）：文件-分节从属 + 跨文件分节相关
export const sceneGraph = (id) => http.get(`/scenes/${id}/knowledge/graph`)
// 混合检索（Hybrid RAG）：ngram 全文关键词 + 向量余弦，RRF 融合
export const searchSceneKnowledge = (id, q, topK = 6) =>
  http.get(`/scenes/${id}/knowledge/search`, { params: { q, top_k: topK }, timeout: 20000 })
export const searchPersonalKnowledge = (q, topK = 6) =>
  http.get('/knowledge/personal/search', { params: { q, top_k: topK }, timeout: 20000 })
// 为分块补建向量（上传时嵌入失败 / 换嵌入模型后全量重建）
export const reindexSceneKnowledge = (id) => http.post(`/scenes/${id}/knowledge/reindex`, null, { timeout: 120000 })
// LightRAG 图谱检索：返回实体/关系/分块检索上下文（查询含一次 LLM 关键词抽取，较慢）
export const lightragSceneSearch = (id, q, mode = 'mix', topK = 6) =>
  http.get(`/scenes/${id}/knowledge/lightrag`, { params: { q, mode, top_k: topK }, timeout: 120000 })
export const lightragPersonalSearch = (q, mode = 'mix', topK = 6) =>
  http.get('/knowledge/personal/lightrag', { params: { q, mode, top_k: topK }, timeout: 120000 })

// ---- 个人工作区资料（阶段二）：owner 隔离，全部要求登录 ----
export const listPersonalDocuments = () => http.get('/knowledge/personal')
// 个人资料实体关系图谱（与场景图谱同一套抽取逻辑）
export const personalGraph = () => http.get('/knowledge/personal/graph')
export const uploadPersonalKnowledge = (file, onProgress) => {
  const form = new FormData()
  form.append('file', file)
  return http.post('/knowledge/personal', form, { timeout: 60000, onUploadProgress: onProgress })
}
export const listPersonalChunks = (documentId) => http.get(`/knowledge/personal/documents/${documentId}/chunks`)
export const getPersonalSource = (documentId) => http.get(`/knowledge/personal/documents/${documentId}/source`)
export const updatePersonalSource = (documentId, text) =>
  http.put(`/knowledge/personal/documents/${documentId}/source`, { text }, { timeout: 30000 })
export const deletePersonalDocument = (documentId) => http.delete(`/knowledge/personal/documents/${documentId}`)

// 分节级概览（旧版后端兼容 / 对话侧数据源）
export const getSectionOverview = (id) => http.get(`/scenes/${id}/knowledge/sections`)

export const patchSectionVisibility = (id, section, visibility) =>
  http.patch(`/scenes/${id}/knowledge/sections/${encodeURIComponent(section)}`, { visibility })

// 发布与社区互动
export const publishScene = (id) => http.post(`/scenes/${id}/publish`)
export const unpublishScene = (id) => http.post(`/scenes/${id}/unpublish`)
export const likeScene = (id) => http.post(`/scenes/${id}/like`)
export const favoriteScene = (id) => http.post(`/scenes/${id}/favorite`)

// 封面图：直链供 <img> 引用；bust 参数用于上传后强制刷新缓存
export const coverUrl = (id, bust) => `${baseUrl}/api/scenes/${id}/cover${bust ? `?t=${bust}` : ''}`

export const uploadCover = (id, file) => {
  const form = new FormData()
  form.append('file', file)
  return http.post(`/scenes/${id}/cover`, form, { timeout: 30000 })
}

export const removeCover = (id) => http.delete(`/scenes/${id}/cover`)

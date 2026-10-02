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

import { http } from './http'

// 认证与当前用户
export const adminLogin = (username, password) =>
  http.post('/admin/login', { username, password })

export const fetchCurrentUser = () => http.get('/auth/me')

export const logoutAdmin = () => http.post('/auth/logout')

// 仪表盘
export const fetchDashboard = () => http.get('/admin/dashboard')

// 用户管理
export const fetchUsers = (params) => http.get('/admin/users', { params })
export const createUser = (payload) => http.post('/admin/users', payload)
export const updateUser = (userId, payload) => http.patch(`/admin/users/${userId}`, payload)
export const deleteUser = (userId) => http.delete(`/admin/users/${userId}`)
export const batchDeleteUsers = (ids) => http.post('/admin/users/batch-delete', { ids })

// 数字人管理
export const fetchAvatarCatalog = () => http.get('/admin/avatars/catalog')
export const fetchAvatarPreferences = (params) => http.get('/admin/avatars/preferences', { params })
export const upsertAvatarPreference = (payload) => http.put('/admin/avatars/preferences', payload)
export const deleteAvatarPreference = (userId, sceneId = '') =>
  http.delete('/admin/avatars/preferences', { params: { user_id: userId, scene_id: sceneId } })
export const batchDeleteAvatarPreferences = (items) =>
  http.post('/admin/avatars/preferences/batch-delete', { items })

// 创建的数字人角色管理
export const fetchAvatarPresets = (params) => http.get('/admin/avatars/presets', { params })
export const updateAvatarPreset = (avatarId, payload) => http.patch(`/admin/avatars/presets/${avatarId}`, payload)
export const deleteAvatarPreset = (avatarId) => http.delete(`/admin/avatars/presets/${avatarId}`)
export const batchUpdateAvatarPresetsPublic = (ids, is_public) =>
  http.post('/admin/avatars/presets/batch-public', { ids, is_public })
export const batchDeleteAvatarPresets = (ids) => http.post('/admin/avatars/presets/batch-delete', { ids })

// 场景管理
export const fetchScenes = (params) => http.get('/admin/scenes', { params })
export const fetchSceneDetail = (sceneId) => http.get(`/admin/scenes/${sceneId}`)
export const updateScene = (sceneId, payload) => http.patch(`/admin/scenes/${sceneId}`, payload)
export const deleteScene = (sceneId) => http.delete(`/admin/scenes/${sceneId}`)
export const batchUpdateScenesStatus = (ids, status) => http.post('/admin/scenes/batch-status', { ids, status })
export const batchDeleteScenes = (ids) => http.post('/admin/scenes/batch-delete', { ids })

// 对话记录管理
export const fetchSessions = (params) => http.get('/admin/sessions', { params })
export const fetchSessionDetail = (sessionId) => http.get(`/admin/sessions/${sessionId}`)
export const deleteSession = (sessionId) => http.delete(`/admin/sessions/${sessionId}`)
export const batchDeleteSessions = (ids) => http.post('/admin/sessions/batch-delete', { ids })

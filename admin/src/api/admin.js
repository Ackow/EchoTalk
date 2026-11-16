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
export const fetchRegistrationSetting = () => http.get('/admin/settings/registration')
export const updateRegistrationSetting = (restricted) =>
  http.put('/admin/settings/registration', { registration_restricted: Boolean(restricted) })

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

// API Token 统计
export const fetchTokenStats = (params) => http.get('/admin/token-stats', { params })

// 听力资源管理
export const fetchListeningUnits = () => http.get('/admin/listening/units')
export const importListeningUnits = (payload) => http.post('/admin/listening/import', payload)
export const deleteListeningUnit = (unitId) => http.delete(`/admin/listening/units/${unitId}`)

// 用户权益与积分调账
export const grantUserSaas = (userId, payload) => http.post(`/admin/users/${userId}/grant`, payload)

// 多角色场景管理
export const fetchAdminDebates = (params) => http.get('/admin/debates', { params })
export const updateAdminDebate = (topicId, payload) => http.patch(`/admin/debates/${topicId}`, payload)
export const deleteAdminDebate = (topicId) => http.delete(`/admin/debates/${topicId}`)

// 多角色会话记录
export const fetchAdminDebateSessions = (params) => http.get('/admin/debate-sessions', { params })
export const fetchAdminDebateSessionDetail = (sessionId) => http.get(`/admin/debate-sessions/${sessionId}`)
export const deleteAdminDebateSession = (sessionId) => http.delete(`/admin/debate-sessions/${sessionId}`)

// 知识库文档管理
export const fetchAdminKnowledge = (params) => http.get('/admin/knowledge', { params })
export const deleteAdminKnowledge = (scope, docId) => http.delete(`/admin/knowledge/${scope}/${docId}`)
export const fetchLightragConfig = () => http.get('/admin/knowledge/lightrag-config')
export const updateLightragConfig = (payload) => http.put('/admin/knowledge/lightrag-config', payload)

// 复习计划与听力记录
export const fetchAdminReviews = (params) => http.get('/admin/reviews', { params })
export const deleteAdminReview = (itemId) => http.delete(`/admin/reviews/${itemId}`)
export const fetchAdminListeningAttempts = (params) => http.get('/admin/listening/attempts', { params })

// SaaS 套餐、任务、活动、订单与兑换码
export const fetchAdminSaasPlans = () => http.get('/admin/saas/plans')
export const updateAdminSaasPlan = (tier, payload) => http.put(`/admin/saas/plans/${tier}`, payload)
export const fetchAdminTasks = () => http.get('/admin/saas/tasks')
export const updateAdminTask = (taskCode, payload) => http.put(`/admin/saas/tasks/${taskCode}`, payload)
export const fetchAdminCampaigns = () => http.get('/admin/saas/campaigns')
export const createAdminCampaign = (payload) => http.post('/admin/saas/campaigns', payload)
export const updateAdminCampaign = (id, payload) => http.patch(`/admin/saas/campaigns/${id}`, payload)
export const deleteAdminCampaign = (id) => http.delete(`/admin/saas/campaigns/${id}`)
export const fetchAdminOrders = (params) => http.get('/admin/saas/orders', { params })
export const fetchAdminLedger = (params) => http.get('/admin/saas/ledger', { params })
export const fetchAdminRedeemCodes = (params) => http.get('/admin/saas/redeem-codes', { params })
export const generateAdminRedeemCodes = (payload) => http.post('/admin/saas/redeem-codes', payload)
export const updateBillingConfig = (payload) => http.put('/admin/saas/billing-config', payload)

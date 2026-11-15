import { baseUrl, http } from './http'

export const debateCoverUrl = (topicId, version) =>
  `${baseUrl}/debate/topics/${encodeURIComponent(topicId)}/cover${version ? `?v=${version}` : ''}`

export function uploadDebateCover(topicId, file) {
  const form = new FormData()
  form.append('file', file)
  return http.upload(`/debate/topics/${encodeURIComponent(topicId)}/cover`, form)
}

export function removeDebateCover(topicId) {
  return http.delete(`/debate/topics/${encodeURIComponent(topicId)}/cover`)
}

export function listDebateTopics() {
  return http.get('/debate/topics')
}

export function generateDebateTopicDraft(idea, sceneType = 'debate') {
  return http.post('/debate/topics/generate', { idea, sceneType })
}

export function createDebateTopic(payload) {
  return http.post('/debate/topics', payload)
}

export function updateDebateTopic(topicId, payload) {
  return http.put(`/debate/topics/${encodeURIComponent(topicId)}`, payload)
}

export function deleteDebateTopic(topicId) {
  return http.delete(`/debate/topics/${encodeURIComponent(topicId)}`)
}

export function likeDebateTopic(topicId) {
  return http.post(`/debate/topics/${encodeURIComponent(topicId)}/like`)
}

export function favoriteDebateTopic(topicId) {
  return http.post(`/debate/topics/${encodeURIComponent(topicId)}/favorite`)
}

export function publishDebateTopic(topicId) {
  return http.post(`/debate/topics/${encodeURIComponent(topicId)}/publish`)
}

export function unpublishDebateTopic(topicId) {
  return http.post(`/debate/topics/${encodeURIComponent(topicId)}/unpublish`)
}

export function duplicateDebateTopic(topicId) {
  return http.post(`/debate/topics/${encodeURIComponent(topicId)}/duplicate`)
}

export async function exportDebateTopic(topicId, filename) {
  const { data } = await http.get(`/debate/topics/${encodeURIComponent(topicId)}/export`, {
    responseType: 'blob',
    timeout: 60000,
  })
  const url = URL.createObjectURL(data)
  const link = document.createElement('a')
  link.href = url
  link.download = filename || `echotalk_debate_${topicId}.zip`
  link.click()
  URL.revokeObjectURL(url)
}

export function importDebateTopic(file) {
  const form = new FormData()
  form.append('file', file)
  return http.post('/debate/topics/import', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function createDebateSession(payload) {
  return http.post('/debate/sessions', payload)
}

export function getDebateSession(sessionId) {
  return http.get(`/debate/sessions/${encodeURIComponent(sessionId)}`)
}

export function submitDebateTurn(sessionId, payload) {
  return http.post(`/debate/sessions/${encodeURIComponent(sessionId)}/turns`, payload)
}

export function suggestDebateReply(sessionId) {
  return http.post(`/debate/sessions/${encodeURIComponent(sessionId)}/suggest-reply`)
}

export function finishDebateSession(sessionId) {
  return http.post(`/debate/sessions/${encodeURIComponent(sessionId)}/finish`)
}

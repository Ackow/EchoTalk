// 练习会话 API 客户端：创建会话、恢复会话、提交对话轮次。
import { baseUrl, http } from './http'
import { clearSession, session } from '../auth/session'

// 历史记录：分页返回本人有实际轮次的会话，含最后一轮预览与全局统计
export const listSessions = (params = {}) => http.get('/sessions', { params })
export const getGrowthAnalytics = (days = 30) => http.get('/sessions/analytics', { params: { days } })

// 创建练习会话：返回 { id, scene_id, greeting, state, version }
export const createSession = (sceneId) => http.post('/sessions', { scene_id: sceneId })

// 恢复会话：公开字段 + 按轮次排序的公开对话记录（turns）
export const getSession = (id) => http.get(`/sessions/${id}`)
export const getSessionReport = (id) => http.get(`/sessions/${encodeURIComponent(id)}/report`)
export const getLatestSession = (sceneId) => http.get('/sessions/latest', { params: { scene_id: sceneId } })

export const getTurnAudio = async (sessionId, turnId, voiceStyle, speechRate = 1) => {
  const { data } = await http.get(`/sessions/${sessionId}/turns/${turnId}/audio`, {
    params: { voice_style: voiceStyle, speech_rate: speechRate }, responseType: 'blob', timeout: 30000,
  })
  return data
}

export const getUserTurnAudio = async (sessionId, turnId) => {
  const { data } = await http.get(`/sessions/${encodeURIComponent(sessionId)}/turns/${encodeURIComponent(turnId)}/user-audio`, {
    responseType: 'blob', timeout: 30000,
  })
  return data
}

// 问候音频由后端持久化并复用，用户身份仍通过请求头校验。
export const getGreetingAudio = async (id, voiceStyle, speechRate = 1) => {
  const { data } = await http.get(`/sessions/${id}/greeting-audio`, {
    params: { voice_style: voiceStyle, speech_rate: speechRate }, responseType: 'blob', timeout: 30000,
  })
  return data
}

// 提交一轮对话：request_id 供后端幂等去重（安全重试复用同一 ID）；
// 后端需调模型与场景检索，超时单独放宽到 60s
export const submitTurn = (id, requestId, text) =>
  http.post(`/sessions/${id}/turns`, { request_id: requestId, text }, { timeout: 60000 })

// AI 帮助回复：结合当前场景阶段与最近对话生成 2~3 条地道英语参考回复
export const suggestReply = (id) =>
  http.post(`/sessions/${encodeURIComponent(id)}/suggest-reply`, {}, { timeout: 30000 })

// 场景结束交互动作（如咖啡厅付款确认）
export const applySessionAction = (id, action, payload = {}) =>
  http.post(`/sessions/${encodeURIComponent(id)}/action`, { action, payload })

// 流式提交一轮对话（SSE）：边生成文本边按句下发 MP3 音频分段
export async function submitTurnStream(
  id,
  requestId,
  text,
  { voiceStyle, includeAudio = true, audioToken, onDelta, onDone, onCorrection, onPronunciation, onAudio, onAudioError, onAudioEnd, signal } = {}
) {
  const headers = { 'Content-Type': 'application/json' }
  if (session.token) headers.Authorization = `Bearer ${session.token}`

  const res = await fetch(`${baseUrl}/api/sessions/${encodeURIComponent(id)}/turns/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      request_id: requestId,
      text,
      voice_style: voiceStyle || undefined,
      include_audio: Boolean(includeAudio),
      audio_token: audioToken || undefined,
    }),
    signal,
  })

  if (res.status === 401) {
    clearSession()
    throw new Error('登录已失效，请重新登录')
  }
  if (!res.ok) {
    let msg = `请求失败（${res.status}）`
    try {
      const body = await res.json()
      msg = body?.error?.message || body?.detail || msg
    } catch { /* ignore */ }
    throw new Error(msg)
  }
  if (!res.body) throw new Error('浏览器不支持流式响应')

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  const dispatchBlock = (block) => {
    if (!block.trim()) return
    let eventName = 'message'
    const dataLines = []
    for (const line of block.split(/\r?\n/)) {
      if (line.startsWith('event:')) eventName = line.slice(6).trim()
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart())
    }
    if (!dataLines.length) return
    let parsed = {}
    try {
      parsed = JSON.parse(dataLines.join('\n'))
    } catch {
      return
    }
    if (eventName === 'delta') onDelta?.(parsed.text || '')
    else if (eventName === 'done') onDone?.(parsed)
    else if (eventName === 'correction') onCorrection?.(parsed)
    else if (eventName === 'pronunciation') onPronunciation?.(parsed)
    else if (eventName === 'audio') onAudio?.(parsed)
    else if (eventName === 'audio_error') onAudioError?.(parsed)
    else if (eventName === 'audio_end') onAudioEnd?.(parsed)
    else if (eventName === 'error') throw new Error(parsed.message || '流式对话失败，请重试')
  }

  while (true) {
    const { done, value } = await reader.read()
    if (value) {
      buffer += decoder.decode(value, { stream: true })
      const blocks = buffer.split(/\r?\n\r?\n/)
      buffer = blocks.pop() ?? ''
      for (const block of blocks) dispatchBlock(block)
    }
    if (done) {
      buffer += decoder.decode()
      if (buffer.trim()) dispatchBlock(buffer)
      break
    }
  }
}

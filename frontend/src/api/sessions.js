// 练习会话 API 客户端：创建会话、恢复会话、提交对话轮次。
import { http } from './http'

// 创建练习会话：返回 { id, scene_id, greeting, state, version }
export const createSession = (sceneId) => http.post('/sessions', { scene_id: sceneId })

// 恢复会话：公开字段 + 按轮次排序的公开对话记录（turns）
export const getSession = (id) => http.get(`/sessions/${id}`)

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

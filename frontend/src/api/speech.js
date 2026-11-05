// 上传标准 WAV，由后端统一鉴权并调用 ASR；识别结果待用户确认后才发送给 Agent。
import { http } from './http'

export const getSpeechStatus = () => http.get('/speech/status')

export function transcribeRecording(blob, signal) {
  const data = new FormData()
  data.append('file', blob, 'recording.wav')
  return http.post('/speech/transcriptions', data, { timeout: 45000, signal })
}

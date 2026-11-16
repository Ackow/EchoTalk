// 听力工作室、四六级专项与经验值/任务 API。
import { baseUrl, http } from './http'

export const getListeningUnits = () => http.get('/listening/units')
export const submitListeningAttempt = (payload) => http.post('/listening/attempts', payload)
export const completeListeningUnit = (unitId) => http.post(`/listening/units/${unitId}/complete`)
export const addListeningReview = (payload) => http.post('/listening/review-add', payload)
export const getListeningProfile = () => http.get('/listening/profile')
export const claimDailyCheckin = () => http.post('/listening/checkin')

export function getListeningAudioUrl(text, rate = 1.0, style = 'emma') {
  const params = new URLSearchParams({
    text: String(text || ''),
    rate: String(rate),
    style: String(style)
  })
  return `${baseUrl}/api/listening/audio?${params.toString()}`
}

export async function fetchListeningAudioBlob(text, rate = 1.0, style = 'emma') {
  const res = await http.get('/listening/audio', {
    params: {
      text: String(text || ''),
      rate,
      style
    },
    responseType: 'blob',
    timeout: 30000
  })
  return res.data
}

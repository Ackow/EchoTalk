// 复习计划 API：对接后端 /api/review，自动从历史对话提取薄弱点并用 SM-2 算法调度。
import { http } from './http'

export const listReviewItems = (sync = true) => http.get('/review', { params: { sync } })
export const syncReviewItems = () => http.post('/review/sync')
export const createReviewItem = (payload) => http.post('/review', payload)
export const updateReviewItem = (id, payload) => http.patch(`/review/${id}`, payload)
export const deleteReviewItem = (id) => http.delete(`/review/${id}`)
export const submitReviewResult = (id, rating) => http.post(`/review/${id}/submit`, { rating })

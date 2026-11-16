import { reactive } from 'vue'
import { http } from './http'

export const saasState = reactive({
  loaded: false,
  plan_tier: 'free',
  plan_name: 'Free 免费体验版',
  plan_expires_at: null,
  credits_balance: 0,
  auto_use_credits: true,
  checkin_streak: 0,
  checked_in_today: false,
  allow_zip_import: false,
  allow_zip_export: false,
  quotas: [],
  active_campaigns: [],
})

export function getSaasMe() {
  return http.get('/saas/me')
}

export async function refreshSaasState() {
  try {
    const { data } = await getSaasMe()
    Object.assign(saasState, data, { loaded: true })
    return data
  } catch {
    return null
  }
}

export function updateSaasSettings(autoUseCredits) {
  return http.patch('/saas/me/settings', { auto_use_credits: autoUseCredits })
}

export function getSaasPlans() {
  return http.get('/saas/plans')
}

export function postDailyCheckin() {
  return http.post('/saas/checkin')
}

export function getSaasTasks() {
  return http.get('/saas/tasks')
}

export function claimSaasTask(taskCode) {
  return http.post(`/saas/tasks/${encodeURIComponent(taskCode)}/claim`)
}

export function mockCheckout(payload) {
  return http.post('/saas/checkout/mock', payload)
}

export function redeemSaasCode(code) {
  return http.post('/saas/redeem', { code })
}

export function getSaasLedger(page = 1, pageSize = 20) {
  return http.get('/saas/ledger', { params: { page, page_size: pageSize } })
}

import { reactive } from 'vue'

const TOKEN_KEY = 'echotalk_admin_token'

export const adminSession = reactive({
  token: localStorage.getItem(TOKEN_KEY) || '',
  user: null,
})

export function setAdminSession(token, user) {
  adminSession.token = token
  adminSession.user = user
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearAdminSession() {
  adminSession.token = ''
  adminSession.user = null
  localStorage.removeItem(TOKEN_KEY)
}

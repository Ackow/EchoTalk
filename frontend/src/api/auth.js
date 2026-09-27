// 账户相关 API：注册、登录、退出、当前用户。
// 令牌由 http.js 拦截器自动附加，调用方无需手动传入。
import { http } from './http'

// 注册新账户，返回 { access_token, user }
export function register(credentials) {
  return http.post('/auth/register', credentials)
}

// 登录已有账户，返回 { access_token, user }
export function login(credentials) {
  return http.post('/auth/login', credentials)
}

// 退出登录：撤销当前令牌
export function logout() {
  return http.post('/auth/logout')
}

// 查询当前登录用户信息（用于刷新后恢复身份）
export function currentUser() {
  return http.get('/auth/me')
}

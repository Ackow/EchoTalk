// 账户相关 API：注册、登录、退出、当前用户、改密与头像。
// 令牌由 http.js 拦截器自动附加，调用方无需手动传入。
import { baseUrl, http } from './http'

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

// 修改密码：校验当前密码后重设，其他设备的登录会被退出
export function changePassword(payload) {
  return http.put('/auth/password', payload)
}

// 上传/替换头像：jpg / png / webp，后端上限 2 MB
export function uploadAvatar(file) {
  const form = new FormData()
  form.append('file', file)
  return http.post('/auth/avatar', form, { timeout: 30000 })
}

// 移除头像：前端回落到用户名首字母
export function removeAvatar() {
  return http.delete('/auth/avatar')
}

// 头像直链：文件名自带随机串，换图即换地址，可以直接让浏览器长缓存
export const avatarUrl = (user) => {
  if (!user?.avatar_path) return ''
  const token = user.avatar_path.split('/').pop() // 取文件名作为版本号
  return `${baseUrl}/api/auth/avatar/${user.id}?v=${encodeURIComponent(token)}`
}

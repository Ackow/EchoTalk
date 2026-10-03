// 数字人与声音偏好 API 客户端。
// 后端阶段七接口（/avatars、/voices、/preferences/avatar）就绪前，页面用 FALLBACK 缺省数据
// 保持可预览，并如实标注"示例"，不伪装成已连通的服务。
import { http } from './http'

// 缺省形象清单：与后端 storage/avatars/manifest.json 的结构保持一致
export const FALLBACK_AVATARS = [
  { id: 'sarah_2d', display_name: 'Sarah · 技术面试官', kind: '2d', theme: 'violet', voice_hint: 'female_young' },
  { id: 'leo_2d', display_name: 'Leo · 咖啡师', kind: '2d', theme: 'amber', voice_hint: 'male_young' },
  { id: 'david_2d', display_name: 'David · 产品经理', kind: '2d', theme: 'teal', voice_hint: 'male_mature' },
  { id: 'default', display_name: '默认形象', kind: '2d', theme: 'slate', voice_hint: 'neutral' },
]

// 缺省声音表：voice_style → 渠道 voice；available=false 表示渠道未探测成功
export const FALLBACK_VOICES = [
  { style: 'us_female', label: 'Emma · 美式英语', tts_voice: 'en-US-EmmaNeural', available: true },
  { style: 'uk_female', label: 'Sonia · 英式英语', tts_voice: 'en-GB-SoniaNeural', available: true },
  { style: 'us_male', label: 'Andrew · 美式英语', tts_voice: 'en-US-AndrewNeural', available: true },
]

// 可选交流角色（来自场景包 roles[].avatar 的推荐值演示）
export const FALLBACK_ROLES = [
  { id: 'barista', display_name: 'Leo', title: 'Barista', avatar: 'leo_2d', voice: 'en-US-YoungMale' },
  { id: 'sarah', display_name: 'Sarah', title: '技术面试官', avatar: 'sarah_2d', voice: 'en-US-YoungFemale' },
  { id: 'david', display_name: 'David', title: '产品经理', avatar: 'david_2d', voice: 'en-US-MatureMale' },
]

// 统一解包：后端返回 { data: ... } 或裸对象都兼容
const unwrap = (res) => (res?.data !== undefined ? res.data : res)

export const listAvatars = async () => {
  const { data } = await http.get('/avatars')
  return Array.isArray(data) && data.length ? data : FALLBACK_AVATARS
}

export const listVoices = async () => {
  const { data } = await http.get('/voices')
  return Array.isArray(data) && data.length ? data : FALLBACK_VOICES
}

// 按优先级解析实际生效的形象/声音；解析链见 Avatar-Design.md §5
export const resolveAvatar = (sceneId, roleId) =>
  unwrap(http.get('/avatars/resolve', { params: { scene_id: sceneId, role_id: roleId } }))

// 读取偏好：未设置时返回字段为 null 的对象，而非 404
export const getAvatarPreference = async () => {
  try {
    return unwrap(await http.get('/preferences/avatar'))
  } catch {
    return null // 游客或接口未就绪：按"跟随场景推荐"处理
  }
}

// 整体覆盖保存；缺省字段视为不改动
export const saveAvatarPreference = (payload) => unwrap(http.put('/preferences/avatar', payload))

// 恢复默认：回到"跟随场景推荐"
export const resetAvatarPreference = () => unwrap(http.delete('/preferences/avatar'))

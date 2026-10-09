// 数字人与声音偏好 API 客户端。
// 形象与音色清单初版写死前端（各形象/音色之间无绑定，可与任意场景自由组合）；
// 用户选择的组合在登录后存数据库（/preferences/avatar），游客仅存本机。
import { http } from './http'

// 固定形象清单：id 决定独立造型，theme 仅用于缩略图底色；声音与场景可自由搭配
export const FALLBACK_AVATARS = [
  { id: 'mira_2d', display_name: 'Mira · 米拉', kind: '2d', theme: 'violet', tagline: '温柔、有耐心，对每个想法充满好奇。', description: '短发 · 轻耳麦 · 紫色针织衫', greeting: 'Hey! 今天想聊点什么？' },
  { id: 'vera_2d', display_name: 'Vera · 薇拉', kind: '2d', theme: 'teal', tagline: '干练直率，喜欢把问题聊透。', description: '高马尾 · 金色耳环 · 白衬衫与绿色马甲', greeting: 'Hi! 我们来一起梳理你的想法。' },
  { id: 'nora_2d', display_name: 'Nora · 诺拉', kind: '2d', theme: 'blue', tagline: '沉稳专注，善于安静地倾听。', description: '长直发 · 圆框眼镜 · 奶白高领与藏蓝外套', greeting: 'Hello. 慢慢说，我会认真听。' },
  { id: 'iris_2d', display_name: 'Iris · 艾瑞丝', kind: '2d', theme: 'amber', tagline: '活泼开朗，总能带动谈话气氛。', description: '双丸子卷发 · 小雀斑 · 黄色连帽衫与斜挎带', greeting: 'Hey there! 分享一件今天的趣事吧。' },
]

// 缺省声音表：voice_style（声音名小写）→ 渠道 voice，覆盖美/英/澳口音；
// available 三态：true/false=探测结果，null=尚未探测
export const FALLBACK_VOICES = [
  { style: 'emma', label: 'Emma · 美式英语', tts_voice: 'en-US-EmmaNeural', available: null },
  { style: 'aria', label: 'Aria · 美式英语', tts_voice: 'en-US-AriaNeural', available: null },
  { style: 'jenny', label: 'Jenny · 美式英语', tts_voice: 'en-US-JennyNeural', available: null },
  { style: 'andrew', label: 'Andrew · 美式英语', tts_voice: 'en-US-AndrewNeural', available: null },
  { style: 'brian', label: 'Brian · 美式英语', tts_voice: 'en-US-BrianNeural', available: null },
  { style: 'guy', label: 'Guy · 美式英语', tts_voice: 'en-US-GuyNeural', available: null },
  { style: 'sonia', label: 'Sonia · 英式英语', tts_voice: 'en-GB-SoniaNeural', available: null },
  { style: 'ryan', label: 'Ryan · 英式英语', tts_voice: 'en-GB-RyanNeural', available: null },
  { style: 'natasha', label: 'Natasha · 澳式英语', tts_voice: 'en-AU-NatashaNeural', available: null },
  { style: 'william', label: 'William · 澳式英语', tts_voice: 'en-AU-WilliamNeural', available: null },
]

// 历史 voice_style 枚举归一：早期版本用口音_性别作 style，读取旧偏好时映射到声音名
export const VOICE_STYLE_ALIASES = { us_female: 'emma', uk_female: 'sonia', us_male: 'andrew' }

// 可选交流角色（来自场景包 roles[].avatar 的推荐值演示）
export const FALLBACK_ROLES = [
  { id: 'barista', display_name: 'Leo', title: 'Barista', avatar: 'mira_2d', voice: 'en-US-YoungMale' },
  { id: 'sarah', display_name: 'Sarah', title: '技术面试官', avatar: 'mira_2d', voice: 'en-US-YoungFemale' },
  { id: 'david', display_name: 'David', title: '产品经理', avatar: 'mira_2d', voice: 'en-US-MatureMale' },
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
export const resolveAvatar = async (sceneId, roleId) =>
  unwrap(await http.get('/avatars/resolve', { params: { scene_id: sceneId, role_id: roleId } }))

// 读取偏好：按场景档读取（sceneId 为空表示「跟随推荐」档）；未设置时返回字段全 null 的对象，而非 404
export const getAvatarPreference = async (sceneId) => {
  try {
    return unwrap(await http.get('/preferences/avatar', { params: { scene_id: sceneId || undefined } }))
  } catch {
    return null // 后端不可用：按"跟随场景推荐"处理
  }
}

// 整体覆盖保存当前场景档；payload.scene_id 即档位键，缺省字段视为不改动
export const saveAvatarPreference = async (payload) => unwrap(await http.put('/preferences/avatar', payload))

// 恢复默认：删除当前场景档的偏好
export const resetAvatarPreference = async (sceneId) => unwrap(await http.delete('/preferences/avatar', { params: { scene_id: sceneId || undefined } }))

// TTS 语音合成：文本 → MP3 Blob（试听与后续对话播报复用）；合成耗时较长，单独放宽超时
export const synthesizeSpeech = async (text, voiceStyle, speechRate = 1) =>
  unwrap(await http.post('/tts/synthesize', { text, voice_style: voiceStyle, speech_rate: speechRate }, { responseType: 'blob', timeout: 30000 }))

// 探测各声音当前是否可用（edge-tts 渠道连通性，后端缓存 5 分钟）；失败返回 null 保持现状
export const fetchTtsVoices = async () => {
  try { return unwrap(await http.get('/tts/voices')) } catch { return null }
}

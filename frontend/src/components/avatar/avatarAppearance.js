// 参数化数字人外观配置与音色映射（用于场景预设、捏脸自定义与跨端同步）

export const SKIN_TONES = {
  fair: { top: '#ffede4', bottom: '#f9cfc0', neck: '#f5c6b5', shadow: '#dfa695', nose: '#d59582' },
  warm: { top: '#ffe5d0', bottom: '#f7c8a8', neck: '#f2bfa0', shadow: '#dca17e', nose: '#c98968' },
  medium: { top: '#fae0cc', bottom: '#ecc0a2', neck: '#e7b697', shadow: '#d19a7a', nose: '#be8161' },
}

export const AVATAR_PRESETS = {
  leo_2d: {
    base: 'male',
    skinTone: 'warm',
    hairStyle: 'undercut',
    hairColor: '#47302a',
    eyeStyle: 'bright',
    eyeColor: '#3b2738',
    glasses: 'none',
    outfit: 'apron_violet',
    accessory: 'none',
    backdrop: 'cafe',
  },
  emily_2d: {
    base: 'female',
    skinTone: 'fair',
    hairStyle: 'low_bun',
    hairColor: '#46335e',
    eyeStyle: 'gentle',
    eyeColor: '#35264a',
    glasses: 'none',
    outfit: 'airline_blazer',
    accessory: 'headset_single',
    backdrop: 'airport',
  },
  david_2d: {
    base: 'male',
    skinTone: 'medium',
    hairStyle: 'side_part',
    hairColor: '#2c263f',
    eyeStyle: 'calm',
    eyeColor: '#2d294b',
    glasses: 'rect_dark',
    outfit: 'pm_suit',
    accessory: 'none',
    backdrop: 'meeting',
  },
  sarah_2d: {
    base: 'female',
    skinTone: 'fair',
    hairStyle: 'shoulder_sleek',
    hairColor: '#3d2b52',
    eyeStyle: 'calm',
    eyeColor: '#2d2040',
    glasses: 'round_violet',
    outfit: 'tech_cardigan',
    accessory: 'earring_pearl',
    backdrop: 'interview',
  },
  claire_2d: {
    base: 'female',
    skinTone: 'warm',
    hairStyle: 'high_ponytail',
    hairColor: '#3b2b4a',
    eyeStyle: 'bright',
    eyeColor: '#35264a',
    glasses: 'none',
    outfit: 'station_uniform',
    accessory: 'headset_single',
    backdrop: 'station',
  },
}

export const APPEARANCE_OPTIONS = {
  backdrop: [
    { value: 'cafe', label: '咖啡厅' },
    { value: 'airport', label: '机场大厅' },
    { value: 'station', label: '火车站大厅' },
    { value: 'meeting', label: '商务会议室' },
    { value: 'interview', label: '科技面试室' },
    { value: 'library', label: '图书馆' },
    { value: 'park', label: '公园街头' },
    { value: 'rooftop', label: '黄昏天台' },
    { value: 'study', label: '温馨书房' },
    { value: 'studio', label: '极简纯紫' },
  ],
  base: [
    { value: 'male', label: '男性轮廓' },
    { value: 'female', label: '女性轮廓' },
  ],
  skinTone: [
    { value: 'fair', label: '白皙', color: '#ffede4' },
    { value: 'warm', label: '暖调', color: '#ffe0c4' },
    { value: 'medium', label: '自然', color: '#ecc0a2' },
  ],
  hairStyle: [
    { value: 'undercut', label: '清爽短发' },
    { value: 'side_part', label: '商务偏分' },
    { value: 'spiky_crop', label: '利落刺猬头' },
    { value: 'curly_short', label: '蓬松卷发' },
    { value: 'low_bun', label: '优雅盘发' },
    { value: 'high_ponytail', label: '元气高马尾' },
    { value: 'shoulder_sleek', label: '及肩直发' },
    { value: 'wavy_long', label: '温柔大波浪' },
  ],
  hairColor: [
    { value: '#47302a', label: '深棕' },
    { value: '#2c263f', label: '靛黑' },
    { value: '#46335e', label: '梅紫' },
    { value: '#6b4a33', label: '栗棕' },
    { value: '#8c4a32', label: '暖红棕' },
    { value: '#b8864b', label: '亚麻金' },
    { value: '#3b4252', label: '冷灰' },
  ],
  eyeStyle: [
    { value: 'bright', label: '明亮' },
    { value: 'gentle', label: '柔和' },
    { value: 'calm', label: '沉稳' },
  ],
  eyeColor: [
    { value: '#3b2738', label: '深棕' },
    { value: '#2d294b', label: '深紫' },
    { value: '#2563eb', label: '钴蓝' },
    { value: '#0f766e', label: '墨绿' },
  ],
  glasses: [
    { value: 'none', label: '无眼镜' },
    { value: 'rect_dark', label: '深色方框' },
    { value: 'round_violet', label: '紫框圆镜' },
  ],
  outfit: [
    { value: 'apron_violet', label: '紫色围裙' },
    { value: 'airline_blazer', label: '航司制服' },
    { value: 'station_uniform', label: '铁路制服' },
    { value: 'pm_suit', label: '商务西装' },
    { value: 'tech_cardigan', label: '针织开衫' },
  ],
  accessory: [
    { value: 'none', label: '无配饰' },
    { value: 'headset_single', label: '单耳耳麦' },
    { value: 'headphones', label: '头戴耳机' },
    { value: 'earring_pearl', label: '珍珠耳钉' },
    { value: 'hairclip', label: '暖黄发夹' },
    { value: 'beret', label: '紫罗兰贝雷帽' },
    { value: 'bow_tie', label: '学院领结' },
    { value: 'name_badge', label: '工作工牌' },
  ],
}

export function resolveAppearance(characterId = 'leo_2d', custom = null) {
  const basePreset = AVATAR_PRESETS[characterId] || AVATAR_PRESETS.leo_2d
  if (!custom || typeof custom !== 'object') return { ...basePreset }
  return { ...basePreset, ...custom }
}

const ROLE_VOICE_MAP = {
  'en-US-YoungMale': 'andrew',
  'en-US-Male': 'guy',
  'en-US-MatureMale': 'brian',
  'en-US-Female': 'aria',
  'en-US-YoungFemale': 'emma',
  'en-GB-Female': 'sonia',
  'en-GB-Male': 'ryan',
  'en-AU-Female': 'natasha',
  'en-AU-Male': 'william',
}

export function resolveRoleVoiceStyle(roleVoice, validStyles) {
  if (!roleVoice) return 'emma'
  const direct = String(roleVoice).trim()
  const mapped = ROLE_VOICE_MAP[direct] || direct.toLowerCase()
  if (Array.isArray(validStyles) && validStyles.includes(mapped)) return mapped
  return ROLE_VOICE_MAP[direct] || 'emma'
}

// 场景展示元数据：分类文案、难度、封面色调与图标，供封面组件与历史记录等页面共用。

// 分类长文案（列表页、历史记录用）；短文案见各页自己的筛选标签
export const CATEGORY_LABELS = {
  daily: '日常沟通', travel: '出行场景', business: '职场沟通', career: '求职训练',
  academic: '学术场景', campus: '校园生活', interview: '模拟面试', debate: '辩论讨论', custom: '自定义',
}
export const categoryLabel = (key) => CATEGORY_LABELS[key] || key || '通用'

// 难度五级：后端只存英文枚举，展示层负责中文
export const DIFFICULTIES = {
  entry: { label: '入门', cls: 'entry' }, easy: { label: '简单', cls: 'easy' }, normal: { label: '普通', cls: 'normal' },
  hard: { label: '困难', cls: 'hard' }, expert: { label: '专家', cls: 'expert' },
}
export const diffInfo = (value) => DIFFICULTIES[value] || DIFFICULTIES.normal
export const diffLabel = (value) => diffInfo(value).label
export const diffClass = (value) => diffInfo(value).cls

// 图标：场景专属 > 分类 > 对话模式 > 兜底
const SCENE_VISUALS = { airport_rebooking: 'plane', cafe_ordering: 'coffee', launch_alignment: 'messages', tech_interview: 'briefcase' }
const CATEGORY_VISUALS = { daily: 'messages', business: 'messages', career: 'briefcase', academic: 'graduation-cap', travel: 'plane', campus: 'graduation-cap', custom: 'compass' }
const MODE_VISUALS = { conversation: 'messages', interview: 'briefcase', debate: 'messages' }
export const sceneIcon = (scene = {}) =>
  SCENE_VISUALS[scene.id] || CATEGORY_VISUALS[scene.category] || MODE_VISUALS[scene.mode] || 'messages'

// 色调只认已定义的 6 套，未知分类回落到自定义紫粉
const TONES = ['daily', 'travel', 'business', 'career', 'academic', 'custom']
export const sceneTone = (scene = {}) => {
  const value = scene.id === 'airport_rebooking' ? 'travel' : (scene.category || 'custom')
  return TONES.includes(value) ? value : 'custom'
}

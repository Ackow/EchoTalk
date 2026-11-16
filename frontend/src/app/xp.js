// 全局经验值与段位系统（优先同步后端真实用户画像，未登录时使用本地状态兜底）
import { computed, ref } from 'vue'
import { claimDailyCheckin, getListeningProfile } from '../api/listening'
import { session } from '../auth/session'

export const RANK_TIERS = [
  { level: 1, name: '微光旅人', badge: 'Spark', minXp: 0, maxXp: 150, color: '#8b73dd', desc: '完成首次对话或 2–3 个听力单元，开启每日开口与磨耳朵习惯。' },
  { level: 2, name: '捕风听者', badge: 'Catcher', minXp: 150, maxXp: 500, color: '#35a876', desc: '慢速与日常高频句型稳定听辨，开始尝试无字幕独立作答。' },
  { level: 3, name: '声纹破译师', badge: 'Decoder', minXp: 500, maxXp: 1200, color: '#4c8bf5', desc: '胜任四级听力与日常多轮对话，能捕捉连读、弱读与关键转折。' },
  { level: 4, name: '频率领航员', badge: 'Pilot', minXp: 1200, maxXp: 2800, color: '#d97706', desc: '适配六级长篇、常速英语电台与常规技术面试表达。' },
  { level: 5, name: '共鸣大师', badge: 'Resonance', minXp: 2800, maxXp: 6000, color: '#db2777', desc: '从容应对面试深度追问、多角色辩论与学术讲座信息拆解。' },
  { level: 6, name: '声域传说', badge: 'Legend', minXp: 6000, maxXp: null, color: '#7c3aed', desc: '长期高频原速盲听与自由表达双高，达成稳定高阶语言掌控。' }
]

const STORAGE_KEY = 'echotalk_global_xp'
const initialXp = Number(localStorage.getItem(STORAGE_KEY) || 585)

export const totalXp = ref(Number.isFinite(initialXp) ? initialXp : 585)
export const todayXp = ref(45)
export const dailyGoalXp = 60

export const dailyQuests = ref([
  { id: 'q-checkin', title: '每日签到领积分', current: 0, target: 1, xp: 5, type: 'checkin' },
  { id: 'q-listen', title: '完成 1 节听力训练', current: 1, target: 1, xp: 25, route: 'listening' },
  { id: 'q-talk', title: '完成 3 轮语音对话', current: 1, target: 3, xp: 15, route: 'practice' },
  { id: 'q-review', title: '完成今日间隔复习', current: 0, target: 1, xp: 15, route: 'review' }
])

export const streakDays = ref(0)
export const checkedInToday = ref(false)
export const checkinStreak = ref(0)
export const nextCheckinXp = ref(5)
export const checkinRewards = ref([5, 8, 10, 12, 15, 18, 25])

export function applyXpSnapshot(snapshot) {
  if (!snapshot) return
  if (typeof snapshot.totalXp === 'number') {
    totalXp.value = snapshot.totalXp
    localStorage.setItem(STORAGE_KEY, String(snapshot.totalXp))
  }
  if (typeof snapshot.todayXp === 'number') {
    todayXp.value = snapshot.todayXp
  }
  if (typeof snapshot.streakDays === 'number') {
    streakDays.value = snapshot.streakDays
  }
  if (typeof snapshot.checkedInToday === 'boolean') {
    checkedInToday.value = snapshot.checkedInToday
  }
  if (typeof snapshot.checkinStreak === 'number') {
    checkinStreak.value = snapshot.checkinStreak
  }
  if (typeof snapshot.nextCheckinXp === 'number') {
    nextCheckinXp.value = snapshot.nextCheckinXp
  }
  if (Array.isArray(snapshot.checkinRewards) && snapshot.checkinRewards.length) {
    checkinRewards.value = snapshot.checkinRewards
  }
  if (Array.isArray(snapshot.dailyQuests)) {
    dailyQuests.value = snapshot.dailyQuests
  }
}

export async function performDailyCheckin() {
  if (!session.token) {
    return { requiresLogin: true, gainedXp: 0, alreadyCheckedIn: false }
  }
  const { data } = await claimDailyCheckin()
  applyXpSnapshot(data)
  return {
    requiresLogin: false,
    gainedXp: Number(data?.gainedXp || 0),
    alreadyCheckedIn: Boolean(data?.alreadyCheckedIn),
  }
}

export async function syncGlobalXpProfile() {
  if (!session.token) return null
  try {
    const { data } = await getListeningProfile()
    applyXpSnapshot(data)
    return data
  } catch {
    return null
  }
}

export function addGlobalXp(amount) {
  if (!amount || amount <= 0) return
  totalXp.value += amount
  todayXp.value += amount
  localStorage.setItem(STORAGE_KEY, String(totalXp.value))
}

export const nextRank = computed(() => {
  const cur = currentRank.value
  return RANK_TIERS.find((t) => t.level === cur.level + 1) || null
})

export const currentRank = computed(() => {
  const xp = totalXp.value
  let tier = RANK_TIERS[0]
  for (const t of RANK_TIERS) {
    if (xp >= t.minXp) tier = t
  }

  if (tier.maxXp === null) {
    return {
      ...tier,
      subRank: 'MAX',
      progressPct: 100,
      nextNeed: 0
    }
  }

  const span = tier.maxXp - tier.minXp
  const offset = Math.max(0, xp - tier.minXp)
  const ratio = Math.min(1, offset / span)
  const subRank = ratio < 0.34 ? 'I' : ratio < 0.67 ? 'II' : 'III'

  return {
    ...tier,
    subRank,
    progressPct: Math.round(ratio * 100),
    nextNeed: Math.max(0, tier.maxXp - xp)
  }
})

if (session.token) {
  syncGlobalXpProfile()
}

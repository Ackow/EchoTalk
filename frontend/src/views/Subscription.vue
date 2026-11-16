<template>
  <div class="task-center-page">
    <div class="task-center-container">
      <!-- 顶部双卡：1. 单一共享免费额度池百分比 + 2. 回声积分与段位资产 -->
      <section class="top-overview-grid">
        <div class="tactile-card pool-card">
          <div class="pool-head">
            <div>
              <div class="pool-title-row">
                <h3>今日免费额度池</h3>
                <span class="reset-pill">每日 00:00 重置</span>
              </div>
              <p class="muted-text">
                1v1 对话、多角色交锋、听力 AI 助教与场景生成共用此额度池
              </p>
            </div>
            <div class="pool-pct-readout">
              <template v-if="profile.daily_pool_capacity === -1">
                <strong class="pct-num unlimited">无限畅享</strong>
              </template>
              <template v-else>
                <strong class="pct-num" :class="{ warn: profile.daily_pool_pct >= 80 }">
                  {{ profile.daily_pool_pct }}%
                </strong>
                <small>已使用 · 剩余 {{ Math.max(0, 100 - profile.daily_pool_pct) }}%</small>
              </template>
            </div>
          </div>

          <div class="pool-track">
            <div
              class="pool-fill"
              :class="{ warn: profile.daily_pool_pct >= 80, full: profile.daily_pool_pct >= 100 }"
              :style="{
                width:
                  profile.daily_pool_capacity === -1 ? '100%' : `${Math.min(100, profile.daily_pool_pct)}%`,
              }"
            ></div>
          </div>

          <div class="switch-row">
            <div class="switch-info">
              <strong>免费额度池用满（100%）后自动消耗回声积分</strong>
              <span>关闭后，当日免费额度耗尽将暂停扣费，保护你的回声积分余额</span>
            </div>
            <label class="tactile-switch">
              <input
                type="checkbox"
                :checked="profile.auto_use_credits"
                @change="toggleAutoCredits($event.target.checked)"
              />
              <span class="slider"></span>
            </label>
          </div>
        </div>

        <div class="tactile-card wallet-card">
          <div class="wallet-main">
            <div class="wallet-block">
              <span class="wallet-label">可用回声积分（Echo Credit）</span>
              <div class="wallet-val-row">
                <EchoCreditIcon :size="24" />
                <strong class="wallet-num">{{ profile.credits_balance }}</strong>
                <span class="tier-pill" :class="`tier-${profile.plan_tier}`">
                  {{ tierLabel(profile.plan_tier) }}
                </span>
              </div>
              <small class="muted-text">
                <template v-if="profile.plan_tier !== 'free' && profile.plan_expires_at">
                  {{ profile.plan_name }} · 有效期至 {{ formatDate(profile.plan_expires_at).slice(0, 10) }}
                </template>
                <template v-else>
                  可用于超出每日免费额度后的对话轮次与 AI 生成
                </template>
              </small>
            </div>

            <div class="xp-divider"></div>

            <div class="wallet-block">
              <span class="wallet-label">当前段位与累计经验</span>
              <div class="wallet-val-row">
                <span class="rank-lv" :style="{ background: currentRank.color }">Lv.{{ currentRank.level }}</span>
                <strong class="xp-num">{{ totalXp }} <small>XP</small></strong>
              </div>
              <small class="muted-text">{{ currentRank.name }} · {{ currentRank.subRank }}</small>
            </div>
          </div>

          <div class="wallet-actions">
            <button class="btn-secondary sm" type="button" @click="ledgerOpen = true">积分收支明细</button>
            <button class="btn-primary sm" type="button" @click="subDialogOpen = true">会员订阅 / 充值</button>
          </div>
        </div>
      </section>

      <p v-if="bannerMsg" class="banner-tip" :class="{ err: bannerErr }">{{ bannerMsg }}</p>

      <!-- 中部：7天连续登录签到（XP + 回声积分二合一） -->
      <section class="tactile-card checkin-section">
        <div class="section-head">
          <div>
            <div class="title-with-badge">
              <h3>每日签到领双份奖励</h3>
              <span class="streak-pill">已连续签到 {{ profile.checkin_streak }} 天</span>
              <span v-if="activeMultiplier > 1" class="camp-pill">限时活动 {{ activeMultiplier }}x 积分加成中</span>
            </div>
            <p class="muted-text">每日签到同时获得段位经验（XP）与回声积分，连续 3 / 7 天享额外里程碑加成</p>
          </div>
          <button
            class="btn-primary"
            :class="{ done: profile.checked_in_today }"
            :disabled="profile.checked_in_today || checkingIn"
            type="button"
            @click="handleCheckin"
          >
            {{ profile.checked_in_today ? '今日已签到' : '立即签到' }}
          </button>
        </div>

        <div class="checkin-days-grid">
          <div
            v-for="(xpVal, idx) in checkinXpList"
            :key="idx"
            class="day-card"
            :class="dayStatusClass(idx)"
          >
            <span class="day-index">第 {{ idx + 1 }} 天</span>
            <div class="day-rewards">
              <span class="reward-credit">
                <EchoCreditIcon :size="13" /> +{{ dayCreditReward(idx + 1) }}
              </span>
              <span class="reward-xp">+{{ xpVal }} XP</span>
            </div>
            <span class="day-status">{{ dayStatusText(idx) }}</span>
          </div>
        </div>
      </section>

      <!-- 底部：统一任务中心（XP 经验任务 + 回声积分任务合二为一） -->
      <section class="tactile-card tasks-section">
        <div class="section-head">
          <div>
            <h3>日常训练与成长任务</h3>
            <p class="muted-text">完成口语、听力、复习或创建场景，一次打卡同时领取 XP 段位经验与回声积分</p>
          </div>
        </div>

        <div class="tasks-grid">
          <div v-for="t in tasks" :key="t.task_code" class="task-card" :class="{ finished: t.finished }">
            <div class="task-top">
              <span class="task-cat" :class="t.category">
                {{ t.category === 'daily' ? '每日训练' : '新手里程碑' }}
              </span>
              <div class="dual-rewards">
                <span class="badge-credit">
                  <EchoCreditIcon :size="13" /> +{{ Math.round(t.reward_credits * activeMultiplier) }}
                </span>
                <span class="badge-xp">+{{ t.reward_xp || 15 }} XP</span>
              </div>
            </div>

            <h4>{{ t.title }}</h4>
            <p>{{ t.description }}</p>

            <div class="task-foot">
              <div class="task-prog-wrap">
                <div class="task-prog-bar">
                  <div
                    class="task-prog-fill"
                    :style="{ width: `${Math.min(100, Math.round((t.progress_count / Math.max(1, t.target_count)) * 100))}%` }"
                  ></div>
                </div>
                <span class="task-prog-text">
                  {{ Math.min(t.progress_count, t.target_count) }} / {{ t.target_count }}
                </span>
              </div>

              <button
                v-if="t.claimable"
                class="btn-primary sm"
                type="button"
                @click="handleClaimTask(t.task_code)"
              >
                领取双奖励
              </button>
              <span v-else-if="t.finished" class="done-pill">今日已领</span>
              <button v-else class="btn-secondary sm" type="button" @click="router.push(t.route_path)">
                去完成
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- 积分收支明细弹窗 -->
    <div v-if="ledgerOpen" class="modal-backdrop" @click.self="ledgerOpen = false">
      <div class="modal-card">
        <div class="modal-head">
          <h3>回声积分收支明细</h3>
          <button class="close-btn" type="button" @click="ledgerOpen = false">
            <AppIcon name="x" :size="16" />
          </button>
        </div>
        <div v-if="ledger.length === 0" class="empty-tip">暂无积分变动记录</div>
        <div v-else class="ledger-list">
          <div v-for="item in ledger" :key="item.id" class="ledger-row">
            <div>
              <strong>{{ item.remark }}</strong>
              <small>{{ formatDate(item.created_at) }}</small>
            </div>
            <div class="ledger-right">
              <span class="delta" :class="item.delta >= 0 ? 'plus' : 'minus'">
                {{ item.delta >= 0 ? `+${item.delta}` : item.delta }}
              </span>
              <small>余额 {{ item.balance_after }}</small>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 纯净版会员订阅弹窗（图1） -->
    <SubscriptionDialog v-if="subDialogOpen" @close="subDialogOpen = false" @updated="loadAll" />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import EchoCreditIcon from '../components/EchoCreditIcon.vue'
import SubscriptionDialog from '../components/settings/SubscriptionDialog.vue'
import {
  claimSaasTask,
  getSaasLedger,
  getSaasMe,
  getSaasTasks,
  postDailyCheckin,
  refreshSaasState,
  updateSaasSettings,
} from '../api/saas'
import { addGlobalXp, currentRank, syncGlobalXpProfile, totalXp } from '../app/xp'
import { session } from '../auth/session'

const router = useRouter()
const subDialogOpen = ref(false)
const ledgerOpen = ref(false)
const checkingIn = ref(false)
const bannerMsg = ref('')
const bannerErr = ref(false)

const profile = reactive({
  plan_tier: 'free',
  plan_name: 'Free 免费体验版',
  credits_balance: 0,
  auto_use_credits: true,
  checkin_streak: 0,
  checked_in_today: false,
  daily_pool_capacity: 40,
  daily_pool_used: 0,
  daily_pool_pct: 0,
  checkin_xp_rewards: [5, 8, 10, 12, 15, 18, 25],
  active_campaigns: [],
})

const tasks = ref([])
const ledger = ref([])

const checkinXpList = computed(() => profile.checkin_xp_rewards || [5, 8, 10, 12, 15, 18, 25])
const activeMultiplier = computed(() => {
  const mults = (profile.active_campaigns || []).map((c) => Number(c.bonus_multiplier || 1))
  return mults.length ? Math.max(...mults) : 1
})

function tierLabel(tier) {
  return { free: 'FREE', pro: 'PRO', enterprise: 'ENTERPRISE' }[tier] || 'FREE'
}

function dayCreditReward(dayNum) {
  const tierMult = profile.plan_tier === 'enterprise' ? 3 : profile.plan_tier === 'pro' ? 2 : 1
  const base = Math.round(10 * tierMult * activeMultiplier.value)
  const milestone = dayNum === 7 ? 40 : dayNum === 3 ? 15 : 0
  return base + milestone
}

function dayStatusClass(idx) {
  const streakMod = profile.checkin_streak % 7
  const filledCount = profile.checked_in_today && streakMod === 0 && profile.checkin_streak > 0 ? 7 : streakMod
  if (idx < filledCount) return 'claimed'
  if (idx === filledCount && !profile.checked_in_today) return 'today'
  return ''
}

function dayStatusText(idx) {
  const cls = dayStatusClass(idx)
  if (cls === 'claimed') return '已领取'
  if (cls === 'today') return '今日可签'
  return '待解锁'
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN', { hour12: false }).slice(0, 16)
}

function showTip(msg, isErr = false) {
  bannerMsg.value = msg
  bannerErr.value = isErr
}

async function loadAll() {
  if (!session.token) return
  const [meRes, taskRes, ledgerRes] = await Promise.all([
    getSaasMe(),
    getSaasTasks(),
    getSaasLedger(1, 20),
  ])
  Object.assign(profile, meRes.data)
  tasks.value = taskRes.data.items || []
  ledger.value = ledgerRes.data.items || []
  await refreshSaasState()
  await syncGlobalXpProfile()
}

async function toggleAutoCredits(val) {
  try {
    await updateSaasSettings(val)
    profile.auto_use_credits = val
    await refreshSaasState()
    showTip(val ? '已开启「免费额度用满后自动使用回声积分」' : '已关闭自动积分抵扣')
  } catch (e) {
    showTip(e?.response?.data?.error?.message || '设置更新失败', true)
  }
}

async function handleCheckin() {
  if (!session.token) {
    router.push({ name: 'login' })
    return
  }
  checkingIn.value = true
  try {
    const { data } = await postDailyCheckin()
    if (data.xp_earned) addGlobalXp(data.xp_earned)
    showTip(`签到成功！获得 +${data.credits_earned} 回声积分 与 +${data.xp_earned || 5} XP（已连签 ${data.checkin_streak} 天）`)
    await loadAll()
  } catch (e) {
    showTip(e?.response?.data?.error?.message || '签到失败', true)
  } finally {
    checkingIn.value = false
  }
}

async function handleClaimTask(taskCode) {
  try {
    const { data } = await claimSaasTask(taskCode)
    if (data.xp_earned) addGlobalXp(data.xp_earned)
    showTip(`奖励已到账：+${data.credits_earned} 回声积分 · +${data.xp_earned || 15} XP`)
    await loadAll()
  } catch (e) {
    showTip(e?.response?.data?.error?.message || '领取失败', true)
  }
}

onMounted(loadAll)
</script>

<style scoped>
.task-center-page {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 22px 28px 28px;
  overflow-y: auto;
}
.task-center-container {
  width: 100%;
  max-width: 1320px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.tactile-card {
  border: 1.5px solid #ebe7f5;
  border-bottom: 4px solid #e3dcf2;
  border-radius: 18px;
  background: #ffffff;
  padding: 20px 22px;
}
.top-overview-grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 18px;
}
@media (max-width: 980px) {
  .top-overview-grid {
    grid-template-columns: 1fr;
  }
}
.pool-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}
.pool-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}
.pool-title-row h3,
.section-head h3 {
  margin: 0;
  font-size: 17px;
  color: #35304e;
}
.reset-pill {
  background: #f4f0ff;
  color: #6046b4;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
}
.muted-text {
  margin: 0;
  font-size: 12.5px;
  color: #837f96;
}
.pool-pct-readout {
  text-align: right;
  flex-shrink: 0;
}
.pct-num {
  display: block;
  font-size: 26px;
  color: #6046b4;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}
.pct-num.warn {
  color: #d97706;
}
.pct-num.unlimited {
  font-size: 18px;
  color: #2a8c5f;
}
.pool-pct-readout small {
  font-size: 11.5px;
  color: #837f96;
}
.pool-track {
  margin: 14px 0 16px;
  height: 11px;
  background: #f1edf9;
  border-radius: 999px;
  overflow: hidden;
}
.pool-fill {
  height: 100%;
  background: linear-gradient(90deg, #8b73dd, #6951b8);
  border-radius: 999px;
  transition: width 0.3s ease;
}
.pool-fill.warn {
  background: linear-gradient(90deg, #f59e0b, #d97706);
}
.pool-fill.full {
  background: #dc2626;
}
.switch-row {
  padding: 11px 14px;
  border-radius: 12px;
  background: #faf9fd;
  border: 1px solid #efecf7;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
.switch-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.switch-info strong {
  font-size: 13px;
  color: #35304e;
}
.switch-info span {
  font-size: 11.5px;
  color: #837f96;
}
.tactile-switch {
  position: relative;
  width: 42px;
  height: 23px;
  flex-shrink: 0;
}
.tactile-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.slider {
  position: absolute;
  inset: 0;
  border-radius: 999px;
  background: #ddd6ec;
  cursor: pointer;
  transition: 0.2s;
}
.slider::before {
  content: '';
  position: absolute;
  width: 17px;
  height: 17px;
  left: 3px;
  top: 3px;
  border-radius: 50%;
  background: #fff;
  transition: 0.2s;
}
.tactile-switch input:checked + .slider {
  background: #8b73dd;
}
.tactile-switch input:checked + .slider::before {
  transform: translateX(19px);
}
.wallet-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 14px;
}
.wallet-main {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 16px;
  background: #faf9fd;
  border: 1px solid #efecf7;
  border-radius: 14px;
  padding: 14px 16px;
}
.xp-divider {
  width: 1px;
  height: 48px;
  background: #e6e1f2;
}
.wallet-label {
  display: block;
  font-size: 11.5px;
  color: #837f96;
  margin-bottom: 6px;
}
.wallet-val-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.wallet-num {
  font-size: 24px;
  color: #b45309;
  font-variant-numeric: tabular-nums;
}
.xp-num {
  font-size: 22px;
  color: #35304e;
  font-variant-numeric: tabular-nums;
}
.xp-num small {
  font-size: 12px;
  color: #837f96;
}
.rank-lv {
  padding: 2px 7px;
  border-radius: 6px;
  color: #fff;
  font-size: 11px;
  font-weight: 800;
}
.tier-pill {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 800;
}
.tier-free {
  background: #eaf7f0;
  color: #2a8c5f;
}
.tier-pro {
  background: linear-gradient(135deg, #8b73dd, #6046b4);
  color: #ffffff;
}
.tier-enterprise {
  background: #2f2a45;
  color: #ffd670;
}
.wallet-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  margin-bottom: 14px;
}
.title-with-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}
.streak-pill {
  background: #eee9ff;
  color: #6046b4;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 700;
}
.camp-pill {
  background: #fff3ea;
  color: #c46a24;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 700;
}
.checkin-days-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 10px;
}
@media (max-width: 860px) {
  .checkin-days-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}
.day-card {
  border: 1.5px solid #efecf7;
  border-radius: 13px;
  background: #faf9fd;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.day-card.claimed {
  background: #f3faf6;
  border-color: #c6e9d6;
}
.day-card.today {
  background: #faf7ff;
  border-color: #8b73dd;
  box-shadow: 0 3px 10px rgba(139, 115, 221, 0.14);
}
.day-index {
  font-size: 11.5px;
  font-weight: 700;
  color: #625e76;
}
.day-rewards {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
}
.reward-credit {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 13px;
  font-weight: 800;
  color: #b45309;
}
.reward-xp {
  font-size: 11px;
  font-weight: 700;
  color: #6046b4;
}
.day-status {
  font-size: 11px;
  color: #837f96;
}
.day-card.claimed .day-status {
  color: #2a8c5f;
  font-weight: 700;
}
.day-card.today .day-status {
  color: #6046b4;
  font-weight: 700;
}
.tasks-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
@media (max-width: 980px) {
  .tasks-grid {
    grid-template-columns: 1fr;
  }
}
.task-card {
  border: 1.5px solid #efecf7;
  border-radius: 14px;
  background: #faf9fd;
  padding: 15px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.task-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.task-cat {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  background: #eee9ff;
  color: #6046b4;
}
.task-cat.onboarding {
  background: #eaf7f0;
  color: #2a8c5f;
}
.dual-rewards {
  display: flex;
  align-items: center;
  gap: 6px;
}
.badge-credit {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #b45309;
  font-size: 11.5px;
  font-weight: 800;
  padding: 2px 7px;
  border-radius: 6px;
}
.badge-xp {
  background: #f4f0ff;
  color: #6046b4;
  font-size: 11.5px;
  font-weight: 800;
  padding: 2px 7px;
  border-radius: 6px;
}
.task-card h4 {
  margin: 0;
  font-size: 15px;
  color: #35304e;
}
.task-card p {
  margin: 0;
  font-size: 12px;
  color: #625e76;
  flex: 1;
}
.task-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-top: 4px;
}
.task-prog-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}
.task-prog-bar {
  flex: 1;
  height: 6px;
  background: #e9e4f5;
  border-radius: 999px;
  overflow: hidden;
}
.task-prog-fill {
  height: 100%;
  background: #8b73dd;
  border-radius: 999px;
}
.task-prog-text {
  font-size: 11.5px;
  color: #837f96;
  font-variant-numeric: tabular-nums;
}
.done-pill {
  font-size: 12px;
  font-weight: 700;
  color: #2a8c5f;
}
.banner-tip {
  margin: 0;
  padding: 9px 14px;
  border-radius: 10px;
  background: #eaf7f0;
  color: #2a8c5f;
  font-size: 13px;
  font-weight: 600;
}
.banner-tip.err {
  background: #fdece8;
  color: #b84a39;
}
.btn-primary {
  border: 1.5px solid #8067d1;
  border-bottom: 3px solid #6951b8;
  border-radius: 10px;
  background: #8b73dd;
  color: #ffffff;
  font-weight: 700;
  padding: 8px 16px;
  cursor: pointer;
}
.btn-primary.done {
  background: #eaf7f0;
  border-color: #bfe4d0;
  border-bottom-color: #9dd4b7;
  color: #2a8c5f;
  cursor: default;
}
.btn-secondary {
  border: 1.5px solid #e6e1f2;
  border-bottom: 3px solid #ddd6ec;
  border-radius: 10px;
  background: #ffffff;
  color: #5a5572;
  font-weight: 600;
  padding: 8px 16px;
  cursor: pointer;
}
.btn-primary.sm,
.btn-secondary.sm {
  padding: 6px 12px;
  font-size: 12px;
}
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: grid;
  place-items: center;
  background: var(--scrim-bg, rgba(34, 37, 59, 0.28));
  -webkit-backdrop-filter: var(--scrim-blur, blur(2px));
  backdrop-filter: var(--scrim-blur, blur(2px));
}
.modal-card {
  width: 480px;
  max-width: 92vw;
  max-height: 80vh;
  overflow-y: auto;
  border: 1.5px solid #ebe7f5;
  border-bottom: 5px solid #e3dcf2;
  border-radius: 20px;
  background: #ffffff;
  padding: 20px 22px;
}
.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.modal-head h3 {
  margin: 0;
  font-size: 16px;
  color: #35304e;
}
.close-btn {
  border: 1px solid #efecf7;
  background: #faf9fd;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  cursor: pointer;
}
.ledger-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ledger-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-radius: 10px;
  background: #faf9fd;
  border: 1px solid #efecf7;
}
.ledger-row strong {
  display: block;
  font-size: 13px;
  color: #35304e;
}
.ledger-row small {
  font-size: 11.5px;
  color: #837f96;
}
.ledger-right {
  text-align: right;
}
.delta {
  display: block;
  font-size: 14px;
  font-weight: 800;
}
.delta.plus {
  color: #2a8c5f;
}
.delta.minus {
  color: #b84a39;
}
.empty-tip {
  text-align: center;
  padding: 24px;
  color: #837f96;
}
</style>

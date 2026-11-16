<template>
  <Teleport to="body">
    <div class="sub-scrim" @click.self="emit('close')">
      <section class="sub-modal" role="dialog" aria-modal="true" aria-labelledby="sub-modal-title">
        <!-- 顶栏：月付/年付切换 + 当前积分、兑换码与对齐的关闭按钮 -->
        <div class="top-bar">
          <div class="billing-toggle">
            <button
              class="bill-btn"
              :class="{ active: billingCycle === 'monthly' }"
              type="button"
              @click="billingCycle = 'monthly'"
            >
              按月订阅
            </button>
            <button
              class="bill-btn"
              :class="{ active: billingCycle === 'yearly' }"
              type="button"
              @click="billingCycle = 'yearly'"
            >
              按年订阅 <span class="save-tag">省 20%+</span>
            </button>
          </div>

          <div class="top-right">
            <span class="sub-status-chip" :class="`tier-${currentTier}`">
              <b>{{ tierLabel(currentTier) }}</b>
              <template v-if="currentTier !== 'free' && saasState.plan_expires_at">
                · {{ formatExpireShort(saasState.plan_expires_at) }} 到期
              </template>
              <template v-else>· 免费版</template>
            </span>
            <span class="balance-chip">
              <EchoCreditIcon :size="15" />
              <b>{{ saasState.credits_balance }}</b> 点
            </span>
            <div class="redeem-inline">
              <input
                v-model.trim="redeemInput"
                type="text"
                placeholder="输入兑换码激活"
                @keyup.enter="handleRedeem"
              />
              <button type="button" :disabled="!redeemInput || redeeming" @click="handleRedeem">
                {{ redeeming ? '...' : '兑换' }}
              </button>
            </div>
            <button class="dialog-close" type="button" aria-label="关闭" @click="emit('close')">
              <AppIcon name="x" :size="16" />
            </button>
          </div>
        </div>

        <p v-if="bannerMsg" class="banner-tip" :class="{ err: bannerErr }">{{ bannerMsg }}</p>

        <!-- 图1核心：三栏套餐对比卡片 -->
        <div class="plans-grid">
          <div
            v-for="p in plans"
            :key="p.tier"
            class="tactile-card plan-card"
            :class="{ featured: p.tier === 'pro', current: currentTier === p.tier }"
          >
            <div class="plan-head">
              <span class="tier-pill" :class="`tier-${p.tier}`">{{ tierLabel(p.tier) }}</span>
              <span v-if="currentTier === p.tier" class="current-tag">当前方案</span>
            </div>
            <h3>{{ p.name }}</h3>
            <p class="plan-desc">{{ p.description }}</p>
            <div class="plan-price">
              <template v-if="p.monthly_price_yuan === 0">
                <strong>¥0</strong><span>/ 永久免费</span>
              </template>
              <template v-else>
                <strong>¥{{ billingCycle === 'yearly' ? p.yearly_price_yuan : p.monthly_price_yuan }}</strong>
                <span>/ {{ billingCycle === 'yearly' ? '年' : '月' }}</span>
                <del v-if="billingCycle === 'yearly' && p.monthly_price_yuan * 12 > p.yearly_price_yuan" class="price-strike">
                  ¥{{ p.monthly_price_yuan * 12 }}
                </del>
              </template>
            </div>

            <ul class="plan-features">
              <li>
                每月赠送 <b>{{ p.monthly_grant_credits }}</b> 积分（签到 {{ p.checkin_multiplier }}x）
              </li>
              <li>
                每日免费额度池：<b>{{ poolCapacityLabel(p.tier) }}</b>
              </li>
              <li>
                超额积分抵扣：<b>{{ p.tier === 'enterprise' ? '全免畅享' : `${Math.round(p.credit_discount_rate * 10)} 折消耗` }}</b>
              </li>
              <li class="feature-bool">
                <span>场景包 ZIP 导入：</span>
                <span class="bool-mark" :class="p.allow_zip_import ? 'yes' : 'no'">
                  <AppIcon :name="p.allow_zip_import ? 'check' : 'x'" :size="12" />
                </span>
              </li>
              <li class="feature-bool">
                <span>场景包 ZIP 导出分发：</span>
                <span class="bool-mark" :class="p.allow_zip_export ? 'yes' : 'no'">
                  <AppIcon :name="p.allow_zip_export ? 'check' : 'x'" :size="12" />
                </span>
              </li>
              <li>
                私有知识库文档：<b>{{ p.max_knowledge_docs === 0 ? '不支持' : `上限 ${p.max_knowledge_docs} 份` }}</b>
              </li>
            </ul>

            <button
              v-if="p.tier !== 'free'"
              class="btn-primary full-w"
              type="button"
              @click="openCheckout('plan_upgrade', p)"
            >
              {{
                currentTier === p.tier && saasState.plan_expires_at
                  ? `续费（${formatExpireShort(saasState.plan_expires_at)} 到期）`
                  : currentTier === p.tier
                    ? '续费当前方案'
                    : `升级 ${tierLabel(p.tier)}`
              }}
            </button>
            <button v-else class="btn-secondary full-w" type="button" disabled>基础体验版</button>
          </div>
        </div>

        <!-- 图1底部：回声积分加油包 -->
        <div class="tactile-card packs-section">
          <div class="packs-head">
            <h4>回声积分加油包</h4>
            <p>积分永久有效，可在每日免费额度池用满（100%）后自动抵扣对话与 AI 生成</p>
          </div>
          <div class="packs-grid">
            <div v-for="pack in creditPacks" :key="pack.code" class="pack-item">
              <div class="pack-copy">
                <strong><EchoCreditIcon :size="16" /> {{ pack.credits }} 点</strong>
                <small>{{ pack.name }}</small>
              </div>
              <button class="btn-secondary sm" type="button" @click="openCheckout('credit_pack', pack)">
                ¥{{ pack.price_yuan }} 购买
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- 兑换码激活确认层（已关闭直接模拟订阅） -->
    <div v-if="checkoutTarget" class="sub-scrim nested" @click.self="checkoutTarget = null">
      <div class="checkout-modal">
        <div class="modal-head">
          <h3>使用兑换码激活</h3>
          <button class="dialog-close static" type="button" @click="checkoutTarget = null">
            <AppIcon name="x" :size="15" />
          </button>
        </div>
        <p class="checkout-desc">
          当前已关闭直接模拟订阅与购买，请输入管理员发放的兑换码激活「{{ checkoutTitle }}」或领取对应回声积分。
        </p>
        <div class="checkout-summary">
          <div>
            <span>目标方案 / 礼包</span>
            <strong>{{ checkoutTitle }}</strong>
          </div>
          <div>
            <span>兑换码</span>
            <input
              v-model.trim="modalRedeemCode"
              type="text"
              class="modal-redeem-input"
              placeholder="输入兑换码（如 ECHO-XXXX）"
              @keyup.enter="confirmRedeemFromModal"
            />
          </div>
        </div>
        <div class="checkout-actions">
          <button class="btn-secondary" type="button" @click="checkoutTarget = null">取消</button>
          <button class="btn-primary" type="button" :disabled="!modalRedeemCode || paying" @click="confirmRedeemFromModal">
            {{ paying ? '兑换中...' : '立即兑换激活' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../AppIcon.vue'
import EchoCreditIcon from '../EchoCreditIcon.vue'
import { getSaasPlans, redeemSaasCode, refreshSaasState, saasState } from '../../api/saas'
import { session } from '../../auth/session'

const emit = defineEmits(['close', 'updated'])
const router = useRouter()

const plans = ref([])
const creditPacks = ref([])
const billingCycle = ref('monthly')
const redeemInput = ref('')
const redeeming = ref(false)
const paying = ref(false)
const checkoutTarget = ref(null)
const modalRedeemCode = ref('')
const bannerMsg = ref('')
const bannerErr = ref(false)

const currentTier = computed(() => saasState.plan_tier || 'free')

const checkoutTitle = computed(() => {
  if (!checkoutTarget.value) return ''
  if (checkoutTarget.value.type === 'plan_upgrade') {
    const cycleLabel = billingCycle.value === 'yearly' ? '年付' : '月付'
    return `${checkoutTarget.value.item.name}（${cycleLabel}）`
  }
  return `回声积分加油包 · ${checkoutTarget.value.item.credits} 点`
})

const checkoutPrice = computed(() => {
  if (!checkoutTarget.value) return 0
  if (checkoutTarget.value.type === 'plan_upgrade') {
    return billingCycle.value === 'yearly'
      ? checkoutTarget.value.item.yearly_price_yuan
      : checkoutTarget.value.item.monthly_price_yuan
  }
  return checkoutTarget.value.item.price_yuan
})

function tierLabel(tier) {
  return { free: 'FREE', pro: 'PRO', enterprise: 'ENTERPRISE' }[tier] || 'FREE'
}

function formatExpireShort(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function poolCapacityLabel(tier) {
  return { free: '1x 标准容量/日', pro: '10x 专业容量/日', enterprise: '无限制畅享' }[tier] || '标准容量'
}

function showTip(msg, isErr = false) {
  bannerMsg.value = msg
  bannerErr.value = isErr
}

async function loadData() {
  const { data } = await getSaasPlans()
  plans.value = data.plans || []
  creditPacks.value = data.credit_packs || []
  if (session.token) await refreshSaasState()
}

async function handleRedeem() {
  if (!redeemInput.value) return
  redeeming.value = true
  try {
    const { data } = await redeemSaasCode(redeemInput.value)
    redeemInput.value = ''
    await refreshSaasState()
    emit('updated')
    showTip(`兑换成功，获得 ${data.reward_credits || 0} 点${data.reward_tier ? ` 及 ${data.reward_days} 天 ${tierLabel(data.reward_tier)}` : ''}`)
  } catch (e) {
    showTip(e?.response?.data?.error?.message || '兑换码无效', true)
  } finally {
    redeeming.value = false
  }
}

function openCheckout(type, item) {
  if (!session.token) {
    emit('close')
    router.push({ name: 'login' })
    return
  }
  modalRedeemCode.value = ''
  checkoutTarget.value = { type, item }
}

async function confirmRedeemFromModal() {
  if (!modalRedeemCode.value) return
  paying.value = true
  try {
    const { data } = await redeemSaasCode(modalRedeemCode.value)
    modalRedeemCode.value = ''
    checkoutTarget.value = null
    await refreshSaasState()
    emit('updated')
    showTip(data?.message || '兑换成功，已更新会员或积分')
  } catch (e) {
    showTip(e?.response?.data?.error?.message || e?.response?.data?.detail || '兑换码无效或已核销', true)
  } finally {
    paying.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.sub-scrim {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: grid;
  place-items: center;
  padding: 20px;
  background: var(--scrim-bg, rgba(34, 37, 59, 0.28));
  -webkit-backdrop-filter: var(--scrim-blur, blur(2px));
  backdrop-filter: var(--scrim-blur, blur(2px));
}
.sub-scrim.nested {
  z-index: 70;
}
.sub-modal {
  position: relative;
  width: min(980px, 95vw);
  max-height: 90vh;
  overflow-y: auto;
  border: 1.5px solid #ebe7f5;
  border-bottom: 5px solid #e3dcf2;
  border-radius: 22px;
  background: #faf9fd;
  padding: 22px 26px 24px;
  box-shadow: 0 24px 60px rgba(45, 36, 78, 0.16);
}
.dialog-close {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  border: 1px solid #e6e1f2;
  background: #ffffff;
  color: #625e76;
  display: grid;
  place-items: center;
  cursor: pointer;
  flex-shrink: 0;
}
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.billing-toggle {
  display: inline-flex;
  background: #f1edf9;
  padding: 4px;
  border-radius: 12px;
}
.bill-btn {
  border: none;
  background: transparent;
  padding: 7px 16px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 700;
  color: #625e76;
  cursor: pointer;
}
.bill-btn.active {
  background: #ffffff;
  color: #6046b4;
  box-shadow: 0 2px 6px rgba(96, 70, 180, 0.12);
}
.save-tag {
  background: #eaf7f0;
  color: #2a8c5f;
  padding: 1px 6px;
  border-radius: 6px;
  font-size: 11px;
  margin-left: 4px;
}
.top-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.sub-status-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 11px;
  border-radius: 999px;
  font-size: 12px;
  background: #f4f0ff;
  color: #6046b4;
}
.sub-status-chip.tier-pro {
  background: #eee9ff;
  color: #6046b4;
  border: 1px solid #d5c9f7;
}
.sub-status-chip.tier-enterprise {
  background: #2f2a45;
  color: #ffd670;
}
.balance-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: #ffffff;
  border: 1px solid #e6e1f2;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12.5px;
  color: #5a5572;
}
.balance-chip b {
  color: #b45309;
  font-variant-numeric: tabular-nums;
}
.redeem-inline {
  display: flex;
  background: #ffffff;
  border: 1px solid #e6e1f2;
  border-radius: 10px;
  overflow: hidden;
}
.redeem-inline input {
  border: none;
  padding: 6px 10px;
  font-size: 12px;
  width: 150px;
  outline: none;
  color: #35304e;
}
.redeem-inline button {
  border: none;
  border-left: 1px solid #efecf7;
  background: #f4f0ff;
  color: #6046b4;
  font-size: 12px;
  font-weight: 700;
  padding: 0 12px;
  cursor: pointer;
}
.banner-tip {
  margin: 0 0 14px;
  padding: 9px 12px;
  border-radius: 10px;
  background: #eaf7f0;
  color: #2a8c5f;
  font-size: 12.5px;
  font-weight: 600;
}
.banner-tip.err {
  background: #fdece8;
  color: #b84a39;
}
.tactile-card {
  border: 1.5px solid #ebe7f5;
  border-bottom: 4px solid #e3dcf2;
  border-radius: 18px;
  background: #ffffff;
  padding: 20px;
}
.plans-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
@media (max-width: 860px) {
  .plans-grid {
    grid-template-columns: 1fr;
  }
}
.plan-card {
  display: flex;
  flex-direction: column;
}
.plan-card.featured {
  border-color: #b7a6ea;
  background: linear-gradient(180deg, #faf8ff 0%, #ffffff 45%);
}
.plan-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.tier-pill {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.4px;
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
.current-tag {
  font-size: 11px;
  font-weight: 700;
  color: #2a8c5f;
  background: #eaf7f0;
  padding: 2px 8px;
  border-radius: 999px;
}
.plan-card h3 {
  margin: 0 0 6px;
  font-size: 18px;
  color: #35304e;
}
.plan-desc {
  margin: 0 0 12px;
  font-size: 12px;
  color: #837f96;
  min-height: 34px;
}
.plan-price {
  margin-bottom: 14px;
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.plan-price strong {
  font-size: 28px;
  color: #35304e;
}
.plan-price span {
  font-size: 13px;
  color: #837f96;
}
.price-strike {
  margin-left: 6px;
  font-size: 13.5px;
  color: #dc4c41;
  text-decoration: line-through;
  text-decoration-color: #dc4c41;
  text-decoration-thickness: 1.5px;
}
.plan-features {
  list-style: none;
  padding: 0;
  margin: 0 0 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
  color: #5a5572;
  flex: 1;
}
.feature-bool {
  display: flex;
  align-items: center;
  gap: 6px;
}
.bool-mark {
  display: inline-grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border-radius: 999px;
}
.bool-mark.yes {
  background: #eaf7f0;
  color: #2a8c5f;
}
.bool-mark.no {
  background: #fdece8;
  color: #b84a39;
}
.packs-section {
  margin-top: 16px;
  padding: 16px 20px;
}
.packs-head {
  margin-bottom: 12px;
}
.packs-head h4 {
  margin: 0 0 3px;
  font-size: 15px;
  color: #35304e;
}
.packs-head p {
  margin: 0;
  font-size: 12px;
  color: #837f96;
}
.packs-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
@media (max-width: 760px) {
  .packs-grid {
    grid-template-columns: 1fr;
  }
}
.pack-item {
  border: 1px solid #efecf7;
  border-radius: 12px;
  background: #faf9fd;
  padding: 12px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.pack-copy strong {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #35304e;
  font-size: 15px;
}
.pack-copy small {
  display: block;
  margin-top: 2px;
  font-size: 12px;
  color: #837f96;
}
.btn-primary {
  border: 1.5px solid #8067d1;
  border-bottom: 3px solid #6951b8;
  border-radius: 10px;
  background: #8b73dd;
  color: #ffffff;
  font-weight: 700;
  padding: 9px 16px;
  cursor: pointer;
}
.btn-secondary {
  border: 1.5px solid #e6e1f2;
  border-bottom: 3px solid #ddd6ec;
  border-radius: 10px;
  background: #ffffff;
  color: #5a5572;
  font-weight: 600;
  padding: 9px 16px;
  cursor: pointer;
}
.btn-secondary.sm {
  padding: 6px 12px;
  font-size: 12.5px;
}
.full-w {
  width: 100%;
}
.checkout-modal {
  width: 420px;
  max-width: 92vw;
  border: 1.5px solid #ebe7f5;
  border-bottom: 5px solid #e3dcf2;
  border-radius: 20px;
  background: #ffffff;
  padding: 20px;
}
.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.modal-head h3 {
  margin: 0;
  font-size: 16px;
  color: #35304e;
}
.checkout-desc {
  font-size: 12.5px;
  color: #625e76;
  margin: 0 0 14px;
}
.checkout-summary {
  background: #faf9fd;
  border: 1px solid #efecf7;
  border-radius: 12px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}
.checkout-summary > div {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}
.price-highlight {
  font-size: 17px;
  color: #6046b4;
}
.checkout-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.modal-redeem-input {
  width: 220px;
  height: 34px;
  padding: 0 10px;
  border: 1.5px solid #e2dcf2;
  border-radius: 9px;
  background: #fff;
  color: #2d294b;
  font-size: 13px;
  outline: none;
}
.modal-redeem-input:focus {
  border-color: #8b73dd;
}
</style>

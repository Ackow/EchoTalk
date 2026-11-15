<template>
  <section v-if="paymentPromptVisible" class="ending-card is-checkout" aria-label="订单结账">
    <div class="ending-head">
      <span class="ending-badge"><AppIcon name="coffee" :size="13" />柜台结账</span>
      <b v-if="quotedAmount" class="ending-amount">${{ quotedAmount }}</b>
    </div>
    <p class="ending-title">确认订单并完成付款，即可结束本次点单练习</p>
    <ul v-if="orderDisplayItems.length" class="ending-items">
      <li v-for="(item, idx) in orderDisplayItems" :key="idx">{{ item }}</li>
    </ul>
    <div class="pay-methods" role="radiogroup" aria-label="选择支付方式">
      <button
        v-for="m in PAYMENT_METHODS"
        :key="m.id"
        type="button"
        class="pay-method-chip"
        :class="{ active: paymentMethod === m.id }"
        :disabled="paying"
        @click="paymentMethod = m.id"
      ><AppIcon :name="m.icon" :size="14" /><span>{{ m.label }}</span></button>
    </div>
    <div class="ending-actions">
      <button class="confirm-button" type="button" :disabled="paying" @click="confirmPayment">
        <span v-if="paying" class="ui-spinner send-spinner" aria-hidden="true" />
        <AppIcon v-else name="check" :size="14" />
        <span>{{ paying ? '支付中…' : `确认付款${quotedAmount ? ' $' + quotedAmount : ''}` }}</span>
      </button>
    </div>
  </section>

  <section v-else-if="rebookPromptVisible" class="ending-card is-checkout" aria-label="改签确认">
    <div class="ending-head">
      <span class="ending-badge"><AppIcon name="plane" :size="13" />改签行程确认</span>
    </div>
    <p class="ending-title">选择要确认的改签方案，即可生成电子改签单并结束练习</p>
    <div class="pay-methods" role="radiogroup" aria-label="选择改签方案">
      <button
        v-for="opt in REBOOK_OPTIONS"
        :key="opt.id"
        type="button"
        class="pay-method-chip"
        :class="{ active: rebookOption === opt.id }"
        :disabled="paying"
        @click="rebookOption = opt.id"
      ><AppIcon name="plane" :size="13" /><span>{{ opt.label }}</span></button>
    </div>
    <div class="ending-actions">
      <button class="confirm-button" type="button" :disabled="paying" @click="confirmRebooking">
        <span v-if="paying" class="ui-spinner send-spinner" aria-hidden="true" />
        <AppIcon v-else name="check" :size="14" />
        <span>{{ paying ? '确认中…' : '确认改签方案' }}</span>
      </button>
    </div>
  </section>

  <section v-else-if="meetingPromptVisible" class="ending-card is-checkout" aria-label="会议行动项确认">
    <div class="ending-head">
      <span class="ending-badge"><AppIcon name="file-text" :size="13" />会议收尾 · 行动项</span>
    </div>
    <p class="ending-title">确认下一步行动计划并结束本次对齐会议</p>
    <div class="pay-methods" role="group" aria-label="快速填入下一步行动">
      <button
        v-for="preset in MEETING_NEXT_PRESETS"
        :key="preset"
        type="button"
        class="pay-method-chip"
        :class="{ active: nextStepInput === preset }"
        :disabled="paying"
        @click="nextStepInput = preset"
      >{{ preset }}</button>
    </div>
    <input v-model="nextStepInput" class="ending-input" type="text" placeholder="或输入自定义下一步行动（如：Send revised timeline by Friday）" :disabled="paying" />
    <div class="ending-actions">
      <button class="confirm-button" type="button" :disabled="paying" @click="confirmMeetingEnd">
        <span v-if="paying" class="ui-spinner send-spinner" aria-hidden="true" />
        <AppIcon v-else name="check" :size="14" />
        <span>{{ paying ? '提交中…' : '确认纪要并结束' }}</span>
      </button>
    </div>
  </section>

  <section v-else-if="wrapupPromptVisible" class="ending-card is-checkout" aria-label="结束本次练习">
    <div class="ending-head">
      <span class="ending-badge"><AppIcon :name="endingType === 'interview_result' ? 'briefcase' : 'sparkles'" :size="13" />{{ endingType === 'interview_result' ? '面试收尾' : '练习收尾' }}</span>
    </div>
    <p class="ending-title">{{ endingType === 'interview_result' ? '已进入面试最后阶段，可继续提问或直接结束本轮面试' : '当前已接近练习尾声，可继续交流或点击完成本次练习' }}</p>
    <div v-if="endingType === 'interview_result'" class="pay-methods" role="radiogroup" aria-label="自评表现">
      <button
        v-for="r in INTERVIEW_RATINGS"
        :key="r"
        type="button"
        class="pay-method-chip"
        :class="{ active: interviewRating === r }"
        :disabled="paying"
        @click="interviewRating = r"
      >{{ r }}</button>
    </div>
    <div class="ending-actions">
      <button class="confirm-button" type="button" :disabled="paying" @click="confirmGenericFinish">
        <span v-if="paying" class="ui-spinner send-spinner" aria-hidden="true" />
        <AppIcon v-else name="check" :size="14" />
        <span>{{ paying ? '结算中…' : (endingType === 'interview_result' ? '结束本轮面试' : '完成当前练习') }}</span>
      </button>
    </div>
  </section>

  <section v-else-if="finished" class="ending-card is-done" :class="`kind-${endingType}`" aria-label="场景结束">
    <div class="ending-head">
      <span class="ending-badge"><AppIcon :name="endingMeta.icon" :size="13" />{{ endingMeta.badge }}</span>
      <b v-if="endingType === 'payment' && (scenarioState?.paid_amount || quotedAmount)" class="ending-amount">
        已付 ${{ scenarioState?.paid_amount || quotedAmount }}
      </b>
    </div>
    <p class="ending-title">{{ endingMeta.title }}</p>
    <p class="ending-sub">{{ finishText }}</p>
    <ul v-if="endingType === 'payment' && orderDisplayItems.length" class="ending-items">
      <li v-for="(item, idx) in orderDisplayItems" :key="idx">{{ item }}</li>
    </ul>
    <div v-else-if="endingType === 'boarding_pass' && scenarioState?.selected_option" class="ending-note">
      <b>已选改签方案：</b>{{ scenarioState.selected_option }}
    </div>
    <div v-else-if="endingType === 'meeting_minutes' && scenarioState?.next_step" class="ending-note">
      <b>下一步行动：</b>{{ scenarioState.next_step }}
    </div>
    <div v-else-if="endingType === 'interview_result' && scenarioState?.self_rating" class="ending-note">
      <b>本轮自评：</b>{{ scenarioState.self_rating }}
    </div>
    <div class="ending-stats">
      <span>目标完成 {{ completedGoals }} / {{ goalsCount }}</span>
      <span>·</span>
      <span>共 {{ turnCount }} 轮对话</span>
      <template v-if="endingType === 'payment' && scenarioState?.payment_method">
        <span>·</span>
        <span>{{ paymentMethodLabel(scenarioState.payment_method) }}</span>
      </template>
    </div>
    <div class="ending-actions">
      <button class="ghost-button" type="button" :disabled="reportLoading" @click="emit('open-report')">
        <span v-if="reportLoading" class="ui-spinner" aria-hidden="true" />
        <AppIcon v-else name="file-text" :size="14" />
        <span>{{ reportLoading ? '生成报告中…' : '查看练习报告' }}</span>
      </button>
      <button class="ghost-button" type="button" :disabled="starting" @click="emit('back-to-select')">返回列表</button>
      <button class="confirm-button" type="button" :disabled="starting" @click="emit('restart')">
        <span v-if="starting" class="ui-spinner send-spinner" aria-hidden="true" />
        <AppIcon v-else name="rotate" :size="14" />
        <span>{{ starting ? '准备中…' : '再来一次' }}</span>
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import AppIcon from '../AppIcon.vue'

const PAYMENT_METHODS = [
  { id: 'card', icon: 'credit-card', label: '刷卡 Card' },
  { id: 'apple_pay', icon: 'smartphone', label: 'Apple Pay' },
  { id: 'cash', icon: 'banknote', label: '现金 Cash' },
]
const REBOOK_OPTIONS = [
  { id: 'earliest', label: '最早航班 Earliest Flight' },
  { id: 'next_day', label: '次日航班 Next-Day Flight' },
  { id: 'refund', label: '全额退票 Full Refund' },
]
const MEETING_NEXT_PRESETS = [
  'Confirm launch timeline & owners',
  'Follow up on QA blockers',
  'Sync updated scope by Friday',
]
const INTERVIEW_RATINGS = ['表现自信', '稳步推进', '仍需打磨']

const props = defineProps({
  finished: { type: Boolean, default: false },
  paying: { type: Boolean, default: false },
  starting: { type: Boolean, default: false },
  reportLoading: { type: Boolean, default: false },
  finishText: { type: String, default: '' },
  completedGoals: { type: Number, default: 0 },
  goalsCount: { type: Number, default: 0 },
  turnCount: { type: Number, default: 0 },
  stage: { type: String, default: '' },
  stages: { type: Array, default: () => [] },
  sceneId: { type: String, default: '' },
  sceneMode: { type: String, default: '' },
  scenarioState: { type: Object, default: () => ({}) },
  messages: { type: Array, default: () => [] },
})

const emit = defineEmits(['action', 'open-report', 'back-to-select', 'restart'])

const paymentMethod = ref('card')
const rebookOption = ref('earliest')
const nextStepInput = ref(MEETING_NEXT_PRESETS[0])
const interviewRating = ref(INTERVIEW_RATINGS[0])

const paymentMethodLabel = (id) => ({ card: '刷卡支付', apple_pay: 'Apple Pay', cash: '现金支付' }[id] || id)

const orderDisplayItems = computed(() => {
  const raw = props.scenarioState?.order
  if (!Array.isArray(raw)) return []
  return raw.map((item) => (typeof item === 'string' ? item : item?.name || item?.item || JSON.stringify(item)))
})

const quotedAmount = computed(() => {
  const sc = props.scenarioState || {}
  for (const key of ['paid_amount', 'total_amount', 'total_price', 'total', 'amount']) {
    if (sc[key] !== undefined && sc[key] !== null && sc[key] !== '') {
      const m = String(sc[key]).match(/\d+(?:\.\d{1,2})?/)
      if (m) return Number(m[0]).toFixed(2)
    }
  }
  const agentMsgs = [...props.messages].reverse().filter((m) => m.role === 'agent')
  for (const msg of agentMsgs) {
    const beforeTotal = msg.text.match(/\$\s*(\d+(?:\.\d{1,2})?)\s*(?:total|in total|altogether|all together)\b/i)
    if (beforeTotal) return Number(beforeTotal[1]).toFixed(2)
    const afterTotal = msg.text.match(/(?:total|comes to|that'll be|that will be|all together|altogether)[^$\n]{0,24}\$\s*(\d+(?:\.\d{1,2})?)/i)
    if (afterTotal) return Number(afterTotal[1]).toFixed(2)
    const allDollars = [...msg.text.matchAll(/\$\s*(\d+(?:\.\d{1,2})?)/g)]
    if (allDollars.length) return Number(allDollars[allDollars.length - 1][1]).toFixed(2)
  }
  return ''
})

const endingType = computed(() => {
  const sc = props.scenarioState || {}
  const id = props.sceneId || ''
  const mode = props.sceneMode || ''
  if ('paid' in sc || id === 'cafe_ordering') return 'payment'
  if ('rebooked' in sc || id === 'airport_rebooking') return 'boarding_pass'
  if ('next_step' in sc || id === 'launch_alignment') return 'meeting_minutes'
  if (mode === 'interview' || id === 'tech_interview') return 'interview_result'
  return 'summary'
})

const endingMeta = computed(() => ({
  payment: { icon: 'coffee', badge: '电子小票 · 已结账', title: '点单与付款已完成，祝你享用！' },
  boarding_pass: { icon: 'plane', badge: '改签确认单', title: '新行程已确认，祝你旅途顺利！' },
  meeting_minutes: { icon: 'file-text', badge: '会议纪要', title: '关键事项与下一步行动已对齐！' },
  interview_result: { icon: 'briefcase', badge: '面试结束', title: '本轮模拟面试已完成！' },
  summary: { icon: 'sparkles', badge: '练习完成', title: '本场口语练习已顺利完成！' },
}[endingType.value]))

const paymentPromptVisible = computed(() => {
  if (props.finished) return false
  const sc = props.scenarioState || {}
  if (!('paid' in sc) || sc.paid) return false
  return props.stage === 'checkout' || Boolean(sc.confirmed) || (Boolean(quotedAmount.value) && props.turnCount >= 2)
})

const rebookPromptVisible = computed(() => {
  if (props.finished) return false
  const sc = props.scenarioState || {}
  if (!('rebooked' in sc) || sc.rebooked) return false
  return props.stage === 'confirm' || (Boolean(sc.issue_explained) && Boolean(sc.options_compared)) || props.turnCount >= 4
})

const meetingPromptVisible = computed(() => {
  if (props.finished) return false
  const sc = props.scenarioState || {}
  if (!('next_step' in sc) || sc.next_step) return false
  return (Boolean(sc.reported) && Boolean(sc.clarified)) || props.turnCount >= 4
})

const isLastStage = computed(() => {
  const stages = props.stages || []
  return stages.length > 0 && props.stage === stages[stages.length - 1].id
})

const wrapupPromptVisible = computed(() => {
  if (props.finished || paymentPromptVisible.value || rebookPromptVisible.value || meetingPromptVisible.value) return false
  if (endingType.value === 'payment' || endingType.value === 'boarding_pass' || endingType.value === 'meeting_minutes') return false
  return isLastStage.value || props.turnCount >= 5
})

const confirmPayment = () => emit('action', 'pay', { method: paymentMethod.value, amount: quotedAmount.value || undefined })
const confirmRebooking = () => emit('action', 'finish', {
  state_updates: {
    issue_explained: true,
    options_compared: true,
    rebooked: true,
    selected_option: REBOOK_OPTIONS.find((o) => o.id === rebookOption.value)?.label || rebookOption.value,
  },
})
const confirmMeetingEnd = () => emit('action', 'finish', {
  state_updates: {
    reported: true,
    clarified: true,
    next_step: nextStepInput.value.trim() || MEETING_NEXT_PRESETS[0],
  },
})
const confirmGenericFinish = () => emit('action', 'finish', {
  state_updates: endingType.value === 'interview_result' ? { self_rating: interviewRating.value } : {},
})
</script>

<style scoped>
.ending-card { margin: 8px 0 6px; padding: 14px 16px; border: 1.5px solid #dfd8f6; border-radius: 14px; background: linear-gradient(180deg, #fcfbff 0%, #f6f3fe 100%); display: flex; flex-direction: column; gap: 10px; }
.ending-card.is-done { border-color: #cde6d6; background: linear-gradient(180deg, #fafdfb 0%, #f1f9f4 100%); }
.ending-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.ending-badge { display: inline-flex; align-items: center; gap: 5px; padding: 3px 10px; border-radius: 999px; background: #ece6fc; color: #5b43b0; font-size: 12px; font-weight: 750; }
.ending-card.is-done .ending-badge { background: #dff2e6; color: #2d6f49; }
.ending-amount { font-size: 18px; font-weight: 800; color: #2d294b; font-variant-numeric: tabular-nums; }
.ending-title { margin: 0; font-size: 14px; font-weight: 700; color: #2d294b; }
.ending-sub { margin: -4px 0 0; font-size: 12.5px; color: #6b6485; }
.ending-items { margin: 0; padding: 8px 12px 8px 26px; border-radius: 10px; background: rgba(255, 255, 255, 0.8); border: 1px solid #ece7f8; font-size: 13px; color: #393457; display: flex; flex-direction: column; gap: 4px; }
.ending-note { padding: 8px 11px; border-radius: 9px; background: rgba(255, 255, 255, 0.85); border: 1px solid #d7ebde; font-size: 12.5px; color: #2d294b; }
.ending-input { width: 100%; box-sizing: border-box; padding: 8px 11px; border: 1.5px solid #e1dbf4; border-radius: 9px; background: #fff; font: inherit; font-size: 13px; color: #2d294b; outline: none; }
.ending-input:focus { border-color: #7c62d2; }
.pay-methods { display: flex; flex-wrap: wrap; gap: 8px; }
.pay-method-chip { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border: 1.5px solid #e1dbf4; border-radius: 999px; background: #fff; color: #595275; font-size: 12.5px; font-weight: 650; cursor: pointer; transition: all .15s; }
.pay-method-chip:hover:not(:disabled) { border-color: #9e87e8; color: #4c359d; }
.pay-method-chip.active { border-color: #7c62d2; background: #efeafc; color: #4c359d; }
.ending-stats { display: flex; flex-wrap: wrap; align-items: center; gap: 7px; font-size: 12px; color: #6b6485; }
.ending-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 2px; }
.ghost-button { display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; gap: 7px; min-height: 38px; padding: 0 13px; border: 1.5px solid #e7e1f5; border-bottom: 3px solid #dcd3f0; border-radius: 12px; background: white; color: #5b5572; font-size: 13px; font-weight: 650; transition: border-color .15s, background .15s, color .15s; }
.ghost-button:hover:not(:disabled) { border-color: #c9bdf0; background: #f3effd; color: #5b43b0; }
.confirm-button { display: inline-flex; align-items: center; gap: 6px; min-height: 38px; padding: 0 16px; border: 1.5px solid #7960cc; border-bottom: 4px solid #6349b4; border-radius: 12px; background: #8b73dd; color: #fff; font-size: 13.5px; font-weight: 700; transition: background .15s, transform .12s; }
.confirm-button:hover:not(:disabled) { background: #7d64d1; transform: translateY(-1px); }
.confirm-button:disabled, .ghost-button:disabled { opacity: .6; cursor: not-allowed; }
.ui-spinner { width: 13px; height: 13px; border-radius: 50%; flex: 0 0 auto; border: 2px solid rgba(105, 78, 192, 0.22); border-top-color: #694ec0; animation: spin .72s linear infinite; }
.send-spinner { width: 14px; height: 14px; border-color: rgba(255, 255, 255, 0.34); border-top-color: #fff; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>

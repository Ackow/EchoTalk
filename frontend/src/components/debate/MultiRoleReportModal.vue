<template>
  <div v-if="open" class="modal-backdrop" @click.self="emit('close')">
    <div class="verdict-modal">
      <div class="verdict-head">
        <span class="xp-badge">+{{ verdictResult?.xp_awarded ?? 40 }} XP</span>
        <h3>{{ isPanelMode ? '多角色综合评估报告' : '评委终场裁决报告' }}</h3>
        <p>{{ topicTitle }}</p>
      </div>
      <div class="verdict-scores">
        <div class="v-score">
          <strong>{{ verdictResult?.avg_score ?? Math.round((scores.logic + scores.rebuttal + scores.fluency + scores.presence) / 4) }}</strong>
          <span>综合表现分</span>
        </div>
        <div class="v-summary">
          <strong>{{ isPanelMode ? '委员会评语' : '裁决评语' }}</strong>
          <p>{{ verdictResult?.summary || '表达清晰切题、回应结构稳定；建议后续多补充具体数据或真实案例进一步提升说服力。' }}</p>
        </div>
      </div>
      <div class="setup-actions">
        <button type="button" class="btn-cancel" @click="emit('close')">{{ isPanelMode ? '继续对话' : '继续辩论' }}</button>
        <button type="button" class="btn-start" @click="emit('finish')">返回场景大厅</button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  open: { type: Boolean, default: false },
  isPanelMode: { type: Boolean, default: false },
  topicTitle: { type: String, default: '' },
  verdictResult: { type: Object, default: null },
  scores: {
    type: Object,
    default: () => ({ logic: 0, rebuttal: 0, fluency: 0, presence: 0 }),
  },
})

const emit = defineEmits(['close', 'finish'])
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: grid;
  place-items: center;
  padding: 20px;
  background: var(--scrim-bg, rgba(34, 37, 59, .28));
  -webkit-backdrop-filter: var(--scrim-blur, blur(2px));
  backdrop-filter: var(--scrim-blur, blur(2px));
}
.verdict-modal {
  width: min(520px, 100%);
  padding: 22px 24px;
  border: 1px solid var(--line, #ece8f6);
  border-radius: 16px;
  background: var(--surface, #ffffff);
  box-shadow: 0 20px 56px rgba(34, 37, 59, .18);
}
.xp-badge {
  display: inline-block;
  padding: 2px 9px;
  border-radius: 999px;
  background: #e8f6ef;
  color: #257a50;
  font-size: 11.5px;
  font-weight: 700;
}
.verdict-head h3 { margin: 8px 0 4px; font-size: 16.5px; font-weight: 600; color: var(--ink, #231f3a); }
.verdict-head p { margin: 0; font-size: 12.5px; color: var(--muted, #76718c); }
.verdict-scores {
  display: grid;
  grid-template-columns: 106px minmax(0, 1fr);
  gap: 14px;
  margin-top: 16px;
  padding: 14px;
  border-radius: 12px;
  background: #f7f8fc;
}
.v-score {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  border: 1px solid var(--line, #ece8f6); border-radius: 10px; background: var(--surface, #fff); padding: 10px;
}
.v-score strong { font-size: 26px; color: var(--brand, #7c5fd6); }
.v-score span { font-size: 11px; color: var(--muted, #76718c); }
.v-summary strong { font-size: 13px; color: var(--ink, #231f3a); }
.v-summary p { margin: 5px 0 0; font-size: 12.5px; color: var(--ink-soft, #4b4663); line-height: 1.55; }
.setup-actions { margin-top: 18px; display: flex; justify-content: flex-end; gap: 10px; }
.btn-cancel {
  height: 35px; padding: 0 15px; border: 1.5px solid #e6e1f2; border-bottom: 3px solid #ddd6ec;
  border-radius: 10px; background: #ffffff; color: #5a5572; font-size: 13px; font-weight: 600;
}
.btn-start {
  height: 35px; padding: 0 17px; border: 1.5px solid #8067d1; border-bottom: 3px solid #6951b8;
  border-radius: 10px; background: #8b73dd; color: #ffffff; font-size: 13px; font-weight: 700;
}
</style>

<template>
  <div v-if="topic" class="modal-backdrop" @click.self="emit('close')">
    <div class="setup-modal">
      <div class="setup-head">
        <div class="topic-badges">
          <span class="cat-badge">{{ topic.categoryLabel }}</span>
          <span class="submode-badge" :class="topic.sceneType === 'panel' ? 'panel' : 'debate'">
            {{ topic.sceneType === 'panel' ? '多人对话 / 群面' : '正反辩论' }}
          </span>
        </div>
        <h3>{{ topic.titleZh }}</h3>
        <p>{{ topic.motionEn }}</p>
      </div>

      <div v-if="topic.sceneType !== 'panel'" class="setup-section">
        <label>选择你的辩论立场</label>
        <div class="side-picker">
          <button
            type="button"
            class="side-option pro"
            :class="{ selected: userSide === 'pro' }"
            @click="emit('update:userSide', 'pro')"
          >
            <strong>正方（支持）</strong>
            <span>{{ topic.proSummary }}</span>
          </button>
          <button
            type="button"
            class="side-option con"
            :class="{ selected: userSide === 'con' }"
            @click="emit('update:userSide', 'con')"
          >
            <strong>反方（反对）</strong>
            <span>{{ topic.conSummary }}</span>
          </button>
        </div>
      </div>

      <div v-else class="setup-section">
        <label>本场身份与同台 AI 阵容</label>
        <div class="panel-lineup-card">
          <div class="panel-user-row">
            <span>你的身份</span>
            <strong>{{ topic.userRoleLabel || '候选人 / 主讲人' }}</strong>
          </div>
          <div class="panel-roles-chips">
            <span v-for="r in (topic.roles || [])" :key="r.id || r.name" class="panel-role-pill">
              <b>{{ r.name }}</b> · {{ r.title || '评审成员' }}
            </span>
          </div>
        </div>
      </div>

      <div class="setup-section">
        <label>{{ topic.sceneType === 'panel' ? 'AI 追问压力等级' : 'AI 对手交锋风格' }}</label>
        <div class="style-pills">
          <button
            v-for="opt in opponentStyles"
            :key="opt.id"
            type="button"
            class="style-pill"
            :class="{ selected: opponentStyle === opt.id }"
            @click="emit('update:opponentStyle', opt.id)"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>

      <p v-if="latestSession" class="resume-hint">
        你有未结束的对话（第 {{ latestSession.turn_count }}/{{ activeMaxTurns || 6 }} 轮），要继续上次对话还是新开一场？
      </p>

      <p v-if="setupError" class="setup-error">{{ setupError }}</p>

      <div class="setup-actions">
        <button type="button" class="btn-cancel" :disabled="resuming" @click="emit('close')">取消</button>
        <template v-if="latestSession">
          <button type="button" class="btn-cancel" :disabled="resuming" @click="emit('start')">新开一场</button>
          <button type="button" class="btn-start" :disabled="resuming" @click="emit('resume', latestSession.id)">
            {{ resuming ? '恢复中…' : '继续对话' }}
          </button>
        </template>
        <button v-else type="button" class="btn-start" @click="emit('start')">
          {{ topic.sceneType === 'panel' ? '进入多人对话场' : '进入辩论场' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  topic: { type: Object, default: null },
  userSide: { type: String, default: 'pro' },
  opponentStyle: { type: String, default: 'balanced' },
  opponentStyles: { type: Array, default: () => [] },
  latestSession: { type: Object, default: null },
  activeMaxTurns: { type: Number, default: 6 },
  resuming: { type: Boolean, default: false },
  setupError: { type: String, default: '' },
})

const emit = defineEmits(['close', 'update:userSide', 'update:opponentStyle', 'start', 'resume'])
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
.setup-modal {
  width: min(520px, 100%);
  padding: 22px 24px;
  border: 1px solid var(--line, #ece8f6);
  border-radius: 16px;
  background: var(--surface, #ffffff);
  box-shadow: 0 20px 56px rgba(34, 37, 59, .18);
}
.topic-badges { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.cat-badge {
  padding: 2px 9px;
  border-radius: 999px;
  background: #f1ecff;
  color: #674bc4;
  font-size: 11px;
  font-weight: 700;
}
.submode-badge {
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
}
.submode-badge.debate { background: #f3efff; color: #6c51c9; }
.submode-badge.panel { background: #ebf4ff; color: #2d66c3; }
.setup-head h3 { margin: 8px 0 4px; font-size: 16.5px; font-weight: 600; color: var(--ink, #231f3a); }
.setup-head p { margin: 0; font-size: 12.5px; color: var(--muted, #76718c); }
.setup-section { margin-top: 16px; }
.setup-section label { display: block; margin-bottom: 8px; font-size: 12.5px; font-weight: 600; color: var(--ink, #231f3a); }
.side-picker { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.side-option {
  display: flex; flex-direction: column; gap: 4px; padding: 11px 12px;
  border: 1px solid var(--line, #e6e1f2); border-radius: 12px; background: var(--surface, #fff); text-align: left;
}
.side-option strong { font-size: 13px; color: var(--ink, #231f3a); }
.side-option span { font-size: 11.5px; color: var(--muted, #76718c); line-height: 1.45; }
.side-option.pro.selected { border-color: #35a876; background: #f3fbf7; }
.side-option.con.selected { border-color: #d96b57; background: #fff7f5; }
.panel-lineup-card {
  display: grid; gap: 10px; padding: 12px 13px;
  border: 1px solid #e6e1f3; border-radius: 12px; background: #faf9fe;
}
.panel-user-row { display: flex; align-items: center; justify-content: space-between; font-size: 12.5px; color: var(--muted, #76718c); }
.panel-user-row strong { color: #3d2c6d; }
.panel-roles-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.panel-role-pill {
  padding: 4px 10px; border-radius: 999px; background: #ffffff;
  border: 1px solid #e4def4; font-size: 11.5px; color: #544e6b;
}
.style-pills { display: flex; gap: 8px; }
.style-pill {
  padding: 6px 13px; border: 1px solid var(--line, #e6e1f2); border-radius: 999px;
  background: var(--surface, #fff); font-size: 12.5px; color: var(--ink-soft, #4b4663);
}
.style-pill.selected { border-color: var(--brand, #8b73dd); background: var(--brand-soft, #f3efff); color: var(--brand, #7c5fd6); font-weight: 600; }
.resume-hint { margin: 14px 0 0; font-size: 13px; color: #5b517c; line-height: 1.5; }
.setup-error { margin: 12px 0 0; font-size: 12.5px; color: #c44536; }
.setup-actions { margin-top: 18px; display: flex; justify-content: flex-end; gap: 10px; }
.btn-cancel {
  height: 35px; padding: 0 15px; border: 1.5px solid #e6e1f2; border-bottom: 3px solid #ddd6ec;
  border-radius: 10px; background: #ffffff; color: #5a5572; font-size: 13px; font-weight: 600;
}
.btn-start {
  height: 35px; padding: 0 17px; border: 1.5px solid #8067d1; border-bottom: 3px solid #6951b8;
  border-radius: 10px; background: #8b73dd; color: #ffffff; font-size: 13px; font-weight: 700;
}
.btn-cancel:disabled, .btn-start:disabled { opacity: 0.6; cursor: not-allowed; }
</style>

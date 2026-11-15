<template>
  <aside class="arena-side">
    <div class="side-card roundtable-stage">
      <div class="side-card-head">
        <h4>{{ isPanelMode ? '同台对话席位' : '圆桌辩论席' }}</h4>
        <label class="auto-play-check">
          <input :checked="autoPlayAudio" type="checkbox" @change="emit('update:autoPlayAudio', $event.target.checked)" />
          <span>自动播报</span>
        </label>
      </div>
      <div v-if="activeSpeakerRole" class="speaker-stage-focus" :class="[activeSpeakerRole.roleType, { speaking: roleStageState(activeSpeakerRole.id) === 'speaking' }]">
        <div class="speaker-stage-portrait">
          <CharacterPortrait
            :character="roleAvatarObj(activeSpeakerRole).id"
            :appearance="roleAvatarObj(activeSpeakerRole).appearance || null"
            :state="roleStageState(activeSpeakerRole.id)"
            :lip-sync="true"
            :theme="roleAvatarObj(activeSpeakerRole).theme || 'amber'"
            :name="activeSpeakerRole.name"
          />
        </div>
        <div class="speaker-stage-meta">
          <div class="speaker-stage-title">
            <strong>{{ activeSpeakerRole.name }}</strong>
            <span class="speaker-state-pill" :class="roleStageState(activeSpeakerRole.id)">
              <i class="live-dot-inline" aria-hidden="true"></i>
              {{ roleStageState(activeSpeakerRole.id) === 'speaking' ? '正在发言' : roleStageState(activeSpeakerRole.id) === 'listening' ? '正在倾听' : '当前席位' }}
            </span>
          </div>
          <span class="speaker-stage-role">{{ formatRoleLabel(activeSpeakerRole.roleType, activeSpeakerRole.title, { isPanelMode, userSide }) }}</span>
        </div>
      </div>
      <div class="speaker-roster" role="tablist" aria-label="圆桌角色切换">
        <button
          v-for="role in aiRoles"
          :key="role.id"
          type="button"
          class="roster-pill"
          :class="[role.roleType, { active: activeSpeakerRole?.id === role.id }]"
          @click="emit('update:speakingRole', role.id)"
        >
          <span v-if="activeSpeakerRole?.id === role.id" class="roster-dot" aria-hidden="true"></span>
          <span>{{ role.name }}</span>
          <small>{{ formatRoleLabel(role.roleType, role.title, { isPanelMode, userSide }) }}</small>
        </button>
      </div>
    </div>

    <div class="side-card">
      <div class="side-card-head">
        <h4>{{ isPanelMode ? '实时评估雷达' : '战况雷达' }}</h4>
        <span class="momentum-tag" :class="winRate > 50 ? 'up' : winRate < 50 ? 'down' : 'even'">
          <template v-if="isPanelMode">
            {{ turnCount === 0 && winRate === 50 ? '待评估' : `认可度 ${winRate}%` }}
          </template>
          <template v-else>
            {{ winRate === 50 ? '均势' : winRate > 50 ? '占优' : '落后' }} {{ winRate }}%
          </template>
        </span>
      </div>

      <div class="radar-wrap">
        <svg viewBox="0 0 248 184" class="radar-svg" aria-label="四维能力雷达图">
          <polygon
            v-for="(ring, rIdx) in [0.35, 0.65, 1]"
            :key="rIdx"
            :points="radarRingPoints(ring)"
            class="radar-grid"
          />
          <line x1="124" y1="38" x2="124" y2="146" class="radar-axis" />
          <line x1="70" y1="92" x2="178" y2="92" class="radar-axis" />
          <polygon :points="radarDataPoints" class="radar-area" />
          <circle
            v-for="(pt, pIdx) in radarDataCoords"
            :key="pIdx"
            :cx="pt.x"
            :cy="pt.y"
            r="3.5"
            class="radar-dot"
          />
          <text x="124" y="24" text-anchor="middle" class="radar-label">逻辑 {{ scores.logic || '--' }}</text>
          <text x="186" y="96" text-anchor="start" class="radar-label">{{ isPanelMode ? '应变' : '反驳' }} {{ scores.rebuttal || '--' }}</text>
          <text x="124" y="168" text-anchor="middle" class="radar-label">气场 {{ scores.presence || '--' }}</text>
          <text x="62" y="96" text-anchor="end" class="radar-label">地道 {{ scores.fluency || '--' }}</text>
        </svg>
      </div>

      <div class="mini-kpi-row">
        <span class="kpi-chip">阶段目标：{{ activeStages[stageIndex]?.shortTag || '推进' }}</span>
        <span class="kpi-chip xp">已推进 {{ turnCount }}/{{ maxTurns }} 轮</span>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import CharacterPortrait from '../avatar/CharacterPortrait.vue'
import { formatRoleLabel, radarRingPoints } from '../../composables/useMultiRoleSession'

const props = defineProps({
  isPanelMode: { type: Boolean, default: false },
  autoPlayAudio: { type: Boolean, default: true },
  activeSpeakerRole: { type: Object, default: null },
  aiRoles: { type: Array, default: () => [] },
  speakingRole: { type: String, default: '' },
  playingMsgId: { type: String, default: '' },
  voiceBusy: { type: Boolean, default: false },
  roleAvatarObj: { type: Function, required: true },
  userSide: { type: String, default: 'pro' },
  winRate: { type: Number, default: 50 },
  turnCount: { type: Number, default: 0 },
  maxTurns: { type: Number, default: 6 },
  scores: { type: Object, default: () => ({ logic: 0, rebuttal: 0, fluency: 0, presence: 0 }) },
  activeStages: { type: Array, default: () => [] },
  stageIndex: { type: Number, default: 0 },
})

const emit = defineEmits(['update:autoPlayAudio', 'update:speakingRole'])

function roleStageState(roleId) {
  if (props.playingMsgId && props.speakingRole === roleId) return 'speaking'
  if (props.voiceBusy && props.speakingRole === roleId) return 'listening'
  return 'idle'
}

const radarDataCoords = computed(() => {
  const cx = 124
  const cy = 92
  const r = 54
  return [
    { x: cx, y: Number((cy - (r * props.scores.logic) / 100).toFixed(1)) },
    { x: Number((cx + (r * props.scores.rebuttal) / 100).toFixed(1)), y: cy },
    { x: cx, y: Number((cy + (r * props.scores.presence) / 100).toFixed(1)) },
    { x: Number((cx - (r * props.scores.fluency) / 100).toFixed(1)), y: cy },
  ]
})

const radarDataPoints = computed(() => radarDataCoords.value.map((p) => `${p.x},${p.y}`).join(' '))
</script>

<style scoped>
.arena-side { display: flex; flex-direction: column; gap: 12px; }
.side-card { padding: 14px 15px; border: 1.5px solid #ebe7f5; border-radius: 15px; background: var(--surface, #fff); }
.roundtable-stage { display: flex; flex-direction: column; gap: 8px; }
.side-card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.side-card-head h4 { margin: 0; font-size: 13.5px; font-weight: 700; color: var(--ink, #231f3a); }
.auto-play-check { display: inline-flex; align-items: center; gap: 4px; font-size: 11.5px; color: #6d6882; cursor: pointer; }
.auto-play-check input { accent-color: #8b73dd; }
.speaker-stage-focus {
  display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 12px 12px 10px;
  border: 1.5px solid #ebe7f5; border-bottom: 3px solid #dfd8f0; border-radius: 14px; background: #faf9fe;
  transition: border-color 0.18s, background 0.18s;
}
.speaker-stage-focus.speaking { border-color: #8b73dd; border-bottom-color: #6951b8; background: #f5f1ff; }
.speaker-stage-focus.opponent.speaking { border-color: #df9d8f; border-bottom-color: #c87462; background: #fdf6f4; }
.speaker-stage-focus.interviewer.speaking { border-color: #93b7f2; border-bottom-color: #4f79cc; background: #f3f7ff; }
.speaker-stage-focus.judge.speaking { border-color: #82cca4; border-bottom-color: #4aa777; background: #f3fbf7; }
.speaker-stage-portrait {
  width: 156px; height: 168px; border-radius: 14px; background: #ffffff; border: 1px solid #ece7f6;
  overflow: hidden; display: flex; align-items: flex-end; justify-content: center;
}
.speaker-stage-portrait :deep(svg) { width: 100%; height: 100%; display: block; }
.speaker-stage-meta { display: flex; flex-direction: column; align-items: center; gap: 3px; text-align: center; }
.speaker-stage-title { display: inline-flex; align-items: center; gap: 7px; }
.speaker-stage-title strong { font-size: 14.5px; font-weight: 700; color: var(--ink, #231f3a); }
.speaker-stage-role { font-size: 12px; color: var(--muted, #76718c); }
.speaker-state-pill {
  display: inline-flex; align-items: center; gap: 5px; height: 20px; padding: 0 8px;
  border-radius: 999px; background: #f1eefb; color: #6650b8; font-size: 11px; font-weight: 650;
}
.speaker-state-pill.speaking { background: #e9e2ff; color: #543ba8; }
.speaker-state-pill.listening { background: #eaf4ff; color: #365fb3; }
.live-dot-inline { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.speaker-roster { display: flex; flex-wrap: wrap; gap: 6px; }
.roster-pill {
  flex: 1 1 auto; min-width: 0; display: inline-flex; align-items: center; justify-content: center; gap: 5px;
  padding: 6px 8px; border: 1.5px solid #ebe7f5; border-bottom: 2.5px solid #dfd8f0; border-radius: 10px;
  background: #fff; color: var(--ink-soft, #4b4663); font-size: 12px; font-weight: 600;
  transition: border-color 0.15s, background 0.15s, color 0.15s;
}
.roster-pill small { font-size: 11px; font-weight: 500; color: var(--muted, #76718c); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.roster-pill.active { border-color: #8b73dd; background: #f5f1ff; color: #5b43b0; }
.roster-dot { width: 6px; height: 6px; flex: 0 0 6px; border-radius: 50%; background: #7c5fd6; }
.momentum-tag { padding: 2px 8px; border-radius: 999px; font-size: 11.5px; font-weight: 700; }
.momentum-tag.up { background: #eee9ff; color: #6046b4; }
.momentum-tag.down { background: #fdeee9; color: #b84a39; }
.momentum-tag.even { background: #f3f2f8; color: #666380; }
.radar-wrap { display: grid; place-items: center; padding: 4px 0; }
.radar-svg { width: 100%; max-width: 248px; height: auto; }
.radar-grid { fill: none; stroke: #e8e3f5; stroke-width: 1.1; }
.radar-axis { stroke: #e2dcf2; stroke-width: 1; stroke-dasharray: 2 2; }
.radar-area { fill: rgba(139, 115, 221, 0.24); stroke: #7a5fd6; stroke-width: 2; }
.radar-dot { fill: #6951b8; stroke: #ffffff; stroke-width: 1.5; }
.radar-label { fill: #5c5772; font-size: 10.5px; font-weight: 700; }
.mini-kpi-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 6px; }
.kpi-chip { padding: 4px 9px; border-radius: 8px; background: #f6f4fc; color: #5b5670; font-size: 11.5px; font-weight: 600; }
.kpi-chip.xp { background: #e8f6ef; color: #257a50; font-weight: 700; }
</style>

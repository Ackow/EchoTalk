<template>
  <div class="studio-hub">
    <!-- 工具栏：复用 AppTabs 频道切换 + 右侧精简指标 -->
    <div class="studio-toolbar">
      <AppTabs
        :model-value="selectedChannel"
        :options="channels.map((c) => ({ value: c.id, label: c.label, count: channelCount(c.id) }))"
        aria-label="听力频道筛选"
        @update:model-value="$emit('update:selectedChannel', $event)"
      />
      <div class="toolbar-stats">
        <span class="stat-chip accent">原速独立 <strong>{{ stats.independentRate === null ? '—' : `${stats.independentRate}%` }}</strong></span>
        <span class="stat-chip green">辅助理解 <strong>{{ stats.assistedRate === null ? '—' : `${stats.assistedRate}%` }}</strong></span>
        <span class="stat-chip">今日 <strong>{{ todayXp }} / {{ dailyGoalXp }} XP</strong></span>
      </div>
    </div>

    <!-- 四六级专属控制面板（仅在“四六级专项”频道展开） -->
    <section v-if="selectedChannel === 'cet'" class="cet-panel">
      <div class="cet-panel-head">
        <AppTabs
          :model-value="cetLevel"
          :options="[
            { value: 'cet4', label: 'CET-4 四级' },
            { value: 'cet6', label: 'CET-6 六级' }
          ]"
          aria-label="四六级级别切换"
          @update:model-value="$emit('update:cetLevel', $event)"
        />

        <div class="cet-mode-switch">
          <button
            type="button"
            class="cat-chip"
            :class="{ active: cetMode === 'practice' }"
            @click="$emit('update:cetMode', 'practice')"
          >
            专项训练（允许慢速与提示）
          </button>
          <button
            type="button"
            class="cat-chip"
            :class="{ active: cetMode === 'mock' }"
            @click="$emit('update:cetMode', 'mock')"
          >
            全真模拟（{{ currentCet.durationMin }} 分钟 · 禁提示）
          </button>
        </div>
      </div>

      <div class="cet-mode-desc" :class="{ mock: cetMode === 'mock' }">
        <span class="mode-pill">{{ cetMode === 'mock' ? '全真考场模式' : '专项精听模式' }}</span>
        <span v-if="cetMode === 'mock'">
          已开启 {{ currentCet.durationMin }} 分钟模拟倒计时，进入套题后禁用 0.75× 慢速与三段式提示，模拟真实考场节奏。
        </span>
        <span v-else>
          支持 0.75× 慢速播放、关键词提示、英文原文与中文释义，适合逐题精听与错题拆解。
        </span>
      </div>

      <div v-if="availableCetYears.length" class="cet-year-row" role="tablist" aria-label="按年份筛选">
        <span class="year-label">年份筛选</span>
        <button
          type="button"
          class="cat-chip"
          :class="{ active: selectedCetYear === 'all' }"
          @click="$emit('update:selectedCetYear', 'all')"
        >
          全部年份
        </button>
        <button
          v-for="yr in availableCetYears"
          :key="yr"
          type="button"
          class="cat-chip"
          :class="{ active: selectedCetYear === yr }"
          @click="$emit('update:selectedCetYear', yr)"
        >
          {{ yr }} 年
        </button>
      </div>
    </section>

    <!-- 英语电台横幅（仅在“英语电台”频道展开） -->
    <section v-if="selectedChannel === 'radio'" class="radio-banner">
      <span class="radio-icon"><AppIcon name="headphones" :size="20" /></span>
      <div>
        <strong>EchoFM 每日磨耳朵频道</strong>
        <p>支持 0.75× 慢速精听与语块跟读，适合碎片时间盲听输入。</p>
      </div>
    </section>

    <!-- 多邻国风格紧凑多列关卡网格（一行 3–4 张） -->
    <div class="units-duo-grid">
      <article
        v-for="unit in filteredUnits"
        :key="unit.id"
        class="duo-card"
        :class="[
          `ch-${unit.channel || 'daily'}`,
          { active: unit.progress > 0 && unit.progress < 100, done: unit.progress === 100 }
        ]"
        @click="$emit('start-unit', unit)"
      >
        <div class="duo-banner">
          <div class="duo-banner-wave" aria-hidden="true">
            <span v-for="bar in 9" :key="bar" class="wave-bar" :style="{ '--i': bar }"></span>
          </div>
          <span class="duo-ch-pill">
            <AppIcon :name="channelIcon(unit.channel)" :size="13" />
            <span>{{ shortChannelLabel(unit) }}</span>
          </span>
          <span v-if="unit.progress === 100" class="duo-status-pill done">
            <AppIcon name="check" :size="12" />
            <span>已完成</span>
          </span>
          <span v-else class="duo-xp-pill">+{{ unit.xp }} XP</span>
        </div>

        <div class="duo-body">
          <h3 class="duo-title">{{ splitUnitTitle(unit.title).main }}</h3>
          <p class="duo-sub">{{ unit.subtitle }}</p>

          <div class="duo-tags">
            <span class="duo-tag level" :class="unitLevelMeta(unit).tone">{{ unitLevelMeta(unit).label }}</span>
            <span v-if="splitUnitTitle(unit.title).speaker" class="duo-tag speaker">
              {{ splitUnitTitle(unit.title).speaker }}
            </span>
            <span class="duo-tag">{{ unit.exercises.length }} 题精听</span>
          </div>

          <div class="duo-card-foot">
            <div class="duo-progress-wrap">
              <div class="duo-track">
                <i :style="{ width: `${unit.progress}%` }"></i>
              </div>
              <span class="duo-meta">
                {{ unit.duration }}
                <template v-if="unit.progress > 0 && unit.progress < 100"> · 已练 {{ unit.progress }}%</template>
              </span>
            </div>
            <button
              type="button"
              class="duo-btn"
              :class="{
                primary: unit.progress > 0 && unit.progress < 100,
                subtle: unit.progress === 100
              }"
              @click.stop="$emit('start-unit', unit)"
            >
              {{ unit.progress === 100 ? '重练' : unit.progress > 0 ? '继续' : '开始' }}
            </button>
          </div>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from '../AppIcon.vue'
import AppTabs from '../AppTabs.vue'

const props = defineProps({
  units: { type: Array, default: () => [] },
  stats: {
    type: Object,
    default: () => ({ independentRate: null, assistedRate: null, weakTags: [] })
  },
  todayXp: { type: Number, default: 0 },
  dailyGoalXp: { type: Number, default: 100 },
  selectedChannel: { type: String, default: 'all' },
  cetLevel: { type: String, default: 'cet4' },
  cetMode: { type: String, default: 'practice' },
  selectedCetYear: { type: String, default: 'all' }
})

defineEmits([
  'update:selectedChannel',
  'update:cetLevel',
  'update:cetMode',
  'update:selectedCetYear',
  'start-unit'
])

const channels = [
  { id: 'all', label: '全部频道' },
  { id: 'daily', label: '日常对话' },
  { id: 'cet', label: '四六级真题' },
  { id: 'radio', label: '新闻电台' },
  { id: 'talks', label: '真实访谈' }
]

const CET_CONFIG = {
  cet4: {
    label: 'CET-4 英语四级',
    durationMin: 25,
    sections: [
      { id: 'news', name: 'Section A · 新闻听力', count: '3 篇 · 7 题' },
      { id: 'conversation', name: 'Section B · 长对话', count: '2 篇 · 8 题' },
      { id: 'passage', name: 'Section C · 听力篇章', count: '3 篇 · 10 题' }
    ]
  },
  cet6: {
    label: 'CET-6 英语六级',
    durationMin: 30,
    sections: [
      { id: 'conversation', name: 'Section A · 长对话', count: '2 篇 · 8 题' },
      { id: 'passage', name: 'Section B · 听力篇章', count: '2 篇 · 7 题' },
      { id: 'lecture', name: 'Section C · 讲座/讲话', count: '3 篇 · 10 题' }
    ]
  }
}

const currentCet = computed(() => CET_CONFIG[props.cetLevel])

function channelCount(id) {
  if (id === 'all') return props.units.length
  return props.units.filter((u) => u.channel === id).length
}

function channelIcon(channel) {
  const map = {
    daily: 'messages',
    cet: 'graduation-cap',
    radio: 'headphones',
    talks: 'mic'
  }
  return map[channel] || 'headphones'
}

function shortChannelLabel(unit) {
  const ch = unit?.channel
  if (ch === 'talks') return 'TED 演讲与访谈'
  if (ch === 'radio') return 'BBC 新闻电台'
  if (ch === 'cet') return unit?.cetLevel === 'cet6' ? 'CET-6 真题' : 'CET-4 真题'
  return unit?.channelLabel || '日常对话'
}

function splitUnitTitle(title) {
  const raw = String(title || '').trim()
  const idx = raw.lastIndexOf(' | ')
  if (idx > 0 && idx < raw.length - 3) {
    return {
      main: raw.slice(0, idx).trim(),
      speaker: raw.slice(idx + 3).trim()
    }
  }
  return { main: raw, speaker: '' }
}

function unitLevelMeta(unit) {
  if (unit?.channel === 'daily' || Number(unit?.xp || 0) <= 25) {
    return { label: '日常实用', tone: 'easy' }
  }
  if (unit?.channel === 'cet') {
    return { label: unit?.cetLevel === 'cet6' ? '六级备考' : '四级备考', tone: 'exam' }
  }
  if (unit?.channel === 'radio') {
    return { label: '新闻原速', tone: 'hard' }
  }
  return { label: '地道访谈', tone: 'medium' }
}

function extractUnitYear(unit) {
  const hay = `${unit?.id || ''} ${unit?.channelLabel || ''} ${unit?.title || ''}`
  const m = hay.match(/(20\d{2})/)
  return m ? m[1] : ''
}

const availableCetYears = computed(() => {
  const years = new Set()
  for (const u of props.units) {
    if (u.channel === 'cet' && u.cetLevel === props.cetLevel) {
      const y = extractUnitYear(u)
      if (y) years.add(y)
    }
  }
  return Array.from(years).sort((a, b) => Number(b) - Number(a))
})

const filteredUnits = computed(() => {
  if (props.selectedChannel === 'all') return props.units
  if (props.selectedChannel === 'cet') {
    return props.units.filter((u) => {
      if (u.channel !== 'cet' || u.cetLevel !== props.cetLevel) return false
      if (props.selectedCetYear === 'all') return true
      return extractUnitYear(u) === props.selectedCetYear
    })
  }
  return props.units.filter((u) => u.channel === props.selectedChannel)
})
</script>

<style scoped>
.studio-hub {
  max-width: 1320px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.toolbar-stats {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.stat-chip {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  padding: 6px 12px;
  border: 1.5px solid #e6e1f4;
  border-radius: 12px;
  background: #ffffff;
  font-size: 12px;
  color: #7f7c90;
}

.stat-chip strong {
  font-size: 13px;
  font-weight: 800;
  color: #29283e;
  font-variant-numeric: tabular-nums;
}

.stat-chip.accent {
  border-color: #d8cef4;
  background: #f6f3ff;
  color: #654ab8;
}

.stat-chip.accent strong {
  color: #654ab8;
}

.stat-chip.green {
  border-color: #d3ebdc;
  background: #eff9f2;
  color: #2f855a;
}

.stat-chip.green strong {
  color: #2f855a;
}

.studio-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.cet-panel {
  padding: 18px 20px;
  border: 2px solid #eae7f2;
  border-bottom: 5px solid #e3dfed;
  border-radius: 20px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.cet-panel-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.cet-mode-switch {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.cat-chip {
  padding: 7px 14px;
  border: 1.5px solid #e4def5;
  border-radius: 999px;
  background: #fbfaff;
  color: #6b6584;
  font-size: 12.5px;
  font-weight: 600;
  transition: all 0.15s;
}

.cat-chip:hover {
  border-color: #c8bbf0;
  color: #393451;
}

.cat-chip.active {
  border-color: #8067d1;
  background: #efeafc;
  color: #654ab8;
}

.cet-mode-desc {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border: 1.5px solid #e7e2f4;
  border-radius: 12px;
  background: #faf8ff;
  color: #5b5572;
  font-size: 13px;
  line-height: 1.5;
}

.cet-mode-desc.mock {
  border-color: #f0d7b5;
  background: #fff9f0;
  color: #7c511c;
}

.mode-pill {
  display: inline-flex;
  align-items: center;
  padding: 2px 9px;
  border-radius: 999px;
  background: #ece6fb;
  color: #5e47b0;
  font-size: 12px;
  font-weight: 700;
}

.cet-mode-desc.mock .mode-pill {
  background: #fde8cb;
  color: #a65c12;
}

.cet-year-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed #e6e1f2;
}

.year-label {
  font-size: 12.5px;
  font-weight: 700;
  color: #6e6785;
  margin-right: 4px;
}

.cet-sec-card {
  padding: 12px 14px;
  border: 1.5px solid #eae7f2;
  border-radius: 14px;
  background: #fbfaff;
}

.cet-sec-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 13.5px;
}

.cet-badge {
  font-size: 11.5px;
  font-weight: 700;
  color: #654ab8;
  background: #efeafc;
  padding: 2px 9px;
  border-radius: 999px;
}

.cet-sec-tip {
  margin: 6px 0 0;
  font-size: 12.5px;
  color: #7f7c90;
  line-height: 1.5;
}

.radio-banner {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
  border: 2px solid #e0d8f6;
  border-radius: 18px;
  background: #f8f5ff;
}

.radio-icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 13px;
  background: #e8e2fc;
  color: #654ab8;
}

.radio-banner strong {
  display: block;
  font-size: 14px;
  color: #2d294b;
}

.radio-banner p {
  margin: 3px 0 0;
  font-size: 12.5px;
  color: #706d85;
}

.units-duo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(238px, 1fr));
  gap: 14px;
}

.duo-card {
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
  border: 1.5px solid #ebe7f5;
  border-bottom: 4px solid #dfd8ef;
  border-radius: 18px;
  background: #ffffff;
  cursor: pointer;
  transition: transform 0.14s, border-color 0.14s, box-shadow 0.14s;
}

.duo-card:hover {
  transform: translateY(-2px);
  border-color: #c7bbf0;
  box-shadow: 0 10px 24px rgba(59, 49, 102, 0.07);
}

.duo-card.active {
  border-color: #b7a7eb;
  border-bottom-color: #9f8be3;
  background: #fcfbff;
}

.duo-card.done {
  border-color: #d6efe2;
  border-bottom-color: #bde4d0;
}

/* 顶部频道氛围条 + 声波装饰 */
.duo-banner {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid rgba(235, 231, 245, 0.8);
  background: linear-gradient(135deg, #f5f2ff 0%, #eef4ff 100%);
  overflow: hidden;
}

.duo-card.ch-daily .duo-banner {
  background: linear-gradient(135deg, #eef6ff 0%, #f4f2ff 100%);
}

.duo-card.ch-cet .duo-banner {
  background: linear-gradient(135deg, #fff6ea 0%, #fdf2f8 100%);
}

.duo-card.ch-radio .duo-banner {
  background: linear-gradient(135deg, #ecfbf3 0%, #eef7ff 100%);
}

.duo-card.ch-talks .duo-banner {
  background: linear-gradient(135deg, #f4efff 0%, #fdf2fa 100%);
}

.duo-card.done .duo-banner {
  background: linear-gradient(135deg, #eafaf1 0%, #f1fcf7 100%);
}

.duo-banner-wave {
  position: absolute;
  right: 54px;
  bottom: -2px;
  display: flex;
  align-items: flex-end;
  gap: 3px;
  height: 28px;
  opacity: 0.22;
  pointer-events: none;
}

.wave-bar {
  width: 3px;
  border-radius: 999px;
  background: #7d67d1;
  height: calc(7px + ((var(--i) * 7) % 18) * 1px);
}

.duo-card.ch-radio .wave-bar { background: #2ea36f; }
.duo-card.ch-cet .wave-bar { background: #d4883b; }
.duo-card.ch-daily .wave-bar { background: #4f7de8; }

.duo-ch-pill {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 9px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(113, 90, 193, 0.14);
  font-size: 11px;
  font-weight: 700;
  color: #5b46ab;
  white-space: nowrap;
}

.duo-card.ch-daily .duo-ch-pill { color: #3d63bd; border-color: rgba(79, 125, 232, 0.18); }
.duo-card.ch-cet .duo-ch-pill { color: #b56a1e; border-color: rgba(212, 136, 59, 0.2); }
.duo-card.ch-radio .duo-ch-pill { color: #24845a; border-color: rgba(46, 163, 111, 0.2); }

.duo-xp-pill,
.duo-status-pill {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}

.duo-xp-pill {
  background: rgba(255, 255, 255, 0.88);
  color: #2f9968;
  border: 1px solid rgba(53, 168, 118, 0.18);
}

.duo-status-pill.done {
  background: #35a876;
  color: #ffffff;
}

.duo-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 13px 16px 15px;
}

.duo-title {
  margin: 0 0 6px;
  font-size: 14.5px;
  font-weight: 700;
  color: #26253b;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.duo-sub {
  margin: 0;
  font-size: 12px;
  color: #7b7990;
  line-height: 1.5;
  flex: 1;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.duo-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 11px;
}

.duo-tag {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  padding: 2px 8px;
  border-radius: 7px;
  background: #f5f4fa;
  color: #6f6c84;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.duo-tag.speaker {
  max-width: 130px;
  background: #f4f1ff;
  color: #654ab8;
}

.duo-tag.level.easy { background: #eaf7f0; color: #2a8c5f; }
.duo-tag.level.medium { background: #eff2ff; color: #5258cc; }
.duo-tag.level.hard { background: #fff3ea; color: #c46a24; }
.duo-tag.level.exam { background: #fef5e7; color: #b5731a; }

.duo-card-foot {
  margin-top: 13px;
  padding-top: 10px;
  border-top: 1px dashed #eeebf7;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.duo-progress-wrap {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.duo-track {
  height: 5px;
  border-radius: 999px;
  background: #efeafc;
  overflow: hidden;
}

.duo-track i {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: #8b73dd;
}

.duo-card.done .duo-track i {
  background: #35a876;
}

.duo-meta {
  font-size: 11px;
  color: #8b879c;
  white-space: nowrap;
}

.duo-btn {
  height: 30px;
  padding: 0 13px;
  flex: 0 0 auto;
  border: 1.5px solid #d9d1f2;
  border-bottom: 3px solid #c5b9e9;
  border-radius: 10px;
  background: #f6f3ff;
  color: #6046b4;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
  transition: background 0.14s, color 0.14s, border-color 0.14s;
}

.duo-card:hover .duo-btn:not(.subtle),
.duo-btn.primary {
  border-color: #8067d1;
  border-bottom-color: #6951b8;
  background: #8b73dd;
  color: #ffffff;
}

.duo-btn.subtle {
  border-color: #d4e8dc;
  border-bottom-color: #bddcc9;
  background: #f3fbf6;
  color: #2c8a5e;
}
</style>

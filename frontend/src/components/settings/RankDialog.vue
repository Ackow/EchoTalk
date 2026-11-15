<template>
  <Teleport to="body">
    <!-- 段位与任务弹窗：沿用 SettingsDialog 左侧分类 + 右侧内容结构 -->
    <div class="rank-scrim" @click.self="emit('close')">
      <section class="rank-dialog" role="dialog" aria-modal="true" aria-labelledby="rank-title">
        <button class="dialog-close" type="button" aria-label="关闭" @click="emit('close')">
          <AppIcon name="x" :size="16" />
        </button>

        <aside class="set-nav">
          <h2 id="rank-title" class="set-nav-title"><AppIcon name="target" :size="15" />段位与任务</h2>
          <nav class="set-nav-list" aria-label="段位分类">
            <button
              v-for="item in SECTIONS"
              :key="item.key"
              class="set-nav-item"
              :class="{ active: active === item.key }"
              type="button"
              @click="active = item.key"
            >
              <AppIcon :name="item.icon" :size="15" />{{ item.label }}
            </button>
          </nav>
        </aside>

        <div class="dialog-body">
          <!-- 1. 我的段位 -->
          <section v-if="active === 'overview'" class="pane">
            <header class="pane-head">
              <h3>我的段位</h3>
              <p>经验值（XP）记录你在听力、口语、复习与面试中的累计投入。</p>
            </header>

            <div class="rank-hero-row">
              <RankBadge :level="currentRank.level" :sub-rank="currentRank.subRank" :size="58" />
              <div class="rank-hero-copy">
                <b>{{ currentRank.name }} · {{ currentRank.subRank }}</b>
                <small>
                  <template v-if="nextRank">距「{{ nextRank.name }}」还差 {{ currentRank.nextNeed }} XP</template>
                  <template v-else>已解锁最高声域传说段位</template>
                </small>
              </div>
              <span class="rank-state">{{ totalXp }} XP</span>
            </div>

            <div class="progress-block">
              <div class="prog-meta">
                <span>当前段位进度</span>
                <b>{{ currentRank.progressPct }}%</b>
              </div>
              <div class="prog-track">
                <div class="prog-fill" :style="{ width: `${currentRank.progressPct}%`, background: currentRank.color }"></div>
              </div>
            </div>

            <dl class="stat-grid">
              <div>
                <dt>今日经验</dt>
                <dd>{{ todayXp }} / {{ dailyGoalXp }} XP</dd>
              </div>
              <div>
                <dt>当前小阶</dt>
                <dd>{{ currentRank.name }} · {{ currentRank.subRank }}</dd>
              </div>
            </dl>

            <p class="about-note">
              段位反映你的<strong>练习投入度</strong>；真实的听力理解能力仍由工作室内的「原速独立正确率」单独评估，两者互不混淆。
            </p>
          </section>

          <!-- 2. 段位体系 -->
          <section v-else-if="active === 'tiers'" class="pane">
            <header class="pane-head">
              <h3>段位图鉴（Lv.1 – Lv.6）</h3>
              <p>每个大段位内设 I / II / III 三个小阶，按累计经验自动晋升。</p>
            </header>

            <div class="tiers-list">
              <div
                v-for="tier in tiers"
                :key="tier.level"
                class="tier-row"
                :class="{ current: tier.level === currentRank.level, locked: totalXp < tier.minXp }"
              >
                <RankBadge
                  :level="tier.level"
                  :sub-rank="tier.level < currentRank.level ? 'III' : tier.level === currentRank.level ? currentRank.subRank : ''"
                  :size="38"
                  :locked="totalXp < tier.minXp"
                />
                <div class="tier-copy">
                  <div class="tier-head">
                    <b>{{ tier.name }}</b>
                    <span>{{ tier.maxXp ? `${tier.minXp} – ${tier.maxXp} XP` : `${tier.minXp}+ XP` }}</span>
                  </div>
                  <small>{{ tier.desc }}</small>
                </div>
              </div>
            </div>
          </section>

          <!-- 3. 今日任务与规则 -->
          <section v-else class="pane">
            <header class="pane-head">
              <h3>今日任务与获取规则</h3>
              <p>完成每日微任务可更快累积 XP，点击未完成任务可直接前往训练。</p>
            </header>

            <div class="quests-list">
              <button
                v-for="q in dailyQuests"
                :key="q.id"
                type="button"
                class="pref-row quest-btn"
                :class="{ done: q.current >= q.target }"
                @click="goTask(q.route)"
              >
                <span class="quest-check">
                  <AppIcon v-if="q.current >= q.target" name="check" :size="12" />
                </span>
                <div class="pref-copy">
                  <b>{{ q.title }}</b>
                  <small>{{ q.current >= q.target ? '已完成' : `当前进度 ${q.current} / ${q.target}` }}</small>
                </div>
                <span class="quest-xp">+{{ q.xp }} XP</span>
              </button>
            </div>

            <div class="rules-list">
              <b>全局 XP 获取规则</b>
              <ul>
                <li>听力工作室：完成单元 +25 ~ 35 XP（原速独立作答额外激励）</li>
                <li>语音对话：每轮有效表达 +5 XP，达成场景目标 +20 XP</li>
                <li>复习计划：每复习 1 条 +3 XP，清空今日到期队列 +15 XP</li>
                <li>模拟面试 / 辩论：完成整场并生成复盘报告 +40 XP</li>
              </ul>
            </div>
          </section>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../AppIcon.vue'
import RankBadge from '../RankBadge.vue'
import { RANK_TIERS, currentRank, dailyGoalXp, dailyQuests, nextRank, syncGlobalXpProfile, todayXp, totalXp } from '../../app/xp'

const emit = defineEmits(['close'])
const router = useRouter()

const SECTIONS = [
  { key: 'overview', label: '我的段位', icon: 'user' },
  { key: 'quests', label: '今日任务', icon: 'calendar-check' },
  { key: 'tiers', label: '段位图鉴', icon: 'star' }
]
const active = ref('overview')
const tiers = RANK_TIERS

onMounted(() => { void syncGlobalXpProfile() })

function goTask(routeName) {
  emit('close')
  router.push({ name: routeName })
}
</script>

<style scoped>
/* 弹窗壳：与 SettingsDialog.vue 1:1 对齐 */
.rank-scrim {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: grid;
  place-items: center;
  padding: 24px;
  background: var(--scrim-bg, rgba(34, 37, 59, .28));
  -webkit-backdrop-filter: var(--scrim-blur, blur(2px));
  backdrop-filter: var(--scrim-blur, blur(2px));
  animation: scrim-in .18s ease-out;
}

.rank-dialog {
  position: relative;
  display: grid;
  width: min(680px, 100%);
  height: min(500px, calc(100vh - 48px));
  grid-template-columns: 184px minmax(0, 1fr);
  overflow: hidden;
  border: 1.5px solid #e9e4f4;
  border-radius: 22px;
  background: var(--surface);
  box-shadow: 0 22px 54px rgba(34, 37, 59, .16);
  animation: dialog-in .2s cubic-bezier(.22, .8, .32, 1);
}

.dialog-close {
  position: absolute;
  top: 14px;
  right: 14px;
  z-index: 2;
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: #8b87a0;
  transition: background .15s, color .15s;
}

.dialog-close:hover {
  background: #f4f1fb;
  color: #554888;
}

/* 左侧分类栏 */
.set-nav {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 16px 12px 12px;
  border-right: 1px solid #f1eef8;
  background: #faf8ff;
}

.set-nav-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 8px 10px;
  color: #393451;
  font-size: 16px;
  font-weight: 750;
}

.set-nav-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.set-nav-item {
  display: flex;
  height: 38px;
  align-items: center;
  gap: 9px;
  padding: 0 11px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: #625e76;
  font-size: 14.5px;
  text-align: left;
  transition: background .15s, color .15s;
}

.set-nav-item:hover {
  background: #f3effc;
  color: #5946a7;
}

.set-nav-item.active {
  background: #eee9ff;
  color: #6c52c4;
  font-weight: 700;
}

/* 右侧内容区 */
.dialog-body {
  min-height: 0;
  overflow-y: auto;
  padding: 22px 26px 24px;
}

.pane {
  display: flex;
  flex-direction: column;
}

.pane-head {
  margin-bottom: 18px;
  padding-right: 30px;
}

.pane-head h3 {
  margin: 0;
  color: #393451;
  font-size: 16px;
  font-weight: 750;
}

.pane-head p {
  margin: 5px 0 0;
  color: #8b87a0;
  font-size: 12.5px;
  line-height: 1.7;
}

/* 我的段位 */
.rank-hero-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding-bottom: 18px;
  border-bottom: 1px solid #f2eff8;
}

.rank-lv-box {
  display: grid;
  place-items: center;
  height: 46px;
  padding: 0 13px;
  border-radius: 14px;
  color: #ffffff;
  font-size: 15px;
  font-weight: 800;
}

.rank-hero-copy {
  min-width: 0;
  flex: 1;
}

.rank-hero-copy b {
  display: block;
  color: #332f4b;
  font-size: 15.5px;
  font-weight: 750;
}

.rank-hero-copy small {
  display: block;
  margin-top: 4px;
  color: #918da6;
  font-size: 12px;
}

.rank-state {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border: 1px solid #ddd3f3;
  border-radius: 999px;
  background: #faf8ff;
  color: #6c52c4;
  font-size: 12px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.progress-block {
  margin-top: 16px;
}

.prog-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12.5px;
  color: #6b6683;
  margin-bottom: 7px;
}

.prog-track {
  height: 8px;
  border-radius: 999px;
  background: #efeaf9;
  overflow: hidden;
}

.prog-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.25s ease;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px 28px;
  margin: 18px 0 0;
}

.stat-grid dt {
  color: #918da6;
  font-size: 11.5px;
}

.stat-grid dd {
  margin: 4px 0 0;
  color: #3a3552;
  font-size: 13.5px;
  font-weight: 600;
}

.about-note {
  margin: 20px 0 0;
  padding: 13px 15px;
  border: 1px solid #f0edf8;
  border-radius: 13px;
  background: #fbf9ff;
  color: #6f6a86;
  font-size: 12.5px;
  line-height: 1.75;
}

/* 段位图鉴 */
.tiers-list {
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.tier-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 14px;
  border: 1.5px solid #eeeaf7;
  border-radius: 14px;
  background: #fdfcff;
}

.tier-row.locked {
  opacity: 0.65;
}

.tier-row.current {
  border-color: #c2b3ec;
  background: #f7f4ff;
}

.tier-lv {
  flex: 0 0 auto;
  padding: 2px 8px;
  border-radius: 7px;
  color: #ffffff;
  font-size: 11px;
  font-weight: 700;
  margin-top: 2px;
}

.tier-copy {
  flex: 1;
  min-width: 0;
}

.tier-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.tier-head b {
  color: #3a3552;
  font-size: 13.5px;
  font-weight: 700;
}

.tier-head span {
  color: #8b87a0;
  font-size: 11.5px;
  font-variant-numeric: tabular-nums;
}

.tier-copy small {
  display: block;
  margin-top: 4px;
  color: #7e7a93;
  font-size: 12px;
  line-height: 1.55;
}

/* 今日任务（沿用 SettingsDialog .pref-row 立体行） */
.quests-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.pref-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 15px;
  border: 1.5px solid #eeeaf7;
  border-bottom: 4px solid #e9e3f4;
  border-radius: 15px;
  background: #fdfcff;
  text-align: left;
  transition: border-color .15s;
}

.pref-row:hover {
  border-color: #cfc4ee;
}

.pref-copy {
  flex: 1;
  min-width: 0;
}

.pref-copy b {
  display: block;
  color: #3a3552;
  font-size: 13.5px;
  font-weight: 700;
}

.pref-copy small {
  display: block;
  margin-top: 3px;
  color: #8b87a0;
  font-size: 12px;
}

.quest-check {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  flex: 0 0 20px;
  border-radius: 50%;
  border: 1.5px solid #d4cee6;
  color: #ffffff;
}

.pref-row.done .quest-check {
  border-color: #35a876;
  background: #35a876;
}

.pref-row.done .pref-copy b {
  color: #8b87a0;
  text-decoration: line-through;
}

.quest-xp {
  font-size: 12.5px;
  font-weight: 700;
  color: #35a876;
  white-space: nowrap;
}

.rules-list {
  margin-top: 18px;
}

.rules-list b {
  display: block;
  color: #4b4664;
  font-size: 12.5px;
  font-weight: 700;
}

.rules-list ul {
  margin: 8px 0 0;
  padding-left: 17px;
  color: #6f6a86;
  font-size: 12.5px;
  line-height: 1.85;
}

.rules-list li::marker {
  color: #b9aee0;
}

@keyframes scrim-in { from { opacity: 0; } to { opacity: 1; } }
@keyframes dialog-in { from { opacity: 0; transform: translateY(8px) scale(.99); } to { opacity: 1; transform: none; } }

@media (max-width: 760px) {
  .rank-scrim { padding: 16px; }
  .rank-dialog { grid-template-columns: 148px minmax(0, 1fr); }
  .dialog-body { padding: 16px 16px 20px; }
  .stat-grid { grid-template-columns: minmax(0, 1fr); }
}
</style>

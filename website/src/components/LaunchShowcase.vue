<template>
  <section class="voice-demo-section" aria-label="交互式 AI 语音与多角色试听">
    <div class="tactile-card demo-shell">
      <div class="demo-top">
        <div class="demo-title-wrap">
          <span class="sec-tag">互动试听 · 先听语音再展原文</span>
          <h2>亲耳听听 EchoTalk 2.0 的真实 AI 伙伴</h2>
          <p>切换 1v1 场景与多角色辩论席位，点击语音气泡即可试听真实 Neural 英语播报，并随时展开原文。</p>
        </div>

        <!-- Role Switcher Pills -->
        <div class="role-tabs" role="tablist" aria-label="切换试听角色">
          <button
            v-for="role in roles"
            :key="role.id"
            type="button"
            role="tab"
            :aria-selected="activeId === role.id"
            class="role-tab"
            :class="[role.tone, { active: activeId === role.id }]"
            @click="selectRole(role.id)"
          >
            <span class="role-dot" :class="role.tone"></span>
            <span class="role-tab-text">
              <strong>{{ role.name }}</strong>
              <small>{{ role.roleLabel }}</small>
            </span>
          </button>
        </div>
      </div>

      <!-- Interactive Voice Bubble Stage -->
      <div class="demo-stage" :class="currentRole.tone">
        <div class="speaker-badge">
          <div class="speaker-avatar" :class="[currentRole.tone, { talking: isPlaying }]">
            <span>{{ currentRole.initial }}</span>
            <i v-if="isPlaying" class="pulse-ring" aria-hidden="true"></i>
          </div>
          <div class="speaker-info">
            <div class="speaker-name-row">
              <strong>{{ currentRole.name }}</strong>
              <span class="voice-pill" :class="currentRole.tone">{{ currentRole.voiceTag }}</span>
            </div>
            <span class="speaker-scene">{{ currentRole.sceneLabel }}</span>
          </div>
          <span class="eval-chip" :class="currentRole.tone">{{ currentRole.metricBadge }}</span>
        </div>

        <!-- Step 1: Voice Playback Capsule + 原文/收起 Toggle -->
        <div class="bubble-row">
          <button
            type="button"
            class="voice-capsule"
            :class="[currentRole.tone, { playing: isPlaying }]"
            :aria-label="isPlaying ? '暂停播放英语语音' : '播放英语语音'"
            @click="togglePlay"
          >
            <span class="capsule-progress" :style="{ width: `${progressPct}%` }"></span>
            <span class="capsule-icon" aria-hidden="true">{{ isPlaying ? '❚❚' : '▶' }}</span>
            <span class="capsule-sec">{{ currentRole.durationLabel }}</span>
            <span class="capsule-bars" aria-hidden="true">
              <i
                v-for="(h, idx) in barHeights"
                :key="idx"
                :style="{ height: `${h}px`, animationDelay: `${idx * 75}ms` }"
              ></i>
            </span>
          </button>

          <button
            type="button"
            class="toggle-original-btn"
            :class="[currentRole.tone, { open: showTranscript }]"
            :aria-expanded="showTranscript"
            @click="showTranscript = !showTranscript"
          >
            {{ showTranscript ? '收起原文' : '展开原文' }}
          </button>
        </div>

        <!-- Step 2: Smooth Unfolding Transcript Card -->
        <Transition name="unfold">
          <div v-if="showTranscript" class="transcript-box" :class="currentRole.tone">
            <p class="transcript-en">{{ currentRole.textEn }}</p>
            <p class="transcript-zh">{{ currentRole.textZh }}</p>
          </div>
        </Transition>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'

const emit = defineEmits(['voice-start'])

const roles = [
  {
    id: 'leo',
    initial: 'L',
    name: 'Leo · Barista',
    roleLabel: '1v1 咖啡点单',
    voiceTag: 'Andrew · 美式英语',
    sceneLabel: '繁忙咖啡厅点餐 (Cafe Ordering) · SSE 并发切句 TTS',
    metricBadge: 'ISE 发音 92 · 138 WPM',
    durationLabel: '6"',
    audioSrc: '/audio/leo-cafe.mp3',
    tone: 'purple',
    textEn: "Sorry, we're out of croissants today! A large drip coffee is $3.50 — would you like a blueberry muffin instead?",
    textZh: '抱歉，今天可颂已经卖完了！一大杯美式滴滤咖啡 3.50 美元——要不要换一个蓝莓马芬？',
  },
  {
    id: 'marcus',
    initial: 'M',
    name: 'Marcus · 反方辩手',
    roleLabel: '1vN 多角色辩论',
    voiceTag: 'Ryan · 英式英语',
    sceneLabel: '圆桌辩论 · AI 是否会取代初级软件工程师？',
    metricBadge: '交叉质询 · 压迫感攻防',
    durationLabel: '7"',
    audioSrc: '/audio/marcus-debate.mp3',
    tone: 'coral',
    textEn: 'AI copilots already generate 60% of boilerplate code — junior roles must prove deeper architectural value.',
    textZh: 'AI 编程助手已经能生成 60% 的样板代码——初级工程师必须证明更深层的架构价值。',
  },
  {
    id: 'elena',
    initial: 'E',
    name: 'Elena · 资深评委',
    roleLabel: '圆桌裁决点评',
    voiceTag: 'Ava · 美式英语',
    sceneLabel: '实时胜率裁决 · 四维战况雷达动态评估',
    metricBadge: '胜率跃升 58% → 72%',
    durationLabel: '6"',
    audioSrc: '/audio/elena-ruling.mp3',
    tone: 'mint',
    textEn: 'Sharp counter-argument! Grounding your point in system ownership pushed Pro momentum to 72%.',
    textZh: '非常犀利的反驳！将论点立足于系统所有权，成功把正方优势推升至 72%。',
  },
]

const barHeights = [7, 14, 10, 17, 12, 8, 16, 11, 15, 9, 13, 8, 12, 7]

const activeId = ref('leo')
const isPlaying = ref(false)
const progressPct = ref(0)
const showTranscript = ref(false)

let audioEl = null
let autoExpandTimer = null

const currentRole = computed(() => roles.find((r) => r.id === activeId.value) || roles[0])

function stopAudio() {
  if (autoExpandTimer) {
    clearTimeout(autoExpandTimer)
    autoExpandTimer = null
  }
  if (audioEl) {
    audioEl.pause()
    audioEl.currentTime = 0
    audioEl = null
  }
  isPlaying.value = false
  progressPct.value = 0
}

function selectRole(id) {
  if (activeId.value === id) return
  stopAudio()
  activeId.value = id
  showTranscript.value = false
}

function togglePlay() {
  if (isPlaying.value) {
    stopAudio()
    return
  }

  emit('voice-start')
  stopAudio()

  const el = new Audio(currentRole.value.audioSrc)
  audioEl = el
  isPlaying.value = true
  progressPct.value = 6

  // Mimic promo video: show voice capsule playing first, then smoothly unfold transcript
  if (!showTranscript.value) {
    autoExpandTimer = setTimeout(() => {
      showTranscript.value = true
    }, 520)
  }

  el.addEventListener('timeupdate', () => {
    if (el.duration && Number.isFinite(el.duration)) {
      progressPct.value = Math.min(100, (el.currentTime / el.duration) * 100)
    }
  })
  el.addEventListener('ended', () => {
    isPlaying.value = false
    progressPct.value = 100
  })
  el.addEventListener('error', () => {
    isPlaying.value = false
  })

  el.play().catch(() => {
    isPlaying.value = false
  })
}

defineExpose({ stopAudio })

onBeforeUnmount(() => {
  stopAudio()
})
</script>

<style scoped>
.voice-demo-section {
  max-width: 1220px;
  margin: 44px auto 0;
  padding: 0 24px;
}
.demo-shell {
  padding: 26px 28px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  background: linear-gradient(180deg, #ffffff 0%, #fcfbff 100%);
}
.demo-top {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
}
.sec-tag {
  display: inline-block;
  padding: 3px 11px;
  border-radius: 999px;
  background: #eee9ff;
  color: var(--primary-ink);
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 8px;
}
.demo-title-wrap h2 {
  font-size: 24px;
  font-weight: 800;
  color: var(--text);
  margin-bottom: 4px;
}
.demo-title-wrap p {
  font-size: 13.5px;
  color: var(--text-muted);
}
.role-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.role-tab {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 13px;
  border-radius: 12px;
  border: 1.5px solid #ebe7f5;
  border-bottom: 3px solid #e0d9f0;
  background: #ffffff;
  cursor: pointer;
  text-align: left;
  transition: transform 0.14s ease, border-color 0.16s ease, background 0.16s ease;
}
.role-tab:hover { transform: translateY(-1px); }
.role-tab.active.purple { border-color: #8b73dd; border-bottom-color: #6951b8; background: #f5f1ff; }
.role-tab.active.coral { border-color: #df9d8f; border-bottom-color: #c87462; background: #fdf6f4; }
.role-tab.active.mint { border-color: #82cca4; border-bottom-color: #4aa777; background: #f3fbf7; }
.role-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.role-dot.purple { background: #8b73dd; }
.role-dot.coral { background: #c87462; }
.role-dot.mint { background: #2a8c5f; }
.role-tab-text strong { display: block; font-size: 12.5px; color: var(--text); line-height: 1.2; }
.role-tab-text small { display: block; font-size: 11px; color: var(--text-muted); }

.demo-stage {
  border-radius: 16px;
  border: 1.5px solid #ebe7f5;
  background: #faf9fd;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.demo-stage.coral { background: #fffaf9; border-color: #f2dcd6; }
.demo-stage.mint { background: #f6fcf9; border-color: #cfead9; }

.speaker-badge {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.speaker-avatar {
  position: relative;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-weight: 800;
  font-size: 16px;
  flex-shrink: 0;
}
.speaker-avatar.purple { background: #eee9ff; color: #6046b4; border: 1.5px solid #d7cbf5; }
.speaker-avatar.coral { background: #fdece8; color: #b84a39; border: 1.5px solid #efc6bc; }
.speaker-avatar.mint { background: #eaf7f0; color: #2a8c5f; border: 1.5px solid #b8e3cc; }
.pulse-ring {
  position: absolute;
  inset: -5px;
  border-radius: 50%;
  border: 2px solid currentColor;
  opacity: 0.45;
  animation: speakerPulse 1.2s ease-out infinite;
}
@keyframes speakerPulse {
  0% { transform: scale(0.95); opacity: 0.55; }
  100% { transform: scale(1.25); opacity: 0; }
}
.speaker-info { flex: 1; min-width: 200px; }
.speaker-name-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.speaker-name-row strong { font-size: 15px; color: var(--text); }
.voice-pill { padding: 2px 9px; border-radius: 999px; font-size: 11px; font-weight: 700; }
.voice-pill.purple { background: #eee9ff; color: #6046b4; }
.voice-pill.coral { background: #fdece8; color: #b84a39; }
.voice-pill.mint { background: #eaf7f0; color: #2a8c5f; }
.speaker-scene { font-size: 12px; color: var(--text-muted); }
.eval-chip {
  padding: 5px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}
.eval-chip.purple { background: #eaf7f0; color: #2a8c5f; }
.eval-chip.coral { background: #fff3ea; color: #c46a24; }
.eval-chip.mint { background: #eee9ff; color: #6046b4; }

.bubble-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.voice-capsule {
  position: relative;
  overflow: hidden;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  width: 268px;
  max-width: 100%;
  padding: 10px 16px;
  border-radius: 16px;
  border: 1.5px solid #8b73dd;
  border-bottom: 3.5px solid #6951b8;
  background: #ffffff;
  color: #6046b4;
  cursor: pointer;
  transition: transform 0.14s ease;
}
.voice-capsule:hover { transform: translateY(-1px); }
.voice-capsule.coral { border-color: #df9d8f; border-bottom-color: #c87462; color: #b84a39; }
.voice-capsule.mint { border-color: #82cca4; border-bottom-color: #4aa777; color: #2a8c5f; }
.capsule-progress {
  position: absolute;
  inset: 0 auto 0 0;
  background: rgba(139, 115, 221, 0.14);
  transition: width 0.12s linear;
}
.voice-capsule.coral .capsule-progress { background: rgba(200, 116, 98, 0.14); }
.voice-capsule.mint .capsule-progress { background: rgba(42, 140, 95, 0.14); }
.capsule-icon, .capsule-sec, .capsule-bars { position: relative; z-index: 1; }
.capsule-icon { font-size: 12px; font-weight: 800; width: 16px; text-align: center; }
.capsule-sec { font-size: 12.5px; font-weight: 800; font-variant-numeric: tabular-nums; }
.capsule-bars { display: inline-flex; align-items: center; gap: 3.5px; flex: 1; height: 20px; }
.capsule-bars i {
  display: block;
  width: 3px;
  border-radius: 999px;
  background: currentColor;
  opacity: 0.45;
}
.voice-capsule.playing .capsule-bars i {
  opacity: 0.92;
  animation: barDance 0.72s ease-in-out infinite alternate;
}
@keyframes barDance {
  0% { transform: scaleY(0.45); }
  100% { transform: scaleY(1.15); }
}

.toggle-original-btn {
  padding: 9px 14px;
  border-radius: 12px;
  border: 1.5px solid #e6e1f2;
  border-bottom: 3px solid #ddd6ec;
  background: #ffffff;
  color: #5a5572;
  font-size: 12.5px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.toggle-original-btn.open.purple { background: #f4f0ff; border-color: #8b73dd; color: #6046b4; }
.toggle-original-btn.open.coral { background: #fdf6f4; border-color: #df9d8f; color: #b84a39; }
.toggle-original-btn.open.mint { background: #f3fbf7; border-color: #82cca4; color: #2a8c5f; }

.transcript-box {
  border-radius: 14px;
  border: 1.5px solid #e6e0f5;
  background: #ffffff;
  padding: 14px 16px;
}
.transcript-box.coral { border-color: #f0d5ce; }
.transcript-box.mint { border-color: #bee6d0; }
.transcript-en {
  font-size: 14.5px;
  font-weight: 600;
  color: var(--text);
  line-height: 1.55;
  margin-bottom: 4px;
}
.transcript-zh {
  font-size: 12.5px;
  color: var(--text-muted);
}

.unfold-enter-active, .unfold-leave-active {
  transition: opacity 0.28s ease, transform 0.28s ease;
}
.unfold-enter-from, .unfold-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@media (prefers-reduced-motion: reduce) {
  .pulse-ring, .voice-capsule.playing .capsule-bars i { animation: none; }
}
</style>

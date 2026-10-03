import { computed, onBeforeUnmount, ref, shallowRef } from 'vue'

// 口型驱动三级降级（L1 → L2 → L3），运行时按可用性自上而下选择：
//   L1 时间轴：TTS 返回词级 viseme 时间戳，按当前播放时间查表，口型与语音严格对齐
//   L2 音量包络：Web Audio AnalyserNode 取 RMS，嘴部开合随实时音量变化
//   L3 播放状态：仅用 playing 布尔，固定开合；此级别由 CSS 关键帧完成，本模块不参与
// 任何一级都不可用时退到 off（嘴部保持闭合），不报错、不空转。
//
// 注意：MediaElementAudioSourceNode 对同一媒体元素只能创建一次（重复创建会抛错），
// 因此该节点由播放器单例持有，本模块只读取 level 数值，不自己碰音频链。

const NOISE_FLOOR = 0.012 // 低于此 RMS 视为静音，避免环境噪声让嘴一直动
const PEAK = 0.32          // 高于此 RMS 视为全开，低于阈值线性映射到 0~1
const SMOOTHING = 0.35     // 平滑系数，抑制口型抖动（0 = 不平滑，1 = 几乎不动）

// 词 → viseme 的静态映射：按词首元音归类，首版不做音素级精细转换
const VISEME_BY_VOWEL = {
  a: 'wide', e: 'wide', i: 'wide', o: 'round', u: 'round',
}
// 各 viseme 对应的最大开合幅度（round 嘴型收窄但更鼓，wide 相反）
const VISEME_OPEN = { closed: 0.05, wide: 0.85, round: 0.6, open: 1 }

export function useLipsync() {
  const level = ref(0)              // 0~1 开合目标值
  const activeLevel = ref('state')  // 实际生效级别：timeline/envelope/state/off
  const audio = shallowRef(null)    // 参与分析的目标：HTMLAudioElement（由播放器注入）
  const timeline = ref(null)        // L1 时间轴数据 { duration_ms, words:[{start_ms,end_ms,viseme}] }

  let ctx = null
  let analyser = null
  let sourceNode = null
  let rafId = 0
  let smoothed = 0
  let lastViseme = 'closed'

  // ---- L1：按播放进度查表 ----
  function readTimeline() {
    const el = audio.value
    const data = timeline.value
    if (!el || !data?.words?.length || !el.duration) return null
    const now = el.currentTime * 1000
    // 找到当前时间落在哪个词区间
    const hit = data.words.find((w) => now >= w.start_ms && now < w.end_ms)
    if (!hit) return lastViseme
    lastViseme = hit.viseme || guessViseme(hit.text)
    return lastViseme
  }

  // 无 viseme 标注时按词首字母猜一个（体现降级链路，不假装精确）
  function guessViseme(word) {
    const first = String(word || '').trim().charAt(0).toLowerCase()
    return VISEME_BY_VOWEL[first] || 'open'
  }

  // ---- L2：音量包络 ----
  function readEnvelope() {
    if (!analyser) return null
    const buf = new Uint8Array(analyser.frequencyBinCount)
    analyser.getByteTimeDomainData(buf)
    // 时域数据算 RMS：偏离 128 的幅度越大，能量越高
    let sum = 0
    for (let i = 0; i < buf.length; i += 1) {
      const v = (buf[i] - 128) / 128
      sum += v * v
    }
    const rms = Math.sqrt(sum / buf.length)
    if (rms <= NOISE_FLOOR) return 0
    return Math.min(1, (rms - NOISE_FLOOR) / (PEAK - NOISE_FLOOR))
  }

  // ---- 统一驱动循环 ----
  function tick() {
    let target = 0
    if (activeLevel.value === 'timeline') {
      const viseme = readTimeline()
      target = viseme ? (VISEME_OPEN[viseme] ?? 0.5) : 0
    } else if (activeLevel.value === 'envelope') {
      target = readEnvelope() ?? 0
    }
    // 平滑：避免每帧跳变造成的抽搐感
    smoothed += (target - smoothed) * SMOOTHING
    level.value = smoothed
    rafId = requestAnimationFrame(tick)
  }

  function start() {
    if (!rafId) rafId = requestAnimationFrame(tick)
  }

  function stop() {
    if (rafId) { cancelAnimationFrame(rafId); rafId = 0 }
  }

  // 绑定播放器单例已建好的 analyser；重复绑定不新建节点
  function bindAnalyser(node) {
    analyser = node || null
  }

  // 完整接管音频链：仅在播放器尚未创建过节点时调用一次
  function attach(el) {
    audio.value = el
    if (!el || sourceNode) return // 幂等：已有节点直接复用
    const Ctx = window.AudioContext || window.webkitAudioContext
    if (!Ctx) return // 浏览器不支持 Web Audio：静默降级
    ctx = new Ctx()
    sourceNode = ctx.createMediaElementSource(el)
    analyser = ctx.createAnalyser()
    analyser.fftSize = 1024
    analyser.smoothingTimeConstant = 0.6
    sourceNode.connect(analyser)
    analyser.connect(ctx.destination) // 必须回连 destination，否则音频无声
  }

  // 切换级别：调用方按后端下发的 lip_sync 字段设置
  function setLevel(next) {
    if (!['timeline', 'envelope', 'state', 'off'].includes(next)) next = 'state'
    activeLevel.value = next
    if (next === 'timeline' || next === 'envelope') start()
    else stop()
  }

  // 打断：立刻闭合，不残留上一帧的开合
  function interrupt() {
    smoothed = 0
    level.value = 0
    stop()
  }

  onBeforeUnmount(() => {
    stop()
    // 不主动 close AudioContext：它属于播放器单例的生命周期
    sourceNode = null
    analyser = null
    ctx = null
  })

  return {
    mouthOpen: computed(() => level.value), // 供 AvatarStage 写入 --mouth-open
    activeLevel: computed(() => activeLevel.value), // 实际级别，供界面如实展示
    isDriven: computed(() => activeLevel.value === 'timeline' || activeLevel.value === 'envelope'),
    setLevel,
    attach,
    bindAnalyser,
    setTimeline: (data) => { timeline.value = data || null },
    interrupt,
  }
}

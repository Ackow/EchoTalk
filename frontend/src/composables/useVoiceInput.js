import { computed, onBeforeUnmount, ref } from 'vue'
import { encodeWav } from '../audio/wav'
import { transcribeRecording } from '../api/speech'

/** 管理麦克风生命周期；录音、转写和取消都以版本号隔离过期异步结果。 */
export function useVoiceInput({ onResult, onError }) {
  const status = ref('idle') // requesting / recording / stopping / transcribing
  const seconds = ref(0)
  const level = ref(0)
  // 用 ref 包一层：调用方（Practice.vue）按 .value 读取，裸布尔会导致永远判“不支持”。
  const supported = ref(Boolean(navigator.mediaDevices?.getUserMedia && window.AudioContext && window.AudioWorkletNode))
  const busy = computed(() => status.value !== 'idle')
  let generation = 0
  let active = null
  let upload = null

  function release(recording) {
    // 停止设备指示灯与音频线程；不依赖组件卸载或垃圾回收。
    if (!recording) return
    clearInterval(recording.timer)
    recording.flushDone?.()
    recording.stream?.getTracks().forEach(track => track.stop())
    recording.node?.disconnect()
    recording.source?.disconnect()
    recording.context?.close().catch(() => {})
    recording.chunks = []
  }

  function cancel() {
    // 取消可发生在权限请求、采集中或识别中；迟到的结果不会写进输入框。
    generation += 1
    upload?.abort()
    upload = null
    release(active)
    active = null
    status.value = 'idle'
    seconds.value = 0
    level.value = 0
  }

  async function start() {
    if (busy.value) return
    if (!supported.value) return onError('当前环境无法使用麦克风，请使用桌面客户端或支持录音的浏览器。')
    const current = ++generation
    const recording = { chunks: [], stream: null, context: null }
    active = recording
    seconds.value = 0
    status.value = 'requesting'
    try {
      recording.stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true } })
      if (current !== generation) { release(recording); return }
      recording.context = new AudioContext()
      await recording.context.resume()
      await recording.context.audioWorklet.addModule(new URL('./audio/pcm-recorder.worklet.js', document.baseURI).href)
      if (current !== generation) { release(recording); return }
      recording.node = new AudioWorkletNode(recording.context, 'pcm-recorder')
      recording.source = recording.context.createMediaStreamSource(recording.stream)
      recording.node.port.onmessage = ({ data }) => {
        if (current !== generation) return
        if (data.type === 'flushed') return recording.flushDone?.()
        if (data.type === 'limit') { stop(); return }
        recording.chunks.push(data.samples)
        let sum = 0
        for (const sample of data.samples) sum += sample * sample
        level.value = Math.min(1, Math.sqrt(sum / data.samples.length) * 6)
      }
      // 静音的处理器输出连接到 destination，保证图运行而不回放自己的声音。
      recording.source.connect(recording.node)
      recording.node.connect(recording.context.destination)
      recording.stream.getAudioTracks()[0].addEventListener('ended', () => {
        if (current !== generation || status.value !== 'recording') return
        cancel()
        onError('麦克风已断开，请重新录制。')
      })
      status.value = 'recording'
      recording.startedAt = performance.now()
      recording.timer = setInterval(() => {
        seconds.value = Math.min(60, Math.floor((performance.now() - recording.startedAt) / 1000))
        if (seconds.value >= 60) stop()
      }, 200)
    } catch (error) {
      if (current !== generation) return
      cancel()
      const message = error.name === 'NotAllowedError' ? '麦克风权限被拒绝，请在系统或浏览器设置中允许访问。' : error.name === 'NotFoundError' ? '没有找到麦克风，请连接设备后重试。' : '无法启动录音，请检查麦克风是否被占用。'
      onError(message)
    }
  }

  async function stop() {
    if (status.value !== 'recording') return
    const current = generation
    const recording = active
    status.value = 'stopping'
    clearInterval(recording.timer)
    try {
      // 等待 worklet 发完尾段，防止短句最后几个音节被截掉。
      await new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error('录音设备响应超时，请重新录制。')), 2000)
        recording.flushDone = () => { clearTimeout(timer); resolve() }
        recording.node.port.postMessage('flush')
      })
      if (current !== generation) return
      const chunks = recording.chunks.slice()
      const sampleRate = recording.context.sampleRate
      release(recording)
      active = null
      level.value = 0
      const blob = await encodeWav(chunks, sampleRate)
      if (current !== generation) return
      status.value = 'transcribing'
      upload = new AbortController()
      const { data } = await transcribeRecording(blob, upload.signal)
      if (current !== generation) return
      status.value = 'idle'
      onResult(data.text)
    } catch (error) {
      if (current !== generation) return
      onError(error.message || '语音识别失败，请重新录制。')
    } finally {
      if (current === generation) {
        release(active)
        active = null
        upload = null
        status.value = 'idle'
      }
    }
  }

  onBeforeUnmount(cancel)
  return { status, seconds, level, busy, supported, start, stop, cancel }
}

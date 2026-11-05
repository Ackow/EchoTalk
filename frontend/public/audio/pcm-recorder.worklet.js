/* 在音频线程中采集单声道 PCM；批量发送，停止时确认最后一段已送达。 */
class PcmRecorder extends AudioWorkletProcessor {
  constructor() {
    super()
    this.buffer = new Float32Array(2048)
    this.offset = 0
    this.active = true
    this.total = 0
    this.limit = sampleRate * 60
    this.port.onmessage = ({ data }) => {
      if (data === 'flush') {
        this.active = false
        this.flush()
        this.port.postMessage({ type: 'flushed' })
      }
    }
  }

  flush() {
    if (!this.offset) return
    const samples = this.buffer.slice(0, this.offset)
    this.port.postMessage({ type: 'samples', samples }, [samples.buffer])
    this.offset = 0
  }

  process(inputs) {
    if (!this.active) return false
    if (this.total >= this.limit) return true
    const channels = inputs[0]
    if (channels?.length) {
      for (let i = 0; i < channels[0].length; i++) {
        let sample = 0
        for (const channel of channels) sample += channel[i]
        this.buffer[this.offset++] = sample / channels.length
        this.total += 1
        if (this.offset === this.buffer.length) this.flush()
        // 音频线程本身限制采样量，后台标签页计时器被节流时也不继续录制。
        if (this.total >= this.limit) {
          this.flush()
          this.port.postMessage({ type: 'limit' })
          break
        }
      }
    }
    return true
  }
}
registerProcessor('pcm-recorder', PcmRecorder)

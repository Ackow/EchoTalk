// 将音频线程采集的 PCM 重采样为标准 16kHz / 单声道 / 16bit WAV。
export async function encodeWav(chunks, sourceRate) {
  const length = chunks.reduce((total, chunk) => total + chunk.length, 0)
  if (length / sourceRate < 0.3) throw new Error('录音太短，请至少说一句话再结束。')
  const count = Math.min(length, sourceRate * 60)
  const context = new OfflineAudioContext(1, Math.floor(count * 16000 / sourceRate), 16000)
  const input = context.createBuffer(1, count, sourceRate)
  const channel = input.getChannelData(0)
  let offset = 0
  for (const chunk of chunks) {
    const size = Math.min(chunk.length, count - offset)
    if (size <= 0) break
    channel.set(chunk.subarray(0, size), offset)
    offset += size
  }
  const source = context.createBufferSource()
  source.buffer = input
  source.connect(context.destination)
  source.start()
  const rendered = await context.startRendering()
  const samples = rendered.getChannelData(0)
  const buffer = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(buffer)
  const text = (offset, value) => [...value].forEach((char, index) => view.setUint8(offset + index, char.charCodeAt(0)))
  text(0, 'RIFF'); view.setUint32(4, 36 + samples.length * 2, true); text(8, 'WAVE')
  text(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true)
  view.setUint16(22, 1, true); view.setUint32(24, 16000, true); view.setUint32(28, 32000, true)
  view.setUint16(32, 2, true); view.setUint16(34, 16, true); text(36, 'data')
  view.setUint32(40, samples.length * 2, true)
  samples.forEach((sample, index) => {
    const value = Math.max(-1, Math.min(1, sample))
    view.setInt16(44 + index * 2, Math.round(value * (value < 0 ? 32768 : 32767)), true)
  })
  return new Blob([buffer], { type: 'audio/wav' })
}

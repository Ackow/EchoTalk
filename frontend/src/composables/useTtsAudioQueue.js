export function base64ToMp3Blob(b64) {
  const bin = atob(b64)
  const bytes = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i += 1) bytes[i] = bin.charCodeAt(i)
  return new Blob([bytes], { type: 'audio/mpeg' })
}

export function useTtsAudioQueue({
  messages,
  playingKey,
  playbackTime,
  playbackDuration,
  avatarState,
  speechRate,
  playbackNotice,
  estimateSeconds,
  getCurrentAudio,
  setCurrentAudio,
}) {
  let streamAudioQueue = []
  let streamAudioEnded = false
  let streamPlaybackGen = 0
  let streamPlayedOffset = 0
  let streamKnownDuration = 0

  function resetStreamAudioQueue() {
    streamPlaybackGen += 1
    for (const item of streamAudioQueue) {
      if (item.url?.startsWith('blob:')) URL.revokeObjectURL(item.url)
    }
    streamAudioQueue = []
    streamAudioEnded = false
    streamPlayedOffset = 0
    streamKnownDuration = 0
    return streamPlaybackGen
  }

  function getStreamPlaybackGen() {
    return streamPlaybackGen
  }

  function enqueueStreamAudioChunk(blob, text = '') {
    streamAudioQueue.push({ url: URL.createObjectURL(blob), text })
  }

  function markStreamAudioEnded(msgKey = '') {
    streamAudioEnded = true
    if (!getCurrentAudio() && streamAudioQueue.length === 0) {
      if (!msgKey || playingKey.value === msgKey) playingKey.value = ''
      if (avatarState.value === 'speaking' || avatarState.value === 'thinking') avatarState.value = 'idle'
    }
  }

  async function pumpStreamAudio(msgKey, expectedGen) {
    if (expectedGen !== streamPlaybackGen || getCurrentAudio()) return
    const next = streamAudioQueue.shift()
    if (!next) {
      if (streamAudioEnded) {
        const displayed = messages.value.find((item) => item.key === msgKey)
        if (displayed && streamPlayedOffset > 0) displayed.duration = streamPlayedOffset
        playingKey.value = ''
        playbackTime.value = 0
        playbackDuration.value = 0
        if (avatarState.value === 'speaking') avatarState.value = 'idle'
      }
      return
    }
    const audio = new Audio(next.url)
    audio.preservesPitch = true
    audio.playbackRate = speechRate.value
    setCurrentAudio(audio)
    playingKey.value = msgKey
    avatarState.value = 'speaking'
    let chunkDuration = 0
    const displayed = messages.value.find((item) => item.key === msgKey)
    if (!playbackDuration.value) {
      playbackDuration.value = estimateSeconds(displayed?.text || next.text || '')
    }
    audio.ontimeupdate = () => {
      const cur = getCurrentAudio()
      playbackTime.value = streamPlayedOffset + (cur?.currentTime || 0)
    }
    audio.onloadedmetadata = () => {
      chunkDuration = Number.isFinite(audio.duration) ? audio.duration : 0
      if (chunkDuration > 0) {
        streamKnownDuration += chunkDuration
        const est = estimateSeconds(displayed?.text || '')
        playbackDuration.value = Math.max(streamKnownDuration, est)
      }
    }
    const finishChunk = () => {
      const actual = Number.isFinite(audio.duration) && audio.duration > 0 ? audio.duration : (audio.currentTime || chunkDuration)
      streamPlayedOffset += actual
      if (next.url?.startsWith('blob:')) URL.revokeObjectURL(next.url)
      if (getCurrentAudio() === audio) setCurrentAudio(null)
      if (expectedGen === streamPlaybackGen) void pumpStreamAudio(msgKey, expectedGen)
    }
    audio.onended = finishChunk
    audio.onerror = finishChunk
    try {
      await audio.play()
    } catch (err) {
      if (next.url?.startsWith('blob:')) URL.revokeObjectURL(next.url)
      if (getCurrentAudio() === audio) setCurrentAudio(null)
      resetStreamAudioQueue()
      playingKey.value = ''
      if (avatarState.value === 'speaking') avatarState.value = 'idle'
      if (err?.name === 'NotAllowedError') {
        playbackNotice.value = '浏览器阻止了自动播放，请点击回复下方的「听语音」。'
      }
    }
  }

  return {
    resetStreamAudioQueue,
    getStreamPlaybackGen,
    enqueueStreamAudioChunk,
    markStreamAudioEnded,
    pumpStreamAudio,
  }
}

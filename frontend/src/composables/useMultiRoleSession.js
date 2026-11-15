import { nextTick, ref } from 'vue'
import { synthesizeSpeech } from '../api/avatar'

export function splitSpeechSentences(text) {
  const raw = String(text || '').replace(/\s+/g, ' ').trim()
  if (!raw) return []
  const parts = raw.match(/[^.!?]+[.!?]+(?:\s+|$)|[^.!?]+$/g) || [raw]
  const merged = []
  for (const part of parts) {
    const clean = part.trim()
    if (!clean) continue
    if (merged.length && merged[merged.length - 1].length < 24) {
      merged[merged.length - 1] = `${merged[merged.length - 1]} ${clean}`
    } else {
      merged.push(clean)
    }
  }
  return merged.length ? merged : [raw]
}

export function formatRoleLabel(roleType, rawTitle, { isPanelMode = false, userSide = 'pro' } = {}) {
  const title = String(rawTitle || '').trim()
  if (!isPanelMode && roleType === 'opponent') {
    const oppSide = userSide === 'pro' ? '反方' : '正方'
    if (!title) return oppSide
    if (title.includes('反方') || title.includes('正方')) return title
    return `${oppSide} · ${title}`
  }
  return title || '参与角色'
}

export function radarRingPoints(scale) {
  const cx = 124
  const cy = 92
  const r = 54 * scale
  return `${cx},${(cy - r).toFixed(1)} ${(cx + r).toFixed(1)},${cy} ${cx},${(cy + r).toFixed(1)} ${(cx - r).toFixed(1)},${cy}`
}

export function useMultiRoleSession({ inArena, feedRef, messages, findRoleIdForMessage, speakingRole }) {
  const playingMsgId = ref('')
  const loadingMsgId = ref('')
  const autoPlayAudio = ref(true)
  const msgAudioProgress = ref(0)
  let msgAudioEl = null
  let seqPlaybackToken = 0
  const ttsCache = new Map()

  function stopMsgAudio(cancelSequence = true) {
    if (cancelSequence) seqPlaybackToken += 1
    if (msgAudioEl) {
      msgAudioEl.pause()
      msgAudioEl.onended = null
      msgAudioEl.ontimeupdate = null
      msgAudioEl.onerror = null
      msgAudioEl = null
    }
    playingMsgId.value = ''
    msgAudioProgress.value = 0
  }

  function clearMsgAudioCache() {
    stopMsgAudio(true)
  }

  async function fetchSentenceTtsUrl(text, voiceStyle) {
    const voice = voiceStyle || 'brian'
    const cacheKey = `${voice}:${text}`
    let url = ttsCache.get(cacheKey)
    if (!url) {
      const blob = await synthesizeSpeech(text, voice, 1.0)
      url = URL.createObjectURL(blob)
      if (ttsCache.size >= 80) {
        const oldestKey = ttsCache.keys().next().value
        const oldestUrl = ttsCache.get(oldestKey)
        if (oldestUrl) URL.revokeObjectURL(oldestUrl)
        ttsCache.delete(oldestKey)
      }
      ttsCache.set(cacheKey, url)
    }
    return url
  }

  async function playSingleMsgAudio(msg, token) {
    if (!msg?.en || !inArena.value || token !== seqPlaybackToken) return
    const rid = findRoleIdForMessage(msg)
    if (rid) speakingRole.value = rid
    const sentences = splitSpeechSentences(msg.en)
    if (!sentences.length) return
    const voice = msg.voiceStyle || 'brian'
    const total = sentences.length

    loadingMsgId.value = msg.id
    let currentPromise = fetchSentenceTtsUrl(sentences[0], voice)
    try {
      for (let i = 0; i < total; i++) {
        if (!inArena.value || token !== seqPlaybackToken) break
        const url = await currentPromise
        if (loadingMsgId.value === msg.id) loadingMsgId.value = ''
        if (!inArena.value || token !== seqPlaybackToken) break

        const nextPromise = i + 1 < total ? fetchSentenceTtsUrl(sentences[i + 1], voice).catch(() => null) : null

        await new Promise((resolve) => {
          if (!inArena.value || token !== seqPlaybackToken) {
            resolve()
            return
          }
          stopMsgAudio(false)
          msgAudioEl = new Audio(url)
          playingMsgId.value = msg.id
          msgAudioProgress.value = Math.round((i / total) * 100)
          const finish = () => {
            stopMsgAudio(false)
            resolve()
          }
          msgAudioEl.ontimeupdate = () => {
            if (msgAudioEl?.duration) {
              const frac = msgAudioEl.currentTime / msgAudioEl.duration
              msgAudioProgress.value = Math.min(100, ((i + frac) / total) * 100)
            }
          }
          msgAudioEl.onended = finish
          msgAudioEl.onerror = finish
          msgAudioEl.play().catch(finish)
        })

        if (!nextPromise) break
        currentPromise = nextPromise
      }
    } catch {
      // 单句合成失败时静默结束，避免阻塞后续流程
    } finally {
      if (loadingMsgId.value === msg.id) loadingMsgId.value = ''
    }
  }

  async function revealAndPlayMessages(aiMsgs) {
    if (!Array.isArray(aiMsgs) || !aiMsgs.length) return
    stopMsgAudio(true)
    const token = seqPlaybackToken
    for (let i = 0; i < aiMsgs.length; i++) {
      if (!inArena.value || token !== seqPlaybackToken) break
      const msg = aiMsgs[i]
      messages.value.push(msg)
      const rid = findRoleIdForMessage(msg)
      if (rid) speakingRole.value = rid
      await nextTick()
      if (feedRef.value) feedRef.value.scrollTop = feedRef.value.scrollHeight
      if (autoPlayAudio.value) {
        await playSingleMsgAudio(msg, token)
      } else if (i < aiMsgs.length - 1) {
        await new Promise((resolve) => setTimeout(resolve, 650))
      }
    }
  }

  async function playMessagesSequentially(msgList) {
    if (!Array.isArray(msgList) || !msgList.length) return
    stopMsgAudio(true)
    const token = seqPlaybackToken
    for (const msg of msgList) {
      if (!inArena.value || token !== seqPlaybackToken) break
      await playSingleMsgAudio(msg, token)
    }
  }

  async function toggleMsgAudio(msg) {
    if (!msg?.en) return
    if (playingMsgId.value === msg.id) {
      stopMsgAudio(true)
      return
    }
    stopMsgAudio(true)
    const token = seqPlaybackToken
    await playSingleMsgAudio(msg, token)
  }

  function disposeTtsCache() {
    for (const url of ttsCache.values()) {
      URL.revokeObjectURL(url)
    }
    ttsCache.clear()
  }

  return {
    playingMsgId,
    loadingMsgId,
    autoPlayAudio,
    msgAudioProgress,
    stopMsgAudio,
    clearMsgAudioCache,
    revealAndPlayMessages,
    playMessagesSequentially,
    toggleMsgAudio,
    disposeTtsCache,
  }
}

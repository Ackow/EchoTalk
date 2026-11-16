const REPO = 'Ackow/EchoTalk'
export const RELEASES_PAGE_URL = `https://github.com/${REPO}/releases/latest`
const RELEASES_API_URL = `https://api.github.com/repos/${REPO}/releases/latest`
const CACHE_KEY = 'echotalk_latest_release_v1'
const CACHE_TTL_MS = 5 * 60 * 1000

/**
 * 识别访客操作系统与 CPU 架构（用于自动匹配对应安装包）。
 * 返回 key: 'mac-arm64' | 'mac-x64' | 'win-x64' | 'other'
 */
export async function detectClientTarget() {
  const ua = navigator.userAgent || ''
  const platform = navigator.platform || ''
  const isWin = /Win/i.test(platform) || /Windows/i.test(ua)
  const isMac = /Mac/i.test(platform) || /Macintosh|Mac OS X/i.test(ua)

  if (isWin) {
    return { key: 'win-x64', label: 'Windows 安装包 (.exe)', shortLabel: 'Windows 版' }
  }

  if (isMac) {
    // 注意：所有 Mac 浏览器的 UA 均固定包含 "Intel Mac OS X"，不能用 UA 判断架构
    let arch = ''
    try {
      if (navigator.userAgentData?.getHighEntropyValues) {
        const info = await navigator.userAgentData.getHighEntropyValues(['architecture'])
        arch = (info.architecture || '').toLowerCase()
      }
    } catch {
      // ignore
    }

    if (arch === 'x86') {
      return { key: 'mac-x64', label: 'macOS Intel 安装包 (.dmg)', shortLabel: 'macOS (Intel)' }
    }
    if (arch === 'arm') {
      return { key: 'mac-arm64', label: 'macOS Apple Silicon 安装包 (.dmg)', shortLabel: 'macOS (Apple Silicon)' }
    }

    // Safari / Firefox 无 userAgentData 时，通过 WebGL 渲染器区分 Apple GPU 与 Intel/AMD GPU
    try {
      const canvas = document.createElement('canvas')
      const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl')
      const ext = gl && gl.getExtension('WEBGL_debug_renderer_info')
      const renderer = ext ? String(gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) || '') : ''
      if (/\b(Intel|AMD|Radeon|NVIDIA)\b/i.test(renderer) && !/Apple/i.test(renderer)) {
        return { key: 'mac-x64', label: 'macOS Intel 安装包 (.dmg)', shortLabel: 'macOS (Intel)' }
      }
    } catch {
      // ignore
    }

    return { key: 'mac-arm64', label: 'macOS Apple Silicon 安装包 (.dmg)', shortLabel: 'macOS (Apple Silicon)' }
  }

  return { key: 'other', label: '前往 GitHub Releases 选择安装包', shortLabel: '桌面端下载' }
}

function matchAssets(assets = []) {
  const list = Array.isArray(assets) ? assets : []
  const dmgArm = list.find((a) => /\.dmg$/i.test(a.name) && /arm64|aarch64/i.test(a.name))
  const dmgX64 = list.find((a) => /\.dmg$/i.test(a.name) && /x64|x86_64|intel/i.test(a.name))
  const dmgAny = list.find((a) => /\.dmg$/i.test(a.name))
  const winExe = list.find((a) => /\.exe$/i.test(a.name))

  return {
    'mac-arm64': dmgArm?.browser_download_url || dmgAny?.browser_download_url || '',
    'mac-x64': dmgX64?.browser_download_url || dmgAny?.browser_download_url || '',
    'win-x64': winExe?.browser_download_url || '',
  }
}

export async function fetchLatestRelease() {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY)
    if (raw) {
      const cached = JSON.parse(raw)
      if (cached && Date.now() - cached.ts < CACHE_TTL_MS) {
        return cached.data
      }
    }
  } catch {
    // ignore
  }

  try {
    const res = await fetch(RELEASES_API_URL, {
      headers: { Accept: 'application/vnd.github+json' },
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const json = await res.json()
    const data = {
      version: json.tag_name || 'v2.0.0',
      pageUrl: json.html_url || RELEASES_PAGE_URL,
      urls: matchAssets(json.assets),
    }
    try {
      sessionStorage.setItem(CACHE_KEY, JSON.stringify({ ts: Date.now(), data }))
    } catch {
      // ignore
    }
    return data
  } catch {
    return {
      version: '',
      pageUrl: RELEASES_PAGE_URL,
      urls: { 'mac-arm64': '', 'mac-x64': '', 'win-x64': '' },
    }
  }
}

export async function triggerAutoDownload() {
  const [target, release] = await Promise.all([detectClientTarget(), fetchLatestRelease()])
  const url = release.urls[target.key] || release.pageUrl || RELEASES_PAGE_URL
  window.open(url, '_blank', 'noopener')
  return { target, release, url }
}

/**
 * 尝试通过 echotalk://open 唤起本机桌面客户端。
 * 若 1.8 秒内页面未切走，则触发 onFallback 回调提示下载。
 */
export function openLocalApp(onFallback) {
  let switched = false
  const onBlurOrHide = () => {
    if (document.hidden || !document.hasFocus()) {
      switched = true
      cleanup()
    }
  }
  const cleanup = () => {
    document.removeEventListener('visibilitychange', onBlurOrHide)
    window.removeEventListener('blur', onBlurOrHide)
  }

  document.addEventListener('visibilitychange', onBlurOrHide)
  window.addEventListener('blur', onBlurOrHide)

  window.location.href = 'echotalk://open'

  setTimeout(() => {
    cleanup()
    if (!switched && typeof onFallback === 'function') {
      onFallback()
    }
  }, 1800)
}

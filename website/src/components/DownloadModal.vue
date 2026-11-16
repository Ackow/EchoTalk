<template>
  <Teleport to="body">
    <div v-if="open" class="dl-backdrop" @click.self="$emit('close')">
      <div class="tactile-card dl-modal" role="dialog" aria-modal="true">
        <div class="dl-head">
          <span class="dl-badge">EchoTalk 2.0 桌面客户端{{ release.version ? ` · ${release.version}` : '' }}</span>
          <button type="button" class="dl-close" aria-label="关闭" @click="$emit('close')">×</button>
        </div>

        <p v-if="notice" class="dl-notice">{{ notice }}</p>
        <h3>选择适合当前设备的安装包</h3>
        <p class="dl-sub">安装包托管于 GitHub Releases，已为你自动识别当前系统。</p>

        <div class="dl-primary-box">
          <div>
            <span class="dl-rec-tag">推荐当前设备</span>
            <strong>{{ target.label }}</strong>
          </div>
          <a
            :href="recommendedUrl"
            target="_blank"
            rel="noopener"
            class="btn-primary dl-go"
          >
            立即下载
          </a>
        </div>

        <div class="dl-others">
          <a :href="release.urls['mac-arm64'] || release.pageUrl" target="_blank" rel="noopener">
            <b>macOS (Apple Silicon)</b><span>.dmg</span>
          </a>
          <a :href="release.urls['mac-x64'] || release.pageUrl" target="_blank" rel="noopener">
            <b>macOS (Intel)</b><span>.dmg</span>
          </a>
          <a :href="release.urls['win-x64'] || release.pageUrl" target="_blank" rel="noopener">
            <b>Windows 10/11</b><span>.exe</span>
          </a>
        </div>

        <div class="dl-foot">
          <button type="button" class="btn-secondary dl-open-btn" @click="handleOpenApp">
            已安装？打开本机 APP
          </button>
          <a :href="release.pageUrl" target="_blank" rel="noopener" class="dl-all-link">
            查看全部历史版本 →
          </a>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import {
  RELEASES_PAGE_URL,
  detectClientTarget,
  fetchLatestRelease,
  openLocalApp,
} from '../utils/clientDownload.js'

const props = defineProps({
  open: Boolean,
  notice: { type: String, default: '' },
})
const emit = defineEmits(['close', 'update:notice'])

const target = ref({ key: 'other', label: '桌面客户端安装包', shortLabel: '桌面端' })
const release = ref({
  version: '',
  pageUrl: RELEASES_PAGE_URL,
  urls: { 'mac-arm64': '', 'mac-x64': '', 'win-x64': '' },
})

const recommendedUrl = computed(() => {
  return release.value.urls[target.value.key] || release.value.pageUrl || RELEASES_PAGE_URL
})

async function loadMeta() {
  const [t, r] = await Promise.all([detectClientTarget(), fetchLatestRelease()])
  target.value = t
  release.value = r
}

function handleOpenApp() {
  openLocalApp(() => {
    emit('update:notice', '未检测到本机已安装的 EchoTalk 客户端，请先下载安装后再尝试打开。')
  })
}

watch(() => props.open, (v) => {
  if (v) loadMeta()
})
onMounted(loadMeta)
</script>

<style scoped>
.dl-backdrop {
  position: fixed;
  inset: 0;
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(34, 37, 59, 0.32);
  backdrop-filter: blur(3px);
}
.dl-modal {
  width: 100%;
  max-width: 520px;
  padding: 24px 26px;
}
.dl-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.dl-badge {
  font-size: 12px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 999px;
  background: #eee9ff;
  color: var(--primary-ink);
}
.dl-close {
  width: 30px;
  height: 30px;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: #fff;
  color: var(--text-soft);
  font-size: 18px;
  cursor: pointer;
}
.dl-notice {
  padding: 9px 12px;
  border-radius: 10px;
  background: #fff3ea;
  border: 1px solid #f4d8be;
  color: #9c4f17;
  font-size: 13px;
  margin-bottom: 12px;
}
.dl-modal h3 { font-size: 20px; font-weight: 800; color: var(--text); margin-bottom: 4px; }
.dl-sub { font-size: 13.5px; color: var(--text-muted); margin-bottom: 16px; }
.dl-primary-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 14px;
  background: #faf9fd;
  border: 1.5px solid #e6e1f2;
  margin-bottom: 12px;
}
.dl-rec-tag {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  color: #2a8c5f;
  background: #eaf7f0;
  padding: 2px 8px;
  border-radius: 999px;
  margin-bottom: 4px;
}
.dl-primary-box strong { display: block; font-size: 14.5px; color: var(--text); }
.dl-go { padding: 10px 18px; font-size: 13.5px; white-space: nowrap; }
.dl-others {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 18px;
}
.dl-others a {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px;
  border-radius: 11px;
  border: 1px solid var(--border);
  background: #fff;
  font-size: 12px;
  transition: border-color 0.15s, background 0.15s;
}
.dl-others a:hover { border-color: var(--primary); background: #f8f6ff; }
.dl-others b { color: var(--text); font-weight: 700; }
.dl-others span { color: var(--text-dim); font-size: 11.5px; }
.dl-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 14px;
  border-top: 1px solid #efecf7;
}
.dl-open-btn { padding: 8px 14px; font-size: 13px; }
.dl-all-link { font-size: 13px; font-weight: 600; color: var(--primary-ink); }
@media (max-width: 540px) {
  .dl-others { grid-template-columns: 1fr; }
  .dl-primary-box { flex-direction: column; align-items: stretch; }
}
</style>

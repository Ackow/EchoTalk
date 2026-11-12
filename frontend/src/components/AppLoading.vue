<template>
  <!-- 全局加载遮罩：覆盖整个窗口，路由切换或长流程加载时显示 -->
  <transition name="mask">
    <div v-if="loadingVisible" class="app-loading" role="status" aria-live="polite" aria-busy="true">
      <div class="al-stage">
        <span class="al-halo" aria-hidden="true"></span>
        <span class="al-ring outer" aria-hidden="true"></span>
        <span class="al-ring inner" aria-hidden="true"></span>
        <span class="al-logo"><img :src="brandImage" alt="EchoTalk" /></span>
      </div>
      <div class="al-brand"><b>EchoTalk</b><em>2.0</em></div>
      <p class="al-text">
        {{ loadingText || '正在加载' }}
        <span class="al-dots" aria-hidden="true"><i></i><i></i><i></i></span>
      </p>
    </div>
  </transition>
</template>

<script setup>
import brandImage from '../assets/echotalk-brand.png'
import { loadingText, loadingVisible } from '../app/loading'
</script>

<style scoped>
.app-loading {
  position: fixed;
  inset: 0;
  z-index: 4000; /* 高于侧栏、模态与浮层 */
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  /* 与首屏 boot.css 同一套视觉：切换时不出现底色差异 */
  background: radial-gradient(58% 52% at 50% 46%, #ffffff 0%, #fbfaff 68%, #f8f5fd 100%);
  -webkit-app-region: no-drag; /* 遮罩期间不触发窗口拖拽 */
  user-select: none;
}

/* 主视觉：双环反向旋转 + logo 呼吸，外圈光晕做柔化 */
.al-stage { position: relative; display: grid; width: 120px; height: 120px; place-items: center; }
.al-halo {
  position: absolute;
  inset: -18px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(148, 120, 230, .18), transparent 68%);
  animation: al-halo 2.4s ease-in-out infinite;
}
.al-ring { position: absolute; border-radius: 50%; }
.al-ring.outer { inset: 0; border: 2.5px solid #e9e0fa; border-top-color: #9f88e4; animation: al-spin 1.6s linear infinite; }
.al-ring.inner { inset: 14px; border: 2px solid #f0e9fc; border-bottom-color: #7f66d6; animation: al-spin 1s linear infinite reverse; }

.al-logo {
  position: relative;
  display: grid;
  width: 72px;
  height: 72px;
  place-items: center;
  overflow: hidden;
  border: 1.5px solid #e7dcfa;
  border-radius: 22px;
  background: #fff;
  box-shadow: 0 3px 0 #e4d9f6; /* 底厚边：延续卡片风格，不额外加光圈，避免与内环挤在一起 */
  animation: al-breathe 2.2s ease-in-out infinite;
}
.al-logo img { display: block; width: 100%; height: 100%; object-fit: contain; transform: scale(1.3); }

.al-brand { display: flex; align-items: center; gap: 7px; }
.al-brand b { color: #3b3557; font-size: 19px; font-weight: 800; letter-spacing: -.02em; }
.al-brand em {
  padding: 1.5px 7px;
  border: 1px solid #ddd3f3;
  border-radius: 999px;
  background: #fff;
  color: #7b68b8;
  font-size: 10px;
  font-style: normal;
  font-weight: 700;
}

.al-text { display: inline-flex; align-items: center; gap: 7px; margin: -4px 0 0; color: #8f88a6; font-size: 13px; }
.al-dots { display: inline-flex; gap: 3px; }
.al-dots i { width: 4px; height: 4px; border-radius: 50%; background: #a48fe0; animation: al-dot 1.2s ease-in-out infinite; }
.al-dots i:nth-child(2) { animation-delay: .16s; }
.al-dots i:nth-child(3) { animation-delay: .32s; }

.mask-enter-active, .mask-leave-active { transition: opacity .2s ease; }
.mask-enter-from, .mask-leave-to { opacity: 0; }

@keyframes al-spin { to { transform: rotate(360deg); } }
@keyframes al-breathe { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.04); } }
@keyframes al-halo { 0%, 100% { opacity: .55; transform: scale(.9); } 50% { opacity: 1; transform: scale(1.06); } }
@keyframes al-dot { 0%, 80%, 100% { opacity: .25; transform: translateY(0); } 40% { opacity: 1; transform: translateY(-3px); } }

@media (prefers-reduced-motion: reduce) {
  .al-halo, .al-ring, .al-logo, .al-dots i { animation: none; }
}
</style>

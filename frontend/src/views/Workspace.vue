<template>
  <section class="home-page">
    <div class="home-content">
      <div class="top-grid">
        <section class="hero">
          <div class="hero-copy">
            <span class="eyebrow"><span class="eyebrow-icon"><AppIcon name="messages" :size="17" /></span>准备好开口了吗？</span>
            <h2>今天聊点什么？</h2>
            <p>选一个喜欢的场景，<br />和交流伙伴一起练习英语。</p>
            <router-link class="primary-button" :to="{ name: 'practice' }"><AppIcon name="mic" :size="18" />开始练习<AppIcon name="arrow-right" :size="18" class="btn-arrow" /></router-link>
          </div>
          <span class="hero-doodle doodle-one" aria-hidden="true">✳</span><span class="hero-doodle doodle-two" aria-hidden="true">✦</span>
          <img class="hero-illustration" :src="heroImage" alt="" />
        </section>
        <div class="quick-links">
          <router-link class="quick-card" :to="{ name: 'scenes' }">
            <span class="quick-icon purple" aria-hidden="true"><svg class="feature-icon" viewBox="0 0 64 64" fill="none"><path d="M12 19 25 14l14 5 13-5v31l-13 5-14-5-13 5V19Z" fill="#fff9ec" stroke="#55466e" stroke-width="2.6" stroke-linejoin="round"/><path d="M25 14v31m14-26v31" stroke="#b4a0d9" stroke-width="2.2"/><path d="M29 29c0-5 3.5-8.5 8-8.5s8 3.5 8 8.5c0 5.4-8 12-8 12s-8-6.6-8-12Z" fill="#b19aea" stroke="#55466e" stroke-width="2.6" stroke-linejoin="round"/><circle cx="37" cy="29" r="2.5" fill="#fff"/></svg></span><span class="quick-copy"><b>发现新场景</b><small>浏览对话主题，找到想练习的场景</small></span><span class="quick-arrow"><AppIcon name="arrow-right" :size="18" /></span>
          </router-link>
          <router-link class="quick-card green" :to="{ name: 'avatar' }">
            <span class="quick-icon mint" aria-hidden="true"><svg class="feature-icon" viewBox="0 0 64 64" fill="none"><path d="M15 49c1-9 7-14 17-14s16 5 17 14v3H15v-3Z" fill="#a7dfc5" stroke="#55466e" stroke-width="2.6" stroke-linejoin="round"/><circle cx="32" cy="26" r="13" fill="#fff3db" stroke="#55466e" stroke-width="2.6"/><path d="M19 24v-3a13 13 0 0 1 26 0v3" stroke="#55466e" stroke-width="3" stroke-linecap="round"/><rect x="15.5" y="23" width="6" height="11" rx="3" fill="#b19aea" stroke="#55466e" stroke-width="2.3"/><rect x="42.5" y="23" width="6" height="11" rx="3" fill="#b19aea" stroke="#55466e" stroke-width="2.3"/><path d="M27 26h.1m9.8 0h.1" stroke="#55466e" stroke-width="3" stroke-linecap="round"/><path d="M28.5 31.5c2 1.8 5 1.8 7 0" stroke="#b87672" stroke-width="2" stroke-linecap="round"/></svg></span><span class="quick-copy"><b>设置交流伙伴</b><small>选择喜欢的形象、声音与语速</small></span><span class="quick-arrow"><AppIcon name="arrow-right" :size="18" /></span>
          </router-link>
        </div>
      </div>

      <section class="featured">
        <header class="section-heading"><div><span class="section-icon"><AppIcon name="compass" :size="21" /></span><h2>精选场景</h2><p>选择一个话题，开始你的英语练习。</p></div><router-link :to="{ name: 'scenes' }">查看更多场景 <AppIcon name="arrow-right" :size="16" /></router-link></header>
        <div v-if="loading" class="scene-message" role="status">正在加载场景…</div>
        <div v-else-if="loadError" class="scene-message" role="status">暂时无法加载场景，请稍后再试。</div>
        <div v-else-if="!scenes.length" class="scene-message">还没有可用的场景，去场景探索看看吧。</div>
        <div v-else class="scene-grid">
          <router-link v-for="(scene, index) in scenes" :key="scene.id" class="scene-card" :style="{ animationDelay: `${index * 55}ms` }" :to="{ name: 'practice', query: { scene: scene.id } }">
            <div class="scene-art" :class="`tone-${index % 4}`">
              <img v-if="scene.cover_path && !failedCovers.has(scene.id)" :src="coverUrl(scene.id)" alt="" @error="failedCovers.add(scene.id)" />
              <template v-else><span class="scene-art-circle"></span><AppIcon :name="sceneIcon(scene)" :size="42" /><span class="scene-art-dot"></span></template>
            </div>
            <div class="scene-body"><div><span class="scene-tag">{{ scene.mode === 'interview' ? '模拟面试' : '场景对话' }}</span><h3>{{ scene.name }}</h3><p>{{ scene.description || '在真实情境中练习英语表达。' }}</p></div><span class="scene-arrow"><AppIcon name="arrow-right" :size="16" /></span></div>
          </router-link>
        </div>
      </section>

      <section class="plan-banner"><span class="plan-icon"><AppIcon name="calendar-check" :size="25" /></span><div><div class="plan-title"><h2>个性化训练计划</h2><span>正在准备中</span></div><p>未来将根据你的目标提供练习建议，敬请期待。</p></div></section>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import heroImage from '../assets/today-conversation-cartoon.png'
import { coverUrl, listScenes } from '../api/scenes'
import { usePageLoading } from '../app/loading'

const scenes = ref([])
const loading = ref(true)
const loadError = ref(false)
const failedCovers = ref(new Set())
const sceneIcon = scene => scene.mode === 'interview' ? 'briefcase' : scene.category === 'business' ? 'messages' : scene.id.includes('airport') ? 'compass' : 'messages'
const finishLoading = usePageLoading() // 与路由遮罩同一条流程：精选场景到位后才收起
onMounted(async () => {
  try { const { data } = await listScenes(); scenes.value = (data?.items || []).slice(0, 4) }
  catch { loadError.value = true }
  finally { loading.value = false; finishLoading() }
})
</script>

<style scoped>
.home-page { flex: 1; min-height: 0; overflow-y: auto; background: #fbfaff; color: #29283e; }
.home-content { max-width: 1400px; margin: 0 auto; padding: 28px clamp(22px, 3vw, 42px) 45px; }
.top-grid { display: grid; grid-template-columns: minmax(0, 1.8fr) minmax(270px, 1fr); gap: 18px; }
.hero { position: relative; display: flex; min-height: 296px; overflow: hidden; border: 2px solid #e0d8f6; border-bottom: 6px solid #d3c8ef; border-radius: 26px; background: #eee9ff; }
.hero-copy { position: relative; z-index: 1; padding: 32px clamp(24px, 3vw, 40px); }
.eyebrow { display: inline-flex; align-items: center; gap: 8px; padding: 5px 12px 5px 5px; border-radius: 18px; background: #fff; color: #715ac1; font-size: 12px; font-weight: 700; }
.eyebrow-icon { display: grid; place-items: center; width: 29px; height: 29px; border-radius: 10px; background: #8d78de; color: #fff; }
.hero h2 { margin: 19px 0 10px; color: #2d294b; font-size: clamp(24px, 2.4vw, 34px); line-height: 1.25; font-weight: 800; }
.hero p { margin: 0; color: #706d85; font-size: 14px; line-height: 1.8; }
.primary-button { display: inline-flex; align-items: center; justify-content: center; gap: 12px; min-width: 160px; min-height: 46px; margin-top: 21px; padding: 0 19px; border: 2px solid #8067d1; border-bottom: 5px solid #6951b8; border-radius: 15px; background: #8b73dd; color: #fff; font-size: 14px; font-weight: 750; text-decoration: none; transition: transform .15s, background .15s; }
.primary-button .btn-arrow { transition: transform .18s cubic-bezier(.22, .8, .32, 1); }
.primary-button:hover { background: #7d64d1; transform: translateY(-2px); }.primary-button:hover .btn-arrow { transform: translateX(3px); }.primary-button:active { transform: translateY(2px); border-bottom-width: 3px; margin-top: 23px; }
.hero-illustration { position: absolute; bottom: -4px; right: -2px; width: 51%; height: 96%; object-fit: contain; object-position: right bottom; pointer-events: none; }
.hero-doodle { position: absolute; z-index: 1; color: #e7ad57; pointer-events: none; }.doodle-one { top: 25px; right: 35%; font-size: 22px; }.doodle-two { right: 4%; top: 28px; font-size: 17px; color: #a899e5; }
.quick-links { display: grid; gap: 16px; }.quick-card { display: flex; align-items: center; gap: 16px; min-width: 0; padding: 20px; border: 2px solid #e4def5; border-bottom: 5px solid #ddd5f2; border-radius: 22px; background: #f8f5ff; color: inherit; text-decoration: none; transition: transform .16s, border-color .16s; }.quick-card.green { background: #eff9f2; border-color: #daeddf; border-bottom-color: #cce6d3; }.quick-card:hover { transform: translateY(-2px); border-color: #bcb1ee; }.quick-card:active,.scene-card:active { transform: translateY(1px); }
.quick-icon { display: grid; place-items: center; flex: 0 0 64px; width: 64px; height: 64px; border-radius: 22px; }.feature-icon { width: 50px; height: 50px; transition: transform .2s ease; }.quick-card:hover .feature-icon { transform: rotate(-6deg) scale(1.05); }.purple { background: #e8e2fc; color: #826bdc; }.mint { background: #def3e6; color: #35a876; }.quick-copy { flex: 1; min-width: 0; }.quick-copy b,.quick-copy small { display: block; }.quick-copy b { font-size: 17px; font-weight: 750; }.quick-copy small { margin-top: 7px; color: #7f7c90; font-size: 12.5px; line-height: 1.6; }.quick-arrow,.scene-arrow { display: grid; place-items: center; flex: 0 0 34px; width: 34px; height: 34px; border: 1.5px solid #dfd9f0; border-bottom: 3px solid #d4c9ed; border-radius: 12px; background: white; color: #806bd4; transition: transform .16s cubic-bezier(.22, .8, .32, 1), background .15s, border-color .15s; }
.quick-card:hover .quick-arrow,.scene-card:hover .scene-arrow { transform: translateX(3px); background: #f3efff; border-color: #c8bbf0; }
.featured { margin-top: 32px; }.section-heading,.section-heading > div { display: flex; align-items: center; gap: 12px; }.section-heading { justify-content: space-between; margin-bottom: 17px; }.section-icon { color: #8065d9; }.section-heading h2 { margin: 0; font-size: 19px; font-weight: 800; white-space: nowrap; }.section-heading p { margin: 0; color: #858195; font-size: 12.5px; }.section-heading > a { display: flex; align-items: center; gap: 6px; color: #795fd0; font-size: 12.5px; font-weight: 700; text-decoration: none; white-space: nowrap; }
.scene-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 15px; }.scene-card { overflow: hidden; border: 2px solid #eae7f2; border-bottom: 5px solid #e3dfed; border-radius: 20px; background: white; color: inherit; text-decoration: none; transition: transform .16s, border-color .16s; }.scene-card:hover { transform: translateY(-4px); border-color: #c9bdf0; }
.scene-art { position: relative; display: grid; place-items: center; height: 96px; overflow: hidden; background: #e6efff; color: #7799d6; }.scene-art img { width: 100%; height: 100%; object-fit: cover; transition: transform .28s cubic-bezier(.22, .8, .32, 1); }.scene-card:hover .scene-art img { transform: scale(1.04); }.scene-art > svg { z-index: 1; transition: transform .22s cubic-bezier(.22, .8, .32, 1); }.scene-card:hover .scene-art > svg { transform: scale(1.08) rotate(-3deg); }.tone-1 { background: #f9ede2; color: #c79264; }.tone-2 { background: #e8f4e9; color: #6ba27b; }.tone-3 { background: #ece9fa; color: #9180c9; }.scene-art-circle { position: absolute; width: 115px; height: 115px; border-radius: 50%; background: #ffffff80; transition: transform .25s ease; }.scene-card:hover .scene-art-circle { transform: scale(1.06); }.scene-art-dot { position: absolute; width: 30px; height: 30px; right: 14%; top: 12px; border-radius: 50%; background: #ffffff80; transition: transform .25s ease; }.scene-card:hover .scene-art-dot { transform: translate(-4px, 3px); }
.scene-body { display: flex; justify-content: space-between; align-items: center; gap: 8px; min-height: 111px; padding: 12px 14px; }.scene-body > div { min-width: 0; }.scene-tag { display: inline-block; margin-bottom: 6px; color: #8b7bc5; font-size: 10px; font-weight: 700; }.scene-body h3 { margin: 0; font-size: 13px; line-height: 1.4; font-weight: 750; }.scene-body p { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; margin: 5px 0 0; color: #898596; font-size: 11px; line-height: 1.5; }
.scene-message { padding: 26px; border: 1px solid #e9e7f1; border-radius: 16px; background: #fff; color: #858195; font-size: 13px; }
.plan-banner { display: flex; align-items: center; gap: 18px; margin-top: 30px; padding: 20px 24px; border: 1px solid #e7e3f4; border-radius: 18px; background: #f8f7ff; }.plan-icon { display: grid; place-items: center; flex: 0 0 56px; width: 56px; height: 56px; border-radius: 18px; background: #ede9fc; color: #8a73de; }.plan-title { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }.plan-title h2 { margin: 0; font-size: 16px; font-weight: 800; }.plan-title span { padding: 4px 9px; border-radius: 12px; background: #e8e2fc; color: #745dca; font-size: 11px; font-weight: 700; }.plan-banner p { margin: 6px 0 0; color: #858195; font-size: 12.5px; line-height: 1.6; }
a:focus-visible { outline: 3px solid #786bd1; outline-offset: 3px; }
@media (prefers-reduced-motion: no-preference) {
  .hero-copy { animation: gentle-in .45s cubic-bezier(.22, .8, .32, 1) both; }
  .hero-illustration { animation: gentle-in .55s cubic-bezier(.22, .8, .32, 1) .06s both; }
  .quick-card:nth-child(1) { animation: gentle-in .45s cubic-bezier(.22, .8, .32, 1) .07s both; }
  .quick-card:nth-child(2) { animation: gentle-in .45s cubic-bezier(.22, .8, .32, 1) .14s both; }
  .scene-card { animation: card-in .42s cubic-bezier(.22, .8, .32, 1) backwards; }
  .plan-banner { animation: gentle-in .45s cubic-bezier(.22, .8, .32, 1) .2s both; }
  .doodle-one { animation: doodle-float 4.6s ease-in-out infinite; }
  .doodle-two { animation: doodle-float 5.4s ease-in-out 1.2s infinite; }
  @keyframes gentle-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
  @keyframes card-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
  @keyframes doodle-float { 0%, 100% { transform: translateY(0) rotate(0deg); } 50% { transform: translateY(-4px) rotate(6deg); } }
}
@media (prefers-reduced-motion: reduce) {
  .primary-button, .primary-button .btn-arrow, .quick-card, .feature-icon, .quick-arrow, .scene-card, .scene-arrow, .scene-art img, .scene-art > svg, .scene-art-circle, .scene-art-dot { transition: none; }
  .primary-button:hover, .primary-button:hover .btn-arrow, .quick-card:hover, .quick-card:hover .feature-icon, .quick-card:hover .quick-arrow, .scene-card:hover, .scene-card:hover .scene-arrow, .scene-card:hover .scene-art img, .scene-card:hover .scene-art > svg, .scene-card:hover .scene-art-circle, .scene-card:hover .scene-art-dot { transform: none; }
}
@media (max-width: 1050px) { .top-grid { grid-template-columns: 1fr; }.quick-links { grid-template-columns: repeat(2, 1fr); }.quick-card { min-height: 105px; }.scene-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 900px) { .quick-links { grid-template-columns: 1fr; }.quick-card { min-height: 88px; } }
@media (max-width: 650px) { .home-content { padding: 18px 16px 32px; }.hero { min-height: 250px; }.hero-copy { padding: 23px; }.hero-illustration { width: 45%; opacity: .65; }.hero h2 { font-size: 23px; }.hero p { font-size: 12px; }.quick-links { grid-template-columns: 1fr; }.quick-card { min-height: 88px; padding: 14px; }.section-heading p { display: none; }.section-heading h2 { font-size: 17px; }.scene-grid { gap: 10px; }.scene-body { align-items: start; }.scene-arrow { display: none; }.plan-banner { padding: 16px; } }
</style>

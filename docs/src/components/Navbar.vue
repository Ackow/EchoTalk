<template>
  <nav class="navbar">
    <router-link to="/" class="nav-brand">
      <span>🎙️</span>
      <span class="gradient-text">EchoTalk</span>
    </router-link>
    <div class="nav-links">
      <router-link to="/#features">产品特性</router-link>
      <router-link to="/docs">产品文档</router-link>
      <router-link to="/community">场景社区</router-link>
    </div>
    <a class="nav-cta" href="https://github.com/Ackow/EchoTalk/releases" target="_blank">⬇ 下载客户端</a>
  </nav>
</template>
<style scoped>
.navbar { position: fixed; top: 0; left: 0; right: 0; z-index: 100; display: flex; align-items: center; justify-content: space-between; padding: 0 48px; height: 76px; background: rgba(8,12,20,0.8); backdrop-filter: blur(20px); border-bottom: 1px solid var(--border); }
.nav-brand { display: flex; align-items: center; gap: 10px; font-weight: 800; font-size: 1.45rem; }
.nav-links { display: flex; gap: 36px; }
.nav-links a { font-size: 1.05rem; font-weight: 500; color: var(--text-muted); transition: color 0.2s; }
.nav-links a:hover { color: var(--text); }
.nav-links a.router-link-exact-active { color: var(--text); }
.nav-cta { display: inline-flex; align-items: center; gap: 8px; padding: 10px 24px; border-radius: 10px; font-size: 1rem; font-weight: 600; background: linear-gradient(135deg, var(--primary), var(--blue)); color: #fff; transition: transform 0.15s, box-shadow 0.2s; }
.nav-cta:hover { transform: translateY(-1px); box-shadow: 0 6px 24px var(--primary-glow); }
@media (max-width: 768px) { .navbar { padding: 0 20px; } .nav-links { display: none; } }
</style>
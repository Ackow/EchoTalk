<template>
  <nav class="navbar">
    <router-link to="/" class="nav-brand">
      <img src="/images/brand.png" alt="EchoTalk" class="brand-img" />
      <span class="gradient-text">EchoTalk</span>
      <span class="brand-ver">2.0</span>
    </router-link>
    <div class="nav-links">
      <router-link to="/">产品介绍</router-link>
      <router-link to="/features">核心特性</router-link>
      <router-link to="/pricing">订阅方案</router-link>
      <router-link to="/community">场景社区</router-link>
      <router-link to="/docs">产品文档</router-link>
    </div>
    <a class="nav-cta" href="https://github.com/Ackow/EchoTalk/releases" target="_blank">下载桌面端</a>
  </nav>
</template>

<style scoped>
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 42px;
  height: 72px;
  background: rgba(251, 250, 255, 0.88);
  backdrop-filter: blur(16px);
  border-bottom: 1.5px solid var(--border);
}
.nav-brand {
  display: flex;
  align-items: center;
  gap: 9px;
  font-weight: 800;
  font-size: 20px;
}
.brand-img {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  object-fit: cover;
}
.brand-ver {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 999px;
  background: #eee9ff;
  color: #6046b4;
}
.nav-links {
  display: flex;
  gap: 28px;
}
.nav-links a {
  font-size: 14.5px;
  font-weight: 600;
  color: var(--text-muted);
  padding: 6px 2px;
  border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
}
.nav-links a:hover,
.nav-links a.router-link-exact-active {
  color: var(--primary-ink);
  border-bottom-color: var(--primary);
}
.nav-cta {
  display: inline-flex;
  align-items: center;
  padding: 8px 18px;
  border-radius: 11px;
  font-size: 13.5px;
  font-weight: 700;
  background: var(--primary);
  border: 1.5px solid #8067d1;
  border-bottom: 3px solid var(--primary-deep);
  color: #ffffff;
  transition: transform 0.15s, background 0.15s;
}
.nav-cta:hover {
  background: #7e65d2;
  transform: translateY(-1px);
}
@media (max-width: 860px) {
  .navbar { padding: 0 20px; }
  .nav-links { display: none; }
}
</style>

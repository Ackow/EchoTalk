<template>
  <footer class="footer">
    <div class="footer-brand gradient-text">EchoTalk 2.0</div>
    <p>全链路 AI 英语口语与听力训练平台 · 1v1 语音对话 · 1vN 多角色群面/辩论 · 双引擎知识图谱</p>
    <div class="footer-links">
      <a href="https://github.com/Ackow/EchoTalk" target="_blank">GitHub 仓库</a>
      <router-link to="/docs">产品文档</router-link>
      <router-link to="/community">场景社区</router-link>
      <a href="https://github.com/Ackow/EchoTalk/releases" target="_blank">下载客户端</a>
    </div>
  </footer>
</template>

<style>
.footer {
  padding: 48px 24px 36px;
  text-align: center;
  border-top: 1.5px solid var(--border);
  max-width: 1200px;
  margin: 0 auto;
}
.footer-brand {
  font-weight: 800;
  font-size: 20px;
  margin-bottom: 8px;
}
.footer p {
  font-size: 13.5px;
  color: var(--text-dim);
  margin-bottom: 18px;
}
.footer-links {
  display: flex;
  gap: 24px;
  justify-content: center;
  flex-wrap: wrap;
}
.footer-links a {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-muted);
  transition: color 0.15s;
}
.footer-links a:hover {
  color: var(--primary-ink);
}
</style>

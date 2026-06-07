<template>
  <footer class="footer">
    <div class="footer-brand gradient-text">EchoTalk</div>
    <p>AI 英语口语练习平台 · Version 1.0.0</p>
    <div class="footer-links">
      <a href="https://github.com/Ackow/EchoTalk" target="_blank">GitHub</a>
      <a href="https://www.bilibili.com/video/BVxxxxxx" target="_blank">Bilibili 演示</a>
      <a href="https://github.com/Ackow/EchoTalk/releases" target="_blank">下载客户端</a>
    </div>
  </footer>
</template>
<style>
.footer { padding: 52px 24px 36px; text-align: center; border-top: 1px solid var(--border); max-width: 1200px; margin: 0 auto; }
.footer-brand { font-weight: 800; font-size: 1.25rem; margin-bottom: 10px; }
.footer p { font-size: 0.92rem; color: var(--text-dim); margin-bottom: 20px; }
.footer-links { display: flex; gap: 28px; justify-content: center; flex-wrap: wrap; }
.footer-links a { font-size: 0.88rem; color: var(--text-muted); transition: color 0.2s; }
.footer-links a:hover { color: var(--primary); }
</style>
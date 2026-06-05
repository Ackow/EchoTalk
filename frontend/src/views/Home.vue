<template>
  <div class="home-container">
    <header class="hero-section">
      <h1 class="text-gradient logo-text">EchoTalk</h1>
      <p class="subtitle">云音口语 · 沉浸式英语口语AI练习平台</p>
    </header>

    <div class="scenes-grid">
      <div class="scene-card glass-card">
        <h3>场景选择载入中...</h3>
        <p>Phase 1 初始化中，后续阶段将实现热插拔场景卡片。</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-container {
  padding: 40px;
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.hero-section {
  text-align: center;
  margin-bottom: 60px;
}

.logo-text {
  font-size: 4rem;
  font-family: var(--font-display);
  font-weight: 800;
  margin-bottom: 10px;
}

.subtitle {
  font-size: 1.2rem;
  color: var(--text-secondary);
  letter-spacing: 0.05em;
}

.scenes-grid {
  width: 100%;
  max-width: 1000px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
}

.scene-card {
  padding: 30px;
  text-align: center;
}

.scene-card h3 {
  margin-bottom: 12px;
  color: var(--text-primary);
}

.scene-card p {
  color: var(--text-muted);
  font-size: 0.9rem;
  line-height: 1.6;
}
</style>

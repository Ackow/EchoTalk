<template>
  <div class="practice-container">
    <div class="glass-panel main-panel">
      <h2>口语实战演练</h2>
      <p class="desc">实时语音对话、波形动画与发音纠错面板加载中...</p>
      <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
    </div>
  </div>
</template>

<style scoped>
.practice-container {
  padding: 40px;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}
.main-panel {
  padding: 40px;
  text-align: center;
  max-width: 600px;
  width: 100%;
}
h2 {
  margin-bottom: 16px;
  color: var(--text-primary);
}
.desc {
  color: var(--text-secondary);
  margin-bottom: 24px;
}
</style>

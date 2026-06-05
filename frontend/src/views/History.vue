<template>
  <div class="history-container">
    <div class="glass-panel main-panel">
      <h2>对话历史 & 云端回放</h2>
      <p class="desc">往期口语练习的录音以及打分报告加载中...</p>
      <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
    </div>
  </div>
</template>

<style scoped>
.history-container {
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

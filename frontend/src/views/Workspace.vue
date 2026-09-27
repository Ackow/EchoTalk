<template>
  <!-- 今日训练首页：训练计划接入后端前保持安静的空状态，不做装饰性占位。 -->
  <section class="home-state">
    <div class="home-icon"><AppIcon name="logo" :size="24" /></div>
    <h2>今天从一次短练习开始</h2>
    <p>训练计划将根据你的目标与最近表现生成。账户与个人数据已就绪，各训练模块按 2.0 设计稿分阶段接入。</p>
  </section>
</template>

<script setup>
import AppIcon from '../components/AppIcon.vue'
</script>

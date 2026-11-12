<template>
  <!-- 布局由路由结构决定：/login 全屏，其余路由在 AppShell 壳层内渲染。 -->
  <router-view />
  <!-- 全局加载遮罩：路由切换、长流程加载时覆盖整个窗口 -->
  <AppLoading />
</template>

<script setup>
import AppLoading from './components/AppLoading.vue'
</script>

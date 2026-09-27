<template>
  <!-- 模块占位页：诚实标注"规划中"，不伪装可用的操作。 -->
  <section class="module-placeholder">
    <p class="placeholder-desc">{{ route.meta.desc }}</p>
    <p class="placeholder-note">该模块在 2.0 设计稿中已定稿，将随对应后端能力一起开放。</p>
    <router-link class="placeholder-back" :to="{ name: 'workspace' }">
      <AppIcon name="chevron-left" :size="13" />返回今日训练
    </router-link>
  </section>
</template>

<script setup>
import { useRoute } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'

const route = useRoute()
</script>

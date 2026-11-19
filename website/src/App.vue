<template>
  <div class="app-wrapper">
    <Navbar />
    <div ref="progressRef" class="scroll-progress-bar" aria-hidden="true"></div>
    <main class="main-content">
      <router-view v-slot="{ Component, route }">
        <transition name="page-fade" mode="out-in">
          <component :is="Component" :key="route.path" />
        </transition>
      </router-view>
    </main>
    <AppFooter />
  </div>
</template>
<script setup>
import { ref } from 'vue'
import Navbar from './components/Navbar.vue'
import AppFooter from './components/AppFooter.vue'
import { useScrollProgress } from './composables/useScrollReveal.js'

const progressRef = ref(null)
useScrollProgress(progressRef)
</script>
<style>
.app-wrapper { display: flex; flex-direction: column; min-height: 100vh; }
.main-content { flex: 1; padding-top: 76px; }
</style>

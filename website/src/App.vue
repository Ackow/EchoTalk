<template>
  <div class="app-wrapper">
    <Navbar />
    <div ref="progressRef" class="scroll-progress-bar" aria-hidden="true"></div>
    <main class="main-content">
      <router-view v-slot="{ Component, route }">
        <transition name="page-fade" mode="out-in" @after-enter="onPageAfterEnter">
          <component :is="Component" :key="route.path" />
        </transition>
      </router-view>
    </main>
    <AppFooter />
  </div>
</template>
<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import Navbar from './components/Navbar.vue'
import AppFooter from './components/AppFooter.vue'
import {
  getLenis,
  initSmoothScroll,
  scrollToTopImmediate,
  useScrollProgress,
} from './composables/useScrollReveal.js'

const progressRef = ref(null)
useScrollProgress(progressRef)

const route = useRoute()
let destroySmoothScroll = () => {}

onMounted(() => {
  destroySmoothScroll = initSmoothScroll()
})

onBeforeUnmount(() => {
  destroySmoothScroll()
})

watch(
  () => route.fullPath,
  () => {
    if (!route.hash) {
      scrollToTopImmediate()
    }
  }
)

function onPageAfterEnter() {
  nextTick(() => {
    if (route.hash) {
      const lenis = getLenis()
      if (lenis) {
        lenis.scrollTo(route.hash, { offset: -84 })
      }
    }
    ScrollTrigger.refresh()
  })
}
</script>
<style>
.app-wrapper { display: flex; flex-direction: column; min-height: 100vh; }
.main-content { flex: 1; padding-top: 76px; }
</style>

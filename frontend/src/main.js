// 应用入口：挂载 Vue 根组件和路由。
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './assets/styles.css' // 全局样式

// 标记运行平台，CSS 据此处理 macOS 红绿灯留白等差异；浏览器环境无此标记。
document.documentElement.dataset.platform = window.electronAPI?.platform || ''

createApp(App).use(router).mount('#app') // 只装路由，无其他全局插件

// 首屏遮罩退场：等首帧绘制后再淡出，避免 Vue 内容与遮罩之间出现空档
const bootMask = document.getElementById('boot')
if (bootMask) {
  requestAnimationFrame(() => {
    bootMask.classList.add('boot-out')
    setTimeout(() => bootMask.remove(), 260) // 与 boot.css 的 .22s 过渡对齐
  })
}

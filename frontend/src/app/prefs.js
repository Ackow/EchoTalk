// 本机界面偏好：跨组件共享 + 写 localStorage，设置弹窗与侧栏共用同一份状态。
import { ref, watch } from 'vue'

const SIDEBAR_KEY = 'echotalk:sidebar-collapsed' // 侧边栏收起偏好

export const sidebarHidden = ref(localStorage.getItem(SIDEBAR_KEY) === '1') // 初始沿用上次选择

watch(sidebarHidden, (value) => localStorage.setItem(SIDEBAR_KEY, value ? '1' : '0'))

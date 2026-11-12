// 全局加载遮罩状态：路由切换与手动流程共用，带延迟显示与最短停留，避免一闪而过。
import { onBeforeUnmount, ref } from 'vue'

const SHOW_DELAY = 140 // 快于此耗时的操作不弹遮罩，防止闪烁
const MIN_VISIBLE = 240 // 一旦显示，至少停留这么久，动画不会抽搐
const PAGE_TIMEOUT = 8000 // 页面级兜底：接口挂起或流程漏收时也把遮罩收回，不卡死界面

export const loadingVisible = ref(false)
export const loadingText = ref('')

let pending = 0 // 并发计数：并行的加载流程只显示一次遮罩
let showTimer = null
let hideTimer = null
let shownAt = 0

// 开始一个加载流程；text 为空时沿用上一次文案，immediate 用于已知会慢、需要立刻盖住的场景
export function beginLoading(text = '', immediate = false) {
  pending += 1
  if (text) loadingText.value = text
  if (hideTimer) {
    clearTimeout(hideTimer) // 正在退场又被重新唤起：取消隐藏，保持连续
    hideTimer = null
  }
  if (loadingVisible.value) return
  if (immediate) {
    if (showTimer) {
      clearTimeout(showTimer)
      showTimer = null
    }
    loadingVisible.value = true
    shownAt = Date.now()
    return
  }
  if (showTimer) return
  showTimer = setTimeout(() => {
    showTimer = null
    if (pending <= 0) return
    loadingVisible.value = true
    shownAt = Date.now()
  }, SHOW_DELAY)
}

// 结束一个加载流程；计数归零后按最短停留时间收尾
export function endLoading() {
  if (pending > 0) pending -= 1
  if (pending > 0) return
  if (showTimer) {
    clearTimeout(showTimer) // 还没显示就结束了：直接取消，不留下一次闪现
    showTimer = null
  }
  if (!loadingVisible.value) return
  const wait = Math.max(0, MIN_VISIBLE - (Date.now() - shownAt))
  hideTimer = setTimeout(() => {
    hideTimer = null
    if (pending === 0) {
      loadingVisible.value = false
      loadingText.value = ''
    }
  }, wait)
}

// 页面级加载：在 setup 中调用，让「路由切换 → 首屏数据到位」共用一次遮罩，
// 不会出现遮罩先收起、骨架屏再补上来的两段跳。数据到位后调用返回的 finish 收起。
export function usePageLoading(text = '', immediate = false) {
  // 首屏启动时 #boot 还没撤：立刻续上同一套视觉，避免中间漏出空白骨架
  beginLoading(text, immediate || Boolean(document.getElementById('boot')))
  let finished = false
  let timer = null
  function finish() {
    if (finished) return
    finished = true
    clearTimeout(timer)
    endLoading() // 计数归还；提前离开页面时也不留下悬挂的遮罩
  }
  timer = setTimeout(finish, PAGE_TIMEOUT)
  onBeforeUnmount(finish)
  return finish
}

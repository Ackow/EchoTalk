import { onBeforeUnmount, onMounted } from 'vue'

/**
 * Progressive-enhancement scroll progress indicator fallback.
 * Native CSS `animation-timeline: scroll(root)` handles supporting browsers;
 * this runs only when CSS scroll-timeline is unsupported and user allows motion.
 */
export function useScrollProgress(barRef) {
  let rafId = 0
  let active = false

  function update() {
    rafId = 0
    const el = barRef.value
    if (!el) return
    const scrollable = document.documentElement.scrollHeight - window.innerHeight
    const ratio = scrollable > 0 ? Math.min(1, Math.max(0, window.scrollY / scrollable)) : 0
    el.style.transform = `scaleX(${ratio})`
  }

  function onScroll() {
    if (!rafId) {
      rafId = window.requestAnimationFrame(update)
    }
  }

  onMounted(() => {
    if (typeof window === 'undefined') return
    if (
      !CSS.supports('animation-timeline', 'scroll()') &&
      window.matchMedia('(prefers-reduced-motion: no-preference)').matches
    ) {
      active = true
      update()
      window.addEventListener('scroll', onScroll, { passive: true })
    }
  })

  onBeforeUnmount(() => {
    if (active) {
      window.removeEventListener('scroll', onScroll)
    }
    if (rafId) {
      window.cancelAnimationFrame(rafId)
    }
  })
}

/**
 * Progressive-enhancement scroll entry & exit fallback via IntersectionObserver.
 * Native CSS `animation-timeline: view()` handles supporting browsers;
 * toggles `.is-visible` so elements fade in when entering and fade out when leaving.
 */
export function useScrollReveal(containerRef) {
  let observer = null

  onMounted(() => {
    if (typeof window === 'undefined') return
    const root = containerRef.value
    if (!root) return

    if (
      !CSS.supports('(animation-timeline: view()) and (animation-range: entry)') &&
      window.matchMedia('(prefers-reduced-motion: no-preference)').matches
    ) {
      root.classList.add('js-reveal-ready')
      const targets = root.querySelectorAll('[data-reveal], [data-reveal-left], [data-reveal-right]')

      observer = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            entry.target.classList.toggle('is-visible', entry.isIntersecting)
          }
        },
        {
          threshold: 0.14,
          rootMargin: '-24px 0px -24px 0px',
        }
      )

      targets.forEach((el) => observer.observe(el))
    }
  })

  onBeforeUnmount(() => {
    if (observer) {
      observer.disconnect()
      observer = null
    }
  })
}

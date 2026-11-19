import { onBeforeUnmount, onMounted } from 'vue'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import Lenis from 'lenis'

let lenisInstance = null

/**
 * Initializes global Lenis smooth scrolling synchronized with GSAP ScrollTrigger.
 * Respects `prefers-reduced-motion: reduce` and returns a clean destroy callback.
 */
export function initSmoothScroll() {
  if (typeof window === 'undefined') return () => {}

  gsap.registerPlugin(ScrollTrigger)

  if (!window.matchMedia('(prefers-reduced-motion: no-preference)').matches) {
    return () => {}
  }

  if (lenisInstance) {
    return () => {}
  }

  const lenis = new Lenis({
    duration: 1.05,
    easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    smoothWheel: true,
    wheelMultiplier: 0.95,
  })

  lenisInstance = lenis
  lenis.on('scroll', ScrollTrigger.update)

  const tick = (time) => {
    lenis.raf(time * 1000)
  }

  gsap.ticker.add(tick)
  gsap.ticker.lagSmoothing(0)

  return () => {
    gsap.ticker.remove(tick)
    lenis.off('scroll', ScrollTrigger.update)
    lenis.destroy()
    if (lenisInstance === lenis) {
      lenisInstance = null
    }
  }
}

export function getLenis() {
  return lenisInstance
}

export function stopSmoothScroll() {
  if (lenisInstance) {
    lenisInstance.stop()
  }
}

export function startSmoothScroll() {
  if (lenisInstance) {
    lenisInstance.start()
  }
}

export function scrollToTopImmediate() {
  if (typeof window === 'undefined') return
  if (lenisInstance) {
    lenisInstance.scrollTo(0, { immediate: true })
  } else {
    window.scrollTo(0, 0)
  }
}

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
 * Preserved for backward compatibility on Features.vue and other views.
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

import { onBeforeUnmount, onMounted } from 'vue'

/**
 * Adds subtle pointer-following radial spotlight (--mx, --my, --spot-opacity)
 * and gentle 3D tilt (--rx, --ry clamped to ±3deg) to `.spotlight-card` elements.
 * Automatically disabled on touch devices and when `prefers-reduced-motion: reduce`.
 */
export function useCardSpotlight(containerRef, selector = '.spotlight-card') {
  const cleanups = []

  onMounted(() => {
    if (typeof window === 'undefined') return
    const root = containerRef.value
    if (!root) return

    const canHover = window.matchMedia('(hover: hover) and (pointer: fine)').matches
    const allowsMotion = window.matchMedia('(prefers-reduced-motion: no-preference)').matches
    if (!canHover || !allowsMotion) return

    const cards = root.querySelectorAll(selector)
    cards.forEach((card) => {
      let rafId = 0
      let lastX = 0
      let lastY = 0

      function apply() {
        rafId = 0
        const rect = card.getBoundingClientRect()
        if (!rect.width || !rect.height) return

        const x = lastX - rect.left
        const y = lastY - rect.top
        const nx = Math.max(-1, Math.min(1, (x / rect.width) * 2 - 1))
        const ny = Math.max(-1, Math.min(1, (y / rect.height) * 2 - 1))

        card.style.setProperty('--mx', `${x.toFixed(1)}px`)
        card.style.setProperty('--my', `${y.toFixed(1)}px`)
        card.style.setProperty('--spot-opacity', '1')
        card.style.setProperty('--rx', `${(-ny * 3).toFixed(2)}deg`)
        card.style.setProperty('--ry', `${(nx * 3).toFixed(2)}deg`)
      }

      function onPointerMove(e) {
        lastX = e.clientX
        lastY = e.clientY
        if (!rafId) {
          rafId = window.requestAnimationFrame(apply)
        }
      }

      function onPointerLeave() {
        if (rafId) {
          window.cancelAnimationFrame(rafId)
          rafId = 0
        }
        card.style.setProperty('--spot-opacity', '0')
        card.style.setProperty('--rx', '0deg')
        card.style.setProperty('--ry', '0deg')
      }

      card.addEventListener('pointermove', onPointerMove, { passive: true })
      card.addEventListener('pointerleave', onPointerLeave, { passive: true })

      cleanups.push(() => {
        if (rafId) {
          window.cancelAnimationFrame(rafId)
          rafId = 0
        }
        card.removeEventListener('pointermove', onPointerMove)
        card.removeEventListener('pointerleave', onPointerLeave)
      })
    })
  })

  onBeforeUnmount(() => {
    while (cleanups.length) {
      const fn = cleanups.pop()
      fn()
    }
  })
}

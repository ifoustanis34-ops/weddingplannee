import { type MaybeRefOrGetter, onBeforeUnmount, ref, toValue, watch } from 'vue'

const DURATION = 600

function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
    ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
    : false
}

/**
 * Number rolling up to its value in 600 ms (reservations-stock.md §8), from the previous value
 * when it changes. Immediate when the user prefers reduced motion or outside a browser.
 */
export function useCountUp(target: MaybeRefOrGetter<number | null | undefined>) {
  const current = ref(0)
  let frame = 0

  const run = (to: number) => {
    cancelAnimationFrame(frame)
    if (prefersReducedMotion() || typeof requestAnimationFrame !== 'function') {
      current.value = to
      return
    }
    const from = current.value
    const started = performance.now()
    const step = (now: number) => {
      const t = Math.min(1, (now - started) / DURATION)
      const eased = 1 - (1 - t) ** 3
      current.value = Math.round(from + (to - from) * eased)
      if (t < 1) frame = requestAnimationFrame(step)
    }
    frame = requestAnimationFrame(step)
  }

  watch(
    () => toValue(target) ?? 0,
    (value) => run(value),
    { immediate: true },
  )
  onBeforeUnmount(() => cancelAnimationFrame(frame))
  return current
}

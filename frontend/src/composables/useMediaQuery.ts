import { onBeforeUnmount, ref, type Ref } from 'vue'

/** Reactive `matchMedia` (false where it is unavailable, e.g. in unit tests). */
export function useMediaQuery(query: string): Ref<boolean> {
  const list = typeof window !== 'undefined' && window.matchMedia ? window.matchMedia(query) : null
  const matches = ref(list?.matches ?? false)
  const update = (event: MediaQueryListEvent) => (matches.value = event.matches)
  list?.addEventListener('change', update)
  onBeforeUnmount(() => list?.removeEventListener('change', update))
  return matches
}

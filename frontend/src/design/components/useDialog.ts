import { type Ref, nextTick, onBeforeUnmount, watch } from 'vue'

const FOCUSABLE =
  'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])'

let openDialogs = 0

/** Escape to close, focus trap, focus restore and body scroll lock for drawers and modals. */
export function useDialog(open: Ref<boolean>, panel: Ref<HTMLElement | null>, close: () => void) {
  let previouslyFocused: HTMLElement | null = null

  function onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      event.stopPropagation()
      close()
      return
    }
    if (event.key !== 'Tab' || !panel.value) return
    const items = [...panel.value.querySelectorAll<HTMLElement>(FOCUSABLE)]
    const first = items[0]
    const last = items[items.length - 1]
    if (!first || !last) return
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }

  function lock(locked: boolean): void {
    openDialogs = Math.max(0, openDialogs + (locked ? 1 : -1))
    document.body.style.overflow = openDialogs > 0 ? 'hidden' : ''
  }

  watch(
    open,
    async (isOpen, wasOpen) => {
      if (isOpen) {
        previouslyFocused = document.activeElement as HTMLElement | null
        lock(true)
        await nextTick()
        const target =
          panel.value?.querySelector<HTMLElement>('[autofocus]') ??
          panel.value?.querySelector<HTMLElement>(FOCUSABLE) ??
          panel.value
        target?.focus()
      } else if (wasOpen) {
        lock(false)
        previouslyFocused?.focus()
      }
    },
    { immediate: true },
  )

  onBeforeUnmount(() => {
    if (open.value) lock(false)
  })

  return { onKeydown }
}

import { computed, useAttrs } from 'vue'

/**
 * Form controls render a wrapper (label, hint, error) around the native element: `class` and
 * `style` style the wrapper (layout), every other attribute goes to the native control.
 */
export function useFieldAttrs() {
  const attrs = useAttrs()
  const rootAttrs = computed(() => ({ class: attrs.class, style: attrs.style }))
  const controlAttrs = computed(() =>
    Object.fromEntries(Object.entries(attrs).filter(([key]) => key !== 'class' && key !== 'style')),
  )
  return { rootAttrs, controlAttrs }
}

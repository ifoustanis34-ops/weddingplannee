import { readonly, ref } from 'vue'

export type ToastTone = 'success' | 'error' | 'info'

export interface Toast {
  id: number
  tone: ToastTone
  message: string
}

const toasts = ref<Toast[]>([])
let nextId = 1
const DURATION_MS = 3600

function dismiss(id: number): void {
  toasts.value = toasts.value.filter((toast) => toast.id !== id)
}

function push(tone: ToastTone, message: string): number {
  const id = nextId++
  toasts.value = [...toasts.value.slice(-3), { id, tone, message }]
  setTimeout(() => dismiss(id), tone === 'error' ? DURATION_MS * 2 : DURATION_MS)
  return id
}

/** App-wide notifications rendered by <WToast /> in an aria-live region. */
export function useToast() {
  return {
    toasts: readonly(toasts),
    success: (message: string) => push('success', message),
    error: (message: string) => push('error', message),
    info: (message: string) => push('info', message),
    dismiss,
  }
}

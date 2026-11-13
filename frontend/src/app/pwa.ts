import type { QueryClient } from '@tanstack/vue-query'
import { ref } from 'vue'

import { api } from '@/api/client'

/**
 * Installable app and Web Push (feedback 13/11/2026).
 *
 * - The service worker (`public/sw.js`) is registered on every page; in development it only
 *   handles push (`?dev=1`, no cache, so Vite's modules are never served stale).
 * - « Installer l'application »: Chrome/Android hand over `beforeinstallprompt`; iOS has no such
 *   event, the profile explains « Partager → Sur l'écran d'accueil ».
 * - Push: the server gives its VAPID public key, the browser subscribes, the server stores the
 *   subscription of this device and sends notifications from then on.
 */

interface InstallPrompt extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

export const installable = ref(false)
export const installed = ref(
  typeof window !== 'undefined' &&
    (window.matchMedia?.('(display-mode: standalone)').matches ||
      (navigator as Navigator & { standalone?: boolean }).standalone === true),
)
let deferred: InstallPrompt | null = null

export const isIos = () =>
  typeof navigator !== 'undefined' && /iphone|ipad|ipod/i.test(navigator.userAgent)

export function pushSupported(): boolean {
  return (
    typeof window !== 'undefined' &&
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window
  )
}

/** Kinds of push (server `notifications.push`) → the data to refresh in an open app. */
const REFRESH: Record<string, string[][]> = {
  mission: [['staff']],
  task: [['staff']],
  alert: [['alerts'], ['dashboard']],
  payment: [['reservations'], ['dashboard'], ['billing']],
}

export function setupPwa(queryClient: QueryClient): void {
  if (typeof window === 'undefined') return
  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault()
    deferred = event as InstallPrompt
    installable.value = true
  })
  window.addEventListener('appinstalled', () => {
    installed.value = true
    installable.value = false
    deferred = null
  })
  if (!('serviceWorker' in navigator)) return
  const url = import.meta.env.DEV ? '/sw.js?dev=1' : '/sw.js'
  void navigator.serviceWorker.register(url, { scope: '/' }).catch(() => undefined)
  navigator.serviceWorker.addEventListener('message', (event: MessageEvent) => {
    const data = event.data as { type?: string; kind?: string } | null
    if (data?.type !== 'push') return
    for (const key of REFRESH[data.kind ?? ''] ?? [['alerts']])
      void queryClient.invalidateQueries({ queryKey: key })
  })
}

export async function promptInstall(): Promise<boolean> {
  if (!deferred) return false
  await deferred.prompt()
  const { outcome } = await deferred.userChoice
  deferred = null
  installable.value = false
  return outcome === 'accepted'
}

// --- Push ----------------------------------------------------------------------------------------

export interface PushConfig {
  enabled: boolean
  publicKey: string
}

export const pushApi = {
  config: () => api.get<PushConfig>('/push/config').then((r) => r.data),
  subscribe: (subscription: PushSubscriptionJSON) =>
    api.post('/push/subscriptions', subscription).then(() => undefined),
  unsubscribe: (endpoint: string) =>
    api.post('/push/subscriptions/remove', { endpoint }).then(() => undefined),
  test: () => api.post<{ sent: number }>('/push/test').then((r) => r.data),
}

/** VAPID keys travel as base64url; the browser wants the raw bytes. */
export function urlBase64ToUint8Array(value: string): Uint8Array<ArrayBuffer> {
  const padded = (value + '='.repeat((4 - (value.length % 4)) % 4))
    .replace(/-/g, '+')
    .replace(/_/g, '/')
  const raw = atob(padded)
  const bytes = new Uint8Array(new ArrayBuffer(raw.length))
  for (let i = 0; i < raw.length; i += 1) bytes[i] = raw.charCodeAt(i)
  return bytes
}

async function registration(): Promise<ServiceWorkerRegistration> {
  return navigator.serviceWorker.ready
}

export async function currentSubscription(): Promise<PushSubscription | null> {
  if (!pushSupported()) return null
  return (await registration()).pushManager.getSubscription()
}

/** Ask the permission (once), subscribe this device and register it with the server. */
export async function enablePush(): Promise<'granted' | 'denied' | 'unavailable'> {
  if (!pushSupported()) return 'unavailable'
  const config = await pushApi.config()
  if (!config.enabled) return 'unavailable'
  const permission = await Notification.requestPermission()
  if (permission !== 'granted') return 'denied'
  const reg = await registration()
  const subscription =
    (await reg.pushManager.getSubscription()) ??
    (await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(config.publicKey),
    }))
  await pushApi.subscribe(subscription.toJSON())
  return 'granted'
}

/** Stop the notifications on this device (also on sign-out: the next person gets none). */
export async function disablePush(): Promise<void> {
  const subscription = await currentSubscription().catch(() => null)
  if (!subscription) return
  await pushApi.unsubscribe(subscription.endpoint).catch(() => undefined)
  await subscription.unsubscribe().catch(() => false)
}

import type { AxiosRequestConfig, InternalAxiosRequestConfig } from 'axios'
import { computed, ref } from 'vue'

import { api } from '@/api/client'
import { ApiError } from '@/api/errors'

import { storage } from './storage'

/**
 * Changes made without connection (feedback 20/11/2026): kept on the device, sent by themselves
 * as soon as the network comes back, in the order they were made.
 *
 * A change the server refuses on its return (data changed meanwhile, rule broken) is kept aside
 * with the server's reason: the person retries or drops it from the « Hors ligne » panel.
 */
export interface PendingChange {
  id: string
  /** Who made it and in which space: replayed only for that person, in that space. */
  userId: string
  slug: string | null
  method: string
  url: string
  params?: unknown
  data?: unknown
  createdAt: string
  /** The server's reason, for a change refused on its return. */
  error?: string
}

const KEY = 'queue'
/** Never queued: session, public pages, demo switching, platform console. */
const NEVER = ['/auth/', '/public/', '/demo/', '/platform/', '/push', '/notifications']
const WRITES = new Set(['post', 'put', 'patch', 'delete'])

export const online = ref(typeof navigator === 'undefined' ? true : navigator.onLine)
const all = ref<PendingChange[]>([])
const currentUser = ref<string | null>(null)
export const syncing = ref(false)
export const pending = computed(() =>
  all.value.filter((change) => change.userId === currentUser.value && !change.error),
)
export const failed = computed(() =>
  all.value.filter((change) => change.userId === currentUser.value && change.error),
)

let onSynced: (count: number) => void = () => {}
let loaded: Promise<void> | null = null

function save(): Promise<void> {
  return storage.set(KEY, JSON.parse(JSON.stringify(all.value)))
}

function load(): Promise<void> {
  loaded ??= storage.get<PendingChange[]>(KEY).then((stored) => {
    // Changes queued before the reload come first.
    all.value = [...(stored ?? []), ...all.value.filter((c) => !stored?.some((s) => s.id === c.id))]
  })
  return loaded
}

/** Whether a failed request can wait for the network (a write the server never received). */
export function canQueue(config: InternalAxiosRequestConfig | undefined): boolean {
  if (!config || !currentUser.value) return false
  if (!WRITES.has((config.method ?? 'get').toLowerCase())) return false
  if (config.data instanceof FormData || config.data instanceof Blob) return false
  if ((config as { _replay?: boolean })._replay) return false
  return !NEVER.some((path) => config.url?.startsWith(path))
}

/** Keeps the change for later. The same change made twice (a second tap) is kept once. */
export function enqueue(config: InternalAxiosRequestConfig, slug: string | null): void {
  let data: unknown = config.data
  if (typeof data === 'string') {
    try {
      data = JSON.parse(data)
    } catch {
      // Not JSON: sent back as it is.
    }
  }
  const change: PendingChange = {
    id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    userId: currentUser.value!,
    slug,
    method: (config.method ?? 'post').toLowerCase(),
    url: config.url ?? '',
    params: config.params,
    data,
    createdAt: new Date().toISOString(),
  }
  const same = (c: PendingChange) =>
    !c.error &&
    c.userId === change.userId &&
    c.slug === change.slug &&
    c.method === change.method &&
    c.url === change.url &&
    JSON.stringify(c.data) === JSON.stringify(change.data)
  if (!all.value.some(same)) all.value = [...all.value, change]
  online.value = false
  void save()
}

/** Sends the pending changes, oldest first; stops at the first network failure. */
export async function flush(): Promise<void> {
  if (syncing.value || !currentUser.value) return
  await load()
  if (!pending.value.length) return
  syncing.value = true
  let sent = 0
  try {
    for (const change of [...pending.value]) {
      try {
        await api.request({
          method: change.method,
          url: change.url,
          params: change.params,
          data: change.data,
          headers: change.slug ? { 'X-Organization': change.slug } : {},
          _replay: true,
        } as AxiosRequestConfig)
        all.value = all.value.filter((c) => c.id !== change.id)
        sent += 1
      } catch (error) {
        if (error instanceof ApiError && error.status === 0) {
          online.value = false
          break
        }
        const reason = error instanceof Error ? error.message : String(error)
        all.value = all.value.map((c) => (c.id === change.id ? { ...c, error: reason } : c))
      }
      await save()
    }
  } finally {
    syncing.value = false
  }
  if (sent) onSynced(sent)
}

export function retry(id: string): void {
  all.value = all.value.map((c) => (c.id === id ? { ...c, error: undefined } : c))
  void save().then(flush)
}

export function discard(id: string): void {
  all.value = all.value.filter((c) => c.id !== id)
  void save()
}

export function onQueueSynced(callback: (count: number) => void): void {
  onSynced = callback
}

export function setUser(userId: string | null): void {
  currentUser.value = userId
  if (userId) void load().then(() => (online.value ? flush() : undefined))
}

/** `online` follows the browser; coming back sends what waited. */
export function watchNetwork(): void {
  if (typeof window === 'undefined') return
  void load()
  window.addEventListener('online', () => {
    online.value = true
    void flush()
  })
  window.addEventListener('offline', () => (online.value = false))
  // Some phones miss the « online » event (captive portal, flaky signal): try again regularly.
  setInterval(() => {
    if (navigator.onLine && pending.value.length && !syncing.value) {
      online.value = true
      void flush()
    }
  }, 30_000)
}

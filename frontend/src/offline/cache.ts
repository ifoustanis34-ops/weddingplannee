import { dehydrate, hydrate, type QueryClient } from '@tanstack/vue-query'

import { storage } from './storage'

/**
 * The data already seen stays readable without connection (feedback 20/11/2026): the answers of
 * the server are kept on the device for one person in one space, then shown again at the next
 * start while the network is missing. Fresh answers replace them as soon as it is back.
 */
const MAX_AGE_MS = 7 * 24 * 3600 * 1000
const PREFIX = 'cache:'

interface Saved {
  savedAt: number
  state: ReturnType<typeof dehydrate>
}

const keyOf = (userId: string, slug: string | null) => `${PREFIX}${userId}:${slug ?? '-'}`

let current: string | null = null
let timer: ReturnType<typeof setTimeout> | null = null
let unsubscribe: (() => void) | null = null

/** Restores the saved data of this person in this space, then keeps it up to date. */
export async function startCache(
  queryClient: QueryClient,
  userId: string,
  slug: string | null,
): Promise<void> {
  const key = keyOf(userId, slug)
  if (current === key) return
  stopCache()
  current = key
  const saved = await storage.get<Saved>(key)
  if (current !== key) return
  if (saved && Date.now() - saved.savedAt < MAX_AGE_MS) {
    // Older than what is already on screen: `hydrate` keeps the newer answer.
    hydrate(queryClient, saved.state)
  }
  unsubscribe = queryClient.getQueryCache().subscribe((event) => {
    if (event.type !== 'updated' || event.action.type !== 'success') return
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => void persist(queryClient, key), 1500)
  })
}

async function persist(queryClient: QueryClient, key: string): Promise<void> {
  if (current !== key) return
  const state = dehydrate(queryClient, {
    shouldDehydrateQuery: (query) => query.state.status === 'success',
  })
  await storage.set(key, { savedAt: Date.now(), state } satisfies Saved)
}

export function stopCache(): void {
  unsubscribe?.()
  unsubscribe = null
  if (timer) clearTimeout(timer)
  timer = null
  current = null
}

/** Sign-out: nothing of the agency stays on the device. */
export async function forgetCaches(): Promise<void> {
  stopCache()
  const keys = await storage.keys()
  await Promise.all(keys.filter((key) => key.startsWith(PREFIX)).map(storage.remove))
}

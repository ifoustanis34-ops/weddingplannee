/**
 * A tiny key-value store in IndexedDB for the offline mode (the query cache and the pending
 * changes can exceed what localStorage holds). Every call fails soft: without IndexedDB (private
 * window, blocked storage) the app works online as before.
 */
const DB = 'wedivo-offline'
const STORE = 'kv'

let opening: Promise<IDBDatabase | null> | null = null

function open(): Promise<IDBDatabase | null> {
  opening ??= new Promise((resolve) => {
    try {
      if (typeof indexedDB === 'undefined') return resolve(null)
      const request = indexedDB.open(DB, 1)
      request.onupgradeneeded = () => request.result.createObjectStore(STORE)
      request.onsuccess = () => resolve(request.result)
      request.onerror = () => resolve(null)
      request.onblocked = () => resolve(null)
    } catch {
      resolve(null)
    }
  })
  return opening
}

async function run<T>(
  mode: IDBTransactionMode,
  action: (store: IDBObjectStore) => IDBRequest,
): Promise<T | undefined> {
  const db = await open()
  if (!db) return undefined
  return new Promise((resolve) => {
    try {
      const request = action(db.transaction(STORE, mode).objectStore(STORE))
      request.onsuccess = () => resolve(request.result as T)
      request.onerror = () => resolve(undefined)
    } catch {
      resolve(undefined)
    }
  })
}

export const storage = {
  get: <T>(key: string) => run<T>('readonly', (store) => store.get(key)),
  set: (key: string, value: unknown) =>
    run('readwrite', (store) => store.put(value, key)).then(() => undefined),
  remove: (key: string) => run('readwrite', (store) => store.delete(key)).then(() => undefined),
  keys: () =>
    run<IDBValidKey[]>('readonly', (store) => store.getAllKeys()).then((keys) =>
      (keys ?? []).map(String),
    ),
}

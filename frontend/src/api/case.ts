/** Deep key conversion between the API (snake_case) and the app (camelCase). */

type Json = null | boolean | number | string | Json[] | { [key: string]: Json }

const isPlainObject = (value: unknown): value is Record<string, unknown> =>
  Object.prototype.toString.call(value) === '[object Object]'

export const toCamelKey = (key: string): string =>
  key.replace(/_([a-z0-9])/g, (_, char: string) => char.toUpperCase())

export const toSnakeKey = (key: string): string =>
  key.replace(/([a-z0-9])([A-Z])/g, '$1_$2').toLowerCase()

function convert(value: unknown, convertKey: (key: string) => string): unknown {
  if (Array.isArray(value)) return value.map((item) => convert(item, convertKey))
  if (!isPlainObject(value)) return value // File, Blob, FormData, Date... stay untouched
  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [convertKey(key), convert(item, convertKey)]),
  )
}

export const camelize = <T = Json>(value: unknown): T => convert(value, toCamelKey) as T
export const snakify = <T = Json>(value: unknown): T => convert(value, toSnakeKey) as T

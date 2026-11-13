import { describe, expect, it } from 'vitest'

import fr from '@/i18n/fr'

// Every literal `t('a.b.c')` of the app must exist: a missing key shows its raw name on screen.
const sources = import.meta.glob<string>('/src/**/*.{vue,ts}', {
  query: '?raw',
  import: 'default',
  eager: true,
})

function lookup(path: string): unknown {
  return path.split('.').reduce<unknown>((node, key) => {
    return node && typeof node === 'object' ? (node as Record<string, unknown>)[key] : undefined
  }, fr)
}

describe('i18n', () => {
  it('has every key used in the code', () => {
    const missing: string[] = []
    for (const [file, text] of Object.entries(sources)) {
      for (const match of text.matchAll(/\bt\(\s*'([a-zA-Z0-9_.]+)'/g)) {
        if (lookup(match[1]!) === undefined) missing.push(`${match[1]} (${file})`)
      }
    }
    expect(missing).toEqual([])
  })
})

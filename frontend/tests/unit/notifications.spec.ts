import { describe, expect, it } from 'vitest'

import { tabTitle } from '@/modules/notifications/badge'
import { ago } from '@/modules/notifications/format'

describe('unread count outside the page', () => {
  it('prefixes the tab title like WhatsApp', () => {
    expect(tabTitle(0)).toBe('Wedivo')
    expect(tabTitle(3)).toBe('(3) Wedivo')
    expect(tabTitle(250)).toBe('(99+) Wedivo')
  })
})

describe('ago', () => {
  const now = new Date('2026-11-17T12:00:00Z')
  const minus = (ms: number) => new Date(now.getTime() - ms).toISOString()
  it('says how long ago, as a translation key', () => {
    expect(ago(minus(20_000), now).key).toBe('now')
    expect(ago(minus(5 * 60_000), now)).toMatchObject({ key: 'minutes', n: 5 })
    expect(ago(minus(3 * 3600_000), now)).toMatchObject({ key: 'hours', n: 3 })
    expect(ago(minus(26 * 3600_000), now).key).toBe('yesterday')
    expect(ago(minus(4 * 86400_000), now)).toMatchObject({ key: 'days', n: 4 })
    expect(ago(minus(20 * 86400_000), now).key).toBe('date')
  })
})

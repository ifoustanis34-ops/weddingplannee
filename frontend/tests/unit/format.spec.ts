import { describe, expect, it } from 'vitest'

import { daysBetween, formatDate, formatDateTime } from '@/composables/useDate'
import { formatMoney, formatMoneyShort } from '@/composables/useMoney'

const NNBSP = ' '

describe('formatMoney', () => {
  it('groups thousands with a narrow no-break space and appends FCFA', () => {
    expect(formatMoney(1_500_000)).toBe(`1${NNBSP}500${NNBSP}000 FCFA`)
    expect(formatMoney(900)).toBe('900 FCFA')
    expect(formatMoney(0, 'XAF')).toBe('0 FCFA')
  })

  it('shows euros and negative amounts', () => {
    expect(formatMoney(-250_000, 'EUR')).toBe(`−250${NNBSP}000 €`)
  })
})

describe('formatMoneyShort', () => {
  it.each([
    [6_300_000, '6,3 M'],
    [1_000_000, '1 M'],
    [9_350_000, '9,35 M'],
    [7_666_667, '7,67 M'],
    [1_250_000_000, '1,25 Md'],
    [850_000, `850${NNBSP}000`],
  ])('formats %d as %s', (amount, expected) => {
    expect(formatMoneyShort(amount)).toBe(expected)
  })
})

describe('dates', () => {
  it('formats French short dates in the organization time zone', () => {
    expect(formatDate('2026-11-14T12:00:00Z')).toBe('14 nov. 2026')
    // 23:30 UTC on Nov 14 is already Nov 15 in Paris.
    expect(formatDate('2026-11-14T23:30:00Z', 'Europe/Paris')).toBe('15 nov. 2026')
  })

  it('formats date and time', () => {
    expect(formatDateTime('2026-11-14T18:30:00Z')).toBe('14 nov. 2026 à 18:30')
  })

  it('counts calendar days for J-x countdowns', () => {
    expect(daysBetween('2026-10-20T23:00:00Z', '2026-11-14T08:00:00Z')).toBe(25)
    expect(daysBetween('2026-11-14T01:00:00Z', '2026-11-14T22:00:00Z')).toBe(0)
  })
})

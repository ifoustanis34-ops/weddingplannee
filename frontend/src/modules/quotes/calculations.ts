/**
 * Live totals for the editor preview. Mirrors backend `quotes/calculations.py` exactly (integer
 * FCFA, half-up rounding) using integer arithmetic only. The server recomputes and is
 * authoritative.
 */

/** round(numerator / denominator), half up, for non-negative integers. */
function divRound(numerator: number, denominator: number): number {
  const quotient = Math.floor(numerator / denominator)
  const remainder = numerator - quotient * denominator
  return remainder * 2 >= denominator ? quotient + 1 : quotient
}

const toHundredths = (value: number) => Math.round(value * 100)

export function lineAmount(unitPrice: number, quantity: number): number {
  if (!(unitPrice >= 0) || !(quantity > 0)) return 0
  return divRound(Math.round(unitPrice) * toHundredths(quantity), 100)
}

export interface Totals {
  subtotal: number
  discountAmount: number
  total: number
  depositAmount: number
  balance: number
}

export function computeTotals(
  lines: { unitPrice: number; quantity: number }[],
  discountPct: number,
  depositPct: number,
): Totals {
  const subtotal = lines.reduce((sum, line) => sum + lineAmount(line.unitPrice, line.quantity), 0)
  const discountAmount = divRound(subtotal * toHundredths(clampPct(discountPct)), 10_000)
  const total = subtotal - discountAmount
  const depositAmount = divRound(total * toHundredths(clampPct(depositPct)), 10_000)
  return { subtotal, discountAmount, total, depositAmount, balance: total - depositAmount }
}

const clampPct = (value: number) => (Number.isFinite(value) ? Math.min(100, Math.max(0, value)) : 0)

/**
 * Quantity proposed when a catalog service is added (CLAUDE.md §7.3, complement §9):
 * « invité » units and the « per guest » rule take the guest count, « per ten guests »
 * rounds up (centrepieces: 180 guests → 18), anything else is 1.
 */
export function suggestedQuantity(
  unit: string,
  guestCount: number | null,
  rule: 'one' | 'per_guest' | 'per_ten_guests' = 'one',
): number {
  if (!guestCount || guestCount <= 0) return 1
  if (unit === 'guest' || rule === 'per_guest') return guestCount
  if (rule === 'per_ten_guests') return Math.ceil(guestCount / 10)
  return 1
}

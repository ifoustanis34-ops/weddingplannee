/** Pure geometry of the dashboard charts (reservations-stock.md §8): unit-tested, no DOM. */

import { niceStep } from '@/design/components/areaChart'

const round = (n: number) => Math.round(n * 100) / 100

// --- Ring ---------------------------------------------------------------------------------------

export interface RingSegment {
  index: number
  value: number
  /** Share of the total, 0–1. */
  share: number
  /** stroke-dasharray / stroke-dashoffset on a circle of the given radius. */
  dash: string
  offset: number
}

/**
 * Segments of a ring drawn as dashed circles. A 2px surface gap separates two segments
 * (dataviz: never a border); a lone segment is a full circle.
 */
export function ringSegments(values: number[], radius: number, gap = 2): RingSegment[] {
  const total = values.reduce((sum, v) => sum + Math.max(0, v), 0)
  if (total <= 0) return []
  const circumference = 2 * Math.PI * radius
  const visible = values.filter((v) => v > 0).length
  let cursor = 0
  const segments: RingSegment[] = []
  values.forEach((value, index) => {
    if (value <= 0) return
    const share = value / total
    const length = share * circumference
    const drawn = visible > 1 ? Math.max(length - gap, 0.5) : length
    segments.push({
      index,
      value,
      share,
      dash: `${round(drawn)} ${round(circumference - drawn)}`,
      offset: round(-cursor),
    })
    cursor += length
  })
  return segments
}

// --- Sparkline ---------------------------------------------------------------------------------

export function sparkline(
  values: number[],
  width: number,
  height: number,
  pad = 4,
): { line: string; area: string; last: { x: number; y: number } | null } {
  if (!values.length) return { line: '', area: '', last: null }
  const max = Math.max(...values, 0)
  const min = Math.min(...values, 0)
  const span = max - min || 1
  const step = values.length > 1 ? (width - 2 * pad) / (values.length - 1) : 0
  const points = values.map((v, i) => ({
    x: round(values.length > 1 ? pad + i * step : width / 2),
    y: round(height - pad - ((v - min) / span) * (height - 2 * pad)),
  }))
  const line = points.map((p, i) => `${i ? 'L' : 'M'}${p.x} ${p.y}`).join(' ')
  const first = points[0]!
  const last = points[points.length - 1]!
  return {
    line,
    area: `${line} L${last.x} ${height} L${first.x} ${height} Z`,
    last,
  }
}

// --- Income / expenses bars with the profit line ------------------------------------------------

export const BARS_WIDTH = 640
export const BARS_HEIGHT = 240
export const BARS_TOP = 16
export const BARS_BOTTOM = 204
export const BARS_LEFT = 52
export const BARS_RIGHT = 28

export interface BarsColumn {
  index: number
  /** Center of the month and the hover band around it. */
  x: number
  bandX: number
  bandWidth: number
  income: { x: number; y: number; width: number; height: number }
  expense: { x: number; y: number; width: number; height: number } | null
  profit: { x: number; y: number } | null
}

export interface BarsGeometry {
  columns: BarsColumn[]
  ticks: { value: number; y: number }[]
  zeroY: number
  profitLine: string
}

/**
 * One axis for the three series (same unit, FCFA): bars rise from zero, the profit line may
 * go below it. Bars of a month are side by side with a 2px gap; round ends anchored on zero.
 */
export function barsGeometry(
  rows: { income: number; expenses: number | null; profit: number | null }[],
): BarsGeometry {
  const highs = rows.flatMap((r) => [r.income, r.expenses ?? 0, r.profit ?? 0])
  const max = Math.max(0, ...highs)
  const min = Math.min(0, ...rows.map((r) => r.profit ?? 0))
  const step = niceStep(Math.max(max - min, 1))
  const top = Math.max(step, Math.ceil(max / step) * step)
  const bottom = Math.min(0, Math.floor(min / step) * step)
  const plot = BARS_BOTTOM - BARS_TOP
  const yOf = (value: number) => round(BARS_BOTTOM - ((value - bottom) / (top - bottom)) * plot)
  const zeroY = yOf(0)

  const inner = BARS_WIDTH - BARS_LEFT - BARS_RIGHT
  const band = rows.length ? inner / rows.length : inner
  const hasExpenses = rows.some((r) => r.expenses !== null)
  const barWidth = Math.min(18, (band * 0.62) / (hasExpenses ? 2 : 1) - 1)
  const columns: BarsColumn[] = rows.map((row, index) => {
    const x = round(BARS_LEFT + band * index + band / 2)
    const rect = (value: number, left: number) => {
      const y = yOf(Math.max(value, 0))
      return { x: round(left), y, width: round(barWidth), height: round(Math.max(zeroY - y, 0)) }
    }
    const incomeLeft = hasExpenses ? x - barWidth - 1 : x - barWidth / 2
    return {
      index,
      x,
      bandX: round(BARS_LEFT + band * index),
      bandWidth: round(band),
      income: rect(row.income, incomeLeft),
      expense: row.expenses === null ? null : rect(row.expenses, x + 1),
      profit: row.profit === null ? null : { x, y: yOf(row.profit) },
    }
  })
  const ticks: { value: number; y: number }[] = []
  for (let value = bottom; value <= top + step / 1000; value += step) {
    ticks.push({ value: round(value), y: yOf(value) })
  }
  const profitPoints = columns.filter((c) => c.profit).map((c) => c.profit!)
  const profitLine = profitPoints.map((p, i) => `${i ? 'L' : 'M'}${p.x} ${p.y}`).join(' ')
  return { columns, ticks, zeroY, profitLine }
}

// --- Labels -------------------------------------------------------------------------------------

/** « +12,5 % » / « −3 % » with a real minus sign; null when there is nothing to compare. */
export function signedPct(value: number | null, unit = ' %'): string | null {
  if (value === null || value === undefined) return null
  const rounded = Math.round(value * 10) / 10
  const text = String(Math.abs(rounded)).replace('.', ',')
  return `${rounded > 0 ? '+' : rounded < 0 ? '−' : ''}${text}${unit}`
}

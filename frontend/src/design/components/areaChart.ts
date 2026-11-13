/** Geometry of the cash-in area chart (complement §7): pure, so it is unit-tested. */

export const CHART_WIDTH = 600
export const CHART_HEIGHT = 230
/** Side margins of the plot: the first and last points sit 34px from the edges. */
export const CHART_PAD_X = 34
/** Room above the highest point for the value label (72×28). */
export const CHART_TOP = 44
/** Baseline of the plot; month labels go below. */
export const CHART_BOTTOM = 200

export interface ChartPoint {
  x: number
  y: number
  value: number
}

export interface ChartTick {
  value: number
  y: number
}

export interface AreaChartGeometry {
  points: ChartPoint[]
  ticks: ChartTick[]
  line: string
  area: string
}

/** Grid step rounded to 1, 2 or 5 × 10ⁿ, about three steps under the maximum. */
export function niceStep(max: number): number {
  if (max <= 0) return 1
  const raw = max / 3
  const magnitude = 10 ** Math.floor(Math.log10(raw))
  const normalized = raw / magnitude
  const nice = normalized < 1.5 ? 1 : normalized < 3.5 ? 2 : normalized < 7.5 ? 5 : 10
  return nice * magnitude
}

const round = (n: number) => Math.round(n * 100) / 100

export function areaChartGeometry(values: number[]): AreaChartGeometry {
  const max = Math.max(0, ...values)
  const step = niceStep(max)
  const lastTick = Math.floor(max / step) * step
  const top = Math.max(max, lastTick, step)
  const plotHeight = CHART_BOTTOM - CHART_TOP
  const yOf = (value: number) => round(CHART_BOTTOM - (value / top) * plotHeight)

  const span = CHART_WIDTH - 2 * CHART_PAD_X
  const gap = values.length > 1 ? span / (values.length - 1) : 0
  const points = values.map((value, index) => ({
    x: round(values.length > 1 ? CHART_PAD_X + index * gap : CHART_WIDTH / 2),
    y: yOf(value),
    value,
  }))

  const ticks: ChartTick[] = []
  for (let value = 0; value <= lastTick + step / 1000; value += step) {
    ticks.push({ value: round(value), y: yOf(value) })
  }

  // Smooth curve: both control points of a segment sit at its horizontal middle.
  let line = ''
  points.forEach((point, index) => {
    if (index === 0) {
      line = `M${point.x} ${point.y}`
      return
    }
    const previous = points[index - 1] as ChartPoint
    const middle = round((previous.x + point.x) / 2)
    line += ` C${middle} ${previous.y} ${middle} ${point.y} ${point.x} ${point.y}`
  })
  const first = points[0]
  const last = points[points.length - 1]
  const area =
    first && last ? `${line} L${last.x} ${CHART_BOTTOM} L${first.x} ${CHART_BOTTOM} Z` : ''

  return { points, ticks, line, area }
}

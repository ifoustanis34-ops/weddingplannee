import type { ElementType, PlanElement } from './types'

/**
 * What can be placed on a plan, with its usual size in metres. The plan is a sheet of paper:
 * like the quote preview, it keeps fixed light colours in dark mode and in the exported image.
 */
export interface ElementSpec {
  w: number
  h: number
  seats?: number
  fill: string
  stroke: string
  /** Seats can be changed (tables, rows of chairs). */
  seated?: boolean
  /** Fixed proportions (a round table stays round). */
  square?: boolean
}

export const PAPER = {
  sheet: '#ffffff',
  room: '#fbfaff',
  wall: '#17153b',
  grid: '#ebe8f5',
  gridStrong: '#d6d2e6',
  ink: '#17153b',
  muted: '#85829f',
  chair: '#5126c2',
  chairFill: '#eee8fd',
  selected: '#c42c7e',
}

export const ELEMENTS: Record<ElementType, ElementSpec> = {
  chair: { w: 0.5, h: 0.5, fill: PAPER.chairFill, stroke: PAPER.chair },
  chair_row: { w: 5, h: 0.5, seats: 10, fill: PAPER.chairFill, stroke: PAPER.chair, seated: true },
  round_table: {
    w: 1.8,
    h: 1.8,
    seats: 10,
    fill: '#ffffff',
    stroke: '#4a4769',
    seated: true,
    square: true,
  },
  rect_table: { w: 2.4, h: 0.8, seats: 8, fill: '#ffffff', stroke: '#4a4769', seated: true },
  stage: { w: 6, h: 3, fill: '#fdf2dc', stroke: '#b97a0e' },
  dance_floor: { w: 6, h: 6, fill: '#fce6f1', stroke: '#c42c7e' },
  buffet: { w: 4, h: 0.8, fill: '#dff4ec', stroke: '#0e8f69' },
  bar: { w: 3, h: 0.8, fill: '#feebe2', stroke: '#e3622f' },
  dj: { w: 2, h: 1, fill: '#e9e6f4', stroke: '#4a4769' },
  entrance: { w: 2, h: 0.3, fill: '#dff4ec', stroke: '#0e8f69' },
  decor: { w: 2.5, h: 0.6, fill: '#fce6f1', stroke: '#c42c7e' },
  pillar: { w: 0.5, h: 0.5, fill: '#4a4769', stroke: '#17153b', square: true },
  text: { w: 3, h: 0.6, fill: 'none', stroke: 'none' },
}

/** Order of the « Ajouter » palette. */
export const PALETTE: ElementType[] = [
  'round_table',
  'rect_table',
  'chair',
  'chair_row',
  'stage',
  'dance_floor',
  'buffet',
  'bar',
  'dj',
  'decor',
  'entrance',
  'pillar',
  'text',
]

export const CHAIR = 0.45
/** Room the chairs take around a table, to keep tables apart. */
export const CHAIR_GAP = 0.15

export const isTable = (type: ElementType) => type === 'round_table' || type === 'rect_table'

/** Places to sit, as the server counts them. */
export function seatCount(elements: PlanElement[]): number {
  return elements.reduce(
    (sum, element) => sum + (element.type === 'chair' ? 1 : element.seats || 0),
    0,
  )
}

export interface ChairSpot {
  x: number
  y: number
  /** Degrees: the chair faces the table. */
  rotation: number
}

/** Chairs drawn around a table or along a row, in the element's own coordinates. */
export function chairsOf(element: PlanElement): ChairSpot[] {
  const n = Math.max(0, Math.round(element.seats || 0))
  if (!n) return []
  if (element.type === 'round_table') {
    const r = Math.min(element.w, element.h) / 2
    const ring = r + CHAIR_GAP + CHAIR / 2
    return Array.from({ length: n }, (_, i) => {
      const angle = (2 * Math.PI * i) / n - Math.PI / 2
      return {
        x: element.w / 2 + ring * Math.cos(angle),
        y: element.h / 2 + ring * Math.sin(angle),
        rotation: (angle * 180) / Math.PI + 90,
      }
    })
  }
  if (element.type === 'rect_table') {
    const top = Math.ceil(n / 2)
    const bottom = n - top
    const side = (count: number, y: number, rotation: number) =>
      Array.from({ length: count }, (_, i) => ({
        x: (element.w * (i + 0.5)) / count,
        y,
        rotation,
      }))
    return [
      // The back of each chair away from the table (as around a round table).
      ...side(top, -(CHAIR_GAP + CHAIR / 2), 0),
      ...side(bottom, element.h + CHAIR_GAP + CHAIR / 2, 180),
    ]
  }
  if (element.type === 'chair_row') {
    return Array.from({ length: n }, (_, i) => ({
      x: (element.w * (i + 0.5)) / n,
      y: element.h / 2,
      rotation: 0,
    }))
  }
  return []
}

/** Extra margin drawn around an element (the chairs of a table stick out). */
export const outerMargin = (element: PlanElement): number =>
  isTable(element.type) && element.seats ? CHAIR_GAP + CHAIR : 0

export function newId(): string {
  return Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4)
}

/** Rounds a length to the centimetre (positions) or decimetre (snapping while dragging). */
export const round = (value: number, step = 0.01): number =>
  Number((Math.round(value / step) * step).toFixed(2))

/** « 15,5 m » */
export const metres = (value: number): string =>
  `${new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 }).format(value)} m`

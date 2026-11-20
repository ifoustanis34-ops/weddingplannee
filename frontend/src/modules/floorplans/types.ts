/** « Croquis » (feedback 20/11/2026): a venue drawn to scale, positions in metres. */
export type ElementType =
  | 'chair'
  | 'chair_row'
  | 'round_table'
  | 'rect_table'
  | 'stage'
  | 'dance_floor'
  | 'buffet'
  | 'bar'
  | 'dj'
  | 'entrance'
  | 'decor'
  | 'pillar'
  | 'text'

export interface PlanElement {
  id: string
  type: ElementType
  /** Top-left corner, metres from the top-left corner of the room (before rotation). */
  x: number
  y: number
  /** Width (left to right) and depth (top to bottom), metres. */
  w: number
  h: number
  /** Degrees, clockwise, around the centre. */
  rotation: number
  label: string
  /** Chairs of a table or a row of chairs. */
  seats: number
}

export interface FloorPlan {
  id: string
  name: string
  venue: string
  /** Metres, left to right. */
  length: number
  /** Metres, top to bottom. */
  width: number
  elements: PlanElement[]
  notes: string
  /** Places to sit (server count). */
  chairs: number
  createdAt: string
  updatedAt: string
}

export type FloorPlanInput = Pick<
  FloorPlan,
  'name' | 'venue' | 'length' | 'width' | 'elements' | 'notes'
>

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
  | 'head_table'
  | 'cocktail'
  | 'cake'
  | 'lounge'
  | 'photobooth'
  | 'plant'
  | 'chandelier'
  | 'screen'

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

/** How the room looks in 3D (feedback 23/11/2026). */
export interface Ambiance {
  floor: 'tiles' | 'parquet' | 'marble' | 'concrete' | 'grass' | 'carpet'
  /** `none`: outdoors (garden, beach). */
  walls: 'white' | 'cream' | 'grey' | 'none'
  light: 'day' | 'evening'
  /** Metres under the ceiling. */
  height: number
}

export const DEFAULT_AMBIANCE: Ambiance = {
  floor: 'tiles',
  walls: 'white',
  light: 'day',
  height: 3,
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
  ambiance: Ambiance
  /** Places to sit (server count). */
  chairs: number
  createdAt: string
  updatedAt: string
}

export type FloorPlanInput = Pick<
  FloorPlan,
  'name' | 'venue' | 'length' | 'width' | 'elements' | 'notes'
> & { ambiance?: Ambiance }

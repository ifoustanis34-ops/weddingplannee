export type Unit = 'flat' | 'unit' | 'guest' | 'day' | 'evening'

export interface ServiceItem {
  id: string
  category: string
  name: string
  description: string
  unit: Unit
  unitLabel: string
  unitPrice: number
  isActive: boolean
  /** Quantity proposed in a quote: 1, the guest count, or one per ten guests. */
  quantityRule: QuantityRule
  /** Pre-filled in every new quote. */
  isDefault: boolean
  /** Line icon on the quotes; empty = guessed from the name. */
  icon: string
}

export type QuantityRule = 'one' | 'per_guest' | 'per_ten_guests'

export interface ServiceCategory {
  id: string
  name: string
  order: number
  items: ServiceItem[]
}

export type ServiceItemInput = Pick<
  ServiceItem,
  | 'category'
  | 'name'
  | 'description'
  | 'unit'
  | 'unitPrice'
  | 'isActive'
  | 'quantityRule'
  | 'isDefault'
  | 'icon'
>

/** Line icons of the quotes (backend documents.icons.SERVICE_ICONS). */
export const SERVICE_ICONS = [
  'arch',
  'bouquet',
  'cake',
  'calendar',
  'calendar-check',
  'camera',
  'car',
  'chair',
  'clipboard',
  'flower',
  'gift',
  'glass',
  'light',
  'mic',
  'music',
  'plate',
  'sparkles',
  'speaker',
  'table',
  'tools',
  'video',
] as const

export const UNITS: Unit[] = ['flat', 'unit', 'guest', 'day', 'evening']

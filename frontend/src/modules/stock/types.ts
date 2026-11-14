/** Stock and equipment (reservations-stock.md §5). Amounts are null for roles without them. */
export type Tracking = 'quantity' | 'unit'
export type RentUnit = 'day' | 'event'
export type UnitStatus = 'available' | 'maintenance' | 'out_of_service' | 'lost' | 'sold'
export type UnitCondition = 'good' | 'worn' | 'damaged'
export type MovementKind =
  | 'purchase'
  | 'checkout'
  | 'return'
  | 'sale'
  | 'breakage'
  | 'loss'
  | 'maintenance_out'
  | 'maintenance_in'
  | 'adjustment'
export type ManualKind = 'purchase' | 'sale' | 'breakage' | 'loss' | 'adjustment'

export interface StockToday {
  total: number
  available: number
  reserved: number
  out: number
  maintenance: number
  outOfService: number
}

export interface ItemCategory {
  id: string
  name: string
  cleaningDays: number
  position: number
}

export interface Item {
  id: string
  reference: string
  name: string
  category: string
  categoryName: string
  photoUrl: string | null
  description: string
  location: string
  tracking: Tracking
  totalQuantity: number
  /** Units partners can lend on top of ours (feedback 14/11/2026). */
  partnerQuantity: number
  rentPrice: number | null
  rentUnit: RentUnit
  salePrice: number | null
  purchaseCost: number | null
  deposit: number | null
  alertThreshold: number
  cleaningDays: number | null
  delayDays: number
  isActive: boolean
  today: StockToday | null
  stockValue: number | null
  createdAt: string
}

export interface ItemInput {
  reference?: string
  name: string
  category: string
  description?: string
  location?: string
  tracking?: Tracking
  rentPrice?: number
  rentUnit?: RentUnit
  salePrice?: number | null
  purchaseCost?: number
  deposit?: number
  alertThreshold?: number
  cleaningDays?: number | null
  isActive?: boolean
  initialQuantity?: number
  serials?: string[]
}

export interface ItemUnit {
  id: string
  serialNumber: string
  status: UnitStatus
  condition: UnitCondition
  notes: string
}

export interface Movement {
  id: string
  item: string
  itemName: string
  itemReference: string
  unit: string | null
  serialNumber: string | null
  kind: MovementKind
  kindLabel: string
  delta: number
  quantity: number
  reason: string
  reference: string
  unitCost: number | null
  authorName: string | null
  occurredAt: string
  cancelledAt: string | null
  cancelReason: string
}

export interface MovementInput {
  item: string
  unit?: string | null
  kind: ManualKind
  quantity: number
  direction?: 1 | -1
  reason?: string
  reference?: string
  unitCost?: number | null
  serials?: string[]
}

export interface Maintenance {
  id: string
  item: string
  itemName: string
  unit: string | null
  serialNumber: string | null
  quantity: number
  reason: string
  startedAt: string
  expectedEnd: string | null
  endedAt: string | null
  cost: number | null
  isLate: boolean
}

export interface ItemActivity {
  occupancy: { date: string; available: number; total: number }[]
  movements: Movement[]
  units: ItemUnit[]
  maintenances: Maintenance[]
}

export interface Pack {
  id: string
  name: string
  description: string
  price: number | null
  isActive: boolean
  components: { item: string; itemName: string; quantity: number }[]
  available: number | null
}

export interface InventoryLine {
  id: string
  item: string
  itemName: string
  itemReference: string
  categoryName: string
  expected: number
  counted: number | null
  difference: number | null
}

export interface Inventory {
  id: string
  date: string
  category: string | null
  categoryName: string | null
  status: 'draft' | 'validated'
  authorName: string | null
  validatedAt: string | null
  lines: InventoryLine[]
}

export interface StockStats {
  items: number
  units: number
  stockValue: number | null
  utilisation: number | null
  alerts: number
  inMaintenance: number
  outOfService: number
}

export interface AvailabilityGrid {
  days: string[]
  rows: {
    item: string
    name: string
    reference: string
    category: string
    total: number
    cells: { available: number; rate: number }[]
  }[]
}

/** What a partner lends (feedback 14/11/2026). `unitCost`: owner and accountant only. */
export interface PartnerSupply {
  id: string
  item: string
  itemName: string
  itemReference: string
  categoryName: string
  ownQuantity: number
  vendor: string
  vendorName: string
  vendorPhone: string
  quantity: number
  unitCost: number | null
  notes: string
  isActive: boolean
}

export interface PartnerSupplyInput {
  vendor: string
  item?: string | null
  newItemName?: string
  newItemCategory?: string
  newItemRentPrice?: number
  quantity: number
  unitCost?: number
  notes?: string
  isActive?: boolean
}

export interface ImportReport {
  itemsCreated: number
  itemsUpdated: number
  stockAdjusted: number
  partnersCreated: number
  suppliesCreated: number
  suppliesUpdated: number
  errors: string[]
  warnings: string[]
  dryRun: boolean
}

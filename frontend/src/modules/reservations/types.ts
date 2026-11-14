/** Reservations (reservations-stock.md §4.1). Amounts are null for roles without them. */
export type ReservationStatus =
  | 'draft'
  | 'quote_sent'
  | 'awaiting_deposit'
  | 'confirmed'
  | 'preparing'
  | 'delivered'
  | 'installed'
  | 'in_progress'
  | 'picked_up'
  | 'closed'
  | 'cancelled'
export type ReservationKind = 'rental' | 'sale' | 'service' | 'mixed'
export type LineKind = 'rental' | 'sale' | 'pack' | 'service' | 'free' | 'damage'
export type PaymentMethod = 'cash' | 'transfer' | 'orange_money' | 'mtn_momo' | 'wave' | 'cheque'

export interface NextStep {
  key: 'deposit' | 'delivery' | 'setup' | 'event' | 'pickup' | 'return'
  at: string | null
}

export interface ReservationRow {
  id: string
  number: string
  client: string
  clientName: string
  kind: ReservationKind
  title: string
  venue: string
  status: ReservationStatus
  statusLabel: string
  owner: string | null
  ownerName: string | null
  eventStart: string
  eventEnd: string
  deliveryAt: string | null
  total: number | null
  paid: number | null
  balance: number | null
  nextStep: NextStep | null
}

export interface ReservationLine {
  id?: string
  kind: LineKind
  item?: string | null
  itemReference?: string | null
  rentUnit?: 'day' | 'event' | null
  pack?: string | null
  service?: string | null
  label: string
  quantity: number
  unitPrice?: number | null
  periodDays?: number
  deposit?: number | null
  amount?: number | null
  quantityOut?: number
  quantityReturned?: number
  quantityDamaged?: number
  quantityMissing?: number
  /** Part lent by a partner (feedback 14/11/2026); `partnerUnitCost`: owner, accountant. */
  partnerSupply?: string | null
  partnerName?: string | null
  partnerQuantity?: number
  partnerUnitCost?: number | null
}

export interface ReservationPayment {
  id: string
  kind: 'payment' | 'security' | 'security_refund'
  kindLabel: string
  amount: number
  method: PaymentMethod
  methodLabel: string
  paidAt: string
  reference: string
  recordedByName: string | null
  isCancelled: boolean
  cancelReason: string
}

export interface Reservation extends Omit<ReservationRow, 'clientName'> {
  clientDetail: { id: string; name: string; phone: string; email: string }
  wedding: string | null
  weddingTitle: string | null
  address: string
  guestCount: number | null
  setupAt: string | null
  teardownAt: string | null
  pickupAt: string | null
  returnAt: string | null
  vehicle: string
  discount: number | null
  transportFee: number | null
  setupFee: number | null
  subtotal: number | null
  depositRequired: number | null
  securityDeposit: number | null
  securityStatus: 'none' | 'held' | 'refunded' | 'retained'
  securityRetained: number | null
  refundDue: number | null
  notes: string
  confirmedAt: string | null
  checkedOutAt: string | null
  returnedAt: string | null
  cancelledAt: string | null
  cancelReason: string
  lines: ReservationLine[]
  payments: ReservationPayment[]
  logs: {
    id: string
    action: string
    message: string
    authorName: string | null
    createdAt: string
  }[]
}

export interface ReservationInput {
  client: string
  wedding?: string | null
  kind: ReservationKind
  title: string
  venue?: string
  address?: string
  guestCount?: number | null
  owner?: string | null
  notes?: string
  deliveryAt?: string | null
  setupAt?: string | null
  eventStart: string
  eventEnd: string
  teardownAt?: string | null
  pickupAt?: string | null
  returnAt?: string | null
  vehicle?: string
  discount?: number
  transportFee?: number
  setupFee?: number
  depositRequired?: number
  depositPct?: number
  lines: ReservationLine[]
}

export interface ReservationStats {
  confirmedMonth: number
  awaitingDeposit: number
  awaitingDepositAmount: number | null
  toDeliverWeek: number
  balanceDue: number | null
}

export interface PartnerOffer {
  supply: string
  vendor: string
  vendorName: string
  /** What the partner can still lend over the period. */
  free: number
  unitCost: number | null
}

export interface Shortage {
  item: string
  name: string
  needed: number
  available: number
  alternatives: { item: string; name: string; available: number }[]
  /** The rental line to complete, and the partners who can (feedback 14/11/2026). */
  line: string | null
  partnerQuantity: number
  partners: PartnerOffer[]
}

export interface PartnerOrder {
  vendor: string
  vendorName: string
  contact: string
  phone: string
  total: number | null
  lines: {
    line: string
    label: string
    reference: string
    quantity: number
    unitCost: number | null
    total: number | null
  }[]
}

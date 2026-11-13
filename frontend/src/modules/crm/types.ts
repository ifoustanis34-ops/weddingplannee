import type { ReservationStatus } from '@/modules/reservations/types'

/** A client of the agency (reservations-stock.md §4.4). Amounts are null for roles without money. */
export interface Client {
  id: string
  name: string
  company: string
  phone: string
  phoneAlt: string
  email: string
  address: string
  notes: string
  preferences: string
  isArchived: boolean
  orderCount: number
  revenue: number | null
  collected: number | null
  balanceDue: number | null
  lastOrderAt: string | null
  createdAt: string
  updatedAt: string
}

export type ClientInput = Partial<
  Pick<
    Client,
    | 'name'
    | 'company'
    | 'phone'
    | 'phoneAlt'
    | 'email'
    | 'address'
    | 'notes'
    | 'preferences'
    | 'isArchived'
  >
>

export type ClientSort = 'name' | '-revenue' | '-balance_due' | '-last_order_at'

export interface ClientFilters {
  search?: string
  archived?: boolean
  ordering?: ClientSort
}

export interface ClientHistory {
  reservations: {
    id: string
    number: string
    title: string
    status: ReservationStatus
    eventStart: string
    total: number | null
    balance: number | null
  }[]
  quotes: { id: string; number: string; status: string; issueDate: string; total: number | null }[]
  contracts: {
    id: string
    number: string
    status: string
    signedAt: string
    weddingDate: string | null
    total: number | null
  }[]
  payments: {
    id: string
    origin: 'contract' | 'reservation'
    reference: string
    kind: 'payment' | 'security' | 'security_refund'
    amount: number
    method: string
    paidAt: string
    isCancelled: boolean
  }[]
}

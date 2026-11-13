export type PaymentMethod = 'transfer' | 'cash' | 'orange_money' | 'mtn_momo' | 'wave' | 'cheque'
export const PAYMENT_METHODS: PaymentMethod[] = [
  'orange_money',
  'mtn_momo',
  'wave',
  'transfer',
  'cash',
  'cheque',
]

export interface ContractRow {
  id: string
  number: string
  client: string
  clientName: string
  weddingDate: string | null
  wedding: string | null
  total: number
  collected: number
  balance: number
  /** Owner and accountant only (CLAUDE.md §11). */
  expenses?: number
  margin?: number
  marginPct?: number | null
  progress: number
  status: 'active' | 'completed' | 'cancelled'
  statusLabel: string
  signedAt: string
}

export interface ScheduleItem {
  id: string
  label: string
  amount: number
  dueDate: string
  paid: number
  remaining: number
  isPaid: boolean
  isOverdue: boolean
}

export interface Payment {
  id: string
  amount: number
  method: PaymentMethod
  methodLabel: string
  paidAt: string
  reference: string
  receiptNumber: string
  hasReceipt: boolean
  hasProof: boolean
  recordedByName: string | null
  isCancelled: boolean
  cancelledAt: string | null
  cancelReason: string
  createdAt: string
}

export interface ExpenseItem {
  id: string
  label: string
  amount: number
  date: string | null
  isPaid: boolean
}

export interface ContractDetail extends ContractRow {
  clientEmail: string
  clientPhone: string
  quote: { id: string; number: string }
  schedule: ScheduleItem[]
  payments: Payment[]
  expenseItems?: ExpenseItem[]
}

export interface FinanceSummary {
  contractsCount: number
  contractsTotal: number
  collected: number
  balanceDue: number
  collectedThisMonth: number
  overdue: number
  expenses?: number
  margin?: number
  marginPct?: number | null
  /** Next unpaid installments, overdue first (complement §12). */
  upcoming: UpcomingInstallment[]
  /** « À payer aux fournisseurs » (complement §12): biggest amounts still owed. */
  vendorsDue: { id: string; name: string; categoryLabel: string; due: number }[]
}

export interface UpcomingInstallment {
  id: string
  contract: string
  clientName: string
  label: string
  dueDate: string
  remaining: number
  isOverdue: boolean
}

export interface PaymentInput {
  amount: number
  method: PaymentMethod
  paidAt: string
  reference: string
  proof: File | null
}

export interface ExpenseCategory {
  id: string
  name: string
  position: number
  isActive: boolean
}

export interface ExpenseInput {
  label: string
  amount: number
  category: string | null
  wedding: string | null
  reservation?: string | null
  date: string | null
  supplier: string
  method: PaymentMethod | ''
}

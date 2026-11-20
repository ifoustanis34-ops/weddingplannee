import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, type MaybeRefOrGetter, toValue } from 'vue'

import { api } from '@/api/client'
import type { PeriodRequest } from '@/modules/dashboard/api'

/** Invoices, credit notes, revenues, treasury, profitability, reports (§6). */

export type InvoiceStatus = 'paid' | 'partial' | 'issued' | 'overdue' | 'cancelled'
export type RevenueCategory = 'rental' | 'sale' | 'service' | 'transport' | 'damage'

export interface CreditNote {
  id: string
  number: string
  invoice: string
  invoiceNumber: string
  reservation: string
  reservationNumber: string
  clientName: string
  issuedAt: string
  amount: number
  reason: string
}

export interface Invoice {
  id: string
  number: string
  kind: 'deposit' | 'final'
  kindLabel: string
  reservation: string
  reservationDetail: { id: string; number: string; title: string }
  clientDetail: { id: string; name: string; phone: string }
  issuedAt: string
  dueAt: string
  total: number
  credited: number
  paid: number
  balance: number
  status: InvoiceStatus
  lines: { label: string; quantity: number; unitPrice: number; amount: number }[]
  creditNotes: CreditNote[]
}

export interface Revenue {
  id: string
  date: string
  amount: number
  category: RevenueCategory
  categoryLabel: string
  label: string
  method: string
  clientName: string | null
  reservation: string | null
  reservationNumber: string | null
  contract: string | null
  isCancelled: boolean
}

export interface Treasury {
  period: { start: string; end: string; key: string }
  collected: number
  toCollect: number
  spent: number
  balance: number
  previous: { collected: number; spent: number; balance: number }
  invoicesOpen: number
  invoicesOverdue: { count: number; amount: number }
  revenueByCategory: { category: RevenueCategory; label: string; amount: number }[]
  expensesByCategory: { category: string; amount: number }[]
  monthly: { month: string; cashIn: number; cashOut: number; net: number }[]
}

export type ProfitabilityBy = 'event' | 'service' | 'item'
export interface EventRow {
  kind: 'reservation' | 'contract'
  id: string
  number: string
  title: string
  client: string
  date: string
  revenue: number
  costs: number
  margin: number
  marginPct: number | null
}
export interface ServiceRow {
  key: string
  name: string
  revenue: number
  sales: number
  marginAvg: number | null
}
export interface ItemRow {
  id: string
  reference: string
  name: string
  category: string
  revenue: number
  rentedDays: number
  utilisationPct: number | null
  purchaseCost: number
  paybackPct: number | null
}

export const REPORT_TYPES = [
  'revenue',
  'profitable',
  'services',
  'items',
  'clients',
  'expenses',
  'margins',
  'unpaid',
] as const
export type ReportType = (typeof REPORT_TYPES)[number]
export interface ReportColumn {
  key: string
  label: string
  kind: 'text' | 'money' | 'pct' | 'number' | 'date' | 'month'
}
export interface Report {
  type: ReportType
  title: string
  period: { key: string; start: string; end: string; previousStart: string; previousEnd: string }
  columns: ReportColumn[]
  rows: Record<string, unknown>[]
  totals: Record<string, unknown>
  headline: {
    label: string
    current: number
    previous: number | null
    variationPct: number | null
  }
}

const params = (period: PeriodRequest) => ({
  period: period.period,
  from: period.period === 'custom' ? period.from : undefined,
  to: period.period === 'custom' ? period.to : undefined,
})

export const billingApi = {
  invoices: (filters: { reservation?: string; status?: string; search?: string } = {}) =>
    api.get<Invoice[]>('/invoices', { params: filters }).then((r) => r.data),
  issue: (reservation: string, kind: 'deposit' | 'final') =>
    api.post<Invoice>('/invoices', { reservation, kind }).then((r) => r.data),
  credit: (id: string, input: { amount: number; reason: string }) =>
    api.post<CreditNote>(`/invoices/${id}/credit`, input).then((r) => r.data),
  creditNotes: () => api.get<CreditNote[]>('/credit-notes').then((r) => r.data),
  revenues: (period: PeriodRequest, category?: string) =>
    api
      .get<Revenue[]>('/revenues', {
        params: { ...params(period), category: category || undefined },
      })
      .then((r) => r.data),
  treasury: (period: PeriodRequest) =>
    api.get<Treasury>('/finance/treasury', { params: params(period) }).then((r) => r.data),
  profitability: <T>(by: ProfitabilityBy, period: PeriodRequest) =>
    api
      .get<{ rows: T[] }>('/finance/profitability', { params: { by, ...params(period) } })
      .then((r) => r.data.rows),
  report: (type: ReportType, period: PeriodRequest) =>
    api.get<Report>(`/reports/${type}`, { params: params(period) }).then((r) => r.data),
  /** A PDF as a blob (to share it on WhatsApp). */
  blob: (url: string) => api.get<Blob>(url, { responseType: 'blob' }).then((r) => r.data),
  /** PDF or Excel of a report, or the PDF of an invoice / credit note: a file to save. */
  file: async (url: string, query: Record<string, string | undefined>, filename: string) => {
    const response = await api.get<Blob>(url, { params: query, responseType: 'blob' })
    const href = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = href
    link.download = filename
    link.click()
    setTimeout(() => URL.revokeObjectURL(href), 60_000)
  },
  reportFile: (type: ReportType, period: PeriodRequest, output: 'pdf' | 'xlsx') =>
    billingApi.file(`/reports/${type}`, { ...params(period), output }, `rapport-${type}.${output}`),
  uploadReceipt: (expense: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api
      .post<{ receiptUrl: string }>(`/expenses/${expense}/receipt`, form)
      .then((r) => r.data)
  },
}

export const billingKeys = { all: ['billing'] as const }

export function useInvoices(filters: MaybeRefOrGetter<{ reservation?: string; status?: string }>) {
  return useQuery({
    queryKey: computed(() => [...billingKeys.all, 'invoices', { ...toValue(filters) }]),
    queryFn: () => billingApi.invoices(toValue(filters)),
    placeholderData: keepPreviousData,
  })
}

export function useTreasury(period: MaybeRefOrGetter<PeriodRequest>) {
  return useQuery({
    queryKey: computed(() => [...billingKeys.all, 'treasury', { ...toValue(period) }]),
    queryFn: () => billingApi.treasury(toValue(period)),
    placeholderData: keepPreviousData,
  })
}

export function useRevenues(
  period: MaybeRefOrGetter<PeriodRequest>,
  category: MaybeRefOrGetter<string>,
) {
  return useQuery({
    queryKey: computed(() => [
      ...billingKeys.all,
      'revenues',
      { ...toValue(period) },
      toValue(category),
    ]),
    queryFn: () => billingApi.revenues(toValue(period), toValue(category)),
    placeholderData: keepPreviousData,
  })
}

export function useProfitability<T>(
  by: MaybeRefOrGetter<ProfitabilityBy>,
  period: MaybeRefOrGetter<PeriodRequest>,
) {
  return useQuery({
    queryKey: computed(() => [
      ...billingKeys.all,
      'profitability',
      toValue(by),
      { ...toValue(period) },
    ]),
    queryFn: () => billingApi.profitability<T>(toValue(by), toValue(period)),
    placeholderData: keepPreviousData,
  })
}

export function useReport(
  type: MaybeRefOrGetter<ReportType>,
  period: MaybeRefOrGetter<PeriodRequest>,
) {
  return useQuery({
    queryKey: computed(() => [...billingKeys.all, 'report', toValue(type), { ...toValue(period) }]),
    queryFn: () => billingApi.report(toValue(type), toValue(period)),
    placeholderData: keepPreviousData,
  })
}

/** Issuing or crediting changes invoices, the reservation, alerts and the dashboard. */
export function useBillingMutation<TArgs, TResult>(fn: (args: TArgs) => Promise<TResult>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      for (const key of [billingKeys.all, ['reservations'], ['alerts'], ['dashboard'], ['finance']])
        void queryClient.invalidateQueries({ queryKey: key })
    },
  })
}

export const INVOICE_TONES: Record<InvoiceStatus, 'green' | 'gold' | 'violet' | 'red' | 'grey'> = {
  paid: 'green',
  partial: 'gold',
  issued: 'violet',
  overdue: 'red',
  cancelled: 'grey',
}

export interface ExpenseRow {
  id: string
  label: string
  amount: number
  date: string | null
  categoryName: string | null
  weddingTitle: string | null
  reservation: string | null
  reservationNumber: string | null
  supplier: string
  receiptUrl: string | null
}

export const useExpenses = () =>
  useQuery({
    queryKey: [...billingKeys.all, 'expenses'],
    queryFn: () => api.get<ExpenseRow[]>('/expenses').then((r) => r.data),
  })

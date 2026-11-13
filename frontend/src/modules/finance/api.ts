import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { type MaybeRefOrGetter, computed, toValue } from 'vue'

import { api } from '@/api/client'

import type {
  ContractDetail,
  ContractRow,
  ExpenseCategory,
  ExpenseInput,
  FinanceSummary,
  PaymentInput,
} from './types'

export const financeKeys = {
  all: ['finance'] as const,
  contracts: () => [...financeKeys.all, 'contracts'] as const,
  contract: (id: string) => [...financeKeys.all, 'contract', id] as const,
  summary: () => [...financeKeys.all, 'summary'] as const,
  expenseCategories: () => [...financeKeys.all, 'expense-categories'] as const,
}

export const financeApi = {
  contracts: () => api.get<ContractRow[]>('/contracts').then((r) => r.data),
  contract: (id: string) => api.get<ContractDetail>(`/contracts/${id}`).then((r) => r.data),
  summary: () => api.get<FinanceSummary>('/finance/summary').then((r) => r.data),
  recordPayment: (contractId: string, input: PaymentInput) => {
    // Multipart for the optional proof; keys in snake_case (FormData is not converted).
    const form = new FormData()
    form.append('amount', String(input.amount))
    form.append('method', input.method)
    form.append('paid_at', input.paidAt)
    form.append('reference', input.reference)
    if (input.proof) form.append('proof', input.proof)
    return api.post<ContractDetail>(`/contracts/${contractId}/payments`, form).then((r) => r.data)
  },
  cancelPayment: (paymentId: string, reason: string) =>
    api.post(`/payments/${paymentId}/cancel`, { reason }).then(() => undefined),
  updateSchedule: (
    contractId: string,
    installments: { label: string; amount: number; dueDate: string }[],
  ) =>
    api
      .put<ContractDetail>(`/contracts/${contractId}/schedule`, { installments })
      .then((r) => r.data),
  addExpense: (input: { wedding: string; label: string; amount: number; date: string | null }) =>
    api.post('/expenses', input).then(() => undefined),
  /** Any expense: general (category required) or attached to a wedding. */
  createExpense: (input: ExpenseInput) =>
    api.post<{ id: string }>('/expenses', input).then((r) => r.data),
  expenseCategories: () => api.get<ExpenseCategory[]>('/expense-categories').then((r) => r.data),
  deleteExpense: (id: string) => api.delete(`/expenses/${id}`).then(() => undefined),
  /** Files are fetched with the session (X-Organization in dev), then opened or saved. */
  download: async (url: string, filename?: string) => {
    const response = await api.get<Blob>(url, { responseType: 'blob' })
    const href = URL.createObjectURL(response.data)
    if (filename) {
      const link = document.createElement('a')
      link.href = href
      link.download = filename
      link.click()
    } else {
      window.open(href, '_blank', 'noopener')
    }
    setTimeout(() => URL.revokeObjectURL(href), 60_000)
  },
}

export const useContracts = () =>
  useQuery({ queryKey: financeKeys.contracts(), queryFn: financeApi.contracts })
export const useFinanceSummary = () =>
  useQuery({ queryKey: financeKeys.summary(), queryFn: financeApi.summary })

export function useContract(id: MaybeRefOrGetter<string | null>) {
  return useQuery({
    queryKey: computed(() => financeKeys.contract(toValue(id) ?? '')),
    queryFn: () => financeApi.contract(toValue(id)!),
    enabled: computed(() => Boolean(toValue(id))),
  })
}

/** Money moved: contracts, totals and the dashboard are all stale. */
export function useFinanceAction<TArgs, TResult>(fn: (args: TArgs) => Promise<TResult>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: financeKeys.all })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useExpenseCategories(enabled: MaybeRefOrGetter<boolean> = true) {
  return useQuery({
    queryKey: financeKeys.expenseCategories(),
    queryFn: financeApi.expenseCategories,
    enabled: computed(() => toValue(enabled)),
    staleTime: 300_000,
  })
}

/** « Enregistrer une dépense »: refreshes the dashboard and the finance screens. */
export function useCreateExpense() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: financeApi.createExpense,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      void queryClient.invalidateQueries({ queryKey: financeKeys.all })
      void queryClient.invalidateQueries({ queryKey: ['billing'] })
    },
  })
}

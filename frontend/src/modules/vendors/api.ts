import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, type MaybeRefOrGetter, toValue } from 'vue'

import { api } from '@/api/client'

import type { Assignment, Vendor, VendorInput } from './types'

export const vendorKeys = {
  all: ['vendors'] as const,
  list: () => [...vendorKeys.all, 'list'] as const,
  ofWedding: (id: string) => [...vendorKeys.all, 'wedding', id] as const,
}

export const vendorsApi = {
  list: () => api.get<Vendor[]>('/vendors').then((r) => r.data),
  create: (input: VendorInput) => api.post<Vendor>('/vendors', input).then((r) => r.data),
  update: (id: string, input: Partial<VendorInput>) =>
    api.patch<Vendor>(`/vendors/${id}`, input).then((r) => r.data),
  remove: (id: string) => api.delete(`/vendors/${id}`).then(() => undefined),
  ofWedding: (id: string) => api.get<Assignment[]>(`/weddings/${id}/vendors`).then((r) => r.data),
  book: (
    weddingId: string,
    input: { vendor: string; service: string; cost?: number; paidAmount?: number },
  ) => api.post<Assignment>(`/weddings/${weddingId}/vendors`, input).then((r) => r.data),
  updateBooking: (id: string, input: { service?: string; cost?: number; paidAmount?: number }) =>
    api.patch<Assignment>(`/vendor-assignments/${id}`, input).then((r) => r.data),
  removeBooking: (id: string) => api.delete(`/vendor-assignments/${id}`).then(() => undefined),
}

export const useVendors = () => useQuery({ queryKey: vendorKeys.list(), queryFn: vendorsApi.list })

export function useWeddingVendors(id: MaybeRefOrGetter<string | null>) {
  return useQuery({
    queryKey: computed(() => vendorKeys.ofWedding(toValue(id) ?? '')),
    queryFn: () => vendorsApi.ofWedding(toValue(id)!),
    enabled: computed(() => Boolean(toValue(id))),
  })
}

/** Vendor changes refresh the directory, the weddings and the finance summary (amounts due). */
export function useVendorAction<TArgs, TResult>(fn: (args: TArgs) => Promise<TResult>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: vendorKeys.all })
      void queryClient.invalidateQueries({ queryKey: ['weddings'] })
      void queryClient.invalidateQueries({ queryKey: ['finance'] })
    },
  })
}

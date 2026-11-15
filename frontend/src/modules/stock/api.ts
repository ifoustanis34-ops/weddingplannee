import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { type MaybeRefOrGetter, computed, toValue } from 'vue'

import { api } from '@/api/client'
import { prepareImage } from '@/app/images'

import type {
  AvailabilityGrid,
  Inventory,
  Item,
  ItemActivity,
  ItemCategory,
  ItemInput,
  ItemUnit,
  Maintenance,
  Movement,
  MovementInput,
  Pack,
  PartnerSupply,
  PartnerSupplyInput,
  ImportReport,
  StockStats,
} from './types'

interface Page<T> {
  results: T[]
  next: string | null
}

export const stockKeys = {
  all: ['stock'] as const,
  categories: () => [...stockKeys.all, 'categories'] as const,
  items: (filters: Record<string, unknown>) => [...stockKeys.all, 'items', filters] as const,
  item: (id: string) => [...stockKeys.all, 'item', id] as const,
  activity: (id: string) => [...stockKeys.all, 'activity', id] as const,
  packs: (period: Record<string, unknown>) => [...stockKeys.all, 'packs', period] as const,
  grid: (params: Record<string, unknown>) => [...stockKeys.all, 'grid', params] as const,
  movements: (filters: Record<string, unknown>) =>
    [...stockKeys.all, 'movements', filters] as const,
  inventories: () => [...stockKeys.all, 'inventories'] as const,
  stats: () => [...stockKeys.all, 'stats'] as const,
  partners: (filters: Record<string, unknown>) => [...stockKeys.all, 'partners', filters] as const,
}

export const stockApi = {
  categories: () => api.get<ItemCategory[]>('/item-categories').then((r) => r.data),
  items: (filters: { search?: string; category?: string; status?: string; source?: string }) =>
    api
      .get<Item[]>('/items', {
        params: {
          search: filters.search || undefined,
          category: filters.category || undefined,
          status: filters.status || undefined,
          source: filters.source || undefined,
        },
      })
      .then((r) => r.data),
  // Partner equipment (feedback 14/11/2026)
  partnerSupplies: (filters: { search?: string; vendor?: string; item?: string }) =>
    api
      .get<PartnerSupply[]>('/partner-supplies', {
        params: {
          search: filters.search || undefined,
          vendor: filters.vendor || undefined,
          item: filters.item || undefined,
        },
      })
      .then((r) => r.data),
  createPartnerSupply: (input: PartnerSupplyInput) =>
    api.post<PartnerSupply>('/partner-supplies', input).then((r) => r.data),
  updatePartnerSupply: (id: string, input: Partial<PartnerSupplyInput>) =>
    api.patch<PartnerSupply>(`/partner-supplies/${id}`, input).then((r) => r.data),
  deletePartnerSupply: (id: string) =>
    api.delete<{ deleted: boolean }>(`/partner-supplies/${id}`).then((r) => r.data),
  importLists: (file: File, dryRun: boolean) => {
    const form = new FormData()
    form.append('file', file)
    return api
      .post<ImportReport>('/stock/import', form, { params: { dryRun: dryRun || undefined } })
      .then((r) => r.data)
  },
  importTemplate: () =>
    api.get<Blob>('/stock/import/template', { responseType: 'blob' }).then((r) => r.data),
  item: (id: string) => api.get<Item>(`/items/${id}`).then((r) => r.data),
  activity: (id: string) => api.get<ItemActivity>(`/items/${id}/activity`).then((r) => r.data),
  createItem: (input: ItemInput) => api.post<Item>('/items', input).then((r) => r.data),
  updateItem: (id: string, input: Partial<ItemInput>) =>
    api.patch<Item>(`/items/${id}`, input).then((r) => r.data),
  uploadPhoto: async (id: string, file: File) => {
    const form = new FormData()
    form.append('file', await prepareImage(file))
    return api.post<Item>(`/items/${id}/photo`, form).then((r) => r.data)
  },
  removePhoto: (id: string) => api.delete(`/items/${id}/photo`).then(() => undefined),
  updateUnit: (id: string, input: Partial<ItemUnit>) =>
    api.patch<ItemUnit>(`/units/${id}`, input).then((r) => r.data),
  labelsUrl: (id: string, count: number) => `/api/v1/items/${id}/labels?count=${count}`,
  packs: (period: { from?: string; to?: string }) =>
    api.get<Pack[]>('/packs', { params: period }).then((r) => r.data),
  savePack: (id: string | null, input: Partial<Pack>) =>
    (id ? api.patch<Pack>(`/packs/${id}`, input) : api.post<Pack>('/packs', input)).then(
      (r) => r.data,
    ),
  grid: (params: { from?: string; days: number; category?: string }) =>
    api
      .get<AvailabilityGrid>('/availability/grid', {
        params: { ...params, category: params.category || undefined },
      })
      .then((r) => r.data),
  movements: (filters: { kind?: string; item?: string; from?: string; to?: string }) =>
    api
      .get<Page<Movement>>('/stock-movements', {
        params: {
          kind: filters.kind || undefined,
          item: filters.item || undefined,
          from: filters.from || undefined,
          to: filters.to || undefined,
          pageSize: 100,
        },
      })
      .then((r) => r.data),
  recordMovement: (input: MovementInput) =>
    api.post<Movement>('/stock-movements', input).then((r) => r.data),
  cancelMovement: (id: string, reason: string) =>
    api.post<Movement>(`/stock-movements/${id}/cancel`, { reason }).then((r) => r.data),
  startMaintenance: (input: {
    item: string
    unit?: string | null
    quantity?: number
    reason: string
    expectedEnd?: string | null
  }) => api.post<Maintenance>('/maintenance', input).then((r) => r.data),
  closeMaintenance: (id: string, input: { cost?: number | null; notes?: string }) =>
    api.post<Maintenance>(`/maintenance/${id}/close`, input).then((r) => r.data),
  inventories: () => api.get<Inventory[]>('/inventories').then((r) => r.data),
  startInventory: (category: string | null) =>
    api.post<Inventory>('/inventories', { category }).then((r) => r.data),
  count: (id: string, counts: Record<string, number | null>) =>
    api.patch<Inventory>(`/inventories/${id}`, { counts }).then((r) => r.data),
  validateInventory: (id: string) =>
    api.post<Inventory>(`/inventories/${id}/validate`).then((r) => r.data),
  stats: () => api.get<StockStats>('/stock/stats').then((r) => r.data),
}

export const useItemCategories = () =>
  useQuery({ queryKey: stockKeys.categories(), queryFn: stockApi.categories, staleTime: 300_000 })

export function useItems(
  filters: MaybeRefOrGetter<{
    search?: string
    category?: string
    status?: string
    source?: string
  }>,
) {
  return useQuery({
    queryKey: computed(() => stockKeys.items({ ...toValue(filters) })),
    queryFn: () => stockApi.items(toValue(filters)),
    placeholderData: keepPreviousData,
  })
}

export function useItem(id: MaybeRefOrGetter<string | null>) {
  return useQuery({
    queryKey: computed(() => stockKeys.item(toValue(id) ?? '')),
    queryFn: () => stockApi.item(toValue(id)!),
    enabled: computed(() => Boolean(toValue(id))),
  })
}

export function useItemActivity(id: MaybeRefOrGetter<string | null>) {
  return useQuery({
    queryKey: computed(() => stockKeys.activity(toValue(id) ?? '')),
    queryFn: () => stockApi.activity(toValue(id)!),
    enabled: computed(() => Boolean(toValue(id))),
  })
}

export function usePacks(period: MaybeRefOrGetter<{ from?: string; to?: string }>) {
  return useQuery({
    queryKey: computed(() => stockKeys.packs({ ...toValue(period) })),
    queryFn: () => stockApi.packs(toValue(period)),
    placeholderData: keepPreviousData,
  })
}

export function useGrid(
  params: MaybeRefOrGetter<{ from?: string; days: number; category?: string }>,
) {
  return useQuery({
    queryKey: computed(() => stockKeys.grid({ ...toValue(params) })),
    queryFn: () => stockApi.grid(toValue(params)),
    placeholderData: keepPreviousData,
  })
}

export function useMovements(
  filters: MaybeRefOrGetter<{ kind?: string; item?: string; from?: string; to?: string }>,
) {
  return useQuery({
    queryKey: computed(() => stockKeys.movements({ ...toValue(filters) })),
    queryFn: () => stockApi.movements(toValue(filters)),
    placeholderData: keepPreviousData,
  })
}

export const useInventories = () =>
  useQuery({ queryKey: stockKeys.inventories(), queryFn: stockApi.inventories })

export const useStockStats = () =>
  useQuery({ queryKey: stockKeys.stats(), queryFn: stockApi.stats })

/** Any change to the stock: every stock view, the dashboard and the alerts follow. */
export function useStockMutation<TArgs, TResult>(fn: (args: TArgs) => Promise<TResult>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: stockKeys.all })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      void queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })
}

export function usePartnerSupplies(
  filters: MaybeRefOrGetter<{ search?: string; vendor?: string; item?: string }>,
) {
  return useQuery({
    queryKey: computed(() => stockKeys.partners({ ...toValue(filters) })),
    queryFn: () => stockApi.partnerSupplies(toValue(filters)),
    placeholderData: keepPreviousData,
  })
}

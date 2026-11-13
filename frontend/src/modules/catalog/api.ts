import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'

import { api } from '@/api/client'

import type { ServiceCategory, ServiceItem, ServiceItemInput } from './types'

export const catalogKeys = { all: ['catalog'] as const }

export const catalogApi = {
  categories: () => api.get<ServiceCategory[]>('/catalog/categories').then((r) => r.data),
  createCategory: (name: string) =>
    api.post<ServiceCategory>('/catalog/categories', { name }).then((r) => r.data),
  renameCategory: (id: string, name: string) =>
    api.patch<ServiceCategory>(`/catalog/categories/${id}`, { name }).then((r) => r.data),
  deleteCategory: (id: string) => api.delete(`/catalog/categories/${id}`).then(() => undefined),
  createItem: (input: ServiceItemInput) =>
    api.post<ServiceItem>('/catalog/items', input).then((r) => r.data),
  updateItem: (id: string, input: Partial<ServiceItemInput>) =>
    api.patch<ServiceItem>(`/catalog/items/${id}`, input).then((r) => r.data),
  deleteItem: (id: string) => api.delete(`/catalog/items/${id}`).then(() => undefined),
}

export function useCatalog() {
  return useQuery({ queryKey: catalogKeys.all, queryFn: catalogApi.categories, staleTime: 60_000 })
}

/** Every catalog mutation refreshes the whole catalog (small, loaded in one call). */
export function useCatalogMutation<TArgs, TResult>(fn: (args: TArgs) => Promise<TResult>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: catalogKeys.all }),
  })
}

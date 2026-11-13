import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { type MaybeRefOrGetter, computed, toValue } from 'vue'

import { api } from '@/api/client'

import type { Client, ClientFilters, ClientHistory, ClientInput } from './types'

interface Page<T> {
  results: T[]
  next: string | null
  previous: string | null
}

/** One large page (server maximum 300); the list says when there are more. */
export const CLIENT_PAGE_SIZE = 300

export const clientKeys = {
  all: ['clients'] as const,
  lists: () => [...clientKeys.all, 'list'] as const,
  list: (filters: ClientFilters) => [...clientKeys.lists(), filters] as const,
  detail: (id: string) => [...clientKeys.all, 'detail', id] as const,
  history: (id: string) => [...clientKeys.all, 'history', id] as const,
}

export const clientsApi = {
  list: (filters: ClientFilters) =>
    api
      .get<Page<Client>>('/clients', {
        params: {
          pageSize: CLIENT_PAGE_SIZE,
          search: filters.search || undefined,
          archived: filters.archived ? 'true' : undefined,
          ordering: filters.ordering || undefined,
        },
      })
      .then((r) => r.data),
  get: (id: string) => api.get<Client>(`/clients/${id}`).then((r) => r.data),
  history: (id: string) => api.get<ClientHistory>(`/clients/${id}/history`).then((r) => r.data),
  create: (input: ClientInput) => api.post<Client>('/clients', input).then((r) => r.data),
  update: (id: string, input: ClientInput) =>
    api.patch<Client>(`/clients/${id}`, input).then((r) => r.data),
  remove: (id: string) => api.delete(`/clients/${id}`).then(() => undefined),
}

export function useClients(filters: MaybeRefOrGetter<ClientFilters>) {
  return useQuery({
    queryKey: computed(() => clientKeys.list({ ...toValue(filters) })),
    queryFn: () => clientsApi.list(toValue(filters)),
    placeholderData: (previous) => previous,
  })
}

export function useClient(id: MaybeRefOrGetter<string | null>) {
  return useQuery({
    queryKey: computed(() => clientKeys.detail(toValue(id) ?? '')),
    queryFn: () => clientsApi.get(toValue(id)!),
    enabled: computed(() => Boolean(toValue(id))),
  })
}

export function useClientHistory(id: MaybeRefOrGetter<string | null>) {
  return useQuery({
    queryKey: computed(() => clientKeys.history(toValue(id) ?? '')),
    queryFn: () => clientsApi.history(toValue(id)!),
    enabled: computed(() => Boolean(toValue(id))),
  })
}

export function useCreateClient() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: clientsApi.create,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: clientKeys.lists() }),
  })
}

export function useUpdateClient() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: ClientInput }) => clientsApi.update(id, input),
    onSuccess: (client) => {
      queryClient.setQueryData(clientKeys.detail(client.id), client)
      void queryClient.invalidateQueries({ queryKey: clientKeys.lists() })
    },
  })
}

export function useDeleteClient() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: clientsApi.remove,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: clientKeys.lists() }),
  })
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, type MaybeRefOrGetter, toValue } from 'vue'

import { api } from '@/api/client'

import type { Task, TaskInput, Wedding, WeddingInput } from './types'

export const weddingKeys = {
  all: ['weddings'] as const,
  list: () => [...weddingKeys.all, 'list'] as const,
  detail: (id: string) => [...weddingKeys.all, 'detail', id] as const,
  tasks: (id: string) => [...weddingKeys.all, 'tasks', id] as const,
}

export const weddingsApi = {
  list: () => api.get<Wedding[]>('/weddings').then((r) => r.data),
  get: (id: string) => api.get<Wedding>(`/weddings/${id}`).then((r) => r.data),
  create: (input: WeddingInput) => api.post<Wedding>('/weddings', input).then((r) => r.data),
  update: (id: string, input: Partial<WeddingInput>) =>
    api.patch<Wedding>(`/weddings/${id}`, input).then((r) => r.data),
  tasks: (id: string) => api.get<Task[]>(`/weddings/${id}/tasks`).then((r) => r.data),
  addTask: (id: string, input: TaskInput) =>
    api.post<Task>(`/weddings/${id}/tasks`, input).then((r) => r.data),
  standardTasks: (id: string) =>
    api.post<Task[]>(`/weddings/${id}/standard-tasks`).then((r) => r.data),
  setDone: (id: string, done: boolean) =>
    api.post<Task>(`/tasks/${id}/done`, { done }).then((r) => r.data),
  removeTask: (id: string) => api.delete(`/tasks/${id}`).then(() => undefined),
}

export const useWeddings = () =>
  useQuery({ queryKey: weddingKeys.list(), queryFn: weddingsApi.list })

export function useWedding(id: MaybeRefOrGetter<string | null>) {
  return useQuery({
    queryKey: computed(() => weddingKeys.detail(toValue(id) ?? '')),
    queryFn: () => weddingsApi.get(toValue(id)!),
    enabled: computed(() => Boolean(toValue(id))),
  })
}

export function useTasks(id: MaybeRefOrGetter<string | null>) {
  return useQuery({
    queryKey: computed(() => weddingKeys.tasks(toValue(id) ?? '')),
    queryFn: () => weddingsApi.tasks(toValue(id)!),
    enabled: computed(() => Boolean(toValue(id))),
  })
}

/** Any change on a wedding or its tasks refreshes the weddings, the calendar and the dashboard. */
export function useWeddingAction<TArgs, TResult>(fn: (args: TArgs) => Promise<TResult>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: weddingKeys.all })
      void queryClient.invalidateQueries({ queryKey: ['calendar'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

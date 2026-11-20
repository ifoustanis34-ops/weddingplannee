import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, type MaybeRefOrGetter, toValue } from 'vue'

import { api } from '@/api/client'

import type { FloorPlan, FloorPlanInput } from './types'

export const floorPlanKeys = {
  all: ['floor-plans'] as const,
  list: () => [...floorPlanKeys.all, 'list'] as const,
  detail: (id: string) => [...floorPlanKeys.all, 'detail', id] as const,
}

export const floorPlansApi = {
  list: () => api.get<FloorPlan[]>('/floor-plans').then((r) => r.data),
  get: (id: string) => api.get<FloorPlan>(`/floor-plans/${id}`).then((r) => r.data),
  create: (input: FloorPlanInput) => api.post<FloorPlan>('/floor-plans', input).then((r) => r.data),
  update: (id: string, input: Partial<FloorPlanInput>) =>
    api.patch<FloorPlan>(`/floor-plans/${id}`, input).then((r) => r.data),
  remove: (id: string) => api.delete(`/floor-plans/${id}`).then(() => undefined),
}

export const useFloorPlans = () =>
  useQuery({ queryKey: floorPlanKeys.list(), queryFn: floorPlansApi.list })

export function useFloorPlan(id: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => floorPlanKeys.detail(toValue(id))),
    queryFn: () => floorPlansApi.get(toValue(id)),
  })
}

export function useFloorPlanAction<TArgs, TResult>(fn: (args: TArgs) => Promise<TResult>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: floorPlanKeys.all }),
  })
}

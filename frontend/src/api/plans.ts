import type { Plan } from './auth'
import { api } from './client'

/** Offer as stored in the database: prices never live in the front-end code. */
export interface SubscriptionPlan {
  code: Plan
  name: string
  description: string
  monthlyPrice: number
  maxUsers: number | null
  features: string[]
}

export const plansApi = {
  list: () => api.get<SubscriptionPlan[]>('/plans').then((r) => r.data),
}

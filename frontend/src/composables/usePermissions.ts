import { computed } from 'vue'

import type { Role } from '@/api/auth'
import { useSessionStore } from '@/stores/session'

/** UI-only hints mirroring CLAUDE.md §11. The server always has the final word. */
const RULES = {
  manageSettings: ['owner'],
  manageTeam: ['owner'],
  viewFinance: ['owner', 'planner', 'accountant'],
  manageFinance: ['owner', 'accountant'],
  viewMargins: ['owner', 'accountant'],
  editSales: ['owner', 'planner', 'assistant'],
  deleteSales: ['owner', 'planner'],
  manageCatalog: ['owner', 'planner'],
  convertQuote: ['owner', 'planner'],
  editWeddings: ['owner', 'planner', 'assistant'],
  // Stock (reservations-stock.md §12): owner and storekeeper run it, others consult it.
  viewStock: ['owner', 'planner', 'assistant', 'accountant', 'storekeeper'],
  editStock: ['owner', 'storekeeper'],
  /** Rental and sale prices: never for the storekeeper (« aucun montant »). */
  viewStockPrices: ['owner', 'planner', 'assistant', 'accountant'],
  /** Purchase costs and stock value. */
  viewStockCosts: ['owner', 'accountant'],
} as const satisfies Record<string, readonly Role[]>

export type Ability = keyof typeof RULES

export function usePermissions() {
  const session = useSessionStore()
  const role = computed(() => session.role)
  const can = (ability: Ability): boolean =>
    role.value !== null && (RULES[ability] as readonly Role[]).includes(role.value)
  return { role, can }
}

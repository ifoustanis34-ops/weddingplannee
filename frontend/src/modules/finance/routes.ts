import type { RouteRecordRaw } from 'vue-router'

export const financeRoutes: RouteRecordRaw[] = [
  {
    path: '/finances',
    name: 'finance',
    component: () => import('./pages/FinancePage.vue'),
    // Assistants have no access to money (CLAUDE.md §11).
    meta: { layout: 'app', auth: true, roles: ['owner', 'planner', 'accountant'] },
  },
]

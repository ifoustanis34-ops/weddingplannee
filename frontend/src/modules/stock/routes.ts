import type { RouteRecordRaw } from 'vue-router'

const STOCK_ROLES = ['owner', 'planner', 'assistant', 'accountant', 'storekeeper'] as const

export const stockRoutes: RouteRecordRaw[] = [
  {
    path: '/stock',
    name: 'stock',
    component: () => import('./pages/StockPage.vue'),
    meta: { layout: 'app', auth: true, roles: [...STOCK_ROLES] },
  },
  {
    path: '/mouvements',
    name: 'movements',
    component: () => import('./pages/MovementsPage.vue'),
    meta: { layout: 'app', auth: true, roles: [...STOCK_ROLES] },
  },
]

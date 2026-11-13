import type { RouteRecordRaw } from 'vue-router'

export const reservationRoutes: RouteRecordRaw[] = [
  {
    path: '/reservations',
    name: 'reservations',
    component: () => import('./pages/ReservationsPage.vue'),
    meta: {
      layout: 'app',
      auth: true,
      roles: ['owner', 'planner', 'assistant', 'accountant', 'storekeeper'],
    },
  },
]

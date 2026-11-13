import type { RouteRecordRaw } from 'vue-router'

export const reportRoutes: RouteRecordRaw[] = [
  {
    path: '/rapports',
    name: 'reports',
    component: () => import('./pages/ReportsPage.vue'),
    // §12: reports are for the owner and the accountant.
    meta: { layout: 'app', auth: true, roles: ['owner', 'accountant'] },
  },
]

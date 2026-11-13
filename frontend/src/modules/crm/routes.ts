import type { RouteRecordRaw } from 'vue-router'

export const crmRoutes: RouteRecordRaw[] = [
  {
    path: '/clients',
    name: 'clients',
    component: () => import('./pages/ClientsPage.vue'),
    meta: { layout: 'app', auth: true },
  },
  // Old address of the removed prospect pipeline: no dead link.
  { path: '/prospects', redirect: { name: 'clients' } },
  { path: '/relances', redirect: { name: 'dashboard' } },
]

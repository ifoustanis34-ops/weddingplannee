import type { RouteRecordRaw } from 'vue-router'

export const catalogRoutes: RouteRecordRaw[] = [
  {
    path: '/catalogue',
    name: 'catalog',
    component: () => import('./pages/CatalogPage.vue'),
    meta: { layout: 'app', auth: true },
  },
]

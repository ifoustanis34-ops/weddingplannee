import type { RouteRecordRaw } from 'vue-router'

export const eventRoutes: RouteRecordRaw[] = [
  {
    path: '/mariages',
    name: 'weddings',
    component: () => import('./pages/WeddingsPage.vue'),
    meta: { layout: 'app', auth: true, module: 'weddings' },
  },
]

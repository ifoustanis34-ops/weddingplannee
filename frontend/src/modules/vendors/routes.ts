import type { RouteRecordRaw } from 'vue-router'

/** « Fournisseurs » (renamed from « Prestataires » on 13/11/2026; the old address still works). */
export const vendorRoutes: RouteRecordRaw[] = [
  {
    path: '/fournisseurs',
    name: 'vendors',
    component: () => import('./pages/VendorsPage.vue'),
    meta: { layout: 'app', auth: true },
  },
  { path: '/prestataires', redirect: { name: 'vendors' } },
]

import type { RouteRecordRaw } from 'vue-router'

/** « Croquis » (feedback 20/11/2026): plans of the venues, drawn to scale. */
export const floorPlanRoutes: RouteRecordRaw[] = [
  {
    path: '/croquis',
    name: 'floorplans',
    component: () => import('./pages/FloorPlansPage.vue'),
    meta: { layout: 'app', auth: true },
  },
  {
    path: '/croquis/:id',
    name: 'floorplan-edit',
    component: () => import('./pages/FloorPlanEditorPage.vue'),
    meta: { layout: 'app', auth: true, navKey: 'floorplans' },
  },
]

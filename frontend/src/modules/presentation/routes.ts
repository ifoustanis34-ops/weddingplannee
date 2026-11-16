import type { RouteRecordRaw } from 'vue-router'

/** Presentation mode (feedback 16/11/2026): choose a journey the app then plays by itself. */
export const presentationRoutes: RouteRecordRaw[] = [
  {
    path: '/presentation',
    name: 'presentation',
    component: () => import('./pages/PresentationPage.vue'),
    meta: { layout: 'app', auth: true },
  },
]

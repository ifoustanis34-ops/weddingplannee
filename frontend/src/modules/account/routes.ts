import type { RouteRecordRaw } from 'vue-router'

/** « Mon profil »: every signed-in person, whatever the role (feedback 13/11/2026). */
export const accountRoutes: RouteRecordRaw[] = [
  {
    path: '/profil',
    name: 'profile',
    component: () => import('./pages/ProfilePage.vue'),
    meta: { layout: 'app', auth: true },
  },
]

import type { RouteRecordRaw } from 'vue-router'

/** Platform console (super-admin, 14/11/2026). Not /admin: Nginx sends it to Django. */
export const platformRoutes: RouteRecordRaw[] = [
  {
    path: '/plateforme',
    name: 'platform-overview',
    component: () => import('./pages/OverviewPage.vue'),
    meta: { layout: 'platform', auth: true, platform: true },
  },
  {
    path: '/plateforme/agences',
    name: 'platform-agencies',
    component: () => import('./pages/AgenciesPage.vue'),
    meta: { layout: 'platform', auth: true, platform: true },
  },
  {
    path: '/plateforme/utilisateurs',
    name: 'platform-accounts',
    component: () => import('./pages/AccountsPage.vue'),
    meta: { layout: 'platform', auth: true, platform: true },
  },
  {
    path: '/plateforme/journal',
    name: 'platform-journal',
    component: () => import('./pages/JournalPage.vue'),
    meta: { layout: 'platform', auth: true, platform: true },
  },
  {
    path: '/plateforme/profil',
    name: 'platform-profile',
    component: () => import('@/modules/account/pages/ProfilePage.vue'),
    meta: { layout: 'platform', auth: true, platform: true },
  },
]

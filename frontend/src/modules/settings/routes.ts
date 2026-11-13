import type { RouteRecordRaw } from 'vue-router'

export const SETTINGS_TABS = [
  'entreprise',
  'identite',
  'equipe',
  'catalogue',
  'abonnement',
  'integrations',
] as const
export type SettingsTab = (typeof SETTINGS_TABS)[number]

export const settingsRoutes: RouteRecordRaw[] = [
  {
    path: '/parametres/:tab?',
    name: 'settings',
    component: () => import('./pages/SettingsPage.vue'),
    meta: { layout: 'app', auth: true, roles: ['owner'] },
  },
]

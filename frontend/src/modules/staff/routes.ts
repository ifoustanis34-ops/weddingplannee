import type { RouteRecordRaw } from 'vue-router'

export const staffRoutes: RouteRecordRaw[] = [
  {
    path: '/personnel',
    name: 'staff',
    component: () => import('./pages/StaffPage.vue'),
    meta: { layout: 'app', auth: true, roles: ['owner', 'planner', 'assistant', 'accountant'] },
  },
  {
    path: '/taches',
    name: 'tasks',
    component: () => import('./pages/TasksPage.vue'),
    meta: { layout: 'app', auth: true, roles: ['owner', 'planner', 'assistant', 'accountant'] },
  },
  {
    // What the badge QR opens: public, no account (feedback 13/11/2026).
    path: '/b/:token',
    name: 'public-badge',
    component: () => import('./pages/PublicBadgePage.vue'),
    meta: { layout: 'blank' },
  },
  {
    path: '/paie',
    name: 'pay',
    component: () => import('./pages/PayPage.vue'),
    // Pay: owner and accountant (§12).
    meta: { layout: 'app', auth: true, roles: ['owner', 'accountant'] },
  },
  {
    path: '/presences',
    name: 'attendance',
    component: () => import('./pages/AttendancePage.vue'),
    meta: { layout: 'app', auth: true, roles: ['owner', 'planner', 'accountant'] },
  },
  {
    path: '/mes-missions',
    name: 'missions',
    component: () => import('./pages/MissionsPage.vue'),
    meta: { layout: 'app', auth: true },
  },
]

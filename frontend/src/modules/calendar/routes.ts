import type { RouteRecordRaw } from 'vue-router'

export const calendarRoutes: RouteRecordRaw[] = [
  {
    path: '/calendrier',
    name: 'calendar',
    component: () => import('./pages/CalendarPage.vue'),
    meta: { layout: 'app', auth: true },
  },
]

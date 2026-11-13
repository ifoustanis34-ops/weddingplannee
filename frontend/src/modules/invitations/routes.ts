import type { RouteRecordRaw } from 'vue-router'

export const invitationRoutes: RouteRecordRaw[] = [
  {
    path: '/mariages/:id/billets',
    name: 'wedding-tickets',
    component: () => import('./pages/TicketsPage.vue'),
    meta: { layout: 'app', auth: true, navKey: 'weddings', module: 'weddings' },
  },
  {
    // The guest's page from the QR or the email link: no account (§6).
    path: '/t/:token',
    name: 'public-ticket',
    component: () => import('./pages/PublicTicketPage.vue'),
    meta: { layout: 'blank' },
  },
]

import type { RouteRecordRaw } from 'vue-router'

export const quoteRoutes: RouteRecordRaw[] = [
  {
    path: '/devis',
    name: 'quotes',
    component: () => import('./pages/QuotesPage.vue'),
    meta: { layout: 'app', auth: true },
  },
  {
    path: '/devis/nouveau',
    name: 'quote-new',
    component: () => import('./pages/QuoteEditorPage.vue'),
    meta: { layout: 'app', auth: true, navKey: 'quotes' },
  },
  {
    path: '/devis/:id',
    name: 'quote-edit',
    component: () => import('./pages/QuoteEditorPage.vue'),
    meta: { layout: 'app', auth: true, navKey: 'quotes' },
  },
  // Public link sent by email (backend quotes/services.py public_url).
  {
    path: '/proposition/:token',
    name: 'quote-public',
    component: () => import('./pages/PublicQuotePage.vue'),
    meta: { layout: 'blank' },
  },
]

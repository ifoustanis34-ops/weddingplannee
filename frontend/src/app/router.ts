import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { accountRoutes } from '@/modules/account/routes'
import { calendarRoutes } from '@/modules/calendar/routes'
import { catalogRoutes } from '@/modules/catalog/routes'
import { crmRoutes } from '@/modules/crm/routes'
import { eventRoutes } from '@/modules/events/routes'
import { invitationRoutes } from '@/modules/invitations/routes'
import { financeRoutes } from '@/modules/finance/routes'
import { quoteRoutes } from '@/modules/quotes/routes'
import { platformRoutes } from '@/modules/platform/routes'
import { settingsRoutes } from '@/modules/settings/routes'
import { reportRoutes } from '@/modules/reports/routes'
import { staffRoutes } from '@/modules/staff/routes'
import { reservationRoutes } from '@/modules/reservations/routes'
import { stockRoutes } from '@/modules/stock/routes'
import { vendorRoutes } from '@/modules/vendors/routes'
import { FIELD_ROLES, type Role } from '@/api/auth'
import { visibleNavItems } from '@/app/navigation'
import { useToast } from '@/composables/useToast'
import { i18n } from '@/i18n'
import { useSessionStore } from '@/stores/session'

declare module 'vue-router' {
  interface RouteMeta {
    layout?: 'auth' | 'app' | 'platform' | 'blank'
    /** Platform console: Wedivo team only (the API enforces it too). */
    platform?: boolean
    /** Requires a signed-in user. */
    auth?: boolean
    /** Only for signed-out visitors (login, signup...). */
    guest?: boolean
    /** Roles allowed on the page (UI hint; the API enforces the same rules). */
    roles?: Role[]
    /** Menu entry highlighted for this page when its route name differs (editor → « Devis »). */
    navKey?: string
    /** Page of a module that each space turns on (« Mariages », 13/11/2026). */
    module?: 'weddings'
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'dashboard',
    component: () => import('@/modules/dashboard/pages/HomePage.vue'),
    meta: { layout: 'app', auth: true },
  },
  ...crmRoutes,
  ...quoteRoutes,
  ...financeRoutes,
  ...catalogRoutes,
  ...settingsRoutes,
  ...eventRoutes,
  ...invitationRoutes,
  ...calendarRoutes,
  ...vendorRoutes,
  ...stockRoutes,
  ...reservationRoutes,
  ...reportRoutes,
  ...staffRoutes,
  ...accountRoutes,
  ...platformRoutes,
  {
    // Team invitation link (backend accounts/tasks.py).
    path: '/invitation/:token',
    name: 'invitation',
    component: () => import('@/modules/auth/pages/InvitationPage.vue'),
    meta: { layout: 'auth' },
  },
  {
    path: '/connexion',
    name: 'login',
    component: () => import('@/modules/auth/pages/LoginPage.vue'),
    meta: { layout: 'auth', guest: true },
  },
  {
    path: '/inscription',
    name: 'signup',
    component: () => import('@/modules/auth/pages/SignupPage.vue'),
    meta: { layout: 'auth', guest: true },
  },
  {
    path: '/mot-de-passe-oublie',
    name: 'forgot-password',
    component: () => import('@/modules/auth/pages/ForgotPasswordPage.vue'),
    meta: { layout: 'auth', guest: true },
  },
  {
    // Link sent by email (backend accounts/tasks.py).
    path: '/reinitialiser-mot-de-passe',
    name: 'reset-password',
    component: () => import('@/modules/auth/pages/ResetPasswordPage.vue'),
    meta: { layout: 'auth' },
  },
  {
    // Link sent by email (backend accounts/tasks.py).
    path: '/verifier-email',
    name: 'verify-email',
    component: () => import('@/modules/auth/pages/VerifyEmailPage.vue'),
    meta: { layout: 'auth' },
  },
  // Design system gallery, development builds only (tree-shaken from production).
  ...(import.meta.env.DEV
    ? [
        {
          path: '/dev/ui',
          name: 'dev-ui',
          component: () => import('@/app/dev/DevUiPage.vue'),
          meta: { layout: 'blank' as const },
        },
      ]
    : []),
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/app/NotFoundPage.vue'),
    meta: { layout: 'blank' },
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
  // New page: back to the top. Same page with another query (filters, opened drawer): stay put.
  scrollBehavior: (to, from, saved) => saved ?? (to.path === from.path ? false : { top: 0 }),
})

router.beforeEach(async (to, from) => {
  const session = useSessionStore()
  try {
    await session.bootstrap()
  } catch {
    // Server unreachable: public pages stay usable; private ones wait behind the login page,
    // which explains the problem when the visitor tries to sign in.
    return to.meta.auth ? { name: 'login', query: { redirect: to.fullPath } } : true
  }
  if (to.meta.auth && !session.isAuthenticated) {
    return { name: 'login', query: to.fullPath !== '/' ? { redirect: to.fullPath } : {} }
  }
  const isPlatformAdmin = !!session.user?.isPlatformAdmin
  const noSpace = session.organizations.length === 0
  if (to.meta.guest && session.isAuthenticated) {
    return { name: isPlatformAdmin && noSpace ? 'platform-overview' : 'dashboard' }
  }
  // An account opened with a temporary password chooses its own before anything else.
  if (session.user?.mustChangePassword && to.meta.auth) {
    const profile = isPlatformAdmin && noSpace ? 'platform-profile' : 'profile'
    if (to.name !== 'profile' && to.name !== 'platform-profile') {
      // Coming from a page of the app (a menu click): say why nothing else opens yet.
      if (from.name === 'profile' || from.name === 'platform-profile') {
        useToast().info(i18n.global.t('profile.mustChangeFirst'))
      }
      return { name: profile }
    }
  }
  // Platform console (super-admin, 14/11/2026): Wedivo team only.
  if (to.meta.platform) return isPlatformAdmin ? true : { name: 'dashboard' }
  // A Wedivo team account with no agency space lands in the console.
  if (to.meta.layout === 'app' && isPlatformAdmin && noSpace) return { name: 'platform-overview' }
  if (to.name === 'profile') return true // « Mon profil »: every role
  if (to.meta.module === 'weddings' && !session.weddingsEnabled) return { name: 'dashboard' }
  if (to.meta.roles && (!session.role || !to.meta.roles.includes(session.role))) {
    return { name: 'dashboard' }
  }
  // Field roles (storekeeper, team lead, staff) only open what is theirs (reservations-stock.md
  // §12); the API refuses the rest anyway.
  if (
    to.meta.layout === 'app' &&
    session.role &&
    FIELD_ROLES.includes(session.role) &&
    !visibleNavItems(session.role, session.weddingsEnabled).some(
      (item) => item.routeName === to.name,
    )
  ) {
    return to.name === 'dashboard' ? true : { name: 'dashboard' }
  }
  return true
})

/** Only accept internal redirects (no open redirect through `?redirect=`). */
export function safeRedirect(value: unknown): string {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') ? value : '/'
}

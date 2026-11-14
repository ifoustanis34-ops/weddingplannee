import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { api } from '@/api/client'
import { i18n } from '@/i18n'
import type { DashboardSummary } from '@/modules/dashboard/api'
import { barsGeometry, ringSegments, signedPct, sparkline } from '@/modules/dashboard/charts'
import DashboardPage from '@/modules/dashboard/pages/DashboardPage.vue'
import { useSessionStore } from '@/stores/session'

vi.mock('@/api/client', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() },
  configureApi: vi.fn(),
}))
const NNBSP = ' '

const month = (label: string, income: number, expenses: number) => ({
  month: `2026-${label}`,
  label,
  revenue: income,
  income,
  expenses,
  profit: income - expenses,
})

const summary: DashboardSummary = {
  period: {
    key: 'month',
    start: '2026-11-01',
    end: '2026-11-30',
    previousStart: '2026-10-01',
    previousEnd: '2026-10-31',
  },
  isNew: false,
  today: {
    date: '2026-11-12',
    weddingsToday: 0,
    weddingsWeek: 1,
    tasksToday: 2,
    paymentsToday: 1,
    deliveriesToday: 1,
    returnsToday: 0,
    eventsToday: 0,
  },
  signature: {
    revenue: 2_600_000,
    revenueVariation: 12.5,
    collected: 2_420_000,
    toCollect: 10_480_000,
    profit: 647_000,
    profitVariation: -4,
  },
  performance: {
    utilisation: null,
    utilisationDelta: null,
    marginAvg: 32,
    marginAvgDelta: -7.8,
    basketAvg: 2_600_000,
    basketAvgVariation: -11,
    quoteConfirmation: 100,
    quoteConfirmationDelta: 0,
    collectionRate: 82.3,
    collectionRateDelta: -7.4,
  },
  orders: { confirmed: 3, pending: 2, cancelled: 1 },
  topServices: [{ name: 'Décoration de salle', count: 4, revenue: 3_600_000 }],
  materialToday: {
    available: 1_250,
    categories: [{ name: 'Mobilier', available: 1_250, reserved: 30, out: 0, maintenance: 5 }],
  },
  upcomingWeddings: [
    {
      id: 'w1',
      title: 'Mariam & Idriss',
      date: '2026-11-15',
      days: 3,
      venue: 'Salle Bellevue',
      progress: 75,
      tasksTotal: 12,
    },
  ],
  monthly: Array.from({ length: 12 }, (_, i) =>
    month(String(i + 1).padStart(2, '0'), 1_000_000 + i * 100_000, 600_000),
  ),
  expensesByCategory: [
    { id: 'c1', name: 'Sous-traitance', slot: 1, amount: 1_770_000 },
    { id: 'c2', name: 'Loyer de l’entrepôt', slot: 2, amount: 150_000 },
    { id: null, name: null, slot: 0, amount: 42_500 },
  ],
  balances: [
    {
      contract: 'k1',
      reservation: null,
      number: 'CT-2026-0004',
      clientName: 'Famille Ekotto',
      balance: 1_200_000,
      dueDate: '2026-10-31',
      isOverdue: true,
    },
  ],
  planning: Array.from({ length: 7 }, (_, i) => ({
    date: `2026-11-${12 + i}`,
    items:
      i === 3
        ? [
            {
              kind: 'event' as const,
              id: 'w1',
              title: 'Mariam & Idriss',
              subtitle: 'Salle Bellevue',
              team: ['Yao Kouassi'],
              wedding: 'w1',
            },
          ]
        : [],
  })),
  alerts: [
    {
      id: 'a1',
      kind: 'overdue_payment',
      severity: 'critical',
      title: 'Famille Ekotto',
      subtitle: 'Acompte',
      amount: 360_000,
      days: 12,
      date: '2026-10-31',
      contract: 'k1',
    },
  ],
  teamToday: [{ name: 'Yao Kouassi', total: 1, done: 0, status: 'todo' }],
  starter: { catalogItems: 15, clients: 11, hasLogo: true, teamMembers: 4 },
}

function setup(role: 'owner' | 'planner' | 'assistant' | 'accountant' = 'owner') {
  const pinia = createPinia()
  setActivePinia(pinia)
  const session = useSessionStore()
  session.user = {
    id: 'u1',
    email: 'a@b.ci',
    fullName: 'Aïcha Koné',
    phone: '',
    isVerified: true,
    mustChangePassword: false,
    isPlatformAdmin: false,
  }
  session.organizations = [
    {
      organizationId: 'o1',
      slug: 'm',
      name: 'Maison Élégance',
      role,
      roleLabel: '',
      weddingsEnabled: true,
    },
  ]
  session.status = 'authenticated'
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      'dashboard',
      'finance',
      'clients',
      'catalog',
      'quotes',
      'quote-new',
      'weddings',
      'settings',
      'stock',
      'reservations',
      'calendar',
    ].map((name) => ({
      path: name === 'dashboard' ? '/' : `/${name}`,
      name,
      component: { template: '<div />' },
    })),
  })
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return { router, global: { plugins: [pinia, i18n, router, [VueQueryPlugin, { queryClient }]] } }
}

async function mountPage(role: Parameters<typeof setup>[0], data: Partial<DashboardSummary> = {}) {
  // Same shapes as the API: the lists are plain arrays (no pagination on these views), the
  // organization an object. Any other address is refused, never answered with a wrong shape.
  const responses: Record<string, unknown> = {
    '/dashboard/summary': { ...summary, ...data },
    '/organization': { name: 'Maison Élégance Events', timezone: 'Africa/Douala' },
    '/contracts': [],
    '/reservations': [],
    '/weddings': [],
  }
  vi.mocked(api.get).mockImplementation((url: string) =>
    url in responses
      ? Promise.resolve({ data: responses[url] })
      : Promise.reject(new Error(`Unexpected GET ${url} in the dashboard test`)),
  )
  const { router, global } = setup(role)
  await router.push('/')
  const wrapper = mount(DashboardPage, { attachTo: document.body, global: global as never })
  await flushPromises()
  return { wrapper, router }
}

beforeEach(() => {
  // Count-up animations finish at once (reduced motion).
  window.matchMedia = vi.fn().mockReturnValue({ matches: true }) as never
})
afterEach(() => {
  vi.clearAllMocks()
  document.body.innerHTML = ''
})

describe('dashboard geometry', () => {
  it('splits a ring with a gap between segments and none for a lone one', () => {
    const [a, b] = ringSegments([3, 1], 50)
    const circumference = 2 * Math.PI * 50
    expect(a!.share).toBe(0.75)
    expect(Number(a!.dash.split(' ')[0])).toBeCloseTo(circumference * 0.75 - 2, 1)
    expect(b!.offset).toBeCloseTo(-circumference * 0.75, 1)
    const [single] = ringSegments([0, 5], 50)
    expect(Number(single!.dash.split(' ')[0])).toBeCloseTo(circumference, 1)
    expect(ringSegments([0, 0], 50)).toEqual([])
  })

  it('keeps one axis and lets the profit line go below zero', () => {
    const geometry = barsGeometry([
      { income: 1_000_000, expenses: 400_000, profit: 600_000 },
      { income: 200_000, expenses: 700_000, profit: -500_000 },
    ])
    expect(geometry.ticks[0]!.value).toBeLessThan(0)
    expect(geometry.columns[1]!.profit!.y).toBeGreaterThan(geometry.zeroY)
    // Bars rise from zero.
    const income = geometry.columns[0]!.income
    expect(income.y + income.height).toBeCloseTo(geometry.zeroY, 1)
  })

  it('draws a sparkline and formats signed changes', () => {
    expect(sparkline([1, 2, 3], 100, 40).last).toEqual({ x: 96, y: 4 })
    expect(signedPct(12.5)).toBe('+12,5 %')
    expect(signedPct(-3)).toBe('−3 %')
    expect(signedPct(null)).toBeNull()
  })
})

describe('DashboardPage', () => {
  it('opens on the signature zone, the day summary and every block', async () => {
    const { wrapper } = await mountPage('owner')

    expect(wrapper.get('[data-testid="signature-revenue"]').text()).toBe(`2${NNBSP}600${NNBSP}000`)
    expect(wrapper.text()).toMatch(/\+12,5\s%\svs période précédente/)
    expect(wrapper.get('[data-testid="dashboard-summary"]').text()).toContain(
      '1 mariage cette semaine, 2 tâches prévues, 1 échéance de paiement et 1 alerte.',
    )
    for (const title of [
      'Performance',
      'Réservations',
      'Prestations les plus demandées',
      'Matériel aujourd’hui',
      'Recettes et dépenses',
      'Dépenses par catégorie',
      'Soldes à encaisser',
      'Planning des 7 prochains jours',
      'Alertes',
      'Équipe du jour',
    ])
      expect(wrapper.text()).toContain(title)
    expect(wrapper.text()).toContain('Marge moyenne')
    expect(wrapper.text()).toContain('Encaissement des échéances') // until the stock module
    expect(wrapper.text()).toContain('Autres') // folded categories
    expect(wrapper.text()).not.toMatch(/relance|prospect|Temps gagné/i)
  })

  it('switches the period through the address', async () => {
    const { wrapper, router } = await mountPage('owner')

    await wrapper.get('[role="radio"][aria-checked="false"]').trigger('click') // « Aujourd'hui »
    await flushPromises()

    expect(router.currentRoute.value.query.periode).toBe('today')
    expect(vi.mocked(api.get)).toHaveBeenLastCalledWith('/dashboard/summary', {
      params: { period: 'today' },
    })
  })

  it('keeps money away from the assistant', async () => {
    const { wrapper } = await mountPage('assistant', {
      signature: null,
      performance: null,
      monthly: null,
      expensesByCategory: null,
      balances: null,
      today: { ...summary.today, paymentsToday: null },
    })

    expect(wrapper.find('[data-testid="signature-revenue"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Tâches prévues aujourd’hui')
    expect(wrapper.text()).not.toContain('Recettes et dépenses')
    expect(wrapper.text()).not.toContain('Soldes à encaisser')
    expect(wrapper.text()).not.toContain('Enregistrer une dépense')
  })

  it('welcomes a new space instead of empty charts', async () => {
    const { wrapper } = await mountPage('owner', {
      isNew: true,
      starter: { catalogItems: 0, clients: 0, hasLogo: false, teamMembers: 1 },
    })

    expect(wrapper.text()).toContain('Votre activité s’affichera ici')
    expect(wrapper.text()).toContain('Compléter votre catalogue')
    expect(wrapper.text()).not.toContain('Recettes et dépenses')
  })
})

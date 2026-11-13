import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { type Component, nextTick } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import { api } from '@/api/client'
import { i18n } from '@/i18n'
import ContractDrawer from '@/modules/finance/components/ContractDrawer.vue'
import PaymentModal from '@/modules/finance/components/PaymentModal.vue'
import { useSessionStore } from '@/stores/session'

vi.mock('@/api/client', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() },
  configureApi: vi.fn(),
}))
const NNBSP = ' '
const contractRow = {
  id: 'c1',
  number: 'CT-2026-0001',
  client: 'p1',
  clientName: 'Awa & Moussa',
  weddingDate: '2026-12-19',
  wedding: 'w1',
  total: 1_500_000,
  collected: 500_000,
  balance: 1_000_000,
  expenses: 900_000,
  margin: 600_000,
  marginPct: 40,
  progress: 33,
  status: 'active',
  statusLabel: 'En cours',
  signedAt: '2026-10-01T10:00:00Z',
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
      '/',
      '/finances',
      '/clients',
      '/catalogue',
      '/devis/:id',
      '/devis/nouveau',
      '/mariages',
    ].map((path, i) => ({
      path,
      name: ['dashboard', 'finance', 'clients', 'catalog', 'quote-edit', 'quote-new', 'weddings'][
        i
      ],
      component: { template: '<div />' },
    })),
  })
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return { global: { plugins: [pinia, i18n, router, [VueQueryPlugin, { queryClient }]] } }
}

async function mountWith(
  component: Component,
  role: Parameters<typeof setup>[0],
  props: Record<string, unknown> = {},
) {
  const wrapper = mount(
    component as never,
    { props, attachTo: document.body, ...setup(role) } as never,
  )
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.mocked(api.get).mockImplementation((url: string) => {
    if (url === '/contracts') return Promise.resolve({ data: [contractRow] })
    if (url === '/contracts/c1')
      return Promise.resolve({
        data: {
          ...contractRow,
          clientEmail: '',
          clientPhone: '',
          quote: { id: 'q1', number: 'DV-2026-0001' },
          schedule: [
            {
              id: 's1',
              label: 'Acompte',
              amount: 450_000,
              dueDate: '2026-10-01',
              paid: 450_000,
              remaining: 0,
              isPaid: true,
              isOverdue: false,
            },
          ],
          payments: [],
          expenseItems: [
            { id: 'e1', label: 'Traiteur', amount: 900_000, date: null, isPaid: false },
          ],
        },
      })
    return Promise.resolve({ data: {} })
  })
})
afterEach(() => {
  vi.clearAllMocks()
  document.body.innerHTML = ''
})

describe('PaymentModal', () => {
  it('refuses an amount above the balance before calling the API', async () => {
    await mountWith(PaymentModal, 'owner', { open: true, contractId: 'c1' })
    const dialog = document.querySelector('[role="dialog"]') as HTMLElement
    const amount = dialog.querySelector('input[type="number"]') as HTMLInputElement
    amount.value = '1500000'
    amount.dispatchEvent(new Event('input'))
    ;(dialog.querySelector('form') as HTMLFormElement).dispatchEvent(new Event('submit'))
    await flushPromises()

    expect(api.post).not.toHaveBeenCalled()
    expect(dialog.textContent).toContain(
      `Le montant dépasse le solde restant (1${NNBSP}000${NNBSP}000 FCFA).`,
    )
  })

  it('records a valid payment as multipart', async () => {
    vi.mocked(api.post).mockImplementation(() => Promise.resolve({ data: {} }))
    await mountWith(PaymentModal, 'owner', { open: true, contractId: 'c1' })
    const dialog = document.querySelector('[role="dialog"]') as HTMLElement
    const amount = dialog.querySelector('input[type="number"]') as HTMLInputElement
    amount.value = '500000'
    amount.dispatchEvent(new Event('input'))
    ;(dialog.querySelector('form') as HTMLFormElement).dispatchEvent(new Event('submit'))
    await flushPromises()

    const [url, body] = vi.mocked(api.post).mock.calls[0]!
    expect(url).toBe('/contracts/c1/payments')
    expect((body as FormData).get('amount')).toBe('500000')
    expect((body as FormData).get('method')).toBe('orange_money')
  })
})

describe('ContractDrawer', () => {
  it('shows the margin with its mandatory notice', async () => {
    await mountWith(ContractDrawer, 'owner', { contractId: 'c1' })
    await nextTick()
    const drawer = document.querySelector('[role="dialog"]') as HTMLElement

    expect(drawer.textContent).toContain('Ce n’est pas le bénéfice net comptable de l’entreprise.')
    expect(drawer.textContent).toContain('Traiteur')
    expect(drawer.textContent).toContain('Payé')
  })
})

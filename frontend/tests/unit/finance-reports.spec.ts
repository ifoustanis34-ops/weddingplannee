import { flushPromises } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Role } from '@/api/auth'
import { api } from '@/api/client'
import ReportTable from '@/modules/finance/components/ReportTable.vue'
import FinancePage from '@/modules/finance/pages/FinancePage.vue'
import { useSessionStore } from '@/stores/session'

import { mountWithPlugins } from './helpers'

const TREASURY = {
  period: { start: '2026-11-01', end: '2026-11-30', key: 'month' },
  collected: 2_400_000,
  toCollect: 5_100_000,
  spent: 900_000,
  balance: 1_500_000,
  previous: { collected: 2_000_000, spent: 1_000_000, balance: 1_000_000 },
  invoicesOpen: 1_200_000,
  invoicesOverdue: { count: 2, amount: 480_000 },
  revenueByCategory: [{ category: 'rental', label: 'Location', amount: 1_600_000 }],
  expensesByCategory: [{ category: 'Carburant', amount: 300_000 }],
  monthly: [{ month: '2026-11-01', cashIn: 2_400_000, cashOut: 900_000, net: 1_500_000 }],
}

vi.mock('@/api/client', () => ({
  api: {
    get: vi.fn((url: string) =>
      Promise.resolve({ data: url === '/finance/treasury' ? TREASURY : [] }),
    ),
    post: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
  configureApi: vi.fn(),
}))

afterEach(() => {
  document.body.innerHTML = ''
  vi.mocked(api.get).mockClear()
})

function signIn(role: Role): void {
  const session = useSessionStore()
  session.user = {
    id: 'u1',
    email: 'a@b.ci',
    fullName: 'Awa Sangaré',
    phone: '',
    isVerified: true,
    mustChangePassword: false,
  }
  session.organizations = [
    { organizationId: 'o1', slug: 'm', name: 'M', role, roleLabel: '', weddingsEnabled: true },
  ]
  session.selectOrganization('m')
}

describe('ReportTable', () => {
  it('formats money, percentages, months and totals; losses in red', () => {
    const { wrapper } = mountWithPlugins(ReportTable, {
      props: {
        caption: 'Marge',
        columns: [
          { key: 'month', label: 'Mois', kind: 'month' },
          { key: 'margin', label: 'Marge', kind: 'money' },
          { key: 'margin_pct', label: 'Marge %', kind: 'pct' },
          { key: 'variation_pct', label: 'Évolution', kind: 'pct' },
        ],
        rows: [
          { month: '2026-11-01', margin: 1_250_000, marginPct: 34.5, variationPct: 12 },
          { month: '2026-10-01', margin: -98_000, marginPct: -15.1, variationPct: null },
        ],
        totals: { margin: 1_152_000 },
      },
    })
    const text = wrapper.text()
    expect(text).toContain('Novembre 2026')
    expect(text).toMatch(/1\s250\s000/)
    expect(text).toContain('34,5 %')
    expect(text).toContain('+12 %') // a variation carries its sign
    expect(text).toContain('—') // nothing to compare with
    expect(wrapper.findAll('td.text-red').length).toBe(2) // the loss and its percentage
    expect(wrapper.find('tfoot').text()).toMatch(/Total.*1\s152\s000/)
  })
})

describe('FinancePage tabs', () => {
  it('opens on the treasury for the owner and hides margins from the planner', async () => {
    const owner = mountWithPlugins(FinancePage)
    signIn('owner')
    await flushPromises()
    const ownerTabs = owner.wrapper.findAll('[role="tab"]').map((tab) => tab.text())
    expect(ownerTabs).toEqual([
      'Trésorerie',
      'Factures',
      'Recettes',
      'Dépenses',
      'Rentabilité',
      'Contrats',
    ])
    expect(vi.mocked(api.get).mock.calls.some(([url]) => url === '/finance/treasury')).toBe(true)
    owner.wrapper.unmount()

    const planner = mountWithPlugins(FinancePage)
    signIn('planner')
    await flushPromises()
    expect(planner.wrapper.findAll('[role="tab"]').map((tab) => tab.text())).toEqual([
      'Factures',
      'Recettes',
      'Contrats',
    ])
  })
})

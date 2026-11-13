import { flushPromises } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { api } from '@/api/client'
import AlertCenter from '@/modules/alerts/components/AlertCenter.vue'
import { useSessionStore } from '@/stores/session'

import { mountWithPlugins } from './helpers'

vi.mock('@/api/client', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() },
  configureApi: vi.fn(),
}))

const ALERTS = {
  count: 2,
  results: [
    {
      id: 'a1',
      kind: 'overdue_payment',
      severity: 'critical',
      title: 'Famille Ekotto',
      amount: 360_000,
      days: 12,
      date: '2026-10-31',
      contract: 'k1',
    },
    {
      id: 'a2',
      kind: 'late_tasks',
      severity: 'warning',
      title: 'Mariam & Idriss',
      count: 3,
      date: '2026-11-10',
      wedding: 'w1',
    },
  ],
}

async function mountBell() {
  vi.mocked(api.get).mockResolvedValue({ data: ALERTS })
  vi.mocked(api.post).mockResolvedValue({ data: ALERTS.results[0] })
  const mounted = mountWithPlugins(AlertCenter)
  const session = useSessionStore()
  session.organizations = [
    {
      organizationId: 'o1',
      slug: 'm',
      name: 'Maison Élégance',
      role: 'owner',
      roleLabel: '',
      weddingsEnabled: true,
    },
  ]
  session.selectOrganization('m')
  await flushPromises()
  return mounted
}

afterEach(() => {
  vi.clearAllMocks()
  document.body.innerHTML = ''
})

describe('AlertCenter (the bell)', () => {
  it('counts the open alerts and lists them, most urgent first, with their action', async () => {
    const { wrapper } = await mountBell()
    const bell = wrapper.get('[data-testid="alert-bell"]')

    expect(bell.attributes('aria-label')).toBe('Alertes : 2 en cours')
    await bell.trigger('click')

    const text = wrapper.text()
    expect(text).toContain('Famille Ekotto')
    expect(text).toMatch(/Urgent · 360\s000\sFCFA en retard de 12 j/)
    expect(text).toContain('3 tâches en retard')
    expect(wrapper.find('a[href*="contract=k1"]').exists()).toBe(true)
  })

  it('marks an alert as handled', async () => {
    const { wrapper } = await mountBell()
    await wrapper.get('[data-testid="alert-bell"]').trigger('click')

    await wrapper.get('[aria-label="Marquer « Famille Ekotto » comme traitée"]').trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/alerts/a1/dismiss')
  })
})

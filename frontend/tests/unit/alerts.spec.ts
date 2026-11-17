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

const INBOX = {
  results: [
    {
      id: 'n1',
      kind: 'task',
      title: 'Tâche faite, à valider',
      body: 'Dresser les tables · Linda Abena',
      url: '/tasks',
      read: false,
      createdAt: new Date(Date.now() - 5 * 60_000).toISOString(),
    },
    {
      id: 'n2',
      kind: 'payment',
      title: 'Paiement reçu',
      body: 'RES-2026-0005',
      url: '/reservations',
      read: true,
      createdAt: new Date(Date.now() - 3 * 3600_000).toISOString(),
    },
  ],
  unread: 1,
  unreadAll: 1,
}

async function mountBell(inbox: typeof INBOX | null = null) {
  // The API client is mocked whole: data as the app receives it (camelCase), alerts and inbox.
  vi.mocked(api.get).mockImplementation((url: string) =>
    Promise.resolve({ data: url === '/notifications' ? (inbox ?? INBOX) : ALERTS }),
  )
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
  if (inbox) session.status = 'authenticated'
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

    expect(bell.attributes('aria-label')).toBe('Notifications : 0 non lues · Alertes : 2 en cours')
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

  it('shows the unread notifications first, like WhatsApp, and opens one', async () => {
    const { wrapper, router } = await mountBell(INBOX)
    const bell = wrapper.get('[data-testid="alert-bell"]')
    expect(bell.text()).toBe('1')
    expect(document.title).toBe('(1) Wedivo')

    await bell.trigger('click')
    expect(wrapper.text()).toContain('Tâche faite, à valider')
    expect(wrapper.text()).toContain('Il y a 5 min')
    expect(wrapper.text()).toContain('Il y a 3 h')

    const item = wrapper.findAll('li button').find((b) => b.text().includes('Tâche faite'))
    await item!.trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/notifications/n1/read')
    expect(router.currentRoute.value.fullPath).toBe('/tasks')
  })
})

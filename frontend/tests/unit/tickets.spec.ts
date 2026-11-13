import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Component } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import { api } from '@/api/client'
import { i18n } from '@/i18n'
import PublicTicketPage from '@/modules/invitations/pages/PublicTicketPage.vue'
import TicketsPage from '@/modules/invitations/pages/TicketsPage.vue'
import { useSessionStore } from '@/stores/session'

vi.mock('@/api/client', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() },
  configureApi: vi.fn(),
}))

const design = {
  id: 'd1',
  palette: 'noir-or',
  partner1: 'David',
  partner2: 'Grâce',
  title: 'Invitation officielle',
  subtitle: 'À notre mariage',
  intro: 'Avec l’amour comme guide…',
  panelText: 'Deux cœurs, une même histoire',
  bottomSlogan: 'Amour • Engagement • Éternité',
  scriptLine: 'Votre présence est un bonheur pour nous !',
  startsAt: '2027-05-24T15:00:00Z',
  startsAtLocal: '2027-05-24T15:00',
  venue: 'Le Grand Royaume',
  address: 'Yaoundé',
  dressCode: 'Tenue élégante',
  stubTitle: 'Billet d’invitation',
  stubSubtitle: 'Événement mariage',
  stubScript: 'Merci de confirmer votre présence',
  stubFooter: 'Ensemble pour toujours',
  showMonogram: false,
  categories: ['Standard', 'Famille', 'VIP'],
  updatedAt: '2026-10-21T10:00:00Z',
}
const ticket = {
  id: 't1',
  code: 'WDV-DG-0001',
  status: 'active',
  issuedAt: '2026-10-21T10:00:00Z',
  sentAt: null,
  openedAt: null,
  cancelledAt: null,
  hasDocument: true,
  url: 'http://localhost:8090/t/abc',
}
const guests = [
  {
    id: 'g1',
    name: 'Famille Kouassi',
    email: '',
    phone: '',
    seats: 4,
    category: 'Famille',
    table: '3',
    notes: '',
    rsvpStatus: 'pending',
    rsvpAt: null,
    ticket,
    ticketState: 'generated',
    lastTicketId: 't1',
  },
  {
    id: 'g2',
    name: 'M. Yao',
    email: 'yao@mail.ci',
    phone: '',
    seats: 2,
    category: 'VIP',
    table: '',
    notes: '',
    rsvpStatus: 'pending',
    rsvpAt: null,
    ticket: null,
    ticketState: 'none',
    lastTicketId: null,
  },
]

function respond(url: string) {
  if (url === '/weddings/w1') return { data: { id: 'w1', title: 'David & Grâce' } }
  if (url === '/weddings/w1/ticket-design') return { data: design }
  if (url === '/weddings/w1/guests') return { data: guests }
  if (url === '/documents/designs') return { data: { designs: [], palettes: [] } }
  if (url === '/public/tickets/abc')
    return {
      data: {
        status: 'active',
        code: 'WDV-DG-0001',
        guest: { name: 'Famille Kouassi', seats: 4, rsvpStatus: 'pending' },
        couple: 'David & Grâce',
        startsAt: '2027-05-24T15:00:00Z',
        venue: 'Le Grand Royaume',
        address: 'Yaoundé',
        agency: 'Maison Élégance Events',
      },
    }
  return { data: [] }
}

async function mountAt(path: string, component: Component) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const session = useSessionStore()
  session.user = {
    id: 'u1',
    email: 'a@b.ci',
    fullName: 'A',
    phone: '',
    isVerified: true,
    mustChangePassword: false,
  }
  session.organizations = [
    {
      organizationId: 'o1',
      slug: 'm',
      name: 'M',
      role: 'owner',
      roleLabel: '',
      weddingsEnabled: true,
    },
  ]
  session.status = 'authenticated'
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/mariages', name: 'weddings', component: { template: '<div />' } },
      { path: '/mariages/:id/billets', name: 'wedding-tickets', component },
      { path: '/t/:token', name: 'public-ticket', component },
    ],
  })
  await router.push(path)
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = mount(component, {
    attachTo: document.body,
    global: { plugins: [pinia, i18n, router, [VueQueryPlugin, { queryClient }]] },
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.mocked(api.get).mockImplementation((url: string) => Promise.resolve(respond(url)))
  URL.createObjectURL = vi.fn(() => 'blob:x')
  URL.revokeObjectURL = vi.fn()
})
afterEach(() => {
  vi.clearAllMocks()
  vi.useRealTimers()
  document.body.innerHTML = ''
})

describe('TicketsPage', () => {
  it('lists the guests with their ticket status and totals', async () => {
    const wrapper = await mountAt('/mariages/w1/billets', TicketsPage)

    const rows = wrapper.findAll('[data-testid="guest-row"]')
    expect(rows).toHaveLength(2)
    expect(rows[0]!.text()).toContain('Généré')
    expect(rows[0]!.text()).toContain('WDV-DG-0001')
    expect(rows[1]!.text()).toContain('Non généré')
    expect(wrapper.text()).toContain('David & Grâce')
  })

  it('generates the selection and follows the batch to the end', async () => {
    vi.mocked(api.post).mockImplementation((url: string) =>
      Promise.resolve(
        url === '/weddings/w1/tickets/generate'
          ? { data: { batch: 'b1', total: 1, done: 0, failed: 0, status: 'running' } }
          : { data: new Blob() },
      ),
    )
    vi.mocked(api.get).mockImplementation((url: string) =>
      Promise.resolve(
        url === '/ticket-batches/b1'
          ? { data: { batch: 'b1', total: 1, done: 1, failed: 0, status: 'done' } }
          : respond(url),
      ),
    )
    const wrapper = await mountAt('/mariages/w1/billets', TicketsPage)
    vi.useFakeTimers()

    await wrapper.get('[aria-label="Générer le billet de M. Yao"]').trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/weddings/w1/tickets/generate', { guests: ['g2'] })
    await vi.advanceTimersByTimeAsync(1100)
    await flushPromises()

    expect(wrapper.text()).toContain('Génération terminée')
    // The list is reloaded once the batch is done (new statuses).
    const loads = vi.mocked(api.get).mock.calls.filter(([url]) => url === '/weddings/w1/guests')
    expect(loads.length).toBeGreaterThanOrEqual(2)
  })

  it('copies a WhatsApp message with the guest’s link (never sent automatically)', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })
    const wrapper = await mountAt('/mariages/w1/billets', TicketsPage)

    await wrapper
      .get('[aria-label="Copier le message WhatsApp pour Famille Kouassi"]')
      .trigger('click')
    await flushPromises()

    expect(writeText).toHaveBeenCalledWith(
      'Bonjour Famille Kouassi, voici votre billet pour le mariage de David & Grâce. Ouvrez-le le jour J pour entrer : http://localhost:8090/t/abc',
    )
  })
})

describe('PublicTicketPage', () => {
  it('shows the ticket and records the answer', async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { rsvpStatus: 'accepted' } })
    const wrapper = await mountAt('/t/abc', PublicTicketPage)

    expect(wrapper.text()).toContain('Mariage de David & Grâce')
    expect(wrapper.get('[data-testid="public-ticket"]').attributes('src')).toBe(
      '/api/v1/public/tickets/abc/image',
    )
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Confirmer ma présence')!
      .trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/public/tickets/abc/rsvp', { accepted: true })
    expect(wrapper.text()).toContain('Votre présence est confirmée')
  })
})

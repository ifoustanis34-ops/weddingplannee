import { flushPromises } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Role } from '@/api/auth'
import { api } from '@/api/client'
import { monthDays, monthKey, parseMonth } from '@/modules/calendar/month'
import CalendarPage from '@/modules/calendar/pages/CalendarPage.vue'
import WeddingDrawer from '@/modules/events/components/WeddingDrawer.vue'
import VendorsPage from '@/modules/vendors/pages/VendorsPage.vue'
import { useSessionStore } from '@/stores/session'

import { mountWithPlugins } from './helpers'

vi.mock('@/api/client', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() },
  configureApi: vi.fn(),
}))

const iso = (offset: number) => {
  const d = new Date()
  d.setDate(d.getDate() + offset)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const wedding = {
  id: 'w1',
  title: 'Mariam & Idriss',
  date: iso(11),
  venue: 'Sofitel Hôtel Ivoire, Cocody',
  guestCount: 320,
  budget: 4_200_000,
  status: 'planned',
  statusLabel: 'En préparation',
  contract: null,
  contractNumber: null,
  client: null,
  tasksTotal: 3,
  tasksDone: 1,
  progress: 33,
  vendorsCount: 1,
  daysLeft: 11,
}
const task = (id: string, title: string, dueDate: string | null, status = 'todo') => ({
  id,
  wedding: 'w1',
  title,
  assignee: null,
  assigneeName: 'Awa Sangaré',
  dueDate,
  status,
  statusLabel: '',
  notes: '',
  doneAt: null,
})
const tasks = [
  task('t1', 'Réception des alliances', iso(-5), 'done'),
  task('t2', 'Confirmer le plan de table', iso(2)),
  task('t3', 'Valider le menu', iso(-1)),
]

function respond(url: string) {
  if (url === '/weddings/w1') return { data: wedding }
  if (url === '/weddings/w1/tasks') return { data: tasks }
  if (url === '/weddings/w1/vendors')
    return {
      data: [
        {
          id: 'b1',
          wedding: 'w1',
          weddingTitle: 'Mariam & Idriss',
          vendor: 'v1',
          vendorName: 'Fleurs d’Ébène',
          vendorCategoryLabel: 'Décoration',
          vendorPhone: '+225 07 22 18 90 45',
          service: 'Décoration de salle',
        },
      ],
    }
  if (url === '/vendors')
    return {
      data: [
        {
          id: 'v1',
          name: 'Fleurs d’Ébène',
          category: 'decoration',
          categoryLabel: 'Décoration',
          phone: '+225 07 22 18 90 45',
          email: '',
          services: '',
          notes: '',
          collaborations: 14,
        },
      ],
    }
  if (url === '/calendar') {
    const base = {
      endDate: null,
      time: null,
      subtitle: '',
      status: null,
      team: [],
      owner: null,
      vehicle: '',
      wedding: null,
      reservation: null,
      contract: null,
      item: null,
      amount: null,
      movable: false,
    }
    return {
      data: [
        { ...base, kind: 'event', id: 'w1', date: iso(0), title: 'Mariam & Idriss', wedding: 'w1' },
        {
          ...base,
          kind: 'delivery',
          id: 'r1:delivery',
          date: iso(0),
          time: '09:00',
          title: 'Famille Diabaté',
          subtitle: 'RES-2026-0006 · Mariage coutumier',
          status: 'confirmed',
          owner: 'Awa Sangaré',
          vehicle: 'Camion 3,5 t',
          reservation: 'r1',
          movable: true,
        },
        {
          ...base,
          kind: 'payment',
          id: 'p1',
          date: iso(0),
          title: 'Aïcha & Serge Kouassi',
          amount: 500_000,
          contract: 'c1',
        },
      ],
    }
  }
  return { data: [] }
}

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

beforeEach(() => {
  vi.mocked(api.get).mockImplementation((url: string) => Promise.resolve(respond(url)))
})
afterEach(() => {
  vi.clearAllMocks()
  document.body.innerHTML = ''
})

describe('month grid', () => {
  it('starts on the Monday before the 1st and shows six weeks', () => {
    const days = monthDays(2026, 9) // October 2026 starts on a Thursday
    expect(days).toHaveLength(42)
    expect(days[0]!.getDay()).toBe(1)
    expect(days[0]!.getDate()).toBe(28) // Monday 28 September
    expect(days[3]!.getDate()).toBe(1)
  })

  it('reads ?mois= and rolls over the year', () => {
    expect(parseMonth('2026-10')).toEqual({ year: 2026, month: 9 })
    expect(parseMonth('n’importe quoi', new Date(2026, 4, 3))).toEqual({ year: 2026, month: 4 })
    expect(monthKey(2026, 12)).toBe('2027-01')
    expect(monthKey(2026, -1)).toBe('2025-12')
  })
})

describe('WeddingDrawer', () => {
  it('lists undone tasks first by due date, with late and soon badges', async () => {
    mountWithPlugins(WeddingDrawer, { props: { weddingId: 'w1' } })
    signIn('planner')
    await flushPromises()

    const dialog = document.querySelector('[role="dialog"]') as HTMLElement
    expect(dialog.textContent).toContain('Mariage de Mariam & Idriss')
    const titles = [...dialog.querySelectorAll('[role="checkbox"]')].map((b) =>
      b.getAttribute('aria-label'),
    )
    expect(titles).toEqual([
      'Valider le menu',
      'Confirmer le plan de table',
      'Réception des alliances',
    ])
    expect(dialog.textContent).toContain('En retard')
    expect(dialog.textContent).toContain('Bientôt')
    expect(dialog.textContent).toContain('Fleurs d’Ébène')
  })

  it('ticks a task', async () => {
    vi.mocked(api.post).mockResolvedValue({ data: tasks[1] })
    mountWithPlugins(WeddingDrawer, { props: { weddingId: 'w1' } })
    signIn('assistant')
    await flushPromises()

    const box = document.querySelector('[aria-label="Confirmer le plan de table"]') as HTMLElement
    box.click()
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/tasks/t2/done', { done: true })
  })
})

describe('VendorsPage', () => {
  it('hides the amount due from the assistant', async () => {
    const { wrapper } = mountWithPlugins(VendorsPage)
    signIn('assistant')
    await flushPromises()

    expect(wrapper.text()).toContain('Fleurs d’Ébène')
    expect(wrapper.text()).toContain('14')
    expect(wrapper.text()).not.toContain('Montant dû')
  })
})

describe('CalendarPage', () => {
  it('shows every kind with its time, toggles kinds and switches to the logistic planning', async () => {
    const { wrapper, router } = mountWithPlugins(CalendarPage)
    signIn('owner')
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('Mariam & Idriss')
    expect(text).toContain('09:00 · Famille Diabaté')
    expect(text).toMatch(/500\s000 · Aïcha/)
    const delivery = wrapper.findAll('button[draggable="true"]')
    expect(delivery).toHaveLength(1) // only the movable reservation can be dragged

    // The legend filters: hiding deliveries asks the server without them.
    await wrapper
      .findAll('button[aria-pressed]')
      .find((b) => b.text() === 'Livraisons')!
      .trigger('click')
    await flushPromises()
    const last = vi
      .mocked(api.get)
      .mock.calls.filter(([url]) => url === '/calendar')
      .at(-1)
    const params = (last?.[1] as { params: Record<string, string> }).params
    expect(params.kinds).not.toContain('delivery')
    expect(params.kinds).toContain('event')

    await router.push({ query: { vue: 'logistique' } })
    await flushPromises()
    expect(wrapper.text()).toContain('Récupérations et retours')
  })
})

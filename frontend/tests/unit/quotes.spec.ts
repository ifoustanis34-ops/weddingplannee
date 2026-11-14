import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import { api } from '@/api/client'
import { i18n } from '@/i18n'
import { computeTotals, lineAmount, suggestedQuantity } from '@/modules/quotes/calculations'
import ServerPreview from '@/modules/quotes/components/ServerPreview.vue'
import QuoteEditorPage from '@/modules/quotes/pages/QuoteEditorPage.vue'
import type { QuoteInput } from '@/modules/quotes/types'
import { useSessionStore } from '@/stores/session'

vi.mock('@/api/client', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  configureApi: vi.fn(),
}))

const NNBSP = ' '

describe('quote calculations (mirror of backend quotes/calculations.py)', () => {
  it('matches the backend test case', () => {
    const totals = computeTotals(
      [
        { unitPrice: 12_000, quantity: 250 },
        { unitPrice: 900_000, quantity: 1 },
        { unitPrice: 300_000, quantity: 1.5 },
      ],
      10,
      30,
    )
    expect(totals).toEqual({
      subtotal: 4_350_000,
      discountAmount: 435_000,
      total: 3_915_000,
      depositAmount: 1_174_500,
      balance: 2_740_500,
    })
  })

  it('rounds half up to the franc without floating point drift', () => {
    expect(lineAmount(3, 0.5)).toBe(2)
    expect(lineAmount(350_000, 1.5)).toBe(525_000)
    expect(lineAmount(1_999, 0.15)).toBe(300) // 299.85
    expect(computeTotals([{ unitPrice: 1_500_000, quantity: 1 }], 0, 30).balance).toBe(1_050_000)
  })

  it('proposes the guest count for « per guest » services', () => {
    expect(suggestedQuantity('guest', 250)).toBe(250)
    expect(suggestedQuantity('flat', 250)).toBe(1)
    expect(suggestedQuantity('guest', null)).toBe(1)
    // Complement §9: chairs follow the guests, centrepieces one per table of ten.
    expect(suggestedQuantity('unit', 180, 'per_guest')).toBe(180)
    expect(suggestedQuantity('unit', 183, 'per_ten_guests')).toBe(19)
    expect(suggestedQuantity('unit', 183, 'one')).toBe(1)
  })
})

const catalog = [
  {
    id: 'c1',
    name: 'Restauration',
    order: 0,
    items: [
      {
        id: 'i1',
        category: 'c1',
        name: 'Menu traiteur ivoirien',
        description: '',
        unit: 'guest',
        unitLabel: 'Invité',
        unitPrice: 12_000,
        isActive: true,
        quantityRule: 'one',
        isDefault: false,
      },
      {
        id: 'i2',
        category: 'c1',
        name: 'Pièce montée',
        description: '',
        unit: 'flat',
        unitLabel: 'Forfait',
        unitPrice: 150_000,
        isActive: true,
        quantityRule: 'one',
        isDefault: false,
      },
    ],
  },
]
const client = {
  id: 'p1',
  name: 'Awa & Moussa',
  company: '',
  phone: '',
  phoneAlt: '',
  email: 'awa@mail.ci',
  address: '',
  notes: '',
  preferences: '',
  isArchived: false,
  orderCount: 0,
  revenue: 0,
  collected: 0,
  balanceDue: 0,
  lastOrderAt: null,
  createdAt: '',
  updatedAt: '',
}

function respond(url: string) {
  if (url === '/catalog/categories') return { data: catalog }
  if (url === '/organization')
    return {
      data: { name: 'Maison Élégance', city: 'Abidjan', legalMentions: '', quoteValidityDays: 30 },
    }
  if (url === '/clients/p1') return { data: client }
  if (url === '/clients') return { data: { results: [client], next: null } }
  if (url === '/documents/designs')
    return {
      data: {
        designs: [
          { code: 'A', name: 'Prestige' },
          { code: 'B', name: 'Élégance' },
        ],
        palettes: [{ code: 'nuit-or', name: 'Nuit & Or', dark: '#0F1B3D', accent: '#C9A24A' }],
        defaultDesign: 'A',
        defaultPalette: 'nuit-or',
        defaultTagline: 'Une organisation sur mesure.',
      },
    }
  return { data: [] }
}

async function mountEditor(path: string, role: 'owner' | 'accountant' = 'owner') {
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
      slug: 'maison',
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
      { path: '/devis', name: 'quotes', component: { template: '<div />' } },
      { path: '/devis/nouveau', name: 'quote-new', component: QuoteEditorPage },
      { path: '/devis/:id', name: 'quote-edit', component: QuoteEditorPage },
    ],
  })
  await router.push(path)
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = mount(QuoteEditorPage, {
    attachTo: document.body,
    global: { plugins: [pinia, i18n, router, [VueQueryPlugin, { queryClient }]] },
  })
  await flushPromises()
  return { wrapper, router }
}

beforeEach(() => {
  vi.mocked(api.get).mockImplementation((url: string) => Promise.resolve(respond(url)))
})
afterEach(() => {
  vi.clearAllMocks()
  document.body.innerHTML = ''
})

/** The guest count no longer comes from the client: the planner types it. */
async function setGuests(wrapper: ReturnType<typeof mount>, count: number): Promise<void> {
  const label = wrapper.findAll('label').find((l) => l.text().startsWith('Nombre d’invités'))
  const input = wrapper.get(`#${label!.attributes('for')}`)
  await input.setValue(count)
  await flushPromises()
}

describe('QuoteEditorPage', () => {
  it('adds a catalog service in one click with the guest count as quantity', async () => {
    const { wrapper } = await mountEditor('/devis/nouveau?client=p1')
    await setGuests(wrapper, 250)

    await wrapper.get('[aria-label="Ajouter Menu traiteur ivoirien"]').trigger('click')
    await flushPromises()

    const line = wrapper.get('[data-testid="quote-line"]')
    expect((line.get('input[aria-label^="Quantité"]').element as HTMLInputElement).value).toBe(
      '250',
    )
    expect(wrapper.get('[data-testid="editor-total"]').text()).toBe(`3${NNBSP}000${NNBSP}000 FCFA`)
    expect(wrapper.text()).toContain('Awa & Moussa')
  })

  it('raises the quantity when a service is added twice', async () => {
    const { wrapper } = await mountEditor('/devis/nouveau?client=p1')
    const add = wrapper.get('[aria-label="Ajouter Pièce montée"]')
    await add.trigger('click')
    await add.trigger('click')
    await flushPromises()

    const lines = wrapper.findAll('[data-testid="quote-line"]')
    expect(lines).toHaveLength(1)
    expect((lines[0]!.get('input[aria-label^="Quantité"]').element as HTMLInputElement).value).toBe(
      '2',
    )
  })

  it('starts a blank quote with the catalog default services', async () => {
    const withDefault = catalog.map((category) => ({
      ...category,
      items: category.items.map((item) => ({ ...item, isDefault: item.id === 'i2' })),
    }))
    vi.mocked(api.get).mockImplementation((url: string) =>
      Promise.resolve(url === '/catalog/categories' ? { data: withDefault } : respond(url)),
    )
    const { wrapper } = await mountEditor('/devis/nouveau?client=p1')
    await flushPromises()

    const lines = wrapper.findAll('[data-testid="quote-line"]')
    expect(lines).toHaveLength(1)
    expect(
      (lines[0]!.get('input[aria-label="Intitulé de la prestation"]').element as HTMLInputElement)
        .value,
    ).toBe('Pièce montée')
  })

  it('updates « per guest » lines when the guest count is typed after them', async () => {
    const { wrapper } = await mountEditor('/devis/nouveau?client=p1')
    await wrapper.get('[aria-label="Ajouter Menu traiteur ivoirien"]').trigger('click')
    await setGuests(wrapper, 250)

    expect(wrapper.get('[data-testid="editor-total"]').text()).toBe(
      `3${NNBSP}000${NNBSP}000\u00a0FCFA`,
    )
  })

  it('saves the draft with its lines', async () => {
    const saved = {
      data: {
        id: 'q1',
        number: 'DV-2026-0001',
        client: 'p1',
        clientDetail: client,
        status: 'draft',
        statusLabel: 'Brouillon',
        issueDate: '2026-10-20',
        validUntil: '2026-11-19',
        weddingDate: '2026-12-19',
        guestCount: 250,
        discountPct: 0,
        depositPct: 30,
        paymentTerms: '',
        notes: '',
        subtotal: 150_000,
        discountAmount: 0,
        total: 150_000,
        depositAmount: 45_000,
        sentAt: null,
        acceptedAt: null,
        refusedAt: null,
        refusalReason: '',
        isTemplate: false,
        design: '',
        palette: '',
        tagline: '',
        eventType: 'Mariage',
        venue: '',
        partners: [],
        templateName: '',
        publicUrl: 'http://x/proposition/t',
        contract: null,
        createdAt: '',
        updatedAt: '',
        lines: [
          {
            serviceItem: 'i2',
            label: 'Pièce montée',
            description: '',
            unit: 'flat',
            unitPrice: 150_000,
            quantity: 1,
            amount: 150_000,
          },
        ],
      },
    }
    vi.mocked(api.post).mockImplementation(() => Promise.resolve(saved))
    vi.mocked(api.get).mockImplementation((url: string) =>
      Promise.resolve(url === '/quotes/q1' ? saved : respond(url)),
    )
    const { wrapper, router } = await mountEditor('/devis/nouveau?client=p1')
    await setGuests(wrapper, 250)
    await wrapper.get('[aria-label="Ajouter Pièce montée"]').trigger('click')
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Enregistrer le brouillon')!
      .trigger('click')
    await flushPromises()

    // The first POST may be the server preview: take the save.
    const [url, body] = vi.mocked(api.post).mock.calls.find(([called]) => called === '/quotes')!
    expect(url).toBe('/quotes')
    expect(body).toMatchObject({
      client: 'p1',
      guestCount: 250,
      lines: [
        { serviceItem: 'i2', label: 'Pièce montée', unit: 'flat', unitPrice: 150_000, quantity: 1 },
      ],
    })
    expect(router.currentRoute.value.params.id).toBe('q1')
  })

  it('locks an accepted quote', async () => {
    vi.mocked(api.get).mockImplementation((url: string) =>
      Promise.resolve(
        url === '/quotes/q1'
          ? {
              data: {
                id: 'q1',
                number: 'DV-2026-0001',
                client: 'p1',
                clientDetail: client,
                status: 'accepted',
                statusLabel: '',
                issueDate: '2026-10-20',
                validUntil: '2026-11-19',
                weddingDate: null,
                guestCount: null,
                discountPct: 0,
                depositPct: 30,
                paymentTerms: '',
                notes: '',
                subtotal: 0,
                discountAmount: 0,
                total: 0,
                depositAmount: 0,
                sentAt: null,
                acceptedAt: '2026-10-21T10:00:00Z',
                refusedAt: null,
                refusalReason: '',
                isTemplate: false,
                design: '',
                palette: '',
                tagline: '',
                eventType: 'Mariage',
                venue: '',
                partners: [],
                templateName: '',
                publicUrl: null,
                contract: null,
                createdAt: '',
                updatedAt: '',
                lines: [],
              },
            }
          : respond(url),
      ),
    )
    const { wrapper } = await mountEditor('/devis/q1')

    expect(wrapper.text()).toContain('Il n’est plus modifiable')
    expect(wrapper.text()).toContain('Convertir en contrat')
    expect(wrapper.findAll('button').some((b) => b.text() === 'Enregistrer')).toBe(false)
  })
})

describe('ServerPreview', () => {
  it('asks the server for the rendering of the draft, once the typing stops', async () => {
    vi.useFakeTimers()
    URL.createObjectURL = vi.fn(() => 'blob:preview')
    URL.revokeObjectURL = vi.fn()
    vi.mocked(api.post).mockResolvedValue({
      data: new Blob(['png']),
      headers: { 'x-page-count': '2' },
    })
    const draft = ref<QuoteInput>({ client: 'p1', lines: [], design: 'C' })
    const wrapper = mount(ServerPreview, {
      props: { quoteId: 'q1', draft: draft.value },
      global: { plugins: [i18n] },
    })
    await wrapper.setProps({ draft: { ...draft.value, palette: 'emeraude-or' } })
    await vi.advanceTimersByTimeAsync(450)
    await flushPromises()

    expect(api.post).toHaveBeenCalledTimes(1) // debounced: one request for two changes
    expect(api.post).toHaveBeenCalledWith(
      '/documents/preview',
      {
        kind: 'quote',
        quote: 'q1',
        draft: { client: 'p1', lines: [], design: 'C', palette: 'emeraude-or' },
      },
      expect.objectContaining({ responseType: 'blob' }),
    )
    expect(wrapper.get('[data-testid="server-preview"]').attributes('src')).toBe('blob:preview')
    expect(wrapper.text()).toContain('2 pages')
    vi.useRealTimers()
  })
})

import { flushPromises } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '@/api/client'
import InvitationPage from '@/modules/auth/pages/InvitationPage.vue'
import BrandingTab from '@/modules/settings/components/BrandingTab.vue'
import InviteModal from '@/modules/settings/components/InviteModal.vue'
import PlanTab from '@/modules/settings/components/PlanTab.vue'
import TeamTab from '@/modules/settings/components/TeamTab.vue'
import { useSessionStore } from '@/stores/session'

import { mountWithPlugins } from './helpers'

vi.mock('@/api/client', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() },
  configureApi: vi.fn(),
}))

const members = [
  {
    id: 'm1',
    userId: 'u1',
    fullName: 'Freddy Kouamé',
    email: 'freddy@maison.ci',
    phone: '',
    role: 'owner',
    roleLabel: 'Propriétaire',
    isActive: true,
  },
  {
    id: 'm2',
    userId: 'u2',
    fullName: 'Didier Kra',
    email: 'didier@maison.ci',
    phone: '',
    role: 'assistant',
    roleLabel: 'Assistant',
    isActive: true,
  },
]
const invitations = [
  {
    id: 'i1',
    email: 'nadege@maison.ci',
    role: 'accountant',
    roleLabel: 'Comptable',
    invitedByName: 'Freddy Kouamé',
    createdAt: '',
    expiresAt: '',
  },
]
const plans = [
  {
    code: 'essentiel',
    name: 'Essentiel',
    description: '',
    monthlyPrice: 15_000,
    maxUsers: 1,
    features: [],
  },
  {
    code: 'pro',
    name: 'Pro',
    description: '',
    monthlyPrice: 35_000,
    maxUsers: 5,
    features: ['Jusqu’à 5 utilisateurs'],
  },
]

const branding = {
  primaryColor: '',
  secondaryColor: '',
  monogramColor: '',
  useBrandColors: false,
  tradeName: 'Maison Élégance Events',
  legalName: '',
  activity: 'Gestion & organisation d’événements',
  slogan: '',
  address: 'Abidjan',
  phones: [],
  whatsapp: '',
  email: '',
  website: '',
  socials: {},
  taxIds: {},
  vatRate: null,
  bankDetails: '',
  mobileMoneyNumbers: [],
  activities: [{ label: 'Mariages', icon: 'rings' }],
  engagements: [],
  quoteTagline: '',
  scripts: {
    satisfaction: '',
    detail: '',
    detailSub: '',
    priority: '',
    thanks: 'Merci pour votre confiance !',
    footer: '',
  },
  signatory: '',
  signatoryRole: '',
  footerKeywords: ['Mariages'],
  quoteTerms: '',
  paymentTerms: '',
  footerText: '',
  showWedivoMention: true,
  logoContrastLight: null,
  logoContrastDark: null,
  files: { logo: null, logoOnDark: null, signatureImage: null, stampImage: null },
  monogram: 'ME',
  missing: ['logo', 'phones'],
  warnings: [],
  updatedAt: '2026-10-20T10:00:00Z',
}

function respond(url: string) {
  if (url === '/organization/branding') return { data: branding }
  if (url === '/organization/members') return { data: members }
  if (url === '/organization/invitations') return { data: invitations }
  if (url === '/plans') return { data: plans }
  if (url === '/organization')
    return { data: { plan: 'pro', trialEndsAt: null, timezone: 'Africa/Abidjan' } }
  if (url === '/auth/invitations/tok')
    return {
      data: {
        organizationName: 'Maison Élégance Events',
        organizationSlug: 'maison-elegance',
        email: 'awa@maison.ci',
        roleLabel: 'Wedding planner',
        invitedByName: 'Freddy Kouamé',
        hasAccount: false,
      },
    }
  return { data: [] }
}

function signIn(): void {
  const session = useSessionStore()
  session.user = {
    id: 'u1',
    email: 'freddy@maison.ci',
    fullName: 'Freddy Kouamé',
    phone: '',
    isVerified: true,
    mustChangePassword: false,
  }
  session.organizations = [
    {
      organizationId: 'o1',
      slug: 'maison',
      name: 'Maison',
      role: 'owner',
      roleLabel: 'Propriétaire',
      weddingsEnabled: true,
    },
  ]
  session.selectOrganization('maison')
}

beforeEach(() => {
  vi.mocked(api.get).mockImplementation((url: string) => Promise.resolve(respond(url)))
})
afterEach(() => {
  vi.clearAllMocks()
  document.body.innerHTML = ''
})

describe('TeamTab', () => {
  it('lists members and pending invitations; the owner role is not editable', async () => {
    const { wrapper } = mountWithPlugins(TeamTab)
    signIn()
    await flushPromises()

    expect(wrapper.text()).toContain('Didier Kra')
    expect(wrapper.text()).toContain('nadege@maison.ci')
    expect(wrapper.text()).toContain('Invitation envoyée')
    // One role select only: Didier's, not the owner's.
    expect(wrapper.findAll('select')).toHaveLength(1)
    expect(wrapper.text()).toContain('Ce que chaque rôle peut faire')
  })

  it('changes a role through the API', async () => {
    vi.mocked(api.patch).mockResolvedValue({ data: { ...members[1], role: 'accountant' } })
    const { wrapper } = mountWithPlugins(TeamTab)
    signIn()
    await flushPromises()

    await wrapper.get('select').setValue('accountant')
    await flushPromises()

    expect(api.patch).toHaveBeenCalledWith('/organization/members/m2', { role: 'accountant' })
  })
})

describe('InviteModal', () => {
  it('sends the invitation with the chosen role', async () => {
    vi.mocked(api.post).mockResolvedValue({ data: invitations[0] })
    mountWithPlugins(InviteModal, { props: { open: true } })
    await flushPromises()

    const dialog = document.querySelector('[role="dialog"]') as HTMLElement
    const email = dialog.querySelector('input[type="email"]') as HTMLInputElement
    email.value = 'awa@maison.ci'
    email.dispatchEvent(new Event('input'))
    ;(dialog.querySelector('form') as HTMLFormElement).dispatchEvent(new Event('submit'))
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/organization/invitations', {
      email: 'awa@maison.ci',
      role: 'planner',
    })
  })
})

describe('PlanTab', () => {
  it('marks the current offer and switches to another one', async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { plan: 'essentiel' } })
    const { wrapper } = mountWithPlugins(PlanTab)
    signIn()
    await flushPromises()

    expect(wrapper.text()).toContain('Offre actuelle')
    expect(wrapper.text()).toMatch(/35\s000/)
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Passer à Essentiel')!
      .trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/organization/plan', { plan: 'essentiel' })
  })
})

describe('InvitationPage', () => {
  it('asks a newcomer for a name before joining', async () => {
    const { wrapper, router } = mountWithPlugins(InvitationPage)
    await router.push('/invitation/tok').catch(() => undefined)
    await flushPromises()

    expect(wrapper.text()).toContain('Rejoindre Maison Élégance Events')
    expect(wrapper.text()).toContain('Wedding planner')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('Indiquez votre nom complet.')
    expect(api.post).not.toHaveBeenCalled()
  })
})

describe('BrandingTab', () => {
  it('previews the header with the monogram and lists what quotes would miss', async () => {
    const { wrapper } = mountWithPlugins(BrandingTab)
    signIn()
    await flushPromises()

    expect(wrapper.text()).toContain('Maison Élégance Events')
    expect(wrapper.text()).toContain('ME')
    expect(wrapper.text()).toContain('Pour des devis complets, ajoutez : votre logo, un téléphone.')
  })

  it('uploads a logo and takes the colours proposed from it', async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: {
        ...branding,
        primaryColor: '#0F1B3D',
        files: { ...branding.files, logo: '/api/v1/files/abc' },
        missing: ['phones'],
        warnings: ['logo_dark'],
      },
    })
    const { wrapper } = mountWithPlugins(BrandingTab)
    signIn()
    await flushPromises()

    const input = wrapper.find('input[type="file"]')
    const file = new File(['png'], 'logo.png', { type: 'image/png' })
    Object.defineProperty(input.element, 'files', { value: [file] })
    await input.trigger('change')
    await flushPromises()

    const [url, form] = vi.mocked(api.post).mock.calls[0] as [string, FormData]
    expect(url).toBe('/organization/branding/files')
    expect(form.get('kind')).toBe('logo')
    expect(wrapper.find('img[src="/api/v1/files/abc"]').exists()).toBe(true)
    expect((wrapper.find('input[type="color"]').element as HTMLInputElement).value).toBe('#0f1b3d')
    expect(wrapper.text()).toContain('Logo sur fond sombre')
    expect(wrapper.text()).toContain('se lit mal sur les bandeaux sombres')
  })

  it('saves the texts without the empty lines', async () => {
    vi.mocked(api.patch).mockResolvedValue({ data: branding })
    const { wrapper } = mountWithPlugins(BrandingTab)
    signIn()
    await flushPromises()

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    const payload = vi.mocked(api.patch).mock.calls[0]?.[1] as Record<string, unknown>
    expect(payload.phones).toEqual(['', '', ''])
    expect(payload.activities).toEqual([{ label: 'Mariages', icon: 'rings' }])
    expect(payload.footerKeywords).toEqual(['Mariages'])
  })
})

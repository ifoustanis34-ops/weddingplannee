import { afterEach, describe, expect, it, vi } from 'vitest'

import type { OrganizationSummary, Role } from '@/api/auth'
import { plansApi } from '@/api/plans'
import SidebarContent from '@/app/layouts/SidebarContent.vue'
import { menuItems, mobileTabItems, NAV_ITEMS, phaseTag, visibleNavItems } from '@/app/navigation'
import SignupPage from '@/modules/auth/pages/SignupPage.vue'
import { useSessionStore } from '@/stores/session'

import { mountWithPlugins, settle } from './helpers'

vi.mock('@/api/plans', () => ({ plansApi: { list: vi.fn() } }))

afterEach(() => {
  document.body.innerHTML = ''
})

const ORG: OrganizationSummary = {
  organizationId: 'o1',
  slug: 'maison-elegance',
  name: 'Maison Élégance Events',
  role: 'owner',
  roleLabel: 'Propriétaire',
  weddingsEnabled: true,
}

function signIn(role: Role = 'owner', organizations: OrganizationSummary[] = [ORG]): void {
  const session = useSessionStore()
  session.user = {
    id: 'u1',
    email: 'freddy@maison-elegance.ci',
    fullName: 'Freddy Kouamé',
    phone: '',
    isVerified: true,
    mustChangePassword: false,
    isPlatformAdmin: false,
  }
  session.organizations = organizations.map((org) => ({ ...org, role }))
  session.selectOrganization(organizations[0]?.slug ?? null)
}

describe('navigation', () => {
  it('follows the prototype order and never lists a module that is not built', () => {
    // reservations-stock.md §3; modules not built yet (reports, staff…) stay hidden.
    expect(menuItems('owner').map((item) => item.key)).toEqual([
      'dashboard',
      'reservations',
      'calendar',
      'clients',
      'quotes',
      'stock',
      'movements',
      'finance',
      'reports',
      'staff',
      'tasks',
      'pay',
      'attendance',
      'weddings',
      'vendors',
      'settings',
    ])
    expect(menuItems('assistant').map((item) => item.key)).not.toContain('finance')
    expect(menuItems('planner').map((item) => item.key)).not.toContain('settings')
    // The catalogue leaves the menu (Paramètres › Catalogue) but stays reachable.
    expect(visibleNavItems('planner').map((item) => item.key)).toContain('catalog')
  })

  it('gives the field roles only what is theirs', () => {
    expect(menuItems('storekeeper').map((item) => item.key)).toEqual([
      'dashboard',
      'reservations',
      'calendar',
      'stock',
      'movements',
    ])
    for (const role of ['team_lead', 'staff'] as const)
      expect(menuItems(role).map((item) => item.key)).toEqual(['dashboard', 'missions'])
  })

  it('puts reservations and stock in the mobile tabs, clients and quotes as fallbacks', () => {
    expect(mobileTabItems('owner').map((item) => item.key)).toEqual([
      'dashboard',
      'reservations',
      'stock',
      'finance',
    ])
    expect(mobileTabItems('assistant').map((item) => item.key)).toEqual([
      'dashboard',
      'clients',
      'reservations',
      'stock',
    ])
  })

  it('keeps phase labels off unless the feature flag is on', () => {
    const weddings = NAV_ITEMS.find((item) => item.key === 'weddings')
    expect(weddings?.phase).toBe(2)
    expect(phaseTag(weddings!)).toBeNull()
  })
})

describe('SidebarContent', () => {
  it('shows the company block and the signed-in member', async () => {
    const { wrapper, router } = mountWithPlugins(SidebarContent)
    signIn()
    await router.push('/')
    await settle()

    expect(wrapper.text()).toContain('maison-elegance.wedivo.pro')
    expect(wrapper.text()).not.toContain('Relances')
    expect(wrapper.text()).toContain('Freddy Kouamé')
    expect(wrapper.text()).toContain('Propriétaire')
    const groups = wrapper.findAll('nav p').map((p) => p.text())
    expect(groups).toEqual([
      'Pilotage',
      'Activité',
      'Matériel',
      'Finances',
      'Équipe',
      'Événementiel',
      'Espace',
    ])
    // Dashboard is the current page: highlighted with the ribbon bar.
    const active = wrapper.get('nav [aria-current="page"]')
    expect(active.text()).toContain('Tableau de bord')
    expect(active.find('.bg-ribbon').exists()).toBe(true)
  })

  it('offers the space switcher only with several organizations', async () => {
    const { wrapper } = mountWithPlugins(SidebarContent)
    signIn('owner', [
      ORG,
      { ...ORG, organizationId: 'o2', slug: 'atelier-bassam', name: 'Atelier Bassam' },
    ])
    await settle()

    await wrapper.get('button[aria-expanded]').trigger('click')
    expect(wrapper.text()).toContain('Atelier Bassam')
  })
})

describe('SignupPage', () => {
  it('labels the three steps, starts in Cameroon and shows no price (16/11/2026)', async () => {
    const { wrapper } = mountWithPlugins(SignupPage)
    await settle()

    const labels = wrapper.findAll('ol li').map((li) => li.text())
    expect(labels).toEqual(['1. Entreprise', '2. Votre compte', '3. Votre espace'])
    // The country list starts on Cameroon, first of the list (16/11/2026); the number of
    // weddings a year is no longer asked.
    const select = wrapper.get('select').element as HTMLSelectElement
    expect(select.value).toBe('CM')
    expect(select.options[0]?.textContent?.trim()).toBe('Cameroun')
    expect(wrapper.text()).not.toMatch(/Mariages organisés/)
    expect(wrapper.text()).not.toMatch(/FCFA|\/ mois/)
    expect(plansApi.list).not.toHaveBeenCalled()
  })
})

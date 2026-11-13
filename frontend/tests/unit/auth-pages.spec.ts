import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { authApi } from '@/api/auth'
import { ApiError } from '@/api/errors'
import LoginPage from '@/modules/auth/pages/LoginPage.vue'
import SignupPage from '@/modules/auth/pages/SignupPage.vue'

import { mountWithPlugins, settle } from './helpers'

vi.mock('@/api/auth', () => ({
  authApi: {
    csrf: vi.fn(),
    me: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
    signup: vi.fn(),
    slugAvailable: vi.fn(),
  },
}))

const session = {
  user: {
    id: 'u1',
    email: 'awa@doux-moments.sn',
    fullName: 'Awa Diop',
    phone: '',
    isVerified: false,
    mustChangePassword: false,
  },
  organizations: [
    {
      organizationId: 'o1',
      slug: 'doux-moments',
      name: 'Doux Moments',
      role: 'owner' as const,
      roleLabel: 'Propriétaire',
      weddingsEnabled: true,
    },
  ],
}

beforeEach(() => {
  localStorage.clear()
  vi.mocked(authApi.csrf).mockImplementation(() => Promise.resolve(undefined))
})
afterEach(() => {
  document.body.innerHTML = ''
})

describe('LoginPage', () => {
  it('validates before calling the API', async () => {
    const { wrapper } = mountWithPlugins(LoginPage)
    await wrapper.get('form').trigger('submit')
    await settle()

    expect(authApi.login).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Ce champ est obligatoire.')
  })

  it('signs in and goes to the dashboard', async () => {
    vi.mocked(authApi.login).mockImplementation(() => Promise.resolve(session))
    const { wrapper, router } = mountWithPlugins(LoginPage)
    await wrapper.get('input[type="email"]').setValue('awa@doux-moments.sn')
    await wrapper.get('input[autocomplete="current-password"]').setValue('Mariage-Dakar-2026')
    await wrapper.get('form').trigger('submit')
    await settle()

    expect(authApi.login).toHaveBeenCalledWith('awa@doux-moments.sn', 'Mariage-Dakar-2026')
    expect(router.currentRoute.value.name).toBe('dashboard')
  })
})

describe('SignupPage', () => {
  async function fillStep(
    wrapper: ReturnType<typeof mountWithPlugins>['wrapper'],
    values: Record<string, string>,
  ) {
    for (const [selector, value] of Object.entries(values))
      await wrapper.get(selector).setValue(value)
    await wrapper.get('form').trigger('submit')
    await settle()
  }

  async function reachLastStep() {
    vi.mocked(authApi.slugAvailable).mockImplementation((params) =>
      Promise.resolve({ slug: params.slug ?? 'doux-moments', available: true, reason: null }),
    )
    const mounted = mountWithPlugins(SignupPage)
    await fillStep(mounted.wrapper, {
      'input[autocomplete="organization"]': 'Doux Moments',
      'input[autocomplete="address-level2"]': 'Dakar',
      select: 'SN',
    })
    await fillStep(mounted.wrapper, {
      'input[autocomplete="name"]': 'Awa Diop',
      'input[type="email"]': 'awa@doux-moments.sn',
      'input[autocomplete="new-password"]': 'Mariage-Dakar-2026',
    })
    return mounted
  }

  it('blocks a step until its fields are valid', async () => {
    const { wrapper } = mountWithPlugins(SignupPage)
    await wrapper.get('form').trigger('submit')
    await settle()

    expect(wrapper.find('input[autocomplete="organization"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Indiquez le nom de votre entreprise.')
  })

  it('proposes a subdomain from the company name and creates the space', async () => {
    vi.mocked(authApi.signup).mockImplementation(() => Promise.resolve(session))
    const { wrapper, router } = await reachLastStep()

    expect(authApi.slugAvailable).toHaveBeenCalledWith({ name: 'Doux Moments' })
    expect((wrapper.get('input[autocapitalize="none"]').element as HTMLInputElement).value).toBe(
      'doux-moments',
    )

    await wrapper.get('form').trigger('submit')
    await settle()

    expect(authApi.signup).toHaveBeenCalledWith({
      companyName: 'Doux Moments',
      city: 'Dakar',
      country: 'SN',
      weddingsPerYear: null,
      fullName: 'Awa Diop',
      email: 'awa@doux-moments.sn',
      phone: '',
      password: 'Mariage-Dakar-2026',
      slug: 'doux-moments',
      plan: 'pro',
    })
    expect(router.currentRoute.value.name).toBe('dashboard')
  })

  it('returns to the step holding a server error and shows it on the field', async () => {
    vi.mocked(authApi.signup).mockImplementation(() =>
      Promise.reject(
        new ApiError('email_taken', 'Un compte existe déjà avec cet email.', 400, {
          email: ['Email déjà utilisé.'],
        }),
      ),
    )
    const { wrapper } = await reachLastStep()
    await wrapper.get('form').trigger('submit')
    await settle()

    expect(wrapper.find('input[type="email"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Email déjà utilisé.')
  })
})

import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { authApi } from '@/api/auth'
import { ApiError } from '@/api/errors'
import { useSessionStore } from '@/stores/session'

vi.mock('@/api/auth', () => ({
  authApi: { csrf: vi.fn(), me: vi.fn(), login: vi.fn(), logout: vi.fn(), signup: vi.fn() },
}))

const session = {
  user: {
    id: 'u1',
    email: 'aicha.kone@maison-elegance.ci',
    fullName: 'Aïcha Koné',
    phone: '',
    isVerified: true,
    mustChangePassword: false,
    isPlatformAdmin: false,
  },
  organizations: [
    {
      organizationId: 'o1',
      slug: 'maison-elegance',
      name: 'Maison Élégance Events',
      role: 'owner' as const,
      roleLabel: 'Propriétaire',
      weddingsEnabled: true,
    },
    {
      organizationId: 'o2',
      slug: 'doux-moments',
      name: 'Doux Moments',
      role: 'planner' as const,
      roleLabel: 'Wedding planner',
      weddingsEnabled: true,
    },
  ],
}

describe('session store', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.mocked(authApi.csrf).mockImplementation(() => Promise.resolve(undefined))
  })

  it('logs in and selects the first organization', async () => {
    vi.mocked(authApi.login).mockImplementation(() => Promise.resolve(session))
    const store = useSessionStore()
    await store.login('aicha.kone@maison-elegance.ci', 'secret')

    expect(store.isAuthenticated).toBe(true)
    expect(store.firstName).toBe('Aïcha')
    expect(store.currentOrganization?.slug).toBe('maison-elegance')
    expect(store.role).toBe('owner')
  })

  it('remembers the chosen organization across reloads', async () => {
    vi.mocked(authApi.me).mockImplementation(() => Promise.resolve(session))
    const store = useSessionStore()
    await store.bootstrap()
    store.selectOrganization('doux-moments')

    setActivePinia(createPinia())
    const reloaded = useSessionStore()
    await reloaded.bootstrap()
    expect(reloaded.currentOrganization?.name).toBe('Doux Moments')
    expect(reloaded.role).toBe('planner')
  })

  it('treats a 401 at startup as a signed-out visitor', async () => {
    vi.mocked(authApi.me).mockImplementation(() =>
      Promise.reject(new ApiError('not_authenticated', 'Connectez-vous pour continuer.', 401)),
    )
    const store = useSessionStore()
    await store.bootstrap()

    expect(store.status).toBe('anonymous')
  })

  it('clears the session on logout even if the call fails', async () => {
    vi.mocked(authApi.login).mockImplementation(() => Promise.resolve(session))
    vi.mocked(authApi.logout).mockImplementation(() => Promise.reject(new Error('offline')))
    const store = useSessionStore()
    await store.login('a', 'b')
    await store.logout().catch(() => undefined)

    expect(store.isAuthenticated).toBe(false)
    expect(store.user).toBeNull()
  })
})

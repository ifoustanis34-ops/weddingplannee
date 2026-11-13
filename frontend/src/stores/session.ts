import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import {
  type OrganizationSummary,
  type Session,
  type SignupPayload,
  authApi,
  invitationApi,
} from '@/api/auth'
import { ApiError } from '@/api/errors'
import { disablePush } from '@/app/pwa'

const ORG_KEY = 'wedivo-organization'

function readStoredSlug(): string | null {
  try {
    return localStorage.getItem(ORG_KEY)
  } catch {
    return null
  }
}

function storeSlug(slug: string | null): void {
  try {
    if (slug) localStorage.setItem(ORG_KEY, slug)
    else localStorage.removeItem(ORG_KEY)
  } catch {
    // Storage unavailable: the choice only lasts for this tab.
  }
}

export const useSessionStore = defineStore('session', () => {
  const user = ref<Session['user'] | null>(null)
  const organizations = ref<OrganizationSummary[]>([])
  const currentSlug = ref<string | null>(readStoredSlug())
  const status = ref<'unknown' | 'authenticated' | 'anonymous'>('unknown')
  let bootstrapping: Promise<void> | null = null

  const isAuthenticated = computed(() => status.value === 'authenticated')
  const currentOrganization = computed<OrganizationSummary | null>(
    () =>
      organizations.value.find((org) => org.slug === currentSlug.value) ??
      organizations.value[0] ??
      null,
  )
  const role = computed(() => currentOrganization.value?.role ?? null)
  /** « Mariages » module of the current space (feedback 13/11/2026). */
  const weddingsEnabled = computed(() => currentOrganization.value?.weddingsEnabled ?? false)
  const firstName = computed(() => user.value?.fullName.split(' ')[0] ?? '')

  function apply(session: Session): void {
    user.value = session.user
    organizations.value = session.organizations
    status.value = 'authenticated'
    const known = session.organizations.some((org) => org.slug === currentSlug.value)
    if (!known) selectOrganization(session.organizations[0]?.slug ?? null)
  }

  function clear(): void {
    user.value = null
    organizations.value = []
    status.value = 'anonymous'
  }

  function selectOrganization(slug: string | null): void {
    currentSlug.value = slug
    storeSlug(slug)
  }

  /** Resolve the session once at startup (and after a hard refresh). */
  function bootstrap(): Promise<void> {
    if (status.value !== 'unknown') return Promise.resolve()
    bootstrapping ??= (async () => {
      try {
        await authApi.csrf()
        apply(await authApi.me())
      } catch (error) {
        if (error instanceof ApiError && error.status !== 401 && error.status !== 403) throw error
        clear()
      } finally {
        bootstrapping = null
      }
    })()
    return bootstrapping
  }

  async function login(email: string, password: string): Promise<void> {
    await authApi.csrf()
    apply(await authApi.login(email, password))
  }

  async function signup(payload: SignupPayload): Promise<void> {
    await authApi.csrf()
    const session = await authApi.signup(payload)
    selectOrganization(payload.slug)
    apply(session)
  }

  /** Join a space from a team invitation, then open it. */
  async function acceptInvitation(
    token: string,
    input: { fullName?: string; password: string },
    slug: string,
  ): Promise<void> {
    await authApi.csrf()
    const session = await invitationApi.accept(token, input)
    selectOrganization(slug)
    apply(session)
  }

  async function logout(): Promise<void> {
    try {
      // This device stops receiving the notifications of the account that leaves.
      await disablePush()
      await authApi.logout()
    } finally {
      clear()
    }
  }

  /** « Mon profil »: name and phone; the session follows. */
  async function updateProfile(input: { fullName?: string; phone?: string }): Promise<void> {
    apply(await authApi.updateProfile(input))
  }

  async function changePassword(current: string, next: string): Promise<void> {
    await authApi.changePassword(current, next)
    if (user.value) user.value = { ...user.value, mustChangePassword: false }
  }

  async function refresh(): Promise<void> {
    apply(await authApi.me())
  }

  return {
    user,
    organizations,
    currentSlug,
    status,
    isAuthenticated,
    currentOrganization,
    role,
    weddingsEnabled,
    firstName,
    bootstrap,
    login,
    signup,
    acceptInvitation,
    logout,
    refresh,
    updateProfile,
    changePassword,
    clear,
    selectOrganization,
  }
})

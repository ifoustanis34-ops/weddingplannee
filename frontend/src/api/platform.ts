import type { Plan, Role } from './auth'
import { api } from './client'

/** Platform console (super-admin, 14/11/2026): every agency and account, Wedivo team only. */

export interface Page<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface PlatformOverview {
  agencies: {
    total: number
    active: number
    suspended: number
    lifetime: number
    inTrial: number
    trialOver: number
    newThisMonth: number
    /** Active agencies where someone signed in during the last 30 days. */
    engaged: number
  }
  users: {
    total: number
    active: number
    inactive: number
    admins: number
    newThisMonth: number
    seenThisMonth: number
  }
  plans: { code: Plan; label: string; count: number }[]
  latestAgencies: { id: string; name: string; slug: string; createdAt: string }[]
  /** New agencies and accounts per month, 12 months, oldest first. */
  growth: { month: string; agencies: number; accounts: number }[]
  watchlist: {
    id: string
    name: string
    slug: string
    kind: 'trial_ending' | 'trial_ended' | 'suspended'
    at: string | null
    ownerEmail: string | null
  }[]
  activity: {
    id: string
    action: string
    targetLabel: string
    createdAt: string
    actorFullName: string | null
  }[]
  /** Django admin, when it is on (always in development). */
  djangoAdminUrl: string | null
}

export interface Agency {
  id: string
  name: string
  slug: string
  city: string
  country: string
  currency: string
  plan: Plan
  planLabel: string
  trialEndsAt: string | null
  lifetimeAccess: boolean
  lifetimeGrantedAt: string | null
  isActive: boolean
  suspendedAt: string | null
  suspensionReason: string
  weddingsEnabled: boolean
  adminNote: string
  membersCount: number
  ownerName: string | null
  ownerEmail: string | null
  createdAt: string
}

export type AgencyStatus = '' | 'active' | 'suspended' | 'lifetime' | 'trial' | 'trial_over'

export interface NewAgency {
  name: string
  slug: string
  city: string
  country: string
  plan: Plan
  ownerFullName: string
  ownerEmail: string
  ownerPhone: string
  ownerPassword: string
  lifetimeAccess: boolean
  weddingsEnabled: boolean
}

export type AgencyUpdate = Partial<
  Pick<
    Agency,
    | 'name'
    | 'city'
    | 'country'
    | 'plan'
    | 'trialEndsAt'
    | 'weddingsEnabled'
    | 'adminNote'
    | 'lifetimeAccess'
    | 'isActive'
    | 'suspensionReason'
  >
>

export interface AgencyMember {
  id: string
  userId: string
  fullName: string
  email: string
  phone: string
  userIsActive: boolean
  lastLogin: string | null
  role: Role
  roleLabel: string
  isActive: boolean
  joinedAt: string | null
}

export interface AccountMembership {
  id: string
  organizationId: string
  organizationName: string
  organizationSlug: string
  organizationIsActive: boolean
  role: Role
  roleLabel: string
  isActive: boolean
}

export interface Account {
  id: string
  email: string
  fullName: string
  phone: string
  isActive: boolean
  isVerified: boolean
  isPlatformAdmin: boolean
  mustChangePassword: boolean
  dateJoined: string
  lastLogin: string | null
  agenciesCount: number
  memberships: AccountMembership[]
}

export type AccountStatus = '' | 'active' | 'inactive' | 'admins' | 'never_logged_in' | 'no_agency'

export interface NewAccount {
  fullName: string
  email: string
  phone: string
  password: string
  organizationId: string | null
  role: Role | ''
  isPlatformAdmin: boolean
}

export type AccountUpdate = Partial<
  Pick<Account, 'fullName' | 'email' | 'phone' | 'isActive' | 'isPlatformAdmin'>
>

export interface JournalEntry {
  id: string
  action: string
  targetType: string
  targetId: string
  targetLabel: string
  organizationId: string | null
  organizationName: string | null
  changes: Record<string, unknown>
  actorName: string | null
  createdAt: string
}

interface ListParams {
  search?: string
  status?: string
  organization?: string
  page?: number
  pageSize?: number
}

export const platformApi = {
  overview: () => api.get<PlatformOverview>('/platform/overview').then((r) => r.data),

  agencies: (params: ListParams) =>
    api.get<Page<Agency>>('/platform/agencies', { params }).then((r) => r.data),
  agency: (id: string) => api.get<Agency>(`/platform/agencies/${id}`).then((r) => r.data),
  createAgency: (input: NewAgency) =>
    api
      .post<{ agency: Agency; ownerEmail: string; createdAccount: boolean }>(
        '/platform/agencies',
        input,
      )
      .then((r) => r.data),
  updateAgency: (id: string, input: AgencyUpdate) =>
    api.patch<Agency>(`/platform/agencies/${id}`, input).then((r) => r.data),
  agencyMembers: (id: string) =>
    api.get<AgencyMember[]>(`/platform/agencies/${id}/members`).then((r) => r.data),

  accounts: (params: ListParams) =>
    api.get<Page<Account>>('/platform/users', { params }).then((r) => r.data),
  account: (id: string) => api.get<Account>(`/platform/users/${id}`).then((r) => r.data),
  createAccount: (input: NewAccount) =>
    api.post<Account>('/platform/users', input).then((r) => r.data),
  updateAccount: (id: string, input: AccountUpdate) =>
    api.patch<Account>(`/platform/users/${id}`, input).then((r) => r.data),
  setPassword: (id: string, password: string) =>
    api.post(`/platform/users/${id}/password`, { password }).then(() => undefined),
  addMembership: (id: string, organizationId: string, role: Role) =>
    api
      .post<Account>(`/platform/users/${id}/memberships`, { organizationId, role })
      .then((r) => r.data),
  updateMembership: (id: string, input: { role?: Role; isActive?: boolean }) =>
    api.patch<AgencyMember>(`/platform/memberships/${id}`, input).then((r) => r.data),

  journal: (params: ListParams) =>
    api.get<Page<JournalEntry>>('/platform/journal', { params }).then((r) => r.data),
}

import type { Role } from './auth'
import { api } from './client'

export interface Organization {
  id: string
  slug: string
  name: string
  logo: string | null
  country: string
  city: string
  currency: 'XOF' | 'XAF' | 'EUR'
  timezone: string
  weddingsPerYear: number | null
  /** Daily email of the open alerts to the owner (reservations-stock.md §5.4). */
  alertDigest: boolean
  /** Cancellation policy (reservations-stock.md §4.1). */
  depositKeptOnCancel: boolean
  weddingsEnabled: boolean
  plan: 'essentiel' | 'pro' | 'agence'
  trialEndsAt: string | null
  quotePrefix: string
  quoteValidityDays: number
  legalMentions: string
}

export interface Member {
  id: string
  userId: string
  fullName: string
  email: string
  phone: string
  role: Role
  roleLabel: string
  isActive: boolean
}

export interface NewMember {
  fullName: string
  email: string
  phone: string
  role: Exclude<Role, 'owner'>
  password: string
}

export interface Invitation {
  id: string
  email: string
  role: Member['role']
  roleLabel: string
  invitedByName: string | null
  createdAt: string
  expiresAt: string
}

export type OrganizationInput = Partial<
  Pick<
    Organization,
    | 'name'
    | 'slug'
    | 'city'
    | 'country'
    | 'currency'
    | 'timezone'
    | 'legalMentions'
    | 'quotePrefix'
    | 'quoteValidityDays'
    | 'alertDigest'
    | 'depositKeptOnCancel'
    | 'weddingsEnabled'
  >
>

export const organizationApi = {
  get: () => api.get<Organization>('/organization').then((r) => r.data),
  /** The logo is not sent here: it belongs to the documents' identity (`api/branding`). */
  update: (input: OrganizationInput) =>
    api.patch<Organization>('/organization', input).then((r) => r.data),
  members: () => api.get<Member[]>('/organization/members').then((r) => r.data),
  updateMember: (id: string, input: { role?: Member['role']; isActive?: boolean }) =>
    api.patch<Member>(`/organization/members/${id}`, input).then((r) => r.data),
  invitations: () => api.get<Invitation[]>('/organization/invitations').then((r) => r.data),
  /** The owner opens an account (temporary password, changed at first sign-in). */
  createMember: (input: NewMember) =>
    api
      .post<{ member: Member; createdAccount: boolean }>('/organization/members', input)
      .then((r) => r.data),
  setMemberPassword: (id: string, password: string) =>
    api.post(`/organization/members/${id}/password`, { password }).then(() => undefined),
  invite: (input: { email: string; role: Member['role'] }) =>
    api.post<Invitation>('/organization/invitations', input).then((r) => r.data),
  cancelInvitation: (id: string) =>
    api.delete(`/organization/invitations/${id}`).then(() => undefined),
  changePlan: (plan: Organization['plan']) =>
    api.post<Organization>('/organization/plan', { plan }).then((r) => r.data),
}

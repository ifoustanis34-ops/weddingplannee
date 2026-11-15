import { api } from './client'

export type Role =
  | 'owner'
  | 'planner'
  | 'assistant'
  | 'accountant'
  /** Field roles (reservations-stock.md §12): no amounts, only their own modules. */
  | 'storekeeper'
  | 'team_lead'
  | 'staff'

export const FIELD_ROLES: readonly Role[] = ['storekeeper', 'team_lead', 'staff']
export type Plan = 'essentiel' | 'pro' | 'agence'

export interface SessionUser {
  id: string
  email: string
  fullName: string
  phone: string
  isVerified: boolean
  /** Account opened by the owner with a temporary password: choose your own first. */
  mustChangePassword: boolean
  /** Wedivo team (« super-admin »): opens the platform console /plateforme. */
  isPlatformAdmin: boolean
  /** Guided tour followed or declined; while false it is offered at sign-in (15/11/2026). */
  tourDone?: boolean
}

export interface OrganizationSummary {
  organizationId: string
  slug: string
  name: string
  role: Role
  roleLabel: string
  /** « Mariages » module on for this space (13/11/2026). */
  weddingsEnabled: boolean
}

export interface Session {
  user: SessionUser
  organizations: OrganizationSummary[]
}

export interface SignupPayload {
  companyName: string
  city: string
  country: string
  weddingsPerYear: number | null
  fullName: string
  email: string
  phone: string
  password: string
  slug: string
  plan: Plan
}

export interface SlugAvailability {
  slug: string
  available: boolean
  reason: string | null
}

export const authApi = {
  csrf: () => api.get('/auth/csrf').then(() => undefined),
  me: () => api.get<Session>('/auth/me').then((r) => r.data),
  updateProfile: (input: { fullName?: string; phone?: string }) =>
    api.patch<Session>('/auth/me', input).then((r) => r.data),
  changePassword: (currentPassword: string, newPassword: string) =>
    api.post('/auth/me/password', { currentPassword, newPassword }).then(() => undefined),
  finishTour: () => api.post('/auth/me/tour').then(() => undefined),
  login: (email: string, password: string) =>
    api.post<Session>('/auth/login', { email, password }).then((r) => r.data),
  signup: (payload: SignupPayload) =>
    api.post<Session>('/auth/signup', payload).then((r) => r.data),
  logout: () => api.post('/auth/logout').then(() => undefined),
  slugAvailable: (params: { slug?: string; name?: string }) =>
    api.get<SlugAvailability>('/auth/slug-available', { params }).then((r) => r.data),
  verifyEmail: (token: string) => api.post('/auth/verify-email', { token }).then(() => undefined),
  resendVerification: () => api.post('/auth/verify-email/resend').then(() => undefined),
  requestPasswordReset: (email: string) =>
    api.post('/auth/password-reset', { email }).then(() => undefined),
  confirmPasswordReset: (uid: string, token: string, password: string) =>
    api.post('/auth/password-reset/confirm', { uid, token, password }).then(() => undefined),
}

export interface InvitationPreview {
  organizationName: string
  organizationSlug: string
  email: string
  roleLabel: string
  invitedByName: string | null
  hasAccount: boolean
}

/** Team invitation link (public): preview, then join and open the session. */
export const invitationApi = {
  preview: (token: string) =>
    api.get<InvitationPreview>(`/auth/invitations/${token}`).then((r) => r.data),
  accept: (token: string, input: { fullName?: string; password: string }) =>
    api.post<Session>(`/auth/invitations/${token}/accept`, input).then((r) => r.data),
}

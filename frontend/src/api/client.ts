import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'

import { camelize, snakify } from './case'
import { toApiError } from './errors'

/**
 * Shared Axios instance.
 * - JWT session in httpOnly cookies (`withCredentials`), CSRF token echoed from the cookie.
 * - snake_case on the wire, camelCase in the app.
 * - One transparent session refresh on 401, then `onSessionExpired`.
 */
export const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  withXSRFToken: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
  timeout: 20_000,
})

interface Hooks {
  /** Slug of the active organization, sent as `X-Organization` (dev; prod uses the subdomain). */
  organizationSlug: () => string | null
  onSessionExpired: () => void
}

const hooks: Hooks = { organizationSlug: () => null, onSessionExpired: () => {} }

export function configureApi(overrides: Partial<Hooks>): void {
  Object.assign(hooks, overrides)
}

const SPACELESS_PATHS = ['/auth/', '/platform/', '/plans']
const AUTH_PATHS = ['/auth/login', '/auth/refresh', '/auth/logout', '/auth/signup']
const EXPIRED_CODES = new Set(['not_authenticated', 'authentication_failed', 'token_not_valid'])

api.interceptors.request.use((config) => {
  // Session and platform console calls never depend on a space: a suspended one must not
  // break them (the server answers 404 for an unknown or suspended space).
  const spaceless = SPACELESS_PATHS.some((path) => config.url?.startsWith(path))
  const slug = spaceless ? null : hooks.organizationSlug()
  if (slug) config.headers.set('X-Organization', slug)
  if (config.data && !(config.data instanceof FormData)) config.data = snakify(config.data)
  if (config.params) config.params = snakify(config.params)
  return config
})

let refreshing: Promise<void> | null = null

function refreshSession(): Promise<void> {
  // Single flight: concurrent 401s wait for the same refresh.
  // `/auth/refresh` is in AUTH_PATHS: its own 401 never triggers another refresh.
  refreshing ??= api
    .post('/auth/refresh')
    .then(() => undefined)
    .finally(() => {
      refreshing = null
    })
  return refreshing
}

type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean }

api.interceptors.response.use(
  (response) => {
    response.data = camelize(response.data)
    return response
  },
  async (error: AxiosError<{ code?: string }>) => {
    const config = error.config as RetriableConfig | undefined
    const status = error.response?.status
    const code = error.response?.data?.code ?? ''
    const isAuthCall = AUTH_PATHS.some((path) => config?.url?.startsWith(path))

    if (status === 401 && config && !config._retried && !isAuthCall) {
      if (EXPIRED_CODES.has(code)) {
        config._retried = true
        try {
          await refreshSession()
          return await api.request(config)
        } catch {
          hooks.onSessionExpired()
        }
      }
    }
    throw toApiError(error)
  },
)

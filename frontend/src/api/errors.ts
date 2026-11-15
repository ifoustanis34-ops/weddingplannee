import { isAxiosError } from 'axios'

import { toCamelKey } from './case'

/** Uniform error raised by every API call: `{ code, message, fields }` (CLAUDE.md §9). */
export class ApiError extends Error {
  readonly code: string
  readonly status: number
  /** Field errors keyed in camelCase, ready to map onto form fields. */
  readonly fields: Record<string, string[]>

  constructor(code: string, message: string, status = 0, fields: Record<string, string[]> = {}) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.fields = fields
  }

  fieldError(field: string): string | undefined {
    return this.fields[field]?.[0]
  }
}

interface ErrorBody {
  code?: unknown
  message?: unknown
  fields?: unknown
}

const NETWORK_MESSAGE = 'Connexion impossible. Vérifiez votre réseau puis réessayez.'
const TOO_LARGE_MESSAGE =
  'Fichier trop lourd pour le serveur. Choisissez une image plus légère (moins de 5 Mo) ou réduisez-la.'
const UNKNOWN_MESSAGE = 'Une erreur inattendue est survenue. Réessayez dans un instant.'

function normalizeFields(raw: unknown): Record<string, string[]> {
  if (!raw || typeof raw !== 'object') return {}
  const fields: Record<string, string[]> = {}
  for (const [key, value] of Object.entries(raw as Record<string, unknown>)) {
    const messages = Array.isArray(value) ? value.map(String) : [String(value)]
    fields[key.split('.').map(toCamelKey).join('.')] = messages
  }
  return fields
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error
  if (isAxiosError(error)) {
    if (!error.response) return new ApiError('network_error', NETWORK_MESSAGE)
    const { status, data } = error.response
    // Refused by the web server before reaching Wedivo (Nginx « client_max_body_size »).
    if (status === 413) return new ApiError('file_too_large', TOO_LARGE_MESSAGE, status)
    const body = (data && typeof data === 'object' ? data : {}) as ErrorBody
    return new ApiError(
      typeof body.code === 'string' ? body.code : `http_${status}`,
      typeof body.message === 'string' ? body.message : UNKNOWN_MESSAGE,
      status,
      normalizeFields(body.fields),
    )
  }
  return new ApiError('unknown_error', UNKNOWN_MESSAGE)
}

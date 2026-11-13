import { AxiosError, AxiosHeaders } from 'axios'
import { describe, expect, it } from 'vitest'

import { camelize, snakify } from '@/api/case'
import { ApiError, toApiError } from '@/api/errors'

describe('case conversion', () => {
  it('converts nested keys both ways and leaves values alone', () => {
    const api = {
      trial_ends_at: 'x',
      organizations: [{ role_label: 'Propriétaire', is_active: true }],
    }
    const app = camelize<Record<string, unknown>>(api)

    expect(app).toEqual({
      trialEndsAt: 'x',
      organizations: [{ roleLabel: 'Propriétaire', isActive: true }],
    })
    expect(snakify(app)).toEqual(api)
  })

  it('does not touch files or form data', () => {
    const form = new FormData()
    expect(snakify(form)).toBe(form)
  })
})

function axiosError(status: number, data: unknown): AxiosError {
  const headers = new AxiosHeaders()
  return new AxiosError('failed', 'ERR', { headers }, null, {
    status,
    statusText: '',
    data,
    headers: {},
    config: { headers },
  })
}

describe('toApiError', () => {
  it('reads the uniform error body and camelCases field names', () => {
    const error = toApiError(
      axiosError(400, {
        code: 'invalid',
        message: 'Certains champs sont à corriger.',
        fields: { company_name: ['Obligatoire.'] },
      }),
    )

    expect(error).toBeInstanceOf(ApiError)
    expect(error.code).toBe('invalid')
    expect(error.status).toBe(400)
    expect(error.fieldError('companyName')).toBe('Obligatoire.')
  })

  it('explains network failures', () => {
    const error = toApiError(new AxiosError('Network Error'))

    expect(error.code).toBe('network_error')
    expect(error.message).toContain('réseau')
  })
})

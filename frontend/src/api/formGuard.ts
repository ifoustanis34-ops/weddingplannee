import { ref } from 'vue'

import { api } from './client'

/**
 * Anti-bot of the public forms (20/11/2026, server `core/antibot.py`): a dated token fetched
 * when the form opens, and the honeypot field `website` that only robots fill. Added by
 * `authApi` to sign-in, sign-up and forgotten password; a person never sees any of it.
 */
export const honeypot = ref('')

const FRESH_MS = 100 * 60 * 1000 // the server accepts 2 h
let token: { value: string; at: number } | null = null
let fetching: Promise<string> | null = null

export function prepareFormToken(): Promise<string> {
  if (token && Date.now() - token.at < FRESH_MS) return Promise.resolve(token.value)
  fetching ??= api
    .get<{ formToken: string }>('/auth/form-token')
    .then((r) => {
      token = { value: r.data.formToken, at: Date.now() }
      return token.value
    })
    .finally(() => {
      fetching = null
    })
  return fetching
}

export async function guardFields(): Promise<{ formToken: string; website: string }> {
  const formToken = await prepareFormToken().catch(() => '')
  // One token per sending: the next form fetches a new one.
  token = null
  return { formToken, website: honeypot.value }
}

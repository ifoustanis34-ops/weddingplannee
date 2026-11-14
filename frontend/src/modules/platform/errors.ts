import { toApiError } from '@/api/errors'

/** Server field errors (snake_case) keyed like the form (camelCase), first message each. */
export function fieldErrors(error: unknown): {
  fields: Record<string, string | undefined>
  message: string
} {
  const apiError = toApiError(error)
  const fields = Object.fromEntries(
    Object.entries(apiError.fields).map(([key, messages]) => [
      key.replace(/_(\w)/g, (_, c: string) => c.toUpperCase()),
      messages[0],
    ]),
  )
  return { fields, message: apiError.message }
}

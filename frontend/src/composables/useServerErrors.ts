import { ApiError, toApiError } from '@/api/errors'

import { useToast } from './useToast'

/**
 * Route an API failure to the form: field errors go next to the fields, anything else becomes a
 * toast. Returns the field names that received an error.
 */
export function useServerErrors() {
  const toast = useToast()

  return function apply(
    error: unknown,
    setFieldError: (field: string, message: string) => void,
    knownFields: readonly string[],
  ): string[] {
    const apiError = error instanceof ApiError ? error : toApiError(error)
    const matched = Object.entries(apiError.fields).filter(([field]) => knownFields.includes(field))
    for (const [field, messages] of matched) setFieldError(field, messages[0] ?? apiError.message)
    if (!matched.length) toast.error(apiError.message)
    return matched.map(([field]) => field)
  }
}

import type { TypedSchema, TypedSchemaError } from 'vee-validate'
import type { z } from 'zod'

/**
 * vee-validate ↔ zod 4 bridge. The official `@vee-validate/zod` adapter only accepts zod 3,
 * whose versions carry a known vulnerability (GHSA-mrhx-c7xc-m3w5); vee-validate 4 has no
 * built-in zod 4 support yet. Same contract as the official adapter: errors grouped by field
 * path (`a.b`, `items[0].name`), first error first.
 */
export function toTypedSchema<S extends z.ZodType>(
  schema: S,
): TypedSchema<z.input<S>, z.output<S>> {
  return {
    __type: 'VVTypedSchema',
    async parse(values) {
      const result = await schema.safeParseAsync(values)
      if (result.success) return { value: result.data, errors: [] }
      const byPath = new Map<string, TypedSchemaError>()
      for (const issue of result.error.issues) {
        const path = toPath(issue.path)
        const entry = byPath.get(path) ?? { path, errors: [] }
        entry.errors.push(issue.message)
        byPath.set(path, entry)
      }
      return { errors: [...byPath.values()] }
    },
  }
}

function toPath(segments: readonly PropertyKey[]): string {
  return segments
    .map((segment, index) =>
      typeof segment === 'number' ? `[${segment}]` : `${index ? '.' : ''}${String(segment)}`,
    )
    .join('')
}

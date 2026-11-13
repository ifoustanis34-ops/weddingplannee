export const controlClasses = (hasError: boolean): string =>
  [
    'w-full rounded-[10px] border bg-surface px-3 text-ink placeholder:text-muted',
    'focus:border-violet focus:shadow-[0_0_0_3px_var(--violet-soft)] focus:outline-none',
    'disabled:cursor-not-allowed disabled:bg-surface-2 disabled:text-muted',
    hasError ? 'border-red' : 'border-line-2',
  ].join(' ')

export const describedBy = (id: string, error?: string, hint?: string): string | undefined =>
  error ? `${id}-error` : hint ? `${id}-hint` : undefined

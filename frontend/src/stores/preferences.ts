import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

export type Theme = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'wedivo-theme'

function readStoredTheme(): Theme {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    if (value === 'light' || value === 'dark') return value
  } catch {
    // Storage can be unavailable (private mode); fall back to system preference.
  }
  return 'system'
}

const darkQuery =
  typeof matchMedia === 'function' ? matchMedia('(prefers-color-scheme: dark)') : null

/** Theme: system preference by default, manual choice remembered (CLAUDE.md §6). */
export const usePreferencesStore = defineStore('preferences', () => {
  const theme = ref<Theme>(readStoredTheme())
  const systemDark = ref(darkQuery?.matches ?? false)
  darkQuery?.addEventListener('change', (event) => (systemDark.value = event.matches))

  const resolvedTheme = computed<'light' | 'dark'>(() =>
    theme.value === 'system' ? (systemDark.value ? 'dark' : 'light') : theme.value,
  )

  function toggleTheme(): void {
    theme.value = resolvedTheme.value === 'dark' ? 'light' : 'dark'
  }

  watch(
    theme,
    (value) => {
      const root = document.documentElement
      if (value === 'system') delete root.dataset.theme
      else root.dataset.theme = value
      try {
        if (value === 'system') localStorage.removeItem(STORAGE_KEY)
        else localStorage.setItem(STORAGE_KEY, value)
      } catch {
        // Ignore storage failures: the theme still applies for this session.
      }
    },
    { immediate: true },
  )

  return { theme, resolvedTheme, toggleTheme }
})

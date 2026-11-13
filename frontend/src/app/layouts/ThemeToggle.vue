<script setup lang="ts">
import { Moon, Sun } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { usePreferencesStore } from '@/stores/preferences'

const { t } = useI18n()
const preferences = usePreferencesStore()
const isDark = computed(() => preferences.resolvedTheme === 'dark')
</script>

<template>
  <button
    type="button"
    class="inline-flex size-10 items-center justify-center rounded-[10px] border border-line-2 bg-surface text-ink-2 hover:bg-surface-2 hover:text-ink"
    :aria-label="t('theme.toggle')"
    :aria-pressed="isDark"
    @click="preferences.toggleTheme()"
  >
    <Sun v-if="isDark" class="size-[18px]" aria-hidden="true" />
    <Moon v-else class="size-[18px]" aria-hidden="true" />
  </button>
</template>

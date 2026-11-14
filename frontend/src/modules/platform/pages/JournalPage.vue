<script setup lang="ts">
import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import { ScrollText } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { type JournalEntry, platformApi } from '@/api/platform'
import { formatDateTime } from '@/composables/useDate'
import { WCard, WEmptyState } from '@/design'

import ConsolePager from '../components/ConsolePager.vue'

/** Every action done from the console: who, what, on whom, when. */
const i18n = useI18n()
const { t } = i18n
const page = ref(1)
const journal = useQuery({
  queryKey: computed(() => ['platform', 'journal', page.value]),
  queryFn: () => platformApi.journal({ page: page.value }),
  placeholderData: keepPreviousData,
})

function label(entry: JournalEntry): string {
  const key = `platform.journal.actions.${entry.action.replace('.', '_')}`
  return i18n.te(key) ? t(key) : entry.action
}

/** « Rôle : planner → owner · Accès : oui → non » from the recorded changes. */
function details(entry: JournalEntry): string {
  return Object.entries(entry.changes)
    .map(([field, value]) => {
      if (value && typeof value === 'object' && 'from' in value && 'to' in value) {
        return `${field} : ${show(value.from)} → ${show(value.to)}`
      }
      return `${field} : ${show(value)}`
    })
    .join(' · ')
}
function show(value: unknown): string {
  if (value === true) return t('platform.common.yes')
  if (value === false) return t('platform.common.no')
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'string' || typeof value === 'number') return String(value)
  return JSON.stringify(value)
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-[1180px] flex-col gap-5">
    <header>
      <h1>{{ t('platform.journal.title') }}</h1>
      <p class="text-muted">{{ t('platform.journal.subtitle') }}</p>
    </header>
    <WCard>
      <div v-if="journal.isPending.value" class="skeleton h-64" />
      <WEmptyState
        v-else-if="journal.isError.value"
        :title="t('platform.common.loadError')"
        :description="toApiError(journal.error.value).message"
      />
      <WEmptyState
        v-else-if="!journal.data.value?.results.length"
        :icon="ScrollText"
        :title="t('platform.journal.empty')"
      />
      <template v-else>
        <ol class="flex flex-col">
          <li
            v-for="entry in journal.data.value.results"
            :key="entry.id"
            class="flex flex-col gap-1 border-b border-line py-3 last:border-0 sm:flex-row sm:gap-4"
          >
            <time class="shrink-0 text-[13px] text-muted sm:w-40" :datetime="entry.createdAt">{{
              formatDateTime(entry.createdAt)
            }}</time>
            <div class="min-w-0 flex-1">
              <p>
                <span class="font-bold">{{ label(entry) }}</span>
                <span class="text-ink-2"> · {{ entry.targetLabel || entry.targetId }}</span>
                <span v-if="entry.actorName" class="text-muted">
                  {{ t('platform.journal.by', { name: entry.actorName }) }}</span
                >
              </p>
              <p
                v-if="Object.keys(entry.changes).length"
                class="text-[12.5px] break-words text-muted"
              >
                {{ details(entry) }}
              </p>
            </div>
          </li>
        </ol>
        <ConsolePager v-model="page" :count="journal.data.value.count" />
      </template>
    </WCard>
  </div>
</template>

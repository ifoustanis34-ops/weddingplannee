<script setup lang="ts">
import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import { Building2, Plus, Search } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { toApiError } from '@/api/errors'
import { type AgencyStatus, platformApi } from '@/api/platform'
import { formatDate } from '@/composables/useDate'
import { useMediaQuery } from '@/composables/useMediaQuery'
import { WButton, WCard, WChips, WEmptyState, WInput } from '@/design'

import AgencyBadges from '../components/AgencyBadges.vue'
import AgencyCreateModal from '../components/AgencyCreateModal.vue'
import AgencyDrawer from '../components/AgencyDrawer.vue'
import ConsolePager from '../components/ConsolePager.vue'

/** Every agency: search, filter by access, open one (?agence=id), create one. */
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const compact = useMediaQuery('(max-width: 639px)')

const STATUSES: AgencyStatus[] = ['', 'active', 'lifetime', 'trial', 'trial_over', 'suspended']
const statusOptions = computed(() =>
  STATUSES.map((value) => ({
    value,
    label: value ? t(`platform.agencies.statuses.${value}`) : t('platform.common.all'),
  })),
)
const status = ref<AgencyStatus>(
  STATUSES.includes(route.query.statut as AgencyStatus) ? (route.query.statut as AgencyStatus) : '',
)
const search = ref('')
const debounced = ref('')
let timer: ReturnType<typeof setTimeout> | undefined
watch(search, (value) => {
  clearTimeout(timer)
  timer = setTimeout(() => (debounced.value = value.trim()), 250)
})
const page = ref(1)
watch([status, debounced], () => (page.value = 1))
watch(status, (value) => router.replace({ query: { ...route.query, statut: value || undefined } }))

const agencies = useQuery({
  queryKey: computed(() => ['platform', 'agencies', status.value, debounced.value, page.value]),
  queryFn: () =>
    platformApi.agencies({ status: status.value, search: debounced.value, page: page.value }),
  placeholderData: keepPreviousData,
})

const openId = computed(() => (typeof route.query.agence === 'string' ? route.query.agence : null))
const drawerOpen = computed({
  get: () => !!openId.value,
  set: (open) => {
    if (!open) void router.replace({ query: { ...route.query, agence: undefined } })
  },
})
function open(id: string): void {
  void router.replace({ query: { ...route.query, agence: id } })
}
// « Créer » from the console home (?nouvelle=1).
const createOpen = ref(route.query.nouvelle === '1')
watch(createOpen, (isOpen) => {
  if (!isOpen && route.query.nouvelle) {
    void router.replace({ query: { ...route.query, nouvelle: undefined } })
  }
})
</script>

<template>
  <div class="mx-auto flex w-full max-w-[1180px] flex-col gap-5">
    <header class="flex flex-wrap items-end gap-3">
      <div class="min-w-0 flex-1">
        <h1>{{ t('platform.agencies.title') }}</h1>
        <p class="text-muted">{{ t('platform.agencies.subtitle') }}</p>
      </div>
      <WButton @click="createOpen = true"
        ><Plus class="size-4" aria-hidden="true" />{{ t('platform.agencies.create') }}</WButton
      >
    </header>

    <WCard>
      <div class="flex flex-col gap-3 lg:flex-row lg:items-center">
        <div class="relative lg:w-80">
          <Search
            class="pointer-events-none absolute top-1/2 left-3 z-10 size-4 -translate-y-1/2 text-muted"
            aria-hidden="true"
          />
          <WInput
            v-model="search"
            type="search"
            class="[&_input]:pl-9"
            :label="t('platform.common.search')"
            hide-label
            :placeholder="t('platform.common.search')"
          />
        </div>
        <WChips v-model="status" :options="statusOptions" :label="t('platform.agencies.title')" />
      </div>

      <div v-if="agencies.isPending.value" class="skeleton mt-4 h-64" />
      <WEmptyState
        v-else-if="agencies.isError.value"
        class="mt-4"
        :title="t('platform.common.loadError')"
        :description="toApiError(agencies.error.value).message"
      />
      <WEmptyState
        v-else-if="!agencies.data.value?.results.length"
        class="mt-4"
        :icon="Building2"
        :title="t('platform.agencies.empty')"
      />
      <template v-else>
        <!-- Phones: one card per agency -->
        <ul v-if="compact" class="mt-4 flex flex-col gap-2.5">
          <li v-for="agency in agencies.data.value.results" :key="agency.id">
            <button
              type="button"
              class="w-full rounded-wd border border-line p-3.5 text-left active:bg-surface-2"
              @click="open(agency.id)"
            >
              <span class="flex items-start justify-between gap-3">
                <span class="min-w-0">
                  <span class="block font-bold break-words">{{ agency.name }}</span>
                  <span class="block truncate text-[12.5px] text-muted"
                    >{{ agency.slug }} · {{ agency.city }}, {{ agency.country }}</span
                  >
                </span>
                <span class="shrink-0 text-[13px] font-semibold">{{ agency.planLabel }}</span>
              </span>
              <span class="mt-2 block truncate text-[13px] text-ink-2">{{
                agency.ownerEmail ?? t('platform.agencies.noOwner')
              }}</span>
              <span class="mt-2.5 flex flex-wrap items-center justify-between gap-2">
                <AgencyBadges :agency="agency" />
                <span class="text-[12.5px] text-muted"
                  >{{ agency.membersCount }}
                  {{ t('platform.agencies.columns.members').toLowerCase() }} ·
                  {{ formatDate(agency.createdAt) }}</span
                >
              </span>
            </button>
          </li>
        </ul>
        <div v-else class="mt-4 overflow-x-auto">
          <table class="w-full min-w-[820px] border-collapse text-[14px]">
            <caption class="sr-only">
              {{
                t('platform.agencies.title')
              }}
            </caption>
            <thead>
              <tr class="text-left text-[12.5px] font-bold text-muted">
                <th scope="col" class="border-b border-line px-3 py-2.5">
                  {{ t('platform.agencies.columns.agency') }}
                </th>
                <th scope="col" class="border-b border-line px-3 py-2.5">
                  {{ t('platform.agencies.columns.owner') }}
                </th>
                <th scope="col" class="border-b border-line px-3 py-2.5">
                  {{ t('platform.agencies.columns.plan') }}
                </th>
                <th scope="col" class="border-b border-line px-3 py-2.5">
                  {{ t('platform.agencies.columns.access') }}
                </th>
                <th scope="col" class="border-b border-line px-3 py-2.5 text-right">
                  {{ t('platform.agencies.columns.members') }}
                </th>
                <th scope="col" class="border-b border-line px-3 py-2.5">
                  {{ t('platform.agencies.columns.created') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="agency in agencies.data.value.results"
                :key="agency.id"
                class="cursor-pointer hover:bg-surface-2"
                @click="open(agency.id)"
              >
                <td class="border-b border-line px-3 py-3">
                  <button
                    type="button"
                    class="text-left font-bold hover:underline"
                    @click.stop="open(agency.id)"
                  >
                    {{ agency.name }}
                  </button>
                  <span class="block text-[12.5px] text-muted"
                    >{{ agency.slug }} · {{ agency.city }}, {{ agency.country }}</span
                  >
                </td>
                <td class="border-b border-line px-3 py-3">
                  <template v-if="agency.ownerEmail">
                    <span class="block font-semibold">{{ agency.ownerName }}</span>
                    <span class="block text-[12.5px] text-muted">{{ agency.ownerEmail }}</span>
                  </template>
                  <span v-else class="text-muted">{{ t('platform.agencies.noOwner') }}</span>
                </td>
                <td class="border-b border-line px-3 py-3 font-semibold">{{ agency.planLabel }}</td>
                <td class="border-b border-line px-3 py-3"><AgencyBadges :agency="agency" /></td>
                <td class="num border-b border-line px-3 py-3 text-right">
                  {{ agency.membersCount }}
                </td>
                <td class="border-b border-line px-3 py-3 text-muted">
                  {{ formatDate(agency.createdAt) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <ConsolePager v-model="page" :count="agencies.data.value.count" />
      </template>
    </WCard>

    <AgencyDrawer v-model:open="drawerOpen" :agency-id="openId" />
    <AgencyCreateModal v-model:open="createOpen" @created="open" />
  </div>
</template>

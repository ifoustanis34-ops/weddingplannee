<script setup lang="ts">
import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import { Plus, Search, Users } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { toApiError } from '@/api/errors'
import { type AccountStatus, platformApi } from '@/api/platform'
import { formatDate, formatDateTime } from '@/composables/useDate'
import { useMediaQuery } from '@/composables/useMediaQuery'
import { WAvatar, WBadge, WButton, WCard, WChips, WEmptyState, WInput } from '@/design'

import AccountCreateModal from '../components/AccountCreateModal.vue'
import AccountDrawer from '../components/AccountDrawer.vue'
import ConsolePager from '../components/ConsolePager.vue'

/** Every account of the platform: search, filter, open one (?compte=id), create one. */
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const compact = useMediaQuery('(max-width: 639px)')

const STATUSES: AccountStatus[] = [
  '',
  'active',
  'inactive',
  'admins',
  'never_logged_in',
  'no_agency',
]
const statusOptions = computed(() =>
  STATUSES.map((value) => ({
    value,
    label: value ? t(`platform.accounts.statuses.${value}`) : t('platform.common.all'),
  })),
)
const status = ref<AccountStatus>(
  STATUSES.includes(route.query.statut as AccountStatus)
    ? (route.query.statut as AccountStatus)
    : '',
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

const accounts = useQuery({
  queryKey: computed(() => ['platform', 'accounts', status.value, debounced.value, page.value]),
  queryFn: () =>
    platformApi.accounts({ status: status.value, search: debounced.value, page: page.value }),
  placeholderData: keepPreviousData,
})

const openId = computed(() => (typeof route.query.compte === 'string' ? route.query.compte : null))
const drawerOpen = computed({
  get: () => !!openId.value,
  set: (open) => {
    if (!open) void router.replace({ query: { ...route.query, compte: undefined } })
  },
})
function open(id: string): void {
  void router.replace({ query: { ...route.query, compte: id } })
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
        <h1>{{ t('platform.accounts.title') }}</h1>
        <p class="text-muted">{{ t('platform.accounts.subtitle') }}</p>
      </div>
      <WButton @click="createOpen = true"
        ><Plus class="size-4" aria-hidden="true" />{{ t('platform.accounts.create') }}</WButton
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
        <WChips v-model="status" :options="statusOptions" :label="t('platform.accounts.title')" />
      </div>

      <div v-if="accounts.isPending.value" class="skeleton mt-4 h-64" />
      <WEmptyState
        v-else-if="accounts.isError.value"
        class="mt-4"
        :title="t('platform.common.loadError')"
        :description="toApiError(accounts.error.value).message"
      />
      <WEmptyState
        v-else-if="!accounts.data.value?.results.length"
        class="mt-4"
        :icon="Users"
        :title="t('platform.accounts.empty')"
      />
      <template v-else>
        <!-- Phones: one card per account -->
        <ul v-if="compact" class="mt-4 flex flex-col gap-2.5">
          <li v-for="account in accounts.data.value.results" :key="account.id">
            <button
              type="button"
              class="w-full rounded-wd border border-line p-3.5 text-left active:bg-surface-2"
              :class="!account.isActive && 'opacity-60'"
              @click="open(account.id)"
            >
              <span class="flex items-center gap-3">
                <WAvatar :name="account.fullName" />
                <span class="min-w-0">
                  <span class="block font-bold break-words">{{ account.fullName }}</span>
                  <span class="block truncate text-[12.5px] text-muted">{{ account.email }}</span>
                </span>
              </span>
              <span class="mt-2.5 block text-[13px] text-ink-2">
                <template v-if="account.memberships.length">
                  <span
                    v-for="membership in account.memberships"
                    :key="membership.id"
                    class="block truncate"
                  >
                    <span class="font-semibold">{{ membership.organizationName }}</span>
                    <span class="text-muted"> · {{ membership.roleLabel }}</span>
                  </span>
                </template>
                <span v-else class="text-muted">{{ t('platform.accounts.noAgency') }}</span>
              </span>
              <span class="mt-2.5 flex flex-wrap items-center justify-between gap-2">
                <span class="flex flex-wrap gap-1.5">
                  <WBadge :tone="account.isActive ? 'green' : 'red'">{{
                    account.isActive
                      ? t('platform.accounts.badges.active')
                      : t('platform.accounts.badges.inactive')
                  }}</WBadge>
                  <WBadge v-if="account.isPlatformAdmin" tone="violet">{{
                    t('platform.accounts.badges.admin')
                  }}</WBadge>
                </span>
                <span class="text-[12.5px] text-muted">{{
                  account.lastLogin ? formatDateTime(account.lastLogin) : t('platform.common.never')
                }}</span>
              </span>
            </button>
          </li>
        </ul>
        <div v-else class="mt-4 overflow-x-auto">
          <table class="w-full min-w-[820px] border-collapse text-[14px]">
            <caption class="sr-only">
              {{
                t('platform.accounts.title')
              }}
            </caption>
            <thead>
              <tr class="text-left text-[12.5px] font-bold text-muted">
                <th scope="col" class="border-b border-line px-3 py-2.5">
                  {{ t('platform.accounts.columns.account') }}
                </th>
                <th scope="col" class="border-b border-line px-3 py-2.5">
                  {{ t('platform.accounts.columns.agencies') }}
                </th>
                <th scope="col" class="border-b border-line px-3 py-2.5">
                  {{ t('platform.accounts.columns.status') }}
                </th>
                <th scope="col" class="border-b border-line px-3 py-2.5">
                  {{ t('platform.accounts.columns.lastLogin') }}
                </th>
                <th scope="col" class="border-b border-line px-3 py-2.5">
                  {{ t('platform.accounts.columns.joined') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="account in accounts.data.value.results"
                :key="account.id"
                class="cursor-pointer hover:bg-surface-2"
                :class="!account.isActive && 'opacity-60'"
                @click="open(account.id)"
              >
                <td class="border-b border-line px-3 py-3">
                  <span class="flex items-center gap-3">
                    <WAvatar :name="account.fullName" />
                    <span class="min-w-0">
                      <button
                        type="button"
                        class="block text-left font-bold hover:underline"
                        @click.stop="open(account.id)"
                      >
                        {{ account.fullName }}
                      </button>
                      <span class="block text-[12.5px] text-muted">{{ account.email }}</span>
                    </span>
                  </span>
                </td>
                <td class="border-b border-line px-3 py-3">
                  <span v-if="!account.memberships.length" class="text-muted">{{
                    t('platform.accounts.noAgency')
                  }}</span>
                  <span v-else class="flex flex-col">
                    <span
                      v-for="membership in account.memberships.slice(0, 2)"
                      :key="membership.id"
                      class="truncate"
                      :class="!membership.isActive && 'text-muted line-through'"
                    >
                      <span class="font-semibold">{{ membership.organizationName }}</span>
                      <span class="text-muted"> · {{ membership.roleLabel }}</span>
                    </span>
                    <span v-if="account.memberships.length > 2" class="text-[12.5px] text-muted">{{
                      t('platform.accounts.moreAgencies', {
                        count: account.memberships.length - 2,
                      })
                    }}</span>
                  </span>
                </td>
                <td class="border-b border-line px-3 py-3">
                  <span class="flex flex-wrap gap-1.5">
                    <WBadge :tone="account.isActive ? 'green' : 'red'">{{
                      account.isActive
                        ? t('platform.accounts.badges.active')
                        : t('platform.accounts.badges.inactive')
                    }}</WBadge>
                    <WBadge v-if="account.isPlatformAdmin" tone="violet">{{
                      t('platform.accounts.badges.admin')
                    }}</WBadge>
                    <WBadge v-if="account.mustChangePassword" tone="gold">{{
                      t('platform.accounts.badges.temporary')
                    }}</WBadge>
                  </span>
                </td>
                <td class="border-b border-line px-3 py-3 text-muted">
                  {{
                    account.lastLogin
                      ? formatDateTime(account.lastLogin)
                      : t('platform.common.never')
                  }}
                </td>
                <td class="border-b border-line px-3 py-3 text-muted">
                  {{ formatDate(account.dateJoined) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <ConsolePager v-model="page" :count="accounts.data.value.count" />
      </template>
    </WCard>

    <AccountDrawer v-model:open="drawerOpen" :account-id="openId" />
    <AccountCreateModal v-model:open="createOpen" @created="open" />
  </div>
</template>

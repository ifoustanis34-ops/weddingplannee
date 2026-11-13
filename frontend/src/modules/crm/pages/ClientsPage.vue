<script setup lang="ts">
import { Phone, Plus, Search, Users } from '@lucide/vue'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import DownloadMenu from '@/components/DownloadMenu.vue'
import { toApiError } from '@/api/errors'
import { formatDate } from '@/composables/useDate'
import { formatAmount } from '@/composables/useMoney'
import { usePermissions } from '@/composables/usePermissions'
import {
  type TableColumn,
  WAvatar,
  WBadge,
  WButton,
  WCard,
  WEmptyState,
  WInput,
  WSelect,
  WSwitch,
  WTable,
} from '@/design'

import { CLIENT_PAGE_SIZE, useClients } from '../api'
import ClientDrawer from '../components/ClientDrawer.vue'
import ClientFormModal from '../components/ClientFormModal.vue'
import type { Client, ClientSort } from '../types'

/** « Clients » (reservations-stock.md §4.4): one record per client, no pipeline. */
const { t } = useI18n()
const { can } = usePermissions()
const route = useRoute()
const router = useRouter()
const seesMoney = computed(() => can('viewFinance'))

const search = ref('')
const debouncedSearch = ref('')
let timer: ReturnType<typeof setTimeout> | undefined
watch(search, (value) => {
  clearTimeout(timer)
  timer = setTimeout(() => (debouncedSearch.value = value), 300)
})
onBeforeUnmount(() => clearTimeout(timer))
const archived = ref(false)
const ordering = ref<ClientSort>('name')
const clients = useClients(() => ({
  search: debouncedSearch.value.trim(),
  archived: archived.value,
  ordering: ordering.value,
}))
const rows = computed(() => clients.data.value?.results ?? [])
const truncated = computed(() => Boolean(clients.data.value?.next))

const sortOptions = computed(() => [
  { value: 'name', label: t('clients.sort.name') },
  ...(seesMoney.value
    ? [
        { value: '-revenue', label: t('clients.sort.revenue') },
        { value: '-balance_due', label: t('clients.sort.balance') },
      ]
    : []),
  { value: '-last_order_at', label: t('clients.sort.recent') },
])

const columns = computed<TableColumn[]>(() => [
  { key: 'name', label: t('clients.columns.client') },
  { key: 'phone', label: t('clients.fields.phone') },
  { key: 'orderCount', label: t('clients.columns.orders'), align: 'right' },
  ...(seesMoney.value
    ? [
        { key: 'revenue', label: t('clients.columns.revenue'), align: 'right' as const },
        { key: 'balanceDue', label: t('clients.columns.balance'), align: 'right' as const },
      ]
    : []),
  { key: 'lastOrderAt', label: t('clients.columns.lastOrder') },
])
const row = (value: unknown) => value as Client

// --- Drawer and creation, addressable by URL (?client=<id>, ?nouveau=1) -----------------
const openId = computed(() => (typeof route.query.client === 'string' ? route.query.client : null))
const openClient = (client: Client) =>
  void router.replace({ query: { ...route.query, client: client.id } })
const closeClient = () => void router.replace({ query: { ...route.query, client: undefined } })

const createOpen = ref(false)
watch(
  () => route.query.nouveau,
  (value) => {
    if (value && can('editSales')) {
      createOpen.value = true
      void router.replace({ query: { ...route.query, nouveau: undefined } })
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="flex flex-col gap-[22px]">
    <header class="flex flex-wrap items-end gap-x-6 gap-y-3">
      <div class="min-w-0 flex-1">
        <h1>{{ t('clients.title') }}</h1>
        <p class="mt-1 max-w-[64ch] text-muted">{{ t('clients.subtitle') }}</p>
      </div>
      <DownloadMenu url="/exports/clients" filename="clients" />
      <WButton v-if="can('editSales')" @click="createOpen = true"
        ><Plus class="size-[18px]" aria-hidden="true" />{{ t('clients.add') }}</WButton
      >
    </header>

    <div class="flex flex-wrap items-end gap-3">
      <WInput
        v-model="search"
        class="min-w-[220px] flex-1"
        type="search"
        :label="t('clients.search')"
        :placeholder="t('clients.searchPlaceholder')"
        hide-label
      >
        <template #prefix><Search class="size-[18px] text-muted" aria-hidden="true" /></template>
      </WInput>
      <WSelect
        v-model="ordering"
        class="w-[210px]"
        :label="t('clients.sortLabel')"
        :options="sortOptions"
        hide-label
      />
      <WSwitch v-model="archived" :label="t('clients.showArchived')" />
    </div>

    <WCard>
      <WEmptyState
        v-if="clients.isError.value"
        :title="t('clients.loadError')"
        :description="toApiError(clients.error.value).message"
      >
        <WButton variant="secondary" @click="clients.refetch()">{{ t('common.retry') }}</WButton>
      </WEmptyState>
      <WTable
        v-else
        :columns="columns"
        :rows="rows as unknown as Record<string, unknown>[]"
        row-key="id"
        :caption="t('clients.title')"
        :loading="clients.isPending.value"
        clickable-rows
        @row-click="(r) => openClient(row(r))"
      >
        <template #empty>
          <WEmptyState v-if="search" :icon="Search" :title="t('clients.noResults')">
            <WButton variant="secondary" @click="search = ''">{{
              t('clients.clearSearch')
            }}</WButton>
          </WEmptyState>
          <WEmptyState
            v-else
            :icon="Users"
            :title="t('clients.emptyTitle')"
            :description="t('clients.emptyText')"
          >
            <WButton v-if="can('editSales')" @click="createOpen = true"
              ><Plus class="size-[18px]" aria-hidden="true" />{{ t('clients.add') }}</WButton
            >
          </WEmptyState>
        </template>
        <template #cell-name="{ row: r }">
          <span class="flex items-center gap-3">
            <WAvatar :name="row(r).name" :size="40" />
            <span class="min-w-0">
              <span class="flex items-center gap-2">
                <span class="truncate font-bold">{{ row(r).name }}</span>
                <WBadge v-if="row(r).isArchived" tone="grey">{{
                  t('clients.archivedBadge')
                }}</WBadge>
              </span>
              <span v-if="row(r).company" class="block truncate text-[12.5px] text-muted">{{
                row(r).company
              }}</span>
            </span>
          </span>
        </template>
        <template #cell-phone="{ row: r }">
          <a
            v-if="row(r).phone"
            :href="`tel:${row(r).phone.replace(/\s/g, '')}`"
            class="num inline-flex items-center gap-1.5 whitespace-nowrap hover:text-violet"
            @click.stop
            ><Phone class="size-[15px]" aria-hidden="true" />{{ row(r).phone }}</a
          >
          <span v-else class="text-muted">—</span>
        </template>
        <template #cell-orderCount="{ row: r }"
          ><span class="num">{{ row(r).orderCount }}</span></template
        >
        <template #cell-revenue="{ row: r }"
          ><span class="num">{{
            row(r).revenue ? formatAmount(row(r).revenue!) : '—'
          }}</span></template
        >
        <template #cell-balanceDue="{ row: r }"
          ><span class="num" :class="(row(r).balanceDue ?? 0) > 0 && 'font-bold text-coral'">{{
            row(r).balanceDue ? formatAmount(row(r).balanceDue!) : '—'
          }}</span></template
        >
        <template #cell-lastOrderAt="{ row: r }">{{
          row(r).lastOrderAt ? formatDate(row(r).lastOrderAt!) : '—'
        }}</template>
      </WTable>
      <p v-if="truncated" class="mt-3 text-[13px] text-muted">
        {{ t('clients.tooMany', { count: CLIENT_PAGE_SIZE }) }}
      </p>
    </WCard>

    <ClientDrawer :client-id="openId" @close="closeClient" />
    <ClientFormModal v-model:open="createOpen" @saved="openClient" />
  </div>
</template>

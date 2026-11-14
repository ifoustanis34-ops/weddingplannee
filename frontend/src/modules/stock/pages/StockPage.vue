<script setup lang="ts">
import { ArrowLeftRight, LayoutGrid, List, Package, Plus, Search } from '@lucide/vue'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import DownloadMenu from '@/components/DownloadMenu.vue'
import { toApiError } from '@/api/errors'
import { formatAmount, formatMoneyShort } from '@/composables/useMoney'
import { usePermissions } from '@/composables/usePermissions'
import {
  type TableColumn,
  WButton,
  WCard,
  WChips,
  WEmptyState,
  WInput,
  WSelect,
  WTable,
  WTabs,
  WTile,
} from '@/design'

import { useItemCategories, useItems, useStockStats } from '../api'
import AvailabilityTab from '../components/AvailabilityTab.vue'
import InventoryTab from '../components/InventoryTab.vue'
import ItemCard from '../components/ItemCard.vue'
import ItemDrawer from '../components/ItemDrawer.vue'
import ItemFormModal from '../components/ItemFormModal.vue'
import MovementModal from '../components/MovementModal.vue'
import PacksTab from '../components/PacksTab.vue'
import PartnersTab from '../components/PartnersTab.vue'
import StockBar from '../components/StockBar.vue'
import StockLegend from '../components/StockLegend.vue'
import type { Item } from '../types'

/** « Stock & matériel » (reservations-stock.md §5.5). */
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { can } = usePermissions()

const TABS = ['items', 'partners', 'packs', 'availability', 'inventory'] as const
type Tab = (typeof TABS)[number]
const tab = computed<Tab>({
  get: () =>
    (TABS as readonly string[]).includes(String(route.query.onglet))
      ? (route.query.onglet as Tab)
      : 'items',
  set: (value) =>
    void router.replace({
      query: { ...route.query, onglet: value === 'items' ? undefined : value },
    }),
})
const tabs = computed(() => TABS.map((key) => ({ key, label: t(`stock.tabs.${key}`) })))

const stats = useStockStats()
const categories = useItemCategories()
const search = ref('')
const debounced = ref('')
let timer: ReturnType<typeof setTimeout> | undefined
watch(search, (value) => {
  clearTimeout(timer)
  timer = setTimeout(() => (debounced.value = value.trim()), 250)
})
onBeforeUnmount(() => clearTimeout(timer))
const category = ref('all')
const status = ref('')
// « Notre matériel » / « Chez les partenaires » (feedback 14/11/2026).
const source = ref<'' | 'own' | 'partner'>('')
const sourceOptions = computed(() =>
  (['', 'own', 'partner'] as const).map((value) => ({
    value,
    label: t(`stock.sources.${value || 'all'}`),
  })),
)
const view = ref<'grid' | 'table'>('grid')
const items = useItems(() => ({
  search: debounced.value,
  category: category.value === 'all' ? '' : category.value,
  status: status.value,
  source: source.value,
}))

const chips = computed(() => [
  { value: 'all', label: t('stock.allCategories') },
  ...(categories.data.value ?? []).map((c) => ({ value: c.id, label: c.name })),
])
const statusOptions = computed(() =>
  (['', 'available', 'low', 'maintenance', 'out_of_service'] as const).map((value) => ({
    value,
    label: t(`stock.statuses.${value || 'all'}`),
  })),
)
const columns = computed<TableColumn[]>(() => [
  { key: 'name', label: t('stock.columns.item') },
  { key: 'categoryName', label: t('stock.columns.category') },
  { key: 'bar', label: t('stock.columns.available') },
  { key: 'totalQuantity', label: t('stock.columns.total'), align: 'right' },
  { key: 'partnerQuantity', label: t('stock.tabs.partners'), align: 'right' },
  ...(can('viewStockPrices')
    ? [{ key: 'rentPrice', label: t('stock.columns.rent'), align: 'right' as const }]
    : []),
  { key: 'location', label: t('stock.columns.location') },
])
const row = (value: unknown) => value as Item

const openId = computed(() =>
  typeof route.query.article === 'string' ? route.query.article : null,
)
const openItem = (id: string) => void router.replace({ query: { ...route.query, article: id } })
const closeItem = () => void router.replace({ query: { ...route.query, article: undefined } })
const createOpen = ref(false)
const movementOpen = ref(false)
</script>

<template>
  <div class="flex flex-col gap-[22px]">
    <header class="flex flex-wrap items-end gap-x-6 gap-y-3">
      <div class="min-w-0 flex-1">
        <h1>{{ t('stock.title') }}</h1>
        <p class="mt-1 max-w-[64ch] text-muted">{{ t('stock.subtitle') }}</p>
      </div>
      <DownloadMenu url="/exports/items" filename="stock" />
      <div v-if="can('editStock')" class="flex flex-wrap gap-2">
        <WButton variant="secondary" @click="movementOpen = true">
          <ArrowLeftRight class="size-[18px]" aria-hidden="true" />{{ t('stock.addMovement') }}
        </WButton>
        <WButton @click="createOpen = true">
          <Plus class="size-[18px]" aria-hidden="true" />{{ t('stock.addItem') }}
        </WButton>
      </div>
    </header>

    <div v-if="stats.data.value" class="grid grid-cols-2 gap-3.5 lg:grid-cols-4">
      <WTile :label="t('stock.tiles.items')" :value="String(stats.data.value.items)">
        <span>
          {{ t('stock.tiles.itemsHint', { count: formatAmount(stats.data.value.units) }) }}
        </span>
      </WTile>
      <WTile
        v-if="stats.data.value.stockValue !== null"
        :label="t('stock.tiles.value')"
        :value="formatMoneyShort(stats.data.value.stockValue)"
      >
        <span>{{ t('stock.tiles.valueHint') }}</span>
      </WTile>
      <WTile :label="t('stock.tiles.maintenance')" :value="String(stats.data.value.inMaintenance)">
        <span>
          {{ t('stock.tiles.maintenanceHint', { count: stats.data.value.outOfService }) }}
        </span>
      </WTile>
      <WTile :label="t('stock.tiles.alerts')" :value="String(stats.data.value.alerts)">
        <span>{{ t('stock.tiles.alertsHint') }}</span>
      </WTile>
    </div>
    <div v-else class="grid grid-cols-2 gap-3.5 lg:grid-cols-4">
      <div v-for="n in 4" :key="n" class="skeleton h-[92px] rounded-wd-lg" />
    </div>

    <WTabs v-model="tab" :tabs="tabs" :label="t('stock.title')">
      <template v-if="tab === 'items'">
        <div class="mb-4 flex flex-col gap-3">
          <WChips v-model="source" :options="sourceOptions" :label="t('stock.tabs.items')" />
          <WChips v-model="category" :options="chips" :label="t('stock.fields.category')" />
          <div class="flex flex-wrap items-end gap-3">
            <WInput
              v-model="search"
              class="min-w-[220px] flex-1"
              type="search"
              :label="t('stock.search')"
              :placeholder="t('stock.searchPlaceholder')"
              hide-label
            >
              <template #prefix
                ><Search class="size-[18px] text-muted" aria-hidden="true"
              /></template>
            </WInput>
            <WSelect
              v-model="status"
              class="w-[190px]"
              :label="t('stock.statusFilter')"
              :options="statusOptions"
              hide-label
            />
            <div
              class="flex rounded-[10px] border border-line-2 p-0.5"
              role="radiogroup"
              :aria-label="t('stock.view')"
            >
              <button
                v-for="[key, icon] in [
                  ['grid', LayoutGrid],
                  ['table', List],
                ] as const"
                :key="key"
                type="button"
                role="radio"
                :aria-checked="view === key"
                :aria-label="t(`stock.views.${key}`)"
                class="inline-flex size-9 items-center justify-center rounded-[8px]"
                :class="view === key ? 'bg-surface-2 text-ink' : 'text-muted'"
                @click="view = key"
              >
                <component :is="icon" class="size-[18px]" aria-hidden="true" />
              </button>
            </div>
          </div>
          <StockLegend />
        </div>

        <WEmptyState
          v-if="items.isError.value"
          :title="t('stock.loadError')"
          :description="toApiError(items.error.value).message"
        >
          <WButton variant="secondary" @click="items.refetch()">{{ t('common.retry') }}</WButton>
        </WEmptyState>
        <div
          v-else-if="items.isPending.value"
          class="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4"
        >
          <div v-for="n in 8" :key="n" class="skeleton h-64 rounded-wd-lg" />
        </div>
        <WEmptyState
          v-else-if="!items.data.value?.length"
          :icon="Package"
          :title="
            debounced || status || source || category !== 'all'
              ? t('stock.noResults')
              : t('stock.emptyTitle')
          "
          :description="
            debounced || status || category !== 'all' ? undefined : t('stock.emptyText')
          "
        >
          <WButton v-if="can('editStock') && !debounced" @click="createOpen = true">
            <Plus class="size-[18px]" aria-hidden="true" />{{ t('stock.addItem') }}
          </WButton>
        </WEmptyState>
        <div
          v-else-if="view === 'grid'"
          class="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4"
          :class="items.isPlaceholderData.value && 'opacity-60'"
        >
          <ItemCard
            v-for="item in items.data.value"
            :key="item.id"
            :item="item"
            @open="openItem(item.id)"
          />
        </div>
        <WCard v-else>
          <WTable
            :columns="columns"
            :rows="items.data.value as unknown as Record<string, unknown>[]"
            row-key="id"
            :caption="t('stock.title')"
            clickable-rows
            @row-click="(r) => openItem(row(r).id)"
          >
            <template #cell-name="{ row: r }">
              <span class="block font-bold">{{ row(r).name }}</span>
              <span class="text-[12px] text-muted">{{ row(r).reference }}</span>
            </template>
            <template #cell-bar="{ row: r }">
              <div class="w-[180px]">
                <StockBar
                  v-if="row(r).today"
                  :available="row(r).today!.available"
                  :reserved="row(r).today!.reserved"
                  :out="row(r).today!.out"
                  :maintenance="row(r).today!.maintenance + row(r).today!.outOfService"
                />
                <span class="num mt-1 block text-[12px] font-semibold">{{
                  t('stock.availableOf', {
                    available: row(r).today?.available ?? 0,
                    total: row(r).totalQuantity,
                  })
                }}</span>
              </div>
            </template>
            <template #cell-totalQuantity="{ row: r }"
              ><span class="num">{{ row(r).totalQuantity }}</span></template
            >
            <template #cell-partnerQuantity="{ row: r }"
              ><span class="num" :class="!row(r).partnerQuantity && 'text-muted'">{{
                row(r).partnerQuantity || '—'
              }}</span></template
            >
            <template #cell-rentPrice="{ row: r }"
              ><span class="num">{{
                row(r).rentPrice !== null ? formatAmount(row(r).rentPrice!) : '—'
              }}</span></template
            >
            <template #cell-location="{ row: r }">{{ row(r).location || '—' }}</template>
          </WTable>
        </WCard>
      </template>
      <PartnersTab v-else-if="tab === 'partners'" />
      <PacksTab v-else-if="tab === 'packs'" />
      <AvailabilityTab v-else-if="tab === 'availability'" @open="openItem" />
      <InventoryTab v-else />
    </WTabs>

    <ItemDrawer :item-id="openId" @close="closeItem" />
    <ItemFormModal v-model:open="createOpen" @saved="(item) => openItem(item.id)" />
    <MovementModal v-model:open="movementOpen" />
  </div>
</template>

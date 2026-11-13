<script setup lang="ts">
import { Landmark, Wallet } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { toApiError } from '@/api/errors'
import DownloadMenu from '@/components/DownloadMenu.vue'
import { formatDate } from '@/composables/useDate'
import { formatAmount, formatMoney, formatMoneyShort } from '@/composables/useMoney'
import { usePermissions } from '@/composables/usePermissions'
import {
  type TableColumn,
  WBadge,
  WButton,
  WCard,
  WDateBlock,
  WEmptyState,
  WProgress,
  WTable,
  WTabs,
  WTile,
} from '@/design'

import type { PeriodRequest } from '@/modules/dashboard/api'
import PeriodPicker from '@/modules/dashboard/components/PeriodPicker.vue'

import { useContracts, useFinanceSummary } from '../api'
import ExpensesTab from '../components/ExpensesTab.vue'
import InvoicesTab from '../components/InvoicesTab.vue'
import ProfitabilityTab from '../components/ProfitabilityTab.vue'
import RevenuesTab from '../components/RevenuesTab.vue'
import TreasuryTab from '../components/TreasuryTab.vue'
import ContractDrawer from '../components/ContractDrawer.vue'
import PaymentModal from '../components/PaymentModal.vue'
import type { ContractRow } from '../types'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { can } = usePermissions()
const canManage = computed(() => can('manageFinance'))

const summary = useFinanceSummary()
const contracts = useContracts()
const rows = computed(() => contracts.data.value ?? [])
const showMargins = computed(() => summary.data.value?.margin !== undefined)

const openedId = computed(() =>
  typeof route.query.contract === 'string' ? route.query.contract : null,
)
const openContract = (row: unknown) =>
  void router.replace({ query: { ...route.query, contract: (row as ContractRow).id } })
const close = () => void router.replace({ query: { ...route.query, contract: undefined } })

const columns = computed<TableColumn[]>(() => [
  { key: 'clientName', label: t('finance.fields.client'), sortable: true },
  { key: 'total', label: t('finance.fields.contract'), sortable: true, align: 'right' },
  { key: 'collected', label: t('finance.fields.collected'), sortable: true, align: 'right' },
  { key: 'balance', label: t('finance.fields.balance'), sortable: true, align: 'right' },
  ...(showMargins.value
    ? [
        {
          key: 'margin',
          label: t('finance.fields.marginShort'),
          sortable: true,
          align: 'right' as const,
        },
      ]
    : []),
])
const row = (value: unknown) => value as ContractRow

const paymentOpen = ref(false)

// Tabs (§6): treasury, invoices, revenues, expenses, profitability (owner and accountant see
// them all; the planner reads invoices, revenues and contracts). Addressable: `?onglet=`.
const TABS = ['tresorerie', 'factures', 'recettes', 'depenses', 'rentabilite', 'contrats'] as const
type Tab = (typeof TABS)[number]
const MARGIN_TABS: Tab[] = ['tresorerie', 'depenses', 'rentabilite']
const allowed = computed(() =>
  TABS.filter((key) => can('viewMargins') || !MARGIN_TABS.includes(key)),
)
const tabs = computed(() => allowed.value.map((key) => ({ key, label: t(`finance.tabs.${key}`) })))
const tab = computed<Tab>({
  get: () => {
    const wanted = String(route.query.onglet ?? '')
    if ((allowed.value as readonly string[]).includes(wanted)) return wanted as Tab
    if (typeof route.query.contract === 'string') return 'contrats'
    return allowed.value[0]!
  },
  set: (value) => void router.replace({ query: { ...route.query, onglet: value } }),
})
const withPeriod = computed(() => ['tresorerie', 'recettes', 'rentabilite'].includes(tab.value))
const period = ref<PeriodRequest>({ period: 'month' })

// « Télécharger » follows the tab: what is on screen, in PDF, CSV or Excel.
const download = computed(() => {
  const range = {
    period: period.value.period,
    from: period.value.period === 'custom' ? period.value.from : undefined,
    to: period.value.period === 'custom' ? period.value.to : undefined,
  }
  const all = ['pdf', 'csv', 'xlsx'] as ('pdf' | 'csv' | 'xlsx')[]
  switch (tab.value) {
    case 'tresorerie':
      return {
        url: '/reports/revenue',
        name: 'tresorerie',
        params: range,
        formats: all,
        param: 'output',
      }
    case 'factures':
      return {
        url: '/exports/invoices',
        name: 'factures',
        params: {},
        formats: all,
        param: 'output',
      }
    case 'recettes':
      return {
        url: '/exports/revenues',
        name: 'recettes',
        params: range,
        formats: all,
        param: 'output',
      }
    case 'depenses':
      return {
        url: '/exports/expenses',
        name: 'depenses',
        params: {},
        formats: all,
        param: 'output',
      }
    case 'rentabilite':
      return {
        url: '/reports/margins',
        name: 'rentabilite',
        params: range,
        formats: all,
        param: 'output',
      }
    default:
      // Contracts: the historical export (CSV, Excel), owner and accountant.
      return showMargins.value
        ? {
            url: '/finance/export',
            name: 'contrats',
            params: {},
            formats: ['csv', 'xlsx'] as ('pdf' | 'csv' | 'xlsx')[],
            param: 'type',
          }
        : null
  }
})
const openFromInstallment = (contract: string) =>
  void router.replace({ query: { ...route.query, contract } })
</script>

<template>
  <div class="flex flex-col gap-[22px]">
    <header class="flex flex-wrap items-end gap-x-6 gap-y-3">
      <div class="min-w-0 flex-1">
        <h1>{{ t('finance.title') }}</h1>
        <p class="mt-1 max-w-[64ch] text-muted">{{ t('finance.subtitle') }}</p>
      </div>
      <div class="flex flex-wrap gap-2">
        <DownloadMenu
          v-if="download"
          :url="download.url"
          :filename="download.name"
          :params="download.params"
          :formats="download.formats"
          :param="download.param"
        />
        <WButton v-if="canManage" @click="paymentOpen = true"
          ><Wallet class="size-[18px]" aria-hidden="true" />{{
            t('finance.payment.title')
          }}</WButton
        >
      </div>
    </header>

    <div class="flex flex-col gap-3">
      <WTabs v-model="tab" :tabs="tabs" :label="t('finance.title')" />
      <PeriodPicker v-if="withPeriod" v-model="period" />
    </div>

    <TreasuryTab v-if="tab === 'tresorerie'" :period="period" />
    <InvoicesTab v-else-if="tab === 'factures'" />
    <RevenuesTab v-else-if="tab === 'recettes'" :period="period" />
    <ExpensesTab v-else-if="tab === 'depenses'" />
    <ProfitabilityTab v-else-if="tab === 'rentabilite'" :period="period" />

    <!-- « Contrats »: tiles with full amounts (complement §12) -->
    <section
      v-if="tab === 'contrats'"
      class="grid grid-cols-2 gap-3.5 min-[1001px]:grid-cols-4"
      :aria-busy="summary.isPending.value"
    >
      <template v-if="summary.data.value">
        <WTile
          :label="t('finance.tiles.total')"
          :value="formatMoney(summary.data.value.contractsTotal)"
        >
          {{
            t(
              'finance.contractsCount',
              { count: summary.data.value.contractsCount },
              summary.data.value.contractsCount,
            )
          }}
        </WTile>
        <WTile :label="t('finance.fields.collected')">
          <template #value
            ><span class="text-green">{{
              formatMoney(summary.data.value.collected)
            }}</span></template
          >
          {{ t('finance.thisMonth') }} {{ formatMoney(summary.data.value.collectedThisMonth) }}
        </WTile>
        <WTile
          dark
          :label="t('finance.fields.balanceDue')"
          :value="formatMoney(summary.data.value.balanceDue)"
        >
          <template v-if="summary.data.value.overdue"
            >{{ t('finance.overduePrefix') }}{{ formatMoney(summary.data.value.overdue) }}</template
          >
        </WTile>
        <WTile
          v-if="showMargins"
          :label="t('finance.fields.forecastMargin')"
          :value="formatMoney(summary.data.value.margin ?? 0)"
        >
          {{ t('finance.expensesPrefix') }}{{ formatMoney(summary.data.value.expenses ?? 0) }}
        </WTile>
      </template>
      <div v-for="n in summary.data.value ? 0 : 4" v-else :key="n" class="skeleton h-[92px]" />
    </section>

    <div
      v-if="tab === 'contrats'"
      class="grid grid-cols-1 items-start gap-4 min-[1101px]:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]"
    >
      <WCard :title="t('finance.contractsTitle')" :subtitle="t('finance.contractsHint')">
        <WEmptyState
          v-if="contracts.isError.value"
          :title="t('finance.loadError')"
          :description="toApiError(contracts.error.value).message"
        >
          <WButton variant="secondary" @click="contracts.refetch()">{{
            t('common.retry')
          }}</WButton>
        </WEmptyState>
        <WTable
          v-else
          :columns="columns"
          :rows="rows as unknown as Record<string, unknown>[]"
          row-key="id"
          :caption="t('finance.contractsTitle')"
          :loading="contracts.isPending.value"
          :page-size="25"
          clickable-rows
          @row-click="openContract"
        >
          <template #empty>
            <WEmptyState
              :icon="Landmark"
              :title="t('finance.emptyTitle')"
              :description="t('finance.emptyText')"
            >
              <WButton :to="{ name: 'quotes' }" variant="secondary">{{ t('nav.quotes') }}</WButton>
            </WEmptyState>
          </template>
          <template #cell-clientName="{ row: r }">
            <span class="block font-bold">{{ row(r).clientName }}</span>
            <span class="block text-[12.5px] text-muted">{{
              row(r).weddingDate
                ? t('finance.weddingOn', { date: formatDate(row(r).weddingDate!) })
                : row(r).number
            }}</span>
            <WProgress
              class="mt-1.5 max-w-[180px]"
              :value="row(r).progress"
              :label="t('finance.fields.progress')"
              green-when-full
            />
          </template>
          <template #cell-total="{ row: r }">{{ formatAmount(row(r).total) }}</template>
          <template #cell-collected="{ row: r }">{{ formatAmount(row(r).collected) }}</template>
          <template #cell-balance="{ row: r }">
            <span v-if="row(r).balance > 0" class="font-bold">{{
              formatAmount(row(r).balance)
            }}</span>
            <WBadge v-else tone="green">{{ t('finance.settled') }}</WBadge>
          </template>
          <template #cell-margin="{ row: r }">{{ formatAmount(row(r).margin ?? 0) }}</template>
        </WTable>
      </WCard>

      <WCard :title="t('finance.upcoming.title')" :subtitle="t('finance.upcoming.subtitle')">
        <div v-if="summary.isPending.value" class="skeleton h-48" />
        <p v-else-if="!summary.data.value?.upcoming.length" class="text-muted">
          {{ t('finance.upcoming.empty') }}
        </p>
        <ul v-else class="-my-2 divide-y divide-line">
          <li v-for="item in summary.data.value.upcoming" :key="item.id">
            <button
              type="button"
              class="flex w-full items-center gap-3 rounded-wd py-2.5 text-left hover:bg-surface-2"
              @click="openFromInstallment(item.contract)"
            >
              <WDateBlock :date="item.dueDate" />
              <span class="min-w-0 flex-1">
                <span class="block truncate font-bold">{{ item.clientName }}</span>
                <span class="block truncate text-[12.5px] text-muted"
                  >{{ item.label
                  }}<span v-if="item.isOverdue" class="font-bold text-red">{{
                    t('finance.upcoming.late')
                  }}</span></span
                >
              </span>
              <span class="num font-semibold">{{ formatMoneyShort(item.remaining) }}</span>
            </button>
          </li>
        </ul>

        <template v-if="summary.data.value?.vendorsDue?.length">
          <h3 class="mt-6 mb-1">{{ t('finance.vendorsDue') }}</h3>
          <ul class="divide-y divide-line">
            <li
              v-for="vendor in summary.data.value.vendorsDue"
              :key="vendor.id"
              class="flex items-center gap-3 py-2.5"
            >
              <span
                class="flex size-9 shrink-0 items-center justify-center rounded-full bg-gold-soft font-display text-[12.5px] font-semibold text-gold"
                aria-hidden="true"
                >{{ vendor.name.charAt(0).toUpperCase() }}</span
              >
              <span class="min-w-0 flex-1">
                <span class="block truncate font-bold">{{ vendor.name }}</span>
                <span class="block text-[12.5px] text-muted">{{ vendor.categoryLabel }}</span>
              </span>
              <span class="num font-semibold">{{ formatMoneyShort(vendor.due) }}</span>
            </li>
          </ul>
        </template>
      </WCard>
    </div>

    <ContractDrawer :contract-id="openedId" @close="close" />
    <PaymentModal v-model:open="paymentOpen" />
  </div>
</template>

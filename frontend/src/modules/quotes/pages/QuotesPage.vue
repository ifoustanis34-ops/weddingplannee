<script setup lang="ts">
import { BookOpen, FileText, Plus, Search } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import DownloadMenu from '@/components/DownloadMenu.vue'
import { toApiError } from '@/api/errors'
import { formatDate } from '@/composables/useDate'
import { formatMoney } from '@/composables/useMoney'
import { usePermissions } from '@/composables/usePermissions'
import { useToast } from '@/composables/useToast'
import {
  type TableColumn,
  WBadge,
  WButton,
  WEmptyState,
  WInput,
  WMoney,
  WTable,
  WTabs,
  WTile,
} from '@/design'

import { quotesApi, useQuoteAction, useQuoteStats, useQuoteSummary, useQuotes } from '../api'
import NewQuoteModal from '../components/NewQuoteModal.vue'
import { QUOTE_TABS, type QuoteTab, STATUS_TONES } from '../constants'
import type { QuoteListItem, QuoteStatus } from '../types'

/** Quote list (complement §9): four tiles, tabs, one action per line. */
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const toast = useToast()
const { can } = usePermissions()
const canEdit = computed(() => can('editSales'))

const tab = computed<QuoteTab>({
  get: () =>
    (QUOTE_TABS as readonly string[]).includes(String(route.query.tab))
      ? (route.query.tab as QuoteTab)
      : 'all',
  set: (value) =>
    void router.replace({ query: { ...route.query, tab: value === 'all' ? undefined : value } }),
})
const search = ref(typeof route.query.q === 'string' ? route.query.q : '')
const debounced = ref(search.value)
let timer: ReturnType<typeof setTimeout> | undefined
watch(search, (value) => {
  clearTimeout(timer)
  timer = setTimeout(() => (debounced.value = value.trim()), 300)
})

const quotes = useQuotes(
  computed(() => ({ status: tab.value === 'all' ? '' : tab.value, search: debounced.value })),
)
const summary = useQuoteSummary()
const stats = useQuoteStats()
const rows = computed(() => quotes.data.value?.results ?? [])

const tabs = computed(() =>
  QUOTE_TABS.map((key) => {
    const counts = summary.data.value
    let count: number | undefined
    if (counts) {
      count =
        key === 'all'
          ? (['draft', 'sent', 'accepted', 'refused', 'expired'] as const).reduce(
              (sum, s) => sum + counts[s],
              0,
            )
          : counts[key]
    }
    return { key, label: t(`quotes.tabs.${key}`), count }
  }),
)

// --- Tiles ------------------------------------------------------------------------------------
/** « 18 min », « 1 h 40 » */
function duration(minutes: number | null | undefined): string {
  if (minutes === null || minutes === undefined) return '—'
  if (minutes < 60) return t('quotes.stats.minutes', { minutes })
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return rest
    ? t('quotes.stats.hoursMinutes', { hours, minutes: String(rest).padStart(2, '0') })
    : t('quotes.stats.hours', { hours })
}
const tiles = computed(() => {
  const s = stats.data.value
  return [
    { key: 'creation', value: duration(s?.medianCreationMinutes), dark: true },
    { key: 'sent', value: s ? String(s.sentThisMonth) : '—' },
    {
      key: 'acceptance',
      value: s?.acceptanceRate == null ? '—' : `${s.acceptanceRate} %`,
    },
    { key: 'pending', value: s ? formatMoney(s.pendingAmount) : '—' },
  ]
})

// --- Table ------------------------------------------------------------------------------------
const isTemplates = computed(() => tab.value === 'templates')
const columns = computed<TableColumn[]>(() =>
  isTemplates.value
    ? [
        { key: 'templateName', label: t('quotes.fields.templateName'), sortable: true },
        { key: 'total', label: t('quotes.columns.amount'), sortable: true, align: 'right' },
        { key: 'updatedAt', label: t('common.fields.updatedAt'), sortable: true },
      ]
    : [
        { key: 'number', label: t('quotes.number'), sortable: true },
        { key: 'clientName', label: t('quotes.client'), sortable: true },
        { key: 'issueDate', label: t('quotes.date'), sortable: true },
        { key: 'total', label: t('quotes.columns.amount'), sortable: true, align: 'right' },
        { key: 'status', label: t('common.fields.status'), sortable: true },
        { key: 'action', label: t('quotes.action') },
      ],
)
const row = (value: unknown) => value as QuoteListItem
const open = (value: unknown) =>
  void router.push({ name: 'quote-edit', params: { id: row(value).id } })
const newOpen = ref(false)

// --- Line actions: draft → send, sent → accepted, accepted → contract -------------------------
const busy = ref<string | null>(null)
const send = useQuoteAction(quotesApi.send)
const accept = useQuoteAction(quotesApi.accept)
const convert = useQuoteAction(quotesApi.convert)

async function act(quote: QuoteListItem): Promise<void> {
  busy.value = quote.id
  try {
    if (quote.status === 'draft') {
      const sent = await send.mutateAsync(quote.id)
      toast.success(t('quotes.sentNumber', { number: sent.number }))
    } else if (quote.status === 'sent') {
      await accept.mutateAsync(quote.id)
      toast.success(t('quotes.accepted'))
    } else if (quote.status === 'accepted') {
      await convert.mutateAsync(quote.id)
      toast.success(t('quotes.converted'))
    }
  } catch (error) {
    toast.error(toApiError(error).message)
  } finally {
    busy.value = null
  }
}
function actionLabel(quote: QuoteListItem): string | null {
  if (quote.status === 'draft') return t('quotes.sendShort')
  if (quote.status === 'sent') return t('quotes.markAccepted')
  if (quote.status === 'accepted' && !quote.hasContract) return t('quotes.convert')
  return null
}
</script>

<template>
  <div class="flex flex-col gap-[22px]">
    <header class="flex flex-wrap items-end gap-x-6 gap-y-3">
      <div class="min-w-0 flex-1">
        <h1>{{ t('quotes.title') }}</h1>
        <p class="mt-1 max-w-[64ch] text-muted">{{ t('quotes.subtitle') }}</p>
      </div>
      <DownloadMenu url="/exports/quotes" filename="devis" />
      <div class="flex flex-wrap gap-2">
        <WButton :to="{ name: 'catalog' }" variant="secondary"
          ><BookOpen class="size-[18px]" aria-hidden="true" />{{
            t('quotes.manageCatalog')
          }}</WButton
        >
        <WButton v-if="canEdit" @click="newOpen = true"
          ><Plus class="size-[18px]" aria-hidden="true" />{{ t('quotes.new') }}</WButton
        >
      </div>
    </header>

    <section
      class="grid grid-cols-2 gap-3.5 min-[1001px]:grid-cols-4"
      :aria-busy="stats.isPending.value"
    >
      <WTile
        v-for="tile in tiles"
        :key="tile.key"
        :label="t(`quotes.stats.${tile.key}`)"
        :value="tile.value"
        :dark="tile.dark"
      />
    </section>

    <section class="rounded-wd-lg border border-line bg-surface p-5">
      <WTabs v-model="tab" :tabs="tabs" :label="t('quotes.title')">
        <WInput
          v-model="search"
          type="search"
          hide-label
          :label="t('quotes.search')"
          :placeholder="t('quotes.searchPlaceholder')"
          class="mb-3 sm:max-w-[340px]"
        >
          <template #prefix><Search class="size-4" aria-hidden="true" /></template>
        </WInput>
        <WEmptyState
          v-if="quotes.isError.value"
          :title="t('quotes.loadError')"
          :description="toApiError(quotes.error.value).message"
        >
          <WButton variant="secondary" @click="quotes.refetch()">{{ t('common.retry') }}</WButton>
        </WEmptyState>
        <WTable
          v-else
          :columns="columns"
          :rows="rows as unknown as Record<string, unknown>[]"
          row-key="id"
          :caption="t('quotes.title')"
          :loading="quotes.isPending.value"
          :page-size="25"
          clickable-rows
          @row-click="open"
        >
          <template #empty>
            <WEmptyState
              :icon="FileText"
              :title="isTemplates ? t('quotes.noTemplates') : t('quotes.emptyTab')"
              :description="isTemplates ? t('quotes.noTemplatesText') : undefined"
            />
          </template>
          <template #cell-number="{ row: r }"
            ><span class="font-bold">{{ row(r).number || '—' }}</span></template
          >
          <template #cell-templateName="{ row: r }"
            ><span class="font-bold">{{ row(r).templateName }}</span></template
          >
          <template #cell-issueDate="{ row: r }">{{ formatDate(row(r).issueDate) }}</template>
          <template #cell-total="{ row: r }"><WMoney :amount="row(r).total" /></template>
          <template #cell-status="{ row: r }">
            <WBadge :tone="STATUS_TONES[row(r).status as QuoteStatus]">{{
              t(`quotes.statuses.${row(r).status}`)
            }}</WBadge>
          </template>
          <template #cell-action="{ row: r }">
            <span v-if="row(r).hasContract" class="text-[13px] font-semibold text-green">{{
              t('quotes.contractDone')
            }}</span>
            <WButton
              v-else-if="canEdit && actionLabel(row(r))"
              size="sm"
              :variant="row(r).status === 'accepted' ? 'primary' : 'secondary'"
              :loading="busy === row(r).id"
              @click.stop="act(row(r))"
              >{{ actionLabel(row(r)) }}</WButton
            >
            <span v-else class="text-muted">—</span>
          </template>
          <template #cell-updatedAt="{ row: r }">{{ formatDate(row(r).updatedAt) }}</template>
        </WTable>
      </WTabs>
    </section>

    <NewQuoteModal v-model:open="newOpen" />
  </div>
</template>

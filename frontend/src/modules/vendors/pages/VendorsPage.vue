<script setup lang="ts">
import { Briefcase, MessageCircle, Phone, Plus, Search } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { formatAmount } from '@/composables/useMoney'
import { usePermissions } from '@/composables/usePermissions'
import { whatsappHref } from '@/app/support'
import {
  type TableColumn,
  WBadge,
  WButton,
  WCard,
  WChips,
  WEmptyState,
  WInput,
  WTable,
} from '@/design'

import { useVendors } from '../api'
import VendorModal from '../components/VendorModal.vue'
import type { Vendor, VendorKind } from '../types'

/** « Partenaires et fournisseurs » (complement §13, feedback 13/11/2026): trusted address book, collaborations, amounts due. */
const { t } = useI18n()
const { can } = usePermissions()
const vendors = useVendors()
const seesMoney = computed(() => can('viewFinance'))

// Feedback 13/11/2026: suppliers and partners, one address book.
const kind = ref<'all' | VendorKind>('all')
const kindChips = computed(() => {
  const all = vendors.data.value ?? []
  const count = (k: VendorKind) => all.filter((v) => v.kind === k).length
  return [
    { value: 'all', label: `${t('vendors.all')} (${all.length})` },
    { value: 'supplier', label: `${t('vendors.kindsPlural.supplier')} (${count('supplier')})` },
    { value: 'partner', label: `${t('vendors.kindsPlural.partner')} (${count('partner')})` },
  ]
})
const category = ref<string>('all')
// A category of the other kind would leave an empty list.
watch(kind, () => (category.value = 'all'))
const chips = computed(() => {
  const ofKind = (vendors.data.value ?? []).filter(
    (v) => kind.value === 'all' || v.kind === kind.value,
  )
  const present = [...new Set(ofKind.map((v) => v.category))]
  return [
    { value: 'all', label: t('vendors.all') },
    ...present.map((value) => ({ value, label: t(`vendors.categories.${value}`) })),
  ]
})
const search = ref('')
const rows = computed(() => {
  const words = search.value.trim().toLowerCase()
  return (vendors.data.value ?? []).filter(
    (v) =>
      (kind.value === 'all' || v.kind === kind.value) &&
      (category.value === 'all' || v.category === category.value) &&
      (!words ||
        `${v.name} ${v.contactName} ${v.city} ${v.phone} ${v.categoryLabel} ${v.services}`
          .toLowerCase()
          .includes(words)),
  )
})
const columns = computed<TableColumn[]>(() => [
  { key: 'name', label: t('vendors.columns.vendor'), sortable: true },
  { key: 'services', label: t('vendors.columns.services') },
  { key: 'contact', label: t('vendors.columns.contact') },
  {
    key: 'collaborations',
    label: t('vendors.columns.collaborations'),
    sortable: true,
    align: 'right',
  },
  ...(seesMoney.value
    ? [{ key: 'due', label: t('vendors.columns.due'), sortable: true, align: 'right' as const }]
    : []),
  { key: 'call', label: t('vendors.columns.call') },
])
const row = (value: unknown) => value as Vendor
const initials = (name: string) =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w.charAt(0).toUpperCase())
    .join('')

const modalOpen = ref(false)
const edited = ref<Vendor | null>(null)
const addLabel = computed(() =>
  t(kind.value === 'partner' ? 'vendors.addPartner' : 'vendors.addSupplier'),
)
function openVendor(value: Vendor | null): void {
  if (value && !can('editWeddings')) return
  edited.value = value
  modalOpen.value = true
}
</script>

<template>
  <div class="flex flex-col gap-[22px]">
    <header class="flex flex-wrap items-end gap-x-6 gap-y-3">
      <div class="min-w-0 flex-1">
        <h1>{{ t('vendors.title') }}</h1>
        <p class="mt-1 max-w-[64ch] text-muted">{{ t('vendors.subtitle') }}</p>
      </div>
      <WButton v-if="can('editWeddings')" @click="openVendor(null)"
        ><Plus class="size-[18px]" aria-hidden="true" />{{ addLabel }}</WButton
      >
    </header>

    <WChips v-model="kind" :options="kindChips" :label="t('vendors.form.kind')" />
    <WInput
      v-model="search"
      class="max-w-[420px]"
      type="search"
      :label="t('vendors.search')"
      :placeholder="t('vendors.searchPlaceholder')"
      hide-label
    >
      <template #prefix><Search class="size-[18px] text-muted" aria-hidden="true" /></template>
    </WInput>
    <WChips
      v-if="chips.length > 1"
      v-model="category"
      :options="chips"
      :label="t('vendors.form.category')"
    />

    <WCard>
      <WEmptyState
        v-if="vendors.isError.value"
        :title="t('vendors.loadError')"
        :description="toApiError(vendors.error.value).message"
      >
        <WButton variant="secondary" @click="vendors.refetch()">{{ t('common.retry') }}</WButton>
      </WEmptyState>
      <WTable
        v-else
        :columns="columns"
        :rows="rows as unknown as Record<string, unknown>[]"
        row-key="id"
        :caption="t('vendors.title')"
        :loading="vendors.isPending.value"
        clickable-rows
        @row-click="(r) => openVendor(row(r))"
      >
        <template #empty>
          <WEmptyState
            :icon="Briefcase"
            :title="t('vendors.emptyTitle')"
            :description="t('vendors.emptyText')"
          />
        </template>
        <template #cell-name="{ row: r }">
          <span class="flex items-center gap-3">
            <span
              class="flex size-10 shrink-0 items-center justify-center rounded-[11px] bg-violet-soft font-display text-[13px] font-semibold text-violet"
              aria-hidden="true"
              >{{ initials(row(r).name) }}</span
            >
            <span class="min-w-0">
              <span class="block truncate font-bold">{{ row(r).name }}</span>
              <span class="mt-0.5 flex items-center gap-2 text-[12.5px] text-muted">
                <WBadge :tone="row(r).kind === 'partner' ? 'violet' : 'grey'">{{
                  row(r).kindLabel
                }}</WBadge>
                {{ row(r).categoryLabel }}
              </span>
            </span>
          </span>
        </template>
        <template #cell-contact="{ row: r }">
          <span class="block font-semibold whitespace-nowrap">{{ row(r).contactName || '—' }}</span>
          <span v-if="row(r).phone" class="num block text-[13px] whitespace-nowrap">{{
            row(r).phone
          }}</span>
          <span v-if="row(r).city" class="block text-[12.5px] text-muted">{{ row(r).city }}</span>
        </template>
        <template #cell-services="{ row: r }">
          <span
            class="line-clamp-2 max-w-[300px] min-w-[200px] text-[13px] text-ink-2"
            :title="row(r).services"
            >{{ row(r).services || '—' }}</span
          >
        </template>
        <template #cell-due="{ row: r }">{{
          row(r).due ? formatAmount(row(r).due!) : '—'
        }}</template>
        <template #cell-call="{ row: r }">
          <span class="inline-flex gap-1.5">
            <a
              v-if="row(r).whatsapp"
              :href="whatsappHref(row(r).whatsapp)"
              target="_blank"
              rel="noopener"
              class="inline-flex size-8 items-center justify-center rounded-[8px] border border-line-2 bg-surface hover:bg-surface-2"
              :aria-label="t('vendors.whatsapp', { name: row(r).name })"
              @click.stop
            >
              <MessageCircle class="size-[15px]" aria-hidden="true" />
            </a>
            <a
              v-if="row(r).phone"
              :href="`tel:${row(r).phone.replace(/\s/g, '')}`"
              class="inline-flex size-8 items-center justify-center rounded-[8px] border border-line-2 bg-surface hover:bg-surface-2"
              :aria-label="t('weddings.drawer.call', { name: row(r).name })"
              @click.stop
            >
              <Phone class="size-[15px]" aria-hidden="true" />
            </a>
          </span>
        </template>
      </WTable>
    </WCard>

    <VendorModal
      v-model:open="modalOpen"
      :vendor="edited"
      :default-kind="kind === 'partner' ? 'partner' : 'supplier'"
    />
  </div>
</template>

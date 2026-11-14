<script setup lang="ts">
import { useQueryClient } from '@tanstack/vue-query'
import { Handshake, Pencil, Phone, Plus, Search, Trash2, Upload } from '@lucide/vue'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { formatMoney } from '@/composables/useMoney'
import { usePermissions } from '@/composables/usePermissions'
import { useToast } from '@/composables/useToast'
import { WBadge, WButton, WCard, WEmptyState, WInput } from '@/design'
import { useSessionStore } from '@/stores/session'

import { stockApi, stockKeys, usePartnerSupplies } from '../api'
import type { PartnerSupply } from '../types'
import ImportListsModal from './ImportListsModal.vue'
import PartnerSupplyModal from './PartnerSupplyModal.vue'

/** « Matériel des partenaires » (feedback 14/11/2026): what each partner can lend us. */
const { t } = useI18n()
const toast = useToast()
const { can } = usePermissions()
const session = useSessionStore()
const queryClient = useQueryClient()
const isOwner = computed(() => session.role === 'owner')
const canEdit = computed(() => can('editStock'))

const search = ref('')
const debounced = ref('')
let timer: ReturnType<typeof setTimeout> | undefined
watch(search, (value) => {
  clearTimeout(timer)
  timer = setTimeout(() => (debounced.value = value.trim()), 250)
})
onBeforeUnmount(() => clearTimeout(timer))
const supplies = usePartnerSupplies(() => ({ search: debounced.value }))

const groups = computed(() => {
  const byVendor = new Map<
    string,
    { id: string; name: string; phone: string; rows: PartnerSupply[] }
  >()
  for (const supply of supplies.data.value ?? []) {
    const group = byVendor.get(supply.vendor) ?? {
      id: supply.vendor,
      name: supply.vendorName,
      phone: supply.vendorPhone,
      rows: [],
    }
    group.rows.push(supply)
    byVendor.set(supply.vendor, group)
  }
  return [...byVendor.values()]
})

const modalOpen = ref(false)
const editing = ref<PartnerSupply | null>(null)
const forVendor = ref<string | null>(null)
function openModal(supply: PartnerSupply | null, vendor: string | null = null): void {
  editing.value = supply
  forVendor.value = vendor
  modalOpen.value = true
}
const importOpen = ref(false)

async function remove(supply: PartnerSupply): Promise<void> {
  try {
    const { deleted } = await stockApi.deletePartnerSupply(supply.id)
    void queryClient.invalidateQueries({ queryKey: stockKeys.all })
    toast.success(deleted ? t('stock.partners.removed') : t('stock.partners.disabled'))
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-wrap items-end gap-3">
      <div class="min-w-0 flex-1">
        <h2 class="text-[17px] font-semibold">{{ t('stock.partners.title') }}</h2>
        <p class="text-[13.5px] text-muted">{{ t('stock.partners.subtitle') }}</p>
      </div>
      <div class="flex flex-wrap gap-2">
        <WButton v-if="isOwner" variant="secondary" @click="importOpen = true">
          <Upload class="size-[16px]" aria-hidden="true" />{{ t('stock.partners.import') }}
        </WButton>
        <WButton v-if="canEdit" @click="openModal(null)">
          <Plus class="size-[16px]" aria-hidden="true" />{{ t('stock.partners.add') }}
        </WButton>
      </div>
    </div>

    <WInput
      v-model="search"
      type="search"
      :label="t('stock.partners.search')"
      :placeholder="t('stock.partners.search')"
      hide-label
    >
      <template #prefix><Search class="size-[18px] text-muted" aria-hidden="true" /></template>
    </WInput>

    <div v-if="supplies.isPending.value" class="skeleton h-48 rounded-wd-lg" />
    <WEmptyState
      v-else-if="supplies.isError.value"
      :title="t('stock.loadError')"
      :description="toApiError(supplies.error.value).message"
    />
    <WEmptyState
      v-else-if="!groups.length"
      :icon="Handshake"
      :title="t('stock.partners.empty')"
      :description="debounced ? undefined : t('stock.partners.emptyText')"
    >
      <WButton v-if="isOwner && !debounced" variant="secondary" @click="importOpen = true">
        <Upload class="size-[16px]" aria-hidden="true" />{{ t('stock.partners.import') }}
      </WButton>
      <WButton v-if="canEdit && !debounced" @click="openModal(null)">
        <Plus class="size-[16px]" aria-hidden="true" />{{ t('stock.partners.add') }}
      </WButton>
    </WEmptyState>

    <WCard v-for="group in groups" v-else :key="group.id" :padded="false">
      <header class="flex flex-wrap items-center gap-3 border-b border-line px-4 py-3">
        <span
          class="flex size-9 shrink-0 items-center justify-center rounded-[10px] bg-violet-soft text-violet"
        >
          <Handshake class="size-[18px]" aria-hidden="true" />
        </span>
        <div class="min-w-0 flex-1">
          <p class="font-bold break-words">{{ group.name }}</p>
          <a
            v-if="group.phone"
            :href="`tel:${group.phone.replace(/\s/g, '')}`"
            class="inline-flex items-center gap-1 text-[12.5px] text-muted hover:underline"
            ><Phone class="size-3.5" aria-hidden="true" />{{ group.phone }}</a
          >
        </div>
        <WButton v-if="canEdit" size="sm" variant="ghost" @click="openModal(null, group.id)">
          <Plus class="size-[15px]" aria-hidden="true" />{{ t('stock.partners.add') }}
        </WButton>
      </header>
      <ul class="divide-y divide-line">
        <li
          v-for="supply in group.rows"
          :key="supply.id"
          class="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3"
          :class="!supply.isActive && 'opacity-60'"
        >
          <div class="min-w-0 flex-1 basis-[200px]">
            <p class="font-semibold break-words">{{ supply.itemName }}</p>
            <p class="text-[12.5px] text-muted">
              {{ supply.categoryName }} · {{ supply.itemReference }} ·
              {{ t('stock.partners.ours', { count: supply.ownQuantity }) }}
            </p>
          </div>
          <div class="text-right">
            <p class="num text-[17px] font-semibold">{{ supply.quantity }}</p>
            <p class="text-[12px] text-muted">{{ t('stock.partners.canLend') }}</p>
          </div>
          <div v-if="supply.unitCost !== null" class="text-right">
            <p class="num font-semibold">{{ formatMoney(supply.unitCost) }}</p>
            <p class="text-[12px] text-muted">{{ t('stock.partners.cost') }}</p>
          </div>
          <WBadge v-if="!supply.isActive" tone="grey">{{ t('stock.partners.inactive') }}</WBadge>
          <div v-if="canEdit" class="flex gap-1">
            <WButton
              size="sm"
              variant="ghost"
              icon
              :aria-label="t('stock.partners.edit')"
              :title="t('stock.partners.edit')"
              @click="openModal(supply)"
              ><Pencil class="size-[15px]" aria-hidden="true"
            /></WButton>
            <WButton
              size="sm"
              variant="ghost"
              icon
              class="text-red"
              :aria-label="t('stock.partners.remove')"
              :title="t('stock.partners.remove')"
              @click="remove(supply)"
              ><Trash2 class="size-[15px]" aria-hidden="true"
            /></WButton>
          </div>
        </li>
      </ul>
    </WCard>

    <PartnerSupplyModal v-model:open="modalOpen" :supply="editing" :vendor-id="forVendor" />
    <ImportListsModal v-model:open="importOpen" />
  </div>
</template>

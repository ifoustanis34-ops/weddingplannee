<script setup lang="ts">
import { ClipboardCheck, Plus } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { formatDate } from '@/composables/useDate'
import { usePermissions } from '@/composables/usePermissions'
import { useToast } from '@/composables/useToast'
import { WBadge, WButton, WCard, WEmptyState, WModal, WSelect } from '@/design'

import { stockApi, useInventories, useItemCategories, useStockMutation } from '../api'
import type { Inventory } from '../types'

/** Physical count (§5.3): expected vs counted, differences become adjustments on validation. */
const { t } = useI18n()
const toast = useToast()
const { can } = usePermissions()
const inventories = useInventories()
const categories = useItemCategories()

const startOpen = ref(false)
const startCategory = ref('')
const selectedId = ref<string | null>(null)
const selected = computed<Inventory | null>(
  () =>
    inventories.data.value?.find((i) => i.id === selectedId.value) ??
    inventories.data.value?.find((i) => i.status === 'draft') ??
    null,
)
const counts = ref<Record<string, number | null>>({})
watch(
  selected,
  (inventory) => {
    counts.value = Object.fromEntries((inventory?.lines ?? []).map((l) => [l.id, l.counted]))
  },
  { immediate: true },
)
const difference = (lineId: string, expected: number) => {
  const counted = counts.value[lineId]
  return typeof counted === 'number' && !isNaN(counted) ? counted - expected : null
}
const draft = computed(() => selected.value?.status === 'draft' && can('editStock'))

const start = useStockMutation((category: string | null) => stockApi.startInventory(category))
const save = useStockMutation(
  ({ id, values }: { id: string; values: Record<string, number | null> }) =>
    stockApi.count(id, values),
)
const validate = useStockMutation((id: string) => stockApi.validateInventory(id))
const validateOpen = ref(false)

async function begin(): Promise<void> {
  try {
    const inventory = await start.mutateAsync(startCategory.value || null)
    selectedId.value = inventory.id
    startOpen.value = false
    toast.success(t('stock.inventory.started'))
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
function cleaned(): Record<string, number | null> {
  return Object.fromEntries(
    Object.entries(counts.value).map(([k, v]) => [
      k,
      typeof v === 'number' && !isNaN(v) ? v : null,
    ]),
  )
}
async function saveCounts(): Promise<void> {
  if (!selected.value) return
  try {
    await save.mutateAsync({ id: selected.value.id, values: cleaned() })
    toast.success(t('stock.inventory.countsSaved'))
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
async function confirmValidate(): Promise<void> {
  if (!selected.value) return
  try {
    await save.mutateAsync({ id: selected.value.id, values: cleaned() })
    const done = await validate.mutateAsync(selected.value.id)
    validateOpen.value = false
    const adjusted = done.lines.filter((l) => l.difference).length
    toast.success(t('stock.inventory.validatedDone', { count: adjusted }))
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
const categoryOptions = computed(() => [
  { value: '', label: t('stock.inventory.allCategories') },
  ...(categories.data.value ?? []).map((c) => ({ value: c.id, label: c.name })),
])
</script>

<template>
  <div class="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
    <WCard :padded="false">
      <div class="flex items-center justify-between gap-2 px-4 pt-4">
        <h2 class="text-[15.5px] font-semibold">{{ t('stock.tabs.inventory') }}</h2>
        <WButton v-if="can('editStock')" size="sm" @click="startOpen = true">
          <Plus class="size-[15px]" aria-hidden="true" />{{ t('stock.inventory.start') }}
        </WButton>
      </div>
      <div v-if="inventories.isPending.value" class="p-4"><div class="skeleton h-24" /></div>
      <p v-else-if="!inventories.data.value?.length" class="p-4 text-[13px] text-muted">
        {{ t('stock.inventory.empty') }}
      </p>
      <ul v-else class="mt-2 flex flex-col pb-2">
        <li v-for="inventory in inventories.data.value" :key="inventory.id">
          <button
            type="button"
            class="flex w-full items-center gap-2 px-4 py-2.5 text-left hover:bg-surface-2"
            :class="selected?.id === inventory.id && 'bg-surface-2'"
            @click="selectedId = inventory.id"
          >
            <span class="min-w-0 flex-1">
              <span class="block font-bold">{{ formatDate(inventory.date) }}</span>
              <span class="block truncate text-[12px] text-muted">
                {{ inventory.categoryName ?? t('stock.inventory.allCategories') }} ·
                {{ t('stock.inventory.lines', { count: inventory.lines.length }) }}
              </span>
            </span>
            <WBadge :tone="inventory.status === 'draft' ? 'gold' : 'green'">{{
              t(`stock.inventory.${inventory.status}`)
            }}</WBadge>
          </button>
        </li>
      </ul>
    </WCard>

    <WCard v-if="selected" :padded="false">
      <div class="flex flex-wrap items-center gap-3 px-5 pt-5">
        <div class="min-w-0 flex-1">
          <h2 class="text-[17px] font-semibold">
            {{ formatDate(selected.date) }} ·
            {{ selected.categoryName ?? t('stock.inventory.allCategories') }}
          </h2>
          <p class="text-[12.5px] text-muted">
            {{ t('stock.inventory.unitsNote') }}
            <template v-if="selected.authorName">
              · {{ t('stock.inventory.by', { name: selected.authorName }) }}</template
            >
          </p>
        </div>
        <template v-if="draft">
          <WButton variant="secondary" :loading="save.isPending.value" @click="saveCounts">{{
            t('stock.inventory.saveCounts')
          }}</WButton>
          <WButton @click="validateOpen = true">
            <ClipboardCheck class="size-[18px]" aria-hidden="true" />{{
              t('stock.inventory.validate')
            }}
          </WButton>
        </template>
      </div>
      <div class="mt-4 overflow-x-auto">
        <table class="w-full min-w-[560px] border-collapse text-[13.5px]">
          <thead>
            <tr class="text-left text-[12.5px] font-bold text-muted">
              <th scope="col" class="border-b border-line px-5 py-2">
                {{ t('stock.columns.item') }}
              </th>
              <th scope="col" class="border-b border-line px-3 py-2 text-right">
                {{ t('stock.inventory.expected') }}
              </th>
              <th scope="col" class="border-b border-line px-3 py-2 text-right">
                {{ t('stock.inventory.counted') }}
              </th>
              <th scope="col" class="border-b border-line px-5 py-2 text-right">
                {{ t('stock.inventory.difference') }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="line in selected.lines" :key="line.id">
              <td class="border-b border-line px-5 py-2">
                <span class="block font-bold">{{ line.itemName }}</span>
                <span class="text-[12px] text-muted"
                  >{{ line.itemReference }} · {{ line.categoryName }}</span
                >
              </td>
              <td class="num border-b border-line px-3 py-2 text-right">{{ line.expected }}</td>
              <td class="border-b border-line px-3 py-2 text-right">
                <input
                  v-if="draft"
                  v-model.number="counts[line.id]"
                  type="number"
                  min="0"
                  inputmode="numeric"
                  class="num h-9 w-24 rounded-[8px] border border-line-2 bg-surface px-2 text-right"
                  :aria-label="`${t('stock.inventory.counted')} : ${line.itemName}`"
                />
                <span v-else class="num">{{ line.counted ?? '—' }}</span>
              </td>
              <td
                class="num border-b border-line px-5 py-2 text-right font-bold"
                :class="
                  (difference(line.id, line.expected) ?? 0) < 0
                    ? 'text-coral'
                    : (difference(line.id, line.expected) ?? 0) > 0
                      ? 'text-green'
                      : 'text-muted'
                "
              >
                {{
                  difference(line.id, line.expected) === null
                    ? '—'
                    : difference(line.id, line.expected)! > 0
                      ? `+${difference(line.id, line.expected)}`
                      : String(difference(line.id, line.expected)).replace('-', '−')
                }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </WCard>
    <WEmptyState v-else :icon="ClipboardCheck" :title="t('stock.inventory.empty')" />

    <WModal v-model:open="startOpen" :title="t('stock.inventory.startTitle')" size="sm">
      <WSelect
        v-model="startCategory"
        :label="t('stock.inventory.category')"
        :options="categoryOptions"
      />
      <template #footer>
        <WButton variant="secondary" @click="startOpen = false">{{ t('common.cancel') }}</WButton>
        <WButton :loading="start.isPending.value" @click="begin">{{
          t('stock.inventory.startSave')
        }}</WButton>
      </template>
    </WModal>
    <WModal v-model:open="validateOpen" :title="t('stock.inventory.validate')" size="sm">
      <p>{{ t('stock.inventory.validateConfirm') }}</p>
      <template #footer>
        <WButton variant="secondary" @click="validateOpen = false">{{
          t('common.cancel')
        }}</WButton>
        <WButton :loading="validate.isPending.value" @click="confirmValidate">{{
          t('stock.inventory.validate')
        }}</WButton>
      </template>
    </WModal>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeftRight, ImageUp, Package, Pencil, QrCode, Trash2, Wrench } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { api } from '@/api/client'
import { toApiError } from '@/api/errors'
import { formatDate, formatDateTime } from '@/composables/useDate'
import { formatMoney } from '@/composables/useMoney'
import { usePermissions } from '@/composables/usePermissions'
import { useToast } from '@/composables/useToast'
import { WBadge, WButton, WDrawer, WEmptyState, WInput, WModal, WSelect } from '@/design'
import RingChart from '@/modules/dashboard/components/RingChart.vue'

import { stockApi, useItem, useItemActivity, useStockMutation } from '../api'
import type { ItemUnit, Maintenance, UnitCondition, UnitStatus } from '../types'
import ItemFormModal from './ItemFormModal.vue'
import MaintenanceModal from './MaintenanceModal.vue'
import MovementModal from './MovementModal.vue'

/**
 * Item sheet (reservations-stock.md §5.5): photo, stock by status (ring), 30-day occupancy,
 * units, maintenance, last movements. Upcoming reservations and profitability join with S4/S6.
 */
const props = defineProps<{ itemId: string | null }>()
const emit = defineEmits<{ close: [] }>()
const { t } = useI18n()
const toast = useToast()
const { can } = usePermissions()

const open = computed({
  get: () => props.itemId !== null,
  set: (value) => {
    if (!value) emit('close')
  },
})
const id = computed(() => props.itemId)
const item = useItem(id)
const activity = useItemActivity(id)
const canEdit = computed(() => can('editStock'))

const editOpen = ref(false)
const movementOpen = ref(false)
const maintenanceOpen = ref(false)
const closing = ref<Maintenance | null>(null)
const labelsOpen = ref(false)
const labelCount = ref(1)

const ring = computed(() => {
  const today = item.data.value?.today
  if (!today) return []
  return [
    { key: 'available', value: today.available, color: 'var(--chart-4)' },
    { key: 'reserved', value: today.reserved, color: 'var(--chart-income)' },
    { key: 'out', value: today.out, color: 'var(--chart-expense)' },
    {
      key: 'maintenance',
      value: today.maintenance + today.outOfService,
      color: 'var(--chart-other)',
    },
  ].map((part) => ({
    ...part,
    label: t(`stock.parts.${part.key}`),
    display: String(part.value),
  }))
})

// --- Photo --------------------------------------------------------------------------------------
const photoInput = ref<HTMLInputElement | null>(null)
// A photo the server no longer has shows the placeholder, not a broken image (feedback 15/11/2026).
const photoFailed = ref(false)
watch(
  () => item.data.value?.photoUrl,
  () => (photoFailed.value = false),
)
const uploadPhoto = useStockMutation((file: File) => stockApi.uploadPhoto(props.itemId!, file))
const removePhoto = useStockMutation(() => stockApi.removePhoto(props.itemId!))
async function onPhoto(event: Event): Promise<void> {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  try {
    await uploadPhoto.mutateAsync(file)
    toast.success(t('stock.drawer.photoSaved'))
  } catch (error) {
    toast.error(toApiError(error).message)
  } finally {
    if (photoInput.value) photoInput.value.value = ''
  }
}

// --- Units --------------------------------------------------------------------------------------
const updateUnit = useStockMutation(
  ({ unit, input }: { unit: ItemUnit; input: Partial<ItemUnit> }) =>
    stockApi.updateUnit(unit.id, input),
)
const EDITABLE_STATUS: UnitStatus[] = ['available', 'out_of_service']
const statusOptions = computed(() =>
  EDITABLE_STATUS.map((value) => ({ value, label: t(`stock.unitStatus.${value}`) })),
)
const conditionOptions = computed(() =>
  (['good', 'worn', 'damaged'] as UnitCondition[]).map((value) => ({
    value,
    label: t(`stock.unitCondition.${value}`),
  })),
)
async function changeUnit(unit: ItemUnit, input: Partial<ItemUnit>): Promise<void> {
  try {
    await updateUnit.mutateAsync({ unit, input })
    toast.success(t('stock.drawer.unitSaved'))
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
const unitTone = (status: UnitStatus) =>
  status === 'available' ? 'green' : status === 'maintenance' ? 'gold' : 'grey'

function closeMaintenance(maintenance: Maintenance): void {
  closing.value = maintenance
  maintenanceOpen.value = true
}
function startMaintenance(): void {
  closing.value = null
  maintenanceOpen.value = true
}

// --- Labels: the PDF is fetched with the session (and the organization header), then opened.
const printing = ref(false)
async function printLabels(): Promise<void> {
  if (!props.itemId) return
  printing.value = true
  try {
    const response = await api.get<Blob>(`/items/${props.itemId}/labels`, {
      params: { count: labelCount.value },
      responseType: 'blob',
    })
    const url = URL.createObjectURL(response.data)
    window.open(url, '_blank', 'noopener')
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
    labelsOpen.value = false
  } catch (error) {
    toast.error(toApiError(error).message)
  } finally {
    printing.value = false
  }
}

const occupancyMax = computed(() =>
  Math.max(1, ...(activity.data.value?.occupancy ?? []).map((d) => d.total)),
)
</script>

<template>
  <WDrawer
    v-model:open="open"
    :title="item.data.value?.name ?? t('common.loading')"
    :subtitle="
      item.data.value ? t('stock.drawer.reference', { reference: item.data.value.reference }) : ''
    "
  >
    <div v-if="item.isPending.value" class="flex flex-col gap-3" :aria-label="t('common.loading')">
      <div v-for="n in 4" :key="n" class="skeleton h-12" />
    </div>
    <WEmptyState
      v-else-if="item.isError.value || !item.data.value"
      :title="t('stock.drawer.notFound')"
    />

    <template v-else>
      <p v-if="!canEdit" class="rounded-wd bg-surface-2 px-3 py-2 text-[13px] text-ink-2">
        {{ t('stock.drawer.readOnly') }}
      </p>

      <!-- Photo -->
      <section class="relative overflow-hidden rounded-wd-lg bg-surface-2">
        <img
          v-if="item.data.value.photoUrl && !photoFailed"
          :src="item.data.value.photoUrl"
          :alt="item.data.value.name"
          class="aspect-[16/9] w-full object-cover"
          @error="photoFailed = true"
        />
        <div v-else class="flex aspect-[16/9] items-center justify-center text-muted">
          <Package class="size-12" aria-hidden="true" />
        </div>
        <div v-if="canEdit" class="absolute right-2 bottom-2 flex gap-2">
          <input
            ref="photoInput"
            type="file"
            accept="image/*"
            class="sr-only"
            :aria-label="t('stock.drawer.addPhoto')"
            @change="onPhoto"
          />
          <WButton
            size="sm"
            variant="secondary"
            :loading="uploadPhoto.isPending.value"
            @click="photoInput?.click()"
          >
            <ImageUp class="size-[15px]" aria-hidden="true" />{{
              item.data.value.photoUrl ? t('stock.drawer.changePhoto') : t('stock.drawer.addPhoto')
            }}
          </WButton>
          <WButton
            v-if="item.data.value.photoUrl"
            size="sm"
            variant="secondary"
            icon
            :aria-label="t('stock.drawer.removePhoto')"
            @click="removePhoto.mutate()"
          >
            <Trash2 class="size-[15px]" aria-hidden="true" />
          </WButton>
        </div>
      </section>

      <!-- Stock today -->
      <section>
        <h3>{{ t('stock.drawer.stockToday') }}</h3>
        <div class="mt-3 flex items-center gap-5">
          <RingChart
            :items="ring"
            :center-value="String(item.data.value.today?.available ?? 0)"
            :center-label="t('stock.parts.available')"
            :label="ring.map((r) => `${r.label} ${r.value}`).join(', ')"
            :size="120"
          />
          <dl class="grid flex-1 grid-cols-2 gap-x-3 gap-y-2 text-[13px]">
            <div v-for="part in ring" :key="part.key">
              <dt class="flex items-center gap-1.5 font-semibold text-muted">
                <span class="size-2.5 rounded-[3px]" :style="{ background: part.color }" />{{
                  part.label
                }}
              </dt>
              <dd class="num font-display text-[17px] font-semibold">{{ part.value }}</dd>
            </div>
          </dl>
        </div>
        <p class="mt-2 text-[12.5px] text-muted">
          {{ item.data.value.categoryName }} ·
          {{ t('stock.drawer.delay', { days: item.data.value.delayDays }) }}
          <template v-if="item.data.value.location"> · {{ item.data.value.location }}</template>
        </p>
      </section>

      <!-- Occupancy of the next 30 days -->
      <section v-if="activity.data.value">
        <h3>{{ t('stock.drawer.occupancy') }}</h3>
        <p class="text-[12.5px] text-muted">{{ t('stock.drawer.occupancyHint') }}</p>
        <div
          class="mt-2 flex h-14 items-end gap-[2px]"
          role="img"
          :aria-label="t('stock.drawer.occupancy')"
        >
          <span
            v-for="day in activity.data.value.occupancy"
            :key="day.date"
            class="flex-1 rounded-t-[3px] bg-chart-4"
            :style="{ height: `${Math.max(8, (day.available / occupancyMax) * 100)}%` }"
            :title="`${formatDate(day.date)} : ${day.available} / ${day.total}`"
          />
        </div>
      </section>

      <!-- Prices and value (by role) -->
      <section v-if="item.data.value.rentPrice !== null || item.data.value.purchaseCost !== null">
        <h3>{{ t('stock.drawer.prices') }}</h3>
        <dl class="mt-2 grid grid-cols-2 gap-x-4 gap-y-2.5 text-[13.5px]">
          <div v-if="item.data.value.rentPrice !== null">
            <dt class="text-[12.5px] font-semibold text-muted">{{ t('stock.columns.rent') }}</dt>
            <dd class="num font-semibold">
              {{ formatMoney(item.data.value.rentPrice) }}
              {{ t(`stock.perUnit.${item.data.value.rentUnit}`) }}
            </dd>
          </div>
          <div v-if="item.data.value.salePrice !== null">
            <dt class="text-[12.5px] font-semibold text-muted">
              {{ t('stock.fields.salePrice') }}
            </dt>
            <dd class="num font-semibold">{{ formatMoney(item.data.value.salePrice) }}</dd>
          </div>
          <div v-if="item.data.value.deposit !== null">
            <dt class="text-[12.5px] font-semibold text-muted">{{ t('stock.fields.deposit') }}</dt>
            <dd class="num font-semibold">{{ formatMoney(item.data.value.deposit) }}</dd>
          </div>
          <div v-if="item.data.value.stockValue !== null">
            <dt class="text-[12.5px] font-semibold text-muted">{{ t('stock.drawer.value') }}</dt>
            <dd class="num font-semibold">{{ formatMoney(item.data.value.stockValue) }}</dd>
          </div>
        </dl>
      </section>

      <!-- Open maintenance -->
      <section v-if="activity.data.value?.maintenances.length">
        <h3>{{ t('stock.drawer.maintenances') }}</h3>
        <ul class="mt-2 flex flex-col gap-2">
          <li
            v-for="maintenance in activity.data.value.maintenances"
            :key="maintenance.id"
            class="flex items-center gap-3 rounded-wd border border-line px-3 py-2.5"
          >
            <Wrench class="size-[18px] shrink-0 text-muted" aria-hidden="true" />
            <div class="min-w-0 flex-1">
              <p class="truncate font-bold">
                {{ maintenance.reason
                }}<template v-if="maintenance.serialNumber">
                  · {{ maintenance.serialNumber }}</template
                >
              </p>
              <p
                class="text-[12.5px]"
                :class="maintenance.isLate ? 'font-semibold text-coral' : 'text-muted'"
              >
                {{ t('stock.drawer.since', { date: formatDate(maintenance.startedAt) }) }}
                <template v-if="maintenance.expectedEnd">
                  · {{ t('stock.drawer.expected', { date: formatDate(maintenance.expectedEnd) }) }}
                </template>
                <template v-if="maintenance.isLate"> · {{ t('stock.drawer.late') }}</template>
              </p>
            </div>
            <WButton
              v-if="canEdit"
              size="sm"
              variant="secondary"
              @click="closeMaintenance(maintenance)"
              >{{ t('stock.drawer.close') }}</WButton
            >
          </li>
        </ul>
      </section>

      <!-- Units -->
      <section v-if="item.data.value.tracking === 'unit' && activity.data.value">
        <h3>{{ t('stock.drawer.units') }}</h3>
        <ul class="mt-2 divide-y divide-line rounded-wd border border-line">
          <li
            v-for="unit in activity.data.value.units"
            :key="unit.id"
            class="flex flex-wrap items-center gap-2 px-3 py-2.5"
          >
            <span class="num min-w-0 flex-1 font-bold">{{ unit.serialNumber }}</span>
            <template v-if="canEdit && EDITABLE_STATUS.includes(unit.status)">
              <WSelect
                :model-value="unit.status"
                class="w-[150px]"
                :label="t('stock.drawer.units')"
                :options="statusOptions"
                hide-label
                @update:model-value="(v) => changeUnit(unit, { status: v as UnitStatus })"
              />
              <WSelect
                :model-value="unit.condition"
                class="w-[120px]"
                :label="t('stock.unitCondition.good')"
                :options="conditionOptions"
                hide-label
                @update:model-value="(v) => changeUnit(unit, { condition: v as UnitCondition })"
              />
            </template>
            <template v-else>
              <WBadge :tone="unitTone(unit.status)">{{
                t(`stock.unitStatus.${unit.status}`)
              }}</WBadge>
              <WBadge tone="grey" :dot="false">{{
                t(`stock.unitCondition.${unit.condition}`)
              }}</WBadge>
            </template>
          </li>
        </ul>
      </section>

      <!-- Last movements -->
      <section v-if="activity.data.value">
        <h3>{{ t('stock.drawer.movements') }}</h3>
        <p v-if="!activity.data.value.movements.length" class="mt-1 text-muted">
          {{ t('stock.drawer.noMovement') }}
        </p>
        <ul v-else class="mt-2 flex flex-col gap-2">
          <li
            v-for="movement in activity.data.value.movements"
            :key="movement.id"
            class="flex items-baseline gap-3 text-[13px]"
            :class="movement.cancelledAt && 'text-muted line-through'"
          >
            <span
              class="num w-12 shrink-0 text-right font-bold"
              :class="
                movement.delta > 0 ? 'text-green' : movement.delta < 0 ? 'text-coral' : 'text-muted'
              "
              >{{ movement.delta > 0 ? '+' : movement.delta < 0 ? '−' : ''
              }}{{ movement.quantity }}</span
            >
            <span class="min-w-0 flex-1">
              <span class="font-semibold">{{ t(`stock.movement.kinds.${movement.kind}`) }}</span>
              <template v-if="movement.reason"> · {{ movement.reason }}</template>
            </span>
            <span class="shrink-0 text-[12px] text-muted">{{
              formatDateTime(movement.occurredAt)
            }}</span>
          </li>
        </ul>
      </section>
    </template>

    <template v-if="item.data.value" #footer>
      <WButton variant="secondary" @click="labelsOpen = true">
        <QrCode class="size-[18px]" aria-hidden="true" />{{ t('stock.drawer.labels') }}
      </WButton>
      <div v-if="canEdit" class="ml-auto flex flex-wrap gap-2">
        <WButton
          variant="secondary"
          icon
          :aria-label="t('stock.drawer.edit')"
          @click="editOpen = true"
        >
          <Pencil class="size-[18px]" aria-hidden="true" />
        </WButton>
        <WButton variant="secondary" @click="startMaintenance">
          <Wrench class="size-[18px]" aria-hidden="true" />{{ t('stock.drawer.maintenance') }}
        </WButton>
        <WButton @click="movementOpen = true">
          <ArrowLeftRight class="size-[18px]" aria-hidden="true" />{{ t('stock.drawer.movement') }}
        </WButton>
      </div>
    </template>
  </WDrawer>

  <template v-if="item.data.value">
    <ItemFormModal v-model:open="editOpen" :item="item.data.value" />
    <MovementModal v-model:open="movementOpen" :item-id="item.data.value.id" />
    <MaintenanceModal
      v-model:open="maintenanceOpen"
      :item="item.data.value"
      :units="activity.data.value?.units ?? []"
      :closing="closing"
    />
    <WModal v-model:open="labelsOpen" :title="t('stock.drawer.labels')" size="sm">
      <WInput
        v-if="item.data.value.tracking === 'quantity'"
        v-model.number="labelCount"
        :label="t('stock.drawer.labelsCount')"
        type="number"
        min="1"
        max="240"
      />
      <template #footer>
        <WButton variant="secondary" @click="labelsOpen = false">{{ t('common.cancel') }}</WButton>
        <WButton :loading="printing" @click="printLabels">
          <QrCode class="size-[18px]" aria-hidden="true" />{{ t('stock.drawer.labels') }}
        </WButton>
      </template>
    </WModal>
  </template>
</template>

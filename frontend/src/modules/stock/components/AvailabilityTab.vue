<script setup lang="ts">
import { ChevronLeft, ChevronRight } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { formatDate } from '@/composables/useDate'
import { WButton, WChips } from '@/design'

import { useGrid, useItemCategories } from '../api'

/**
 * « Disponibilité » (§5.2): articles × 30 days, each cell colored by its occupancy rate
 * (one hue, light → dark: sequential), the number of free pieces written inside.
 */
const emit = defineEmits<{ open: [itemId: string] }>()
const { t } = useI18n()
const DAYS = 30
const offset = ref(0)
const category = ref('all')
const categories = useItemCategories()
const start = computed(() => {
  const day = new Date()
  day.setDate(day.getDate() + offset.value)
  return day.toISOString().slice(0, 10)
})
const grid = useGrid(() => ({
  from: start.value,
  days: DAYS,
  category: category.value === 'all' ? '' : category.value,
}))
const chips = computed(() => [
  { value: 'all', label: t('stock.allCategories') },
  ...(categories.data.value ?? []).map((c) => ({ value: c.id, label: c.name })),
])
// Sequential: one hue, light (free) to dark (full).
function shade(rate: number): string {
  if (rate <= 0) return 'var(--surface-2)'
  if (rate < 34) return 'color-mix(in srgb, var(--violet) 18%, var(--surface))'
  if (rate < 67) return 'color-mix(in srgb, var(--violet) 42%, var(--surface))'
  if (rate < 100) return 'color-mix(in srgb, var(--violet) 70%, var(--surface))'
  return 'var(--violet)'
}
const dayLabel = (iso: string) =>
  new Intl.DateTimeFormat('fr-FR', { day: 'numeric', timeZone: 'UTC' }).format(
    new Date(`${iso}T12:00:00Z`),
  )
const weekday = (iso: string) =>
  new Intl.DateTimeFormat('fr-FR', { weekday: 'narrow', timeZone: 'UTC' }).format(
    new Date(`${iso}T12:00:00Z`),
  )
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-wrap items-center gap-3">
      <WChips v-model="category" :options="chips" :label="t('stock.fields.category')" />
      <div class="ml-auto flex items-center gap-1">
        <WButton
          variant="secondary"
          icon
          :aria-label="t('stock.grid.previous')"
          @click="offset -= DAYS"
        >
          <ChevronLeft class="size-[18px]" aria-hidden="true" />
        </WButton>
        <WButton variant="secondary" size="sm" @click="offset = 0">{{
          t('stock.grid.today')
        }}</WButton>
        <WButton
          variant="secondary"
          icon
          :aria-label="t('stock.grid.next')"
          @click="offset += DAYS"
        >
          <ChevronRight class="size-[18px]" aria-hidden="true" />
        </WButton>
      </div>
    </div>
    <div v-if="grid.isPending.value" class="skeleton h-80 rounded-wd-lg" />
    <div
      v-else-if="grid.data.value"
      class="overflow-x-auto rounded-wd-lg border border-line bg-surface"
      :class="grid.isPlaceholderData.value && 'opacity-60'"
    >
      <table class="border-collapse text-[12px]">
        <caption class="sr-only">
          {{
            t('stock.grid.caption')
          }}
        </caption>
        <thead>
          <tr>
            <th
              scope="col"
              class="sticky left-0 z-10 min-w-[220px] bg-surface px-3 py-2 text-left font-bold text-muted"
            >
              {{ t('stock.columns.item') }}
            </th>
            <th
              v-for="day in grid.data.value.days"
              :key="day"
              scope="col"
              class="min-w-[30px] px-0.5 py-2 text-center font-semibold text-muted"
            >
              <span class="block text-[10.5px] uppercase">{{ weekday(day) }}</span>
              <span class="block font-bold text-ink-2">{{ dayLabel(day) }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in grid.data.value.rows" :key="row.item" class="border-t border-line">
            <th scope="row" class="sticky left-0 z-10 bg-surface px-3 py-1.5 text-left font-normal">
              <button
                type="button"
                class="block max-w-[220px] truncate text-left font-bold hover:text-violet"
                @click="emit('open', row.item)"
              >
                {{ row.name }}
              </button>
              <span class="text-[11.5px] text-muted">{{ row.reference }} · {{ row.total }}</span>
            </th>
            <td
              v-for="(cell, index) in row.cells"
              :key="index"
              class="border-l border-surface p-[2px]"
            >
              <span
                class="num flex h-7 items-center justify-center rounded-[5px] text-[11px] font-bold"
                :class="cell.rate >= 67 ? 'text-white' : 'text-ink-2'"
                :style="{ background: shade(cell.rate) }"
                :title="
                  t('stock.grid.cell', {
                    name: row.name,
                    date: formatDate(grid.data.value.days[index]!),
                    available: cell.available,
                    total: row.total,
                  })
                "
                >{{ cell.rate > 0 ? cell.available : '' }}</span
              >
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <ul class="flex flex-wrap items-center gap-x-4 gap-y-1 text-[12.5px] font-semibold text-ink-2">
      <li class="text-muted">{{ t('stock.grid.legend') }} :</li>
      <li
        v-for="[rate, key] in [
          [0, 'free'],
          [50, 'partial'],
          [100, 'full'],
        ] as const"
        :key="key"
        class="flex items-center gap-1.5"
      >
        <span
          class="size-3 rounded-[3px] border border-line"
          :style="{ background: shade(rate) }"
        />
        {{ t(`stock.grid.${key}`) }}
      </li>
    </ul>
  </div>
</template>

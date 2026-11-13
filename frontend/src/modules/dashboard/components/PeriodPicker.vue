<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { WButton, WInput } from '@/design'

import type { PeriodKey, PeriodRequest } from '../api'

/** Period segments (reservations-stock.md §8): one control above everything it scopes. */
const model = defineModel<PeriodRequest>({ required: true })
const { t } = useI18n()
const KEYS: PeriodKey[] = ['today', 'week', 'month', 'quarter', 'year', 'custom']

const from = ref(model.value.from ?? '')
const to = ref(model.value.to ?? '')
const editing = ref(model.value.period === 'custom' && !model.value.from)
watch(
  () => model.value,
  (value) => {
    from.value = value.from ?? from.value
    to.value = value.to ?? to.value
  },
)

function choose(key: PeriodKey): void {
  if (key === 'custom') {
    editing.value = true
    return
  }
  editing.value = false
  model.value = { period: key }
}

function apply(): void {
  if (!from.value || !to.value) return
  model.value = { period: 'custom', from: from.value, to: to.value }
  editing.value = false
}

const isActive = (key: PeriodKey) =>
  key === 'custom' ? editing.value || model.value.period === 'custom' : model.value.period === key
</script>

<template>
  <div class="flex flex-wrap items-end gap-2.5">
    <div
      role="radiogroup"
      :aria-label="t('dashboard.periods.label')"
      class="-mx-1 flex max-w-full overflow-x-auto px-1 [scrollbar-width:none]"
    >
      <div class="flex rounded-[12px] border border-line bg-surface p-1">
        <button
          v-for="key in KEYS"
          :key="key"
          type="button"
          role="radio"
          :aria-checked="isActive(key)"
          class="h-8 shrink-0 rounded-[9px] px-3 text-[13px] font-bold whitespace-nowrap transition-colors"
          :class="isActive(key) ? 'bg-hero text-hero-ink' : 'text-ink-2 hover:bg-surface-2'"
          @click="choose(key)"
        >
          {{ t(`dashboard.periods.${key}`) }}
        </button>
      </div>
    </div>
    <form v-if="editing" class="flex flex-wrap items-end gap-2" @submit.prevent="apply">
      <WInput v-model="from" type="date" :label="t('dashboard.periods.from')" class="w-[160px]" />
      <WInput v-model="to" type="date" :label="t('dashboard.periods.to')" class="w-[160px]" />
      <WButton type="submit" variant="secondary" :disabled="!from || !to">{{
        t('dashboard.periods.apply')
      }}</WButton>
    </form>
  </div>
</template>

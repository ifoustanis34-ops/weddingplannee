<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

/**
 * « disponible / réservé / loué / maintenance » (reservations-stock.md §5.5): one stacked bar,
 * 2px surface gaps between the parts, colors from the chart tokens (maintenance in grey, §4.3).
 */
const props = withDefaults(
  defineProps<{
    available: number
    reserved: number
    out: number
    maintenance: number
    label?: string
    height?: number
  }>(),
  { label: undefined, height: 8 },
)
const { t } = useI18n()

export type StockPart = 'available' | 'reserved' | 'out' | 'maintenance'
const COLORS: Record<StockPart, string> = {
  available: 'var(--chart-4)',
  reserved: 'var(--chart-income)',
  out: 'var(--chart-expense)',
  maintenance: 'var(--chart-other)',
}
const parts = computed(() => {
  const values: Record<StockPart, number> = {
    available: props.available,
    reserved: props.reserved,
    out: props.out,
    maintenance: props.maintenance,
  }
  const total = Object.values(values).reduce((sum, v) => sum + v, 0)
  return (Object.keys(values) as StockPart[])
    .filter((key) => values[key] > 0)
    .map((key) => ({ key, value: values[key], share: total ? values[key] / total : 0 }))
})
const summary = computed(
  () => props.label ?? parts.value.map((p) => `${t(`stock.parts.${p.key}`)} ${p.value}`).join(', '),
)
</script>

<template>
  <div
    class="flex w-full gap-[2px] overflow-hidden rounded-full bg-surface-2"
    :style="{ height: `${height}px` }"
    role="img"
    :aria-label="summary"
  >
    <span
      v-for="part in parts"
      :key="part.key"
      class="h-full first:rounded-l-full last:rounded-r-full"
      :style="{ width: `${part.share * 100}%`, background: COLORS[part.key] }"
    />
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

/** Legend of the stock bars (identity is never color alone). */
const { t } = useI18n()
const PARTS = [
  ['available', 'var(--chart-4)'],
  ['reserved', 'var(--chart-income)'],
  ['out', 'var(--chart-expense)'],
  ['maintenance', 'var(--chart-other)'],
] as const
</script>

<template>
  <ul class="flex flex-wrap gap-x-4 gap-y-1 text-[12.5px] font-semibold text-ink-2">
    <li v-for="[key, color] in PARTS" :key="key" class="flex items-center gap-1.5">
      <span class="size-2.5 rounded-[3px]" :style="{ background: color }" />
      {{ t(`stock.parts.${key}`) }}
    </li>
  </ul>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import { type Currency, formatMoney, formatMoneyShort } from '@/composables/useMoney'

const props = withDefaults(
  defineProps<{ amount: number; currency?: Currency; short?: boolean }>(),
  { currency: 'XOF' },
)

const text = computed(() =>
  props.short ? formatMoneyShort(props.amount) : formatMoney(props.amount, props.currency),
)
</script>

<template>
  <span
    class="font-display tabular whitespace-nowrap"
    :title="short ? formatMoney(amount, currency) : undefined"
    >{{ text }}</span
  >
</template>

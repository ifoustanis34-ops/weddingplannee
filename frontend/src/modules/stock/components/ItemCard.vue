<script setup lang="ts">
import { Package } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { formatAmount } from '@/composables/useMoney'

import type { Item } from '../types'
import StockBar from './StockBar.vue'

/** Grid card (§5.5): photo, name, bar « disponible / réservé / loué / maintenance ». */
const props = defineProps<{ item: Item }>()
defineEmits<{ open: [] }>()
const { t } = useI18n()
const today = computed(() => props.item.today)
const low = computed(
  () => props.item.alertThreshold > 0 && (today.value?.available ?? 0) <= props.item.alertThreshold,
)
</script>

<template>
  <button
    type="button"
    class="flex w-full flex-col overflow-hidden rounded-wd-lg border border-line bg-surface text-left transition-shadow hover:shadow-wd"
    :aria-label="`${item.name}, ${item.reference}`"
    @click="$emit('open')"
  >
    <div class="relative aspect-[4/3] w-full bg-surface-2">
      <img
        v-if="item.photoUrl"
        :src="item.photoUrl"
        alt=""
        class="size-full object-cover"
        loading="lazy"
      />
      <div v-else class="flex size-full items-center justify-center text-muted">
        <Package class="size-10" aria-hidden="true" />
      </div>
      <span
        class="absolute top-2 left-2 rounded-full bg-surface/90 px-2 py-0.5 text-[11.5px] font-bold text-ink-2"
        >{{ item.reference }}</span
      >
    </div>
    <div class="flex flex-1 flex-col gap-2 p-3.5">
      <div>
        <p class="line-clamp-2 font-bold">{{ item.name }}</p>
        <p class="text-[12.5px] text-muted">{{ item.categoryName }}</p>
      </div>
      <StockBar
        v-if="today"
        :available="today.available"
        :reserved="today.reserved"
        :out="today.out"
        :maintenance="today.maintenance + today.outOfService"
      />
      <div class="mt-auto text-[13px]">
        <p class="num font-semibold" :class="low ? 'text-coral' : 'text-ink-2'">
          {{
            t('stock.availableOf', { available: today?.available ?? 0, total: item.totalQuantity })
          }}
        </p>
        <p v-if="item.rentPrice !== null" class="num text-[12.5px] text-muted">
          {{ formatAmount(item.rentPrice) }} {{ t(`stock.perUnit.${item.rentUnit}`) }}
        </p>
      </div>
    </div>
  </button>
</template>

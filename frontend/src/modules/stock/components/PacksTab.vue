<script setup lang="ts">
import { Boxes, Plus } from '@lucide/vue'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { formatMoney } from '@/composables/useMoney'
import { usePermissions } from '@/composables/usePermissions'
import { WBadge, WButton, WEmptyState, WInput } from '@/design'

import { usePacks } from '../api'
import type { Pack } from '../types'
import PackModal from './PackModal.vue'

/** Packs (§5.1) with their availability over a chosen period. */
const { t } = useI18n()
const { can } = usePermissions()
const today = new Date().toISOString().slice(0, 10)
const from = ref(today)
const to = ref(today)
const packs = usePacks(() => ({
  from: from.value,
  to: to.value < from.value ? from.value : to.value,
}))
const editOpen = ref(false)
const edited = ref<Pack | null>(null)
function edit(pack: Pack | null): void {
  edited.value = pack
  editOpen.value = true
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-wrap items-end gap-3">
      <WInput v-model="from" type="date" :label="t('stock.packs.period')" class="w-[170px]" />
      <WInput v-model="to" type="date" :label="t('stock.packs.to')" class="w-[170px]" />
      <WButton v-if="can('editStock')" class="ml-auto" @click="edit(null)">
        <Plus class="size-[18px]" aria-hidden="true" />{{ t('stock.packs.add') }}
      </WButton>
    </div>
    <div v-if="packs.isPending.value" class="grid gap-4 md:grid-cols-2">
      <div v-for="n in 4" :key="n" class="skeleton h-44 rounded-wd-lg" />
    </div>
    <WEmptyState
      v-else-if="!packs.data.value?.length"
      :icon="Boxes"
      :title="t('stock.packs.empty')"
    />
    <div
      v-else
      class="grid gap-4 md:grid-cols-2"
      :class="packs.isPlaceholderData.value && 'opacity-60'"
    >
      <component
        :is="can('editStock') ? 'button' : 'div'"
        v-for="pack in packs.data.value"
        :key="pack.id"
        :type="can('editStock') ? 'button' : undefined"
        class="flex flex-col gap-3 rounded-wd-lg border border-line bg-surface p-5 text-left"
        :class="can('editStock') && 'hover:shadow-wd'"
        @click="can('editStock') && edit(pack)"
      >
        <div class="flex items-start gap-3">
          <div class="min-w-0 flex-1">
            <p class="font-display text-[16px] font-semibold">{{ pack.name }}</p>
            <p v-if="pack.price !== null" class="num text-[13.5px] text-ink-2">
              {{ formatMoney(pack.price) }}
            </p>
          </div>
          <WBadge :tone="(pack.available ?? 0) > 0 ? 'green' : 'red'">{{
            (pack.available ?? 0) > 0
              ? t('stock.packs.available', { count: pack.available }, pack.available ?? 0)
              : t('stock.packs.none')
          }}</WBadge>
        </div>
        <ul class="flex flex-col gap-1 text-[13px] text-ink-2">
          <li v-for="component in pack.components" :key="component.item" class="flex gap-2">
            <span class="num w-10 shrink-0 text-right font-bold text-ink">{{
              component.quantity
            }}</span>
            <span class="min-w-0 truncate">{{ component.itemName }}</span>
          </li>
        </ul>
      </component>
    </div>
    <PackModal v-model:open="editOpen" :pack="edited" />
  </div>
</template>

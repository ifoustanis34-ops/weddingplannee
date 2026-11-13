<script setup lang="ts">
import { Plus, Search } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { formatMoney } from '@/composables/useMoney'
import { WButton, WCard, WChips, WInput } from '@/design'
import { useCatalog } from '@/modules/catalog/api'
import type { ServiceItem } from '@/modules/catalog/types'

/** « Catalogue » card of the quote editor (complement §9): one click adds a service. */
const emit = defineEmits<{ pick: [item: ServiceItem] }>()
const { t } = useI18n()
const catalog = useCatalog()
const query = ref('')
const category = ref<string>('all')

const normalize = (text: string) =>
  text
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()

const categories = computed(() =>
  (catalog.data.value ?? []).filter((c) => c.items.some((item) => item.isActive)),
)
const chips = computed(() => [
  { value: 'all', label: t('quotes.allCategories') },
  ...categories.value.map((c) => ({ value: c.id, label: c.name })),
])
const items = computed(() =>
  categories.value
    .filter((c) => category.value === 'all' || c.id === category.value)
    .flatMap((c) =>
      c.items
        .filter(
          (item) =>
            item.isActive && normalize(`${item.name} ${c.name}`).includes(normalize(query.value)),
        )
        .map((item) => ({ item, categoryName: c.name })),
    ),
)
const total = computed(() => categories.value.reduce((n, c) => n + c.items.length, 0))
</script>

<template>
  <WCard :title="t('quotes.catalogTitle')">
    <template #actions>
      <span class="text-[13px] font-semibold text-muted">{{
        t('quotes.catalogCount', { count: total }, total)
      }}</span>
    </template>
    <div class="flex flex-col gap-3">
      <WInput
        v-model="query"
        type="search"
        hide-label
        :label="t('quotes.catalogSearch')"
        :placeholder="t('quotes.catalogSearch')"
      >
        <template #prefix><Search class="size-4" aria-hidden="true" /></template>
      </WInput>
      <WChips
        v-if="chips.length > 2"
        v-model="category"
        :options="chips"
        :label="t('catalog.title')"
      />
      <div v-if="catalog.isPending.value" class="skeleton h-32" />
      <p v-else-if="!items.length" class="text-[13px] text-muted">{{ t('quotes.catalogEmpty') }}</p>
      <ul v-else class="-mx-1 flex max-h-[340px] flex-col overflow-y-auto px-1">
        <li
          v-for="{ item, categoryName } in items"
          :key="item.id"
          class="flex items-center gap-3 border-b border-line py-2.5 last:border-b-0"
        >
          <span class="min-w-0 flex-1">
            <span class="block truncate font-bold">{{ item.name }}</span>
            <span class="block truncate text-[12.5px] text-muted">
              {{ categoryName }}, {{ formatMoney(item.unitPrice) }} /
              {{ t(`catalog.units.${item.unit}`).toLowerCase() }}
            </span>
          </span>
          <WButton
            size="sm"
            variant="secondary"
            :aria-label="t('quotes.addService', { name: item.name })"
            @click="emit('pick', item)"
          >
            <Plus class="size-[15px]" aria-hidden="true" />{{ t('quotes.add') }}
          </WButton>
        </li>
      </ul>
    </div>
  </WCard>
</template>

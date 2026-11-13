<script setup lang="ts">
import { Plus, X } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { usePermissions } from '@/composables/usePermissions'
import { useServerErrors } from '@/composables/useServerErrors'
import { useToast } from '@/composables/useToast'
import { WButton, WInput, WModal, WSelect, WTextarea } from '@/design'

import { stockApi, useItems, useStockMutation } from '../api'
import type { Pack } from '../types'

/** Ready-to-book set (§5.1): available when all its parts are. */
const props = defineProps<{ pack?: Pack | null }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const toast = useToast()
const applyServerErrors = useServerErrors()
const { can } = usePermissions()
const items = useItems({})

const name = ref('')
const description = ref('')
const price = ref<number | null>(0)
const rows = ref<{ item: string; quantity: number | null }[]>([])
const errors = ref<Record<string, string>>({})

watch(open, (isOpen) => {
  if (!isOpen) return
  errors.value = {}
  name.value = props.pack?.name ?? ''
  description.value = props.pack?.description ?? ''
  price.value = props.pack?.price ?? 0
  rows.value = props.pack
    ? props.pack.components.map((c) => ({ item: c.item, quantity: c.quantity }))
    : [{ item: '', quantity: 1 }]
})

const itemOptions = computed(() =>
  (items.data.value ?? []).map((i) => ({ value: i.id, label: `${i.name} (${i.reference})` })),
)
const nameOf = (id: string) => items.data.value?.find((i) => i.id === id)?.name ?? ''
const save = useStockMutation((input: Partial<Pack>) =>
  stockApi.savePack(props.pack?.id ?? null, input),
)

async function submit(): Promise<void> {
  errors.value = {}
  const components = rows.value
    .filter((row) => row.item && row.quantity && row.quantity > 0)
    .map((row) => ({ item: row.item, itemName: '', quantity: row.quantity! }))
  if (!name.value.trim()) errors.value.name = t('stock.packs.nameRequired')
  if (!components.length) errors.value.components = t('stock.packs.componentsRequired')
  if (Object.keys(errors.value).length) return
  const input: Partial<Pack> = {
    name: name.value.trim(),
    description: description.value,
    components,
  }
  if (can('viewStockPrices')) input.price = price.value ?? 0
  try {
    await save.mutateAsync(input)
    toast.success(t('stock.packs.saved'))
    open.value = false
  } catch (error) {
    applyServerErrors(error, (field, message) => (errors.value[field] = message), [
      'name',
      'price',
      'components',
    ])
  }
}
</script>

<template>
  <WModal
    v-model:open="open"
    :title="pack ? t('stock.packs.titleEdit') : t('stock.packs.titleNew')"
    size="md"
  >
    <form id="pack-form" class="flex flex-col gap-4" novalidate @submit.prevent="submit">
      <WInput v-model="name" :label="t('stock.packs.name')" :error="errors.name" required />
      <WInput
        v-if="can('viewStockPrices')"
        v-model.number="price"
        :label="t('stock.packs.price')"
        :error="errors.price"
        type="number"
        min="0"
        step="1000"
        inputmode="numeric"
      />
      <WTextarea v-model="description" :label="t('stock.packs.description')" :rows="2" />
      <fieldset class="flex flex-col gap-2">
        <legend class="mb-1 text-[13px] font-bold">{{ t('stock.packs.components') }}</legend>
        <div v-for="(row, index) in rows" :key="index" class="flex items-end gap-2">
          <WSelect
            v-model="row.item"
            class="min-w-0 flex-1"
            :label="t('stock.movement.item')"
            :options="itemOptions"
            :placeholder="t('stock.movement.chooseItem')"
            hide-label
          />
          <WInput
            v-model.number="row.quantity"
            class="w-[90px]"
            :label="t('stock.movement.quantity')"
            type="number"
            min="1"
            hide-label
          />
          <WButton
            variant="ghost"
            icon
            :aria-label="t('stock.packs.removeComponent', { name: nameOf(row.item) })"
            @click="rows.splice(index, 1)"
          >
            <X class="size-[18px]" aria-hidden="true" />
          </WButton>
        </div>
        <p v-if="errors.components" class="text-[13px] font-semibold text-red">
          {{ errors.components }}
        </p>
        <WButton
          size="sm"
          variant="secondary"
          class="self-start"
          @click="rows.push({ item: '', quantity: 1 })"
        >
          <Plus class="size-[15px]" aria-hidden="true" />{{ t('stock.packs.addComponent') }}
        </WButton>
      </fieldset>
    </form>
    <template #footer>
      <WButton variant="secondary" @click="open = false">{{ t('common.cancel') }}</WButton>
      <WButton type="submit" form="pack-form" :loading="save.isPending.value">{{
        t('stock.packs.save')
      }}</WButton>
    </template>
  </WModal>
</template>

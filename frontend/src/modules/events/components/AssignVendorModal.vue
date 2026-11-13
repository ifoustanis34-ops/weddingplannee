<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { usePermissions } from '@/composables/usePermissions'
import { useToast } from '@/composables/useToast'
import { WButton, WInput, WModal, WSelect } from '@/design'
import { useVendorAction, useVendors, vendorsApi } from '@/modules/vendors/api'

/** Book a vendor of the directory for a wedding: service, cost, already paid. */
const props = defineProps<{ weddingId: string }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const toast = useToast()
const { can } = usePermissions()
const vendors = useVendors()

const vendor = ref<string | null>(null)
const service = ref('')
const cost = ref<number | null>(null)
const paid = ref<number | null>(null)
const errors = ref<Record<string, string | undefined>>({})

watch(open, (isOpen) => {
  if (!isOpen) return
  vendor.value = null
  service.value = ''
  cost.value = null
  paid.value = null
  errors.value = {}
})

const options = computed(() =>
  (vendors.data.value ?? []).map((v) => ({ value: v.id, label: `${v.name} · ${v.categoryLabel}` })),
)
const book = useVendorAction(() =>
  vendorsApi.book(props.weddingId, {
    vendor: vendor.value!,
    service: service.value.trim(),
    ...(can('viewFinance') ? { cost: cost.value ?? 0, paidAmount: paid.value ?? 0 } : {}),
  }),
)
async function submit(): Promise<void> {
  errors.value = {}
  if (!vendor.value) {
    errors.value.vendor = t('weddings.assign.vendorRequired')
    return
  }
  try {
    await book.mutateAsync(undefined)
    toast.success(t('weddings.assign.done'))
    open.value = false
  } catch (error) {
    const apiError = toApiError(error)
    errors.value = Object.fromEntries(Object.entries(apiError.fields).map(([k, v]) => [k, v[0]]))
    if (!Object.keys(apiError.fields).length) toast.error(apiError.message)
  }
}
</script>

<template>
  <WModal v-model:open="open" :title="t('weddings.drawer.addVendor')">
    <form id="assign-form" class="grid gap-4 sm:grid-cols-2" novalidate @submit.prevent="submit">
      <WSelect
        v-model="vendor"
        class="sm:col-span-2"
        :label="t('weddings.assign.vendor')"
        :placeholder="t('weddings.assign.choose')"
        :options="options"
        :hint="!options.length ? t('weddings.assign.emptyDirectory') : undefined"
        :error="errors.vendor"
        required
      />
      <WInput v-model="service" class="sm:col-span-2" :label="t('weddings.assign.service')" />
      <template v-if="can('viewFinance')">
        <WInput
          v-model.number="cost"
          type="number"
          min="0"
          :label="t('weddings.assign.cost')"
          :error="errors.cost"
        />
        <WInput
          v-model.number="paid"
          type="number"
          min="0"
          :label="t('weddings.assign.paid')"
          :error="errors.paidAmount ?? errors.paid_amount"
        />
      </template>
    </form>
    <template #footer>
      <WButton variant="secondary" @click="open = false">{{ t('common.cancel') }}</WButton>
      <WButton type="submit" form="assign-form" :loading="book.isPending.value">{{
        t('weddings.assign.submit')
      }}</WButton>
    </template>
  </WModal>
</template>

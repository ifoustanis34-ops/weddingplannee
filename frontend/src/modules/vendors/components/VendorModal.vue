<script setup lang="ts">
import { Trash2 } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { useToast } from '@/composables/useToast'
import { useSessionStore } from '@/stores/session'
import { WButton, WInput, WModal, WSelect, WTextarea } from '@/design'

import { useVendorAction, vendorsApi } from '../api'
import {
  emptyVendor,
  VENDOR_CATEGORIES,
  VENDOR_KINDS,
  type Vendor,
  type VendorInput,
  type VendorKind,
} from '../types'

/**
 * « Ajouter un fournisseur / un partenaire » / edit a record (feedback 13/11/2026: the complete record): the
 * company, who to call, its legal identifiers and how it is paid.
 */
const props = defineProps<{ vendor: Vendor | null; defaultKind?: VendorKind }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const toast = useToast()

const form = ref<VendorInput>(emptyVendor())
const errors = ref<Record<string, string | undefined>>({})

watch(open, (isOpen) => {
  if (!isOpen) return
  errors.value = {}
  const v = props.vendor
  if (!v) {
    form.value = emptyVendor(props.defaultKind)
    return
  }
  const base = emptyVendor()
  form.value = Object.fromEntries(
    Object.keys(base).map((key) => [
      key,
      v[key as keyof VendorInput] ?? base[key as keyof VendorInput],
    ]),
  ) as VendorInput
})

/** The WhatsApp number is usually the phone: copied while left empty. */
function phoneBlur(): void {
  if (!form.value.whatsapp.trim() && form.value.phone.trim()) form.value.whatsapp = form.value.phone
}

const kindOptions = computed(() =>
  VENDOR_KINDS.map((value) => ({ value, label: t(`vendors.kinds.${value}`) })),
)
const title = computed(() =>
  props.vendor
    ? t('vendors.form.editTitle')
    : t(form.value.kind === 'partner' ? 'vendors.addPartner' : 'vendors.addSupplier'),
)
const categoryOptions = computed(() =>
  VENDOR_CATEGORIES.map((value) => ({ value, label: t(`vendors.categories.${value}`) })),
)

const save = useVendorAction(() =>
  props.vendor ? vendorsApi.update(props.vendor.id, form.value) : vendorsApi.create(form.value),
)
// « Supprimer » (feedback 13/11/2026): owner and planner. A contact that worked on weddings
// leaves the address book but stays on those weddings.
const session = useSessionStore()
const canDelete = computed(() => session.role === 'owner' || session.role === 'planner')
const deleteOpen = ref(false)
const remove = useVendorAction((id: string) => vendorsApi.remove(id))
async function confirmDelete(): Promise<void> {
  if (!props.vendor) return
  try {
    await remove.mutateAsync(props.vendor.id)
    toast.success(t('vendors.delete.done', { name: props.vendor.name }))
    deleteOpen.value = false
    open.value = false
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}

const camel = (key: string) => key.replace(/_(\w)/g, (_, c: string) => c.toUpperCase())
async function submit(): Promise<void> {
  errors.value = {}
  if (!form.value.name.trim()) {
    errors.value.name = t('vendors.form.nameRequired')
    return
  }
  try {
    const saved = await save.mutateAsync(undefined)
    toast.success(
      props.vendor ? t('vendors.form.saved') : t('vendors.form.created', { name: saved.name }),
    )
    open.value = false
  } catch (error) {
    const apiError = toApiError(error)
    errors.value = Object.fromEntries(
      Object.entries(apiError.fields).map(([k, v]) => [camel(k), v[0]]),
    )
    if (!Object.keys(apiError.fields).length) toast.error(apiError.message)
  }
}
</script>

<template>
  <WModal v-model:open="open" size="lg" :title="title">
    <form id="vendor-form" class="flex flex-col gap-6" novalidate @submit.prevent="submit">
      <fieldset class="grid gap-4 sm:grid-cols-2">
        <legend class="mb-3 text-[13px] font-bold text-muted">
          {{ t('vendors.form.sections.company') }}
        </legend>
        <WInput
          v-model="form.name"
          class="sm:col-span-2"
          :label="t('vendors.form.name')"
          :error="errors.name"
          required
          autofocus
        />
        <WSelect
          v-model="form.kind"
          :label="t('vendors.form.kind')"
          :options="kindOptions"
          :hint="t(`vendors.kindHints.${form.kind}`)"
          :error="errors.kind"
        />
        <WSelect
          v-model="form.category"
          :label="t('vendors.form.category')"
          :options="categoryOptions"
          :error="errors.category"
        />
        <WTextarea
          v-model="form.services"
          class="sm:col-span-2"
          :label="t('vendors.form.services')"
          :placeholder="t('vendors.form.servicesPlaceholder')"
          :error="errors.services"
          :rows="3"
        />
      </fieldset>

      <fieldset class="grid gap-4 sm:grid-cols-2">
        <legend class="mb-3 text-[13px] font-bold text-muted">
          {{ t('vendors.form.sections.contact') }}
        </legend>
        <WInput
          v-model="form.contactName"
          :label="t('vendors.form.contactName')"
          :placeholder="t('vendors.form.contactPlaceholder')"
          :error="errors.contactName"
        />
        <WInput
          v-model="form.email"
          type="email"
          :label="t('common.fields.email')"
          :error="errors.email"
        />
        <WInput
          v-model="form.phone"
          type="tel"
          :label="t('common.fields.phone')"
          placeholder="+237 6XX XX XX XX"
          :error="errors.phone"
          @blur="phoneBlur"
        />
        <WInput
          v-model="form.whatsapp"
          type="tel"
          :label="t('vendors.form.whatsapp')"
          :error="errors.whatsapp"
        />
        <WInput
          v-model="form.city"
          :label="t('vendors.form.city')"
          :placeholder="t('vendors.form.cityPlaceholder')"
          :error="errors.city"
        />
        <WInput
          v-model="form.address"
          :label="t('vendors.form.address')"
          :placeholder="t('vendors.form.addressPlaceholder')"
          :error="errors.address"
        />
      </fieldset>

      <fieldset class="grid gap-4 sm:grid-cols-2">
        <legend class="mb-3 text-[13px] font-bold text-muted">
          {{ t('vendors.form.sections.legal') }}
        </legend>
        <WInput
          v-model="form.taxId"
          :label="t('vendors.form.taxId')"
          placeholder="M0XXXXXXXXXXXA"
          :error="errors.taxId"
        />
        <WInput
          v-model="form.tradeRegister"
          :label="t('vendors.form.tradeRegister')"
          placeholder="RC/DLA/2020/B/0000"
          :error="errors.tradeRegister"
        />
      </fieldset>

      <fieldset class="grid gap-4 sm:grid-cols-2">
        <legend class="mb-3 text-[13px] font-bold text-muted">
          {{ t('vendors.form.sections.payment') }}
        </legend>
        <WInput
          v-model="form.paymentTerms"
          class="sm:col-span-2"
          :label="t('vendors.form.paymentTerms')"
          :placeholder="t('vendors.form.paymentTermsPlaceholder')"
          :error="errors.paymentTerms"
        />
        <WInput
          v-model="form.mobileMoney"
          type="tel"
          :label="t('vendors.form.mobileMoney')"
          :hint="t('vendors.form.mobileMoneyHint')"
          :error="errors.mobileMoney"
        />
        <WInput
          v-model="form.bankDetails"
          :label="t('vendors.form.bankDetails')"
          :placeholder="t('vendors.form.bankPlaceholder')"
          :error="errors.bankDetails"
        />
        <WTextarea
          v-model="form.notes"
          class="sm:col-span-2"
          :label="t('vendors.form.notes')"
          :placeholder="t('vendors.form.notesPlaceholder')"
          :rows="3"
        />
      </fieldset>
    </form>
    <template #footer>
      <button
        v-if="vendor && canDelete"
        type="button"
        class="mr-auto inline-flex h-10 items-center gap-2 rounded-[10px] px-3 text-[14px] font-bold text-red hover:bg-red-soft"
        @click="deleteOpen = true"
      >
        <Trash2 class="size-[18px]" aria-hidden="true" />{{ t('vendors.delete.action') }}
      </button>
      <WButton variant="secondary" @click="open = false">{{ t('common.cancel') }}</WButton>
      <WButton type="submit" form="vendor-form" :loading="save.isPending.value">{{
        vendor ? t('vendors.form.save') : title
      }}</WButton>
    </template>
  </WModal>
  <WModal
    v-if="vendor"
    v-model:open="deleteOpen"
    :title="t('vendors.delete.title', { name: vendor.name })"
    size="sm"
  >
    <p class="text-[14px] text-ink-2">
      {{ vendor.collaborations ? t('vendors.delete.textUsed') : t('vendors.delete.text') }}
    </p>
    <template #footer>
      <WButton variant="secondary" @click="deleteOpen = false">{{ t('common.cancel') }}</WButton>
      <WButton variant="danger" :loading="remove.isPending.value" @click="confirmDelete">{{
        t('vendors.delete.confirm')
      }}</WButton>
    </template>
  </WModal>
</template>

<script setup lang="ts">
import { Check, FileDown, Pencil, Truck, Undo2, Wallet, X } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { api } from '@/api/client'
import { toApiError } from '@/api/errors'
import { formatDate, formatDateTime } from '@/composables/useDate'
import { formatMoney } from '@/composables/useMoney'
import { usePermissions } from '@/composables/usePermissions'
import { useSessionStore } from '@/stores/session'
import { useToast } from '@/composables/useToast'
import { WBadge, WButton, WDrawer, WEmptyState, WInput, WModal, WSelect } from '@/design'
import WhatsAppButton from '@/components/WhatsAppButton.vue'
import ReservationInvoices from '@/modules/finance/components/ReservationInvoices.vue'
import ReservationTeam from '@/modules/staff/components/ReservationTeam.vue'

import { reservationsApi, useReservation, useReservationMutation } from '../api'
import { METHODS, OUT, STATUS_TONES, STEPS } from '../constants'
import type { Reservation, ReservationLine, ReservationStatus } from '../types'
import ReservationPartners from './ReservationPartners.vue'
import ReservationWizard from './ReservationWizard.vue'

/** Reservation sheet (reservations-stock.md §4.2): steps, order, payments, documents, history. */
const props = defineProps<{ reservationId: string | null }>()
const emit = defineEmits<{ close: [] }>()
const { t } = useI18n()
const toast = useToast()
const { can } = usePermissions()
const session = useSessionStore()

const open = computed({
  get: () => props.reservationId !== null,
  set: (value) => {
    if (!value) emit('close')
  },
})
const reservation = useReservation(() => props.reservationId)
const data = computed(() => reservation.data.value)
const role = computed(() => session.role)
const canEdit = computed(() => role.value === 'owner' || role.value === 'planner')
const canLogistics = computed(() => canEdit.value || role.value === 'storekeeper')
// §7: the team on the reservation (the storekeeper does not manage people).
const seesTeam = computed(() =>
  ['owner', 'planner', 'assistant', 'accountant'].includes(role.value ?? ''),
)
const canPay = computed(() => role.value === 'owner' || role.value === 'accountant')
const seesMoney = computed(() => can('viewFinance'))
const editOpen = ref(false)

const equipment = computed(() =>
  (data.value?.lines ?? []).filter((l) => ['rental', 'sale', 'pack'].includes(l.kind)),
)
const timeline = computed(() =>
  STEPS.map((key) => {
    const field = key.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase()) as keyof Reservation
    return { key, at: (data.value?.[field] as string | null) ?? null }
  }).filter((step) => step.at),
)
const isPast = (at: string) => new Date(at).getTime() < Date.now()

// --- Actions --------------------------------------------------------------------------------------
const act = useReservationMutation(
  async ({ id, action, status }: { id: string; action: string; status?: string }) => {
    if (action === 'confirm') return reservationsApi.confirm(id)
    return reservationsApi.status(id, status!)
  },
)
async function run(action: string, status?: ReservationStatus): Promise<void> {
  if (!data.value) return
  try {
    const saved = await act.mutateAsync({ id: data.value.id, action, status })
    toast.success(
      action === 'confirm'
        ? saved.status === 'confirmed'
          ? t('reservations.drawer.confirmed')
          : t('reservations.drawer.awaitingDeposit')
        : t('reservations.drawer.advanced', { status: t(`reservations.statuses.${saved.status}`) }),
    )
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
const NEXT: Partial<Record<ReservationStatus, ReservationStatus[]>> = {
  confirmed: ['preparing'],
  delivered: ['installed', 'picked_up'],
  installed: ['in_progress', 'picked_up'],
  in_progress: ['picked_up'],
}
const hasEquipment = computed(() => equipment.value.length > 0)
const nextSteps = computed<ReservationStatus[]>(() => {
  const status = data.value?.status
  if (!status) return []
  if (!hasEquipment.value && (status === 'confirmed' || status === 'preparing'))
    return ['in_progress']
  if (!hasEquipment.value && status === 'in_progress') return ['closed']
  return NEXT[status] ?? []
})

// Checkout ------------------------------------------------------------------------------------
const checkoutOpen = ref(false)
const outCounts = ref<Record<string, number>>({})
function openCheckout(): void {
  outCounts.value = Object.fromEntries(equipment.value.map((l) => [l.id!, l.quantity]))
  checkoutOpen.value = true
}
const checkout = useReservationMutation(
  ({ id, quantities }: { id: string; quantities: Record<string, number> }) =>
    reservationsApi.checkout(id, quantities),
)
async function confirmCheckout(): Promise<void> {
  if (!data.value) return
  try {
    await checkout.mutateAsync({ id: data.value.id, quantities: outCounts.value })
    checkoutOpen.value = false
    toast.success(t('reservations.checkout.done'))
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}

// Return --------------------------------------------------------------------------------------
const returnOpen = ref(false)
const returned = ref<Record<string, { returned: number; damaged: number; missing: number }>>({})
const returnable = computed(() =>
  equipment.value.filter((l) => l.kind !== 'sale' && (l.quantityOut ?? 0) > 0),
)
function openReturn(): void {
  returned.value = Object.fromEntries(
    returnable.value.map((l) => [l.id!, { returned: l.quantityOut ?? 0, damaged: 0, missing: 0 }]),
  )
  returnOpen.value = true
}
const mismatch = (line: ReservationLine) => {
  const c = returned.value[line.id!]
  return !c || c.returned + c.damaged + c.missing !== (line.quantityOut ?? 0)
}
const doReturn = useReservationMutation(
  ({
    id,
    lines,
  }: {
    id: string
    lines: Record<string, { returned: number; damaged: number; missing: number }>
  }) => reservationsApi.return(id, lines),
)
async function confirmReturn(): Promise<void> {
  if (!data.value || returnable.value.some(mismatch)) return
  try {
    await doReturn.mutateAsync({ id: data.value.id, lines: returned.value })
    returnOpen.value = false
    toast.success(t('reservations.return.done'))
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}

// Payments and security deposit --------------------------------------------------------------
const paymentOpen = ref(false)
const paymentKind = ref<'payment' | 'security'>('payment')
const payment = ref({
  amount: 0,
  method: 'orange_money',
  paidAt: new Date().toISOString().slice(0, 10),
  reference: '',
})
function openPayment(kind: 'payment' | 'security'): void {
  paymentKind.value = kind
  payment.value = {
    amount: kind === 'security' ? (data.value?.securityDeposit ?? 0) : (data.value?.balance ?? 0),
    method: 'orange_money',
    paidAt: new Date().toISOString().slice(0, 10),
    reference: '',
  }
  paymentOpen.value = true
}
const pay = useReservationMutation(
  ({
    id,
    input,
  }: {
    id: string
    input: { amount: number; method: string; paidAt: string; reference: string; kind: string }
  }) => reservationsApi.pay(id, input),
)
async function confirmPayment(): Promise<void> {
  if (!data.value) return
  try {
    await pay.mutateAsync({
      id: data.value.id,
      input: { ...payment.value, kind: paymentKind.value },
    })
    paymentOpen.value = false
    toast.success(t('reservations.payment.saved', { amount: formatMoney(payment.value.amount) }))
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
const methodOptions = computed(() =>
  METHODS.map((value) => ({ value, label: t(`finance.methods.${value}`) })),
)
const settleOpen = ref(false)
const settle = ref({ retained: 0, method: 'cash', reason: '' })
const doSettle = useReservationMutation(({ id }: { id: string }) =>
  reservationsApi.settleSecurity(id, settle.value),
)
async function confirmSettle(): Promise<void> {
  if (!data.value) return
  try {
    await doSettle.mutateAsync({ id: data.value.id })
    settleOpen.value = false
    toast.success(t('reservations.payment.settled'))
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}

// Cancellation -------------------------------------------------------------------------------
const cancelOpen = ref(false)
const cancelReason = ref('')
const doCancel = useReservationMutation(({ id }: { id: string }) =>
  reservationsApi.cancel(id, cancelReason.value),
)
async function confirmCancel(): Promise<void> {
  if (!data.value) return
  try {
    await doCancel.mutateAsync({ id: data.value.id })
    cancelOpen.value = false
    toast.success(t('reservations.cancel.done'))
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}

// Documents: fetched with the session, then opened -------------------------------------------
function slipBlob(type: 'checkout' | 'return'): Promise<Blob> {
  return api
    .get<Blob>(`/reservations/${data.value!.id}/document`, {
      params: { type },
      responseType: 'blob',
    })
    .then((r) => r.data)
}
const slipName = (type: 'checkout' | 'return') =>
  t(type === 'checkout' ? 'reservations.drawer.checkoutSlip' : 'reservations.drawer.returnSlip')
async function openDocument(type: 'checkout' | 'return'): Promise<void> {
  if (!data.value) return
  try {
    const url = URL.createObjectURL(await slipBlob(type))
    window.open(url, '_blank', 'noopener')
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
const money = (value: number | null | undefined) => (value == null ? '—' : formatMoney(value))
</script>

<template>
  <WDrawer v-model:open="open" wide :title="data?.title ?? t('common.loading')">
    <template v-if="data" #heading="{ titleId }">
      <div>
        <p class="text-[12.5px] font-bold text-violet">{{ data.number }}</p>
        <h2 :id="titleId" class="text-[17px] font-semibold">{{ data.title }}</h2>
        <p class="mt-1 flex flex-wrap items-center gap-2 text-[13px] text-muted">
          <WBadge :tone="STATUS_TONES[data.status]">{{
            t(`reservations.statuses.${data.status}`)
          }}</WBadge>
          <span>{{ data.clientDetail.name }}</span>
          <span v-if="data.venue">· {{ data.venue }}</span>
          <span v-if="data.vehicle"
            >· {{ t('reservations.drawer.vehicle', { name: data.vehicle }) }}</span
          >
        </p>
      </div>
    </template>

    <div
      v-if="reservation.isPending.value"
      class="flex flex-col gap-3"
      :aria-label="t('common.loading')"
    >
      <div v-for="n in 4" :key="n" class="skeleton h-12" />
    </div>
    <WEmptyState v-else-if="!data" :title="t('reservations.drawer.notFound')" />

    <template v-else>
      <p
        v-if="data.status === 'cancelled'"
        class="rounded-wd bg-red-soft px-3 py-2 text-[13px] font-semibold text-red"
      >
        {{ t('reservations.drawer.cancelled', { reason: data.cancelReason }) }}
        <template v-if="data.refundDue">
          · {{ t('reservations.drawer.refundDue', { amount: money(data.refundDue) }) }}</template
        >
      </p>

      <!-- Timeline of the logistic steps -->
      <section>
        <h3>{{ t('reservations.drawer.timeline') }}</h3>
        <ol class="mt-3 grid gap-2 sm:grid-cols-4 lg:grid-cols-7">
          <li
            v-for="step in timeline"
            :key="step.key"
            class="rounded-wd border px-3 py-2"
            :class="isPast(step.at!) ? 'border-line bg-surface-2' : 'border-line'"
          >
            <p class="flex items-center gap-1 text-[11.5px] font-bold text-muted">
              <Check v-if="isPast(step.at!)" class="size-3 text-green" aria-hidden="true" />
              {{ t(`reservations.steps.${step.key}`) }}
            </p>
            <p class="text-[12.5px] font-semibold">{{ formatDateTime(step.at!) }}</p>
          </li>
        </ol>
      </section>

      <!-- Order -->
      <section>
        <h3>{{ t('reservations.drawer.lines') }}</h3>
        <ul class="mt-2 divide-y divide-line rounded-wd border border-line">
          <li
            v-for="line in data.lines"
            :key="line.id"
            class="flex items-start gap-3 px-3 py-2.5 text-[13.5px]"
          >
            <span class="num w-10 shrink-0 text-right font-bold">{{ line.quantity }}</span>
            <span class="min-w-0 flex-1">
              <span class="block font-semibold" :class="line.kind === 'damage' && 'text-coral'">{{
                line.label
              }}</span>
              <span class="block text-[12px] text-muted">
                {{ t(`reservations.lineKinds.${line.kind}`) }}
                <template v-if="line.partnerQuantity">
                  ·
                  <span class="font-semibold text-violet">{{
                    t('reservations.drawer.partnerPart', {
                      count: line.partnerQuantity,
                      name: line.partnerName,
                    })
                  }}</span></template
                >
                <template v-if="line.quantityOut">
                  · {{ t('reservations.drawer.quantityOut', { out: line.quantityOut }) }}</template
                >
                <template v-if="data.returnedAt && line.quantityOut && line.kind !== 'sale'">
                  ·
                  {{
                    t('reservations.drawer.returned', {
                      returned: line.quantityReturned,
                      damaged: line.quantityDamaged,
                      missing: line.quantityMissing,
                    })
                  }}
                </template>
              </span>
            </span>
            <span v-if="seesMoney" class="num shrink-0">{{ money(line.amount) }}</span>
          </li>
        </ul>
        <dl
          v-if="seesMoney"
          class="ml-auto mt-3 grid max-w-[300px] grid-cols-2 gap-y-1 text-[13.5px]"
        >
          <template v-if="data.discount">
            <dt class="text-muted">{{ t('reservations.wizard.discount') }}</dt>
            <dd class="num text-right">−{{ money(data.discount) }}</dd>
          </template>
          <template v-if="data.transportFee">
            <dt class="text-muted">{{ t('reservations.wizard.transport') }}</dt>
            <dd class="num text-right">{{ money(data.transportFee) }}</dd>
          </template>
          <template v-if="data.setupFee">
            <dt class="text-muted">{{ t('reservations.wizard.setupFee') }}</dt>
            <dd class="num text-right">{{ money(data.setupFee) }}</dd>
          </template>
          <dt class="font-bold">{{ t('reservations.wizard.total') }}</dt>
          <dd class="num text-right font-display text-[16px] font-semibold">
            {{ money(data.total) }}
          </dd>
          <dt class="text-muted">{{ t('reservations.columns.paid') }}</dt>
          <dd class="num text-right">{{ money(data.paid) }}</dd>
          <dt class="font-bold">{{ t('reservations.columns.balance') }}</dt>
          <dd class="num text-right font-bold" :class="(data.balance ?? 0) > 0 && 'text-coral'">
            {{ money(data.balance) }}
          </dd>
        </dl>
      </section>

      <ReservationPartners v-if="hasEquipment" :reservation="data" :can-edit="canEdit" />

      <!-- Payments and caution -->
      <section v-if="seesMoney">
        <div class="flex flex-wrap items-center gap-2">
          <h3 class="flex-1">{{ t('reservations.drawer.payments') }}</h3>
          <WButton
            v-if="
              canPay && !['draft', 'cancelled'].includes(data.status) && (data.balance ?? 0) > 0
            "
            size="sm"
            @click="openPayment('payment')"
          >
            <Wallet class="size-[15px]" aria-hidden="true" />{{ t('reservations.drawer.record') }}
          </WButton>
        </div>
        <p v-if="!data.payments.length" class="mt-1 text-muted">
          {{ t('reservations.drawer.noPayment') }}
        </p>
        <ul v-else class="mt-2 flex flex-col gap-1.5 text-[13px]">
          <li
            v-for="p in data.payments"
            :key="p.id"
            class="flex items-baseline gap-3"
            :class="p.isCancelled && 'text-muted line-through'"
          >
            <span class="w-24 shrink-0">{{ formatDate(p.paidAt) }}</span>
            <span class="min-w-0 flex-1"
              >{{ p.kindLabel }} · {{ p.methodLabel
              }}<template v-if="p.reference"> · {{ p.reference }}</template></span
            >
            <span class="num font-semibold">{{ formatMoney(p.amount) }}</span>
          </li>
        </ul>
        <div
          class="mt-3 flex flex-wrap items-center gap-2 rounded-wd border border-line px-3 py-2.5 text-[13px]"
        >
          <span class="font-bold">{{ t('reservations.drawer.security') }}</span>
          <span class="num">{{ money(data.securityDeposit) }}</span>
          <span class="text-muted"
            >·
            {{
              t(`reservations.drawer.securityStatus.${data.securityStatus}`, {
                amount: money(data.securityRetained),
              })
            }}</span
          >
          <WButton
            v-if="
              canPay &&
              data.securityStatus === 'none' &&
              (data.securityDeposit ?? 0) > 0 &&
              !['draft', 'cancelled'].includes(data.status)
            "
            size="sm"
            variant="secondary"
            class="ml-auto"
            @click="openPayment('security')"
            >{{ t('reservations.drawer.collectSecurity') }}</WButton
          >
          <WButton
            v-if="canPay && data.securityStatus === 'held'"
            size="sm"
            variant="secondary"
            class="ml-auto"
            @click="((settle = { retained: 0, method: 'cash', reason: '' }), (settleOpen = true))"
            >{{ t('reservations.drawer.settleSecurity') }}</WButton
          >
        </div>
      </section>

      <!-- Documents -->
      <section v-if="hasEquipment">
        <h3>{{ t('reservations.drawer.documents') }}</h3>
        <div class="mt-2 flex flex-wrap gap-2">
          <span class="inline-flex gap-1">
            <WButton size="sm" variant="secondary" @click="openDocument('checkout')">
              <FileDown class="size-[15px]" aria-hidden="true" />{{
                t('reservations.drawer.checkoutSlip')
              }}
            </WButton>
            <WhatsAppButton
              icon
              :phone="data.clientDetail.phone"
              :file="() => slipBlob('checkout')"
              :filename="`${data.number}-bon-de-sortie.pdf`"
              :label="t('whatsapp.slip', { document: slipName('checkout').toLowerCase() })"
            />
          </span>
          <span class="inline-flex gap-1">
            <WButton size="sm" variant="secondary" @click="openDocument('return')">
              <FileDown class="size-[15px]" aria-hidden="true" />{{
                t('reservations.drawer.returnSlip')
              }}
            </WButton>
            <WhatsAppButton
              icon
              :phone="data.clientDetail.phone"
              :file="() => slipBlob('return')"
              :filename="`${data.number}-bon-de-retour.pdf`"
              :label="t('whatsapp.slip', { document: slipName('return').toLowerCase() })"
            />
          </span>
        </div>
      </section>

      <ReservationTeam
        v-if="seesTeam"
        :reservation-id="data.id"
        :can-edit="canEdit"
        :open="!['closed', 'cancelled'].includes(data.status)"
      />

      <ReservationInvoices v-if="can('viewFinance')" :reservation="data" />

      <!-- History -->
      <section>
        <h3>{{ t('reservations.drawer.history') }}</h3>
        <ol class="mt-2 ml-[5px] flex flex-col gap-3 border-l-2 border-line pl-5">
          <li v-for="entry in data.logs" :key="entry.id" class="relative text-[13px]">
            <span
              class="absolute top-1 -left-[27px] size-3 rounded-full border-2 border-violet bg-surface"
              aria-hidden="true"
            />
            <p class="font-semibold">{{ entry.message }}</p>
            <p class="text-[12px] text-muted">
              {{ formatDateTime(entry.createdAt)
              }}<template v-if="entry.authorName"> · {{ entry.authorName }}</template>
            </p>
          </li>
        </ol>
      </section>
    </template>

    <template v-if="data" #footer>
      <WButton
        v-if="canEdit && !['closed', 'cancelled', ...OUT].includes(data.status)"
        variant="ghost"
        class="text-red"
        @click="((cancelReason = ''), (cancelOpen = true))"
      >
        <X class="size-[18px]" aria-hidden="true" />{{ t('reservations.drawer.actions.cancel') }}
      </WButton>
      <div class="ml-auto flex flex-wrap gap-2">
        <WButton
          v-if="
            canEdit &&
            ['draft', 'quote_sent', 'awaiting_deposit', 'confirmed', 'preparing'].includes(
              data.status,
            )
          "
          variant="secondary"
          icon
          :aria-label="t('reservations.drawer.actions.edit')"
          @click="editOpen = true"
        >
          <Pencil class="size-[18px]" aria-hidden="true" />
        </WButton>
        <WButton
          v-if="canEdit && data.status === 'draft'"
          variant="secondary"
          :loading="act.isPending.value"
          @click="run('status', 'quote_sent')"
          >{{ t('reservations.drawer.actions.quoteSent') }}</WButton
        >
        <WButton
          v-if="canEdit && ['draft', 'quote_sent'].includes(data.status)"
          :loading="act.isPending.value"
          @click="run('confirm')"
          >{{ t('reservations.drawer.actions.confirm') }}</WButton
        >
        <template v-if="canLogistics">
          <WButton
            v-for="target in nextSteps"
            :key="target"
            variant="secondary"
            :loading="act.isPending.value"
            @click="run('status', target)"
            >{{ t(`reservations.drawer.actions.${target}`) }}</WButton
          >
          <WButton
            v-if="hasEquipment && ['confirmed', 'preparing'].includes(data.status)"
            @click="openCheckout"
          >
            <Truck class="size-[18px]" aria-hidden="true" />{{
              t('reservations.drawer.actions.checkout')
            }}
          </WButton>
          <WButton v-if="OUT.includes(data.status) && hasEquipment" @click="openReturn">
            <Undo2 class="size-[18px]" aria-hidden="true" />{{
              t('reservations.drawer.actions.return')
            }}
          </WButton>
        </template>
      </div>
    </template>
  </WDrawer>

  <ReservationWizard v-if="data" v-model:open="editOpen" :reservation="data" />

  <!-- Checkout -->
  <WModal
    v-model:open="checkoutOpen"
    :title="t('reservations.checkout.title')"
    :description="t('reservations.checkout.text')"
    size="md"
  >
    <ul class="flex flex-col gap-2">
      <li v-for="line in equipment" :key="line.id" class="flex items-center gap-3">
        <span class="min-w-0 flex-1">
          <span class="block font-semibold">{{ line.label }}</span>
          <span class="text-[12px] text-muted"
            >{{ t('reservations.checkout.planned', { count: line.quantity }) }} ·
            {{ t(`reservations.lineKinds.${line.kind}`) }}</span
          >
        </span>
        <input
          v-model.number="outCounts[line.id!]"
          type="number"
          min="0"
          :max="line.quantity"
          class="num h-9 w-24 rounded-[8px] border border-line-2 bg-surface px-2 text-right"
          :aria-label="line.label"
        />
      </li>
    </ul>
    <template #footer>
      <WButton variant="secondary" @click="checkoutOpen = false">{{ t('common.cancel') }}</WButton>
      <WButton :loading="checkout.isPending.value" @click="confirmCheckout">{{
        t('reservations.checkout.save')
      }}</WButton>
    </template>
  </WModal>

  <!-- Return -->
  <WModal
    v-model:open="returnOpen"
    :title="t('reservations.return.title')"
    :description="t('reservations.return.text')"
    size="lg"
  >
    <div class="overflow-x-auto">
      <table class="w-full min-w-[520px] text-[13.5px]">
        <thead>
          <tr class="text-left text-[12px] font-bold text-muted">
            <th class="py-1.5">{{ t('stock.columns.item') }}</th>
            <th class="py-1.5 text-right">{{ t('reservations.return.returned') }}</th>
            <th class="py-1.5 text-right">{{ t('reservations.return.damaged') }}</th>
            <th class="py-1.5 text-right">{{ t('reservations.return.missing') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="line in returnable" :key="line.id" class="border-t border-line">
            <td class="py-2">
              <span class="block font-semibold">{{ line.label }}</span>
              <span
                class="text-[12px]"
                :class="mismatch(line) ? 'font-bold text-red' : 'text-muted'"
                >{{
                  mismatch(line)
                    ? t('reservations.return.mismatch', { count: line.quantityOut })
                    : t('reservations.return.out', { count: line.quantityOut })
                }}</span
              >
            </td>
            <td
              v-for="field in ['returned', 'damaged', 'missing'] as const"
              :key="field"
              class="py-2 text-right"
            >
              <input
                v-model.number="returned[line.id!]![field]"
                type="number"
                min="0"
                :disabled="line.kind === 'pack' && field !== 'returned'"
                class="num h-9 w-20 rounded-[8px] border border-line-2 bg-surface px-2 text-right disabled:opacity-40"
                :aria-label="`${t(`reservations.return.${field}`)} : ${line.label}`"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <template #footer>
      <WButton variant="secondary" @click="returnOpen = false">{{ t('common.cancel') }}</WButton>
      <WButton
        :loading="doReturn.isPending.value"
        :disabled="returnable.some(mismatch)"
        @click="confirmReturn"
        >{{ t('reservations.return.save') }}</WButton
      >
    </template>
  </WModal>

  <!-- Payment or caution -->
  <WModal
    v-model:open="paymentOpen"
    :title="
      paymentKind === 'security'
        ? t('reservations.payment.securityTitle')
        : t('reservations.payment.title')
    "
    :description="
      paymentKind === 'payment' && data
        ? t('reservations.payment.balance', { amount: money(data.balance) })
        : undefined
    "
    size="sm"
  >
    <div class="flex flex-col gap-4">
      <WInput
        v-model.number="payment.amount"
        type="number"
        min="1"
        :label="t('reservations.payment.amount')"
      />
      <WSelect
        v-model="payment.method"
        :label="t('reservations.payment.method')"
        :options="methodOptions"
      />
      <WInput v-model="payment.paidAt" type="date" :label="t('reservations.payment.paidAt')" />
      <WInput v-model="payment.reference" :label="t('reservations.payment.reference')" />
    </div>
    <template #footer>
      <WButton variant="secondary" @click="paymentOpen = false">{{ t('common.cancel') }}</WButton>
      <WButton :loading="pay.isPending.value" @click="confirmPayment">{{
        t('reservations.payment.save')
      }}</WButton>
    </template>
  </WModal>

  <!-- Caution back -->
  <WModal v-model:open="settleOpen" :title="t('reservations.payment.settleTitle')" size="sm">
    <div class="flex flex-col gap-4">
      <WInput
        v-model.number="settle.retained"
        type="number"
        min="0"
        :label="t('reservations.payment.retained')"
        :hint="t('reservations.payment.retainedHint')"
      />
      <WInput
        v-if="settle.retained > 0"
        v-model="settle.reason"
        :label="t('reservations.payment.reason')"
      />
      <WSelect
        v-model="settle.method"
        :label="t('reservations.payment.method')"
        :options="methodOptions"
      />
    </div>
    <template #footer>
      <WButton variant="secondary" @click="settleOpen = false">{{ t('common.cancel') }}</WButton>
      <WButton :loading="doSettle.isPending.value" @click="confirmSettle">{{
        t('reservations.payment.save')
      }}</WButton>
    </template>
  </WModal>

  <!-- Cancel -->
  <WModal
    v-model:open="cancelOpen"
    :title="t('reservations.cancel.title')"
    :description="t('reservations.cancel.text')"
    size="sm"
  >
    <WInput v-model="cancelReason" :label="t('reservations.cancel.reason')" required />
    <template #footer>
      <WButton variant="secondary" @click="cancelOpen = false">{{ t('common.cancel') }}</WButton>
      <WButton
        variant="danger"
        :loading="doCancel.isPending.value"
        :disabled="!cancelReason.trim()"
        @click="confirmCancel"
        >{{ t('reservations.cancel.save') }}</WButton
      >
    </template>
  </WModal>
</template>

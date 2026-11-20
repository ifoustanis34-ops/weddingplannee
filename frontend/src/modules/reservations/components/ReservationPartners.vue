<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { FileDown, Handshake, Undo2 } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { api } from '@/api/client'
import { toApiError } from '@/api/errors'
import { formatMoney } from '@/composables/useMoney'
import { useToast } from '@/composables/useToast'
import WhatsAppButton from '@/components/WhatsAppButton.vue'
import { WButton, WInput } from '@/design'

import { reservationKeys, reservationsApi, useReservationMutation } from '../api'
import type { PartnerOffer, Reservation, ReservationLine, Shortage } from '../types'

/**
 * Equipment lent by partners (feedback 14/11/2026): when our stock is short over the period,
 * the partners who can complete; the parts already taken from them; one order per partner.
 */
const props = defineProps<{ reservation: Reservation; canEdit: boolean }>()
const { t } = useI18n()
const toast = useToast()

const EDITABLE = ['draft', 'quote_sent', 'awaiting_deposit', 'confirmed', 'preparing']
const editable = computed(() => props.canEdit && EDITABLE.includes(props.reservation.status))
const id = computed(() => props.reservation.id)

const shortages = useQuery({
  queryKey: computed(() => reservationKeys.shortages(id.value)),
  queryFn: () => reservationsApi.shortages(id.value),
  enabled: editable,
})
const partnerLines = computed(() =>
  props.reservation.lines.filter((line) => (line.partnerQuantity ?? 0) > 0),
)
const orders = useQuery({
  queryKey: computed(() => [
    ...reservationKeys.partnerOrders(id.value),
    partnerLines.value.map((l) => `${l.id}:${l.partnerQuantity}`).join(','),
  ]),
  queryFn: () => reservationsApi.partnerOrders(id.value),
  enabled: computed(() => partnerLines.value.length > 0),
})

// Quantity typed for each offer, proposed: what is missing, within what the partner has.
const amounts = ref<Record<string, number>>({})
watch(
  () => shortages.data.value,
  (rows) => {
    const next: Record<string, number> = {}
    for (const shortage of rows ?? [])
      for (const offer of shortage.partners)
        next[key(shortage, offer)] = Math.min(shortage.needed - shortage.available, offer.free)
    amounts.value = next
  },
  { immediate: true },
)
const key = (shortage: Shortage, offer: PartnerOffer) => `${shortage.item}:${offer.supply}`

const assign = useReservationMutation(
  (args: { line: string; supply: string | null; quantity: number }) =>
    reservationsApi.assignPartner(id.value, args.line, args.supply, args.quantity),
)

async function take(shortage: Shortage, offer: PartnerOffer): Promise<void> {
  if (!shortage.line) return
  const wanted = amounts.value[key(shortage, offer)] ?? 0
  if (wanted <= 0) return
  const line = props.reservation.lines.find((l) => l.id === shortage.line)
  // Same partner: add to its part; another partner: it replaces the previous one.
  const already = line?.partnerSupply === offer.supply ? (line.partnerQuantity ?? 0) : 0
  try {
    await assign.mutateAsync({
      line: shortage.line,
      supply: offer.supply,
      quantity: already + wanted,
    })
    toast.success(
      t('reservations.drawer.partners.taken', {
        count: wanted,
        item: shortage.name,
        name: offer.vendorName,
      }),
    )
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}

async function giveBack(line: ReservationLine): Promise<void> {
  if (!line.id) return
  try {
    await assign.mutateAsync({ line: line.id, supply: null, quantity: 0 })
    toast.success(t('reservations.drawer.partners.removed', { item: line.label }))
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}

function orderBlob(vendor: string): Promise<Blob> {
  return api
    .get<Blob>(`/reservations/${id.value}/document`, {
      params: { type: 'partner', vendor },
      responseType: 'blob',
    })
    .then((r) => r.data)
}
async function openOrder(vendor: string): Promise<void> {
  try {
    const url = URL.createObjectURL(await orderBlob(vendor))
    window.open(url, '_blank', 'noopener')
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}

const visible = computed(
  () => (shortages.data.value?.length ?? 0) > 0 || partnerLines.value.length > 0,
)
</script>

<template>
  <section v-if="visible" class="flex flex-col gap-3">
    <h3 class="flex items-center gap-2">
      <Handshake class="size-[18px] text-violet" aria-hidden="true" />{{
        t('reservations.drawer.partners.title')
      }}
    </h3>

    <!-- Shortages: who can complete -->
    <div
      v-if="editable && shortages.data.value?.length"
      class="flex flex-col gap-3 rounded-wd border border-red/40 bg-red-soft/40 p-3"
      role="alert"
    >
      <p class="text-[13.5px] text-ink-2">{{ t('reservations.drawer.partners.intro') }}</p>
      <div
        v-for="shortage in shortages.data.value"
        :key="shortage.item"
        class="flex flex-col gap-2"
      >
        <p class="text-[13.5px] font-bold text-red">
          {{
            t('reservations.drawer.partners.missing', {
              name: shortage.name,
              missing: shortage.needed - shortage.available,
              available: shortage.available,
            })
          }}
        </p>
        <p v-if="!shortage.partners.length" class="text-[13px] text-muted">
          {{ t('reservations.drawer.partners.none') }}
        </p>
        <div
          v-for="offer in shortage.partners"
          :key="offer.supply"
          class="flex flex-wrap items-end gap-2 rounded-wd bg-surface p-2.5"
        >
          <div class="min-w-0 flex-1 basis-[160px]">
            <p class="font-semibold">{{ offer.vendorName }}</p>
            <p class="text-[12.5px] text-muted">
              {{ t('reservations.drawer.partners.free', { count: offer.free }) }}
              <template v-if="offer.unitCost !== null">
                ·
                {{
                  t('reservations.drawer.partners.cost', { amount: formatMoney(offer.unitCost) })
                }}
              </template>
            </p>
          </div>
          <WInput
            v-model.number="amounts[key(shortage, offer)]"
            class="w-24"
            type="number"
            min="1"
            :max="offer.free"
            inputmode="numeric"
            :label="t('reservations.drawer.partners.quantity', { name: offer.vendorName })"
            hide-label
          />
          <WButton
            size="sm"
            :loading="assign.isPending.value"
            :disabled="!offer.free || !((amounts[key(shortage, offer)] ?? 0) > 0)"
            @click="take(shortage, offer)"
            >{{ t('reservations.drawer.partners.take', { name: offer.vendorName }) }}</WButton
          >
        </div>
      </div>
    </div>

    <!-- Parts already taken from partners -->
    <ul v-if="partnerLines.length" class="flex flex-col gap-1.5 text-[13.5px]">
      <li
        v-for="line in partnerLines"
        :key="line.id"
        class="flex flex-wrap items-center gap-2 rounded-wd border border-line px-3 py-2"
      >
        <span class="min-w-0 flex-1">
          <span class="font-semibold">{{ line.label }}</span>
          <span class="text-muted">
            ·
            {{
              t('reservations.drawer.partnerPart', {
                count: line.partnerQuantity,
                name: line.partnerName,
              })
            }}</span
          >
        </span>
        <WButton
          v-if="editable"
          size="sm"
          variant="ghost"
          :title="t('reservations.drawer.partners.removeTitle')"
          :loading="assign.isPending.value"
          @click="giveBack(line)"
          ><Undo2 class="size-[15px]" aria-hidden="true" />{{
            t('reservations.drawer.partners.removeTitle')
          }}</WButton
        >
      </li>
    </ul>

    <!-- One order per partner -->
    <div v-if="orders.data.value?.length" class="flex flex-col gap-1.5">
      <p class="text-[12.5px] font-bold text-muted">
        {{ t('reservations.drawer.partners.orders') }}
      </p>
      <div class="flex flex-wrap gap-2">
        <span v-for="order in orders.data.value" :key="order.vendor" class="inline-flex gap-1">
          <WButton size="sm" variant="secondary" @click="openOrder(order.vendor)">
            <FileDown class="size-[15px]" aria-hidden="true" />{{
              t('reservations.drawer.partners.order', { name: order.vendorName })
            }}
            <span class="font-normal text-muted">
              ·
              {{
                order.total !== null
                  ? t('reservations.drawer.partners.orderTotal', {
                      count: order.lines.reduce((sum, l) => sum + l.quantity, 0),
                      amount: formatMoney(order.total),
                    })
                  : t('reservations.drawer.partners.orderCount', {
                      count: order.lines.reduce((sum, l) => sum + l.quantity, 0),
                    })
              }}</span
            >
          </WButton>
          <WhatsAppButton
            icon
            :phone="order.phone"
            :message="
              t('whatsapp.orderMessage', {
                name: order.contact || order.vendorName,
                number: reservation.number,
              })
            "
            :file="() => orderBlob(order.vendor)"
            :filename="`${reservation.number}-commande-${order.vendorName}.pdf`"
            :label="t('whatsapp.order', { name: order.vendorName })"
          />
        </span>
      </div>
    </div>
  </section>
</template>

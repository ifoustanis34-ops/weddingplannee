<script setup lang="ts">
import { Archive, ArchiveRestore, FileText, Mail, Pencil, Phone, Trash2 } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { formatDate } from '@/composables/useDate'
import { formatMoney } from '@/composables/useMoney'
import { usePermissions } from '@/composables/usePermissions'
import { useToast } from '@/composables/useToast'
import { WAvatar, WBadge, WButton, WDrawer, WEmptyState, WModal } from '@/design'

import { STATUS_TONES } from '@/modules/reservations/constants'
import type { ReservationStatus } from '@/modules/reservations/types'

import { useClient, useClientHistory, useDeleteClient, useUpdateClient } from '../api'
import ClientFormModal from './ClientFormModal.vue'

/** Client sheet (reservations-stock.md §4.4): contact, indicators, everything ordered. */
const props = defineProps<{ clientId: string | null }>()
const emit = defineEmits<{ close: [] }>()
const { t } = useI18n()
const toast = useToast()
const { can } = usePermissions()

const open = computed({
  get: () => props.clientId !== null,
  set: (value) => {
    if (!value) emit('close')
  },
})
const id = computed(() => props.clientId)
const client = useClient(id)
const history = useClientHistory(id)
const update = useUpdateClient()
const remove = useDeleteClient()

const canEdit = computed(() => can('editSales'))
const canDelete = computed(() => can('deleteSales'))
const seesMoney = computed(() => can('viewFinance'))
const editOpen = ref(false)
const deleteOpen = ref(false)

/** Not an order yet (or no longer): nothing is due. */
const UNSOLD: ReservationStatus[] = ['draft', 'quote_sent', 'cancelled']
const money = (value: number | null) => (value === null ? '—' : formatMoney(value))
const hasHistory = computed(() => {
  const h = history.data.value
  return Boolean(
    h && (h.reservations.length || h.quotes.length || h.contracts.length || h.payments.length),
  )
})

async function toggleArchive(): Promise<void> {
  const current = client.data.value
  if (!current) return
  try {
    await update.mutateAsync({ id: current.id, input: { isArchived: !current.isArchived } })
    toast.success(
      current.isArchived ? t('clients.drawer.unarchivedDone') : t('clients.drawer.archivedDone'),
    )
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}

async function confirmDelete(): Promise<void> {
  const current = client.data.value
  if (!current) return
  try {
    await remove.mutateAsync(current.id)
    deleteOpen.value = false
    toast.success(t('clients.drawer.deleted'))
    emit('close')
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
</script>

<template>
  <WDrawer
    v-model:open="open"
    :title="client.data.value?.name ?? t('common.loading')"
    :subtitle="client.data.value?.company"
  >
    <template v-if="client.data.value" #heading="{ titleId }">
      <div class="flex items-center gap-3">
        <WAvatar :name="client.data.value.name" :size="44" />
        <div class="min-w-0">
          <h2 :id="titleId" class="truncate text-[17px] font-semibold">
            {{ client.data.value.name }}
          </h2>
          <p class="mt-1 flex flex-wrap items-center gap-1.5 text-[13px] text-muted">
            <span v-if="client.data.value.company">{{ client.data.value.company }}</span>
            <WBadge v-if="client.data.value.isArchived" tone="grey">{{
              t('clients.archivedBadge')
            }}</WBadge>
          </p>
        </div>
      </div>
    </template>

    <div
      v-if="client.isPending.value"
      class="flex flex-col gap-3"
      :aria-label="t('common.loading')"
    >
      <div v-for="n in 4" :key="n" class="skeleton h-10" />
    </div>

    <WEmptyState
      v-else-if="client.isError.value || !client.data.value"
      :title="t('clients.drawer.notFound')"
    />

    <template v-else>
      <p v-if="!canEdit" class="rounded-wd bg-surface-2 px-3 py-2 text-[13px] text-ink-2">
        {{ t('clients.drawer.readOnly') }}
      </p>
      <p
        v-if="client.data.value.isArchived"
        class="rounded-wd bg-surface-2 px-3 py-2 text-[13px] text-ink-2"
      >
        {{ t('clients.drawer.archivedNotice') }}
      </p>

      <!-- Indicators -->
      <section>
        <h3 class="sr-only">{{ t('clients.drawer.indicators') }}</h3>
        <dl class="grid grid-cols-2 gap-3">
          <div class="rounded-wd border border-line p-3">
            <dt class="text-[12.5px] font-semibold text-muted">{{ t('clients.drawer.orders') }}</dt>
            <dd class="num mt-0.5 font-display text-[20px] font-semibold">
              {{ client.data.value.orderCount }}
            </dd>
          </div>
          <div class="rounded-wd border border-line p-3">
            <dt class="text-[12.5px] font-semibold text-muted">
              {{ t('clients.drawer.lastOrder') }}
            </dt>
            <dd class="mt-0.5 font-semibold">
              {{
                client.data.value.lastOrderAt
                  ? formatDate(client.data.value.lastOrderAt)
                  : t('clients.drawer.never')
              }}
            </dd>
          </div>
          <template v-if="seesMoney">
            <div class="rounded-wd border border-line p-3">
              <dt class="text-[12.5px] font-semibold text-muted">
                {{ t('clients.drawer.revenue') }}
              </dt>
              <dd class="num mt-0.5 font-semibold">{{ money(client.data.value.revenue) }}</dd>
            </div>
            <div class="rounded-wd border border-line p-3">
              <dt class="text-[12.5px] font-semibold text-muted">
                {{ t('clients.drawer.balance') }}
              </dt>
              <dd
                class="num mt-0.5 font-semibold"
                :class="(client.data.value.balanceDue ?? 0) > 0 && 'text-coral'"
              >
                {{ money(client.data.value.balanceDue) }}
              </dd>
            </div>
          </template>
        </dl>
      </section>

      <!-- Contact -->
      <section>
        <h3>{{ t('clients.drawer.contact') }}</h3>
        <dl class="mt-2 grid grid-cols-2 gap-x-4 gap-y-3.5">
          <div>
            <dt class="text-[12.5px] font-semibold text-muted">{{ t('clients.fields.phone') }}</dt>
            <dd class="num mt-0.5 font-semibold">{{ client.data.value.phone || '—' }}</dd>
          </div>
          <div>
            <dt class="text-[12.5px] font-semibold text-muted">
              {{ t('clients.fields.phoneAlt') }}
            </dt>
            <dd class="num mt-0.5 font-semibold">{{ client.data.value.phoneAlt || '—' }}</dd>
          </div>
          <div class="col-span-2">
            <dt class="text-[12.5px] font-semibold text-muted">{{ t('clients.fields.email') }}</dt>
            <dd class="mt-0.5 font-semibold break-all">{{ client.data.value.email || '—' }}</dd>
          </div>
          <div class="col-span-2">
            <dt class="text-[12.5px] font-semibold text-muted">
              {{ t('clients.fields.address') }}
            </dt>
            <dd class="mt-0.5 font-semibold whitespace-pre-line">
              {{ client.data.value.address || '—' }}
            </dd>
          </div>
        </dl>
      </section>

      <section v-if="client.data.value.preferences">
        <h3>{{ t('clients.fields.preferences') }}</h3>
        <p class="mt-1 whitespace-pre-line text-ink-2">{{ client.data.value.preferences }}</p>
      </section>
      <section v-if="client.data.value.notes">
        <h3>{{ t('clients.fields.notes') }}</h3>
        <p class="mt-1 whitespace-pre-line text-ink-2">{{ client.data.value.notes }}</p>
      </section>

      <div v-if="client.data.value.email || canEdit" class="flex flex-wrap gap-2">
        <a
          v-if="client.data.value.email"
          :href="`mailto:${client.data.value.email}`"
          class="inline-flex h-8 items-center gap-2 rounded-[8px] border border-line-2 bg-surface px-[11px] text-[13px] font-bold hover:bg-surface-2"
        >
          <Mail class="size-[15px]" aria-hidden="true" />{{ t('clients.drawer.email') }}
        </a>
        <WButton v-if="canEdit" size="sm" variant="secondary" @click="editOpen = true">
          <Pencil class="size-[15px]" aria-hidden="true" />{{ t('clients.drawer.edit') }}
        </WButton>
        <WButton
          v-if="canEdit"
          size="sm"
          variant="secondary"
          :loading="update.isPending.value"
          @click="toggleArchive"
        >
          <component
            :is="client.data.value.isArchived ? ArchiveRestore : Archive"
            class="size-[15px]"
            aria-hidden="true"
          />{{
            client.data.value.isArchived
              ? t('clients.drawer.unarchive')
              : t('clients.drawer.archive')
          }}
        </WButton>
      </div>

      <!-- History -->
      <section class="flex flex-col gap-3">
        <h3>{{ t('clients.drawer.history') }}</h3>
        <div v-if="history.isPending.value" class="skeleton h-16" />
        <p v-else-if="!hasHistory" class="text-muted">{{ t('clients.drawer.historyEmpty') }}</p>
        <template v-else-if="history.data.value">
          <div v-if="history.data.value.reservations.length">
            <h4 class="text-[13px] font-bold text-muted">{{ t('clients.drawer.reservations') }}</h4>
            <ul class="mt-1.5 divide-y divide-line rounded-wd border border-line">
              <li v-for="reservation in history.data.value.reservations" :key="reservation.id">
                <RouterLink
                  :to="{ name: 'reservations', query: { reservation: reservation.id } }"
                  class="flex items-center justify-between gap-3 px-3 py-2.5 hover:bg-surface-2"
                >
                  <span class="min-w-0">
                    <span class="block truncate font-semibold"
                      >{{ reservation.number }} · {{ reservation.title }}</span
                    >
                    <span class="flex items-center gap-2 text-[12.5px] text-muted"
                      >{{ formatDate(reservation.eventStart) }}
                      <WBadge :tone="STATUS_TONES[reservation.status]">{{
                        t(`reservations.statuses.${reservation.status}`)
                      }}</WBadge></span
                    >
                  </span>
                  <span v-if="reservation.total !== null" class="shrink-0 text-right">
                    <span class="num block font-semibold">{{
                      formatMoney(reservation.total)
                    }}</span>
                    <span
                      v-if="reservation.balance && !UNSOLD.includes(reservation.status)"
                      class="num block text-[12px] font-semibold text-coral"
                      >{{
                        t('clients.drawer.remaining', { amount: formatMoney(reservation.balance) })
                      }}</span
                    >
                  </span>
                </RouterLink>
              </li>
            </ul>
          </div>
          <div v-if="history.data.value.contracts.length">
            <h4 class="text-[13px] font-bold text-muted">{{ t('clients.drawer.contracts') }}</h4>
            <ul class="mt-1.5 divide-y divide-line rounded-wd border border-line">
              <li
                v-for="contract in history.data.value.contracts"
                :key="contract.id"
                class="flex items-center justify-between gap-3 px-3 py-2.5"
              >
                <span class="min-w-0">
                  <span class="block font-semibold">{{ contract.number }}</span>
                  <span class="block text-[12.5px] text-muted">{{
                    formatDate(contract.signedAt)
                  }}</span>
                </span>
                <span v-if="contract.total !== null" class="num font-semibold">{{
                  formatMoney(contract.total)
                }}</span>
              </li>
            </ul>
          </div>
          <div v-if="history.data.value.quotes.length">
            <h4 class="text-[13px] font-bold text-muted">{{ t('clients.drawer.quotes') }}</h4>
            <ul class="mt-1.5 divide-y divide-line rounded-wd border border-line">
              <li v-for="quote in history.data.value.quotes" :key="quote.id">
                <RouterLink
                  :to="{ name: 'quote-edit', params: { id: quote.id } }"
                  class="flex items-center justify-between gap-3 px-3 py-2.5 hover:bg-surface-2"
                >
                  <span class="min-w-0">
                    <span class="block font-semibold">{{ quote.number }}</span>
                    <span class="block text-[12.5px] text-muted"
                      >{{ formatDate(quote.issueDate) }} ·
                      {{ t(`quotes.statuses.${quote.status}`) }}</span
                    >
                  </span>
                  <span v-if="quote.total !== null" class="num font-semibold">{{
                    formatMoney(quote.total)
                  }}</span>
                </RouterLink>
              </li>
            </ul>
          </div>
          <div v-if="history.data.value.payments.length">
            <h4 class="text-[13px] font-bold text-muted">{{ t('clients.drawer.payments') }}</h4>
            <ul class="mt-1.5 divide-y divide-line rounded-wd border border-line">
              <li
                v-for="payment in history.data.value.payments"
                :key="payment.id"
                class="flex items-center justify-between gap-3 px-3 py-2.5"
                :class="payment.isCancelled && 'text-muted line-through'"
              >
                <span class="min-w-0">
                  <span class="block font-semibold">{{ formatDate(payment.paidAt) }}</span>
                  <span class="block text-[12.5px] text-muted"
                    >{{ payment.reference
                    }}<template v-if="payment.kind !== 'payment'">
                      · {{ t(`clients.drawer.paymentKinds.${payment.kind}`) }}</template
                    ><template v-if="payment.isCancelled">
                      · {{ t('clients.drawer.cancelled') }}</template
                    ></span
                  >
                </span>
                <span class="num font-semibold">{{ formatMoney(payment.amount) }}</span>
              </li>
            </ul>
          </div>
        </template>
      </section>
    </template>

    <template v-if="client.data.value" #footer>
      <WButton
        v-if="canDelete"
        variant="ghost"
        icon
        class="text-red"
        :aria-label="t('clients.drawer.delete')"
        @click="deleteOpen = true"
      >
        <Trash2 class="size-[18px]" aria-hidden="true" />
      </WButton>
      <div class="ml-auto flex flex-wrap gap-2">
        <a
          v-if="client.data.value.phone"
          :href="`tel:${client.data.value.phone.replace(/\s/g, '')}`"
          class="inline-flex h-10 items-center gap-2 rounded-[10px] border border-line-2 bg-surface px-4 text-[14px] font-bold hover:bg-surface-2"
        >
          <Phone class="size-[18px]" aria-hidden="true" />{{ t('clients.drawer.call') }}
        </a>
        <WButton
          v-if="canEdit"
          :to="{ name: 'quote-new', query: { client: client.data.value.id } }"
        >
          <FileText class="size-[18px]" aria-hidden="true" />{{ t('clients.drawer.createQuote') }}
        </WButton>
      </div>
    </template>
  </WDrawer>

  <ClientFormModal v-model:open="editOpen" :client="client.data.value" />
  <WModal v-model:open="deleteOpen" :title="t('clients.drawer.delete')" size="sm">
    <p>{{ t('clients.drawer.deleteConfirm', { name: client.data.value?.name ?? '' }) }}</p>
    <template #footer>
      <WButton variant="secondary" @click="deleteOpen = false">{{ t('common.cancel') }}</WButton>
      <WButton variant="danger" :loading="remove.isPending.value" @click="confirmDelete">{{
        t('common.delete')
      }}</WButton>
    </template>
  </WModal>
</template>

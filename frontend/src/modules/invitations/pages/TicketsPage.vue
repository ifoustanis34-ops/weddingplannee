<script setup lang="ts">
import {
  ArrowLeft,
  Ban,
  Copy,
  FileDown,
  FileUp,
  MessageCircle,
  Pencil,
  Plus,
  RotateCcw,
  Ticket as TicketIcon,
  Trash2,
} from '@lucide/vue'
import { computed, onBeforeUnmount, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import { toApiError } from '@/api/errors'
import { usePermissions } from '@/composables/usePermissions'
import { useToast } from '@/composables/useToast'
import { type BadgeTone, WBadge, WButton, WCard, WEmptyState, WModal, WProgress } from '@/design'
import { useWedding } from '@/modules/events/api'

import { ticketsApi, useGuests, useTicketAction, useTicketDesign } from '../api'
import GuestModal from '../components/GuestModal.vue'
import TicketDesignCard from '../components/TicketDesignCard.vue'
import type { Guest, TicketBatch, TicketState } from '../types'

/** « Billets » of a wedding (docs/specs/devis-billets.md §6). */
const { t } = useI18n()
const route = useRoute()
const toast = useToast()
const { can } = usePermissions()
const canEdit = computed(() => can('editWeddings'))

const weddingId = computed(() => String(route.params.id))
const wedding = useWedding(weddingId)
const design = useTicketDesign(weddingId)
const guests = useGuests(weddingId)

const STATE_TONES: Record<TicketState, BadgeTone> = {
  none: 'grey',
  generated: 'violet',
  sent: 'fuchsia',
  opened: 'gold',
  confirmed: 'green',
  declined: 'coral',
  cancelled: 'red',
}

const search = ref('')
const rows = computed(() => {
  const term = search.value.trim().toLowerCase()
  const list = guests.data.value ?? []
  return term
    ? list.filter((g) => `${g.name} ${g.category} ${g.table}`.toLowerCase().includes(term))
    : list
})
const totals = computed(() => {
  const list = guests.data.value ?? []
  return {
    guests: list.length,
    seats: list.reduce((sum, g) => sum + g.seats, 0),
    generated: list.filter((g) => g.ticket?.hasDocument).length,
    confirmed: list.filter((g) => g.rsvpStatus === 'accepted').length,
  }
})

// --- Selection -------------------------------------------------------------------------------
const selected = ref<Set<string>>(new Set())
const allSelected = computed(
  () => rows.value.length > 0 && rows.value.every((g) => selected.value.has(g.id)),
)
function toggle(id: string): void {
  const next = new Set(selected.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selected.value = next
}
function toggleAll(): void {
  selected.value = allSelected.value ? new Set() : new Set(rows.value.map((g) => g.id))
}

// --- Batch generation with progress -----------------------------------------------------------
const batch = ref<TicketBatch | null>(null)
let poll: ReturnType<typeof setInterval> | undefined
const batchPercent = computed(() =>
  batch.value && batch.value.total
    ? Math.round((100 * (batch.value.done + batch.value.failed)) / batch.value.total)
    : 0,
)

async function generate(input: { guests?: string[]; all?: boolean }): Promise<void> {
  try {
    batch.value = await ticketsApi.generate(weddingId.value, input)
    clearInterval(poll)
    poll = setInterval(followBatch, 1000)
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
async function followBatch(): Promise<void> {
  if (!batch.value) return
  try {
    batch.value = await ticketsApi.batch(batch.value.batch)
  } catch {
    return
  }
  if (batch.value.status === 'done') {
    clearInterval(poll)
    const { done, failed } = batch.value
    if (failed) toast.error(t('tickets.batch.failed', { done, failed }))
    else toast.success(t('tickets.batch.done', { count: done }, done))
    selected.value = new Set()
    void guests.refetch()
  }
}
onBeforeUnmount(() => clearInterval(poll))

// --- Downloads --------------------------------------------------------------------------------
const exporting = ref<'pdf' | 'zip' | null>(null)
function download(blob: Blob, name: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = name
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
async function exportAll(type: 'pdf' | 'zip'): Promise<void> {
  exporting.value = type
  try {
    download(await ticketsApi.export(weddingId.value, type), `billets.${type}`)
  } catch (error) {
    toast.error(toApiError(error).message)
  } finally {
    exporting.value = null
  }
}
async function downloadOne(guest: Guest): Promise<void> {
  if (!guest.ticket) return
  try {
    download(await ticketsApi.pdf(guest.ticket.id), `${guest.ticket.code}.pdf`)
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}

// --- Links and WhatsApp (manual message, never sent automatically) -----------------------------
async function copy(text: string, done: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text)
    toast.success(done)
  } catch {
    toast.info(text)
  }
}
function whatsappMessage(guest: Guest): string {
  const couple = [design.data.value?.partner1, design.data.value?.partner2]
    .filter(Boolean)
    .join(' & ')
  return t('tickets.whatsapp', { name: guest.name, couple, url: guest.ticket?.url ?? '' })
}

// --- Cancel, reissue, delete ------------------------------------------------------------------
const cancel = useTicketAction((id: string) => ticketsApi.cancel(id))
const reissue = useTicketAction((id: string) => ticketsApi.reissue(id))
const remove = useTicketAction((id: string) => ticketsApi.removeGuest(id))
const confirm = ref<{ kind: 'cancel' | 'reissue' | 'remove'; guest: Guest } | null>(null)
const confirmOpen = computed({
  get: () => confirm.value !== null,
  set: (open: boolean) => {
    if (!open) confirm.value = null
  },
})
async function confirmAction(): Promise<void> {
  const current = confirm.value
  if (!current) return
  try {
    if (current.kind === 'cancel' && current.guest.ticket) {
      await cancel.mutateAsync(current.guest.ticket.id)
      toast.success(t('tickets.cancelled', { code: current.guest.ticket.code }))
    } else if (current.kind === 'reissue') {
      const ticketId = current.guest.lastTicketId
      if (!ticketId) return
      const fresh = await reissue.mutateAsync(ticketId)
      toast.success(t('tickets.reissued', { code: fresh.code }))
    } else if (current.kind === 'remove') {
      await remove.mutateAsync(current.guest.id)
      toast.success(t('tickets.guests.removed', { name: current.guest.name }))
    }
    confirm.value = null
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}

// --- Guest modal and import -------------------------------------------------------------------
const guestOpen = ref(false)
const editing = ref<Guest | null>(null)
function openGuest(guest: Guest | null): void {
  editing.value = guest
  guestOpen.value = true
}
const importing = ref(false)
async function onImport(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  importing.value = true
  try {
    const result = await ticketsApi.importGuests(weddingId.value, file)
    toast.success(t('tickets.import.done', { count: result.created }, result.created))
    if (result.skipped.length)
      toast.info(
        t('tickets.import.skipped', { count: result.skipped.length }, result.skipped.length),
      )
    void guests.refetch()
  } catch (error) {
    toast.error(toApiError(error).message)
  } finally {
    importing.value = false
  }
}
</script>

<template>
  <div class="flex flex-col gap-[22px]">
    <header class="flex flex-wrap items-end justify-between gap-3">
      <div class="min-w-0">
        <RouterLink
          :to="{ name: 'weddings' }"
          class="inline-flex items-center gap-1.5 text-[13px] font-bold text-muted hover:text-ink"
        >
          <ArrowLeft class="size-[15px]" aria-hidden="true" />{{ t('tickets.back') }}
        </RouterLink>
        <h1 class="mt-1">{{ t('tickets.title') }}</h1>
        <p class="text-muted">{{ wedding.data.value?.title ?? '' }}</p>
      </div>
      <dl class="flex flex-wrap gap-5 text-[13px]">
        <div>
          <dt class="text-muted">{{ t('tickets.totals.guests') }}</dt>
          <dd class="num text-[17px] font-semibold">{{ totals.guests }}</dd>
        </div>
        <div>
          <dt class="text-muted">{{ t('tickets.totals.seats') }}</dt>
          <dd class="num text-[17px] font-semibold">{{ totals.seats }}</dd>
        </div>
        <div>
          <dt class="text-muted">{{ t('tickets.totals.generated') }}</dt>
          <dd class="num text-[17px] font-semibold">{{ totals.generated }}</dd>
        </div>
        <div>
          <dt class="text-muted">{{ t('tickets.totals.confirmed') }}</dt>
          <dd class="num text-[17px] font-semibold">{{ totals.confirmed }}</dd>
        </div>
      </dl>
    </header>

    <TicketDesignCard :wedding-id="weddingId" :read-only="!canEdit" />

    <WCard :title="t('tickets.guests.title')" :subtitle="t('tickets.guests.subtitle')">
      <template #actions>
        <div v-if="canEdit" class="flex flex-wrap gap-2">
          <WButton size="sm" variant="secondary" @click="openGuest(null)">
            <Plus class="size-[15px]" aria-hidden="true" />{{ t('tickets.guests.add') }}
          </WButton>
          <label
            class="inline-flex h-8 cursor-pointer items-center gap-2 rounded-[8px] border border-line-2 bg-surface px-[11px] text-[13px] font-bold hover:bg-surface-2 has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-violet"
            :class="importing && 'pointer-events-none opacity-60'"
          >
            <FileUp class="size-[15px]" aria-hidden="true" />{{ t('tickets.import.button') }}
            <input type="file" accept=".csv,.xlsx" class="sr-only" @change="onImport" />
          </label>
          <WButton
            size="sm"
            :disabled="!totals.guests || batch?.status === 'running'"
            @click="generate({ all: true })"
          >
            <TicketIcon class="size-[15px]" aria-hidden="true" />{{ t('tickets.generateAll') }}
          </WButton>
        </div>
      </template>

      <div
        v-if="batch"
        class="mb-4 rounded-wd border border-line p-3"
        role="status"
        aria-live="polite"
      >
        <div class="mb-2 flex justify-between text-[13px]">
          <span class="font-bold">{{
            batch.status === 'done' ? t('tickets.batch.finished') : t('tickets.batch.running')
          }}</span>
          <span class="num">{{ batch.done + batch.failed }} / {{ batch.total }}</span>
        </div>
        <WProgress :value="batchPercent" :label="t('tickets.batch.running')" green-when-full />
      </div>

      <div class="mb-3 flex flex-wrap items-center gap-2">
        <input
          v-model="search"
          type="search"
          class="h-9 min-w-0 flex-1 rounded-[10px] border border-line-2 bg-surface px-3 focus:border-violet focus:outline-none"
          :placeholder="t('tickets.guests.search')"
          :aria-label="t('tickets.guests.search')"
        />
        <WButton
          v-if="canEdit && selected.size"
          size="sm"
          variant="secondary"
          :disabled="batch?.status === 'running'"
          @click="generate({ guests: [...selected] })"
        >
          <TicketIcon class="size-[15px]" aria-hidden="true" />{{
            t('tickets.generateSelection', { count: selected.size }, selected.size)
          }}
        </WButton>
        <WButton
          size="sm"
          variant="secondary"
          :loading="exporting === 'pdf'"
          :disabled="!totals.generated"
          @click="exportAll('pdf')"
        >
          <FileDown class="size-[15px]" aria-hidden="true" />{{ t('tickets.export.pdf') }}
        </WButton>
        <WButton
          size="sm"
          variant="secondary"
          :loading="exporting === 'zip'"
          :disabled="!totals.generated"
          @click="exportAll('zip')"
        >
          <FileDown class="size-[15px]" aria-hidden="true" />{{ t('tickets.export.zip') }}
        </WButton>
      </div>

      <div v-if="guests.isPending.value" class="skeleton h-40" />
      <div v-else-if="guests.isError.value" class="text-muted" role="alert">
        {{ t('tickets.guests.loadError') }}
        <WButton class="ml-2" size="sm" variant="secondary" @click="guests.refetch()">{{
          t('common.retry')
        }}</WButton>
      </div>
      <WEmptyState
        v-else-if="!totals.guests"
        :title="t('tickets.guests.emptyTitle')"
        :description="t('tickets.guests.emptyText')"
      />
      <div v-else class="-mx-5 overflow-x-auto">
        <table class="w-full min-w-[760px] text-left">
          <caption class="sr-only">
            {{
              t('tickets.guests.title')
            }}
          </caption>
          <thead>
            <tr class="border-b border-line text-[12.5px] text-muted">
              <th class="w-10 py-2 pl-5">
                <input
                  type="checkbox"
                  :checked="allSelected"
                  :aria-label="t('tickets.guests.selectAll')"
                  @change="toggleAll"
                />
              </th>
              <th class="py-2 font-semibold">{{ t('tickets.guests.name') }}</th>
              <th class="py-2 text-center font-semibold">{{ t('tickets.guests.seats') }}</th>
              <th class="py-2 font-semibold">{{ t('tickets.guests.category') }}</th>
              <th class="py-2 font-semibold">{{ t('tickets.guests.table') }}</th>
              <th class="py-2 font-semibold">{{ t('tickets.guests.ticket') }}</th>
              <th class="py-2 pr-5 text-right font-semibold">{{ t('tickets.guests.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-line">
            <tr v-for="guest in rows" :key="guest.id" data-testid="guest-row">
              <td class="py-2.5 pl-5">
                <input
                  type="checkbox"
                  :checked="selected.has(guest.id)"
                  :aria-label="t('tickets.guests.select', { name: guest.name })"
                  @change="toggle(guest.id)"
                />
              </td>
              <td class="py-2.5">
                <p class="font-bold">{{ guest.name }}</p>
                <p v-if="guest.email || guest.phone" class="text-[12.5px] text-muted">
                  {{ [guest.email, guest.phone].filter(Boolean).join(' · ') }}
                </p>
              </td>
              <td class="num py-2.5 text-center">{{ guest.seats }}</td>
              <td class="py-2.5">{{ guest.category || '—' }}</td>
              <td class="py-2.5">{{ guest.table || '—' }}</td>
              <td class="py-2.5">
                <WBadge :tone="STATE_TONES[guest.ticketState]">{{
                  t(`tickets.states.${guest.ticketState}`)
                }}</WBadge>
                <p v-if="guest.ticket" class="num mt-1 text-[12px] text-muted">
                  {{ guest.ticket.code }}
                </p>
              </td>
              <td class="py-2.5 pr-5">
                <div class="flex justify-end gap-1">
                  <template v-if="guest.ticket">
                    <WButton
                      icon
                      size="sm"
                      variant="ghost"
                      :aria-label="t('tickets.actions.download', { name: guest.name })"
                      :title="t('tickets.actions.downloadShort')"
                      @click="downloadOne(guest)"
                    >
                      <FileDown class="size-[15px]" aria-hidden="true" />
                    </WButton>
                    <WButton
                      v-if="guest.ticket.url"
                      icon
                      size="sm"
                      variant="ghost"
                      :aria-label="t('tickets.actions.copyLink', { name: guest.name })"
                      :title="t('tickets.actions.copyLinkShort')"
                      @click="copy(guest.ticket.url, t('tickets.linkCopied'))"
                    >
                      <Copy class="size-[15px]" aria-hidden="true" />
                    </WButton>
                    <WButton
                      v-if="guest.ticket.url"
                      icon
                      size="sm"
                      variant="ghost"
                      :aria-label="t('tickets.actions.whatsapp', { name: guest.name })"
                      :title="t('tickets.actions.whatsappShort')"
                      @click="copy(whatsappMessage(guest), t('tickets.whatsappCopied'))"
                    >
                      <MessageCircle class="size-[15px]" aria-hidden="true" />
                    </WButton>
                  </template>
                  <template v-if="canEdit">
                    <WButton
                      v-if="!guest.ticket?.hasDocument"
                      icon
                      size="sm"
                      variant="ghost"
                      :disabled="batch?.status === 'running'"
                      :aria-label="t('tickets.actions.generate', { name: guest.name })"
                      :title="t('tickets.actions.generateShort')"
                      @click="generate({ guests: [guest.id] })"
                    >
                      <TicketIcon class="size-[15px]" aria-hidden="true" />
                    </WButton>
                    <WButton
                      v-if="guest.ticket"
                      icon
                      size="sm"
                      variant="ghost"
                      :aria-label="t('tickets.actions.reissue', { name: guest.name })"
                      :title="t('tickets.actions.reissueShort')"
                      @click="confirm = { kind: 'reissue', guest }"
                    >
                      <RotateCcw class="size-[15px]" aria-hidden="true" />
                    </WButton>
                    <WButton
                      v-if="guest.ticket"
                      icon
                      size="sm"
                      variant="ghost"
                      :aria-label="t('tickets.actions.cancel', { name: guest.name })"
                      :title="t('tickets.actions.cancelShort')"
                      @click="confirm = { kind: 'cancel', guest }"
                    >
                      <Ban class="size-[15px]" aria-hidden="true" />
                    </WButton>
                    <WButton
                      v-if="guest.ticketState === 'cancelled' && guest.lastTicketId"
                      icon
                      size="sm"
                      variant="ghost"
                      :aria-label="t('tickets.actions.reissue', { name: guest.name })"
                      :title="t('tickets.actions.reissueShort')"
                      @click="confirm = { kind: 'reissue', guest }"
                    >
                      <RotateCcw class="size-[15px]" aria-hidden="true" />
                    </WButton>
                    <WButton
                      icon
                      size="sm"
                      variant="ghost"
                      :aria-label="t('tickets.actions.edit', { name: guest.name })"
                      :title="t('common.edit')"
                      @click="openGuest(guest)"
                    >
                      <Pencil class="size-[15px]" aria-hidden="true" />
                    </WButton>
                    <WButton
                      v-if="!guest.ticket?.sentAt"
                      icon
                      size="sm"
                      variant="ghost"
                      :aria-label="t('tickets.actions.remove', { name: guest.name })"
                      :title="t('common.delete')"
                      @click="confirm = { kind: 'remove', guest }"
                    >
                      <Trash2 class="size-[15px]" aria-hidden="true" />
                    </WButton>
                  </template>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </WCard>

    <GuestModal
      v-model:open="guestOpen"
      :wedding-id="weddingId"
      :guest="editing"
      :categories="design.data.value?.categories ?? []"
    />

    <WModal
      v-model:open="confirmOpen"
      :title="confirm ? t(`tickets.confirm.${confirm.kind}.title`) : ''"
      size="sm"
    >
      <p v-if="confirm">
        {{ t(`tickets.confirm.${confirm.kind}.text`, { name: confirm.guest.name }) }}
      </p>
      <template #footer>
        <WButton variant="secondary" @click="confirmOpen = false">{{ t('common.cancel') }}</WButton>
        <WButton
          :variant="confirm?.kind === 'reissue' ? 'primary' : 'danger'"
          :loading="cancel.isPending.value || reissue.isPending.value || remove.isPending.value"
          @click="confirmAction"
          >{{ confirm ? t(`tickets.confirm.${confirm.kind}.action`) : '' }}</WButton
        >
      </template>
    </WModal>
  </div>
</template>

<script setup lang="ts">
import { fromZonedInput, toZonedInput } from '@/composables/useDate'
import { useOrgTimezone } from '@/composables/useOrgTimezone'
import { AlertTriangle, Check, Minus, Package, Plus, Search, X } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { useMembers } from '@/composables/useMembers'
import { formatAmount, formatMoney } from '@/composables/useMoney'
import { usePermissions } from '@/composables/usePermissions'
import { useToast } from '@/composables/useToast'
import { WButton, WDrawer, WInput, WSelect, WTextarea } from '@/design'
import { useCatalog } from '@/modules/catalog/api'
import { clientsApi, useClients } from '@/modules/crm/api'
import { useWeddings } from '@/modules/events/api'
import { usePacks, useItems } from '@/modules/stock/api'

import { reservationsApi, useAvailability, useReservationMutation } from '../api'
import type { Reservation, ReservationInput, ReservationKind, ReservationLine } from '../types'

/**
 * « Assistant de création en tiroir large » (reservations-stock.md §4.2): client, logistic dates,
 * equipment with live availability for the period, packs, services, summary and deposit.
 * The server recomputes every amount and checks the stock under lock at confirmation.
 */
const props = defineProps<{ reservation?: Reservation | null }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [reservation: Reservation] }>()
const { t } = useI18n()
const toast = useToast()
const { can } = usePermissions()
const seesMoney = computed(() => can('viewFinance'))

const STEPS = ['client', 'dates', 'equipment', 'services', 'summary'] as const
const step = ref(0)
const errors = ref<Record<string, string>>({})

// --- Form ---------------------------------------------------------------------------------------
interface Form {
  client: string
  title: string
  kind: ReservationKind
  venue: string
  address: string
  guestCount: number | null
  owner: string
  wedding: string
  notes: string
  deliveryAt: string
  setupAt: string
  eventStart: string
  eventEnd: string
  teardownAt: string
  pickupAt: string
  returnAt: string
  vehicle: string
  discount: number | null
  transportFee: number | null
  setupFee: number | null
  depositMode: 'pct' | 'amount'
  depositPct: number | null
  depositAmount: number | null
}
const form = ref<Form>(blank())
const lines = ref<ReservationLine[]>([])

// Dates are typed in the agency's time zone, like everything the server shows.
const timeZone = useOrgTimezone()
const local = (value: string | null | undefined) => toZonedInput(value, timeZone.value)
const iso = (value: string) => (value ? fromZonedInput(value, timeZone.value) : null)

function blank(): Form {
  return {
    client: '',
    title: '',
    kind: 'rental',
    venue: '',
    address: '',
    guestCount: null,
    owner: '',
    wedding: '',
    notes: '',
    deliveryAt: '',
    setupAt: '',
    eventStart: '',
    eventEnd: '',
    teardownAt: '',
    pickupAt: '',
    returnAt: '',
    vehicle: '',
    discount: 0,
    transportFee: 0,
    setupFee: 0,
    depositMode: 'pct',
    depositPct: 30,
    depositAmount: 0,
  }
}

watch(open, (isOpen) => {
  if (!isOpen) return
  step.value = 0
  errors.value = {}
  const r = props.reservation
  if (!r) {
    form.value = blank()
    lines.value = []
    return
  }
  form.value = {
    client: r.client,
    title: r.title,
    kind: r.kind,
    venue: r.venue,
    address: r.address,
    guestCount: r.guestCount,
    owner: r.owner ?? '',
    wedding: r.wedding ?? '',
    notes: r.notes,
    deliveryAt: local(r.deliveryAt),
    setupAt: local(r.setupAt),
    eventStart: local(r.eventStart),
    eventEnd: local(r.eventEnd),
    teardownAt: local(r.teardownAt),
    pickupAt: local(r.pickupAt),
    returnAt: local(r.returnAt),
    vehicle: r.vehicle,
    discount: r.discount ?? 0,
    transportFee: r.transportFee ?? 0,
    setupFee: r.setupFee ?? 0,
    depositMode: 'amount',
    depositPct: 30,
    depositAmount: r.depositRequired ?? 0,
  }
  lines.value = r.lines.filter((l) => l.kind !== 'damage').map((l) => ({ ...l }))
})

// --- Reference data -----------------------------------------------------------------------------
const clients = useClients({})
const members = useMembers()
const weddings = useWeddings()
const catalog = useCatalog()
const items = useItems({})
const period = computed(() => {
  const from = (form.value.deliveryAt || form.value.setupAt || form.value.eventStart).slice(0, 10)
  const to = (form.value.returnAt || form.value.pickupAt || form.value.eventEnd).slice(0, 10)
  return from && to ? { from, to: to < from ? from : to } : null
})
const availability = useAvailability(() =>
  period.value ? { ...period.value, exclude: props.reservation?.id ?? null } : null,
)
const packs = usePacks(() => period.value ?? {})
const free = computed(
  () => new Map((availability.data.value?.items ?? []).map((row) => [row.item, row])),
)

const clientOptions = computed(() =>
  (clients.data.value?.results ?? []).map((c) => ({ value: c.id, label: c.name })),
)
const ownerOptions = computed(() =>
  (members.data.value ?? [])
    .filter((m) => m.isActive)
    .map((m) => ({ value: m.userId, label: m.fullName })),
)
const weddingOptions = computed(() => [
  { value: '', label: t('reservations.wizard.noWedding') },
  ...(weddings.data.value ?? []).map((w) => ({ value: w.id, label: w.title })),
])
const kindOptions = computed(() =>
  (['rental', 'sale', 'service', 'mixed'] as const).map((value) => ({
    value,
    label: t(`reservations.kinds.${value}`),
  })),
)

// --- Quick client -------------------------------------------------------------------------------
const newClientName = ref('')
const creatingClient = ref(false)
async function quickClient(): Promise<void> {
  if (!newClientName.value.trim()) return
  creatingClient.value = true
  try {
    const client = await clientsApi.create({ name: newClientName.value.trim() })
    await clients.refetch()
    form.value.client = client.id
    newClientName.value = ''
    toast.success(t('reservations.wizard.clientCreated', { name: client.name }))
  } catch (error) {
    toast.error(toApiError(error).message)
  } finally {
    creatingClient.value = false
  }
}

// --- Equipment ----------------------------------------------------------------------------------
const search = ref('')
const itemList = computed(() => {
  const term = search.value.trim().toLowerCase()
  return (items.data.value ?? [])
    .filter(
      (i) =>
        !term || i.name.toLowerCase().includes(term) || i.reference.toLowerCase().includes(term),
    )
    .slice(0, 12)
})
const eventDays = computed(() => {
  if (!form.value.eventStart || !form.value.eventEnd) return 1
  const ms = new Date(form.value.eventEnd).getTime() - new Date(form.value.eventStart).getTime()
  return Math.max(1, Math.ceil(ms / 86_400_000))
})

function addItem(itemId: string, kind: 'rental' | 'sale'): void {
  const existing = lines.value.find((l) => l.kind === kind && l.item === itemId)
  if (existing) {
    existing.quantity += 1
    return
  }
  const item = items.data.value?.find((i) => i.id === itemId)
  if (!item) return
  lines.value.push({
    kind,
    item: item.id,
    itemReference: item.reference,
    rentUnit: item.rentUnit,
    label: item.name,
    quantity: Math.max(
      1,
      Math.min(form.value.guestCount ?? 1, free.value.get(item.id)?.available ?? 1),
    ),
    unitPrice: kind === 'rental' ? item.rentPrice : item.salePrice,
    periodDays: item.rentUnit === 'day' ? eventDays.value : 1,
  })
}
function addPack(packId: string): void {
  const existing = lines.value.find((l) => l.kind === 'pack' && l.pack === packId)
  if (existing) {
    existing.quantity += 1
    return
  }
  const pack = packs.data.value?.find((p) => p.id === packId)
  if (!pack) return
  lines.value.push({
    kind: 'pack',
    pack: pack.id,
    label: pack.name,
    quantity: 1,
    unitPrice: pack.price,
  })
}

/** Pieces of each item the lines take (packs expanded). */
const needs = computed(() => {
  const totals = new Map<string, number>()
  for (const line of lines.value) {
    if ((line.kind === 'rental' || line.kind === 'sale') && line.item)
      totals.set(line.item, (totals.get(line.item) ?? 0) + line.quantity)
    if (line.kind === 'pack' && line.pack) {
      const pack = packs.data.value?.find((p) => p.id === line.pack)
      for (const c of pack?.components ?? [])
        totals.set(c.item, (totals.get(c.item) ?? 0) + c.quantity * line.quantity)
    }
  }
  return totals
})
function shortageOf(itemId: string): number {
  const available = free.value.get(itemId)?.available
  return available === undefined ? 0 : Math.max(0, (needs.value.get(itemId) ?? 0) - available)
}
const anyShortage = computed(() => [...needs.value.keys()].some((id) => shortageOf(id) > 0))
function alternativesOf(itemId: string) {
  const item = items.data.value?.find((i) => i.id === itemId)
  if (!item) return []
  return (items.data.value ?? [])
    .filter((o) => o.category === item.category && o.id !== item.id)
    .map((o) => ({ ...o, free: free.value.get(o.id)?.available ?? 0 }))
    .filter((o) => o.free > 0)
    .slice(0, 3)
}
function replace(line: ReservationLine, itemId: string): void {
  const item = items.data.value?.find((i) => i.id === itemId)
  if (!item) return
  Object.assign(line, {
    item: item.id,
    itemReference: item.reference,
    label: item.name,
    rentUnit: item.rentUnit,
    unitPrice: line.kind === 'rental' ? item.rentPrice : item.salePrice,
  })
}

// --- Services -----------------------------------------------------------------------------------
const services = computed(() =>
  (catalog.data.value ?? []).flatMap((category) =>
    category.items.filter((i) => i.isActive).map((i) => ({ ...i, categoryName: category.name })),
  ),
)
function addService(serviceId: string): void {
  const service = services.value.find((s) => s.id === serviceId)
  if (!service) return
  const existing = lines.value.find((l) => l.kind === 'service' && l.service === serviceId)
  if (existing) existing.quantity += 1
  else
    lines.value.push({
      kind: 'service',
      service: service.id,
      label: service.name,
      quantity: 1,
      unitPrice: service.unitPrice,
    })
}
const freeLabel = ref('')
const freePrice = ref<number | null>(null)
function addFree(): void {
  if (!freeLabel.value.trim()) return
  lines.value.push({
    kind: 'free',
    label: freeLabel.value.trim(),
    quantity: 1,
    unitPrice: freePrice.value ?? 0,
  })
  freeLabel.value = ''
  freePrice.value = null
}
const remove = (line: ReservationLine) => lines.value.splice(lines.value.indexOf(line), 1)
const equipmentLines = computed(() =>
  lines.value.filter((l) => l.kind === 'rental' || l.kind === 'sale' || l.kind === 'pack'),
)
const serviceLines = computed(() =>
  lines.value.filter((l) => l.kind === 'service' || l.kind === 'free'),
)

// --- Totals (estimate; the server recomputes) ---------------------------------------------------
const num = (value: number | null | undefined) =>
  typeof value === 'number' && !isNaN(value) ? value : 0
const lineTotal = (line: ReservationLine) =>
  num(line.unitPrice) *
  line.quantity *
  (line.kind === 'rental' && line.rentUnit === 'day' ? Math.max(1, line.periodDays ?? 1) : 1)
const subtotal = computed(() => lines.value.reduce((sum, l) => sum + lineTotal(l), 0))
const total = computed(
  () =>
    Math.max(0, subtotal.value - num(form.value.discount)) +
    num(form.value.transportFee) +
    num(form.value.setupFee),
)
const depositDue = computed(() =>
  form.value.depositMode === 'pct'
    ? Math.round((total.value * num(form.value.depositPct)) / 100)
    : Math.min(total.value, num(form.value.depositAmount)),
)

// --- Steps and saving ---------------------------------------------------------------------------
function validate(index: number): boolean {
  errors.value = {}
  if (index === 0) {
    if (!form.value.client) errors.value.client = t('reservations.wizard.clientRequired')
    if (!form.value.title.trim()) errors.value.title = t('reservations.wizard.titleRequired')
  }
  if (index === 1 && (!form.value.eventStart || !form.value.eventEnd))
    errors.value.eventStart = t('reservations.wizard.eventRequired')
  return !Object.keys(errors.value).length
}
function go(target: number): void {
  if (target > step.value && !validate(step.value)) return
  step.value = target
}

function payload(): ReservationInput {
  const f = form.value
  return {
    client: f.client,
    wedding: f.wedding || null,
    kind: f.kind,
    title: f.title.trim(),
    venue: f.venue,
    address: f.address,
    guestCount: f.guestCount || null,
    owner: f.owner || null,
    notes: f.notes,
    deliveryAt: iso(f.deliveryAt),
    setupAt: iso(f.setupAt),
    eventStart: iso(f.eventStart)!,
    eventEnd: iso(f.eventEnd)!,
    teardownAt: iso(f.teardownAt),
    pickupAt: iso(f.pickupAt),
    returnAt: iso(f.returnAt),
    vehicle: f.vehicle.trim(),
    discount: num(f.discount),
    transportFee: num(f.transportFee),
    setupFee: num(f.setupFee),
    ...(f.depositMode === 'pct'
      ? { depositPct: num(f.depositPct) }
      : { depositRequired: num(f.depositAmount) }),
    lines: lines.value.map((l) => ({
      kind: l.kind,
      item: l.item ?? null,
      pack: l.pack ?? null,
      service: l.service ?? null,
      label: l.label,
      quantity: l.quantity,
      periodDays: l.periodDays ?? 1,
      // Prices: the catalog price unless the planner set one (roles with money only).
      ...(seesMoney.value ? { unitPrice: l.unitPrice ?? null } : {}),
    })),
  }
}

const save = useReservationMutation(async (confirm: boolean) => {
  const input = payload()
  const saved = props.reservation
    ? await reservationsApi.update(props.reservation.id, input)
    : await reservationsApi.create(input)
  return confirm && (saved.status === 'draft' || saved.status === 'quote_sent')
    ? reservationsApi.confirm(saved.id)
    : saved
})

async function submit(confirm: boolean): Promise<void> {
  if (![0, 1].every((index) => validate(index))) {
    step.value = errors.value.eventStart ? 1 : 0
    return
  }
  try {
    const saved = await save.mutateAsync(confirm)
    toast.success(
      props.reservation
        ? t('reservations.wizard.saved')
        : t('reservations.wizard.created', { number: saved.number }),
    )
    emit('saved', saved)
    open.value = false
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
</script>

<template>
  <WDrawer
    v-model:open="open"
    wide
    :title="
      reservation
        ? t('reservations.wizard.editTitle', { number: reservation.number })
        : t('reservations.wizard.createTitle')
    "
  >
    <!-- Stepper -->
    <ol class="flex flex-wrap gap-2" :aria-label="t('reservations.wizard.createTitle')">
      <li v-for="(key, index) in STEPS" :key="key">
        <button
          type="button"
          class="flex items-center gap-2 rounded-full border px-3 py-1.5 text-[12.5px] font-bold"
          :class="
            index === step
              ? 'border-violet bg-violet-soft text-violet'
              : index < step
                ? 'border-line text-ink-2'
                : 'border-line text-muted'
          "
          :aria-current="index === step ? 'step' : undefined"
          @click="go(index)"
        >
          <span
            class="flex size-5 items-center justify-center rounded-full text-[11px]"
            :class="index < step ? 'bg-green text-white' : 'bg-surface-2'"
          >
            <Check v-if="index < step" class="size-3" aria-hidden="true" />
            <template v-else>{{ index + 1 }}</template>
          </span>
          {{ t(`reservations.wizard.steps.${key}`) }}
        </button>
      </li>
    </ol>

    <!-- 1. Client and event -->
    <section v-if="step === 0" class="grid gap-4 sm:grid-cols-2">
      <WSelect
        v-model="form.client"
        class="sm:col-span-2"
        :label="t('reservations.wizard.client')"
        :options="clientOptions"
        :placeholder="t('reservations.wizard.chooseClient')"
        :error="errors.client"
        required
      />
      <div class="flex items-end gap-2 sm:col-span-2">
        <WInput
          v-model="newClientName"
          class="flex-1"
          :label="t('reservations.wizard.newClientName')"
          :placeholder="t('reservations.wizard.newClient')"
        />
        <WButton variant="secondary" :loading="creatingClient" @click="quickClient">{{
          t('reservations.wizard.createClient')
        }}</WButton>
      </div>
      <WInput
        v-model="form.title"
        class="sm:col-span-2"
        :label="t('reservations.wizard.title')"
        :placeholder="t('reservations.wizard.titlePlaceholder')"
        :error="errors.title"
        required
      />
      <WSelect v-model="form.kind" :label="t('reservations.wizard.kind')" :options="kindOptions" />
      <WInput
        v-model.number="form.guestCount"
        :label="t('reservations.wizard.guests')"
        type="number"
        min="0"
        inputmode="numeric"
      />
      <WInput v-model="form.venue" :label="t('reservations.wizard.venue')" />
      <WSelect
        v-model="form.owner"
        :label="t('reservations.wizard.owner')"
        :options="ownerOptions"
        :placeholder="t('reservations.wizard.owner')"
      />
      <WTextarea
        v-model="form.address"
        class="sm:col-span-2"
        :label="t('reservations.wizard.address')"
        :rows="2"
      />
      <WSelect
        v-model="form.wedding"
        class="sm:col-span-2"
        :label="t('reservations.wizard.wedding')"
        :options="weddingOptions"
      />
    </section>

    <!-- 2. Logistic dates -->
    <section v-else-if="step === 1" class="flex flex-col gap-4">
      <p class="text-[13px] text-muted">{{ t('reservations.wizard.datesHint') }}</p>
      <div class="grid gap-4 sm:grid-cols-2">
        <WInput
          v-model="form.deliveryAt"
          type="datetime-local"
          :label="t('reservations.steps.delivery_at')"
        />
        <WInput
          v-model="form.setupAt"
          type="datetime-local"
          :label="t('reservations.steps.setup_at')"
        />
        <WInput
          v-model="form.eventStart"
          type="datetime-local"
          :label="t('reservations.steps.event_start')"
          :error="errors.eventStart"
          required
        />
        <WInput
          v-model="form.eventEnd"
          type="datetime-local"
          :label="t('reservations.steps.event_end')"
          required
        />
        <WInput
          v-model="form.teardownAt"
          type="datetime-local"
          :label="t('reservations.steps.teardown_at')"
        />
        <WInput
          v-model="form.pickupAt"
          type="datetime-local"
          :label="t('reservations.steps.pickup_at')"
        />
        <WInput
          v-model="form.returnAt"
          type="datetime-local"
          :label="t('reservations.steps.return_at')"
        />
        <WInput
          v-model="form.vehicle"
          :label="t('reservations.wizard.vehicle')"
          :placeholder="t('reservations.wizard.vehiclePlaceholder')"
          maxlength="80"
        />
      </div>
    </section>

    <!-- 3. Equipment with live availability -->
    <section v-else-if="step === 2" class="flex flex-col gap-4">
      <WInput
        v-model="search"
        type="search"
        :label="t('reservations.wizard.searchItem')"
        :placeholder="t('reservations.wizard.searchItemPlaceholder')"
      >
        <template #prefix><Search class="size-[18px] text-muted" aria-hidden="true" /></template>
      </WInput>
      <ul class="grid gap-2 sm:grid-cols-2">
        <li
          v-for="item in itemList"
          :key="item.id"
          class="flex items-center gap-3 rounded-wd border border-line px-3 py-2.5"
        >
          <div class="min-w-0 flex-1">
            <p class="truncate font-bold">{{ item.name }}</p>
            <p class="num text-[12.5px] text-muted">
              {{
                t('reservations.wizard.availableFor', {
                  available: free.get(item.id)?.available ?? item.today?.available ?? 0,
                  total: item.totalQuantity,
                })
              }}
            </p>
          </div>
          <WButton size="sm" variant="secondary" @click="addItem(item.id, 'rental')">
            <Plus class="size-[15px]" aria-hidden="true" />{{ t('reservations.wizard.rentLabel') }}
          </WButton>
          <WButton
            v-if="item.salePrice !== null"
            size="sm"
            variant="ghost"
            @click="addItem(item.id, 'sale')"
            >{{ t('reservations.wizard.saleLabel') }}</WButton
          >
        </li>
      </ul>

      <div v-if="packs.data.value?.length">
        <h3 class="mb-2 text-[13px] font-bold text-muted">{{ t('reservations.wizard.packs') }}</h3>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="pack in packs.data.value"
            :key="pack.id"
            type="button"
            class="flex items-center gap-2 rounded-wd border border-line px-3 py-2 text-left text-[13px] hover:bg-surface-2"
            @click="addPack(pack.id)"
          >
            <Package class="size-4 text-violet" aria-hidden="true" />
            <span>
              <span class="block font-bold">{{ pack.name }}</span>
              <span class="block text-[12px] text-muted">{{
                t(
                  'reservations.wizard.packAvailable',
                  { count: pack.available ?? 0 },
                  pack.available ?? 0,
                )
              }}</span>
            </span>
          </button>
        </div>
      </div>

      <p v-if="!equipmentLines.length" class="text-muted">
        {{ t('reservations.wizard.noEquipment') }}
      </p>
      <ul v-else class="flex flex-col gap-2">
        <li
          v-for="line in equipmentLines"
          :key="`${line.kind}-${line.item ?? line.pack}`"
          class="rounded-wd border px-3 py-2.5"
          :class="line.item && shortageOf(line.item) ? 'border-red bg-red-soft/40' : 'border-line'"
        >
          <div class="flex flex-wrap items-center gap-3">
            <div class="min-w-0 flex-1">
              <p class="font-bold">
                {{ line.label }}
                <span class="text-[12px] font-semibold text-muted"
                  >· {{ t(`reservations.lineKinds.${line.kind}`) }}</span
                >
              </p>
              <p v-if="line.item" class="num text-[12.5px] text-muted">
                {{
                  t('reservations.wizard.availableFor', {
                    available: free.get(line.item)?.available ?? '…',
                    total: free.get(line.item)?.total ?? '…',
                  })
                }}
              </p>
            </div>
            <div class="flex items-center gap-1">
              <WButton
                size="sm"
                variant="secondary"
                icon
                :aria-label="`−1 ${line.label}`"
                @click="line.quantity = Math.max(1, line.quantity - 1)"
              >
                <Minus class="size-[15px]" aria-hidden="true" />
              </WButton>
              <input
                v-model.number="line.quantity"
                type="number"
                min="1"
                inputmode="numeric"
                class="num h-8 w-20 rounded-[8px] border border-line-2 bg-surface px-2 text-right"
                :aria-label="`${t('stock.movement.quantity')} : ${line.label}`"
              />
              <WButton
                size="sm"
                variant="secondary"
                icon
                :aria-label="`+1 ${line.label}`"
                @click="line.quantity += 1"
              >
                <Plus class="size-[15px]" aria-hidden="true" />
              </WButton>
            </div>
            <label
              v-if="line.kind === 'rental' && line.rentUnit === 'day'"
              class="flex items-center gap-1 text-[12.5px]"
            >
              <input
                v-model.number="line.periodDays"
                type="number"
                min="1"
                class="num h-8 w-14 rounded-[8px] border border-line-2 bg-surface px-2 text-right"
              />
              {{ t('reservations.wizard.days') }}
            </label>
            <WButton
              variant="ghost"
              icon
              :aria-label="t('reservations.wizard.remove', { name: line.label })"
              @click="remove(line)"
            >
              <X class="size-[18px]" aria-hidden="true" />
            </WButton>
          </div>
          <div
            v-if="line.item && shortageOf(line.item)"
            class="mt-2 flex flex-col gap-1.5 text-[13px]"
            role="alert"
          >
            <p class="flex items-center gap-1.5 font-bold text-red">
              <AlertTriangle class="size-4" aria-hidden="true" />
              {{ t('reservations.wizard.shortage', { missing: shortageOf(line.item) }) }}
            </p>
            <p v-if="alternativesOf(line.item).length" class="flex flex-wrap items-center gap-2">
              <span class="text-ink-2">{{ t('reservations.wizard.alternatives') }}</span>
              <button
                v-for="alt in alternativesOf(line.item)"
                :key="alt.id"
                type="button"
                class="rounded-full border border-line-2 bg-surface px-2.5 py-0.5 font-semibold hover:bg-surface-2"
                @click="replace(line, alt.id)"
              >
                {{ alt.name }} ({{ alt.free }})
              </button>
            </p>
            <p class="text-ink-2">
              {{ t('reservations.wizard.subcontract') }}
              <RouterLink :to="{ name: 'vendors' }" class="font-bold text-violet hover:underline">{{
                t('reservations.wizard.vendors')
              }}</RouterLink>
            </p>
          </div>
        </li>
      </ul>
    </section>

    <!-- 4. Services and free lines -->
    <section v-else-if="step === 3" class="flex flex-col gap-4">
      <div>
        <h3 class="mb-2 text-[13px] font-bold text-muted">
          {{ t('reservations.wizard.catalog') }}
        </h3>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="service in services"
            :key="service.id"
            type="button"
            class="rounded-wd border border-line px-3 py-2 text-left text-[13px] hover:bg-surface-2"
            @click="addService(service.id)"
          >
            <span class="block font-bold">{{ service.name }}</span>
            <span v-if="seesMoney" class="num block text-[12px] text-muted">{{
              formatMoney(service.unitPrice)
            }}</span>
          </button>
        </div>
      </div>
      <form class="flex flex-wrap items-end gap-2" @submit.prevent="addFree">
        <WInput
          v-model="freeLabel"
          class="min-w-[220px] flex-1"
          :label="t('reservations.wizard.freeLabel')"
        />
        <WInput
          v-if="seesMoney"
          v-model.number="freePrice"
          class="w-[160px]"
          type="number"
          min="0"
          :label="t('reservations.wizard.freePrice')"
        />
        <WButton type="submit" variant="secondary">{{ t('reservations.wizard.addFree') }}</WButton>
      </form>
      <ul v-if="serviceLines.length" class="divide-y divide-line rounded-wd border border-line">
        <li
          v-for="(line, index) in serviceLines"
          :key="index"
          class="flex items-center gap-3 px-3 py-2.5"
        >
          <span class="min-w-0 flex-1 truncate font-bold">{{ line.label }}</span>
          <input
            v-model.number="line.quantity"
            type="number"
            min="1"
            class="num h-8 w-16 rounded-[8px] border border-line-2 bg-surface px-2 text-right"
            :aria-label="`${t('stock.movement.quantity')} : ${line.label}`"
          />
          <span v-if="seesMoney" class="num w-28 text-right">{{
            formatAmount(lineTotal(line))
          }}</span>
          <WButton
            variant="ghost"
            icon
            :aria-label="t('reservations.wizard.remove', { name: line.label })"
            @click="remove(line)"
          >
            <X class="size-[18px]" aria-hidden="true" />
          </WButton>
        </li>
      </ul>
    </section>

    <!-- 5. Summary and deposit -->
    <section v-else class="flex flex-col gap-4">
      <ul class="divide-y divide-line rounded-wd border border-line">
        <li
          v-for="(line, index) in lines"
          :key="index"
          class="flex items-center gap-3 px-3 py-2 text-[13.5px]"
        >
          <span class="num w-10 text-right font-bold">{{ line.quantity }}</span>
          <span class="min-w-0 flex-1 truncate">{{ line.label }}</span>
          <span v-if="seesMoney" class="num">{{ formatAmount(lineTotal(line)) }}</span>
        </li>
      </ul>
      <div v-if="seesMoney" class="grid gap-4 sm:grid-cols-3">
        <WInput
          v-model.number="form.discount"
          type="number"
          min="0"
          :label="t('reservations.wizard.discount')"
        />
        <WInput
          v-model.number="form.transportFee"
          type="number"
          min="0"
          :label="t('reservations.wizard.transport')"
        />
        <WInput
          v-model.number="form.setupFee"
          type="number"
          min="0"
          :label="t('reservations.wizard.setupFee')"
        />
        <WSelect
          v-model="form.depositMode"
          :label="t('reservations.wizard.deposit')"
          :options="[
            { value: 'pct', label: t('reservations.wizard.depositPct') },
            { value: 'amount', label: t('reservations.wizard.depositAmount') },
          ]"
        />
        <WInput
          v-if="form.depositMode === 'pct'"
          v-model.number="form.depositPct"
          type="number"
          min="0"
          max="100"
          :label="t('reservations.wizard.depositPct')"
        />
        <WInput
          v-else
          v-model.number="form.depositAmount"
          type="number"
          min="0"
          :label="t('reservations.wizard.depositAmount')"
        />
      </div>
      <dl
        v-if="seesMoney"
        class="ml-auto grid w-full max-w-[320px] grid-cols-2 gap-y-1.5 text-[14px]"
      >
        <dt class="text-muted">{{ t('reservations.wizard.subtotal') }}</dt>
        <dd class="num text-right">{{ formatMoney(subtotal) }}</dd>
        <dt class="font-bold">{{ t('reservations.wizard.total') }}</dt>
        <dd class="num text-right font-display text-[17px] font-semibold">
          {{ formatMoney(total) }}
        </dd>
        <dt class="text-muted">{{ t('reservations.wizard.depositDue') }}</dt>
        <dd class="num text-right">{{ formatMoney(depositDue) }}</dd>
      </dl>
      <WTextarea v-model="form.notes" :label="t('reservations.wizard.notes')" :rows="2" />
      <p
        v-if="anyShortage"
        class="flex items-center gap-1.5 rounded-wd bg-red-soft px-3 py-2 text-[13px] font-bold text-red"
        role="alert"
      >
        <AlertTriangle class="size-4" aria-hidden="true" />{{
          t('reservations.wizard.quantityTooHigh')
        }}
      </p>
    </section>

    <template #footer>
      <WButton v-if="step > 0" variant="ghost" @click="go(step - 1)">{{
        t('reservations.wizard.previous')
      }}</WButton>
      <div class="ml-auto flex flex-wrap gap-2">
        <template v-if="step < STEPS.length - 1">
          <WButton variant="secondary" :loading="save.isPending.value" @click="submit(false)">{{
            reservation ? t('reservations.wizard.save') : t('reservations.wizard.saveDraft')
          }}</WButton>
          <WButton @click="go(step + 1)">{{ t('reservations.wizard.next') }}</WButton>
        </template>
        <template v-else>
          <WButton variant="secondary" :loading="save.isPending.value" @click="submit(false)">{{
            reservation ? t('reservations.wizard.save') : t('reservations.wizard.saveDraft')
          }}</WButton>
          <WButton
            v-if="!reservation || ['draft', 'quote_sent'].includes(reservation.status)"
            :loading="save.isPending.value"
            :disabled="anyShortage"
            @click="submit(true)"
            >{{ t('reservations.wizard.saveConfirm') }}</WButton
          >
        </template>
      </div>
    </template>
  </WDrawer>
</template>

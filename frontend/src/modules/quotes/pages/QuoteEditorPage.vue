<script setup lang="ts">
import {
  Check,
  Copy,
  FileDown,
  FileSignature,
  LayoutTemplate,
  Link2,
  MessageCircle,
  Plus,
  Save,
  Send,
  Share2,
  Trash2,
  X,
} from '@lucide/vue'
import { useQuery } from '@tanstack/vue-query'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'

import { api } from '@/api/client'
import { toApiError } from '@/api/errors'
import { organizationApi } from '@/api/organization'
import { formatDate, formatDateTime } from '@/composables/useDate'
import { formatMoney } from '@/composables/useMoney'
import { usePermissions } from '@/composables/usePermissions'
import { useToast } from '@/composables/useToast'
import { useWhatsApp } from '@/composables/useWhatsApp'
import { WBadge, WButton, WCard, WEmptyState, WInput, WModal, WSelect, WTextarea } from '@/design'
import { useCatalog } from '@/modules/catalog/api'
import type { ServiceItem } from '@/modules/catalog/types'
import { useClients } from '@/modules/crm/api'

import { documentsApi, quotesApi, useQuote, useQuoteAction } from '../api'
import { computeTotals, lineAmount, suggestedQuantity } from '../calculations'
import CatalogPicker from '../components/CatalogPicker.vue'
import ServerPreview from '../components/ServerPreview.vue'
import { STATUS_TONES } from '../constants'
import type { Quote, QuoteDesign, QuoteInput, QuoteLine, QuotePartner } from '../types'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const toast = useToast()
const { can } = usePermissions()

const quoteId = computed(() => (route.name === 'quote-edit' ? String(route.params.id) : null))
const initialClientId = computed(() =>
  typeof route.query.client === 'string' ? route.query.client : null,
)
const quote = useQuote(quoteId)
const organization = useQuery({ queryKey: ['organization-settings'], queryFn: organizationApi.get })
const clients = useClients({})

// --- Draft state ---------------------------------------------------------------------------
interface Draft {
  client: string | null
  weddingDate: string | null
  guestCount: number | null
  validUntil: string
  discountPct: number
  depositPct: number
  paymentTerms: string
  notes: string
  templateName: string
  lines: QuoteLine[]
  // Document (docs/specs/devis-billets.md §2f); empty = the agency's default.
  design: QuoteDesign | ''
  palette: string
  tagline: string
  venue: string
  partners: QuotePartner[]
}

const today = () => new Date().toISOString().slice(0, 10)
const addDays = (iso: string, days: number) => {
  const date = new Date(`${iso}T12:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

const draft = ref<Draft>(emptyDraft())
const saved = ref('')
const dirty = computed(() => JSON.stringify(draft.value) !== saved.value)
/** Automatic pre-fills (validity, client, default lines) keep a clean draft clean. */
function prefill(change: () => void): void {
  const clean = !dirty.value
  change()
  if (clean) saved.value = JSON.stringify(draft.value)
}
if (!quoteId.value) saved.value = JSON.stringify(draft.value)

function emptyDraft(): Draft {
  return {
    client: initialClientId.value,
    weddingDate: null,
    guestCount: null,
    validUntil: addDays(today(), organization.data.value?.quoteValidityDays ?? 30),
    discountPct: 0,
    depositPct: 30,
    paymentTerms: t('quotes.defaultTerms'),
    notes: '',
    templateName: '',
    lines: [],
    design: '',
    palette: '',
    tagline: '',
    venue: '',
    partners: [],
  }
}

function fromQuote(source: Quote): Draft {
  return {
    client: source.client,
    weddingDate: source.weddingDate,
    guestCount: source.guestCount,
    validUntil: source.validUntil,
    discountPct: Number(source.discountPct),
    depositPct: Number(source.depositPct),
    paymentTerms: source.paymentTerms,
    notes: source.notes,
    templateName: source.templateName,
    lines: source.lines.map((line) => ({
      serviceItem: line.serviceItem,
      label: line.label,
      description: line.description,
      unit: line.unit,
      unitPrice: line.unitPrice,
      quantity: Number(line.quantity),
      icon: line.icon ?? '',
    })),
    design: source.design,
    palette: source.palette,
    tagline: source.tagline,
    venue: source.venue,
    partners: source.partners.map((partner) => ({
      name: partner.name,
      activity: partner.activity,
      signatory: partner.signatory,
      signatoryRole: partner.signatoryRole,
    })),
  }
}

function load(source: Quote): void {
  draft.value = fromQuote(source)
  saved.value = JSON.stringify(draft.value)
}

watch(
  () => quote.data.value,
  (value) => value && load(value),
  { immediate: true },
)
watch(
  () => organization.data.value?.quoteValidityDays,
  (days) => {
    if (!quoteId.value && days) prefill(() => (draft.value.validUntil = addDays(today(), days)))
  },
)

// Lines counted « per guest » follow the guest count: when it changes, and when it becomes known
// after the lines were added (still at the default quantity of 1).
watch(
  () => draft.value.guestCount,
  (next, previous) => {
    if (!next || next <= 0) return
    for (const line of draft.value.lines) {
      if (line.unit !== 'guest') continue
      if (line.quantity === previous || (!previous && line.quantity === 1)) line.quantity = next
    }
  },
)

// --- Derived -------------------------------------------------------------------------------
const current = computed(() => quote.data.value)
const isTemplate = computed(() => current.value?.isTemplate ?? false)
const status = computed(() => current.value?.status ?? 'draft')
const locked = computed(() => status.value === 'accepted' || status.value === 'refused')
const readOnly = computed(() => locked.value || !can('editSales'))
const totals = computed(() =>
  computeTotals(draft.value.lines, draft.value.discountPct, draft.value.depositPct),
)
const clientOptions = computed(() => {
  const options = (clients.data.value?.results ?? []).map((c) => ({ value: c.id, label: c.name }))
  // An archived client is not listed: keep the quote's own client selectable.
  const own = current.value?.clientDetail
  if (own && !options.some((option) => option.value === own.id))
    options.unshift({ value: own.id, label: own.name })
  return options
})
const client = computed(() => {
  if (current.value?.clientDetail) return current.value.clientDetail
  const fromList = clients.data.value?.results.find((c) => c.id === draft.value.client)
  return fromList ? { name: fromList.name, email: fromList.email, phone: fromList.phone } : null
})
const errors = ref<Record<string, string>>({})

// --- Lines ---------------------------------------------------------------------------------
function lineFor(item: ServiceItem): QuoteLine {
  return {
    serviceItem: item.id,
    label: item.name,
    description: item.description,
    unit: item.unit,
    unitPrice: item.unitPrice,
    quantity: suggestedQuantity(item.unit, draft.value.guestCount, item.quantityRule),
    icon: item.icon,
  }
}

/** Adding a service already in the quote raises its quantity instead of a second line. */
function addFromCatalog(item: ServiceItem): void {
  const existing = draft.value.lines.find((line) => line.serviceItem === item.id)
  if (existing) existing.quantity += 1
  else draft.value.lines.push(lineFor(item))
  toast.info(t('quotes.lineAdded', { name: item.name }))
}

// A blank new quote starts with the catalog's default services (complement §9).
const catalog = useCatalog()
const startsBlank = computed(() => !quoteId.value && !route.query.template && !route.query.from)
watch(
  () => catalog.data.value,
  (categories) => {
    if (!categories || !startsBlank.value || draft.value.lines.length) return
    const defaults = categories.flatMap((c) => c.items.filter((i) => i.isActive && i.isDefault))
    if (!defaults.length) return
    prefill(() => (draft.value.lines = defaults.map(lineFor)))
  },
  { immediate: true },
)

function addFreeLine(): void {
  draft.value.lines.push({
    serviceItem: null,
    label: '',
    description: '',
    unit: 'flat',
    unitPrice: 0,
    quantity: 1,
  })
}

function removeLine(index: number): void {
  draft.value.lines.splice(index, 1)
}

// --- Persistence ---------------------------------------------------------------------------
function payload(): QuoteInput {
  return {
    client: draft.value.client,
    weddingDate: draft.value.weddingDate || null,
    guestCount: draft.value.guestCount || null,
    validUntil: draft.value.validUntil,
    discountPct: draft.value.discountPct || 0,
    depositPct: draft.value.depositPct || 0,
    paymentTerms: draft.value.paymentTerms,
    notes: draft.value.notes,
    templateName: draft.value.templateName,
    lines: draft.value.lines.map((line) => ({ ...line, label: line.label.trim() })),
    design: draft.value.design,
    palette: draft.value.palette,
    tagline: draft.value.tagline,
    venue: draft.value.venue,
    partners: draft.value.partners.filter((partner) => partner.name.trim()),
  }
}

// --- Document look (model, palette) and partners ---------------------------------------------
const designs = useQuery({ queryKey: ['document-designs'], queryFn: documentsApi.designs })
const designOptions = computed(() =>
  (designs.data.value?.designs ?? []).map((design) => ({
    value: design.code,
    label: t('quotes.document.design', { code: design.code, name: design.name }),
  })),
)
const currentDesign = computed(() => draft.value.design || designs.data.value?.defaultDesign || 'A')
const currentPalette = computed(
  () => draft.value.palette || designs.data.value?.defaultPalette || '',
)
const MAX_PARTNERS = 2
function addPartner(): void {
  draft.value.partners.push({ name: '', activity: '', signatory: '', signatoryRole: '' })
}

function validate(): boolean {
  const found: Record<string, string> = {}
  // Complement §9: the two blocking cases have their own message.
  if (!isTemplate.value && !draft.value.client) {
    errors.value = { client: t('quotes.chooseClient') }
    toast.error(t('quotes.clientRequired'))
    return false
  }
  if (!draft.value.lines.length) {
    errors.value = {}
    toast.error(t('quotes.linesRequired'))
    return false
  }
  draft.value.lines.forEach((line, index) => {
    if (!line.label.trim()) found[`line-${index}`] = t('quotes.lineLabelRequired')
    else if (!(line.quantity > 0)) found[`line-${index}`] = t('quotes.lineQuantityInvalid')
  })
  errors.value = found
  if (Object.keys(found).length) toast.error(t('quotes.fixErrors'))
  return !Object.keys(found).length
}

const saving = ref(false)
async function save(
  silent = false,
  afterCreate: Record<string, string> = {},
): Promise<Quote | null> {
  if (!validate()) return null
  saving.value = true
  try {
    const result = quoteId.value
      ? await quotesApi.update(quoteId.value, payload())
      : await quotesApi.create(payload())
    load(result)
    if (!quoteId.value) {
      saved.value = JSON.stringify(fromQuote(result))
      await router.replace({ name: 'quote-edit', params: { id: result.id }, query: afterCreate })
    } else {
      update.mutate(result)
    }
    if (!silent) toast.success(t('quotes.draftSaved', { number: result.number }))
    return result
  } catch (error) {
    const apiError = toApiError(error)
    errors.value = Object.fromEntries(
      Object.entries(apiError.fields).map(([k, v]) => [k, v[0] ?? '']),
    )
    toast.error(apiError.message)
    return null
  } finally {
    saving.value = false
  }
}
// Keeps the shared caches (lists, counts) in sync after a save.
const update = useQuoteAction((value: Quote) => Promise.resolve(value))

// --- Lifecycle actions ---------------------------------------------------------------------
const send = useQuoteAction(({ id, channel }: { id: string; channel: 'email' | 'whatsapp' }) =>
  quotesApi.send(id, channel),
)
const accept = useQuoteAction((id: string) => quotesApi.accept(id))
const refuse = useQuoteAction(({ id, reason }: { id: string; reason: string }) =>
  quotesApi.refuse(id, reason),
)
const convert = useQuoteAction((id: string) => quotesApi.convert(id))
const duplicate = useQuoteAction(({ id, asTemplate }: { id: string; asTemplate: boolean }) =>
  quotesApi.duplicate(id, { asTemplate }),
)

const sendOpen = ref(false)
const refuseOpen = ref(false)
function openRefuse(): void {
  refuseReason.value = ''
  refuseOpen.value = true
}
const refuseReason = ref('')
const convertOpen = ref(false)
const deleteOpen = ref(false)

async function run<T>(action: () => Promise<T>, success: string): Promise<T | null> {
  try {
    const result = await action()
    toast.success(success)
    return result
  } catch (error) {
    toast.error(toApiError(error).message)
    return null
  }
}

async function openSend(): Promise<void> {
  // A new quote is saved first; its page then opens the confirmation (?envoyer=1).
  if (!quoteId.value) {
    await save(true, { envoyer: '1' })
    return
  }
  if (dirty.value && !(await save(true))) return
  sendOpen.value = true
}
watch(
  () => [route.query.envoyer, quote.data.value?.id] as const,
  ([flag, id]) => {
    if (flag !== '1' || !id) return
    sendOpen.value = true
    const query = { ...route.query }
    delete query.envoyer
    void router.replace({ query })
  },
  { immediate: true },
)

function cancel(): void {
  void router.push({ name: 'quotes' })
}

async function confirmSend(): Promise<void> {
  if (!quoteId.value) return
  try {
    const result = await send.mutateAsync({ id: quoteId.value, channel: 'email' })
    sendOpen.value = false
    toast.success(t('quotes.sentNumber', { number: result.number }))
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}

async function markAccepted(): Promise<void> {
  if (dirty.value && !(await save(true))) return
  await run(() => accept.mutateAsync(quoteId.value!), t('quotes.accepted'))
}

async function confirmRefuse(): Promise<void> {
  const result = await run(
    () => refuse.mutateAsync({ id: quoteId.value!, reason: refuseReason.value }),
    t('quotes.refused'),
  )
  if (result) refuseOpen.value = false
}

async function confirmConvert(): Promise<void> {
  const result = await run(() => convert.mutateAsync(quoteId.value!), t('quotes.converted'))
  if (result) convertOpen.value = false
}

async function copy(asTemplate: boolean): Promise<void> {
  const result = await run(
    () => duplicate.mutateAsync({ id: quoteId.value!, asTemplate }),
    asTemplate ? t('quotes.templateSaved') : t('quotes.duplicated'),
  )
  if (result) await router.push({ name: 'quote-edit', params: { id: result.id } })
}

async function confirmDelete(): Promise<void> {
  const result = await run(() => quotesApi.remove(quoteId.value!), t('quotes.deleted'))
  if (result !== null) {
    saved.value = JSON.stringify(draft.value)
    await router.push({ name: 'quotes' })
  }
}

// PDF: fetched with the session (and X-Organization in dev), then opened as a blob.
const pdfLoading = ref(false)
let pdfUrl: string | null = null
async function openPdf(): Promise<void> {
  if (!quoteId.value) return
  if (dirty.value && !(await save(true))) return
  pdfLoading.value = true
  try {
    // « Générer le PDF »: freezes a version (reused while nothing changes), then opens it.
    const document = await quotesApi.generate(quoteId.value)
    const response = await api.get<Blob>(document.pdfUrl.replace(/^\/api\/v1/, ''), {
      responseType: 'blob',
    })
    if (pdfUrl) URL.revokeObjectURL(pdfUrl)
    pdfUrl = URL.createObjectURL(response.data)
    window.open(pdfUrl, '_blank', 'noopener')
  } catch (error) {
    toast.error(toApiError(error).message)
  } finally {
    pdfLoading.value = false
  }
}
onBeforeUnmount(() => pdfUrl && URL.revokeObjectURL(pdfUrl))

// « Envoyer sur WhatsApp » / « Partager le PDF » (feedback 20 and 23/11/2026): saves, marks the
// quote as sent (no email, the version is frozen), then hands the PDF and a message with the
// public link to WhatsApp or to any app of the phone.
const whatsapp = useWhatsApp()
const sharing = ref<'whatsapp' | 'any' | null>(null)
const NOT_SAVED = new Error('not saved') // save() has already shown why
let shared: Quote | null = null
async function shareQuote(target: 'whatsapp' | 'any'): Promise<void> {
  sharing.value = target
  shared = null
  const options = {
    phone: client.value?.phone,
    text: async () => {
      let result = current.value ?? null
      if (!locked.value) {
        if ((dirty.value || !quoteId.value) && !(result = await save(true))) throw NOT_SAVED
        result = await send.mutateAsync({ id: result!.id, channel: 'whatsapp' })
      }
      shared = result
      return t('quotes.whatsappMessage', {
        name: result!.clientDetail?.name ?? '',
        number: result!.number,
        total: formatMoney(result!.total),
        date: formatDate(result!.validUntil),
        url: result!.publicUrl ?? '',
        organization: organization.data.value?.name ?? '',
      })
    },
    // The PDF of the version sent (frozen once, reused while nothing changes).
    file: async () => {
      const document = await quotesApi.generate(shared!.id)
      return (
        await api.get<Blob>(document.pdfUrl.replace(/^\/api\/v1/, ''), { responseType: 'blob' })
      ).data
    },
    get filename() {
      return `${shared?.number || current.value?.number || 'devis'}.pdf`
    },
    title: t('quotes.shareTitle'),
  }
  try {
    const result =
      target === 'whatsapp' ? await whatsapp.share(options) : await whatsapp.shareAnywhere(options)
    if (result === 'downloaded') toast.success(t('quotes.pdfDownloaded'))
    else if (result === 'shared' && !whatsapp.canShareFiles() && target === 'whatsapp')
      toast.info(t('quotes.pdfDropInChat'))
  } catch (error) {
    if (error !== NOT_SAVED) toast.error(toApiError(error).message)
  } finally {
    sharing.value = null
  }
}

async function copyLink(): Promise<void> {
  if (!current.value?.publicUrl) return
  try {
    await navigator.clipboard.writeText(current.value.publicUrl)
    toast.success(t('quotes.linkCopied'))
  } catch {
    toast.info(current.value.publicUrl)
  }
}

onBeforeRouteLeave(() => {
  if (dirty.value && !readOnly.value && !window.confirm(t('quotes.leaveUnsaved'))) return false
  return true
})

const pageTitle = computed(() => {
  if (isTemplate.value) return draft.value.templateName || t('quotes.template')
  return current.value?.number || t('quotes.new')
})
</script>

<template>
  <div class="flex flex-col gap-[22px]">
    <div v-if="quoteId && quote.isPending.value" class="grid gap-6 lg:grid-cols-2">
      <div class="skeleton h-[480px]" />
      <div class="skeleton h-[480px]" />
    </div>

    <WEmptyState
      v-else-if="quoteId && quote.isError.value"
      :title="t('quotes.notFound')"
      :description="toApiError(quote.error.value).message"
    >
      <WButton :to="{ name: 'quotes' }" variant="secondary">{{ t('quotes.backToList') }}</WButton>
    </WEmptyState>

    <template v-else>
      <!-- Header -->
      <header class="flex flex-wrap items-end gap-x-6 gap-y-3">
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-3">
            <h1>{{ pageTitle }}</h1>
            <WBadge v-if="current && !isTemplate" :tone="STATUS_TONES[status]">{{
              t(`quotes.statuses.${status}`)
            }}</WBadge>
            <WBadge v-if="isTemplate" tone="gold">{{ t('quotes.template') }}</WBadge>
            <span v-if="dirty && !readOnly" class="text-[13px] font-semibold text-gold">{{
              t('quotes.unsaved')
            }}</span>
          </div>
          <p class="mt-1 max-w-[64ch] text-muted">
            <template v-if="current?.contract">{{
              t('quotes.contractCreated', { number: current.contract.number })
            }}</template>
            <template v-else-if="current?.sentAt">{{
              t('quotes.sentOn', { date: formatDateTime(current.sentAt) })
            }}</template>
            <template v-else>{{ t('quotes.editorSubtitle') }}</template>
          </p>
        </div>

        <div class="flex flex-wrap gap-2">
          <WButton variant="ghost" @click="cancel">{{ t('common.cancel') }}</WButton>
          <WButton
            v-if="!readOnly"
            variant="secondary"
            :loading="saving"
            :disabled="!dirty && Boolean(quoteId)"
            @click="save()"
          >
            <Save class="size-[18px]" aria-hidden="true" />{{ t('quotes.saveDraft') }}
          </WButton>
          <template v-if="!isTemplate && can('editSales')">
            <WButton
              v-if="quoteId && current?.publicUrl && status !== 'draft'"
              variant="secondary"
              @click="copyLink"
            >
              <Link2 class="size-[18px]" aria-hidden="true" />{{ t('quotes.copyLink') }}
            </WButton>
            <WButton
              v-if="!locked || current?.publicUrl"
              variant="secondary"
              :loading="sharing === 'whatsapp'"
              :disabled="sharing !== null"
              @click="shareQuote('whatsapp')"
            >
              <MessageCircle class="size-[18px]" aria-hidden="true" />{{ t('quotes.whatsapp') }}
            </WButton>
            <WButton
              v-if="!locked || current?.publicUrl"
              variant="secondary"
              :loading="sharing === 'any'"
              :disabled="sharing !== null"
              @click="shareQuote('any')"
            >
              <Share2 class="size-[18px]" aria-hidden="true" />{{ t('quotes.sharePdf') }}
            </WButton>
            <WButton v-if="!locked" :loading="saving && !quoteId" @click="openSend">
              <Send class="size-[18px]" aria-hidden="true" />{{
                status === 'draft' ? t('quotes.send') : t('quotes.resend')
              }}
            </WButton>
            <WButton
              v-if="status === 'accepted' && !current?.contract && can('convertQuote')"
              @click="convertOpen = true"
            >
              <FileSignature class="size-[18px]" aria-hidden="true" />{{ t('quotes.convert') }}
            </WButton>
          </template>
        </div>
      </header>

      <div
        v-if="locked"
        class="rounded-wd bg-surface-2 px-3.5 py-3 text-[13.5px] text-ink-2"
        role="status"
      >
        {{
          status === 'accepted'
            ? t('quotes.lockedAccepted', {
                date: current?.acceptedAt ? formatDate(current.acceptedAt) : '',
              })
            : t('quotes.lockedRefused')
        }}
        <template v-if="status === 'refused' && current?.refusalReason">
          · {{ current.refusalReason }}</template
        >
      </div>

      <div
        class="grid grid-cols-1 items-start gap-5 min-[1181px]:grid-cols-[minmax(0,1fr)_minmax(340px,440px)]"
      >
        <!-- Editor -->
        <div class="flex min-w-0 flex-col gap-5">
          <WCard>
            <div class="grid gap-4 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)]">
              <WInput
                v-if="isTemplate"
                v-model="draft.templateName"
                :label="t('quotes.fields.templateName')"
                :disabled="readOnly"
              />
              <WSelect
                v-else
                v-model="draft.client"
                :label="t('quotes.client')"
                :options="clientOptions"
                :placeholder="t('quotes.chooseClient')"
                :error="errors.client"
                :disabled="readOnly || Boolean(current?.sentAt)"
                required
              />
              <WInput
                v-model="draft.weddingDate"
                :label="t('common.fields.weddingDate')"
                type="date"
                :disabled="readOnly"
              />
              <WInput
                v-model.number="draft.guestCount"
                :label="t('common.fields.guestCount')"
                type="number"
                min="0"
                inputmode="numeric"
                :disabled="readOnly"
              />
              <WInput
                v-model="draft.venue"
                class="sm:col-span-2"
                :label="t('quotes.fields.venue')"
                :error="errors.venue"
                maxlength="160"
                :disabled="readOnly"
              />
            </div>
          </WCard>

          <CatalogPicker v-if="!readOnly" @pick="addFromCatalog" />

          <WCard :title="t('quotes.sections.lines')">
            <template v-if="!readOnly" #actions>
              <WButton variant="secondary" size="sm" @click="addFreeLine"
                ><Plus class="size-[15px]" aria-hidden="true" />{{ t('quotes.freeLine') }}</WButton
              >
            </template>
            <p
              v-if="!draft.lines.length"
              class="rounded-wd border border-dashed border-line-2 p-7 text-center text-muted"
            >
              {{ t('quotes.noLines') }}
            </p>
            <ol v-else class="-my-1 divide-y divide-line">
              <li
                v-for="(line, index) in draft.lines"
                :key="index"
                class="grid grid-cols-[minmax(0,1fr)_84px_118px_32px] items-center gap-2.5 py-2.5"
                data-testid="quote-line"
              >
                <div class="min-w-0">
                  <input
                    v-model="line.label"
                    class="w-full rounded-[8px] border border-transparent bg-transparent px-1.5 py-1 font-bold hover:border-line-2 focus:border-violet focus:outline-none disabled:hover:border-transparent"
                    :class="errors[`line-${index}`] && 'border-red'"
                    :aria-label="t('quotes.lineLabel')"
                    :placeholder="t('quotes.lineLabel')"
                    :disabled="readOnly"
                  />
                  <label class="flex items-center gap-1 px-1.5 text-[12.5px] text-muted">
                    <input
                      v-model.number="line.unitPrice"
                      type="number"
                      min="0"
                      step="500"
                      inputmode="numeric"
                      class="num w-24 rounded-[6px] border border-transparent bg-transparent px-1 hover:border-line-2 focus:border-violet focus:outline-none disabled:hover:border-transparent"
                      :aria-label="t('quotes.columns.unitPrice')"
                      :disabled="readOnly"
                    />
                    FCFA /
                    {{ t(`catalog.units.${line.unit}`).toLowerCase() }}
                  </label>
                  <p v-if="errors[`line-${index}`]" class="px-1.5 text-[13px] font-bold text-red">
                    {{ errors[`line-${index}`] }}
                  </p>
                </div>
                <input
                  v-model.number="line.quantity"
                  type="number"
                  min="0.01"
                  step="any"
                  inputmode="decimal"
                  class="num h-9 w-full rounded-[8px] border border-line-2 bg-surface text-center focus:border-violet focus:shadow-[0_0_0_3px_var(--violet-soft)] focus:outline-none"
                  :aria-label="`${t('quotes.columns.quantity')} : ${line.label}`"
                  :disabled="readOnly"
                />
                <p class="num text-right font-semibold whitespace-nowrap">
                  {{ formatMoney(lineAmount(line.unitPrice, line.quantity)) }}
                </p>
                <WButton
                  v-if="!readOnly"
                  variant="ghost"
                  size="sm"
                  icon
                  :aria-label="t('quotes.removeLine', { name: line.label })"
                  @click="removeLine(index)"
                >
                  <Trash2 class="size-[15px]" aria-hidden="true" />
                </WButton>
              </li>
            </ol>

            <div class="mt-4 grid gap-4 border-t border-line pt-4 sm:grid-cols-2">
              <WInput
                v-model.number="draft.discountPct"
                :label="t('quotes.fields.discountPct')"
                type="number"
                min="0"
                max="100"
                step="0.5"
                :error="errors.discountPct"
                :disabled="readOnly"
              />
              <WInput
                v-model.number="draft.depositPct"
                :label="t('quotes.fields.depositPct')"
                type="number"
                min="0"
                max="100"
                step="5"
                :error="errors.depositPct"
                :disabled="readOnly"
              />
            </div>
            <p class="mt-4 flex items-baseline justify-between gap-3 border-t border-line pt-3">
              <span class="font-bold">{{ t('quotes.total') }}</span>
              <span class="num text-[17px] font-semibold" data-testid="editor-total">{{
                formatMoney(totals.total)
              }}</span>
            </p>
          </WCard>

          <WCard :title="t('quotes.sections.conditions')">
            <div class="grid gap-4">
              <WInput
                v-model="draft.validUntil"
                class="sm:max-w-[240px]"
                :label="t('quotes.fields.validUntil')"
                type="date"
                :error="errors.validUntil"
                :disabled="readOnly"
              />
              <WTextarea
                v-model="draft.paymentTerms"
                :label="t('quotes.fields.paymentTerms')"
                :rows="2"
                :disabled="readOnly"
              />
              <WTextarea
                v-model="draft.notes"
                :label="t('quotes.fields.notes')"
                :rows="2"
                :disabled="readOnly"
              />
              <WInput
                v-model="draft.tagline"
                :label="t('quotes.fields.tagline')"
                :placeholder="designs.data.value?.defaultTagline"
                :hint="t('quotes.fields.taglineHint')"
                :error="errors.tagline"
                maxlength="140"
                :disabled="readOnly"
              />
            </div>
          </WCard>

          <WCard :title="t('quotes.sections.partners')" :subtitle="t('quotes.partners.subtitle')">
            <div class="flex flex-col gap-4">
              <fieldset
                v-for="(partner, index) in draft.partners"
                :key="index"
                class="grid gap-3 rounded-wd border border-line p-3.5 sm:grid-cols-2"
              >
                <legend class="sr-only">{{ t('quotes.partners.legend', { n: index + 1 }) }}</legend>
                <WInput
                  v-model="partner.name"
                  :label="t('quotes.partners.name')"
                  maxlength="120"
                  :disabled="readOnly"
                />
                <WInput
                  v-model="partner.activity"
                  :label="t('quotes.partners.activity')"
                  maxlength="120"
                  :disabled="readOnly"
                />
                <WInput
                  v-model="partner.signatory"
                  :label="t('quotes.partners.signatory')"
                  maxlength="80"
                  :disabled="readOnly"
                />
                <WInput
                  v-model="partner.signatoryRole"
                  :label="t('quotes.partners.signatoryRole')"
                  maxlength="60"
                  :disabled="readOnly"
                />
                <div v-if="!readOnly" class="sm:col-span-2">
                  <WButton variant="ghost" size="sm" @click="draft.partners.splice(index, 1)">
                    <Trash2 class="size-[15px]" aria-hidden="true" />{{
                      t('quotes.partners.remove')
                    }}
                  </WButton>
                </div>
              </fieldset>
              <WButton
                v-if="!readOnly && draft.partners.length < MAX_PARTNERS"
                variant="secondary"
                size="sm"
                class="self-start"
                @click="addPartner"
              >
                <Plus class="size-[15px]" aria-hidden="true" />{{ t('quotes.partners.add') }}
              </WButton>
            </div>
          </WCard>

          <!-- Secondary actions -->
          <div v-if="quoteId && can('editSales')" class="flex flex-wrap gap-2">
            <WButton variant="ghost" size="sm" @click="copy(false)"
              ><Copy class="size-[15px]" aria-hidden="true" />{{ t('quotes.duplicate') }}</WButton
            >
            <WButton v-if="!isTemplate" variant="ghost" size="sm" @click="copy(true)"
              ><LayoutTemplate class="size-[15px]" aria-hidden="true" />{{
                t('quotes.saveAsTemplate')
              }}</WButton
            >
            <template v-if="!isTemplate && !locked">
              <WButton variant="ghost" size="sm" @click="markAccepted"
                ><Check class="size-[15px]" aria-hidden="true" />{{
                  t('quotes.markAccepted')
                }}</WButton
              >
              <WButton variant="ghost" size="sm" @click="openRefuse"
                ><X class="size-[15px]" aria-hidden="true" />{{ t('quotes.markRefused') }}</WButton
              >
            </template>
            <WButton
              v-if="(status === 'draft' || isTemplate) && can('deleteSales')"
              variant="ghost"
              size="sm"
              class="text-red"
              @click="deleteOpen = true"
            >
              <Trash2 class="size-[15px]" aria-hidden="true" />{{ t('common.delete') }}
            </WButton>
          </div>
        </div>

        <!-- Live preview -->
        <aside class="flex min-w-0 flex-col gap-3 min-[1181px]:sticky min-[1181px]:top-[84px]">
          <div class="flex items-center justify-between gap-3">
            <h2>{{ t('quotes.previewTitle') }}</h2>
            <WButton
              v-if="quoteId"
              size="sm"
              variant="secondary"
              :loading="pdfLoading"
              @click="openPdf"
            >
              <FileDown class="size-[15px]" aria-hidden="true" />{{ t('quotes.document.generate') }}
            </WButton>
          </div>
          <div class="flex flex-wrap items-end gap-3">
            <WSelect
              :model-value="currentDesign"
              class="w-[190px]"
              :label="t('quotes.document.designLabel')"
              :options="designOptions"
              :disabled="readOnly"
              data-testid="design-select"
              @update:model-value="draft.design = $event as QuoteDesign"
            />
            <div
              role="radiogroup"
              :aria-label="t('quotes.document.paletteLabel')"
              class="flex flex-wrap gap-1.5 pb-1"
            >
              <button
                v-for="palette in designs.data.value?.palettes ?? []"
                :key="palette.code"
                type="button"
                role="radio"
                :aria-checked="currentPalette === palette.code"
                :aria-label="palette.name"
                :title="palette.name"
                :disabled="readOnly"
                class="size-7 rounded-full border-2 transition-shadow disabled:opacity-50"
                :class="
                  currentPalette === palette.code
                    ? 'border-violet shadow-[0_0_0_3px_var(--violet-soft)]'
                    : 'border-line-2'
                "
                :style="{
                  background: `linear-gradient(135deg, ${palette.dark} 0 55%, ${palette.accent} 55% 100%)`,
                }"
                @click="draft.palette = palette.code"
              />
            </div>
          </div>
          <ServerPreview :quote-id="quoteId" :draft="payload()" />
        </aside>
      </div>
    </template>

    <WModal v-model:open="sendOpen" :title="t('quotes.send')" size="sm">
      <p v-if="client?.email">
        {{ t('quotes.sendConfirm', { email: client.email, total: formatMoney(totals.total) }) }}
      </p>
      <p v-else class="text-red">{{ t('quotes.noClientEmail') }}</p>
      <template #footer>
        <WButton variant="secondary" @click="sendOpen = false">{{ t('common.cancel') }}</WButton>
        <WButton :loading="send.isPending.value" :disabled="!client?.email" @click="confirmSend"
          ><Send class="size-4" aria-hidden="true" />{{ t('quotes.send') }}</WButton
        >
      </template>
    </WModal>

    <WModal v-model:open="refuseOpen" :title="t('quotes.markRefused')" size="sm">
      <form id="refuse-form" @submit.prevent="confirmRefuse">
        <WTextarea v-model="refuseReason" :label="t('quotes.refuseReason')" :rows="3" autofocus />
      </form>
      <template #footer>
        <WButton variant="secondary" @click="refuseOpen = false">{{ t('common.cancel') }}</WButton>
        <WButton type="submit" form="refuse-form" :loading="refuse.isPending.value">{{
          t('quotes.markRefused')
        }}</WButton>
      </template>
    </WModal>

    <WModal v-model:open="convertOpen" :title="t('quotes.convert')" size="sm">
      <p>{{ t('quotes.convertConfirm', { total: formatMoney(current?.total ?? 0) }) }}</p>
      <ul class="mt-3 list-disc pl-5 text-[13.5px] text-ink-2">
        <li>
          {{ t('quotes.convertDeposit', { amount: formatMoney(current?.depositAmount ?? 0) }) }}
        </li>
        <li>
          {{
            t('quotes.convertBalance', {
              amount: formatMoney((current?.total ?? 0) - (current?.depositAmount ?? 0)),
            })
          }}
        </li>
        <li>{{ t('quotes.convertWedding') }}</li>
      </ul>
      <template #footer>
        <WButton variant="secondary" @click="convertOpen = false">{{ t('common.cancel') }}</WButton>
        <WButton :loading="convert.isPending.value" @click="confirmConvert"
          ><FileSignature class="size-4" aria-hidden="true" />{{ t('quotes.convert') }}</WButton
        >
      </template>
    </WModal>

    <WModal v-model:open="deleteOpen" :title="t('common.delete')" size="sm">
      <p>{{ t('quotes.deleteConfirm') }}</p>
      <template #footer>
        <WButton variant="secondary" @click="deleteOpen = false">{{ t('common.cancel') }}</WButton>
        <WButton variant="danger" @click="confirmDelete">{{ t('common.delete') }}</WButton>
      </template>
    </WModal>
  </div>
</template>

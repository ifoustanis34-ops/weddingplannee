<script setup lang="ts">
import { Ban, CalendarPlus, CircleCheck, CircleX, Download } from '@lucide/vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import { toApiError } from '@/api/errors'
import { formatDateTime } from '@/composables/useDate'
import { WButton, WEmptyState } from '@/design'

import { publicTicketApi } from '../api'

/**
 * The guest's page, opened from the QR or the email (docs/specs/devis-billets.md §6): their
 * ticket as an image, the PDF, the calendar, and the answer. It never records an entry.
 */
const { t } = useI18n()
const route = useRoute()
const queryClient = useQueryClient()
const token = computed(() => String(route.params.token))
const key = computed(() => ['public-ticket', token.value])
const ticket = useQuery({
  queryKey: key,
  queryFn: () => publicTicketApi.get(token.value),
  retry: false,
})

const busy = ref(false)
const error = ref<string | null>(null)
async function answer(accepted: boolean): Promise<void> {
  busy.value = true
  error.value = null
  try {
    const result = await publicTicketApi.rsvp(token.value, accepted)
    queryClient.setQueryData(key.value, {
      ...ticket.data.value!,
      guest: { ...ticket.data.value!.guest, rsvpStatus: result.rsvpStatus },
    })
  } catch (failure) {
    error.value = toApiError(failure).message
  } finally {
    busy.value = false
  }
}
const active = computed(() => ticket.data.value?.status === 'active')
</script>

<template>
  <main class="min-h-dvh bg-bg px-4 py-6 sm:px-6 sm:py-10">
    <div class="mx-auto flex max-w-3xl flex-col gap-5">
      <div
        v-if="ticket.isPending.value"
        class="skeleton aspect-[200/118]"
        :aria-label="t('common.loading')"
      />

      <WEmptyState
        v-else-if="ticket.isError.value || !ticket.data.value"
        :title="t('tickets.public.notFound')"
        :description="t('tickets.public.notFoundText')"
      />

      <template v-else>
        <header class="flex flex-col gap-1">
          <p class="text-[13px] font-bold text-muted">{{ ticket.data.value.agency }}</p>
          <h1 class="text-[26px] font-semibold">
            {{ t('tickets.public.title', { couple: ticket.data.value.couple }) }}
          </h1>
          <p class="text-muted">
            {{
              t(
                'tickets.public.for',
                { name: ticket.data.value.guest.name, count: ticket.data.value.guest.seats },
                ticket.data.value.guest.seats,
              )
            }}
            <template v-if="ticket.data.value.startsAt">
              · {{ formatDateTime(ticket.data.value.startsAt) }}</template
            >
          </p>
        </header>

        <div
          v-if="!active"
          class="flex items-center gap-3 rounded-wd border-l-[3px] border-red bg-red-soft px-4 py-3"
          role="status"
        >
          <Ban class="size-5 text-red" aria-hidden="true" />{{ t('tickets.public.cancelled') }}
        </div>
        <div
          v-else-if="ticket.data.value.guest.rsvpStatus === 'accepted'"
          class="flex items-center gap-3 rounded-wd border-l-[3px] border-green bg-green-soft px-4 py-3"
          role="status"
        >
          <CircleCheck class="size-5 text-green" aria-hidden="true" />{{
            t('tickets.public.accepted')
          }}
        </div>
        <div
          v-else-if="ticket.data.value.guest.rsvpStatus === 'declined'"
          class="flex items-center gap-3 rounded-wd border-l-[3px] border-coral bg-coral-soft px-4 py-3"
          role="status"
        >
          <CircleX class="size-5 text-coral" aria-hidden="true" />{{ t('tickets.public.declined') }}
        </div>

        <p
          v-if="error"
          class="rounded-r-wd border-l-[3px] border-red bg-red-soft px-4 py-3"
          role="alert"
        >
          {{ error }}
        </p>

        <div v-if="active" class="flex flex-wrap gap-2">
          <WButton
            v-if="ticket.data.value.guest.rsvpStatus !== 'accepted'"
            :loading="busy"
            @click="answer(true)"
            ><CircleCheck class="size-4" aria-hidden="true" />{{
              t('tickets.public.accept')
            }}</WButton
          >
          <WButton
            v-if="ticket.data.value.guest.rsvpStatus !== 'declined'"
            variant="secondary"
            :disabled="busy"
            @click="answer(false)"
            >{{ t('tickets.public.decline') }}</WButton
          >
          <a
            :href="publicTicketApi.pdfUrl(token)"
            class="inline-flex h-10 items-center gap-2 rounded-[10px] border border-line bg-surface px-4 font-bold hover:bg-surface-2"
          >
            <Download class="size-4" aria-hidden="true" />{{ t('tickets.public.download') }}
          </a>
          <a
            :href="publicTicketApi.icsUrl(token)"
            class="inline-flex h-10 items-center gap-2 rounded-[10px] border border-line bg-surface px-4 font-bold hover:bg-surface-2"
          >
            <CalendarPlus class="size-4" aria-hidden="true" />{{ t('tickets.public.calendar') }}
          </a>
        </div>

        <!-- The ticket itself, the same image as the PDF: shown at the door from the phone. -->
        <img
          v-if="active"
          :src="publicTicketApi.imageUrl(token)"
          :alt="t('tickets.public.imageAlt', { code: ticket.data.value.code })"
          class="w-full rounded-[14px] border border-[#E5E2F0] bg-white shadow-wd"
          data-testid="public-ticket"
        />
        <p class="text-center text-[12px] text-muted">{{ t('tickets.public.hint') }}</p>
      </template>
    </div>
  </main>
</template>

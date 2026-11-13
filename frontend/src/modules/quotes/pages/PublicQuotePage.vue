<script setup lang="ts">
import { CircleCheck, CircleX, Download, TimerOff } from '@lucide/vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import { toApiError } from '@/api/errors'
import { formatDate } from '@/composables/useDate'
import { formatMoney } from '@/composables/useMoney'
import { WButton, WEmptyState, WModal, WTextarea } from '@/design'

import { publicQuoteApi } from '../api'

/** What the couple sees from the email link: no account, no internal data (CLAUDE.md §7.3). */
const { t } = useI18n()
const route = useRoute()
const queryClient = useQueryClient()
const token = computed(() => String(route.params.token))
const key = computed(() => ['public-quote', token.value])
const quote = useQuery({
  queryKey: key,
  queryFn: () => publicQuoteApi.get(token.value),
  retry: false,
})

const acceptOpen = ref(false)
const refuseOpen = ref(false)
function openRefuse(): void {
  reason.value = ''
  refuseOpen.value = true
}
const reason = ref('')
const busy = ref(false)
const error = ref<string | null>(null)

async function decide(kind: 'accept' | 'refuse'): Promise<void> {
  busy.value = true
  error.value = null
  try {
    const result =
      kind === 'accept'
        ? await publicQuoteApi.accept(token.value)
        : await publicQuoteApi.refuse(token.value, reason.value)
    queryClient.setQueryData(key.value, result)
    acceptOpen.value = false
    refuseOpen.value = false
  } catch (failure) {
    error.value = toApiError(failure).message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="min-h-dvh bg-bg px-4 py-6 sm:px-6 sm:py-10">
    <div class="mx-auto flex max-w-3xl flex-col gap-5">
      <div
        v-if="quote.isPending.value"
        class="skeleton h-[560px]"
        :aria-label="t('common.loading')"
      />

      <WEmptyState
        v-else-if="quote.isError.value || !quote.data.value"
        :title="t('quotes.public.notFound')"
        :description="t('quotes.public.notFoundText')"
      />

      <template v-else>
        <header class="flex flex-col gap-1">
          <p class="text-[13px] font-bold text-muted">{{ quote.data.value.organization.name }}</p>
          <h1 class="text-[26px] font-semibold">
            {{ t('quotes.public.title', { name: quote.data.value.clientName }) }}
          </h1>
          <p class="text-muted">
            {{
              t('quotes.public.subtitle', {
                total: formatMoney(quote.data.value.total),
                date: formatDate(quote.data.value.validUntil),
              })
            }}
          </p>
        </header>

        <div
          v-if="quote.data.value.status === 'accepted'"
          class="flex items-center gap-3 rounded-wd border-l-[3px] border-green bg-green-soft px-4 py-3"
          role="status"
        >
          <CircleCheck class="size-5 text-green" aria-hidden="true" />{{
            t('quotes.public.accepted')
          }}
        </div>
        <div
          v-else-if="quote.data.value.status === 'refused'"
          class="flex items-center gap-3 rounded-wd border-l-[3px] border-red bg-red-soft px-4 py-3"
          role="status"
        >
          <CircleX class="size-5 text-red" aria-hidden="true" />{{ t('quotes.public.refused') }}
        </div>
        <div
          v-else-if="quote.data.value.status === 'expired'"
          class="flex items-center gap-3 rounded-wd border-l-[3px] border-gold-bright bg-gold-soft px-4 py-3"
          role="status"
        >
          <TimerOff class="size-5 text-gold" aria-hidden="true" />{{ t('quotes.public.expired') }}
        </div>

        <p
          v-if="error"
          class="rounded-r-wd border-l-[3px] border-red bg-red-soft px-4 py-3"
          role="alert"
        >
          {{ error }}
        </p>

        <div class="flex flex-wrap gap-2">
          <template v-if="quote.data.value.status === 'sent'">
            <WButton @click="acceptOpen = true"
              ><CircleCheck class="size-4" aria-hidden="true" />{{
                t('quotes.public.accept')
              }}</WButton
            >
            <WButton variant="secondary" @click="openRefuse">{{
              t('quotes.public.refuse')
            }}</WButton>
          </template>
          <a
            :href="publicQuoteApi.pdfUrl(token)"
            class="inline-flex h-10 items-center gap-2 rounded-[10px] border border-line bg-surface px-4 font-bold hover:bg-surface-2"
          >
            <Download class="size-4" aria-hidden="true" />{{ t('quotes.public.download') }}
          </a>
        </div>

        <!-- The document the couple received: the same image as the PDF (devis-billets.md §3). -->
        <img
          :src="publicQuoteApi.previewUrl(token)"
          :alt="t('quotes.public.documentAlt', { number: quote.data.value.number })"
          class="w-full rounded-[14px] border border-[#E5E2F0] bg-white shadow-wd"
          data-testid="public-preview"
        />
        <p class="text-center text-[12px] text-muted">{{ t('quotes.public.poweredBy') }}</p>
      </template>
    </div>

    <WModal v-model:open="acceptOpen" :title="t('quotes.public.accept')" size="sm">
      <p>
        {{
          t('quotes.public.acceptConfirm', {
            total: formatMoney(quote.data.value?.total ?? 0),
            organization: quote.data.value?.organization.name ?? '',
          })
        }}
      </p>
      <template #footer>
        <WButton variant="secondary" @click="acceptOpen = false">{{ t('common.cancel') }}</WButton>
        <WButton :loading="busy" @click="decide('accept')">{{ t('quotes.public.accept') }}</WButton>
      </template>
    </WModal>
    <WModal v-model:open="refuseOpen" :title="t('quotes.public.refuse')" size="sm">
      <form id="public-refuse" @submit.prevent="decide('refuse')">
        <WTextarea v-model="reason" :label="t('quotes.public.refuseReason')" :rows="3" autofocus />
      </form>
      <template #footer>
        <WButton variant="secondary" @click="refuseOpen = false">{{ t('common.cancel') }}</WButton>
        <WButton type="submit" form="public-refuse" :loading="busy">{{
          t('quotes.public.refuse')
        }}</WButton>
      </template>
    </WModal>
  </main>
</template>

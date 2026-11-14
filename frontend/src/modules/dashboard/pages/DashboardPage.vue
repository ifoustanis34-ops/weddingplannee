<script setup lang="ts">
import { Check, FileText, LockKeyhole, MailWarning, Receipt, Sparkles } from '@lucide/vue'
import { useQuery } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { authApi } from '@/api/auth'
import { toApiError } from '@/api/errors'
import { organizationApi } from '@/api/organization'
import { visibleNavItems } from '@/app/navigation'
import { DEFAULT_TIMEZONE, daysBetween, formatDate } from '@/composables/useDate'
import { usePermissions } from '@/composables/usePermissions'
import { useToast } from '@/composables/useToast'
import { WBadge, WButton, WCard, WEmptyState } from '@/design'
import ExpenseModal from '@/modules/finance/components/ExpenseModal.vue'
import PaymentModal from '@/modules/finance/components/PaymentModal.vue'
import { useSessionStore } from '@/stores/session'

import { type PeriodKey, type PeriodRequest, useDashboard } from '../api'
import AlertsCard from '../components/AlertsCard.vue'
import BalancesCard from '../components/BalancesCard.vue'
import MaterialCard from '../components/MaterialCard.vue'
import ExpenseRingCard from '../components/ExpenseRingCard.vue'
import MoneyChartCard from '../components/MoneyChartCard.vue'
import OrdersCard from '../components/OrdersCard.vue'
import PerformanceCard from '../components/PerformanceCard.vue'
import PeriodPicker from '../components/PeriodPicker.vue'
import PlanningCard from '../components/PlanningCard.vue'
import SignatureCard from '../components/SignatureCard.vue'
import TeamCard from '../components/TeamCard.vue'
import TopServicesCard from '../components/TopServicesCard.vue'

/**
 * Management dashboard (reservations-stock.md §8): in ten seconds, how the business is doing and
 * what to do today. One strong zone (signature), crisp figures, quiet charts; every block follows
 * the period. Figures come from the server, already filtered by role.
 */
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const toast = useToast()
const { can } = usePermissions()

// --- Period, kept in the address (?periode=…&du=…&au=…) -------------------------------------
const PERIOD_KEYS: PeriodKey[] = ['today', 'week', 'month', 'quarter', 'year', 'custom']
const period = computed<PeriodRequest>({
  get: (): PeriodRequest => {
    const key = String(route.query.periode ?? 'month') as PeriodKey
    if (!PERIOD_KEYS.includes(key)) return { period: 'month' }
    if (key === 'custom') {
      const from = typeof route.query.du === 'string' ? route.query.du : ''
      const to = typeof route.query.au === 'string' ? route.query.au : ''
      return from && to ? { period: 'custom', from, to } : { period: 'month' }
    }
    return { period: key }
  },
  set: (value: PeriodRequest) =>
    void router.replace({
      query: {
        ...route.query,
        periode: value.period === 'month' ? undefined : value.period,
        du: value.from,
        au: value.to,
      },
    }),
})

const dashboard = useDashboard(period)
const data = computed(() => dashboard.data.value)
const organization = useQuery({
  queryKey: computed(() => ['organization', session.currentOrganization?.slug]),
  queryFn: organizationApi.get,
  enabled: computed(() => Boolean(session.currentOrganization)),
})
const timeZone = computed(() => organization.data.value?.timezone ?? DEFAULT_TIMEZONE)

const trialDays = computed(() => {
  // Lifetime access (given by the Wedivo team): no trial to count down.
  if (organization.data.value?.lifetimeAccess) return null
  const ends = organization.data.value?.trialEndsAt
  if (!ends) return null
  const days = daysBetween(new Date(), ends, timeZone.value)
  return days >= 0 ? days : null
})

// --- « Jeudi 12 novembre 2026 · 1 mariage cette semaine, 2 tâches prévues et 1 alerte. » ------
const today = computed(() => {
  const label = new Intl.DateTimeFormat('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: timeZone.value,
  }).format(new Date())
  return label.charAt(0).toUpperCase() + label.slice(1)
})
const summary = computed(() => {
  const d = data.value
  if (!d) return ''
  const parts: string[] = []
  const plural = (key: string, count: number) => t(`dashboard.summary.${key}`, { count }, count)
  if (d.today.deliveriesToday) parts.push(plural('deliveriesToday', d.today.deliveriesToday))
  if (d.today.returnsToday) parts.push(plural('returnsToday', d.today.returnsToday))
  if (d.today.eventsToday) parts.push(plural('eventsToday', d.today.eventsToday))
  if (d.today.weddingsToday) parts.push(plural('weddingsToday', d.today.weddingsToday))
  else if (d.today.weddingsWeek) parts.push(plural('weddingsWeek', d.today.weddingsWeek))
  if (d.today.tasksToday) parts.push(plural('tasksToday', d.today.tasksToday))
  if (d.today.paymentsToday) parts.push(plural('paymentsToday', d.today.paymentsToday))
  if (d.alerts.length) parts.push(plural('alerts', d.alerts.length))
  if (!parts.length) return t('dashboard.summary.calm')
  const last = parts.pop()!
  const sentence = parts.length ? `${parts.join(', ')}${t('dashboard.summary.and')}${last}` : last
  return `${sentence.charAt(0).toUpperCase()}${sentence.slice(1)}.`
})
const periodLabel = computed(() => {
  const p = data.value?.period
  if (!p) return ''
  return p.key === 'custom'
    ? t('dashboard.periods.range', { start: formatDate(p.start), end: formatDate(p.end) })
    : t(`dashboard.periods.${p.key}`).toLowerCase()
})

// --- Starter card (new spaces) ---------------------------------------------------------------
const readyRoutes = computed(
  () =>
    new Set(visibleNavItems(session.role, session.weddingsEnabled).map((item) => item.routeName)),
)
const STARTER = [
  { key: 'catalog', route: 'catalog', done: (s: { catalogItems: number }) => s.catalogItems > 0 },
  { key: 'clients', route: 'clients', done: (s: { clients: number }) => s.clients > 0 },
  {
    key: 'logo',
    route: 'settings',
    params: { tab: 'identite' },
    done: (s: { hasLogo: boolean }) => s.hasLogo,
  },
  {
    key: 'team',
    route: 'settings',
    params: { tab: 'equipe' },
    done: (s: { teamMembers: number }) => s.teamMembers > 1,
  },
] as const
const starterDone = computed(() => {
  const starter = data.value?.starter
  return starter ? STARTER.every((step) => step.done(starter)) : true
})
watch(starterDone, (done, wasDone) => {
  if (done && wasDone === false) toast.success(t('dashboard.starter.done'))
})

const resending = ref(false)
async function resend(): Promise<void> {
  resending.value = true
  try {
    await authApi.resendVerification()
    toast.success(t('dashboard.resent'))
  } catch (error) {
    toast.error(toApiError(error).message)
  } finally {
    resending.value = false
  }
}

const paymentOpen = ref(false)
const paymentContract = ref<string | null>(null)
function recordPayment(contractId: string): void {
  paymentContract.value = contractId
  paymentOpen.value = true
}
const expenseOpen = ref(false)
const canRecord = computed(() => can('manageFinance'))
const canSpend = computed(() => can('viewMargins'))
</script>

<template>
  <div class="flex flex-col gap-[18px]">
    <WEmptyState
      v-if="!session.currentOrganization"
      :icon="LockKeyhole"
      :title="t('dashboard.noOrganization')"
      :description="t('dashboard.noOrganizationText')"
    />

    <template v-else>
      <header class="flex flex-wrap items-end gap-x-6 gap-y-3">
        <div class="min-w-0 flex-1">
          <h1>{{ t('dashboard.greeting', { name: session.firstName }) }}</h1>
          <p class="mt-1 max-w-[70ch] text-ink-2" data-testid="dashboard-summary">
            <span class="text-muted">{{ today }} · </span>{{ summary }}
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <WBadge v-if="trialDays !== null" tone="gold">
            {{
              trialDays === 0
                ? t('dashboard.trialLastDay')
                : t('dashboard.trial', { days: trialDays })
            }}
          </WBadge>
          <WButton v-if="canSpend" variant="secondary" @click="expenseOpen = true">
            <Receipt class="size-[18px]" aria-hidden="true" />{{
              t('dashboard.actions.newExpense')
            }}
          </WButton>
          <WButton v-if="can('editSales')" :to="{ name: 'quote-new' }">
            <FileText class="size-[18px]" aria-hidden="true" />{{ t('dashboard.actions.newQuote') }}
          </WButton>
        </div>
      </header>

      <PeriodPicker v-model="period" />

      <div
        v-if="session.user && !session.user.isVerified"
        class="flex flex-wrap items-center gap-3 rounded-[14px] bg-gold-soft px-4 py-3.5"
        role="status"
      >
        <span
          class="flex size-[38px] shrink-0 items-center justify-center rounded-[10px] bg-surface"
        >
          <MailWarning class="size-[18px] text-gold" aria-hidden="true" />
        </span>
        <div class="min-w-0 flex-1">
          <p class="font-bold text-ink">{{ t('dashboard.verifyTitle') }}</p>
          <p class="text-[13.5px] text-ink-2">{{ t('dashboard.verifyText') }}</p>
        </div>
        <WButton variant="secondary" size="sm" :loading="resending" @click="resend">{{
          t('dashboard.resend')
        }}</WButton>
      </div>

      <!-- Loading: skeletons shaped like the cards -->
      <div
        v-if="dashboard.isPending.value"
        class="grid grid-cols-1 gap-[18px] md:grid-cols-2 xl:grid-cols-12"
        :aria-label="t('common.loading')"
        aria-busy="true"
      >
        <div class="skeleton h-[330px] rounded-wd-lg md:col-span-2 xl:col-span-7" />
        <div class="skeleton h-[330px] rounded-wd-lg md:col-span-2 xl:col-span-5" />
        <div v-for="n in 3" :key="n" class="skeleton h-[250px] rounded-wd-lg xl:col-span-4" />
        <div class="skeleton h-[330px] rounded-wd-lg md:col-span-2 xl:col-span-5" />
        <div class="skeleton h-[330px] rounded-wd-lg xl:col-span-3" />
        <div class="skeleton h-[330px] rounded-wd-lg xl:col-span-4" />
      </div>

      <WEmptyState
        v-else-if="dashboard.isError.value || !data"
        :title="t('dashboard.loadError')"
        :description="toApiError(dashboard.error.value).message"
      >
        <WButton variant="secondary" @click="dashboard.refetch()">{{ t('common.retry') }}</WButton>
      </WEmptyState>

      <template v-else>
        <!-- New space: an engaging empty state and the four first steps -->
        <template v-if="data.isNew">
          <section
            class="dash-in relative isolate overflow-hidden rounded-wd-lg bg-hero p-7 text-hero-ink"
          >
            <Sparkles class="size-6 text-gold-bright" aria-hidden="true" />
            <h2 class="mt-3 font-display text-[24px] font-semibold">
              {{ t('dashboard.empty.title') }}
            </h2>
            <p class="mt-1 max-w-[52ch] text-hero-muted">{{ t('dashboard.empty.text') }}</p>
            <WButton v-if="can('editSales')" class="mt-5" :to="{ name: 'quote-new' }">
              <FileText class="size-[18px]" aria-hidden="true" />{{
                t('dashboard.actions.newQuote')
              }}
            </WButton>
          </section>
          <WCard
            v-if="!starterDone"
            :title="t('dashboard.starter.title')"
            :subtitle="t('dashboard.starter.subtitle')"
            class="dash-in"
          >
            <div class="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
              <component
                :is="readyRoutes.has(step.route) && !step.done(data.starter) ? 'RouterLink' : 'div'"
                v-for="step in STARTER"
                :key="step.key"
                :to="{ name: step.route, params: 'params' in step ? step.params : undefined }"
                class="flex items-center gap-3 rounded-wd border border-line-2 px-3.5 py-3 font-bold"
                :class="
                  readyRoutes.has(step.route) && !step.done(data.starter)
                    ? 'hover:bg-surface-2'
                    : 'cursor-default'
                "
              >
                <span
                  class="flex size-[22px] shrink-0 items-center justify-center rounded-full border-2"
                  :class="
                    step.done(data.starter) ? 'border-green bg-green text-white' : 'border-line-2'
                  "
                  aria-hidden="true"
                >
                  <Check v-if="step.done(data.starter)" class="size-3.5" />
                </span>
                <span
                  class="min-w-0 flex-1"
                  :class="step.done(data.starter) && 'text-muted line-through'"
                >
                  {{ t(`dashboard.checklist.${step.key}.title`) }}
                  <span class="sr-only">{{
                    step.done(data.starter) ? t('dashboard.starter.stepDone') : ''
                  }}</span>
                </span>
              </component>
            </div>
          </WCard>
        </template>

        <div
          v-else
          class="grid grid-cols-1 gap-[18px] transition-opacity md:grid-cols-2 xl:grid-cols-12"
          :class="dashboard.isPlaceholderData.value && 'opacity-60'"
          :aria-busy="dashboard.isFetching.value"
        >
          <!-- Row 1: the signature zone and performance -->
          <div class="dash-in order-1 md:col-span-2 xl:order-none xl:col-span-7" style="--i: 0">
            <SignatureCard
              :signature="data.signature"
              :monthly="data.monthly"
              :today="data.today"
              :alerts="data.alerts.length"
              :period-label="periodLabel"
            />
          </div>
          <div
            v-if="data.performance"
            class="dash-in order-4 md:col-span-2 xl:order-none xl:col-span-5"
            style="--i: 1"
          >
            <PerformanceCard :performance="data.performance" />
          </div>

          <!-- Row 2: activity -->
          <div class="dash-in order-4 xl:order-none xl:col-span-4" style="--i: 2">
            <OrdersCard :orders="data.orders" />
          </div>
          <div class="dash-in order-4 xl:order-none xl:col-span-4" style="--i: 3">
            <MaterialCard :material="data.materialToday" />
          </div>
          <div class="dash-in order-4 md:col-span-2 xl:order-none xl:col-span-4" style="--i: 4">
            <TopServicesCard :services="data.topServices" />
          </div>

          <!-- Row 3: money -->
          <div
            v-if="data.monthly"
            class="dash-in order-4 md:col-span-2 xl:order-none xl:col-span-5"
            style="--i: 5"
          >
            <MoneyChartCard :monthly="data.monthly" />
          </div>
          <div
            v-if="data.expensesByCategory"
            class="dash-in order-4 xl:order-none xl:col-span-3"
            style="--i: 6"
          >
            <ExpenseRingCard :rows="data.expensesByCategory" />
          </div>
          <div
            v-if="data.balances"
            class="dash-in order-4 xl:order-none"
            :class="data.expensesByCategory ? 'xl:col-span-4' : 'xl:col-span-7'"
            style="--i: 7"
          >
            <BalancesCard
              :balances="data.balances"
              :can-record="canRecord"
              @record="recordPayment"
            />
          </div>

          <!-- Row 4: today and alerts (on mobile, alerts then planning come right after the
               signature: reservations-stock.md §8) -->
          <div
            class="dash-in order-3 md:col-span-2 xl:order-none xl:col-span-7 xl:row-span-2"
            style="--i: 8"
          >
            <PlanningCard :days="data.planning" />
          </div>
          <div class="dash-in order-2 md:col-span-2 xl:order-none xl:col-span-5" style="--i: 9">
            <AlertsCard :alerts="data.alerts" :can-record="canRecord" @record="recordPayment" />
          </div>
          <div class="dash-in order-4 md:col-span-2 xl:order-none xl:col-span-5" style="--i: 10">
            <TeamCard :team="data.teamToday" />
          </div>
        </div>
      </template>
    </template>

    <PaymentModal v-if="canRecord" v-model:open="paymentOpen" :contract-id="paymentContract" />
    <ExpenseModal v-if="canSpend" v-model:open="expenseOpen" />
  </div>
</template>

<style scoped>
/* Discreet arrival (reservations-stock.md §8): 8px rise and fade, 40ms apart per card. */
.dash-in {
  animation: dash-rise 420ms cubic-bezier(0.2, 0.7, 0.2, 1) both;
  animation-delay: calc(var(--i, 0) * 40ms);
}
@keyframes dash-rise {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
}
@media (prefers-reduced-motion: reduce) {
  .dash-in {
    animation: none;
  }
}
</style>

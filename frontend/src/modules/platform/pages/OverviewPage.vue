<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Ban,
  Building2,
  CheckCircle2,
  Clock,
  ExternalLink,
  Hourglass,
  Infinity as InfinityIcon,
  Plus,
  ShieldCheck,
  Sparkles,
  UserPlus,
  UserX,
  Users,
} from '@lucide/vue'
import { type Component, computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { type PlatformOverview, platformApi } from '@/api/platform'
import { formatDate, formatDateTime } from '@/composables/useDate'
import { WAreaChart, WAvatar, WButton, WCard, WEmptyState, WProgress } from '@/design'
import { useSessionStore } from '@/stores/session'

/** Console home: the state of the whole platform, what needs the team, what happened. */
const i18n = useI18n()
const { t } = i18n
const session = useSessionStore()
const overview = useQuery({ queryKey: ['platform', 'overview'], queryFn: platformApi.overview })
const data = computed(() => overview.data.value)
const firstName = computed(() => session.user?.fullName.split(' ')[0] ?? '')

const today = computed(() => {
  const label = new Intl.DateTimeFormat('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(new Date())
  return label.charAt(0).toUpperCase() + label.slice(1)
})

const percent = (part: number, total: number) => (total ? Math.round((part / total) * 100) : 0)

const kpis = computed(() => {
  const d = data.value
  if (!d) return []
  return [
    {
      key: 'agencies',
      icon: Building2,
      value: d.agencies.active,
      hint: t('platform.overview.kpi.agenciesOf', { total: d.agencies.total }),
      to: { name: 'platform-agencies', query: { statut: 'active' } },
    },
    {
      key: 'engaged',
      icon: Activity,
      value: d.agencies.engaged,
      hint: t('platform.overview.kpi.engagedRate', {
        rate: percent(d.agencies.engaged, d.agencies.active),
      }),
      to: { name: 'platform-agencies' },
    },
    {
      key: 'accounts',
      icon: Users,
      value: d.users.active,
      hint: t('platform.overview.kpi.accountsOf', { count: d.users.seenThisMonth }),
      to: { name: 'platform-accounts', query: { statut: 'active' } },
    },
    {
      key: 'newAgencies',
      icon: Sparkles,
      value: d.agencies.newThisMonth,
      hint: t('platform.overview.kpi.newAccounts', { count: d.users.newThisMonth }),
      to: { name: 'platform-agencies' },
    },
  ]
})

const MONTH = new Intl.DateTimeFormat('fr-FR', { month: 'short' })
const growthPoints = computed(() =>
  (data.value?.growth ?? []).map((m) => ({
    label: MONTH.format(new Date(`${m.month}T12:00:00`)).replace('.', ''),
    value: m.agencies,
  })),
)
const growthTotal = computed(() => growthPoints.value.reduce((sum, p) => sum + p.value, 0))
const growthLabel = computed(() =>
  growthPoints.value.map((p) => `${p.label} : ${p.value}`).join(', '),
)
const accountsTotal = computed(() =>
  (data.value?.growth ?? []).reduce((sum, m) => sum + m.accounts, 0),
)

interface StatusRow {
  key: string
  icon: Component
  tone: string
  value: number
  route: 'platform-agencies' | 'platform-accounts'
  label: string
}
const statusRows = computed<StatusRow[]>(() => {
  const a = data.value?.agencies
  const u = data.value?.users
  if (!a || !u) return []
  const agency = (key: string, icon: Component, tone: string, value: number): StatusRow => ({
    key,
    icon,
    tone,
    value,
    route: 'platform-agencies',
    label: t(`platform.agencies.statuses.${key}`),
  })
  const account = (key: string, icon: Component, tone: string, value: number): StatusRow => ({
    key,
    icon,
    tone,
    value,
    route: 'platform-accounts',
    label: t(`platform.accounts.statuses.${key}`),
  })
  return [
    agency('lifetime', InfinityIcon, 'text-violet bg-violet-soft', a.lifetime),
    agency('trial', Hourglass, 'text-gold bg-gold-soft', a.inTrial),
    agency('trial_over', Clock, 'text-muted bg-grey-soft', a.trialOver),
    agency('suspended', Ban, 'text-red bg-red-soft', a.suspended),
    account('admins', ShieldCheck, 'text-violet bg-violet-soft', u.admins),
    account('inactive', UserX, 'text-red bg-red-soft', u.inactive),
  ]
})
const planTotal = computed(() =>
  Math.max(1, data.value?.plans.reduce((sum, plan) => sum + plan.count, 0) ?? 1),
)

type WatchKind = PlatformOverview['watchlist'][number]['kind']
const WATCH_TONE: Record<WatchKind, string> = {
  trial_ending: 'bg-gold-soft text-gold',
  trial_ended: 'bg-grey-soft text-muted',
  suspended: 'bg-red-soft text-red',
}
const WATCH_ICON: Record<WatchKind, Component> = {
  trial_ending: Hourglass,
  trial_ended: Clock,
  suspended: Ban,
}

function actionLabel(action: string): string {
  const key = `platform.journal.actions.${action.replace('.', '_')}`
  return i18n.te(key) ? t(key) : action
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-[1240px] flex-col gap-5">
    <!-- Loading -->
    <template v-if="overview.isPending.value">
      <div class="skeleton h-[230px] rounded-wd-lg" />
      <div class="grid gap-5 xl:grid-cols-12">
        <div class="skeleton h-[320px] rounded-wd-lg xl:col-span-8" />
        <div class="skeleton h-[320px] rounded-wd-lg xl:col-span-4" />
      </div>
    </template>

    <WEmptyState
      v-else-if="overview.isError.value"
      :title="t('platform.common.loadError')"
      :description="toApiError(overview.error.value).message"
    >
      <WButton variant="secondary" @click="overview.refetch()">{{ t('common.retry') }}</WButton>
    </WEmptyState>

    <template v-else-if="data">
      <!-- Hero: greeting, key figures, quick actions -->
      <section
        class="console-in relative isolate overflow-hidden rounded-wd-lg bg-hero p-5 text-hero-ink sm:p-7"
      >
        <div
          class="pointer-events-none absolute -top-28 -right-20 -z-10 size-80 rounded-full bg-fuchsia opacity-25 blur-[100px]"
          aria-hidden="true"
        />
        <div
          class="pointer-events-none absolute -bottom-32 left-1/4 -z-10 size-72 rounded-full bg-violet opacity-30 blur-[100px]"
          aria-hidden="true"
        />
        <div class="flex flex-wrap items-start gap-x-6 gap-y-4">
          <div class="min-w-0 flex-1">
            <p class="text-[13px] font-semibold text-hero-muted">{{ today }}</p>
            <h1 class="mt-1 font-display text-[28px] leading-tight font-semibold">
              {{ t('platform.overview.greeting', { name: firstName }) }}
            </h1>
            <p class="mt-1 text-hero-muted">{{ t('platform.overview.heroText') }}</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <WButton :to="{ name: 'platform-agencies', query: { nouvelle: '1' } }"
              ><Plus class="size-[18px]" aria-hidden="true" />{{
                t('platform.overview.actions.newAgency')
              }}</WButton
            >
            <RouterLink
              :to="{ name: 'platform-accounts', query: { nouvelle: '1' } }"
              class="inline-flex h-10 items-center gap-2 rounded-[10px] border border-white/20 bg-white/10 px-4 text-[14px] font-bold text-hero-ink transition-colors hover:bg-white/20"
              ><UserPlus class="size-[18px]" aria-hidden="true" />{{
                t('platform.overview.actions.newAccount')
              }}</RouterLink
            >
          </div>
        </div>

        <div class="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <RouterLink
            v-for="kpi in kpis"
            :key="kpi.key"
            :to="kpi.to"
            class="group rounded-wd border border-white/10 bg-white/[0.06] p-4 transition-colors hover:bg-white/[0.11]"
          >
            <span class="flex items-center justify-between gap-2">
              <span class="text-[13px] font-semibold text-hero-muted">{{
                t(`platform.overview.kpi.${kpi.key}`)
              }}</span>
              <component
                :is="kpi.icon"
                class="size-[18px] shrink-0 text-gold-bright transition-transform group-hover:scale-110"
                aria-hidden="true"
              />
            </span>
            <span
              class="num mt-2 block text-[30px] leading-none font-semibold tracking-[-0.02em]"
              >{{ kpi.value }}</span
            >
            <span class="mt-2 block truncate text-[12.5px] text-hero-muted">{{ kpi.hint }}</span>
          </RouterLink>
        </div>
      </section>

      <!-- Growth + offers and statuses -->
      <div class="grid gap-5 xl:grid-cols-12 xl:items-start">
        <WCard
          class="console-in xl:col-span-8"
          style="--i: 1"
          :title="t('platform.overview.growth')"
          :subtitle="t('platform.overview.growthSubtitle')"
        >
          <template #actions>
            <div class="text-right">
              <p class="num text-[22px] leading-none font-semibold">{{ growthTotal }}</p>
              <p class="mt-1 text-[12.5px] text-muted">
                {{ t('platform.overview.growthAccounts') }} :
                <span class="num font-semibold text-ink-2">{{ accountsTotal }}</span>
              </p>
            </div>
          </template>
          <WAreaChart
            :points="growthPoints"
            :label="growthLabel"
            :format-tick="(v: number) => String(Math.round(v))"
            :format-value="(v: number) => String(v)"
          />
        </WCard>

        <WCard
          class="console-in xl:col-span-4"
          style="--i: 2"
          :title="t('platform.overview.plans')"
        >
          <ul class="flex flex-col gap-4">
            <li v-for="plan in data.plans" :key="plan.code">
              <div class="mb-1.5 flex items-baseline justify-between text-[14px]">
                <span class="font-semibold">{{ plan.label }}</span>
                <span class="text-[13px] text-muted"
                  ><span class="num font-semibold text-ink">{{ plan.count }}</span> ·
                  {{ percent(plan.count, planTotal) }} %</span
                >
              </div>
              <WProgress :value="(plan.count / planTotal) * 100" :label="plan.label" ribbon />
            </li>
          </ul>
          <div class="mt-6 border-t border-line pt-4">
            <p class="mb-3 text-[12.5px] font-bold text-muted">
              {{ t('platform.overview.statuses') }}
            </p>
            <div class="grid grid-cols-2 gap-2">
              <RouterLink
                v-for="row in statusRows"
                :key="`${row.route}-${row.key}`"
                :to="{ name: row.route, query: { statut: row.key } }"
                class="flex items-center gap-2.5 rounded-wd border border-line px-3 py-2.5 hover:bg-surface-2"
              >
                <span
                  class="flex size-8 shrink-0 items-center justify-center rounded-[9px]"
                  :class="row.tone"
                >
                  <component :is="row.icon" class="size-4" aria-hidden="true" />
                </span>
                <span class="min-w-0">
                  <span class="num block text-[17px] leading-tight font-semibold">{{
                    row.value
                  }}</span>
                  <span class="block text-[12px] leading-tight text-muted">{{ row.label }}</span>
                </span>
              </RouterLink>
            </div>
          </div>
        </WCard>
      </div>

      <!-- Watchlist + activity -->
      <div class="grid gap-5 lg:grid-cols-2">
        <WCard
          class="console-in"
          style="--i: 3"
          :title="t('platform.overview.watch')"
          :subtitle="t('platform.overview.watchSubtitle')"
        >
          <template #actions>
            <AlertTriangle
              v-if="data.watchlist.length"
              class="size-5 text-gold"
              aria-hidden="true"
            />
          </template>
          <p
            v-if="!data.watchlist.length"
            class="flex items-center gap-2.5 rounded-wd bg-green-soft px-3.5 py-3 text-[13.5px] font-semibold text-green"
          >
            <CheckCircle2 class="size-[18px] shrink-0" aria-hidden="true" />{{
              t('platform.overview.watchEmpty')
            }}
          </p>
          <ul v-else class="flex flex-col">
            <li v-for="item in data.watchlist" :key="`${item.kind}-${item.id}`">
              <RouterLink
                :to="{ name: 'platform-agencies', query: { agence: item.id } }"
                class="-mx-2 flex items-center gap-3 rounded-wd px-2 py-2.5 hover:bg-surface-2"
              >
                <span
                  class="flex size-9 shrink-0 items-center justify-center rounded-[10px]"
                  :class="WATCH_TONE[item.kind]"
                >
                  <component :is="WATCH_ICON[item.kind]" class="size-4" aria-hidden="true" />
                </span>
                <span class="min-w-0 flex-1">
                  <span class="block truncate font-semibold">{{ item.name }}</span>
                  <span class="block truncate text-[12.5px] text-muted">{{
                    item.ownerEmail ?? item.slug
                  }}</span>
                  <span class="block text-[12.5px] font-semibold text-ink-2 sm:hidden">{{
                    t(`platform.overview.watchKinds.${item.kind}`, {
                      date: item.at ? formatDate(item.at) : '—',
                    })
                  }}</span>
                </span>
                <span
                  class="hidden shrink-0 text-right text-[12.5px] font-semibold text-ink-2 sm:block"
                  >{{
                    t(`platform.overview.watchKinds.${item.kind}`, {
                      date: item.at ? formatDate(item.at) : '—',
                    })
                  }}</span
                >
              </RouterLink>
            </li>
          </ul>
        </WCard>

        <WCard class="console-in" style="--i: 4" :title="t('platform.overview.activity')">
          <template #actions>
            <WButton size="sm" variant="ghost" :to="{ name: 'platform-journal' }"
              >{{ t('platform.overview.seeJournal')
              }}<ArrowUpRight class="size-[15px]" aria-hidden="true"
            /></WButton>
          </template>
          <p v-if="!data.activity.length" class="text-[13.5px] text-muted">
            {{ t('platform.overview.activityEmpty') }}
          </p>
          <ol v-else class="relative flex flex-col gap-4 pl-5">
            <span class="absolute top-1.5 bottom-1.5 left-[5px] w-px bg-line" aria-hidden="true" />
            <li v-for="entry in data.activity" :key="entry.id" class="relative">
              <span
                class="absolute top-1.5 -left-5 size-[11px] rounded-full border-2 border-surface bg-violet"
                aria-hidden="true"
              />
              <p class="text-[14px]">
                <span class="font-semibold">{{ actionLabel(entry.action) }}</span>
                <span class="text-ink-2"> · {{ entry.targetLabel }}</span>
              </p>
              <p class="text-[12.5px] text-muted">
                {{ formatDateTime(entry.createdAt)
                }}<template v-if="entry.actorFullName">
                  · {{ t('platform.journal.by', { name: entry.actorFullName }) }}</template
                >
              </p>
            </li>
          </ol>
        </WCard>
      </div>

      <!-- Latest agencies -->
      <WCard class="console-in" style="--i: 5" :title="t('platform.overview.latest')">
        <template #actions>
          <WButton size="sm" variant="ghost" :to="{ name: 'platform-agencies' }"
            >{{ t('platform.overview.seeAll')
            }}<ArrowUpRight class="size-[15px]" aria-hidden="true"
          /></WButton>
        </template>
        <ul class="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
          <li v-for="agency in data.latestAgencies" :key="agency.id">
            <RouterLink
              :to="{ name: 'platform-agencies', query: { agence: agency.id } }"
              class="flex items-center gap-3 rounded-wd border border-line p-3 hover:bg-surface-2"
            >
              <WAvatar :name="agency.name" />
              <span class="min-w-0">
                <span class="block truncate text-[14px] font-semibold">{{ agency.name }}</span>
                <span class="block truncate text-[12px] text-muted">{{
                  formatDate(agency.createdAt)
                }}</span>
              </span>
            </RouterLink>
          </li>
        </ul>
      </WCard>

      <p
        v-if="data.djangoAdminUrl"
        class="console-in flex flex-wrap items-center gap-2 px-1 text-[13px] text-muted"
        style="--i: 6"
      >
        {{ t('platform.overview.djangoAdminHint') }}
        <a
          :href="data.djangoAdminUrl"
          target="_blank"
          rel="noopener"
          class="inline-flex items-center gap-1 font-semibold text-violet hover:underline"
          >{{ t('platform.overview.djangoAdmin')
          }}<ExternalLink class="size-[13px]" aria-hidden="true"
        /></a>
      </p>
    </template>
  </div>
</template>

<style scoped>
.console-in {
  animation: console-in 0.45s cubic-bezier(0.2, 0.7, 0.2, 1) both;
  animation-delay: calc(var(--i, 0) * 55ms);
}
@keyframes console-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
}
@media (prefers-reduced-motion: reduce) {
  .console-in {
    animation: none;
  }
}
</style>

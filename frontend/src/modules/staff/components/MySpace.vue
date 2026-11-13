<script setup lang="ts">
import { ArrowRight, Clock, MapPin, Navigation, UserRound } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { formatDate, toZonedInput } from '@/composables/useDate'
import { useToast } from '@/composables/useToast'
import { WAreaChart, WAvatar, WBadge, WButton, WCard, WEmptyState, WTile } from '@/design'
import RingChart from '@/modules/dashboard/components/RingChart.vue'
import { KIND_STYLE } from '@/modules/calendar/kinds'
import { useSessionStore } from '@/stores/session'

import { ATTENDANCE_TONES, staffApi, useMissions, useMyOverview, useStaffMutation } from '../api'
import { groupMissions } from '../missions'
import MissionCard from './MissionCard.vue'

/**
 * « Mon espace » (feedback 13/11/2026): the home of a field account (staff, team lead) instead of
 * the agency's dashboard. Their day first (next mission, today's missions), then their own
 * figures as rings and a curve; the team lead also sees and checks in today's team. No amount.
 */
const { t } = useI18n()
const toast = useToast()
const session = useSessionStore()
const overview = useMyOverview()
const missions = useMissions()

const data = computed(() => overview.data.value)
const local = (value: string) => toZonedInput(value)
const today = computed(() => local(new Date().toISOString()).slice(0, 10))
const todays = computed(
  () =>
    groupMissions(missions.data.value?.missions ?? [], today.value, (i) =>
      local(i).slice(0, 10),
    ).find((g) => g.key === 'today')?.items ?? [],
)
const next = computed(() =>
  (missions.data.value?.missions ?? []).find((m) => m.id === data.value?.nextMission),
)
const nextWhen = computed(() => {
  if (!next.value) return ''
  const start = local(next.value.start)
  return t('staff.space.when', { date: formatDate(next.value.start), time: start.slice(11) })
})

const taskItems = computed(() => {
  const tasks = data.value?.tasks ?? { todo: 0, done: 0, validated: 0 }
  return [
    { key: 'todo', value: tasks.todo, color: 'var(--gold-bright)' },
    { key: 'done', value: tasks.done, color: 'var(--violet)' },
    { key: 'validated', value: tasks.validated, color: 'var(--green)' },
  ].map((item) => ({
    ...item,
    label: t(`staff.space.tasks.${item.key}`),
    display: String(item.value),
  }))
})
const taskTotal = computed(() => taskItems.value.reduce((sum, i) => sum + i.value, 0))
const attendanceItems = computed(() => {
  const a = data.value?.attendance ?? { present: 0, late: 0, absent: 0 }
  return [
    { key: 'present', value: a.present, color: 'var(--green)' },
    { key: 'late', value: a.late, color: 'var(--gold-bright)' },
    { key: 'absent', value: a.absent, color: 'var(--red)' },
  ].map((item) => ({
    ...item,
    label: t(`staff.attendance.${item.key}`),
    display: String(item.value),
  }))
})
const attendanceTotal = computed(() => attendanceItems.value.reduce((s, i) => s + i.value, 0))
const hoursPoints = computed(() =>
  (data.value?.hoursByWeek ?? []).map((w) => ({
    label: `${w.week.slice(8, 10)}/${w.week.slice(5, 7)}`,
    value: w.hours,
  })),
)
const hoursLabel = computed(() =>
  hoursPoints.value.map((p) => `${p.label} : ${p.value} h`).join(', '),
)

/** Today's team, one block per reservation (a person may work on two). */
const teamByReservation = computed(() => {
  const groups = new Map<string, NonNullable<typeof data.value>['team']>()
  for (const member of data.value?.team ?? []) {
    groups.set(member.reservation, [...(groups.get(member.reservation) ?? []), member])
  }
  return [...groups.entries()].map(([reservation, members]) => ({ reservation, members }))
})

const check = useStaffMutation(({ id, action }: { id: string; action: 'in' | 'absent' }) =>
  action === 'in' ? staffApi.checkIn(id) : staffApi.absent(id),
)
async function run(id: string, action: 'in' | 'absent'): Promise<void> {
  try {
    await check.mutateAsync({ id, action })
    toast.success(t(`staff.attendancePage.done.${action}`))
    void overview.refetch()
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <WEmptyState
      v-if="overview.isError.value"
      :title="t('staff.space.loadError')"
      :description="toApiError(overview.error.value).message"
    />
    <div v-else-if="overview.isPending.value" class="grid gap-4">
      <div class="skeleton h-52 rounded-wd-lg" />
      <div class="skeleton h-24 rounded-wd-lg" />
    </div>
    <WEmptyState
      v-else-if="!data?.staff"
      :icon="UserRound"
      :title="t('staff.missions.noProfile')"
      :description="t('staff.missions.noProfileText')"
    />
    <template v-else>
      <!-- The day: who I am, what comes next -->
      <section
        class="relative isolate overflow-hidden rounded-wd-lg bg-hero p-5 text-hero-ink sm:p-7"
        :aria-label="t('staff.space.title')"
      >
        <div
          class="pointer-events-none absolute -top-24 -right-16 -z-10 size-72 rounded-full bg-fuchsia opacity-25 blur-[90px]"
          aria-hidden="true"
        />
        <div class="grid gap-6 lg:grid-cols-[1fr_minmax(0,420px)] lg:items-center">
          <div class="flex items-center gap-4">
            <img
              v-if="data.staff.photoUrl"
              :src="data.staff.photoUrl"
              :alt="data.staff.name"
              class="size-16 rounded-full border-2 border-gold-bright object-cover"
            />
            <WAvatar v-else :name="data.staff.name" :size="64" />
            <div class="min-w-0">
              <p class="text-[13px] font-semibold text-hero-muted">
                {{ formatDate(new Date()) }}
              </p>
              <h1 class="text-hero-ink">
                {{ t('staff.space.hello', { name: session.firstName }) }}
              </h1>
              <p class="mt-0.5 text-[13.5px] text-hero-muted">
                {{ [data.staff.position, data.staff.department].filter(Boolean).join(' · ') }}
                <span v-if="data.staff.employeeNumber" class="num whitespace-nowrap">
                  · {{ data.staff.employeeNumber }}</span
                >
              </p>
            </div>
          </div>

          <div class="rounded-[16px] border border-white/10 bg-white/[0.07] p-4">
            <p class="text-[12px] font-bold tracking-wide text-hero-muted uppercase">
              {{ t('staff.space.next') }}
            </p>
            <template v-if="next">
              <p class="mt-1.5 flex items-center gap-2 text-[16px] font-bold">
                <component
                  :is="KIND_STYLE[next.step === 'all' ? 'event' : next.step].icon"
                  class="size-[18px] text-gold-bright"
                  aria-hidden="true"
                />
                {{ next.reservationTitle }}
              </p>
              <p class="mt-1 flex items-center gap-1.5 text-[13px] text-hero-muted">
                <Clock class="size-3.5" aria-hidden="true" />{{ next.stepLabel }} · {{ nextWhen }}
              </p>
              <p
                v-if="next.venue || next.address"
                class="mt-0.5 flex items-start gap-1.5 text-[13px] text-hero-muted"
              >
                <MapPin class="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />{{
                  [next.venue, next.address].filter(Boolean).join(' — ')
                }}
              </p>
              <div class="mt-3 flex flex-wrap gap-2">
                <RouterLink
                  :to="{ name: 'missions' }"
                  class="inline-flex h-9 items-center gap-1.5 rounded-[10px] bg-white px-3.5 text-[13px] font-bold text-hero"
                  >{{ t('staff.space.seeMissions') }}<ArrowRight class="size-4" aria-hidden="true"
                /></RouterLink>
                <a
                  v-if="next.mapsUrl"
                  :href="next.mapsUrl"
                  target="_blank"
                  rel="noopener"
                  class="inline-flex h-9 items-center gap-1.5 rounded-[10px] border border-white/25 px-3.5 text-[13px] font-bold hover:bg-white/10"
                  ><Navigation class="size-4" aria-hidden="true" />{{
                    t('staff.missions.route')
                  }}</a
                >
              </div>
            </template>
            <p v-else class="mt-1.5 text-[14px] text-hero-muted">{{ t('staff.space.noNext') }}</p>
          </div>
        </div>
      </section>

      <!-- My figures -->
      <div class="grid grid-cols-2 gap-3.5 lg:grid-cols-4">
        <WTile :label="t('staff.space.kpi.week')" :value="String(data.missionsWeek)" />
        <WTile :label="t('staff.space.kpi.hours')" :value="`${data.hoursMonth} h`">{{
          t('staff.space.kpi.hoursHint')
        }}</WTile>
        <WTile
          :label="t('staff.space.kpi.punctuality')"
          :value="data.punctuality === null ? '—' : `${data.punctuality} %`"
          >{{ t('staff.space.kpi.punctualityHint') }}</WTile
        >
        <WTile :label="t('staff.space.kpi.todo')" :value="String(data.tasks.todo)" />
      </div>

      <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1.4fr)]">
        <WCard :title="t('staff.space.tasks.title')" :subtitle="t('staff.space.tasks.subtitle')">
          <div class="flex flex-wrap items-center gap-5">
            <RingChart
              :items="taskItems"
              :center-value="String(taskTotal)"
              :center-label="t('staff.space.tasks.total')"
              :label="t('staff.space.tasks.title')"
              :size="132"
            />
            <ul class="flex flex-col gap-2 text-[13.5px]">
              <li v-for="item in taskItems" :key="item.key" class="flex items-center gap-2">
                <span class="size-2.5 rounded-full" :style="{ background: item.color }" />
                <span class="text-ink-2">{{ item.label }}</span>
                <b class="num ml-auto pl-4">{{ item.value }}</b>
              </li>
            </ul>
          </div>
        </WCard>
        <WCard
          :title="t('staff.space.attendance.title')"
          :subtitle="t('staff.space.attendance.subtitle')"
        >
          <div class="flex flex-wrap items-center gap-5">
            <RingChart
              :items="attendanceItems"
              :center-value="data.punctuality === null ? '—' : `${data.punctuality} %`"
              :center-label="t('staff.space.attendance.center')"
              :label="t('staff.space.attendance.title')"
              :size="132"
            />
            <ul class="flex flex-col gap-2 text-[13.5px]">
              <li v-for="item in attendanceItems" :key="item.key" class="flex items-center gap-2">
                <span class="size-2.5 rounded-full" :style="{ background: item.color }" />
                <span class="text-ink-2">{{ item.label }}</span>
                <b class="num ml-auto pl-4">{{ item.value }}</b>
              </li>
            </ul>
          </div>
          <p v-if="!attendanceTotal" class="mt-3 text-[13px] text-muted">
            {{ t('staff.space.attendance.none') }}
          </p>
        </WCard>
        <WCard :title="t('staff.space.hours.title')" :subtitle="t('staff.space.hours.subtitle')">
          <WAreaChart
            :points="hoursPoints"
            :label="hoursLabel"
            :format-tick="(v: number) => `${v} h`"
            :format-value="(v: number) => `${v} h`"
          />
        </WCard>
      </div>

      <!-- Team lead: today's team -->
      <WCard
        v-if="data.team.length"
        :title="t('staff.space.team.title')"
        :subtitle="t('staff.space.team.subtitle')"
      >
        <div class="grid gap-4 lg:grid-cols-2">
          <section v-for="group in teamByReservation" :key="group.reservation">
            <h3 class="num mb-2 text-[12.5px] font-bold text-muted">{{ group.reservation }}</h3>
            <ul class="divide-y divide-line rounded-wd border border-line">
              <li
                v-for="member in group.members"
                :key="member.assignment"
                class="flex flex-wrap items-center gap-3 px-3 py-2.5"
              >
                <WAvatar :name="member.name" :size="34" />
                <span class="min-w-0 flex-1">
                  <span class="block text-[14px] font-bold">{{ member.name }}</span>
                  <span class="block text-[12px] text-muted"
                    >{{ member.role }} · {{ local(member.start).slice(11) }}</span
                  >
                </span>
                <WBadge v-if="member.attendance" :tone="ATTENDANCE_TONES[member.attendance]">{{
                  t(`staff.attendance.${member.attendance}`)
                }}</WBadge>
                <span v-else class="flex gap-1">
                  <WButton size="sm" variant="secondary" @click="run(member.assignment, 'in')">{{
                    t('staff.attendancePage.checkIn')
                  }}</WButton>
                  <WButton size="sm" variant="ghost" @click="run(member.assignment, 'absent')">{{
                    t('staff.attendancePage.absent')
                  }}</WButton>
                </span>
              </li>
            </ul>
          </section>
        </div>
      </WCard>

      <!-- Today -->
      <section class="flex flex-col gap-3" aria-labelledby="space-today">
        <div class="flex items-center justify-between gap-3">
          <h2 id="space-today" class="text-[17px] font-semibold">{{ t('staff.space.today') }}</h2>
          <RouterLink
            :to="{ name: 'missions' }"
            class="inline-flex items-center gap-1 text-[13.5px] font-bold text-violet hover:underline"
            >{{ t('staff.space.allMissions') }}<ArrowRight class="size-4" aria-hidden="true"
          /></RouterLink>
        </div>
        <p
          v-if="!todays.length"
          class="rounded-wd-lg border border-dashed border-line-2 px-4 py-6 text-center text-[14px] text-muted"
        >
          {{ t('staff.space.nothingToday') }}
        </p>
        <MissionCard v-for="mission in todays" :key="mission.id" :mission="mission" />
      </section>
    </template>
  </div>
</template>

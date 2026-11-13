<script setup lang="ts">
import { ChevronLeft, ChevronRight, IdCard, Phone, Plus, Search, Users } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import DownloadMenu from '@/components/DownloadMenu.vue'
import { toApiError } from '@/api/errors'
import { formatMoneyShort } from '@/composables/useMoney'
import { useSessionStore } from '@/stores/session'
import { WAvatar, WBadge, WButton, WCard, WEmptyState, WInput, WTabs, WTile } from '@/design'
import { addDays, fromIso, iso, weekStart } from '@/modules/calendar/month'

import { type StaffMember, usePlanning, useStaff, useStaffStats } from '../api'
import BadgesModal from '../components/BadgesModal.vue'
import StaffFormModal from '../components/StaffFormModal.vue'
import TasksTab from '../components/TasksTab.vue'

/** « Personnel » (reservations-stock.md §7): tiles, members with today's availability, week. */
const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const canEdit = computed(() => session.role === 'owner' || session.role === 'planner')

const tab = computed({
  get: () =>
    ['planning', 'taches'].includes(String(route.query.onglet))
      ? String(route.query.onglet)
      : 'membres',
  set: (value: string) => void router.replace({ query: { ...route.query, onglet: value } }),
})
const tabs = computed(() => [
  { key: 'membres', label: t('staff.tabs.members') },
  { key: 'taches', label: t('staff.tabs.tasks') },
  { key: 'planning', label: t('staff.tabs.planning') },
])
const search = ref('')
const showInactive = ref(false)
const people = useStaff(() => ({ search: search.value, active: !showInactive.value }))
const stats = useStaffStats()

const monday = ref(iso(weekStart(new Date())))
const planning = usePlanning(monday)
const shiftWeek = (weeks: number) => (monday.value = iso(addDays(fromIso(monday.value), weeks * 7)))
const dayLabel = (day: string) =>
  new Intl.DateTimeFormat(locale.value, { weekday: 'short', day: 'numeric' })
    .format(fromIso(day))
    .replace('.', '')
const todayIso = iso(new Date())
const TODAY_TONES = { free: 'green', busy: 'violet', absent: 'red' } as const
const CELL_TONES: Record<string, string> = {
  present: 'bg-green-soft text-ink',
  late: 'bg-gold-soft text-ink',
  absent: 'bg-red-soft text-red line-through',
  none: 'bg-violet-soft text-ink',
}

const formOpen = ref(false)
const badgesOpen = ref(false)
const editing = ref<StaffMember | null>(null)
function edit(member: StaffMember | null): void {
  editing.value = member
  formOpen.value = true
}
</script>

<template>
  <div class="flex flex-col gap-[22px]">
    <header class="flex flex-wrap items-end gap-x-6 gap-y-3">
      <div class="min-w-0 flex-1">
        <h1>{{ t('staff.title') }}</h1>
        <p class="mt-1 max-w-[64ch] text-muted">{{ t('staff.subtitle') }}</p>
      </div>
      <DownloadMenu url="/exports/staff" filename="personnel" />
      <WButton variant="secondary" @click="badgesOpen = true">
        <IdCard class="size-[18px]" aria-hidden="true" />{{ t('staff.badges.all') }}
      </WButton>
      <WButton v-if="canEdit" @click="edit(null)">
        <Plus class="size-[18px]" aria-hidden="true" />{{ t('staff.add') }}
      </WButton>
    </header>

    <div v-if="stats.data.value" class="grid grid-cols-2 gap-3.5 lg:grid-cols-4">
      <WTile :label="t('staff.tiles.headcount')" :value="String(stats.data.value.headcount)" />
      <WTile
        :label="t('staff.tiles.missionsWeek')"
        :value="String(stats.data.value.missionsWeek)"
      />
      <WTile
        :label="t('staff.tiles.hoursMonth')"
        :value="`${Math.round(stats.data.value.hoursMonth).toLocaleString(locale)} h`"
      />
      <WTile
        v-if="stats.data.value.payrollMonth !== null"
        :label="t('staff.tiles.payroll')"
        :value="formatMoneyShort(stats.data.value.payrollMonth)"
      />
    </div>
    <div v-else class="grid grid-cols-2 gap-3.5 lg:grid-cols-4">
      <div v-for="n in 4" :key="n" class="skeleton h-[92px] rounded-wd-lg" />
    </div>

    <WTabs v-model="tab" :tabs="tabs" :label="t('staff.title')" />

    <template v-if="tab === 'membres'">
      <div class="flex flex-wrap items-center gap-3">
        <WInput
          v-model="search"
          class="min-w-[220px] flex-1"
          type="search"
          :label="t('staff.search')"
          :placeholder="t('staff.searchPlaceholder')"
          hide-label
        >
          <template #prefix><Search class="size-[18px] text-muted" aria-hidden="true" /></template>
        </WInput>
        <label class="flex items-center gap-2 text-[13.5px] font-semibold text-ink-2">
          <input v-model="showInactive" type="checkbox" class="size-4 accent-violet" />{{
            t('staff.inactive')
          }}
        </label>
      </div>
      <WEmptyState
        v-if="people.isError.value"
        :title="t('staff.loadError')"
        :description="toApiError(people.error.value).message"
      />
      <div v-else-if="people.isPending.value" class="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-3">
        <div v-for="n in 6" :key="n" class="skeleton h-[118px] rounded-wd-lg" />
      </div>
      <WEmptyState
        v-else-if="!people.data.value?.length"
        :icon="Users"
        :title="t('staff.emptyTitle')"
        :description="t('staff.emptyText')"
      />
      <ul v-else class="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-3">
        <li v-for="member in people.data.value" :key="member.id">
          <button
            type="button"
            class="flex h-full w-full flex-col gap-2 rounded-wd-lg border border-line bg-surface p-4 text-left transition-colors hover:border-line-2"
            :disabled="!canEdit"
            @click="edit(member)"
          >
            <span class="flex items-center gap-3">
              <img
                v-if="member.photoUrl"
                :src="member.photoUrl"
                :alt="member.fullName"
                class="size-[42px] shrink-0 rounded-full object-cover"
              />
              <WAvatar v-else :name="member.fullName" :size="42" />
              <span class="min-w-0 flex-1">
                <span class="block truncate font-bold">{{ member.fullName }}</span>
                <span class="block truncate text-[12.5px] text-muted"
                  >{{ member.position }} · {{ member.kindLabel }}</span
                >
              </span>
              <WBadge :tone="TODAY_TONES[member.today.status]">{{
                t(`staff.today.${member.today.status}`)
              }}</WBadge>
            </span>
            <span v-if="member.today.missions.length" class="text-[12.5px] text-ink-2">
              {{
                t('staff.today.on', {
                  list: member.today.missions
                    .map((m) => `${m.number} (${t(`staff.steps.${m.step}`)})`)
                    .join(', '),
                })
              }}
            </span>
            <span class="flex flex-wrap items-center gap-x-3 gap-y-1 text-[12.5px] text-muted">
              <span v-if="member.phone" class="inline-flex items-center gap-1"
                ><Phone class="size-3.5" aria-hidden="true" />{{ member.phone }}</span
              >
              <span v-if="member.payRate !== null"
                >{{ member.payModeLabel }} · {{ formatMoneyShort(member.payRate) }}</span
              >
              <span v-if="member.hasAccount">{{ t('staff.hasAccount') }}</span>
            </span>
          </button>
        </li>
      </ul>
    </template>

    <TasksTab v-else-if="tab === 'taches'" :can-edit="canEdit" />

    <WCard v-else :title="t('staff.planning.title')" :subtitle="t('staff.planning.subtitle')">
      <div class="mb-3 flex items-center gap-2">
        <WButton
          size="sm"
          variant="secondary"
          icon
          :aria-label="t('staff.planning.previous')"
          @click="shiftWeek(-1)"
        >
          <ChevronLeft class="size-[15px]" aria-hidden="true" />
        </WButton>
        <WButton
          size="sm"
          variant="secondary"
          icon
          :aria-label="t('staff.planning.next')"
          @click="shiftWeek(1)"
        >
          <ChevronRight class="size-[15px]" aria-hidden="true" />
        </WButton>
      </div>
      <div v-if="!planning.data.value" class="skeleton h-64" />
      <div v-else class="overflow-x-auto">
        <table class="w-full min-w-[860px] border-collapse text-[12.5px]">
          <caption class="sr-only">
            {{
              t('staff.planning.title')
            }}
          </caption>
          <thead>
            <tr class="border-b border-line text-left text-muted">
              <th scope="col" class="w-[180px] px-2 py-2">{{ t('staff.planning.person') }}</th>
              <th
                v-for="day in planning.data.value.days"
                :key="day"
                scope="col"
                class="px-2 py-2 font-bold first-letter:uppercase"
                :class="day === todayIso && 'text-violet'"
              >
                {{ dayLabel(day) }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in planning.data.value.rows"
              :key="row.staff"
              class="border-b border-line last:border-b-0"
            >
              <th scope="row" class="px-2 py-2 text-left">
                <span class="block font-bold">{{ row.name }}</span>
                <span class="block font-normal text-muted">{{ row.position }}</span>
              </th>
              <td v-for="day in planning.data.value.days" :key="day" class="px-1 py-1.5 align-top">
                <span
                  v-if="row.absent?.includes(day)"
                  class="block rounded-[6px] bg-red-soft px-1.5 py-1 font-bold text-red"
                  >{{ t('staff.today.absent') }}</span
                >
                <RouterLink
                  v-for="cell in row.days[day] ?? []"
                  :key="cell.assignment"
                  :to="{ name: 'reservations', query: { reservation: cell.reservation } }"
                  class="mb-1 block rounded-[6px] px-1.5 py-1 font-semibold hover:brightness-[0.97]"
                  :class="CELL_TONES[cell.attendance ?? 'none']"
                >
                  {{ cell.time }} · {{ cell.number }}
                  <span class="block font-normal text-ink-2">{{
                    t(`staff.steps.${cell.step}`)
                  }}</span>
                </RouterLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </WCard>

    <StaffFormModal v-model:open="formOpen" :member="editing" />
    <BadgesModal v-model:open="badgesOpen" />
  </div>
</template>

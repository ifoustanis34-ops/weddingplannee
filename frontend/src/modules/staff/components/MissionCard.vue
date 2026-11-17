<script setup lang="ts">
import {
  Camera,
  CheckCircle2,
  ChevronDown,
  Clock,
  ListChecks,
  LogIn,
  LogOut,
  MapPin,
  Navigation,
  Package,
  Phone,
  Users,
} from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { toZonedInput } from '@/composables/useDate'
import { useToast } from '@/composables/useToast'
import { WBadge, WButton, WDateBlock } from '@/design'
import { KIND_STYLE } from '@/modules/calendar/kinds'

import { ATTENDANCE_TONES, type Mission, type StaffTask, staffApi, useStaffMutation } from '../api'
import { taskProgress } from '../missions'

/**
 * One mission (feedback 13/11/2026: « missions bien organisées »): the date, the step, where and
 * when, the state; the main action (arrival, departure) always in reach; the tasks always in
 * sight (17/11/2026); equipment and team (team lead) in a fold. A « Tâches » card (tasks given on
 * an event without a mission) has no clocking.
 */
const props = defineProps<{ mission: Mission; open?: boolean }>()
const { t } = useI18n()
const toast = useToast()
const expanded = ref(props.open ?? false)

const local = (value: string) => toZonedInput(value)
const day = computed(() => local(props.mission.start).slice(0, 10))
const hours = computed(() => {
  const start = local(props.mission.start)
  const end = local(props.mission.end)
  const sameDay = start.slice(0, 10) === end.slice(0, 10)
  return sameDay
    ? `${start.slice(11)} – ${end.slice(11)}`
    : t('staff.missions.untilDay', {
        start: start.slice(11),
        date: end.slice(8, 10) + '/' + end.slice(5, 7),
      })
})
const onlyTasks = computed(() => props.mission.kind === 'tasks')
const step = computed(() =>
  onlyTasks.value
    ? { ...KIND_STYLE.task, icon: ListChecks }
    : KIND_STYLE[props.mission.step === 'all' ? 'event' : props.mission.step],
)
const hasFold = computed(() => props.mission.equipment.length > 0 || props.mission.team.length > 0)
const progress = computed(() => taskProgress(props.mission.tasks))
const STATE_TONE = { upcoming: 'grey', in_progress: 'violet', done: 'green' } as const

const act = useStaffMutation(({ id, action }: { id: string; action: 'in' | 'out' | 'absent' }) =>
  action === 'in'
    ? staffApi.checkIn(id)
    : action === 'out'
      ? staffApi.checkOut(id)
      : staffApi.absent(id),
)
async function run(id: string, action: 'in' | 'out' | 'absent'): Promise<void> {
  try {
    await act.mutateAsync({ id, action })
    toast.success(t(`staff.attendancePage.done.${action}`))
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
const task = useStaffMutation(({ id, status }: { id: string; status: string }) =>
  staffApi.updateTask(id, { status }),
)
const photo = useStaffMutation(({ id, file }: { id: string; file: File }) =>
  staffApi.taskPhoto(id, file),
)
async function toggle(item: StaffTask): Promise<void> {
  if (item.status === 'validated') return // checked by the manager: it no longer changes
  try {
    await task.mutateAsync({ id: item.id, status: item.status === 'done' ? 'todo' : 'done' })
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
async function upload(item: StaffTask, event: Event): Promise<void> {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  try {
    await photo.mutateAsync({ id: item.id, file })
    toast.success(t('staff.missions.photoSaved'))
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
const chip =
  'inline-flex h-9 items-center gap-1.5 rounded-[10px] border border-line-2 bg-surface px-3 text-[13px] font-bold hover:bg-surface-2'
</script>

<template>
  <article
    class="overflow-hidden rounded-wd-lg border bg-surface"
    :class="mission.state === 'in_progress' ? 'border-violet shadow-wd' : 'border-line'"
  >
    <div class="flex gap-3.5 p-4">
      <WDateBlock :date="day" weekday />
      <div class="min-w-0 flex-1">
        <div class="flex flex-wrap items-center gap-1.5">
          <span
            class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11.5px] font-bold"
            :class="step.chip"
          >
            <component :is="step.icon" class="size-3.5" aria-hidden="true" />{{
              onlyTasks ? t('staff.missions.tasksCard') : mission.stepLabel
            }}
          </span>
          <WBadge :tone="STATE_TONE[mission.state]">{{
            t(`staff.missions.states.${mission.state}`)
          }}</WBadge>
          <WBadge v-if="mission.attendance" :tone="ATTENDANCE_TONES[mission.attendance.status]">{{
            t(`staff.attendance.${mission.attendance.status}`)
          }}</WBadge>
        </div>
        <h3 class="mt-1.5 text-[15.5px] leading-snug font-bold">{{ mission.reservationTitle }}</h3>
        <p class="mt-0.5 flex items-center gap-1.5 text-[13px] text-ink-2">
          <Clock class="size-3.5 shrink-0 text-muted" aria-hidden="true" />{{ hours }}
          <span v-if="mission.role" class="truncate text-muted">· {{ mission.role }}</span>
        </p>
        <p
          v-if="mission.venue || mission.address"
          class="mt-0.5 flex items-start gap-1.5 text-[13px] text-ink-2"
        >
          <MapPin class="mt-0.5 size-3.5 shrink-0 text-muted" aria-hidden="true" />
          <span>{{ [mission.venue, mission.address].filter(Boolean).join(' — ') }}</span>
        </p>
      </div>
    </div>

    <div class="flex flex-wrap items-center gap-2 px-4 pb-4">
      <template v-if="mission.state !== 'done' && !onlyTasks">
        <WButton
          v-if="!mission.attendance?.checkIn"
          :loading="act.isPending.value"
          @click="run(mission.id, 'in')"
        >
          <LogIn class="size-[18px]" aria-hidden="true" />{{ t('staff.attendancePage.checkIn') }}
        </WButton>
        <WButton
          v-else-if="!mission.attendance.checkOut"
          :loading="act.isPending.value"
          @click="run(mission.id, 'out')"
        >
          <LogOut class="size-[18px]" aria-hidden="true" />{{ t('staff.attendancePage.checkOut') }}
        </WButton>
      </template>
      <span
        v-if="mission.attendance?.checkOut"
        class="rounded-[10px] bg-green-soft px-3 py-2 text-[13px] font-bold text-green"
        >{{ t('staff.missions.hours', { hours: mission.attendance.hours }) }}</span
      >
      <a v-if="mission.mapsUrl" :href="mission.mapsUrl" target="_blank" rel="noopener" :class="chip"
        ><Navigation class="size-[15px]" aria-hidden="true" />{{ t('staff.missions.route') }}</a
      >
      <a v-if="mission.clientPhone" :href="`tel:${mission.clientPhone}`" :class="chip"
        ><Phone class="size-[15px]" aria-hidden="true" />{{ t('staff.missions.client') }}</a
      >
      <button
        v-if="hasFold"
        type="button"
        class="ml-auto inline-flex h-9 items-center gap-1.5 rounded-[10px] px-2.5 text-[13px] font-bold text-violet hover:bg-violet-soft"
        :aria-expanded="expanded"
        @click="expanded = !expanded"
      >
        {{ expanded ? t('staff.missions.less') : t('staff.missions.more') }}
        <ChevronDown
          class="size-4 transition-transform"
          :class="expanded && 'rotate-180'"
          aria-hidden="true"
        />
      </button>
    </div>

    <div v-if="progress.total" class="px-4 pb-3">
      <div class="flex items-center justify-between text-[12px] font-semibold text-muted">
        <span>{{ t('staff.missions.tasks') }}</span>
        <span class="num">{{ progress.done }}/{{ progress.total }}</span>
      </div>
      <div class="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-2">
        <div
          class="h-full rounded-full bg-green transition-[width]"
          :style="{ width: `${(progress.done / progress.total) * 100}%` }"
        />
      </div>
    </div>

    <section v-if="mission.tasks.length" class="px-4 pb-4" :aria-label="t('staff.missions.tasks')">
      <ul class="flex flex-col gap-1.5">
        <li
          v-for="item in mission.tasks"
          :key="item.id"
          class="flex flex-wrap items-center gap-2 rounded-wd border border-line bg-surface-2/40 px-3 py-2"
        >
          <button
            type="button"
            class="flex min-w-0 flex-1 items-center gap-2.5 text-left text-[14px]"
            :aria-pressed="item.status !== 'todo'"
            :disabled="item.status === 'validated'"
            @click="toggle(item)"
          >
            <CheckCircle2
              class="size-5 shrink-0"
              :class="item.status === 'todo' ? 'text-line-2' : 'text-green'"
              aria-hidden="true"
            />
            <span :class="item.status !== 'todo' && 'text-muted line-through'">{{
              item.title
            }}</span>
          </button>
          <WBadge v-if="item.status === 'validated'" tone="green">{{
            t('staff.tasks.columns.validated')
          }}</WBadge>
          <a
            v-if="item.photoUrl"
            :href="item.photoUrl"
            target="_blank"
            rel="noopener"
            class="text-[12.5px] font-bold text-violet"
            >{{ t('staff.missions.seePhoto') }}</a
          >
          <label
            v-if="item.status !== 'validated'"
            class="inline-flex cursor-pointer items-center gap-1 text-[12.5px] font-bold text-ink-2"
          >
            <Camera class="size-[15px]" aria-hidden="true" />{{ t('staff.missions.photo') }}
            <input
              type="file"
              accept="image/*"
              capture="environment"
              class="sr-only"
              @change="upload(item, $event)"
            />
          </label>
        </li>
      </ul>
    </section>

    <div v-if="expanded && hasFold" class="grid gap-4 border-t border-line bg-surface-2/50 p-4">
      <section v-if="mission.equipment.length" :aria-label="t('staff.missions.equipment')">
        <h4 class="flex items-center gap-1.5 text-[12.5px] font-bold text-muted">
          <Package class="size-3.5" aria-hidden="true" />{{ t('staff.missions.equipment') }}
        </h4>
        <ul class="mt-2 divide-y divide-line rounded-wd border border-line bg-surface">
          <li
            v-for="line in mission.equipment"
            :key="line.label"
            class="flex justify-between gap-3 px-3 py-2 text-[13.5px]"
          >
            <span>{{ line.label }}</span
            ><b class="num">× {{ line.quantity }}</b>
          </li>
        </ul>
      </section>

      <section v-if="mission.team.length" :aria-label="t('staff.missions.team')">
        <h4 class="flex items-center gap-1.5 text-[12.5px] font-bold text-muted">
          <Users class="size-3.5" aria-hidden="true" />{{ t('staff.missions.team') }}
        </h4>
        <ul class="mt-2 divide-y divide-line rounded-wd border border-line bg-surface">
          <li
            v-for="member in mission.team"
            :key="member.assignment"
            class="flex flex-wrap items-center gap-2 px-3 py-2"
          >
            <span class="min-w-0 flex-1 text-[13.5px] font-semibold"
              >{{ member.name }}
              <span class="block font-normal text-muted">{{ member.role }}</span></span
            >
            <WBadge v-if="member.attendance" :tone="ATTENDANCE_TONES[member.attendance]">{{
              t(`staff.attendance.${member.attendance}`)
            }}</WBadge>
            <template v-else-if="mission.state !== 'done'">
              <WButton size="sm" variant="secondary" @click="run(member.assignment, 'in')">{{
                t('staff.attendancePage.checkIn')
              }}</WButton>
              <WButton size="sm" variant="ghost" @click="run(member.assignment, 'absent')">{{
                t('staff.attendancePage.absent')
              }}</WButton>
            </template>
          </li>
        </ul>
      </section>

      <p class="text-[12px] text-muted">{{ mission.reservationNumber }} · {{ mission.client }}</p>
    </div>
  </article>
</template>

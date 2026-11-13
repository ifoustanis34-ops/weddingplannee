<script setup lang="ts">
import { LogIn, LogOut, UserX } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import DownloadMenu from '@/components/DownloadMenu.vue'
import { formatDate } from '@/composables/useDate'
import { useToast } from '@/composables/useToast'
import { WBadge, WButton, WCard, WEmptyState } from '@/design'
import { iso } from '@/modules/calendar/month'

import { ATTENDANCE_TONES, staffApi, usePlanning, useStaffMutation } from '../api'

/** « Présences » (§7): today's check-ins (arrival, departure, absence). Pay is its own page. */
const { t } = useI18n()
const toast = useToast()

// --- Today's check-ins: the planning's column of the day.
const todayIso = iso(new Date())
const planning = usePlanning(todayIso)
const todayRows = computed(() =>
  (planning.data.value?.rows ?? []).flatMap((row) =>
    (row.days[todayIso] ?? []).map((cell) => ({ ...cell, name: row.name, position: row.position })),
  ),
)
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
</script>

<template>
  <div class="flex flex-col gap-[22px]">
    <header class="flex flex-wrap items-end gap-x-6 gap-y-3">
      <div class="min-w-0 flex-1">
        <h1>{{ t('staff.attendancePage.title') }}</h1>
        <p class="mt-1 max-w-[64ch] text-muted">{{ t('staff.attendancePage.subtitle') }}</p>
      </div>
      <DownloadMenu
        url="/exports/calendar"
        filename="missions-du-jour"
        :params="{
          from: todayIso,
          to: todayIso,
          kinds: 'delivery,setup,event,teardown,pickup,return',
        }"
      />
    </header>
    <WCard :title="t('staff.attendancePage.todayTitle', { date: formatDate(todayIso) })">
      <div v-if="planning.isPending.value" class="skeleton h-32" />
      <WEmptyState v-else-if="!todayRows.length" :title="t('staff.attendancePage.nobody')" />
      <ul v-else class="-my-1 divide-y divide-line">
        <li
          v-for="row in todayRows"
          :key="row.assignment"
          class="flex flex-wrap items-center gap-3 py-3"
        >
          <span class="min-w-[200px] flex-1">
            <span class="block font-bold">{{ row.name }}</span>
            <span class="block text-[12.5px] text-muted"
              >{{ row.time }} · {{ row.number }} · {{ t(`staff.steps.${row.step}`) }}</span
            >
          </span>
          <WBadge v-if="row.attendance" :tone="ATTENDANCE_TONES[row.attendance]">{{
            t(`staff.attendance.${row.attendance}`)
          }}</WBadge>
          <div class="flex flex-wrap gap-1.5">
            <WButton
              size="sm"
              variant="secondary"
              :loading="act.isPending.value"
              @click="run(row.assignment, 'in')"
            >
              <LogIn class="size-[15px]" aria-hidden="true" />{{
                t('staff.attendancePage.checkIn')
              }}
            </WButton>
            <WButton
              size="sm"
              variant="secondary"
              :loading="act.isPending.value"
              @click="run(row.assignment, 'out')"
            >
              <LogOut class="size-[15px]" aria-hidden="true" />{{
                t('staff.attendancePage.checkOut')
              }}
            </WButton>
            <WButton
              size="sm"
              variant="ghost"
              class="text-red"
              :loading="act.isPending.value"
              @click="run(row.assignment, 'absent')"
            >
              <UserX class="size-[15px]" aria-hidden="true" />{{ t('staff.attendancePage.absent') }}
            </WButton>
          </div>
        </li>
      </ul>
    </WCard>
  </div>
</template>

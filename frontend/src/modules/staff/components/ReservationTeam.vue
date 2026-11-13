<script setup lang="ts">
import { TriangleAlert, UserPlus, X } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { formatDateTime } from '@/composables/useDate'
import { useToast } from '@/composables/useToast'
import { WBadge, WButton, WInput, WSelect } from '@/design'

import {
  ATTENDANCE_TONES,
  type Step,
  STEPS,
  staffApi,
  useAssignments,
  useStaff,
  useStaffMutation,
} from '../api'

/** « Équipe affectée » of a reservation (§4.2, §7): who, on which step, conflicts flagged. */
const props = defineProps<{ reservationId: string; canEdit: boolean; open: boolean }>()
const { t } = useI18n()
const toast = useToast()
const assignments = useAssignments(() => ({ reservation: props.reservationId }))
const people = useStaff(() => ({}))
const staff = ref('')
const step = ref<Step>('all')
const role = ref('')
const staffOptions = computed(() =>
  (people.data.value ?? []).map((p) => ({
    value: p.id,
    label: `${p.fullName} · ${p.position}${p.today.status === 'absent' ? ` (${t('staff.today.absent')})` : ''}`,
  })),
)
const stepOptions = computed(() =>
  STEPS.map((value) => ({ value, label: t(`staff.steps.${value}`) })),
)
const add = useStaffMutation(() =>
  staffApi.assign({
    reservation: props.reservationId,
    staff: staff.value,
    step: step.value,
    role: role.value,
  }),
)
async function assign(): Promise<void> {
  if (!staff.value) return
  try {
    const created = await add.mutateAsync(undefined)
    if (created.conflicts.length) toast.error(created.conflicts.join(' '))
    else toast.success(t('staff.team.assigned', { name: created.staffName }))
    staff.value = ''
    role.value = ''
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
const remove = useStaffMutation((id: string) => staffApi.unassign(id))
async function unassign(id: string): Promise<void> {
  try {
    await remove.mutateAsync(id)
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
</script>

<template>
  <section>
    <h3>{{ t('reservations.drawer.team') }}</h3>
    <div v-if="assignments.isPending.value" class="skeleton mt-2 h-10" />
    <p v-else-if="!assignments.data.value?.length" class="mt-2 text-[13px] text-muted">
      {{ t('staff.team.none') }}
    </p>
    <ul v-else class="mt-2 divide-y divide-line rounded-wd border border-line">
      <li v-for="row in assignments.data.value" :key="row.id" class="px-3 py-2.5">
        <div class="flex flex-wrap items-center gap-2">
          <span class="min-w-0 flex-1">
            <span class="block font-semibold">{{ row.staffName }}</span>
            <span class="block text-[12.5px] text-muted"
              >{{ row.role || row.staffPosition }} · {{ row.stepLabel }} ·
              {{ formatDateTime(row.start) }}</span
            >
          </span>
          <WBadge v-if="row.attendance" :tone="ATTENDANCE_TONES[row.attendance.status]">{{
            t(`staff.attendance.${row.attendance.status}`)
          }}</WBadge>
          <WButton
            v-if="canEdit && !row.attendance?.checkIn"
            size="sm"
            variant="ghost"
            icon
            :aria-label="t('staff.team.remove', { name: row.staffName })"
            @click="unassign(row.id)"
          >
            <X class="size-[15px]" aria-hidden="true" />
          </WButton>
        </div>
        <p
          v-for="message in row.conflicts"
          :key="message"
          class="mt-1 flex items-start gap-1.5 text-[12.5px] font-semibold text-red"
        >
          <TriangleAlert class="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />{{ message }}
        </p>
      </li>
    </ul>
    <form
      v-if="canEdit && open"
      class="mt-3 grid gap-2 sm:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_minmax(0,1fr)_auto] sm:items-end"
      @submit.prevent="assign"
    >
      <WSelect
        v-model="staff"
        :label="t('staff.team.person')"
        :options="staffOptions"
        :placeholder="t('staff.team.choose')"
      />
      <WSelect v-model="step" :label="t('staff.team.step')" :options="stepOptions" />
      <WInput
        v-model="role"
        :label="t('staff.team.role')"
        :placeholder="t('staff.team.rolePlaceholder')"
        maxlength="80"
      />
      <WButton type="submit" variant="secondary" :loading="add.isPending.value" :disabled="!staff">
        <UserPlus class="size-[16px]" aria-hidden="true" />{{ t('staff.team.assign') }}
      </WButton>
    </form>
  </section>
</template>

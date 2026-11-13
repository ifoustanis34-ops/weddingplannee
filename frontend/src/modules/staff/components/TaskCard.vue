<script setup lang="ts">
import {
  CalendarDays,
  Check,
  CircleAlert,
  MapPin,
  MessageSquareText,
  RotateCcw,
  ShieldCheck,
  Undo2,
} from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { daysBetween, formatDate, formatDateTime } from '@/composables/useDate'
import { WAvatar, WButton, WInput } from '@/design'

import type { StaffTask } from '../api'

/**
 * One task, readable at a glance (feedback 13/11/2026): what to do, who, on which event, where
 * and when, what the person reported (comment, photo) and what the manager decides.
 */
const props = defineProps<{ task: StaffTask; canReview: boolean; busy: boolean }>()
const emit = defineEmits<{
  done: [task: StaffTask]
  validate: [task: StaffTask]
  reject: [task: StaffTask, reason: string]
  reopen: [task: StaffTask]
}>()
const { t } = useI18n()

/** « En retard », « Aujourd’hui », « Demain », « Dans 5 j » — only while there is work to do. */
const due = computed(() => {
  if (props.task.status !== 'todo') return null
  const days = daysBetween(new Date(), props.task.eventStart)
  if (days < 0)
    return { label: t('staff.tasks.due.late', { days: -days }), tone: 'bg-red-soft text-red' }
  if (days === 0) return { label: t('staff.tasks.due.today'), tone: 'bg-coral-soft text-coral' }
  if (days === 1) return { label: t('staff.tasks.due.tomorrow'), tone: 'bg-gold-soft text-gold' }
  return { label: t('staff.tasks.due.in', { days }), tone: 'bg-surface-2 text-ink-2' }
})
const rejecting = ref(false)
const reason = ref('')
function sendBack(): void {
  if (!reason.value.trim()) return
  emit('reject', props.task, reason.value.trim())
  rejecting.value = false
  reason.value = ''
}
</script>

<template>
  <article
    class="flex flex-col gap-3 rounded-wd-lg border bg-surface p-4"
    :class="task.status === 'done' ? 'border-gold-bright' : 'border-line'"
  >
    <div class="flex items-center justify-between gap-2 text-[12px] font-bold">
      <RouterLink
        :to="{ name: 'reservations', query: { reservation: task.reservation } }"
        class="text-violet hover:underline"
        >{{ task.reservationNumber }}</RouterLink
      >
      <span v-if="due" class="rounded-full px-2 py-0.5" :class="due.tone">{{ due.label }}</span>
    </div>

    <h3 class="text-[15.5px] leading-snug font-bold">{{ task.title }}</h3>

    <div class="flex items-center gap-2.5">
      <WAvatar :name="task.staffName" :size="30" />
      <span class="min-w-0">
        <span class="block truncate text-[13.5px] font-semibold">{{ task.staffName }}</span>
        <span class="block truncate text-[12px] text-muted">{{ task.staffPosition }}</span>
      </span>
    </div>

    <ul class="flex flex-col gap-1 text-[12.5px] text-ink-2">
      <li class="flex items-start gap-1.5">
        <CalendarDays class="mt-0.5 size-3.5 shrink-0 text-muted" aria-hidden="true" />
        <span>{{ task.reservationTitle }} · {{ formatDate(task.eventStart) }}</span>
      </li>
      <li v-if="task.venue" class="flex items-start gap-1.5">
        <MapPin class="mt-0.5 size-3.5 shrink-0 text-muted" aria-hidden="true" />{{ task.venue }}
      </li>
    </ul>

    <p
      v-if="task.status === 'todo' && task.rejectionReason"
      class="flex items-start gap-1.5 rounded-wd bg-red-soft px-3 py-2 text-[12.5px] font-semibold text-red"
    >
      <CircleAlert class="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
      {{ t('staff.tasks.sentBack', { reason: task.rejectionReason }) }}
    </p>

    <div
      v-if="task.status !== 'todo'"
      class="flex flex-col gap-2 rounded-wd bg-surface-2 px-3 py-2.5"
    >
      <p class="text-[12.5px] text-ink-2">
        {{
          t('staff.tasks.doneBy', {
            name: task.doneByName ?? task.staffName,
            date: task.doneAt ? formatDateTime(task.doneAt) : '—',
          })
        }}
      </p>
      <p v-if="task.comment" class="flex items-start gap-1.5 text-[13px]">
        <MessageSquareText class="mt-0.5 size-3.5 shrink-0 text-muted" aria-hidden="true" />«
        {{ task.comment }} »
      </p>
      <a v-if="task.photoUrl" :href="task.photoUrl" target="_blank" rel="noopener" class="block">
        <img
          :src="task.photoUrl"
          :alt="t('staff.tasks.photoOf', { title: task.title })"
          class="h-28 w-full rounded-wd object-cover"
        />
      </a>
      <p
        v-if="task.status === 'validated'"
        class="flex items-center gap-1.5 text-[12.5px] font-semibold text-green"
      >
        <ShieldCheck class="size-4" aria-hidden="true" />
        {{
          t('staff.tasks.validatedBy', {
            name: task.validatedByName ?? '—',
            date: task.validatedAt ? formatDateTime(task.validatedAt) : '—',
          })
        }}
      </p>
    </div>

    <!-- Actions of the owner and the planner -->
    <div v-if="canReview" class="flex flex-wrap gap-2">
      <WButton
        v-if="task.status === 'todo'"
        size="sm"
        variant="secondary"
        :loading="busy"
        @click="emit('done', task)"
      >
        <Check class="size-[15px]" aria-hidden="true" />{{ t('staff.tasks.markDone') }}
      </WButton>
      <template v-else-if="task.status === 'done' && !rejecting">
        <WButton size="sm" :loading="busy" @click="emit('validate', task)">
          <ShieldCheck class="size-[15px]" aria-hidden="true" />{{ t('staff.tasks.validate') }}
        </WButton>
        <WButton size="sm" variant="secondary" @click="rejecting = true">
          <Undo2 class="size-[15px]" aria-hidden="true" />{{ t('staff.tasks.sendBack') }}
        </WButton>
      </template>
      <WButton
        v-else-if="task.status === 'validated'"
        size="sm"
        variant="ghost"
        :loading="busy"
        @click="emit('reopen', task)"
      >
        <RotateCcw class="size-[15px]" aria-hidden="true" />{{ t('staff.tasks.reopenAction') }}
      </WButton>
    </div>
    <form v-if="rejecting" class="flex flex-col gap-2" @submit.prevent="sendBack">
      <WInput
        v-model="reason"
        :label="t('staff.tasks.reasonLabel')"
        :placeholder="t('staff.tasks.reasonPlaceholder')"
        maxlength="255"
        required
      />
      <div class="flex gap-2">
        <WButton type="submit" size="sm" variant="danger" :disabled="!reason.trim()">{{
          t('staff.tasks.sendBack')
        }}</WButton>
        <WButton size="sm" variant="ghost" @click="rejecting = false">{{
          t('common.cancel')
        }}</WButton>
      </div>
    </form>
  </article>
</template>

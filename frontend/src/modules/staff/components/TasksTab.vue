<script setup lang="ts">
import { ClipboardList, Plus, Search } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { daysBetween } from '@/composables/useDate'
import { useToast } from '@/composables/useToast'
import { WButton, WChips, WEmptyState, WInput, WModal, WSelect, WTile } from '@/design'
import { useReservations } from '@/modules/reservations/api'

import { type StaffTask, staffApi, useStaff, useStaffMutation, useStaffTasks } from '../api'
import TaskCard from './TaskCard.vue'

/**
 * « Tâches » (reservations-stock.md §7, redesigned 13/11/2026): a three-column board — to do,
 * done waiting for validation, validated. The person marks a task done (« Mes missions »), the
 * owner or the planner validates it or sends it back with what is missing.
 */
const props = defineProps<{ canEdit: boolean }>()
const { t } = useI18n()
const toast = useToast()
const tasks = useStaffTasks(() => ({}))

// Filters: a person, an event, a word.
const person = ref('')
const event = ref('')
const search = ref('')
const all = computed(() => tasks.data.value ?? [])
const filtered = computed(() =>
  all.value.filter(
    (task) =>
      (!person.value || task.staff === person.value) &&
      (!event.value || task.reservation === event.value) &&
      (!search.value.trim() ||
        `${task.title} ${task.staffName} ${task.reservationTitle}`
          .toLowerCase()
          .includes(search.value.trim().toLowerCase())),
  ),
)
const byDate = (a: StaffTask, b: StaffTask) => a.eventStart.localeCompare(b.eventStart)
const columns = computed(() => [
  {
    key: 'todo' as const,
    title: t('staff.tasks.columns.todo'),
    hint: t('staff.tasks.columns.todoHint'),
    dot: 'bg-violet',
    items: filtered.value.filter((task) => task.status === 'todo').sort(byDate),
  },
  {
    key: 'done' as const,
    title: t('staff.tasks.columns.done'),
    hint: t('staff.tasks.columns.doneHint'),
    dot: 'bg-gold-bright',
    items: filtered.value.filter((task) => task.status === 'done').sort(byDate),
  },
  {
    key: 'validated' as const,
    title: t('staff.tasks.columns.validated'),
    hint: t('staff.tasks.columns.validatedHint'),
    dot: 'bg-green',
    items: filtered.value
      .filter((task) => task.status === 'validated')
      .sort((a, b) => byDate(b, a)),
  },
])
const late = computed(
  () =>
    filtered.value.filter(
      (task) => task.status === 'todo' && daysBetween(new Date(), task.eventStart) < 0,
    ).length,
)
// A long column stays short: 6 cards, then « Afficher plus ».
const PAGE = 6
const shown = ref<Record<string, number>>({ todo: PAGE, done: PAGE, validated: PAGE })
const more = (key: string) =>
  (shown.value = { ...shown.value, [key]: (shown.value[key] ?? PAGE) + PAGE * 2 })

// Phone: one column at a time.
const mobileColumn = ref<'todo' | 'done' | 'validated'>('todo')
const mobileOptions = computed(() =>
  columns.value.map((c) => ({ value: c.key, label: `${c.title} (${c.items.length})` })),
)

const people = useStaff(() => ({}))
const reservations = useReservations(() => ({ tab: 'all' }))
const personOptions = computed(() => [
  { value: '', label: t('staff.tasks.everyone') },
  ...(people.data.value ?? []).map((p) => ({ value: p.id, label: p.fullName })),
])
const eventOptions = computed(() => [
  { value: '', label: t('staff.tasks.allEvents') },
  ...[...new Map(all.value.map((task) => [task.reservation, task])).values()]
    .sort(byDate)
    .map((task) => ({
      value: task.reservation,
      label: `${task.reservationNumber} · ${task.reservationTitle}`,
    })),
])

// Actions.
const busyId = ref<string | null>(null)
const act = useStaffMutation(
  ({
    task,
    action,
    reason,
  }: {
    task: StaffTask
    action: 'done' | 'validate' | 'reject' | 'reopen'
    reason?: string
  }) => {
    if (action === 'done') return staffApi.updateTask(task.id, { status: 'done' })
    if (action === 'validate') return staffApi.validateTask(task.id)
    if (action === 'reject') return staffApi.rejectTask(task.id, reason ?? '')
    return staffApi.updateTask(task.id, { status: 'todo' })
  },
)
async function run(
  task: StaffTask,
  action: 'done' | 'validate' | 'reject' | 'reopen',
  reason?: string,
): Promise<void> {
  busyId.value = task.id
  try {
    await act.mutateAsync({ task, action, reason })
    toast.success(t(`staff.tasks.toast.${action}`, { title: task.title, name: task.staffName }))
  } catch (error) {
    toast.error(toApiError(error).message)
  } finally {
    busyId.value = null
  }
}

// « Nouvelle tâche » in a modal.
const formOpen = ref(false)
const form = ref({ staff: '', reservation: '', title: '' })
const staffChoices = computed(() =>
  (people.data.value ?? []).map((p) => ({ value: p.id, label: `${p.fullName} · ${p.position}` })),
)
const reservationChoices = computed(() =>
  (reservations.data.value ?? [])
    .filter((r) => !['cancelled', 'closed'].includes(r.status))
    .map((r) => ({ value: r.id, label: `${r.number} · ${r.title}` })),
)
const add = useStaffMutation(() => staffApi.addTask({ ...form.value }))
async function submit(): Promise<void> {
  try {
    const task = await add.mutateAsync(undefined)
    toast.success(t('staff.tasks.added', { name: task.staffName }))
    form.value.title = ''
    formOpen.value = false
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="grid grid-cols-2 gap-3.5 lg:grid-cols-4">
      <WTile :label="t('staff.tasks.columns.todo')" :value="String(columns[0]!.items.length)" />
      <WTile :label="t('staff.tasks.columns.done')" :value="String(columns[1]!.items.length)">{{
        columns[1]!.items.length ? t('staff.tasks.toReview') : ''
      }}</WTile>
      <WTile
        :label="t('staff.tasks.columns.validated')"
        :value="String(columns[2]!.items.length)"
      />
      <WTile :label="t('staff.tasks.lateTile')" :value="String(late)">{{
        late ? t('staff.tasks.lateHint') : ''
      }}</WTile>
    </div>

    <div class="flex flex-wrap items-end gap-3">
      <WInput
        v-model="search"
        class="min-w-[200px] flex-1"
        type="search"
        :label="t('staff.tasks.search')"
        :placeholder="t('staff.tasks.searchPlaceholder')"
        hide-label
      >
        <template #prefix><Search class="size-[18px] text-muted" aria-hidden="true" /></template>
      </WInput>
      <WSelect
        v-model="person"
        class="w-[200px]"
        :label="t('staff.tasks.person')"
        :options="personOptions"
        hide-label
      />
      <WSelect
        v-model="event"
        class="w-[260px]"
        :label="t('staff.tasks.event')"
        :options="eventOptions"
        hide-label
      />
      <WButton v-if="props.canEdit" @click="formOpen = true">
        <Plus class="size-[18px]" aria-hidden="true" />{{ t('staff.tasks.new') }}
      </WButton>
    </div>

    <WEmptyState
      v-if="tasks.isError.value"
      :title="t('staff.tasks.loadError')"
      :description="toApiError(tasks.error.value).message"
    />
    <div v-else-if="tasks.isPending.value" class="grid gap-4 lg:grid-cols-3">
      <div v-for="n in 3" :key="n" class="skeleton h-80 rounded-wd-lg" />
    </div>
    <WEmptyState
      v-else-if="!all.length"
      :icon="ClipboardList"
      :title="t('staff.tasks.empty')"
      :description="t('staff.tasks.emptyText')"
    />
    <template v-else>
      <WChips
        v-model="mobileColumn"
        class="lg:hidden"
        :options="mobileOptions"
        :label="t('staff.tasks.filter')"
      />
      <div class="grid items-start gap-4 lg:grid-cols-3">
        <section
          v-for="column in columns"
          :key="column.key"
          class="flex-col gap-3 rounded-wd-lg bg-surface-2 p-3"
          :class="mobileColumn === column.key ? 'flex' : 'hidden lg:flex'"
          :aria-label="column.title"
        >
          <header class="px-1">
            <h2 class="flex items-center gap-2 text-[15px] font-bold">
              <span class="size-2.5 rounded-full" :class="column.dot" aria-hidden="true" />
              {{ column.title }}
              <span class="num rounded-full bg-surface px-2 text-[12.5px] text-ink-2">{{
                column.items.length
              }}</span>
            </h2>
            <p class="mt-0.5 text-[12.5px] text-muted">{{ column.hint }}</p>
          </header>
          <p
            v-if="!column.items.length"
            class="rounded-wd border border-dashed border-line-2 px-3 py-6 text-center text-[13px] text-muted"
          >
            {{ t('staff.tasks.nothing') }}
          </p>
          <TaskCard
            v-for="task in column.items.slice(0, shown[column.key])"
            :key="task.id"
            :task="task"
            :can-review="props.canEdit"
            :busy="busyId === task.id"
            @done="run($event, 'done')"
            @validate="run($event, 'validate')"
            @reject="(item, reason) => run(item, 'reject', reason)"
            @reopen="run($event, 'reopen')"
          />
          <WButton
            v-if="column.items.length > (shown[column.key] ?? PAGE)"
            variant="secondary"
            block
            @click="more(column.key)"
          >
            {{
              t('staff.tasks.showMore', {
                count: column.items.length - (shown[column.key] ?? PAGE),
              })
            }}
          </WButton>
        </section>
      </div>
    </template>

    <WModal v-model:open="formOpen" :title="t('staff.tasks.new')" size="sm">
      <form id="task-form" class="flex flex-col gap-4" @submit.prevent="submit">
        <WSelect
          v-model="form.staff"
          :label="t('staff.tasks.person')"
          :options="staffChoices"
          :placeholder="t('staff.team.choose')"
          required
        />
        <WSelect
          v-model="form.reservation"
          :label="t('staff.tasks.event')"
          :options="reservationChoices"
          :placeholder="t('staff.team.choose')"
          required
        />
        <WInput
          v-model="form.title"
          :label="t('staff.tasks.title')"
          :placeholder="t('staff.tasks.placeholder')"
          maxlength="160"
          required
        />
      </form>
      <template #footer>
        <WButton variant="secondary" @click="formOpen = false">{{ t('common.cancel') }}</WButton>
        <WButton
          type="submit"
          form="task-form"
          :loading="add.isPending.value"
          :disabled="!form.staff || !form.reservation || !form.title.trim()"
          >{{ t('staff.tasks.add') }}</WButton
        >
      </template>
    </WModal>
  </div>
</template>

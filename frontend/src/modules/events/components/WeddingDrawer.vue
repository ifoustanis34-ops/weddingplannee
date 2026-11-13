<script setup lang="ts">
import { ChevronRight, ListChecks, Phone, Plus, Ticket, Trash2, Wallet } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { formatDate } from '@/composables/useDate'
import { formatMoney } from '@/composables/useMoney'
import { usePermissions } from '@/composables/usePermissions'
import { useToast } from '@/composables/useToast'
import {
  WBadge,
  WButton,
  WDateBlock,
  WDrawer,
  WEmptyState,
  WInput,
  WProgress,
  WSelect,
} from '@/design'
import { useMembers } from '@/composables/useMembers'
import { useContract } from '@/modules/finance/api'
import { useWeddingVendors } from '@/modules/vendors/api'

import { useTasks, useWedding, useWeddingAction, weddingsApi } from '../api'
import type { Task } from '../types'
import AssignVendorModal from './AssignVendorModal.vue'

/** Wedding drawer (complement §11): preparation, money, tasks and vendors. */
const props = defineProps<{ weddingId: string | null }>()
const emit = defineEmits<{ close: [] }>()
const { t } = useI18n()
const toast = useToast()
const { can } = usePermissions()

const open = computed({
  get: () => props.weddingId !== null,
  set: (value) => {
    if (!value) emit('close')
  },
})
const id = computed(() => props.weddingId)
const wedding = useWedding(id)
const tasks = useTasks(id)
const vendors = useWeddingVendors(id)
const members = useMembers()
const canEdit = computed(() => can('editWeddings'))
const seesMoney = computed(() => can('viewFinance'))
const contract = useContract(
  computed(() => (seesMoney.value ? (wedding.data.value?.contract ?? null) : null)),
)

// Undone first, then by due date (complement §11).
const sortedTasks = computed(() =>
  [...(tasks.data.value ?? [])].sort((a, b) => {
    if (a.status !== b.status) return a.status === 'todo' ? -1 : 1
    return (a.dueDate ?? '9999').localeCompare(b.dueDate ?? '9999')
  }),
)
const DAY = 86_400_000
function dueBadge(task: Task): 'late' | 'soon' | null {
  if (task.status === 'done' || !task.dueDate) return null
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const days = Math.round((new Date(`${task.dueDate}T00:00:00`).getTime() - today.getTime()) / DAY)
  if (days < 0) return 'late'
  return days <= 3 ? 'soon' : null
}
const firstName = (name: string | null) => name?.split(' ')[0] ?? ''

const toggle = useWeddingAction(({ task, done }: { task: Task; done: boolean }) =>
  weddingsApi.setDone(task.id, done),
)
async function setDone(task: Task, done: boolean): Promise<void> {
  try {
    await toggle.mutateAsync({ task, done })
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}

const newTitle = ref('')
const newAssignee = ref<string | null>(null)
const newDue = ref('')
const add = useWeddingAction(() =>
  weddingsApi.addTask(props.weddingId!, {
    title: newTitle.value.trim(),
    assignee: newAssignee.value,
    dueDate: newDue.value || null,
  }),
)
async function addTask(): Promise<void> {
  if (!newTitle.value.trim()) return
  try {
    await add.mutateAsync(undefined)
    newTitle.value = ''
    newDue.value = ''
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
const remove = useWeddingAction((task: Task) => weddingsApi.removeTask(task.id))
const standard = useWeddingAction(() => weddingsApi.standardTasks(props.weddingId!))
async function addStandard(): Promise<void> {
  try {
    const created = await standard.mutateAsync(undefined)
    toast.success(t('weddings.drawer.standardAdded', { count: created.length }))
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}

const memberOptions = computed(() => [
  { value: '', label: t('weddings.drawer.nobody') },
  ...(members.data.value ?? [])
    .filter((m) => m.isActive)
    .map((m) => ({ value: m.userId, label: m.fullName })),
])
const assignOpen = ref(false)
</script>

<template>
  <WDrawer
    v-model:open="open"
    :title="
      wedding.data.value
        ? t('weddings.drawer.title', { couple: wedding.data.value.title })
        : t('common.loading')
    "
  >
    <template v-if="wedding.data.value" #heading="{ titleId }">
      <div class="flex items-center gap-3">
        <WDateBlock v-if="wedding.data.value.date" :date="wedding.data.value.date" />
        <div class="min-w-0">
          <h2 :id="titleId" class="truncate text-[17px] font-semibold">
            {{ t('weddings.drawer.title', { couple: wedding.data.value.title }) }}
          </h2>
          <p class="truncate text-[13px] text-muted">
            {{
              [
                wedding.data.value.venue,
                wedding.data.value.guestCount
                  ? t('common.guests', { count: wedding.data.value.guestCount })
                  : '',
              ]
                .filter(Boolean)
                .join(', ')
            }}
          </p>
        </div>
      </div>
    </template>

    <div v-if="wedding.isPending.value" class="flex flex-col gap-3">
      <div v-for="n in 4" :key="n" class="skeleton h-10" />
    </div>
    <WEmptyState
      v-else-if="wedding.isError.value || !wedding.data.value"
      :title="t('weddings.notFound')"
    />

    <template v-else>
      <!-- Preparation -->
      <section class="flex flex-col gap-2">
        <div class="flex items-baseline justify-between">
          <h3>{{ t('weddings.drawer.preparation') }}</h3>
          <span class="num font-semibold">{{ wedding.data.value.progress }}&nbsp;%</span>
        </div>
        <WProgress
          :value="wedding.data.value.progress"
          :label="t('weddings.drawer.preparation')"
          ribbon
        />
      </section>

      <!-- Guests and tickets (docs/specs/devis-billets.md §6) -->
      <RouterLink
        :to="{ name: 'wedding-tickets', params: { id: wedding.data.value.id } }"
        class="flex items-center gap-3 rounded-wd border border-line px-3.5 py-3 hover:bg-surface-2"
        data-testid="wedding-tickets-link"
      >
        <Ticket class="size-5 text-violet" aria-hidden="true" />
        <span class="min-w-0 flex-1">
          <span class="block font-bold">{{ t('weddings.drawer.tickets') }}</span>
          <span class="block text-[12.5px] text-muted">{{ t('weddings.drawer.ticketsHint') }}</span>
        </span>
        <ChevronRight class="size-4 text-muted" aria-hidden="true" />
      </RouterLink>

      <!-- Money (roles that see balances) -->
      <dl v-if="contract.data.value" class="grid grid-cols-2 gap-4">
        <div>
          <dt class="text-[12.5px] font-semibold text-muted">{{ t('finance.fields.contract') }}</dt>
          <dd class="num mt-0.5 font-semibold">{{ formatMoney(contract.data.value.total) }}</dd>
        </div>
        <div>
          <dt class="text-[12.5px] font-semibold text-muted">
            {{ t('finance.fields.balanceDue') }}
          </dt>
          <dd class="num mt-0.5 font-semibold">{{ formatMoney(contract.data.value.balance) }}</dd>
        </div>
      </dl>

      <!-- Tasks -->
      <section class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-2">
          <h3>{{ t('weddings.drawer.tasks') }}</h3>
          <WButton
            v-if="canEdit && tasks.data.value && !tasks.data.value.length"
            size="sm"
            variant="secondary"
            :loading="standard.isPending.value"
            @click="addStandard"
            ><ListChecks class="size-[15px]" aria-hidden="true" />{{
              t('weddings.drawer.addStandard')
            }}</WButton
          >
        </div>
        <div v-if="tasks.isPending.value" class="skeleton h-24" />
        <p v-else-if="!sortedTasks.length" class="text-[13px] text-muted">
          {{ t('weddings.drawer.noTasks') }}
        </p>
        <ul v-else class="-my-1 divide-y divide-line">
          <li v-for="task in sortedTasks" :key="task.id" class="flex items-start gap-3 py-2.5">
            <button
              type="button"
              class="mt-0.5 flex size-[22px] shrink-0 items-center justify-center rounded-[7px] border-2 transition-colors disabled:cursor-default"
              :class="
                task.status === 'done'
                  ? 'border-green bg-green text-white'
                  : 'border-line-2 hover:border-violet'
              "
              role="checkbox"
              :aria-checked="task.status === 'done'"
              :aria-label="task.title"
              :disabled="!canEdit"
              @click="setDone(task, task.status !== 'done')"
            >
              <svg
                v-if="task.status === 'done'"
                viewBox="0 0 16 16"
                class="size-3.5"
                aria-hidden="true"
              >
                <path
                  d="M3.5 8.5l3 3 6-7"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2.2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
            </button>
            <div class="min-w-0 flex-1">
              <p class="font-semibold" :class="task.status === 'done' && 'text-muted line-through'">
                {{ task.title }}
              </p>
              <p class="text-[12.5px] text-muted">
                {{
                  [firstName(task.assigneeName), task.dueDate ? formatDate(task.dueDate) : '']
                    .filter(Boolean)
                    .join(', ') || t('weddings.drawer.unplanned')
                }}
              </p>
            </div>
            <WBadge v-if="dueBadge(task) === 'late'" tone="red">{{
              t('weddings.drawer.late')
            }}</WBadge>
            <WBadge v-else-if="dueBadge(task) === 'soon'" tone="coral">{{
              t('weddings.drawer.soon')
            }}</WBadge>
            <WButton
              v-if="canEdit"
              size="sm"
              variant="ghost"
              icon
              :aria-label="t('weddings.drawer.removeTask', { title: task.title })"
              @click="remove.mutate(task)"
            >
              <Trash2 class="size-[15px]" aria-hidden="true" />
            </WButton>
          </li>
        </ul>
        <form
          v-if="canEdit"
          class="grid grid-cols-[minmax(0,1fr)_auto] gap-2 sm:grid-cols-[minmax(0,1fr)_150px_140px_auto]"
          @submit.prevent="addTask"
        >
          <WInput
            v-model="newTitle"
            hide-label
            :label="t('weddings.drawer.newTask')"
            :placeholder="t('weddings.drawer.newTask')"
          />
          <WSelect
            v-model="newAssignee"
            class="hidden sm:block"
            hide-label
            :label="t('weddings.drawer.assignee')"
            :options="memberOptions"
          />
          <WInput
            v-model="newDue"
            class="hidden sm:block"
            type="date"
            hide-label
            :label="t('weddings.drawer.dueDate')"
          />
          <WButton
            type="submit"
            icon
            :aria-label="t('weddings.drawer.addTask')"
            :loading="add.isPending.value"
            :disabled="!newTitle.trim()"
            ><Plus class="size-[18px]" aria-hidden="true"
          /></WButton>
        </form>
      </section>

      <!-- Vendors -->
      <section class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-2">
          <h3>{{ t('weddings.drawer.vendors') }}</h3>
          <WButton v-if="canEdit" size="sm" variant="secondary" @click="assignOpen = true"
            ><Plus class="size-[15px]" aria-hidden="true" />{{
              t('weddings.drawer.addVendor')
            }}</WButton
          >
        </div>
        <p v-if="!vendors.data.value?.length" class="text-[13px] text-muted">
          {{ t('weddings.drawer.noVendors') }}
        </p>
        <ul v-else class="-my-1 divide-y divide-line">
          <li
            v-for="booking in vendors.data.value"
            :key="booking.id"
            class="flex items-center gap-3 py-2.5"
          >
            <div class="min-w-0 flex-1">
              <p class="truncate font-semibold">{{ booking.vendorName }}</p>
              <p class="truncate text-[12.5px] text-muted">
                {{ booking.service || booking.vendorCategoryLabel
                }}<template v-if="booking.due !== undefined && booking.due > 0">
                  · {{ t('weddings.drawer.due', { amount: formatMoney(booking.due) }) }}</template
                >
              </p>
            </div>
            <a
              v-if="booking.vendorPhone"
              :href="`tel:${booking.vendorPhone.replace(/\s/g, '')}`"
              class="inline-flex size-8 items-center justify-center rounded-[8px] border border-line-2 bg-surface hover:bg-surface-2"
              :aria-label="t('weddings.drawer.call', { name: booking.vendorName })"
            >
              <Phone class="size-[15px]" aria-hidden="true" />
            </a>
          </li>
        </ul>
      </section>
    </template>

    <template v-if="wedding.data.value?.contract && seesMoney" #footer>
      <WButton
        variant="secondary"
        class="ml-auto"
        :to="{ name: 'finance', query: { contract: wedding.data.value.contract } }"
        ><Wallet class="size-[18px]" aria-hidden="true" />{{
          t('weddings.drawer.payments')
        }}</WButton
      >
    </template>
  </WDrawer>

  <AssignVendorModal v-if="weddingId" v-model:open="assignOpen" :wedding-id="weddingId" />
</template>

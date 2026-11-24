<script setup lang="ts">
import { Camera, CircleCheck, IdCard, ImageUp, KeyRound, Trash2 } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { usePermissions } from '@/composables/usePermissions'
import { useToast } from '@/composables/useToast'
import { useSessionStore } from '@/stores/session'
import { WButton, WInput, WModal, WSelect, WSwitch, WTextarea } from '@/design'

import { type StaffInput, type StaffMember, staffApi, useStaffMutation } from '../api'
import BadgesModal from './BadgesModal.vue'
import StaffAccessModal from './StaffAccessModal.vue'

/** Create or edit a staff member (§7). Pay fields: owner and accountant only. */
const props = defineProps<{ member?: StaffMember | null }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [member: StaffMember] }>()
const { t } = useI18n()
const toast = useToast()
const { can } = usePermissions()
const seesPay = computed(() => can('viewMargins'))

const POSITIONS = [
  'Chef d’équipe',
  'Magasinier',
  'Livreur',
  'Chauffeur',
  'Installateur',
  'Décorateur',
  'Serveur',
  'Hôtesse',
]
const blank = (): Required<StaffInput> => ({
  fullName: '',
  phone: '',
  position: '',
  department: '',
  kind: 'day_worker',
  skills: [],
  payMode: 'daily',
  payRate: 0,
  mobileMoney: '',
  emergencyContact: '',
  notes: '',
  isActive: true,
  cnpsNumber: '',
  hireDate: null,
  category: '',
  declared: false,
})
const form = ref(blank())
// Server field errors (camelCase keys, api/errors.ts), shown under each field.
const errors = ref<Record<string, string | undefined>>({})
const photo = ref<File | null>(null)
const preview = ref<string | null>(null)
function pick(event: Event): void {
  photo.value = (event.target as HTMLInputElement).files?.[0] ?? null
  if (preview.value?.startsWith('blob:')) URL.revokeObjectURL(preview.value)
  preview.value = photo.value ? URL.createObjectURL(photo.value) : (props.member?.photoUrl ?? null)
}
const badgeOpen = ref(false)
const accessOpen = ref(false)
const granted = ref(false) // access just opened: the list refreshes behind
const session = useSessionStore()
const isOwner = computed(() => session.role === 'owner')
const skills = ref('')
watch(open, (value) => {
  if (!value) return
  const m = props.member
  granted.value = false
  errors.value = {}
  photo.value = null
  preview.value = m?.photoUrl ?? null
  form.value = m
    ? {
        fullName: m.fullName,
        phone: m.phone,
        position: m.position,
        department: m.department,
        kind: m.kind,
        skills: m.skills,
        payMode: m.payMode,
        payRate: m.payRate ?? 0,
        mobileMoney: m.mobileMoney,
        emergencyContact: m.emergencyContact,
        notes: m.notes,
        isActive: m.isActive,
        cnpsNumber: m.cnpsNumber ?? '',
        hireDate: m.hireDate,
        category: m.category,
        declared: m.declared ?? false,
      }
    : blank()
  skills.value = form.value.skills.join(', ')
})
const kindOptions = computed(() =>
  (['employee', 'day_worker', 'freelance'] as const).map((value) => ({
    value,
    label: t(`staff.kinds.${value}`),
  })),
)
const payOptions = computed(() =>
  (['monthly', 'daily', 'mission', 'hourly'] as const).map((value) => ({
    value,
    label: t(`staff.payModes.${value}`),
  })),
)
const save = useStaffMutation((input: StaffInput) =>
  props.member ? staffApi.update(props.member.id, input) : staffApi.create(input),
)
// « Supprimer » (feedback 13/11/2026): owner and planner, after a confirmation.
const canDelete = computed(() => session.role === 'owner' || session.role === 'planner')
const deleteOpen = ref(false)
const remove = useStaffMutation((id: string) => staffApi.remove(id))
async function confirmDelete(): Promise<void> {
  if (!props.member) return
  const name = props.member.fullName
  try {
    const done = await remove.mutateAsync(props.member.id)
    const parts = [t(done.permanent ? 'staff.delete.done' : 'staff.delete.doneKept', { name })]
    if (done.removedAssignments)
      parts.push(t('staff.delete.removedMissions', done.removedAssignments))
    if (done.accessClosed) parts.push(t('staff.delete.accessClosed'))
    toast.success(parts.join(' '))
    deleteOpen.value = false
    open.value = false
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}

async function submit(): Promise<void> {
  const input: StaffInput = {
    ...form.value,
    skills: skills.value
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean),
  }
  if (!seesPay.value) {
    delete input.payRate
    delete input.payMode
    delete input.cnpsNumber
    delete input.declared
  }
  if (!input.hireDate) input.hireDate = null
  errors.value = {}
  try {
    const member = await save.mutateAsync(input)
    if (photo.value) {
      try {
        await staffApi.photo(member.id, photo.value)
      } catch (error) {
        toast.error(toApiError(error).message) // the record is saved; the photo can be retried
      }
    }
    toast.success(
      t(props.member ? 'staff.form.saved' : 'staff.form.created', { name: member.fullName }),
    )
    emit('saved', member)
    open.value = false
  } catch (error) {
    const apiError = toApiError(error)
    errors.value = Object.fromEntries(
      Object.entries(apiError.fields).map(([field, messages]) => [field, messages[0]]),
    )
    // The message always shows; with field errors it says which field to fix.
    const first = Object.values(errors.value)[0]
    toast.error(first ? `${apiError.message} ${first}` : apiError.message)
  }
}
</script>

<template>
  <WModal v-model:open="open" :title="member ? t('staff.form.editTitle') : t('staff.form.title')">
    <form id="staff-form" class="grid gap-4 sm:grid-cols-2" @submit.prevent="submit">
      <div class="flex items-center gap-4 sm:col-span-2">
        <img
          v-if="preview"
          :src="preview"
          :alt="t('staff.form.photoAlt')"
          class="size-20 rounded-wd border border-line object-cover"
        />
        <div
          v-else
          class="flex size-20 items-center justify-center rounded-wd border border-dashed border-line-2 text-muted"
        >
          <Camera class="size-6" aria-hidden="true" />
        </div>
        <!-- Any picture from the gallery, or one taken now (feedback 15/11/2026); it is made
             square and light before sending (app/images.ts). -->
        <div class="flex flex-col gap-2">
          <label
            class="inline-flex h-10 cursor-pointer items-center gap-2 rounded-[10px] border border-violet/45 px-4 font-bold text-violet hover:bg-violet-soft"
          >
            <ImageUp class="size-[18px]" aria-hidden="true" />{{
              preview ? t('staff.form.changePhoto') : t('staff.form.choosePhoto')
            }}
            <input type="file" accept="image/*" class="sr-only" @change="pick" />
          </label>
          <label
            class="inline-flex h-10 cursor-pointer items-center gap-2 rounded-[10px] px-4 font-bold text-ink-2 hover:bg-surface-2"
          >
            <Camera class="size-[18px]" aria-hidden="true" />{{ t('staff.form.takePhoto') }}
            <input
              type="file"
              accept="image/*"
              capture="environment"
              class="sr-only"
              @change="pick"
            />
          </label>
        </div>
      </div>
      <!-- Wedivo access (feedback 13/11/2026): « Mes missions » for this person -->
      <div
        v-if="member"
        class="flex flex-wrap items-center gap-3 rounded-wd border border-line bg-surface-2 px-4 py-3 sm:col-span-2"
      >
        <span class="min-w-0 flex-1">
          <span class="block text-[14px] font-bold">{{ t('staff.access.label') }}</span>
          <span
            v-if="member.hasAccount || granted"
            class="mt-0.5 flex items-center gap-1.5 text-[13px] text-green"
          >
            <CircleCheck class="size-4" aria-hidden="true" />{{ t('staff.access.has') }}
          </span>
          <span v-else class="block text-[13px] text-muted">{{
            isOwner ? t('staff.access.none') : t('staff.access.ownerOnly')
          }}</span>
        </span>
        <WButton
          v-if="!member.hasAccount && !granted && isOwner"
          size="sm"
          variant="secondary"
          @click="accessOpen = true"
        >
          <KeyRound class="size-[15px]" aria-hidden="true" />{{ t('staff.access.open') }}
        </WButton>
      </div>
      <WInput
        v-model="form.fullName"
        :error="errors.fullName"
        class="sm:col-span-2"
        :label="t('staff.form.name')"
        required
        maxlength="120"
      />
      <WInput
        v-model="form.position"
        :error="errors.position"
        :label="t('staff.form.position')"
        list="staff-positions"
        required
        maxlength="80"
      />
      <datalist id="staff-positions">
        <option v-for="position in POSITIONS" :key="position" :value="position" />
      </datalist>
      <WInput
        v-model="form.department"
        :error="errors.department"
        :label="t('staff.form.department')"
        :placeholder="t('staff.form.departmentPlaceholder')"
        maxlength="80"
      />
      <WSelect
        v-model="form.kind"
        :error="errors.kind"
        :label="t('staff.form.kind')"
        :options="kindOptions"
      />
      <p v-if="member?.employeeNumber" class="self-end pb-2.5 text-[13px] text-ink-2">
        {{ t('staff.form.number') }} <b class="num">{{ member.employeeNumber }}</b>
      </p>
      <WInput
        v-model="form.phone"
        :error="errors.phone"
        type="tel"
        :label="t('staff.form.phone')"
      />
      <WInput
        v-model="form.mobileMoney"
        :error="errors.mobileMoney"
        :label="t('staff.form.mobileMoney')"
      />
      <template v-if="seesPay">
        <WSelect
          v-model="form.payMode"
          :error="errors.payMode"
          :label="t('staff.form.payMode')"
          :options="payOptions"
        />
        <WInput
          v-model.number="form.payRate"
          :error="errors.payRate"
          type="number"
          min="0"
          inputmode="numeric"
          addon="FCFA"
          :label="t(`staff.form.rate.${form.payMode}`)"
          :hint="t('staff.form.rateHint')"
        />
        <WInput
          v-model="form.cnpsNumber"
          :error="errors.cnpsNumber"
          :label="t('staff.form.cnps')"
        />
        <label class="flex items-center gap-2 self-end pb-2.5 text-[14px] font-semibold text-ink-2">
          <input v-model="form.declared" type="checkbox" class="size-5 accent-violet" />
          {{ t('staff.form.declared') }}
        </label>
      </template>
      <WInput
        v-model="form.hireDate"
        :error="errors.hireDate"
        type="date"
        :label="t('staff.form.hireDate')"
      />
      <WInput
        v-model="form.category"
        :error="errors.category"
        :label="t('staff.form.category')"
        :placeholder="t('staff.form.categoryPlaceholder')"
      />
      <WInput
        v-model="skills"
        :error="errors.skills"
        class="sm:col-span-2"
        :label="t('staff.form.skills')"
        :placeholder="t('staff.form.skillsPlaceholder')"
      />
      <WInput
        v-model="form.emergencyContact"
        :error="errors.emergencyContact"
        class="sm:col-span-2"
        :label="t('staff.form.emergency')"
      />
      <WTextarea
        v-model="form.notes"
        :error="errors.notes"
        class="sm:col-span-2"
        :label="t('staff.form.notes')"
        :rows="2"
      />
      <WSwitch
        v-if="member"
        v-model="form.isActive"
        class="sm:col-span-2"
        :label="t('staff.form.active')"
      />
      <div v-if="member && canDelete" class="border-t border-line pt-3 sm:col-span-2">
        <button
          type="button"
          class="inline-flex h-10 items-center gap-2 rounded-[10px] px-3 text-[14px] font-bold text-red hover:bg-red-soft"
          @click="deleteOpen = true"
        >
          <Trash2 class="size-[18px]" aria-hidden="true" />{{ t('staff.delete.action') }}
        </button>
      </div>
    </form>
    <template #footer>
      <WButton v-if="member" variant="secondary" class="mr-auto" @click="badgeOpen = true">
        <IdCard class="size-[18px]" aria-hidden="true" />{{ t('staff.badges.one') }}
      </WButton>
      <WButton variant="secondary" @click="open = false">{{ t('common.cancel') }}</WButton>
      <WButton type="submit" form="staff-form" :loading="save.isPending.value">{{
        t('staff.form.save')
      }}</WButton>
    </template>
  </WModal>
  <WModal
    v-if="member"
    v-model:open="deleteOpen"
    :title="t('staff.delete.title', { name: member.fullName })"
    size="sm"
  >
    <p class="text-[14px] text-ink-2">{{ t('staff.delete.text') }}</p>
    <template #footer>
      <WButton variant="secondary" @click="deleteOpen = false">{{ t('common.cancel') }}</WButton>
      <WButton variant="danger" :loading="remove.isPending.value" @click="confirmDelete">{{
        t('staff.delete.confirm')
      }}</WButton>
    </template>
  </WModal>
  <StaffAccessModal
    v-if="member"
    v-model:open="accessOpen"
    :member="member"
    @done="granted = true"
  />
  <BadgesModal
    v-if="member"
    v-model:open="badgeOpen"
    :staff-ids="[member.id]"
    :name="member.fullName"
  />
</template>

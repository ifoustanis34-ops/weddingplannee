<script setup lang="ts">
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { Ban, Infinity as InfinityIcon, RotateCcw, UserPlus } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import type { Plan, Role } from '@/api/auth'
import { type Agency, type AgencyMember, type AgencyUpdate, platformApi } from '@/api/platform'
import { formatDate, formatDateTime } from '@/composables/useDate'
import { useToast } from '@/composables/useToast'
import {
  WAvatar,
  WBadge,
  WButton,
  WDrawer,
  WInput,
  WNote,
  WSelect,
  WSwitch,
  WTextarea,
} from '@/design'

import { fieldErrors } from '../errors'
import AccountCreateModal from './AccountCreateModal.vue'
import AgencyBadges from './AgencyBadges.vue'

/** One agency: access (lifetime, suspension), offer and trial, identity, members and roles. */
const open = defineModel<boolean>('open', { default: false })
const props = defineProps<{ agencyId: string | null }>()
const { t } = useI18n()
const toast = useToast()
const queryClient = useQueryClient()

const agency = useQuery({
  queryKey: computed(() => ['platform', 'agency', props.agencyId]),
  queryFn: () => platformApi.agency(props.agencyId!),
  enabled: computed(() => !!props.agencyId),
})
const members = useQuery({
  queryKey: computed(() => ['platform', 'agency', props.agencyId, 'members']),
  queryFn: () => platformApi.agencyMembers(props.agencyId!),
  enabled: computed(() => !!props.agencyId),
})
const data = computed(() => agency.data.value)

function refresh(): void {
  void queryClient.invalidateQueries({ queryKey: ['platform'] })
}

// --- Form: identity, offer, trial, module, note ----------------------------------------------
const PLANS: Plan[] = ['essentiel', 'pro', 'agence']
const planOptions = PLANS.map((value) => ({
  value,
  label: value.charAt(0).toUpperCase() + value.slice(1),
}))
interface AgencyForm {
  name: string
  city: string
  country: string
  plan: Plan
  trialEnd: string
  weddingsEnabled: boolean
  adminNote: string
}
const form = ref<AgencyForm>({
  name: '',
  city: '',
  country: '',
  plan: 'pro',
  trialEnd: '',
  weddingsEnabled: false,
  adminNote: '',
})
const errors = ref<Record<string, string | undefined>>({})
const saving = ref(false)
const toDateInput = (value: string | null) => (value ? value.slice(0, 10) : '')
function reset(value: Agency | undefined): void {
  if (!value) return
  form.value = {
    name: value.name,
    city: value.city,
    country: value.country,
    plan: value.plan,
    trialEnd: toDateInput(value.trialEndsAt),
    weddingsEnabled: value.weddingsEnabled,
    adminNote: value.adminNote,
  }
  errors.value = {}
}
watch(data, reset, { immediate: true })

async function update(input: AgencyUpdate, message: string): Promise<boolean> {
  if (!props.agencyId) return false
  try {
    const updated = await platformApi.updateAgency(props.agencyId, input)
    queryClient.setQueryData(['platform', 'agency', props.agencyId], updated)
    refresh()
    toast.success(message)
    return true
  } catch (error) {
    const { fields, message: text } = fieldErrors(error)
    errors.value = fields
    if (!Object.keys(fields).length) toast.error(text)
    return false
  }
}

async function save(): Promise<void> {
  const f = form.value
  saving.value = true
  await update(
    {
      name: f.name.trim(),
      city: f.city.trim(),
      country: f.country.trim().toUpperCase(),
      plan: f.plan,
      trialEndsAt: f.trialEnd ? new Date(`${f.trialEnd}T23:59:59`).toISOString() : null,
      weddingsEnabled: f.weddingsEnabled,
      adminNote: f.adminNote,
    },
    t('platform.common.saved'),
  )
  saving.value = false
}

// --- Access: lifetime, suspension ------------------------------------------------------------
const lifetime = computed({
  get: () => !!data.value?.lifetimeAccess,
  set: (value: boolean) => {
    if (!data.value) return
    void update(
      { lifetimeAccess: value },
      t(
        value
          ? 'platform.agencies.detail.lifetimeGranted'
          : 'platform.agencies.detail.lifetimeRevoked',
        { name: data.value.name },
      ),
    )
  },
})
const reason = ref('')
const suspending = ref(false)
async function setActive(isActive: boolean): Promise<void> {
  if (!data.value) return
  suspending.value = true
  const done = await update(
    isActive ? { isActive } : { isActive, suspensionReason: reason.value.trim() },
    t(isActive ? 'platform.agencies.detail.reactivated' : 'platform.agencies.detail.suspended', {
      name: data.value.name,
    }),
  )
  if (done) reason.value = ''
  suspending.value = false
}

// --- Members ---------------------------------------------------------------------------------
const ROLES: Role[] = [
  'owner',
  'planner',
  'assistant',
  'accountant',
  'storekeeper',
  'team_lead',
  'staff',
]
const roleOptions = computed(() => ROLES.map((r) => ({ value: r, label: t(`roles.${r}`) })))
async function changeMember(
  member: AgencyMember,
  input: { role?: Role; isActive?: boolean },
  message: string,
): Promise<void> {
  try {
    await platformApi.updateMembership(member.id, input)
    refresh()
    toast.success(message)
  } catch (error) {
    toast.error(fieldErrors(error).message)
    refresh()
  }
}
const addOpen = ref(false)
</script>

<template>
  <WDrawer
    v-model:open="open"
    wide
    :title="data?.name ?? t('common.loading')"
    :subtitle="data?.slug"
  >
    <div v-if="agency.isPending.value" class="skeleton h-64" />
    <template v-else-if="data">
      <div class="flex flex-wrap items-center gap-2">
        <AgencyBadges :agency="data" />
        <span class="text-[13px] text-muted">{{
          t('platform.agencies.detail.created', { date: formatDate(data.createdAt) })
        }}</span>
      </div>

      <!-- Access -->
      <section class="flex flex-col gap-3 rounded-wd-lg border border-line p-4">
        <h3 class="flex items-center gap-2 font-semibold">
          <InfinityIcon class="size-[18px] text-violet" aria-hidden="true" />{{
            t('platform.agencies.detail.lifetime')
          }}
        </h3>
        <WSwitch
          v-model="lifetime"
          :label="t('platform.agencies.detail.lifetime')"
          :description="
            data.lifetimeAccess && data.lifetimeGrantedAt
              ? t('platform.agencies.detail.lifetimeSince', {
                  date: formatDate(data.lifetimeGrantedAt),
                })
              : t('platform.agencies.detail.lifetimeHint')
          "
        />
      </section>

      <section
        class="flex flex-col gap-3 rounded-wd-lg border p-4"
        :class="data.isActive ? 'border-line' : 'border-red bg-red-soft'"
      >
        <h3 class="font-semibold">{{ t('platform.agencies.detail.status') }}</h3>
        <template v-if="data.isActive">
          <p class="text-[13.5px] text-muted">{{ t('platform.agencies.detail.suspendHint') }}</p>
          <WInput v-model="reason" :label="t('platform.agencies.detail.suspendReason')" />
          <WButton
            variant="danger"
            class="self-start"
            :loading="suspending"
            @click="setActive(false)"
            ><Ban class="size-4" aria-hidden="true" />{{
              t('platform.agencies.detail.suspend')
            }}</WButton
          >
        </template>
        <template v-else>
          <p class="text-[13.5px] font-semibold text-red">
            {{
              t('platform.agencies.detail.suspendedSince', {
                date: data.suspendedAt ? formatDateTime(data.suspendedAt) : '—',
              })
            }}
          </p>
          <p v-if="data.suspensionReason" class="text-[13.5px]">{{ data.suspensionReason }}</p>
          <WButton class="self-start" :loading="suspending" @click="setActive(true)"
            ><RotateCcw class="size-4" aria-hidden="true" />{{
              t('platform.agencies.detail.reactivate')
            }}</WButton
          >
        </template>
      </section>

      <!-- Identity, offer, trial, note -->
      <form class="flex flex-col gap-4" novalidate @submit.prevent="save">
        <h3 class="font-semibold">{{ t('platform.agencies.detail.subscription') }}</h3>
        <div class="grid gap-4 sm:grid-cols-2">
          <WSelect
            v-model="form.plan"
            :label="t('platform.agencies.detail.plan')"
            :options="planOptions"
            :error="errors.plan"
          />
          <WInput
            v-model="form.trialEnd"
            type="date"
            :label="t('platform.agencies.detail.trialEndsAt')"
            :hint="data.lifetimeAccess ? undefined : t('platform.agencies.detail.trialHint')"
            :error="errors.trialEndsAt"
            :disabled="data.lifetimeAccess"
          />
        </div>
        <WSwitch v-model="form.weddingsEnabled" :label="t('platform.agencies.detail.weddings')" />
        <h3 class="mt-2 font-semibold">{{ t('platform.agencies.detail.identity') }}</h3>
        <WInput
          v-model="form.name"
          :label="t('platform.agencies.detail.name')"
          :error="errors.name"
          required
        />
        <div class="grid gap-4 sm:grid-cols-2">
          <WInput
            v-model="form.city"
            :label="t('platform.agencies.detail.city')"
            :error="errors.city"
          />
          <WInput
            v-model="form.country"
            maxlength="2"
            :label="t('platform.agencies.detail.country')"
            :error="errors.country"
          />
        </div>
        <WTextarea
          v-model="form.adminNote"
          :rows="3"
          :label="t('platform.agencies.detail.note')"
          :hint="t('platform.agencies.detail.noteHint')"
          :error="errors.adminNote"
        />
        <div class="flex gap-2">
          <WButton type="submit" :loading="saving">{{ t('platform.common.save') }}</WButton>
          <WButton variant="secondary" @click="reset(data)">{{ t('common.cancel') }}</WButton>
        </div>
      </form>

      <!-- Members -->
      <section class="flex flex-col gap-3">
        <div class="flex items-center gap-3">
          <h3 class="flex-1 font-semibold">{{ t('platform.agencies.detail.members') }}</h3>
          <WButton size="sm" @click="addOpen = true"
            ><UserPlus class="size-[15px]" aria-hidden="true" />{{
              t('platform.agencies.detail.addMember')
            }}</WButton
          >
        </div>
        <div v-if="members.isPending.value" class="skeleton h-32" />
        <WNote v-else-if="!members.data.value?.length">{{
          t('platform.agencies.detail.noMembers')
        }}</WNote>
        <ul v-else class="flex flex-col">
          <li
            v-for="member in members.data.value"
            :key="member.id"
            class="flex flex-col gap-2 border-b border-line py-3 last:border-0 sm:flex-row sm:items-center"
            :class="!member.isActive && 'opacity-60'"
          >
            <RouterLink
              :to="{ name: 'platform-accounts', query: { compte: member.userId } }"
              class="flex min-w-0 flex-1 items-center gap-3 hover:underline"
            >
              <WAvatar :name="member.fullName" />
              <span class="min-w-0">
                <span class="block truncate font-bold">{{ member.fullName }}</span>
                <span class="block truncate text-[12.5px] text-muted">{{ member.email }}</span>
                <span class="block text-[12px] text-muted">{{
                  t('platform.agencies.detail.lastLogin', {
                    date: member.lastLogin
                      ? formatDateTime(member.lastLogin)
                      : t('platform.common.never'),
                  })
                }}</span>
              </span>
            </RouterLink>
            <div class="flex flex-wrap items-center gap-2">
              <WBadge v-if="!member.userIsActive" tone="red">{{
                t('platform.agencies.detail.accountOff')
              }}</WBadge>
              <WBadge v-if="!member.isActive" tone="grey">{{
                t('platform.agencies.detail.accessOff')
              }}</WBadge>
              <WSelect
                :model-value="member.role"
                :label="member.fullName"
                hide-label
                class="w-44"
                :options="roleOptions"
                :disabled="!member.isActive"
                @update:model-value="
                  (role) =>
                    changeMember(
                      member,
                      { role: role as Role },
                      t('platform.agencies.detail.roleChanged', {
                        name: member.fullName,
                        role: t(`roles.${role}`),
                      }),
                    )
                "
              />
              <WButton
                size="sm"
                variant="ghost"
                :class="member.isActive && 'text-red'"
                @click="
                  changeMember(
                    member,
                    { isActive: !member.isActive },
                    member.isActive
                      ? t('platform.agencies.detail.removeAccess')
                      : t('platform.agencies.detail.restoreAccess'),
                  )
                "
                >{{
                  member.isActive
                    ? t('platform.agencies.detail.removeAccess')
                    : t('platform.agencies.detail.restoreAccess')
                }}</WButton
              >
            </div>
          </li>
        </ul>
      </section>
    </template>

    <AccountCreateModal
      v-if="data"
      v-model:open="addOpen"
      :agency="{ id: data.id, name: data.name }"
      @created="refresh"
    />
  </WDrawer>
</template>

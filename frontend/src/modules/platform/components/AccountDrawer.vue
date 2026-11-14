<script setup lang="ts">
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { KeyRound, Plus, ShieldCheck } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import type { Role } from '@/api/auth'
import {
  type Account,
  type AccountMembership,
  type AccountUpdate,
  platformApi,
} from '@/api/platform'
import { generatePassword } from '@/app/passwords'
import AccountCredentials from '@/components/AccountCredentials.vue'
import { formatDate, formatDateTime } from '@/composables/useDate'
import { useToast } from '@/composables/useToast'
import { WBadge, WButton, WDrawer, WInput, WNote, WSelect, WSwitch } from '@/design'
import { useSessionStore } from '@/stores/session'

import { fieldErrors } from '../errors'

/** One account: identity, on/off, console access, temporary password, agencies and roles. */
const open = defineModel<boolean>('open', { default: false })
const props = defineProps<{ accountId: string | null }>()
const { t } = useI18n()
const toast = useToast()
const session = useSessionStore()
const queryClient = useQueryClient()

const account = useQuery({
  queryKey: computed(() => ['platform', 'account', props.accountId]),
  queryFn: () => platformApi.account(props.accountId!),
  enabled: computed(() => !!props.accountId),
})
const data = computed(() => account.data.value)
const isSelf = computed(() => data.value?.id === session.user?.id)

function store(updated: Account): void {
  queryClient.setQueryData(['platform', 'account', updated.id], updated)
  void queryClient.invalidateQueries({ queryKey: ['platform'] })
}

// --- Identity --------------------------------------------------------------------------------
const form = ref({ fullName: '', email: '', phone: '' })
const errors = ref<Record<string, string | undefined>>({})
const saving = ref(false)
function reset(value: Account | undefined): void {
  if (!value) return
  form.value = { fullName: value.fullName, email: value.email, phone: value.phone }
  errors.value = {}
}
watch(data, reset, { immediate: true })

async function update(input: AccountUpdate, message: string): Promise<boolean> {
  if (!props.accountId) return false
  try {
    store(await platformApi.updateAccount(props.accountId, input))
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
  saving.value = true
  await update(
    {
      fullName: form.value.fullName.trim(),
      email: form.value.email.trim(),
      phone: form.value.phone.trim(),
    },
    t('platform.common.saved'),
  )
  saving.value = false
}

// --- Access ----------------------------------------------------------------------------------
const active = computed({
  get: () => !!data.value?.isActive,
  set: (value: boolean) => {
    if (!data.value) return
    void update(
      { isActive: value },
      t(value ? 'platform.accounts.detail.reactivated' : 'platform.accounts.detail.deactivated', {
        name: data.value.fullName,
      }),
    )
  },
})
const admin = computed({
  get: () => !!data.value?.isPlatformAdmin,
  set: (value: boolean) => {
    if (!data.value) return
    void update(
      { isPlatformAdmin: value },
      t(value ? 'platform.accounts.detail.adminGranted' : 'platform.accounts.detail.adminRevoked', {
        name: data.value.fullName,
      }),
    )
  },
})

// --- Temporary password ----------------------------------------------------------------------
const password = ref('')
const passwordError = ref<string | undefined>()
const settingPassword = ref(false)
const handedOver = ref<string | null>(null)
watch(
  () => props.accountId,
  () => {
    password.value = generatePassword()
    passwordError.value = undefined
    handedOver.value = null
  },
  { immediate: true },
)
async function setPassword(): Promise<void> {
  if (!data.value) return
  passwordError.value = undefined
  if (password.value.length < 8) {
    passwordError.value = t('credentials.tooShort')
    return
  }
  settingPassword.value = true
  try {
    await platformApi.setPassword(data.value.id, password.value)
    handedOver.value = password.value
    void account.refetch()
    toast.success(t('platform.accounts.detail.passwordSet', { name: data.value.fullName }))
  } catch (error) {
    const { fields, message } = fieldErrors(error)
    passwordError.value = fields.password ?? message
  } finally {
    settingPassword.value = false
  }
}

// --- Agencies --------------------------------------------------------------------------------
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
async function changeMembership(
  membership: AccountMembership,
  input: { role?: Role; isActive?: boolean },
): Promise<void> {
  try {
    await platformApi.updateMembership(membership.id, input)
    void account.refetch()
    void queryClient.invalidateQueries({ queryKey: ['platform'] })
    toast.success(t('platform.common.saved'))
  } catch (error) {
    toast.error(fieldErrors(error).message)
    void account.refetch()
  }
}

const agencies = useQuery({
  queryKey: ['platform', 'agencies', 'choices'],
  queryFn: () => platformApi.agencies({ pageSize: 100 }),
  enabled: computed(() => open.value),
  staleTime: 60_000,
})
const agencyOptions = computed(() => {
  const mine = new Set(
    data.value?.memberships.filter((m) => m.isActive).map((m) => m.organizationId) ?? [],
  )
  return (agencies.data.value?.results ?? [])
    .filter((a) => !mine.has(a.id))
    .map((a) => ({ value: a.id, label: a.name }))
})
const addition = ref<{ organizationId: string; role: Role }>({
  organizationId: '',
  role: 'planner',
})
const adding = ref(false)
async function addToAgency(): Promise<void> {
  if (!data.value || !addition.value.organizationId) return
  adding.value = true
  try {
    store(
      await platformApi.addMembership(
        data.value.id,
        addition.value.organizationId,
        addition.value.role,
      ),
    )
    const name = agencyOptions.value.find((o) => o.value === addition.value.organizationId)?.label
    toast.success(t('platform.accounts.detail.added', { name: data.value.fullName, agency: name }))
    addition.value = { organizationId: '', role: 'planner' }
  } catch (error) {
    toast.error(fieldErrors(error).message)
  } finally {
    adding.value = false
  }
}
</script>

<template>
  <WDrawer
    v-model:open="open"
    wide
    :title="data?.fullName ?? t('common.loading')"
    :subtitle="data?.email"
  >
    <div v-if="account.isPending.value" class="skeleton h-64" />
    <template v-else-if="data">
      <div class="flex flex-wrap items-center gap-2 text-[13px] text-muted">
        <WBadge :tone="data.isActive ? 'green' : 'red'">{{
          data.isActive
            ? t('platform.accounts.badges.active')
            : t('platform.accounts.badges.inactive')
        }}</WBadge>
        <WBadge v-if="data.isPlatformAdmin" tone="violet">{{
          t('platform.accounts.badges.admin')
        }}</WBadge>
        <WBadge v-if="data.mustChangePassword" tone="gold">{{
          t('platform.accounts.badges.temporary')
        }}</WBadge>
        <span
          >{{ t('platform.accounts.detail.joined') }} {{ formatDate(data.dateJoined) }} ·
          {{ t('platform.accounts.detail.lastLogin') }}
          {{ data.lastLogin ? formatDateTime(data.lastLogin) : t('platform.common.never') }}</span
        >
      </div>
      <WNote v-if="isSelf">{{ t('platform.accounts.detail.self') }}</WNote>

      <!-- Access -->
      <section class="flex flex-col gap-4 rounded-wd-lg border border-line p-4">
        <h3 class="font-semibold">{{ t('platform.accounts.detail.access') }}</h3>
        <WSwitch
          v-model="active"
          :disabled="isSelf"
          :label="t('platform.accounts.detail.active')"
          :description="t('platform.accounts.detail.activeHint')"
        />
        <WSwitch
          v-model="admin"
          :disabled="isSelf"
          :label="t('platform.accounts.detail.admin')"
          :description="t('platform.accounts.detail.adminHint')"
        >
        </WSwitch>
      </section>

      <!-- Identity -->
      <form class="flex flex-col gap-4" novalidate @submit.prevent="save">
        <h3 class="font-semibold">{{ t('platform.accounts.detail.identity') }}</h3>
        <WInput
          v-model="form.fullName"
          :label="t('platform.accounts.detail.fullName')"
          :error="errors.fullName"
          required
        />
        <div class="grid gap-4 sm:grid-cols-2">
          <WInput
            v-model="form.email"
            type="email"
            :label="t('platform.accounts.detail.email')"
            :error="errors.email"
            required
          />
          <WInput
            v-model="form.phone"
            type="tel"
            :label="t('platform.accounts.detail.phone')"
            :error="errors.phone"
          />
        </div>
        <div class="flex gap-2">
          <WButton type="submit" :loading="saving">{{ t('platform.common.save') }}</WButton>
          <WButton variant="secondary" @click="reset(data)">{{ t('common.cancel') }}</WButton>
        </div>
      </form>

      <!-- Password -->
      <section class="flex flex-col gap-3">
        <h3 class="flex items-center gap-2 font-semibold">
          <KeyRound class="size-[18px]" aria-hidden="true" />{{
            t('platform.accounts.detail.password')
          }}
        </h3>
        <AccountCredentials
          v-if="handedOver"
          :name="data.fullName"
          :email="data.email"
          :password="handedOver"
          :phone="data.phone"
          :organization-name="data.memberships[0]?.organizationName ?? t('platform.name')"
        />
        <template v-else>
          <p class="text-[13.5px] text-muted">{{ t('platform.accounts.detail.passwordHint') }}</p>
          <div class="flex flex-wrap items-end gap-2">
            <WInput
              v-model="password"
              class="min-w-[220px] flex-1"
              :label="t('credentials.temporary')"
              :error="passwordError"
              autocomplete="off"
              spellcheck="false"
            />
            <WButton
              variant="secondary"
              :loading="settingPassword"
              :class="passwordError && 'mb-[22px]'"
              @click="setPassword"
              >{{ t('platform.accounts.detail.setPassword') }}</WButton
            >
          </div>
        </template>
      </section>

      <!-- Agencies -->
      <section class="flex flex-col gap-3">
        <h3 class="font-semibold">{{ t('platform.accounts.detail.agencies') }}</h3>
        <WNote v-if="!data.memberships.length">{{ t('platform.accounts.noAgency') }}</WNote>
        <ul v-else class="flex flex-col">
          <li
            v-for="membership in data.memberships"
            :key="membership.id"
            class="flex flex-col gap-2 border-b border-line py-3 last:border-0 sm:flex-row sm:items-center"
            :class="!membership.isActive && 'opacity-60'"
          >
            <RouterLink
              :to="{ name: 'platform-agencies', query: { agence: membership.organizationId } }"
              class="min-w-0 flex-1 hover:underline"
            >
              <span class="block truncate font-bold">{{ membership.organizationName }}</span>
              <span class="block text-[12.5px] text-muted">{{ membership.organizationSlug }}</span>
            </RouterLink>
            <div class="flex flex-wrap items-center gap-2">
              <WBadge v-if="!membership.organizationIsActive" tone="red">{{
                t('platform.agencies.badges.suspended')
              }}</WBadge>
              <WSelect
                :model-value="membership.role"
                :label="membership.organizationName"
                hide-label
                class="w-44"
                :options="roleOptions"
                :disabled="!membership.isActive"
                @update:model-value="(role) => changeMembership(membership, { role: role as Role })"
              />
              <WButton
                size="sm"
                variant="ghost"
                :class="membership.isActive && 'text-red'"
                @click="changeMembership(membership, { isActive: !membership.isActive })"
                >{{
                  membership.isActive
                    ? t('platform.agencies.detail.removeAccess')
                    : t('platform.agencies.detail.restoreAccess')
                }}</WButton
              >
            </div>
          </li>
        </ul>
        <form
          class="flex flex-col gap-3 rounded-wd-lg bg-surface-2 p-4 sm:flex-row sm:items-end"
          @submit.prevent="addToAgency"
        >
          <WSelect
            v-model="addition.organizationId"
            class="flex-1"
            :label="t('platform.accounts.detail.agency')"
            :placeholder="t('platform.accounts.detail.addToAgency')"
            :options="agencyOptions"
          />
          <WSelect
            v-model="addition.role"
            class="sm:w-44"
            :label="t('platform.accounts.detail.role')"
            :options="roleOptions"
          />
          <WButton type="submit" :loading="adding" :disabled="!addition.organizationId"
            ><Plus class="size-4" aria-hidden="true" />{{
              t('platform.accounts.detail.add')
            }}</WButton
          >
        </form>
      </section>
    </template>
    <template v-if="data?.isPlatformAdmin" #footer>
      <p class="flex items-center gap-2 text-[13px] text-violet">
        <ShieldCheck class="size-4" aria-hidden="true" />{{
          t('platform.accounts.detail.adminHint')
        }}
      </p>
    </template>
  </WDrawer>
</template>

<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { Check, KeyRound, Mail, Minus, UserPlus } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import type { Role } from '@/api/auth'
import { toApiError } from '@/api/errors'
import { type Member, organizationApi } from '@/api/organization'
import { useToast } from '@/composables/useToast'
import { WAvatar, WBadge, WButton, WCard, WEmptyState, WSelect } from '@/design'
import { useSessionStore } from '@/stores/session'

import { type Right, RIGHTS } from '../constants'
import InviteModal from './InviteModal.vue'
import MemberAccountModal from './MemberAccountModal.vue'

/** « Équipe & rôles » (complement §15): members, pending invitations, rights per role. */
const { t } = useI18n()
const toast = useToast()
const session = useSessionStore()
const queryClient = useQueryClient()
const slug = computed(() => session.currentOrganization?.slug)

const members = useQuery({
  queryKey: computed(() => ['organization', slug.value, 'members']),
  queryFn: organizationApi.members,
})
const invitations = useQuery({
  queryKey: computed(() => ['organization', slug.value, 'invitations']),
  queryFn: organizationApi.invitations,
})
const refresh = () => {
  void queryClient.invalidateQueries({ queryKey: ['organization', slug.value] })
  void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
}

const ROLES: Exclude<Role, 'owner'>[] = [
  'planner',
  'assistant',
  'accountant',
  'storekeeper',
  'team_lead',
  'staff',
]
const roleOptions = computed(() => ROLES.map((r) => ({ value: r, label: t(`roles.${r}`) })))

const updateMember = useMutation({
  mutationFn: ({
    id,
    input,
  }: {
    id: string
    input: { role?: Member['role']; isActive?: boolean }
  }) => organizationApi.updateMember(id, input),
  onSuccess: refresh,
})
async function changeRole(member: Member, role: Member['role']): Promise<void> {
  try {
    await updateMember.mutateAsync({ id: member.id, input: { role } })
    toast.success(
      t('settings.team.roleChanged', { name: member.fullName, role: t(`roles.${role}`) }),
    )
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
async function setActive(member: Member, isActive: boolean): Promise<void> {
  try {
    await updateMember.mutateAsync({ id: member.id, input: { isActive } })
    toast.success(
      t(isActive ? 'settings.team.reactivated' : 'settings.team.deactivated', {
        name: member.fullName,
      }),
    )
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}

const cancel = useMutation({
  mutationFn: (id: string) => organizationApi.cancelInvitation(id),
  onSuccess: refresh,
})
async function cancelInvitation(id: string, email: string): Promise<void> {
  try {
    await cancel.mutateAsync(id)
    toast.success(t('settings.team.invitationCancelled', { email }))
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}

const inviteOpen = ref(false)
// « Créer un compte » (no member) or « Nouveau mot de passe » (that member).
const accountOpen = ref(false)
const accountFor = ref<Member | null>(null)
function openAccount(member: Member | null): void {
  accountFor.value = member
  accountOpen.value = true
}
const RIGHT_ROLES: Role[] = [
  'owner',
  'planner',
  'assistant',
  'accountant',
  'storekeeper',
  'team_lead',
  'staff',
]
const rightLabel = (right: Right) => t(`settings.team.rights.values.${right}`)
</script>

<template>
  <div class="flex flex-col gap-5">
    <WCard :title="t('settings.team.title')" :subtitle="t('settings.team.subtitle')">
      <template #actions>
        <WButton size="sm" variant="secondary" @click="inviteOpen = true"
          ><Mail class="size-[15px]" aria-hidden="true" />{{ t('settings.team.invite') }}</WButton
        >
        <WButton size="sm" @click="openAccount(null)"
          ><UserPlus class="size-[15px]" aria-hidden="true" />{{
            t('settings.team.create')
          }}</WButton
        >
      </template>
      <div v-if="members.isPending.value" class="skeleton h-40" />
      <WEmptyState
        v-else-if="members.isError.value"
        :title="t('settings.team.loadError')"
        :description="toApiError(members.error.value).message"
      />
      <div v-else class="overflow-x-auto">
        <table class="w-full min-w-[640px] border-collapse text-[14px]">
          <caption class="sr-only">
            {{
              t('settings.team.title')
            }}
          </caption>
          <thead>
            <tr class="text-left text-[12.5px] font-bold text-muted">
              <th scope="col" class="border-b border-line px-3 py-2.5">
                {{ t('settings.team.member') }}
              </th>
              <th scope="col" class="border-b border-line px-3 py-2.5">
                {{ t('settings.team.role') }}
              </th>
              <th scope="col" class="border-b border-line px-3 py-2.5">
                {{ t('settings.team.status') }}
              </th>
              <th scope="col" class="border-b border-line px-3 py-2.5">
                <span class="sr-only">{{ t('settings.team.actions') }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="member in members.data.value" :key="member.id">
              <td class="border-b border-line px-3 py-[13px]">
                <span class="flex items-center gap-3">
                  <WAvatar :name="member.fullName" />
                  <span class="min-w-0">
                    <span class="block font-bold">{{ member.fullName }}</span>
                    <span class="block text-[12.5px] text-muted">{{ member.email }}</span>
                  </span>
                </span>
              </td>
              <td class="border-b border-line px-3 py-[13px]">
                <span v-if="member.role === 'owner'" class="font-semibold">{{
                  member.roleLabel
                }}</span>
                <WSelect
                  v-else
                  :model-value="member.role"
                  :label="t('settings.team.roleOf', { name: member.fullName })"
                  hide-label
                  class="w-48"
                  :options="roleOptions"
                  :disabled="updateMember.isPending.value || !member.isActive"
                  @update:model-value="(role) => changeRole(member, role as Member['role'])"
                />
              </td>
              <td class="border-b border-line px-3 py-[13px]">
                <WBadge :tone="member.isActive ? 'green' : 'grey'">{{
                  member.isActive ? t('settings.team.active') : t('settings.team.inactive')
                }}</WBadge>
              </td>
              <td class="border-b border-line px-3 py-[13px] text-right whitespace-nowrap">
                <WButton
                  v-if="member.role !== 'owner' && member.isActive"
                  size="sm"
                  variant="ghost"
                  @click="openAccount(member)"
                  ><KeyRound class="size-[15px]" aria-hidden="true" />{{
                    t('settings.team.setPassword')
                  }}</WButton
                >
                <WButton
                  v-if="member.role !== 'owner'"
                  size="sm"
                  variant="ghost"
                  :class="member.isActive && 'text-red'"
                  @click="setActive(member, !member.isActive)"
                  >{{
                    member.isActive ? t('settings.team.deactivate') : t('settings.team.reactivate')
                  }}</WButton
                >
              </td>
            </tr>
            <tr v-for="invitation in invitations.data.value ?? []" :key="invitation.id">
              <td class="border-b border-line px-3 py-[13px]">
                <span class="flex items-center gap-3">
                  <WAvatar :name="invitation.email" />
                  <span class="font-bold">{{ invitation.email }}</span>
                </span>
              </td>
              <td class="border-b border-line px-3 py-[13px] font-semibold">
                {{ invitation.roleLabel }}
              </td>
              <td class="border-b border-line px-3 py-[13px]">
                <WBadge tone="gold">{{ t('settings.team.invited') }}</WBadge>
              </td>
              <td class="border-b border-line px-3 py-[13px] text-right">
                <WButton
                  size="sm"
                  variant="ghost"
                  @click="cancelInvitation(invitation.id, invitation.email)"
                  >{{ t('settings.team.cancelInvitation') }}</WButton
                >
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </WCard>

    <WCard :title="t('settings.team.rights.title')">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[640px] border-collapse text-[14px]">
          <caption class="sr-only">
            {{
              t('settings.team.rights.title')
            }}
          </caption>
          <thead>
            <tr class="text-[12.5px] font-bold text-muted">
              <th scope="col" class="border-b border-line px-3 py-2.5 text-left">
                <span class="sr-only">{{ t('settings.team.rights.area') }}</span>
              </th>
              <th
                v-for="role in RIGHT_ROLES"
                :key="role"
                scope="col"
                class="border-b border-line px-3 py-2.5 text-center"
              >
                {{ t(`roles.${role}`) }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in RIGHTS" :key="row.key">
              <th scope="row" class="border-b border-line px-3 py-3 text-left font-bold">
                {{ t(`settings.team.rights.areas.${row.key}`) }}
              </th>
              <td
                v-for="role in RIGHT_ROLES"
                :key="role"
                class="border-b border-line px-3 py-3 text-center"
              >
                <span
                  v-if="row[role] === 'yes'"
                  class="inline-flex text-green"
                  :title="rightLabel('yes')"
                >
                  <Check class="size-[18px]" aria-hidden="true" /><span class="sr-only">{{
                    rightLabel('yes')
                  }}</span>
                </span>
                <span
                  v-else-if="row[role] === 'no'"
                  class="inline-flex text-muted"
                  :title="rightLabel('no')"
                >
                  <Minus class="size-[18px]" aria-hidden="true" /><span class="sr-only">{{
                    rightLabel('no')
                  }}</span>
                </span>
                <span v-else class="text-[12.5px] font-semibold text-ink-2">{{
                  rightLabel(row[role])
                }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </WCard>

    <InviteModal v-model:open="inviteOpen" @invited="refresh" />
    <MemberAccountModal v-model:open="accountOpen" :member="accountFor" @done="refresh" />
  </div>
</template>

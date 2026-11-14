<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import type { Agency } from '@/api/platform'
import { formatDate } from '@/composables/useDate'
import { WBadge } from '@/design'

/** Access of an agency at a glance: suspended, lifetime, trial (until when) or trial over. */
const props = defineProps<{ agency: Agency }>()
const { t } = useI18n()
const trialRunning = () =>
  !!props.agency.trialEndsAt && new Date(props.agency.trialEndsAt) > new Date()
</script>

<template>
  <span class="flex flex-wrap gap-1.5">
    <WBadge v-if="!agency.isActive" tone="red">{{
      t('platform.agencies.badges.suspended')
    }}</WBadge>
    <WBadge v-if="agency.lifetimeAccess" tone="violet">{{
      t('platform.agencies.badges.lifetime')
    }}</WBadge>
    <template v-else-if="agency.isActive">
      <WBadge v-if="trialRunning()" tone="gold">{{
        t('platform.agencies.badges.trialUntil', { date: formatDate(agency.trialEndsAt!) })
      }}</WBadge>
      <WBadge v-else tone="grey">{{ t('platform.agencies.badges.trialOver') }}</WBadge>
    </template>
  </span>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import { WAvatar, WCard } from '@/design'

import type { DashboardSummary } from '../api'

/**
 * « Équipe du jour »: who has something to do today and where they stand. Staff check-in
 * (arrival, departure) replaces the task count with step S7.
 */
defineProps<{ team: DashboardSummary['teamToday'] }>()
const { t } = useI18n()
const DOT = {
  done: 'bg-green',
  in_progress: 'bg-gold-bright',
  todo: 'bg-line-2',
  absent: 'bg-red',
} as const
</script>

<template>
  <WCard :title="t('dashboard.team.title')" :subtitle="t('dashboard.team.subtitle')" class="h-full">
    <p v-if="!team.length" class="text-muted">{{ t('dashboard.team.empty') }}</p>
    <ul v-else class="flex flex-wrap gap-x-5 gap-y-3">
      <li v-for="member in team" :key="member.name" class="flex items-center gap-2.5">
        <span class="relative">
          <WAvatar :name="member.name" :size="38" />
          <span
            class="absolute -right-0.5 -bottom-0.5 size-3 rounded-full ring-2 ring-surface"
            :class="DOT[member.status]"
            aria-hidden="true"
          />
        </span>
        <span class="min-w-0">
          <span class="block truncate text-[13.5px] font-bold">{{ member.name }}</span>
          <span class="block text-[12px] text-muted"
            >{{ t(`dashboard.team.status.${member.status}`)
            }}<template v-if="member.late"> ({{ t('dashboard.team.late') }})</template> ·
            {{ t('dashboard.team.progress', { done: member.done, total: member.total }) }}</span
          >
        </span>
      </li>
    </ul>
  </WCard>
</template>

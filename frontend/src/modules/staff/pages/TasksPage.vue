<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import DownloadMenu from '@/components/DownloadMenu.vue'
import { useSessionStore } from '@/stores/session'

import TasksTab from '../components/TasksTab.vue'

/** « Tâches » in the sidebar (feedback 13/11/2026): who does what, on which event. */
const { t } = useI18n()
const session = useSessionStore()
const canEdit = computed(() => session.role === 'owner' || session.role === 'planner')
</script>

<template>
  <div class="flex flex-col gap-[22px]">
    <header class="flex flex-wrap items-end gap-x-6 gap-y-3">
      <div class="min-w-0 flex-1">
        <h1>{{ t('staff.tasks.pageTitle') }}</h1>
        <p class="mt-1 max-w-[64ch] text-muted">{{ t('staff.tasks.pageSubtitle') }}</p>
      </div>
      <DownloadMenu url="/exports/tasks" filename="taches" />
    </header>
    <TasksTab :can-edit="canEdit" />
  </div>
</template>

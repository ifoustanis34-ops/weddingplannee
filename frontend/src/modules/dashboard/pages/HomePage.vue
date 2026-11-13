<script setup lang="ts">
import { computed, defineAsyncComponent } from 'vue'

import PushPrompt from '@/components/PushPrompt.vue'
import { useSessionStore } from '@/stores/session'

/**
 * Home (feedback 13/11/2026): staff and team leads land on « Mon espace » (their day and their
 * own figures); every other role keeps the agency's dashboard.
 */
const DashboardPage = defineAsyncComponent(() => import('./DashboardPage.vue'))
const MySpace = defineAsyncComponent(() => import('@/modules/staff/components/MySpace.vue'))
const session = useSessionStore()
const personal = computed(() => session.role === 'staff' || session.role === 'team_lead')
</script>

<template>
  <div class="flex flex-col gap-4">
    <PushPrompt />
    <MySpace v-if="personal" />
    <DashboardPage v-else />
  </div>
</template>

<script setup lang="ts">
import { useQueryClient } from '@tanstack/vue-query'
import { type Component, computed, watch } from 'vue'
import { useRoute } from 'vue-router'

import ShareReady from '@/components/ShareReady.vue'
import { WToast } from '@/design'
import { usePreferencesStore } from '@/stores/preferences'
import { useSessionStore } from '@/stores/session'

import AppLayout from './layouts/AppLayout.vue'
import AuthLayout from './layouts/AuthLayout.vue'
import PlatformLayout from './layouts/PlatformLayout.vue'

// Instantiating the store applies the remembered theme before the first render.
usePreferencesStore()
const route = useRoute()
const session = useSessionStore()
const queryClient = useQueryClient()

const LAYOUTS: Record<string, Component | undefined> = {
  app: AppLayout,
  auth: AuthLayout,
  platform: PlatformLayout,
}
const layout = computed(() => LAYOUTS[route.meta.layout ?? 'blank'])

// Every cached server answer belongs to one organization: drop them when switching space.
watch(
  () => session.currentSlug,
  (slug, previous) => {
    if (previous !== undefined && slug !== previous) queryClient.clear()
  },
)
</script>

<template>
  <component :is="layout" v-if="layout">
    <RouterView />
  </component>
  <RouterView v-else />
  <WToast />
  <ShareReady />
</template>

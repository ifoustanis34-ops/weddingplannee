<script setup lang="ts">
import { MapPinOff } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import { WButton, WEmptyState } from '@/design'

const { t } = useI18n()
</script>

<template>
  <main class="flex min-h-dvh items-center justify-center px-4">
    <WEmptyState :icon="MapPinOff" :title="t('notFound.title')" :description="t('notFound.text')">
      <WButton :to="{ name: 'dashboard' }">{{ t('notFound.home') }}</WButton>
    </WEmptyState>
  </main>
</template>

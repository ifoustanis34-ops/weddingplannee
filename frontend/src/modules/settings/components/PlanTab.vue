<script setup lang="ts">
import { CircleCheck, Sparkles } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import { WCard } from '@/design'

/**
 * « Abonnement » (feedback 15/11/2026): no offers nor prices for now. Every agency has every
 * feature; subscriptions and their payment come with a later update.
 */
const { t } = useI18n()
const FEATURES = ['clients', 'reservations', 'stock', 'finance', 'team', 'weddings'] as const
</script>

<template>
  <WCard>
    <div class="flex flex-col gap-4">
      <div class="flex items-start gap-3">
        <span
          class="flex size-10 shrink-0 items-center justify-center rounded-[10px] bg-violet-soft text-violet"
        >
          <Sparkles class="size-5" aria-hidden="true" />
        </span>
        <div>
          <h2 class="text-[17px] font-semibold">{{ t('settings.plan.includedTitle') }}</h2>
          <p class="mt-1 text-ink-2">{{ t('settings.plan.includedText') }}</p>
        </div>
      </div>
      <ul class="grid gap-2 sm:grid-cols-2">
        <li v-for="feature in FEATURES" :key="feature" class="flex items-center gap-2">
          <CircleCheck class="size-[18px] shrink-0 text-green" aria-hidden="true" />{{
            t(`settings.plan.features.${feature}`)
          }}
        </li>
      </ul>
      <p class="rounded-wd bg-surface-2 px-3.5 py-3 text-[13.5px] text-muted">
        {{ t('settings.plan.later') }}
      </p>
    </div>
  </WCard>
</template>

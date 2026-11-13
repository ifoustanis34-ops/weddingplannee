<script setup lang="ts">
import { CalendarDays, Mail, MessageCircle, Smartphone } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import { WBadge, WButton, WCard } from '@/design'

/**
 * « Intégrations » (complement §15). Only the email sending is integrated today; the others are
 * shown as « Bientôt » with a disabled button: the UI never promises what is not built (§2).
 */
const { t } = useI18n()
const INTEGRATIONS = [
  { key: 'email', icon: Mail, status: 'connected' },
  { key: 'whatsapp', icon: MessageCircle, status: 'soon' },
  { key: 'mobileMoney', icon: Smartphone, status: 'soon' },
  { key: 'googleCalendar', icon: CalendarDays, status: 'soon' },
] as const
</script>

<template>
  <WCard :title="t('settings.integrations.title')" :subtitle="t('settings.integrations.subtitle')">
    <ul class="-my-1 divide-y divide-line">
      <li v-for="item in INTEGRATIONS" :key="item.key" class="flex items-center gap-3 py-3.5">
        <span class="flex size-9 shrink-0 items-center justify-center rounded-[10px] bg-surface-2">
          <component :is="item.icon" class="size-[18px] text-ink-2" aria-hidden="true" />
        </span>
        <div class="min-w-0 flex-1">
          <p class="font-bold">{{ t(`settings.integrations.items.${item.key}.title`) }}</p>
          <p class="text-[13px] text-muted">
            {{ t(`settings.integrations.items.${item.key}.text`) }}
          </p>
        </div>
        <WBadge v-if="item.status === 'connected'" tone="green">{{
          t('settings.integrations.connected')
        }}</WBadge>
        <template v-else>
          <WBadge tone="grey" :dot="false">{{ t('settings.integrations.soon') }}</WBadge>
          <WButton size="sm" variant="secondary" disabled>{{
            t('settings.integrations.connect')
          }}</WButton>
        </template>
      </li>
    </ul>
  </WCard>
</template>

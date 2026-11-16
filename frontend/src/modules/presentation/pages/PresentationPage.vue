<script setup lang="ts">
import { Building2, CalendarCheck, MonitorPlay, Package, Play, Users, Wallet } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { WBadge, WButton, WEmptyState } from '@/design'
import { useSessionStore } from '@/stores/session'

import { useDemoConfig } from '../api'
import { speed, startPresentation } from '../player'
import { SCENARIOS, SPEEDS, scenarioSeconds } from '../scenarios'

/**
 * « Mode présentation » (feedback 16/11/2026): the journeys the app can play by itself on the
 * demo agency's fictitious data, from every role's point of view. Open on demo agencies only.
 */
const { t } = useI18n()
const session = useSessionStore()
const config = useDemoConfig()
const ICONS = {
  building: Building2,
  calendar: CalendarCheck,
  package: Package,
  users: Users,
  wallet: Wallet,
} as const
const available = computed(() => new Set(config.data.value?.roles ?? []))
/** A journey needs every role it shows to exist in the demo agency. */
const playable = (roles: string[]) => roles.every((role) => available.value.has(role as never))
const minutes = (seconds: number) => Math.max(1, Math.round(seconds / 60))
</script>

<template>
  <div class="flex flex-col gap-[22px]">
    <header class="flex flex-wrap items-end gap-x-6 gap-y-3">
      <div class="min-w-0 flex-1">
        <h1>{{ t('presentation.page.title') }}</h1>
        <p class="mt-1 max-w-[70ch] text-muted">{{ t('presentation.page.subtitle') }}</p>
      </div>
      <span
        class="inline-flex items-center gap-1 rounded-[12px] border border-line bg-surface p-1"
        role="group"
        :aria-label="t('presentation.player.speed')"
      >
        <span class="px-2 text-[13px] font-semibold text-muted">{{
          t('presentation.player.speed')
        }}</span>
        <button
          v-for="value in SPEEDS"
          :key="value"
          type="button"
          class="num rounded-[9px] px-3 py-1.5 text-[13px] font-bold"
          :class="speed === value ? 'bg-violet text-white' : 'text-ink-2 hover:bg-surface-2'"
          :aria-pressed="speed === value"
          @click="speed = value"
        >
          {{ String(value).replace('.', ',') }}×
        </button>
      </span>
    </header>

    <div v-if="config.isPending.value" class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <div v-for="n in 3" :key="n" class="skeleton h-56 rounded-wd-lg" />
    </div>
    <WEmptyState
      v-else-if="config.isError.value"
      :title="t('presentation.page.loadError')"
      :description="toApiError(config.error.value).message"
    />
    <WEmptyState
      v-else-if="!config.data.value?.enabled"
      :icon="MonitorPlay"
      :title="t('presentation.page.closedTitle')"
      :description="t('presentation.page.closedText')"
    />
    <template v-else>
      <p class="rounded-wd border border-line bg-surface-2 px-4 py-3 text-[13.5px] text-ink-2">
        {{ t('presentation.page.keys') }}
      </p>
      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <article
          v-for="item in SCENARIOS"
          :key="item.id"
          class="flex flex-col gap-3 rounded-wd-lg border border-line bg-surface p-5"
        >
          <span
            class="flex size-11 items-center justify-center rounded-[12px] bg-violet-soft text-violet"
          >
            <component :is="ICONS[item.icon]" class="size-[22px]" aria-hidden="true" />
          </span>
          <div>
            <h2 class="text-[17px] font-semibold">
              {{ t(`presentation.scenarios.${item.id}.title`) }}
            </h2>
            <p class="mt-1 text-[13.5px] leading-relaxed text-ink-2">
              {{ t(`presentation.scenarios.${item.id}.description`) }}
            </p>
          </div>
          <div class="flex flex-wrap items-center gap-1.5">
            <WBadge v-for="role in item.roles" :key="role" tone="violet">{{
              t(`roles.${role}`)
            }}</WBadge>
            <span class="num ml-auto text-[12.5px] text-muted">{{
              t('presentation.page.length', {
                steps: item.steps.length,
                minutes: minutes(scenarioSeconds(item)),
              })
            }}</span>
          </div>
          <WButton
            class="mt-auto"
            block
            :disabled="!playable(item.roles)"
            @click="startPresentation(item.id, session.role)"
          >
            <Play class="size-[18px]" aria-hidden="true" />{{ t('presentation.page.play') }}
          </WButton>
          <p v-if="!playable(item.roles)" class="text-[12.5px] text-muted">
            {{ t('presentation.page.missingRole') }}
          </p>
        </article>
      </div>
    </template>
  </div>
</template>

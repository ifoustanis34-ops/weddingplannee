<script setup lang="ts">
import {
  ArrowLeft,
  Building2,
  LayoutDashboard,
  LogOut,
  ScrollText,
  ShieldCheck,
  UserRound,
  Users,
} from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import { WAvatar, WLogo } from '@/design'
import { useSessionStore } from '@/stores/session'

/** Menu of the platform console, on desktop and in the mobile drawer. */
const emit = defineEmits<{ navigate: []; logout: [] }>()
const { t } = useI18n()
const route = useRoute()
const session = useSessionStore()

const items = [
  { name: 'platform-overview', label: 'overview', icon: LayoutDashboard },
  { name: 'platform-agencies', label: 'agencies', icon: Building2 },
  { name: 'platform-accounts', label: 'accounts', icon: Users },
  { name: 'platform-journal', label: 'journal', icon: ScrollText },
] as const
const isActive = (name: string) => route.name === name
const hasSpace = computed(() => session.organizations.length > 0)
</script>

<template>
  <div class="flex h-full flex-col px-3.5 pt-[18px] pb-3.5">
    <RouterLink
      :to="{ name: 'platform-overview' }"
      class="self-start rounded-wd px-2 pt-1 pb-3"
      @click="emit('navigate')"
    >
      <WLogo />
    </RouterLink>
    <p
      class="mx-2 mb-2 inline-flex items-center gap-1.5 self-start rounded-full bg-violet-soft px-2.5 py-1 text-[12px] font-bold text-violet"
    >
      <ShieldCheck class="size-[14px]" aria-hidden="true" />{{ t('platform.badge') }}
    </p>
    <nav :aria-label="t('platform.nav.label')" class="-mx-3.5 mt-2 flex-1 overflow-y-auto px-3.5">
      <RouterLink
        v-for="item in items"
        :key="item.name"
        :to="{ name: item.name }"
        class="relative flex items-center gap-[11px] rounded-[10px] px-2.5 py-[9px] text-[14px] font-semibold transition-colors"
        :class="
          isActive(item.name)
            ? 'bg-surface-2 text-ink'
            : 'text-ink-2 hover:bg-surface-2 hover:text-ink'
        "
        :aria-current="isActive(item.name) ? 'page' : undefined"
        @click="emit('navigate')"
      >
        <span
          v-if="isActive(item.name)"
          class="absolute top-2 bottom-2 -left-3.5 w-1 rounded-r-[4px] bg-ribbon"
          aria-hidden="true"
        />
        <component :is="item.icon" class="size-[18px] shrink-0" aria-hidden="true" />
        {{ t(`platform.nav.${item.label}`) }}
      </RouterLink>
      <RouterLink
        v-if="hasSpace"
        :to="{ name: 'dashboard' }"
        class="mt-4 flex items-center gap-[11px] rounded-[10px] px-2.5 py-[9px] text-[14px] font-semibold text-ink-2 hover:bg-surface-2 hover:text-ink"
        @click="emit('navigate')"
      >
        <ArrowLeft class="size-[18px] shrink-0" aria-hidden="true" />{{
          t('platform.nav.backToSpace')
        }}
      </RouterLink>
    </nav>
    <div class="mt-2 border-t border-line pt-3">
      <RouterLink
        :to="{ name: 'platform-profile' }"
        class="flex items-center gap-2.5 rounded-[10px] px-1 py-1 hover:bg-surface-2"
        @click="emit('navigate')"
      >
        <WAvatar :name="session.user?.fullName ?? ''" />
        <span class="min-w-0 flex-1">
          <span class="block truncate text-[13.5px] font-bold">{{ session.user?.fullName }}</span>
          <span class="block truncate text-[12px] text-muted">{{ t('platform.badge') }}</span>
        </span>
        <UserRound class="size-4 shrink-0 text-muted" aria-hidden="true" />
        <span class="sr-only">{{ t('platform.nav.profile') }}</span>
      </RouterLink>
      <button
        type="button"
        class="mt-2 flex w-full items-center gap-[11px] rounded-[10px] px-2.5 py-2 text-[14px] font-semibold text-ink-2 hover:bg-surface-2 hover:text-ink"
        @click="emit('logout')"
      >
        <LogOut class="size-[18px]" aria-hidden="true" />{{ t('shell.logout') }}
      </button>
    </div>
  </div>
</template>

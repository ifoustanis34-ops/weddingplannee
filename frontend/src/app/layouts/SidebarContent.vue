<script setup lang="ts">
import { LogOut, ShieldCheck, UserRound } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import { menuItems, NAV_GROUPS, type NavItem, phaseTag } from '@/app/navigation'
import { WAvatar, WLogo, WPhaseTag } from '@/design'
import { useSessionStore } from '@/stores/session'

import OrganizationSwitcher from './OrganizationSwitcher.vue'

/** Sidebar of the desktop shell, reused as is in the mobile drawer (complement §5). */
const emit = defineEmits<{ navigate: []; logout: [] }>()
const { t } = useI18n()
const route = useRoute()
const session = useSessionStore()

const groups = computed(() => {
  const items = menuItems(session.role, session.weddingsEnabled)
  return NAV_GROUPS.map((group) => ({
    group,
    items: items.filter((item) => item.group === group),
  })).filter((entry) => entry.items.length)
})
const isActive = (item: NavItem) => route.name === item.routeName || route.meta.navKey === item.key
</script>

<template>
  <div class="flex h-full flex-col px-3.5 pt-[18px] pb-3.5">
    <RouterLink
      :to="{ name: 'dashboard' }"
      class="self-start rounded-wd px-2 pt-1 pb-[18px]"
      @click="emit('navigate')"
    >
      <WLogo />
    </RouterLink>
    <OrganizationSwitcher />

    <nav :aria-label="t('nav.label')" class="-mx-3.5 mt-1 flex-1 overflow-y-auto px-3.5">
      <div v-for="entry in groups" :key="entry.group">
        <p class="px-2.5 pt-3.5 pb-1.5 text-[12px] font-bold text-muted">
          {{ t(`nav.groups.${entry.group}`) }}
        </p>
        <RouterLink
          v-for="item in entry.items"
          :key="item.key"
          :to="{ name: item.routeName }"
          class="relative flex items-center gap-[11px] rounded-[10px] px-2.5 py-[9px] text-[14px] font-semibold transition-colors"
          :class="
            isActive(item)
              ? 'bg-surface-2 text-ink'
              : 'text-ink-2 hover:bg-surface-2 hover:text-ink'
          "
          :aria-current="isActive(item) ? 'page' : undefined"
          @click="emit('navigate')"
        >
          <span
            v-if="isActive(item)"
            class="absolute top-2 bottom-2 -left-3.5 w-1 rounded-r-[4px] bg-ribbon"
            aria-hidden="true"
          />
          <component :is="item.icon" class="size-[18px] shrink-0" aria-hidden="true" />
          <span class="min-w-0 flex-1 truncate">{{ t(`nav.${item.label}`) }}</span>
          <WPhaseTag v-if="phaseTag(item)">{{ phaseTag(item) }}</WPhaseTag>
        </RouterLink>
      </div>
    </nav>

    <div class="mt-2 border-t border-line pt-3">
      <RouterLink
        v-if="session.user?.isPlatformAdmin"
        :to="{ name: 'platform-overview' }"
        class="mb-2 flex items-center gap-[11px] rounded-[10px] px-2.5 py-2 text-[14px] font-semibold text-violet hover:bg-violet-soft"
        @click="emit('navigate')"
      >
        <ShieldCheck class="size-[18px]" aria-hidden="true" />{{ t('platform.nav.openConsole') }}
      </RouterLink>
      <RouterLink
        :to="{ name: 'profile' }"
        class="flex items-center gap-2.5 rounded-[10px] px-1 py-1 hover:bg-surface-2"
        :title="t('shell.profile')"
        @click="emit('navigate')"
      >
        <WAvatar :name="session.user?.fullName ?? ''" />
        <span class="min-w-0 flex-1">
          <span class="block truncate text-[13.5px] font-bold">{{ session.user?.fullName }}</span>
          <span class="block truncate text-[12px] text-muted">{{
            session.currentOrganization?.roleLabel
          }}</span>
        </span>
        <UserRound class="size-4 shrink-0 text-muted" aria-hidden="true" />
        <span class="sr-only">{{ t('shell.profile') }}</span>
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

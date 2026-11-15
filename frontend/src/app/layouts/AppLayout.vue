<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import {
  Compass,
  FileText,
  LayoutGrid,
  LogOut,
  Menu,
  Repeat,
  Search,
  SunMoon,
  Users,
} from '@lucide/vue'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { mobileTabItems, type NavItem, visibleNavItems } from '@/app/navigation'
import { useTour } from '@/app/tour'
import { searchApi } from '@/api/search'
import { useToast } from '@/composables/useToast'
import { useDialog } from '@/design/components/useDialog'
import { type CommandItem, WCommandPalette } from '@/design'
import { usePreferencesStore } from '@/stores/preferences'
import { useSessionStore } from '@/stores/session'

import SidebarContent from './SidebarContent.vue'
import ThemeToggle from './ThemeToggle.vue'
import AlertCenter from '@/modules/alerts/components/AlertCenter.vue'
import GuidedTour from '@/components/GuidedTour.vue'
import { useOrgTimezone } from '@/composables/useOrgTimezone'

/** Application shell (complement §5): sidebar, top bar, mobile drawer and tab bar, Ctrl+K. */
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const preferences = usePreferencesStore()
const toast = useToast()
const tour = useTour()

const menuOpen = ref(false)
const paletteOpen = ref(false)
const drawer = ref<HTMLElement | null>(null)
const { onKeydown: onDrawerKeydown } = useDialog(menuOpen, drawer, () => (menuOpen.value = false))

const items = computed(() => visibleNavItems(session.role, session.weddingsEnabled))
const mobileTabs = computed(() => mobileTabItems(session.role, session.weddingsEnabled))
const isActive = (item: NavItem) => route.name === item.routeName || route.meta.navKey === item.key

// Changing page closes the drawer (scrolling back to the top is done by the router).
watch(
  () => route.path,
  () => (menuOpen.value = false),
)

// --- Ctrl+K: pages and actions locally, clients and quotes from the server (§7.10) ---
const query = ref('')
const debounced = ref('')
let debounceTimer: ReturnType<typeof setTimeout> | undefined
watch(query, (value) => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => (debounced.value = value.trim()), 200)
})
const search = useQuery({
  queryKey: computed(() => ['search', session.currentOrganization?.slug, debounced.value]),
  queryFn: ({ signal }) => searchApi.search(debounced.value, signal),
  enabled: computed(() => paletteOpen.value && debounced.value.length >= 2),
  staleTime: 30_000,
})

const GROUP_ORDER = computed(() => [
  t('palette.groupPages'),
  t('palette.groupClients'),
  t('palette.groupQuotes'),
  t('palette.groupActions'),
])

const commands = computed<CommandItem[]>(() => [
  ...items.value.map((item) => ({
    id: `page-${item.key}`,
    label: t(`nav.${item.label}`),
    group: t('palette.groupPages'),
    icon: item.icon,
    run: () => void router.push({ name: item.routeName }),
  })),
  {
    id: 'action-tour',
    label: t('tour.replay'),
    group: t('palette.groupActions'),
    icon: Compass,
    keywords: 'visite guidee aide presentation tutoriel',
    run: () => tour.start(),
  },
  {
    id: 'action-theme',
    label: t('theme.toggle'),
    group: t('palette.groupActions'),
    icon: SunMoon,
    keywords: 'sombre clair dark light',
    run: () => preferences.toggleTheme(),
  },
  ...session.organizations
    .filter((org) => org.slug !== session.currentOrganization?.slug)
    .map((org) => ({
      id: `org-${org.slug}`,
      label: `${t('shell.switchOrganization')} : ${org.name}`,
      group: t('palette.groupActions'),
      icon: Repeat,
      run: () => {
        session.selectOrganization(org.slug)
        toast.info(t('shell.switched', { name: org.name }))
      },
    })),
  {
    id: 'action-logout',
    label: t('shell.logout'),
    group: t('palette.groupActions'),
    icon: LogOut,
    keywords: 'deconnexion quitter',
    run: () => void logout(),
  },
])

const remoteCommands = computed<CommandItem[]>(() => {
  const data = debounced.value.length >= 2 ? search.data.value : undefined
  if (!data) return []
  return [
    ...data.clients.map((client) => ({
      id: `client-${client.id}`,
      label: client.name,
      hint: client.company || undefined,
      group: t('palette.groupClients'),
      icon: Users,
      run: () => void router.push({ name: 'clients', query: { client: client.id } }),
    })),
    ...data.quotes.map((quote) => ({
      id: `quote-${quote.id}`,
      label: quote.number || t('quotes.statuses.draft'),
      hint: quote.clientName,
      group: t('palette.groupQuotes'),
      icon: FileText,
      run: () => void router.push({ name: 'quote-edit', params: { id: quote.id } }),
    })),
  ]
})

async function logout(): Promise<void> {
  await session.logout()
  toast.info(t('shell.loggedOut'))
  await router.push({ name: 'login' })
}

function onShortcut(event: KeyboardEvent): void {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    paletteOpen.value = !paletteOpen.value
  }
}
onMounted(() => window.addEventListener('keydown', onShortcut))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onShortcut)
  clearTimeout(debounceTimer)
})

// Dates everywhere in the agency's time zone (set once the organization is loaded).
useOrgTimezone()
</script>

<template>
  <div class="min-h-dvh nav:grid nav:grid-cols-[var(--sidebar)_minmax(0,1fr)]">
    <!-- Desktop sidebar -->
    <aside class="sticky top-0 hidden h-dvh border-r border-line bg-surface nav:block">
      <SidebarContent @logout="logout" />
    </aside>

    <div class="flex min-w-0 flex-col">
      <!-- Top bar -->
      <header
        class="sticky top-0 z-20 flex items-center gap-2.5 border-b border-line bg-[color-mix(in_srgb,var(--bg)_86%,transparent)] px-[clamp(16px,3vw,32px)] pt-[calc(12px+env(safe-area-inset-top,0px))] pb-3 backdrop-blur-[10px]"
      >
        <button
          type="button"
          class="inline-flex size-10 shrink-0 items-center justify-center rounded-[10px] border border-line-2 bg-surface text-ink-2 hover:bg-surface-2 nav:hidden"
          :aria-label="t('nav.openMenu')"
          :aria-expanded="menuOpen"
          @click="menuOpen = true"
        >
          <Menu class="size-[18px]" aria-hidden="true" />
        </button>
        <button
          type="button"
          data-tour="search"
          class="flex h-10 min-w-0 flex-1 items-center gap-2.5 rounded-[10px] border border-line-2 bg-surface px-3 text-left text-muted hover:bg-surface-2 nav:max-w-[420px]"
          aria-keyshortcuts="Control+K"
          @click="paletteOpen = true"
        >
          <Search class="size-[18px] shrink-0" aria-hidden="true" />
          <span class="truncate">{{ t('shell.search') }}</span>
          <kbd
            class="ml-auto hidden shrink-0 rounded-[6px] border border-line-2 px-1.5 font-sans text-[12px] font-semibold nav:inline"
          >
            {{ t('shell.searchShortcut') }}
          </kbd>
        </button>
        <div class="ml-auto flex shrink-0 items-center gap-2">
          <ThemeToggle />
          <span data-tour="alerts" class="inline-flex"><AlertCenter /></span>
        </div>
      </header>

      <main class="w-full flex-1 px-[clamp(16px,2.5vw,40px)] pt-[26px] pb-[110px] nav:pb-12">
        <slot />
      </main>
    </div>

    <!-- Mobile: bottom tab bar (Accueil, Réservations, Stock, Finances, Plus; clients and quotes
         stand in while a module is not built) -->
    <nav
      class="fixed inset-x-0 bottom-0 z-20 grid auto-cols-fr grid-flow-col border-t border-line bg-[color-mix(in_srgb,var(--surface)_92%,transparent)] pb-[env(safe-area-inset-bottom,0px)] backdrop-blur-[10px] nav:hidden"
      :aria-label="t('nav.tabsLabel')"
    >
      <RouterLink
        v-for="item in mobileTabs"
        :key="item.key"
        :to="{ name: item.routeName }"
        :data-tour="item.key"
        class="flex flex-col items-center gap-1 pt-2 pb-1.5 text-[11px] font-bold"
        :class="isActive(item) ? 'text-violet' : 'text-muted'"
        :aria-current="isActive(item) ? 'page' : undefined"
      >
        <component :is="item.icon" class="size-[22px]" aria-hidden="true" />
        {{ t(`nav.tabs.${item.key}`) }}
      </RouterLink>
      <button
        type="button"
        class="flex flex-col items-center gap-1 pt-2 pb-1.5 text-[11px] font-bold"
        :class="menuOpen ? 'text-violet' : 'text-muted'"
        :aria-expanded="menuOpen"
        @click="menuOpen = true"
      >
        <LayoutGrid class="size-[22px]" aria-hidden="true" />
        {{ t('nav.more') }}
      </button>
    </nav>

    <!-- Mobile: the sidebar in a 282px drawer from the left -->
    <Teleport to="body">
      <Transition
        enter-from-class="opacity-0"
        leave-to-class="opacity-0"
        enter-active-class="transition-opacity duration-200"
        leave-active-class="transition-opacity duration-200"
      >
        <div
          v-if="menuOpen"
          class="fixed inset-0 z-50 bg-[rgba(13,12,32,.45)] nav:hidden"
          @mousedown.self="menuOpen = false"
        >
          <aside
            ref="drawer"
            role="dialog"
            aria-modal="true"
            :aria-label="t('nav.menu')"
            tabindex="-1"
            class="absolute inset-y-0 left-0 w-[282px] max-w-[85vw] bg-surface pt-[env(safe-area-inset-top,0px)] pb-[env(safe-area-inset-bottom,0px)] shadow-wd-lg"
            @keydown="onDrawerKeydown"
          >
            <SidebarContent @navigate="menuOpen = false" @logout="logout" />
          </aside>
        </div>
      </Transition>
    </Teleport>

    <WCommandPalette
      v-model:open="paletteOpen"
      v-model:query="query"
      :items="commands"
      :remote-items="remoteCommands"
      :loading="search.isFetching.value"
      :group-order="GROUP_ORDER"
    />
    <GuidedTour />
  </div>
</template>

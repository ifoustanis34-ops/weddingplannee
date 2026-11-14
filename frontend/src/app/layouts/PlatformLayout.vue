<script setup lang="ts">
import { Menu } from '@lucide/vue'
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { useToast } from '@/composables/useToast'
import { useDialog } from '@/design/components/useDialog'
import { useSessionStore } from '@/stores/session'

import PlatformSidebar from './PlatformSidebar.vue'
import ThemeToggle from './ThemeToggle.vue'

/** Shell of the platform console (super-admin): its own menu, never an agency's. */
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const toast = useToast()

const menuOpen = ref(false)
const drawer = ref<HTMLElement | null>(null)
const { onKeydown } = useDialog(menuOpen, drawer, () => (menuOpen.value = false))
watch(
  () => route.path,
  () => (menuOpen.value = false),
)

async function logout(): Promise<void> {
  await session.logout()
  toast.info(t('shell.loggedOut'))
  await router.push({ name: 'login' })
}
</script>

<template>
  <div class="min-h-dvh nav:grid nav:grid-cols-[var(--sidebar)_minmax(0,1fr)]">
    <aside class="sticky top-0 hidden h-dvh border-r border-line bg-surface nav:block">
      <PlatformSidebar @logout="logout" />
    </aside>

    <div class="flex min-w-0 flex-col">
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
        <p class="truncate font-semibold text-ink-2">{{ t('platform.name') }}</p>
        <div class="ml-auto"><ThemeToggle /></div>
      </header>
      <main class="w-full flex-1 px-[clamp(16px,2.5vw,40px)] pt-[26px] pb-12">
        <slot />
      </main>
    </div>

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
            :aria-label="t('platform.nav.label')"
            tabindex="-1"
            class="absolute inset-y-0 left-0 w-[282px] max-w-[85vw] bg-surface pt-[env(safe-area-inset-top,0px)] pb-[env(safe-area-inset-bottom,0px)] shadow-wd-lg"
            @keydown="onKeydown"
          >
            <PlatformSidebar @navigate="menuOpen = false" @logout="logout" />
          </aside>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

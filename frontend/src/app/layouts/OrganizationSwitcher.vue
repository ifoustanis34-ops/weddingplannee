<script setup lang="ts">
import { Check, ChevronsUpDown } from '@lucide/vue'
import { computed, onBeforeUnmount, ref, useId } from 'vue'
import { useI18n } from 'vue-i18n'

import { visibleNavItems } from '@/app/navigation'
import { useToast } from '@/composables/useToast'
import { WAvatar } from '@/design'
import { useSessionStore } from '@/stores/session'

/**
 * Company block of the sidebar (complement §5): avatar, name and `slug.wedivo.app`.
 * With several spaces it opens the space switcher (CLAUDE.md §5.8); otherwise it leads to
 * Paramètres › Entreprise once that module exists.
 */
const { t } = useI18n()
const session = useSessionStore()
const toast = useToast()
const open = ref(false)
const root = ref<HTMLElement | null>(null)
const id = useId()

const current = computed(() => session.currentOrganization)
const canSwitch = computed(() => session.organizations.length > 1)
const settingsReady = computed(() =>
  visibleNavItems(session.role, session.weddingsEnabled).some((item) => item.key === 'settings'),
)

function choose(slug: string, name: string): void {
  open.value = false
  if (slug === current.value?.slug) return
  session.selectOrganization(slug)
  toast.info(t('shell.switched', { name }))
}

function onDocumentClick(event: MouseEvent): void {
  if (open.value && root.value && !root.value.contains(event.target as Node)) open.value = false
}
document.addEventListener('mousedown', onDocumentClick)
onBeforeUnmount(() => document.removeEventListener('mousedown', onDocumentClick))

const blockClass =
  'flex w-full items-center gap-2.5 rounded-wd bg-surface-2 p-2.5 text-left transition-colors'
</script>

<template>
  <div v-if="current" ref="root" class="relative" @keydown.escape="open = false">
    <component
      :is="canSwitch ? 'button' : settingsReady ? 'RouterLink' : 'div'"
      :type="canSwitch ? 'button' : undefined"
      :to="!canSwitch && settingsReady ? { name: 'settings' } : undefined"
      :class="[blockClass, (canSwitch || settingsReady) && 'hover:bg-surface-3']"
      :aria-expanded="canSwitch ? open : undefined"
      :aria-controls="canSwitch ? `${id}-list` : undefined"
      @click="canSwitch && (open = !open)"
    >
      <WAvatar :name="current.name" kind="organization" />
      <span class="min-w-0 flex-1">
        <span class="block truncate text-[13.5px] font-bold">{{ current.name }}</span>
        <span class="block truncate text-[12px] text-muted">{{
          t('shell.address', { slug: current.slug })
        }}</span>
      </span>
      <ChevronsUpDown v-if="canSwitch" class="size-4 shrink-0 text-muted" aria-hidden="true" />
      <span v-if="canSwitch" class="sr-only">{{ t('shell.switchOrganization') }}</span>
    </component>
    <ul
      v-if="open"
      :id="`${id}-list`"
      class="absolute inset-x-0 top-full z-30 mt-1 rounded-wd border border-line bg-surface p-1 shadow-wd-lg"
    >
      <li v-for="org in session.organizations" :key="org.slug">
        <button
          type="button"
          class="flex w-full items-center gap-2 rounded-wd-sm px-3 py-2 text-left hover:bg-surface-2"
          :aria-current="org.slug === current.slug || undefined"
          @click="choose(org.slug, org.name)"
        >
          <span class="min-w-0 flex-1">
            <span class="block truncate font-semibold">{{ org.name }}</span>
            <span class="block truncate text-[12px] text-muted"
              >{{ t('shell.address', { slug: org.slug }) }} · {{ org.roleLabel }}</span
            >
          </span>
          <Check v-if="org.slug === current.slug" class="size-4 text-violet" aria-hidden="true" />
        </button>
      </li>
    </ul>
  </div>
</template>

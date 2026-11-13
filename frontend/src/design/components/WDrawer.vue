<script setup lang="ts">
import { X } from '@lucide/vue'
import { ref, useId } from 'vue'
import { useI18n } from 'vue-i18n'

import { useDialog } from './useDialog'

withDefaults(
  defineProps<{ title: string; subtitle?: string; side?: 'right' | 'left'; wide?: boolean }>(),
  { side: 'right', wide: false },
)
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const id = useId()
const panel = ref<HTMLElement | null>(null)
const { onKeydown } = useDialog(open, panel, () => (open.value = false))
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-from-class="opacity-0"
      leave-to-class="opacity-0"
      enter-active-class="transition-opacity duration-200"
      leave-active-class="transition-opacity duration-200"
    >
      <div
        v-if="open"
        class="fixed inset-0 z-50 bg-scrim backdrop-blur-[2px]"
        @mousedown.self="open = false"
      >
        <aside
          ref="panel"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="`${id}-title`"
          tabindex="-1"
          class="absolute inset-y-0 flex flex-col bg-surface shadow-wd-lg"
          :class="[
            wide ? 'w-[min(900px,100%)]' : 'w-[min(500px,100%)]',
            side === 'right'
              ? 'right-0 motion-safe:animate-[wd-drawer-in_.22s_ease-out]'
              : 'left-0',
          ]"
          style="
            padding-top: env(safe-area-inset-top, 0);
            padding-bottom: env(safe-area-inset-bottom, 0);
          "
          @keydown="onKeydown"
        >
          <header class="flex items-start gap-3 border-b border-line p-5">
            <div class="min-w-0 flex-1">
              <!-- Custom heading (avatar, badges…): it must put `titleId` on its title. -->
              <slot name="heading" :title-id="`${id}-title`">
                <h2 :id="`${id}-title`" class="truncate text-[17px] font-semibold">{{ title }}</h2>
                <p v-if="subtitle" class="text-[13px] text-muted">{{ subtitle }}</p>
              </slot>
            </div>
            <button
              type="button"
              class="rounded-wd-sm p-1.5 text-muted hover:bg-surface-2 hover:text-ink"
              :aria-label="t('common.close')"
              @click="open = false"
            >
              <X class="size-5" aria-hidden="true" />
            </button>
          </header>
          <div class="flex flex-1 flex-col gap-5 overflow-y-auto p-5"><slot /></div>
          <footer v-if="$slots.footer" class="flex flex-wrap gap-2 border-t border-line px-5 py-4">
            <slot name="footer" />
          </footer>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>

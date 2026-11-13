<script setup lang="ts">
import { X } from '@lucide/vue'
import { ref, useId } from 'vue'
import { useI18n } from 'vue-i18n'

import { useDialog } from './useDialog'

withDefaults(defineProps<{ title: string; description?: string; size?: 'sm' | 'md' | 'lg' }>(), {
  size: 'md',
})
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
      enter-active-class="transition-opacity duration-150"
      leave-active-class="transition-opacity duration-150"
    >
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-center justify-center bg-scrim p-3 backdrop-blur-[2px]"
        @mousedown.self="open = false"
      >
        <div
          ref="panel"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="`${id}-title`"
          :aria-describedby="description ? `${id}-desc` : undefined"
          tabindex="-1"
          class="flex max-h-[92dvh] w-full flex-col rounded-[20px] bg-surface shadow-wd-lg motion-safe:animate-[wd-modal-in_.18s_ease-out]"
          :class="{ sm: 'max-w-[440px]', md: 'max-w-[560px]', lg: 'max-w-[760px]' }[size]"
          style="padding-bottom: env(safe-area-inset-bottom, 0)"
          @keydown="onKeydown"
        >
          <header class="flex items-start gap-3 border-b border-line px-5 py-4">
            <div class="flex-1">
              <h2 :id="`${id}-title`" class="text-[17px] font-semibold">{{ title }}</h2>
              <p v-if="description" :id="`${id}-desc`" class="text-[13px] text-muted">
                {{ description }}
              </p>
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
          <div class="overflow-y-auto px-5 py-5"><slot /></div>
          <footer
            v-if="$slots.footer"
            class="flex flex-wrap justify-end gap-2 border-t border-line px-5 py-4"
          >
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

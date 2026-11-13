<script setup lang="ts">
import { CircleAlert, CircleCheck, Info, X } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import { useToast } from '@/composables/useToast'

const { t } = useI18n()
const { toasts, dismiss } = useToast()
const ICONS = { success: CircleCheck, error: CircleAlert, info: Info }
const TONES = {
  success: 'text-[var(--toast-success)]',
  error: 'text-[var(--toast-alert)]',
  info: 'text-hero-muted',
}
</script>

<template>
  <div
    class="pointer-events-none fixed inset-x-0 bottom-[calc(84px+env(safe-area-inset-bottom,0px))] z-[60] flex flex-col items-stretch gap-2 px-4 nav:inset-x-auto nav:right-6 nav:bottom-6 nav:w-[380px] nav:px-0"
    aria-live="polite"
    aria-atomic="false"
  >
    <TransitionGroup
      enter-from-class="translate-y-2 opacity-0"
      leave-to-class="opacity-0"
      enter-active-class="transition duration-200"
      leave-active-class="transition duration-150"
    >
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :role="toast.tone === 'error' ? 'alert' : 'status'"
        class="pointer-events-auto flex w-full items-start gap-3 rounded-wd bg-hero px-4 py-3 text-[14px] font-semibold text-hero-ink shadow-wd-lg"
      >
        <component
          :is="ICONS[toast.tone]"
          class="mt-0.5 size-5 shrink-0"
          :class="TONES[toast.tone]"
          aria-hidden="true"
        />
        <p class="flex-1">{{ toast.message }}</p>
        <button
          type="button"
          class="rounded p-0.5 text-hero-muted hover:text-hero-ink"
          :aria-label="t('common.close')"
          @click="dismiss(toast.id)"
        >
          <X class="size-4" aria-hidden="true" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

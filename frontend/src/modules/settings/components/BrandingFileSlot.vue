<script setup lang="ts">
import { ImageUp, Trash2 } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import { WButton } from '@/design'

/** One identity file (logo, logo on dark, signature, stamp): preview, replace, remove. */
defineProps<{
  label: string
  hint: string
  url: string | null
  busy?: boolean
  /** Preview on the dark colour of the documents (logo meant for dark bands). */
  dark?: boolean
}>()
const emit = defineEmits<{ upload: [file: File]; remove: [] }>()
const { t } = useI18n()

function onChange(event: Event): void {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) emit('upload', file)
  input.value = ''
}
</script>

<template>
  <div class="flex min-w-0 flex-col gap-2.5 rounded-wd border border-line p-3.5">
    <p class="font-bold">{{ label }}</p>
    <div
      class="grid h-24 place-items-center overflow-hidden rounded-[10px] border border-line"
      :class="dark ? 'bg-hero' : 'bg-white'"
    >
      <img v-if="url" :src="url" alt="" class="max-h-20 max-w-[85%] object-contain" />
      <span v-else class="text-[12.5px]" :class="dark ? 'text-hero-muted' : 'text-muted'">{{
        t('settings.branding.files.empty')
      }}</span>
    </div>
    <p class="text-[12.5px] text-muted">{{ hint }}</p>
    <div class="mt-auto flex flex-wrap gap-2">
      <label
        class="inline-flex h-8 cursor-pointer items-center gap-2 rounded-[8px] border border-line-2 bg-surface px-[11px] text-[13px] font-bold hover:bg-surface-2 has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-violet"
        :class="busy && 'pointer-events-none opacity-60'"
      >
        <ImageUp class="size-[15px]" aria-hidden="true" />
        {{ url ? t('settings.branding.files.replace') : t('settings.branding.files.add') }}
        <span class="sr-only">: {{ label }}</span>
        <input
          type="file"
          accept="image/png,image/jpeg,image/webp,image/svg+xml"
          class="sr-only"
          :disabled="busy"
          @change="onChange"
        />
      </label>
      <WButton
        v-if="url"
        variant="ghost"
        size="sm"
        :disabled="busy"
        :aria-label="`${t('settings.branding.files.remove')} : ${label}`"
        @click="emit('remove')"
      >
        <Trash2 class="size-[15px]" aria-hidden="true" />{{ t('settings.branding.files.remove') }}
      </WButton>
    </div>
  </div>
</template>

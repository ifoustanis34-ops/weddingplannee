<script setup lang="ts">
import { Printer } from '@lucide/vue'
import { onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { useToast } from '@/composables/useToast'
import { WButton, WModal } from '@/design'

import { BADGE_DESIGNS, type BadgeDesign, staffApi } from '../api'

/** Choose the badge design on real previews (the first person, or the one printed), then print. */
const props = defineProps<{ staffIds?: string[]; name?: string }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const toast = useToast()
const design = ref<BadgeDesign>('carte')
const previews = ref<Partial<Record<BadgeDesign, string>>>({})
const printing = ref(false)

function revoke(): void {
  for (const url of Object.values(previews.value)) if (url) URL.revokeObjectURL(url)
  previews.value = {}
}
watch(open, async (value) => {
  if (!value) return
  revoke()
  for (const key of BADGE_DESIGNS) {
    try {
      previews.value = {
        ...previews.value,
        [key]: await staffApi.badgePreview(key, props.staffIds?.[0]),
      }
    } catch {
      // the card stays without image; printing still works
    }
  }
})
onBeforeUnmount(revoke)

async function print(): Promise<void> {
  printing.value = true
  try {
    await staffApi.badges(props.staffIds ?? [], design.value)
    open.value = false
  } catch (error) {
    toast.error(toApiError(error).message)
  } finally {
    printing.value = false
  }
}
</script>

<template>
  <WModal
    v-model:open="open"
    :title="name ? t('staff.badges.titleOne', { name }) : t('staff.badges.titleAll')"
    :description="t('staff.badges.hint')"
    size="lg"
  >
    <div class="grid gap-3 sm:grid-cols-2" role="radiogroup" :aria-label="t('staff.badges.design')">
      <!-- The employee card (front and back) spans the whole row. -->
      <button
        v-for="key in BADGE_DESIGNS"
        :key="key"
        type="button"
        role="radio"
        :aria-checked="design === key"
        class="flex flex-col gap-2 rounded-wd-lg border-2 p-3 text-left transition-colors"
        :class="[
          design === key ? 'border-violet bg-violet-soft' : 'border-line hover:border-line-2',
          key === 'carte' && 'sm:col-span-2',
        ]"
        @click="design = key"
      >
        <span
          class="flex items-center justify-center rounded-wd bg-surface-2 p-2"
          :class="key === 'carte' ? 'h-[260px]' : 'h-[170px]'"
        >
          <img
            v-if="previews[key]"
            :src="previews[key]"
            :alt="t('staff.badges.previewOf', { design: t(`staff.badges.designs.${key}`) })"
            class="max-h-full max-w-full rounded-[6px] shadow-wd"
          />
          <span v-else class="skeleton h-full w-full rounded-[6px]" />
        </span>
        <span class="font-bold">{{ t(`staff.badges.designs.${key}`) }}</span>
        <span class="text-[12.5px] text-muted">{{ t(`staff.badges.descriptions.${key}`) }}</span>
      </button>
    </div>
    <template #footer>
      <WButton variant="secondary" @click="open = false">{{ t('common.cancel') }}</WButton>
      <WButton :loading="printing" @click="print">
        <Printer class="size-[18px]" aria-hidden="true" />{{ t('staff.badges.print') }}
      </WButton>
    </template>
  </WModal>
</template>

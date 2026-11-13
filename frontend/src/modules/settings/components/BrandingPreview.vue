<script setup lang="ts">
import { computed } from 'vue'

import type { Branding } from '@/api/branding'

/**
 * Header of a document as the client will see it: always on white paper, whatever the theme.
 * The real templates arrive in R3; this preview checks the logo, colours and contact details.
 */
const props = defineProps<{
  branding: Pick<
    Branding,
    | 'tradeName'
    | 'activity'
    | 'slogan'
    | 'address'
    | 'phones'
    | 'email'
    | 'website'
    | 'primaryColor'
    | 'secondaryColor'
    | 'monogramColor'
    | 'monogram'
  >
  logo: string | null
}>()

const primary = computed(() => props.branding.primaryColor || '#17153B')
const accent = computed(() => props.branding.secondaryColor || '#B97A0E')
const contacts = computed(() =>
  [props.branding.phones.filter(Boolean).join(' · '), props.branding.email, props.branding.website]
    .filter(Boolean)
    .join(' · '),
)
</script>

<template>
  <div
    class="overflow-hidden rounded-wd border border-[#E5E2F0] bg-white text-[#17153B] [color-scheme:light]"
  >
    <div class="h-1.5" :style="{ background: primary }" />
    <div class="flex flex-wrap items-center gap-4 px-5 py-4">
      <img v-if="logo" :src="logo" alt="" class="h-14 max-w-[160px] object-contain" />
      <div
        v-else
        class="grid size-14 shrink-0 place-items-center rounded-full border-2 font-display text-[20px] font-semibold"
        :style="{
          borderColor: branding.monogramColor || accent,
          color: branding.monogramColor || accent,
        }"
      >
        {{ branding.monogram }}
      </div>
      <div class="min-w-0 flex-1">
        <p class="font-display text-[19px] font-semibold" :style="{ color: primary }">
          {{ branding.tradeName }}
        </p>
        <p class="text-[12.5px] tracking-[.08em] text-[#4A4769]">{{ branding.activity }}</p>
        <p v-if="branding.slogan" class="text-[13px] italic" :style="{ color: accent }">
          {{ branding.slogan }}
        </p>
      </div>
    </div>
    <div
      v-if="contacts || branding.address"
      class="border-t border-[#E5E2F0] px-5 py-2.5 text-[12px] text-[#4A4769]"
    >
      <p v-if="branding.address">{{ branding.address }}</p>
      <p v-if="contacts">{{ contacts }}</p>
    </div>
  </div>
</template>

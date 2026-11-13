<script setup lang="ts">
import { BadgeCheck, CircleX } from '@lucide/vue'
import { useQuery } from '@tanstack/vue-query'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import { api } from '@/api/client'

/**
 * What a badge QR opens (feedback 13/11/2026): anyone checks that the person really belongs to
 * the agency. « Badge valide » while they are on the team; nothing private is shown.
 */
interface PublicBadge {
  valid: boolean
  name: string
  position: string
  department: string
  number: string
  kind: string
  agency: string
  logo: string | null
  photoUrl: string | null
}
const { t } = useI18n()
const route = useRoute()
const token = computed(() => String(route.params.token))
const badge = useQuery({
  queryKey: computed(() => ['public-badge', token.value]),
  queryFn: () => api.get<PublicBadge>(`/public/badges/${token.value}`).then((r) => r.data),
  retry: false,
})
</script>

<template>
  <main class="flex min-h-dvh items-center justify-center bg-bg px-4 py-10">
    <div
      class="w-full max-w-[380px] rounded-wd-lg border border-line bg-surface p-6 text-center shadow-wd"
    >
      <div v-if="badge.isPending.value" class="skeleton mx-auto h-64 w-full" />
      <template v-else-if="badge.isError.value || !badge.data.value">
        <CircleX class="mx-auto size-12 text-red" aria-hidden="true" />
        <h1 class="mt-3 text-[20px]">{{ t('staff.publicBadge.unknown') }}</h1>
        <p class="mt-2 text-muted">{{ t('staff.publicBadge.unknownText') }}</p>
      </template>
      <template v-else>
        <img
          v-if="badge.data.value.logo"
          :src="badge.data.value.logo"
          :alt="badge.data.value.agency"
          class="mx-auto h-12 object-contain"
        />
        <p v-else class="font-bold">{{ badge.data.value.agency }}</p>
        <img
          v-if="badge.data.value.photoUrl"
          :src="badge.data.value.photoUrl"
          :alt="badge.data.value.name"
          class="mx-auto mt-5 size-28 rounded-wd border-2 border-gold-bright object-cover"
        />
        <h1 class="mt-4 text-[22px]">{{ badge.data.value.name }}</h1>
        <p class="text-ink-2">{{ badge.data.value.position }}</p>
        <p class="mt-1 text-[13px] text-muted">
          {{ [badge.data.value.department, badge.data.value.number].filter(Boolean).join(' · ') }}
        </p>
        <p
          class="mt-5 flex items-center justify-center gap-2 rounded-wd px-3 py-3 font-bold"
          :class="badge.data.value.valid ? 'bg-green-soft text-green' : 'bg-red-soft text-red'"
          role="status"
        >
          <component
            :is="badge.data.value.valid ? BadgeCheck : CircleX"
            class="size-5"
            aria-hidden="true"
          />
          {{
            badge.data.value.valid
              ? t('staff.publicBadge.valid', { agency: badge.data.value.agency })
              : t('staff.publicBadge.invalid')
          }}
        </p>
      </template>
    </div>
  </main>
</template>

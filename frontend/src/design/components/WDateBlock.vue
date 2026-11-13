<script setup lang="ts">
import { computed } from 'vue'

/** Date block (complement §4): day in Sora, abbreviated month (« oct. ») or weekday below. */
const props = withDefaults(defineProps<{ date: string; weekday?: boolean }>(), { weekday: false })

// Calendar dates (YYYY-MM-DD) carry no time zone: read them in UTC so the day never shifts.
const parsed = computed(() => new Date(`${props.date.slice(0, 10)}T00:00:00Z`))
const day = computed(() => parsed.value.getUTCDate())
const caption = computed(() =>
  new Intl.DateTimeFormat('fr-FR', {
    timeZone: 'UTC',
    ...(props.weekday ? { weekday: 'short' } : { month: 'short' }),
  }).format(parsed.value),
)
const full = computed(() =>
  new Intl.DateTimeFormat('fr-FR', { timeZone: 'UTC', dateStyle: 'long' }).format(parsed.value),
)
</script>

<template>
  <time
    :datetime="date.slice(0, 10)"
    class="flex w-[46px] shrink-0 flex-col items-center justify-center rounded-[10px] bg-surface-2 py-1.5"
    :title="full"
  >
    <span class="num text-[17px] leading-tight font-semibold">{{ day }}</span>
    <span class="text-[11px] leading-tight font-bold text-muted">{{ caption }}</span>
  </time>
</template>

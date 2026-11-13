<script setup lang="ts">
import logoMark from '@/assets/logo-mark.png'

/** Logotype (complement §3): mark 40px + « Wedivo » in Sora 700 with a gold dot on a dotless i. */
withDefaults(defineProps<{ inverse?: boolean; markOnly?: boolean }>(), {
  inverse: false,
  markOnly: false,
})
</script>

<template>
  <span class="inline-flex items-center gap-2.5" :class="inverse ? 'text-hero-ink' : 'text-ink'">
    <img :src="logoMark" alt="" class="w-10 shrink-0" />
    <span
      v-if="!markOnly"
      class="font-display text-[22px] leading-none font-bold tracking-[-0.03em]"
    >
      <span class="sr-only">Wedivo</span>
      <span aria-hidden="true"
        >Wed<span class="relative inline-block"
          >ı<span
            class="absolute top-[0.04em] left-1/2 size-[0.24em] -translate-x-1/2 rounded-full bg-gold-bright" /></span
        >vo</span
      >
    </span>
  </span>
</template>

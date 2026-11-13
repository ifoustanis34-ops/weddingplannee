<script setup lang="ts">
/** Key figure tile (complement §4). `dark` uses the hero background. */
withDefaults(defineProps<{ label: string; value?: string; dark?: boolean }>(), { dark: false })
</script>

<template>
  <div
    class="rounded-wd-lg border px-[18px] py-4"
    :class="dark ? 'border-hero bg-hero text-hero-ink' : 'border-line bg-surface'"
  >
    <p class="text-[13px] font-semibold" :class="dark ? 'text-hero-muted' : 'text-muted'">
      {{ label }}
    </p>
    <p class="num mt-1 text-[21px] font-semibold tracking-[-0.02em]">
      <slot name="value">{{ value }}</slot>
    </p>
    <div
      v-if="$slots.default"
      class="mt-1 text-[12.5px]"
      :class="dark ? 'text-hero-muted' : 'text-muted'"
    >
      <slot />
    </div>
  </div>
</template>

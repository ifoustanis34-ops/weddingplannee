<script setup lang="ts">
withDefaults(defineProps<{ title?: string; subtitle?: string; padded?: boolean }>(), {
  padded: true,
})
</script>

<template>
  <section class="rounded-wd-lg border border-line bg-surface" :class="padded && 'p-5'">
    <header
      v-if="title || $slots.actions"
      class="mb-4 flex flex-wrap items-start gap-3"
      :class="!padded && 'px-5 pt-5'"
    >
      <div class="min-w-0 flex-1">
        <h2 class="text-[17px] font-semibold">{{ title }}</h2>
        <p v-if="subtitle" class="text-[13px] text-muted">{{ subtitle }}</p>
      </div>
      <slot name="actions" />
    </header>
    <slot />
  </section>
</template>

<script setup lang="ts" generic="Value extends string | number">
/** Filter chips (complement §4): one active at a time, active = ink background. */
defineProps<{ options: { value: Value; label: string }[]; label: string }>()
const model = defineModel<Value>({ required: true })
</script>

<template>
  <div class="flex flex-wrap gap-2" role="group" :aria-label="label">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      class="h-8 rounded-full border px-3 text-[13px] font-bold whitespace-nowrap transition-colors"
      :class="
        model === option.value
          ? 'border-ink bg-ink text-surface'
          : 'border-line-2 bg-surface text-ink-2 hover:bg-surface-2'
      "
      :aria-pressed="model === option.value"
      @click="model = option.value"
    >
      {{ option.label }}
    </button>
  </div>
</template>

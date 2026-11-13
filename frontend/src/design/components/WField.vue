<script setup lang="ts">
/** Label, hint and error wrapper shared by every form control. */
defineProps<{
  id: string
  label?: string
  hint?: string
  error?: string
  required?: boolean
  /** Keep the label for screen readers but do not display it (filters, compact rows). */
  hideLabel?: boolean
}>()
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <div v-if="label" class="flex items-baseline justify-between gap-3">
      <label :for="id" class="text-[13px] font-bold text-ink-2" :class="hideLabel && 'sr-only'">
        {{ label }}<span v-if="required" class="text-red" aria-hidden="true"> *</span>
      </label>
      <!-- Link next to the label, e.g. « Mot de passe oublié ? » -->
      <slot name="label-aside" />
    </div>
    <slot />
    <p v-if="error" :id="`${id}-error`" class="text-[13.5px] font-bold text-red">{{ error }}</p>
    <p v-else-if="hint" :id="`${id}-hint`" class="text-[12.5px] text-muted">{{ hint }}</p>
  </div>
</template>

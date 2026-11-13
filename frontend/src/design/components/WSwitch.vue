<script setup lang="ts">
import { useId } from 'vue'

const props = defineProps<{ label: string; description?: string; disabled?: boolean }>()
const model = defineModel<boolean>({ default: false })
const id = useId()

function toggle(): void {
  if (!props.disabled) model.value = !model.value
}
</script>

<template>
  <div class="flex items-start gap-3">
    <button
      :id="id"
      type="button"
      role="switch"
      :aria-checked="model"
      :aria-describedby="description ? `${id}-desc` : undefined"
      :disabled="disabled"
      class="relative mt-0.5 inline-flex h-6 w-[42px] shrink-0 items-center rounded-full transition-colors disabled:opacity-50"
      :class="model ? 'bg-green' : 'bg-line-2'"
      @click="toggle"
    >
      <span
        class="inline-block size-[18px] rounded-full bg-white shadow-[0_1px_3px_rgba(23,21,59,.25)] transition-transform"
        :class="model ? 'translate-x-[21px]' : 'translate-x-[3px]'"
      />
    </button>
    <div>
      <label :for="id" class="cursor-pointer font-semibold">{{ label }}</label>
      <p v-if="description" :id="`${id}-desc`" class="text-[13px] text-muted">
        {{ description }}
      </p>
    </div>
  </div>
</template>

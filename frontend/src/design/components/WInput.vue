<script setup lang="ts">
import { useId } from 'vue'

import { controlClasses, describedBy } from './fieldClasses'
import { useFieldAttrs } from './useFieldAttrs'
import WField from './WField.vue'

defineOptions({ inheritAttrs: false })

const props = defineProps<{
  label?: string
  hint?: string
  error?: string
  required?: boolean
  hideLabel?: boolean
  /** Grey suffix inside the same rounded frame: « .wedivo.pro », « % », « jours ». */
  addon?: string
  id?: string
}>()

const model = defineModel<string | number | null>()
const id = props.id ?? useId()
const { rootAttrs, controlAttrs } = useFieldAttrs()
</script>

<template>
  <WField
    v-bind="rootAttrs"
    :id="id"
    :label="label"
    :hint="hint"
    :error="error"
    :required="required"
    :hide-label="hideLabel"
  >
    <template v-if="$slots['label-aside']" #label-aside><slot name="label-aside" /></template>
    <div
      class="relative flex items-center"
      :class="
        addon && [
          'overflow-hidden rounded-[10px] border bg-surface focus-within:border-violet focus-within:shadow-[0_0_0_3px_var(--violet-soft)]',
          error ? 'border-red' : 'border-line-2',
        ]
      "
    >
      <span v-if="$slots.prefix" class="pointer-events-none absolute left-3 text-muted">
        <slot name="prefix" />
      </span>
      <input
        :id="id"
        v-model="model"
        v-bind="controlAttrs"
        :required="required"
        :aria-invalid="error ? 'true' : undefined"
        :aria-describedby="describedBy(id, error, hint)"
        :class="[
          controlClasses(Boolean(error)),
          'h-[42px]',
          addon && 'min-w-0 flex-1 rounded-none border-0 focus:shadow-none',
          $slots.prefix && 'pl-9',
          $slots.suffix && 'pr-10',
        ]"
      />
      <span v-if="$slots.suffix" class="absolute right-2 flex items-center text-muted">
        <slot name="suffix" />
      </span>
      <span
        v-if="addon"
        class="flex h-[42px] shrink-0 items-center border-l border-line-2 bg-surface-2 px-3 text-muted"
        >{{ addon }}</span
      >
    </div>
  </WField>
</template>

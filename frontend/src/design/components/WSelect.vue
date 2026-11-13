<script setup lang="ts">
import { ChevronDown } from '@lucide/vue'
import { useId } from 'vue'

import { controlClasses, describedBy } from './fieldClasses'
import { useFieldAttrs } from './useFieldAttrs'
import WField from './WField.vue'

defineOptions({ inheritAttrs: false })

export interface SelectOption {
  value: string | number
  label: string
  /** Shown but not selectable (e.g. « WhatsApp, connexion requise »). */
  disabled?: boolean
}

const props = defineProps<{
  options: SelectOption[]
  label?: string
  hint?: string
  error?: string
  required?: boolean
  hideLabel?: boolean
  placeholder?: string
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
    <div class="relative">
      <select
        :id="id"
        v-model="model"
        v-bind="controlAttrs"
        :required="required"
        :aria-invalid="error ? 'true' : undefined"
        :aria-describedby="describedBy(id, error, hint)"
        :class="[controlClasses(Boolean(error)), 'h-[42px] appearance-none pr-9']"
      >
        <option v-if="placeholder" :value="null" disabled>{{ placeholder }}</option>
        <option
          v-for="option in options"
          :key="option.value"
          :value="option.value"
          :disabled="option.disabled"
        >
          {{ option.label }}
        </option>
      </select>
      <ChevronDown
        class="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-muted"
        aria-hidden="true"
      />
    </div>
  </WField>
</template>

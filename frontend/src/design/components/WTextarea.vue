<script setup lang="ts">
import { useId } from 'vue'

import { controlClasses, describedBy } from './fieldClasses'
import { useFieldAttrs } from './useFieldAttrs'
import WField from './WField.vue'

defineOptions({ inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    label?: string
    hint?: string
    error?: string
    required?: boolean
    hideLabel?: boolean
    rows?: number
    id?: string
  }>(),
  { rows: 4 },
)

const model = defineModel<string | null>()
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
    <textarea
      :id="id"
      v-model="model"
      v-bind="controlAttrs"
      :rows="rows"
      :required="required"
      :aria-invalid="error ? 'true' : undefined"
      :aria-describedby="describedBy(id, error, hint)"
      :class="[controlClasses(Boolean(error)), 'min-h-[84px] py-2.5 leading-relaxed']"
    />
  </WField>
</template>

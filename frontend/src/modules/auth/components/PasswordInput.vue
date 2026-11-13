<script setup lang="ts">
import { Eye, EyeOff } from '@lucide/vue'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { WInput } from '@/design'

defineOptions({ inheritAttrs: false })
defineProps<{ label: string; error?: string; hint?: string; required?: boolean }>()
const model = defineModel<string>()
const visible = ref(false)
const { t } = useI18n()
</script>

<template>
  <WInput
    v-model="model"
    v-bind="$attrs"
    :type="visible ? 'text' : 'password'"
    :label="label"
    :error="error"
    :hint="hint"
    :required="required"
  >
    <template v-if="$slots['label-aside']" #label-aside><slot name="label-aside" /></template>
    <template #suffix>
      <button
        type="button"
        class="rounded p-1.5 hover:text-ink"
        :aria-label="visible ? t('common.hidePassword') : t('common.showPassword')"
        :aria-pressed="visible"
        @click="visible = !visible"
      >
        <EyeOff v-if="visible" class="size-4" aria-hidden="true" />
        <Eye v-else class="size-4" aria-hidden="true" />
      </button>
    </template>
  </WInput>
</template>

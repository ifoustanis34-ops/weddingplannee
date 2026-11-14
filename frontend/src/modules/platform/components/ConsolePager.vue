<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { WButton } from '@/design'

/** « Page 2 sur 7 » with previous / next (25 per page on the server). */
const props = withDefaults(defineProps<{ count: number; pageSize?: number }>(), { pageSize: 25 })
const page = defineModel<number>({ required: true })
const { t } = useI18n()
const pages = computed(() => Math.max(1, Math.ceil(props.count / props.pageSize)))
</script>

<template>
  <div class="flex flex-wrap items-center justify-between gap-3 pt-4 text-[13px] text-muted">
    <span>{{ t('platform.common.results', { count }, count) }}</span>
    <div v-if="pages > 1" class="flex items-center gap-2">
      <WButton size="sm" variant="secondary" :disabled="page <= 1" @click="page -= 1">{{
        t('platform.common.previous')
      }}</WButton>
      <span>{{ t('platform.common.pageOf', { page, pages }) }}</span>
      <WButton size="sm" variant="secondary" :disabled="page >= pages" @click="page += 1">{{
        t('platform.common.next')
      }}</WButton>
    </div>
  </div>
</template>

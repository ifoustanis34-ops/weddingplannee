<script setup lang="ts">
import { onMounted } from 'vue'

import { honeypot, prepareFormToken } from '@/api/formGuard'

/** Invisible trap for robots and early form token (anti-bot, `api/formGuard.ts`). */
onMounted(() => {
  honeypot.value = ''
  void prepareFormToken().catch(() => undefined)
})
</script>

<template>
  <div
    class="pointer-events-none absolute -left-[9999px] h-px w-px overflow-hidden"
    aria-hidden="true"
  >
    <label>
      Site web
      <input v-model="honeypot" type="text" name="website" tabindex="-1" autocomplete="off" />
    </label>
  </div>
</template>

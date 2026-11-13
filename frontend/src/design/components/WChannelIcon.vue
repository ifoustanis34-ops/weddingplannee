<script setup lang="ts">
import { Check, Mail, MessageCircle, Phone } from '@lucide/vue'
import { computed } from 'vue'

export type Channel = 'email' | 'call' | 'whatsapp' | 'task'

/** Channel icon (complement §4): 36px square, soft background of the channel colour. */
const props = defineProps<{ channel: Channel; label?: string }>()

const STYLES: Record<Channel, { icon: typeof Mail; classes: string }> = {
  email: { icon: Mail, classes: 'bg-violet-soft text-violet' },
  call: { icon: Phone, classes: 'bg-gold-soft text-gold' },
  whatsapp: { icon: MessageCircle, classes: 'bg-green-soft text-green' },
  task: { icon: Check, classes: 'bg-grey-soft text-muted' },
}
const style = computed(() => STYLES[props.channel])
</script>

<template>
  <span
    class="flex size-9 shrink-0 items-center justify-center rounded-[10px]"
    :class="style.classes"
    :role="label ? 'img' : undefined"
    :aria-label="label"
    :aria-hidden="label ? undefined : 'true'"
  >
    <component :is="style.icon" class="size-[18px]" aria-hidden="true" />
  </span>
</template>

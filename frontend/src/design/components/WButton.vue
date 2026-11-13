<script setup lang="ts">
import { LoaderCircle } from '@lucide/vue'
import { computed } from 'vue'
import { RouterLink, type RouteLocationRaw } from 'vue-router'

const props = withDefaults(
  defineProps<{
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
    /** `lg` (46px) for the main action of the sign-in and sign-up forms. */
    size?: 'lg' | 'md' | 'sm'
    type?: 'button' | 'submit' | 'reset'
    loading?: boolean
    disabled?: boolean
    block?: boolean
    /** Square icon-only button (40px, 32px in `sm`): give it an `aria-label`. */
    icon?: boolean
    to?: RouteLocationRaw
  }>(),
  { variant: 'primary', size: 'md', type: 'button' },
)

const classes = computed(() => [
  'inline-flex cursor-pointer items-center justify-center gap-2 border font-bold whitespace-nowrap transition-[filter,background-color,border-color,transform] active:translate-y-px disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50',
  {
    lg: ['h-[46px] rounded-[10px] text-[14.5px]', props.icon ? 'w-[46px] px-0' : 'px-5'],
    md: ['h-10 rounded-[10px] text-[14px]', props.icon ? 'w-10 px-0' : 'px-4'],
    sm: ['h-8 rounded-[8px] text-[13px]', props.icon ? 'w-8 px-0' : 'px-[11px]'],
  }[props.size],
  props.block && 'w-full',
  {
    primary: 'border-violet bg-violet text-violet-ink hover:brightness-[1.08]',
    // A visible outline and the brand color: it reads as a button, not as text (feedback 11/2026).
    secondary:
      'border-violet/45 bg-surface text-violet shadow-[0_1px_0_var(--line-2)] hover:border-violet hover:bg-violet-soft',
    ghost: 'border-transparent bg-transparent text-violet hover:bg-violet-soft',
    danger: 'border-red bg-red text-white hover:brightness-[1.08]',
  }[props.variant],
])
</script>

<template>
  <RouterLink v-if="to && !disabled" :to="to" :class="classes"><slot /></RouterLink>
  <button
    v-else
    :type="type"
    :class="classes"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
  >
    <LoaderCircle v-if="loading" class="size-4 animate-spin" aria-hidden="true" />
    <slot />
  </button>
</template>

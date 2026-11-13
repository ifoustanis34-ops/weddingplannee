<script setup lang="ts">
import { useId } from 'vue'

/** Decorative ribbon curves and gold star (complement §3 symbol `ribbons`, viewBox 400×300). */
const id = useId()
</script>

<template>
  <svg viewBox="0 0 400 300" fill="none" aria-hidden="true" focusable="false">
    <defs>
      <linearGradient :id="`${id}-rib`" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#5A2BD0" />
        <stop offset=".45" stop-color="#A12FA4" />
        <stop offset=".75" stop-color="#E5407B" />
        <stop offset="1" stop-color="#F7934A" />
      </linearGradient>
    </defs>
    <path
      d="M20 40 C 70 30, 110 120, 150 210 C 175 265, 220 270, 250 230 C 290 170, 300 90, 380 60"
      :stroke="`url(#${id}-rib)`"
      stroke-width="38"
      stroke-linecap="round"
      opacity=".9"
    />
    <path
      d="M120 20 C 170 20, 210 110, 235 170 C 255 220, 300 250, 370 240"
      :stroke="`url(#${id}-rib)`"
      stroke-width="14"
      stroke-linecap="round"
      opacity=".45"
    />
    <path d="M318 26 l7 15 15 7 -15 7 -7 15 -7 -15 -15 -7 15 -7z" fill="#F4A62A" />
  </svg>
</template>

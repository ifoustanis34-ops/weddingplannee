<script setup lang="ts">
import { useQueryClient } from '@tanstack/vue-query'
import { ChevronLeft, ChevronRight, Pause, Play, RotateCcw, UserRound, X } from '@lucide/vue'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { toApiError } from '@/api/errors'
import { useToast } from '@/composables/useToast'
import { demoApi } from '@/modules/presentation/api'
import {
  paused,
  presenting,
  scenario,
  speed,
  startRole,
  stepIndex,
  stopPresentation,
} from '@/modules/presentation/player'
import { SPEEDS, stepDuration } from '@/modules/presentation/scenarios'
import { useSessionStore } from '@/stores/session'

/**
 * Presentation player (feedback 16/11/2026): plays a journey of the demo agency by itself —
 * switches role when the step asks for it, opens the screen (or a real record of the demo),
 * points at what matters and tells what it is for — then moves on. The presenter keeps the
 * controls: pause (Space), back / next (arrows), speed, quit (Escape).
 */
const { t } = useI18n()
const router = useRouter()
const session = useSessionStore()
const queryClient = useQueryClient()
const toast = useToast()

const step = computed(() => scenario.value?.steps[stepIndex.value] ?? null)
const total = computed(() => scenario.value?.steps.length ?? 0)
const busy = ref(false)
const finished = ref(false)
const progress = ref(0)
const box = ref<{ top: number; left: number; width: number; height: number } | null>(null)
let targetEl: HTMLElement | null = null
let ticker: ReturnType<typeof setInterval> | undefined
let generation = 0

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

async function switchRole(role: NonNullable<typeof session.role>): Promise<void> {
  await demoApi.switchRole(role)
  await session.refresh()
  // Amounts and lists differ by role: everything is read again with the new account.
  await queryClient.invalidateQueries()
}

function measure(): void {
  if (!targetEl || !targetEl.isConnected) {
    box.value = null
    return
  }
  const r = targetEl.getBoundingClientRect()
  box.value =
    r.width && r.height ? { top: r.top, left: r.left, width: r.width, height: r.height } : null
}

async function locate(selector: string | undefined, run: number): Promise<void> {
  targetEl = null
  box.value = null
  if (!selector) return
  for (let i = 0; i < 25 && run === generation; i += 1) {
    const found = [...document.querySelectorAll<HTMLElement>(selector)].find(
      (el) => el.offsetParent !== null || el.getClientRects().length > 0,
    )
    if (found) {
      targetEl = found
      found.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
      await sleep(250)
      measure()
      return
    }
    await sleep(120)
  }
}

async function enter(): Promise<void> {
  const current = step.value
  if (!presenting.value || !current) return
  const run = ++generation
  busy.value = true
  finished.value = false
  progress.value = 0
  try {
    if (current.role && current.role !== session.role) await switchRole(current.role)
    const target = typeof current.route === 'function' ? await current.route() : current.route
    if (run !== generation) return
    await router.push(target).catch(() => undefined)
    await nextTick()
    await sleep(650)
    await locate(current.target, run)
  } catch (error) {
    toast.error(toApiError(error).message)
  } finally {
    if (run === generation) busy.value = false
  }
}

function next(): void {
  if (stepIndex.value < total.value - 1) stepIndex.value += 1
  else {
    finished.value = true
    progress.value = 1
  }
}
function previous(): void {
  if (stepIndex.value > 0) stepIndex.value -= 1
}
function replay(): void {
  finished.value = false
  if (stepIndex.value === 0) void enter()
  else stepIndex.value = 0
}
async function quit(): Promise<void> {
  generation += 1
  const back = startRole.value
  stopPresentation()
  finished.value = false
  box.value = null
  try {
    if (back && back !== session.role) await switchRole(back)
  } catch (error) {
    toast.error(toApiError(error).message)
  }
  startRole.value = null
  await router.push({ name: 'presentation' }).catch(() => undefined)
}

// The clock: moves the progress bar and goes on by itself, unless paused or loading.
function tick(): void {
  if (!presenting.value || paused.value || busy.value || finished.value || !step.value) return
  progress.value += 100 / stepDuration(step.value, speed.value)
  if (progress.value >= 1) next()
}

watch([presenting, stepIndex, scenario], ([on]) => {
  if (on) void enter()
})

function onKey(event: KeyboardEvent): void {
  if (!presenting.value) return
  const tag = (event.target as HTMLElement | null)?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
  if (event.key === ' ') {
    event.preventDefault()
    paused.value = !paused.value
  } else if (event.key === 'ArrowRight') next()
  else if (event.key === 'ArrowLeft') previous()
  else if (event.key === 'Escape') void quit()
}
onMounted(() => {
  ticker = setInterval(tick, 100)
  window.addEventListener('keydown', onKey)
  window.addEventListener('resize', measure)
  window.addEventListener('scroll', measure, true)
  if (presenting.value) void enter()
})
onBeforeUnmount(() => {
  clearInterval(ticker)
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('resize', measure)
  window.removeEventListener('scroll', measure, true)
})

const prefix = computed(() => `presentation.scenarios.${scenario.value?.id ?? ''}`)
/** A record open on the right (drawer): the commentary moves to the left, over the dimmed
 *  page, so it never hides the record's figures and buttons. */
const panelStyle = computed(() => {
  const left = box.value?.left ?? 0
  if (box.value && left > window.innerWidth * 0.35 && left - 32 >= 320)
    return { left: '16px', width: `${Math.min(620, left - 32)}px`, translate: 'none' }
  return {}
})
const pointer = computed(() =>
  box.value
    ? {
        left: `${box.value.left + Math.min(box.value.width - 18, Math.max(box.value.width / 2, 24))}px`,
        top: `${box.value.top + Math.min(box.value.height - 10, Math.max(box.value.height / 2, 14))}px`,
      }
    : null,
)
</script>

<template>
  <div v-if="presenting && scenario && step" class="pointer-events-none fixed inset-0 z-[70]">
    <!-- What to look at: a ring around it and the presenter's pointer gliding to it -->
    <div
      v-if="box"
      class="absolute rounded-[12px] ring-4 ring-gold-bright/90 transition-all duration-500 ease-out"
      :style="{
        top: `${box.top - 6}px`,
        left: `${box.left - 6}px`,
        width: `${box.width + 12}px`,
        height: `${box.height + 12}px`,
        boxShadow: '0 0 0 9999px rgb(10 9 30 / 0.28)',
      }"
      aria-hidden="true"
    />
    <div
      v-if="pointer"
      class="absolute size-6 -translate-x-1/2 -translate-y-1/2 transition-all duration-700 ease-out"
      :style="pointer"
      aria-hidden="true"
    >
      <span class="absolute inset-0 animate-ping rounded-full bg-gold-bright/60" />
      <span
        class="absolute inset-1 rounded-full border-2 border-white bg-gold-bright shadow-wd-lg"
      />
    </div>

    <!-- The commentary and the controls -->
    <section
      class="pointer-events-auto absolute bottom-4 left-1/2 w-[min(680px,calc(100vw-24px))] -translate-x-1/2 overflow-hidden rounded-[18px] bg-hero text-hero-ink shadow-wd-lg"
      :style="panelStyle"
      role="region"
      :aria-label="t('presentation.player.label')"
      aria-live="polite"
    >
      <div class="h-1 bg-white/10">
        <div
          class="h-full bg-ribbon transition-[width] duration-100 ease-linear"
          :style="{ width: `${((stepIndex + (finished ? 1 : progress)) / total) * 100}%` }"
        />
      </div>
      <div class="p-4 sm:p-5">
        <div class="flex flex-wrap items-center gap-2 text-[12.5px] text-hero-muted">
          <span class="font-bold text-gold-bright">{{ t(`${prefix}.title`) }}</span>
          <span>·</span>
          <span class="num">{{ t('presentation.player.step', { n: stepIndex + 1, total }) }}</span>
          <span
            v-if="session.role"
            class="ml-auto inline-flex items-center gap-1 rounded-full bg-white/10 px-2.5 py-0.5 font-semibold text-hero-ink"
          >
            <UserRound class="size-3.5" aria-hidden="true" />{{
              t('presentation.player.seenBy', { role: t(`roles.${session.role}`) })
            }}
          </span>
        </div>
        <template v-if="finished">
          <h2 class="mt-2 text-[20px] font-semibold text-hero-ink">
            {{ t('presentation.player.doneTitle') }}
          </h2>
          <p class="mt-1 text-[14px] text-hero-muted">{{ t('presentation.player.doneText') }}</p>
        </template>
        <template v-else>
          <h2 class="mt-2 text-[20px] leading-snug font-semibold text-hero-ink">
            {{ t(`${prefix}.steps.${step.key}.title`) }}
          </h2>
          <p class="mt-1 text-[14.5px] leading-relaxed text-hero-ink/85">
            {{ t(`${prefix}.steps.${step.key}.text`) }}
          </p>
        </template>

        <div class="mt-4 flex flex-wrap items-center gap-2">
          <button
            type="button"
            class="inline-flex size-10 items-center justify-center rounded-[10px] bg-white/10 hover:bg-white/20 disabled:opacity-40"
            :disabled="stepIndex === 0 || busy"
            :aria-label="t('presentation.player.previous')"
            :title="t('presentation.player.previous')"
            @click="previous"
          >
            <ChevronLeft class="size-5" aria-hidden="true" />
          </button>
          <button
            v-if="!finished"
            type="button"
            class="inline-flex h-10 items-center gap-2 rounded-[10px] bg-white px-4 font-bold text-hero hover:bg-white/90"
            @click="paused = !paused"
          >
            <component :is="paused ? Play : Pause" class="size-[18px]" aria-hidden="true" />{{
              paused ? t('presentation.player.play') : t('presentation.player.pause')
            }}
          </button>
          <button
            v-else
            type="button"
            class="inline-flex h-10 items-center gap-2 rounded-[10px] bg-white px-4 font-bold text-hero hover:bg-white/90"
            @click="replay"
          >
            <RotateCcw class="size-[18px]" aria-hidden="true" />{{
              t('presentation.player.replay')
            }}
          </button>
          <button
            type="button"
            class="inline-flex size-10 items-center justify-center rounded-[10px] bg-white/10 hover:bg-white/20 disabled:opacity-40"
            :disabled="finished || busy"
            :aria-label="t('presentation.player.next')"
            :title="t('presentation.player.next')"
            @click="next"
          >
            <ChevronRight class="size-5" aria-hidden="true" />
          </button>
          <span
            class="ml-1 inline-flex rounded-[10px] bg-white/10 p-0.5"
            role="group"
            :aria-label="t('presentation.player.speed')"
          >
            <button
              v-for="value in SPEEDS"
              :key="value"
              type="button"
              class="num rounded-[8px] px-2.5 py-1.5 text-[12.5px] font-bold"
              :class="
                speed === value ? 'bg-white text-hero' : 'text-hero-muted hover:text-hero-ink'
              "
              :aria-pressed="speed === value"
              @click="speed = value"
            >
              {{ String(value).replace('.', ',') }}×
            </button>
          </span>
          <span v-if="busy" class="text-[12.5px] text-hero-muted">{{
            t('presentation.player.loading')
          }}</span>
          <button
            type="button"
            class="ml-auto inline-flex h-10 items-center gap-1.5 rounded-[10px] px-3 text-[13.5px] font-bold text-hero-muted hover:bg-white/10 hover:text-hero-ink"
            @click="quit"
          >
            <X class="size-4" aria-hidden="true" />{{ t('presentation.player.quit') }}
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

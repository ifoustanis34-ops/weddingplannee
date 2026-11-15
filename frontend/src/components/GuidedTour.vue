<script setup lang="ts">
import { ArrowLeft, ArrowRight, Compass, X } from '@lucide/vue'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { postponeTour, tourPostponed, tourSteps, useTour } from '@/app/tour'
import { WButton, WModal } from '@/design'
import { useSessionStore } from '@/stores/session'

/** Guided tour of the application (feedback 15/11/2026): the offer, then one card per step. */
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const tour = useTour()

// --- Offer at sign-in: « Voulez-vous découvrir Wedivo pas à pas ? » ---------------------------
const offerOpen = ref(false)
const postponed = ref(tourPostponed())
const shouldOffer = computed(
  () =>
    session.user?.tourDone === false &&
    !session.user.mustChangePassword &&
    session.role !== null &&
    !postponed.value &&
    !tour.running.value &&
    route.name !== 'profile',
)
let offerTimer: ReturnType<typeof setTimeout> | undefined
watch(
  shouldOffer,
  (value) => {
    clearTimeout(offerTimer)
    // A short pause: the home page shows first, then the question.
    if (value) offerTimer = setTimeout(() => (offerOpen.value = shouldOffer.value), 700)
  },
  { immediate: true },
)

let answered = false
function accept(): void {
  answered = true
  offerOpen.value = false
  tour.start()
}
function later(): void {
  answered = true
  offerOpen.value = false
  postponeTour()
  postponed.value = true
}
function decline(): void {
  answered = true
  offerOpen.value = false
  void session.finishTour().catch(() => undefined)
}
// Closing the window (cross, Escape, outside) means « plus tard ».
watch(offerOpen, (open) => {
  if (open) answered = false
  else if (!answered) later()
})

// --- The tour itself ----------------------------------------------------------------------------
const steps = computed(() => tourSteps(session.role, session.weddingsEnabled))
const index = ref(0)
const step = computed(() => steps.value[index.value] ?? steps.value[0]!)
const isLast = computed(() => index.value === steps.value.length - 1)
const title = computed(() =>
  step.value.navLabel ? t(`nav.${step.value.navLabel}`) : t(`tour.steps.${step.value.key}.title`),
)
const body = computed(() =>
  t(`tour.steps.${step.value.key}.text`, {
    name: session.firstName,
    space: session.currentOrganization?.name ?? '',
  }),
)

const card = ref<HTMLElement | null>(null)
const highlight = ref<{ top: number; left: number; width: number; height: number } | null>(null)

/** The marked element actually on screen (menu on a computer, bottom tab on a phone). */
function findTarget(): HTMLElement | null {
  if (!step.value.target) return null
  const candidates = document.querySelectorAll<HTMLElement>(`[data-tour="${step.value.target}"]`)
  for (const element of candidates) {
    const box = element.getBoundingClientRect()
    if (box.width > 0 && box.height > 0) return element
  }
  return null
}

function place(): void {
  const element = findTarget()
  if (!element) {
    highlight.value = null
    return
  }
  const box = element.getBoundingClientRect()
  highlight.value = {
    top: box.top - 4,
    left: box.left - 4,
    width: box.width + 8,
    height: box.height + 8,
  }
}

async function show(at: number): Promise<void> {
  index.value = Math.min(Math.max(at, 0), steps.value.length - 1)
  const target = step.value.routeName
  if (target && route.name !== target) {
    try {
      await router.push({ name: target })
    } catch {
      // A page that cannot open (guard): the card is still shown.
    }
  }
  await nextTick()
  findTarget()?.scrollIntoView({ block: 'nearest' })
  place()
  card.value?.focus()
}

function finish(): void {
  tour.stop()
  highlight.value = null
  // Followed or left halfway: it is no longer offered; « Visite guidée » replays it.
  if (session.user?.tourDone === false) void session.finishTour().catch(() => undefined)
}

watch(
  () => tour.running.value,
  (running) => {
    if (running) void show(0)
  },
)

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') finish()
  else if (event.key === 'ArrowRight' && !isLast.value) void show(index.value + 1)
  else if (event.key === 'ArrowLeft' && index.value > 0) void show(index.value - 1)
}

let frame = 0
function onViewportChange(): void {
  if (!tour.running.value) return
  cancelAnimationFrame(frame)
  frame = requestAnimationFrame(place)
}
onMounted(() => {
  window.addEventListener('resize', onViewportChange)
  window.addEventListener('scroll', onViewportChange, true)
})
onBeforeUnmount(() => {
  clearTimeout(offerTimer)
  cancelAnimationFrame(frame)
  window.removeEventListener('resize', onViewportChange)
  window.removeEventListener('scroll', onViewportChange, true)
})
</script>

<template>
  <WModal
    v-model:open="offerOpen"
    size="sm"
    :title="t('tour.offer.title', { name: session.firstName })"
  >
    <div class="flex items-start gap-3.5">
      <span
        class="flex size-11 shrink-0 items-center justify-center rounded-full bg-violet-soft text-violet"
        aria-hidden="true"
      >
        <Compass class="size-6" />
      </span>
      <div class="space-y-2 text-[14px] text-ink-2">
        <p>{{ t('tour.offer.text') }}</p>
        <p class="text-[13px] text-muted">{{ t('tour.offer.hint') }}</p>
      </div>
    </div>
    <template #footer>
      <div class="flex w-full flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <WButton variant="ghost" @click="decline">{{ t('tour.offer.no') }}</WButton>
        <WButton variant="secondary" @click="later">{{ t('tour.offer.later') }}</WButton>
        <WButton @click="accept">{{ t('tour.offer.yes') }}</WButton>
      </div>
    </template>
  </WModal>

  <Teleport to="body">
    <template v-if="tour.running.value">
      <div
        v-if="highlight"
        class="pointer-events-none fixed z-[60] rounded-[12px] ring-[3px] ring-violet ring-offset-2 ring-offset-surface motion-safe:transition-all motion-safe:duration-200"
        :style="{
          top: `${highlight.top}px`,
          left: `${highlight.left}px`,
          width: `${highlight.width}px`,
          height: `${highlight.height}px`,
        }"
        aria-hidden="true"
      />
      <section
        ref="card"
        role="dialog"
        :aria-label="t('tour.label')"
        tabindex="-1"
        class="fixed inset-x-3 bottom-[calc(76px+env(safe-area-inset-bottom,0px))] z-[61] rounded-[18px] border border-line bg-surface p-4 shadow-wd-lg outline-none nav:inset-x-auto nav:right-6 nav:bottom-6 nav:w-[380px]"
        @keydown="onKeydown"
      >
        <div class="flex items-center gap-2">
          <span class="text-[12px] font-bold text-violet">
            {{ t('tour.progress', { step: index + 1, total: steps.length }) }}
          </span>
          <button
            type="button"
            class="ml-auto rounded-wd-sm p-1 text-muted hover:bg-surface-2 hover:text-ink"
            :aria-label="t('tour.close')"
            @click="finish"
          >
            <X class="size-[18px]" aria-hidden="true" />
          </button>
        </div>
        <div
          class="mt-1.5 h-1 overflow-hidden rounded-full bg-surface-2"
          role="progressbar"
          :aria-valuenow="index + 1"
          :aria-valuemin="1"
          :aria-valuemax="steps.length"
        >
          <div
            class="h-full rounded-full bg-violet motion-safe:transition-[width]"
            :style="{ width: `${((index + 1) / steps.length) * 100}%` }"
          />
        </div>
        <div aria-live="polite">
          <h2 class="mt-3 text-[16px] font-semibold">{{ title }}</h2>
          <p class="mt-1.5 text-[14px] leading-relaxed text-ink-2">{{ body }}</p>
        </div>
        <div class="mt-4 flex items-center gap-2">
          <WButton v-if="index > 0" variant="ghost" size="sm" @click="show(index - 1)">
            <ArrowLeft class="size-[15px]" aria-hidden="true" />{{ t('tour.previous') }}
          </WButton>
          <WButton v-if="!isLast" class="ml-auto" size="sm" @click="show(index + 1)">
            {{ t('tour.next') }}<ArrowRight class="size-[15px]" aria-hidden="true" />
          </WButton>
          <WButton v-else class="ml-auto" size="sm" @click="finish">{{ t('tour.finish') }}</WButton>
        </div>
      </section>
    </template>
  </Teleport>
</template>

<script setup lang="ts">
import {
  Calendar,
  CalendarCheck,
  Clock,
  FileText,
  Lock,
  Mail,
  MessageCircle,
  Package,
  Phone,
  UserCog,
  Wallet,
} from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import { hasSupport, SUPPORT, telHref, whatsappHref } from '@/app/support'
import { WLogo, WRibbons } from '@/design'

/**
 * Sign-in and sign-up shell (redesigned 13/11/2026): on the left, what the platform does (the
 * app's own modules, with their menu icons) and how to reach Wedivo; on the right, the form on a
 * card. One column under 900px, the contacts then come under the form.
 */
const { t } = useI18n()
const route = useRoute()

const MODULES = [
  { key: 'reservations', icon: CalendarCheck },
  { key: 'stock', icon: Package },
  { key: 'quotes', icon: FileText },
  { key: 'finance', icon: Wallet },
  { key: 'staff', icon: UserCog },
  { key: 'calendar', icon: Calendar },
] as const

const contacts = computed(() =>
  [
    SUPPORT.phone && {
      key: 'call',
      icon: Phone,
      label: t('auth.help.call'),
      value: SUPPORT.phone,
      href: telHref(SUPPORT.phone),
      external: false,
    },
    SUPPORT.whatsapp && {
      key: 'whatsapp',
      icon: MessageCircle,
      label: t('auth.help.whatsapp'),
      value: SUPPORT.whatsapp,
      href: whatsappHref(SUPPORT.whatsapp),
      external: true,
    },
    SUPPORT.email && {
      key: 'email',
      icon: Mail,
      label: t('auth.help.email'),
      value: SUPPORT.email,
      href: `mailto:${SUPPORT.email}`,
      external: false,
    },
  ].filter((item) => !!item),
)
const year = new Date().getFullYear()

/** The segmented switch only appears on the two entry pages. */
const tabs = computed(() =>
  route.name === 'login' || route.name === 'signup'
    ? [
        { name: 'login', label: t('auth.tabs.login') },
        { name: 'signup', label: t('auth.tabs.signup') },
      ]
    : [],
)
</script>

<template>
  <div class="grid min-h-dvh bg-bg min-[901px]:grid-cols-[minmax(400px,46%)_minmax(0,1fr)]">
    <aside
      class="relative isolate overflow-hidden bg-hero px-[22px] pt-7 pb-8 text-hero-ink min-[901px]:sticky min-[901px]:top-0 min-[901px]:flex min-[901px]:h-dvh min-[901px]:flex-col min-[901px]:px-[clamp(32px,4.5vw,64px)] min-[901px]:py-10"
    >
      <!-- Decoration: a soft glow and the ribbon, kept in the top corner, behind the text -->
      <div
        class="pointer-events-none absolute -top-40 -left-40 -z-10 size-[520px] rounded-full bg-violet opacity-25 blur-[120px]"
        aria-hidden="true"
      />
      <WRibbons
        class="pointer-events-none absolute -top-[70px] -right-[150px] -z-10 hidden w-[470px] opacity-20 min-[901px]:block"
      />

      <WLogo inverse />

      <div class="mt-6 min-[901px]:my-auto min-[901px]:py-8">
        <p
          class="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[0.06] px-3 py-1 text-[12.5px] font-semibold text-hero-muted"
        >
          <span class="size-1.5 rounded-full bg-gold-bright" aria-hidden="true" />
          {{ t('auth.kicker') }}
        </p>
        <p
          class="mt-4 max-w-[18ch] font-display text-[25px] leading-[1.12] font-semibold tracking-[-0.025em] min-[901px]:text-[clamp(30px,3vw,42px)]"
        >
          {{ t('auth.heroTitle') }}
        </p>
        <p class="mt-3 max-w-[46ch] text-[14.5px] leading-relaxed text-hero-muted">
          {{ t('auth.heroLead') }}
        </p>

        <ul
          class="mt-9 hidden max-w-[560px] grid-cols-2 gap-x-6 gap-y-5 min-[901px]:grid"
          :aria-label="t('auth.modulesLabel')"
        >
          <li v-for="item in MODULES" :key="item.key" class="flex items-start gap-3">
            <span
              class="flex size-9 shrink-0 items-center justify-center rounded-[10px] border border-white/10 bg-white/[0.08] text-gold-bright"
            >
              <component :is="item.icon" class="size-[18px]" aria-hidden="true" />
            </span>
            <span class="min-w-0">
              <span class="block text-[14px] font-bold">{{
                t(`auth.modules.${item.key}.title`)
              }}</span>
              <span class="block text-[12.5px] leading-snug text-hero-muted">{{
                t(`auth.modules.${item.key}.text`)
              }}</span>
            </span>
          </li>
        </ul>
      </div>

      <!-- Contacts (desktop): under the list, at the bottom of the panel -->
      <section
        v-if="hasSupport"
        class="hidden rounded-[16px] border border-white/10 bg-white/[0.05] p-4 min-[901px]:block"
        :aria-label="t('auth.help.title')"
      >
        <div class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
          <p class="font-bold">{{ t('auth.help.title') }}</p>
          <p v-if="SUPPORT.hours" class="flex items-center gap-1.5 text-[12.5px] text-hero-muted">
            <Clock class="size-3.5" aria-hidden="true" />{{ SUPPORT.hours }}
          </p>
        </div>
        <ul class="mt-2 flex flex-col">
          <li v-for="item in contacts" :key="item.key">
            <a
              :href="item.href"
              :target="item.external ? '_blank' : undefined"
              :rel="item.external ? 'noopener' : undefined"
              class="flex items-center gap-2.5 rounded-[11px] px-2 py-1.5 transition-colors hover:bg-white/[0.08] focus-visible:bg-white/[0.08]"
            >
              <span
                class="flex size-7 shrink-0 items-center justify-center rounded-full bg-white/10"
              >
                <component :is="item.icon" class="size-4" aria-hidden="true" />
              </span>
              <span class="text-[13px] text-hero-muted">{{ item.label }}</span>
              <span class="num ml-auto text-[14px] font-semibold">{{ item.value }}</span>
            </a>
          </li>
        </ul>
      </section>
      <p class="mt-4 hidden text-[12px] text-hero-muted min-[901px]:block">
        © {{ year }} Wedivo · {{ t('app.tagline') }}
      </p>
    </aside>

    <main class="flex flex-col px-4 py-8 sm:px-8 min-[901px]:py-10">
      <div class="mx-auto flex w-full max-w-[480px] flex-1 flex-col justify-center">
        <div
          class="rounded-wd-lg border border-line bg-surface p-5 shadow-wd-lg sm:p-8 min-[901px]:p-9"
        >
          <nav
            v-if="tabs.length"
            class="mb-7 grid grid-cols-2 gap-1 rounded-wd bg-surface-2 p-1"
            :aria-label="t('auth.tabs.label')"
          >
            <RouterLink
              v-for="tab in tabs"
              :key="tab.name"
              :to="{ name: tab.name }"
              class="flex items-center justify-center rounded-[9px] px-3 py-2 text-center text-[13.5px] leading-tight font-bold transition-colors"
              :class="
                route.name === tab.name
                  ? 'bg-surface text-ink shadow-wd'
                  : 'text-muted hover:text-ink'
              "
              :aria-current="route.name === tab.name ? 'page' : undefined"
            >
              {{ tab.label }}
            </RouterLink>
          </nav>
          <slot />
        </div>

        <p class="mt-5 flex items-center justify-center gap-1.5 text-[12.5px] text-muted">
          <Lock class="size-3.5" aria-hidden="true" />{{ t('auth.secure') }}
        </p>

        <!-- Contacts (phone): under the form -->
        <section
          v-if="hasSupport"
          class="mt-6 min-[901px]:hidden"
          :aria-label="t('auth.help.title')"
        >
          <p class="text-center text-[13px] font-bold">{{ t('auth.help.title') }}</p>
          <ul class="mt-2.5 flex flex-col gap-2">
            <li v-for="item in contacts" :key="item.key">
              <a
                :href="item.href"
                :target="item.external ? '_blank' : undefined"
                :rel="item.external ? 'noopener' : undefined"
                class="flex items-center gap-3 rounded-wd border border-line bg-surface px-3.5 py-2.5"
              >
                <component :is="item.icon" class="size-[18px] text-violet" aria-hidden="true" />
                <span class="text-[13px] text-muted">{{ item.label }}</span>
                <span class="num ml-auto text-[13.5px] font-semibold">{{ item.value }}</span>
              </a>
            </li>
          </ul>
          <p v-if="SUPPORT.hours" class="mt-2 text-center text-[12px] text-muted">
            {{ SUPPORT.hours }}
          </p>
        </section>
      </div>
    </main>
  </div>
</template>

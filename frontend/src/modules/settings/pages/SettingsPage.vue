<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import CatalogPage from '@/modules/catalog/pages/CatalogPage.vue'
import { useSessionStore } from '@/stores/session'

import BrandingTab from '../components/BrandingTab.vue'
import CompanyTab from '../components/CompanyTab.vue'
import IntegrationsTab from '../components/IntegrationsTab.vue'
import PlanTab from '../components/PlanTab.vue'
import TeamTab from '../components/TeamTab.vue'
import { SETTINGS_TABS, type SettingsTab } from '../routes'

/** Settings (complement §15): vertical tabs of 220px, horizontal and scrollable under 860px. */
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSessionStore()

const tab = computed<SettingsTab>(() =>
  (SETTINGS_TABS as readonly string[]).includes(String(route.params.tab))
    ? (route.params.tab as SettingsTab)
    : 'entreprise',
)
const select = (value: SettingsTab) =>
  void router.replace({ name: 'settings', params: { tab: value } })
</script>

<template>
  <div class="flex flex-col gap-[22px]">
    <header>
      <h1>{{ t('settings.title') }}</h1>
      <p class="mt-1 text-muted">
        {{ t('settings.subtitle', { name: session.currentOrganization?.name ?? '' }) }}
      </p>
    </header>

    <div class="grid grid-cols-1 items-start gap-5 min-[861px]:grid-cols-[220px_minmax(0,1fr)]">
      <nav
        class="-mx-1 flex gap-1 overflow-x-auto px-1 pb-1 [scrollbar-width:none] min-[861px]:sticky min-[861px]:top-[84px] min-[861px]:flex-col min-[861px]:overflow-visible"
        :aria-label="t('settings.title')"
      >
        <button
          v-for="key in SETTINGS_TABS"
          :key="key"
          type="button"
          class="shrink-0 rounded-[10px] px-3 py-2.5 text-left font-bold whitespace-nowrap transition-colors"
          :class="tab === key ? 'bg-surface text-ink shadow-wd' : 'text-ink-2 hover:bg-surface-2'"
          :aria-current="tab === key ? 'page' : undefined"
          @click="select(key)"
        >
          {{ t(`settings.tabs.${key}`) }}
        </button>
      </nav>

      <section class="min-w-0">
        <CompanyTab v-if="tab === 'entreprise'" />
        <BrandingTab v-else-if="tab === 'identite'" />
        <TeamTab v-else-if="tab === 'equipe'" />
        <CatalogPage v-else-if="tab === 'catalogue'" embedded />
        <PlanTab v-else-if="tab === 'abonnement'" />
        <IntegrationsTab v-else />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { CalendarDays, Heart, Plus } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { toApiError } from '@/api/errors'
import { formatMoneyShort } from '@/composables/useMoney'
import { usePermissions } from '@/composables/usePermissions'
import { WBadge, WButton, WDateBlock, WEmptyState, WProgress } from '@/design'

import { useWeddings } from '../api'
import NewWeddingModal from '../components/NewWeddingModal.vue'
import WeddingDrawer from '../components/WeddingDrawer.vue'
import type { Wedding } from '../types'

/** « Mariages » (complement §11): one card per wedding, the drawer for the details. */
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { can } = usePermissions()

const weddings = useWeddings()
const openedId = computed(() =>
  typeof route.query.mariage === 'string' ? route.query.mariage : null,
)
const open = (wedding: Wedding) =>
  void router.replace({ query: { ...route.query, mariage: wedding.id } })
const close = () => void router.replace({ query: { ...route.query, mariage: undefined } })
const newOpen = ref(false)

const tasksLeft = (w: Wedding) => w.tasksTotal - w.tasksDone
</script>

<template>
  <div class="flex flex-col gap-[22px]">
    <header class="flex flex-wrap items-end gap-x-6 gap-y-3">
      <div class="min-w-0 flex-1">
        <h1>{{ t('weddings.title') }}</h1>
        <p class="mt-1 max-w-[64ch] text-muted">{{ t('weddings.subtitle') }}</p>
      </div>
      <div class="flex flex-wrap gap-2">
        <WButton :to="{ name: 'calendar' }" variant="secondary"
          ><CalendarDays class="size-[18px]" aria-hidden="true" />{{ t('nav.calendar') }}</WButton
        >
        <WButton v-if="can('editWeddings')" @click="newOpen = true"
          ><Plus class="size-[18px]" aria-hidden="true" />{{ t('weddings.new') }}</WButton
        >
      </div>
    </header>

    <div
      v-if="weddings.isPending.value"
      class="grid grid-cols-[repeat(auto-fill,minmax(290px,1fr))] gap-4"
    >
      <div v-for="n in 3" :key="n" class="skeleton h-56 rounded-wd-lg" />
    </div>
    <WEmptyState
      v-else-if="weddings.isError.value"
      :title="t('weddings.loadError')"
      :description="toApiError(weddings.error.value).message"
    >
      <WButton variant="secondary" @click="weddings.refetch()">{{ t('common.retry') }}</WButton>
    </WEmptyState>
    <WEmptyState
      v-else-if="!weddings.data.value?.length"
      :icon="Heart"
      :title="t('weddings.emptyTitle')"
      :description="t('weddings.emptyText')"
    />
    <ul v-else class="grid grid-cols-[repeat(auto-fill,minmax(290px,1fr))] gap-4">
      <li v-for="wedding in weddings.data.value" :key="wedding.id">
        <button
          type="button"
          class="flex h-full w-full flex-col gap-4 rounded-wd-lg border border-line bg-surface p-5 text-left transition-colors hover:border-line-2"
          @click="open(wedding)"
        >
          <span class="flex items-start gap-3">
            <WDateBlock v-if="wedding.date" :date="wedding.date" />
            <span class="min-w-0 flex-1">
              <span class="block truncate font-display text-[16px] font-semibold">{{
                wedding.title
              }}</span>
              <span class="block truncate text-[13px] text-muted">{{
                wedding.venue || t('weddings.noVenue')
              }}</span>
            </span>
            <WBadge
              v-if="wedding.daysLeft !== null && wedding.daysLeft >= 0"
              :tone="wedding.daysLeft <= 14 ? 'coral' : 'violet'"
              :dot="false"
              >J-{{ wedding.daysLeft }}</WBadge
            >
          </span>
          <span class="grid grid-cols-3 gap-2 rounded-wd bg-surface-2 px-3 py-2.5 text-[12.5px]">
            <span>
              <span class="block text-muted">{{ t('weddings.guests') }}</span>
              <span class="num block font-semibold text-ink">{{ wedding.guestCount ?? '—' }}</span>
            </span>
            <span>
              <span class="block text-muted">{{ t('weddings.budget') }}</span>
              <span class="num block font-semibold text-ink">{{
                wedding.budget !== null ? formatMoneyShort(wedding.budget) : '—'
              }}</span>
            </span>
            <span>
              <span class="block text-muted">{{ t('weddings.vendors') }}</span>
              <span class="num block font-semibold text-ink">{{ wedding.vendorsCount }}</span>
            </span>
          </span>
          <span class="mt-auto flex flex-col gap-1.5">
            <span class="flex justify-between text-[13px]">
              <span class="text-ink-2">{{
                t('weddings.tasksLeft', { count: tasksLeft(wedding) }, tasksLeft(wedding))
              }}</span>
              <span class="num font-semibold">{{ wedding.progress }}&nbsp;%</span>
            </span>
            <WProgress
              :value="wedding.progress"
              :label="t('weddings.progressOf', { title: wedding.title })"
              ribbon
            />
          </span>
        </button>
      </li>
    </ul>

    <WeddingDrawer :wedding-id="openedId" @close="close" />
    <NewWeddingModal v-model:open="newOpen" @created="open" />
  </div>
</template>

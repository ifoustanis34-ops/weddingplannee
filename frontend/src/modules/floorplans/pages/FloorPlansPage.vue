<script setup lang="ts">
import { PencilRuler, Plus, Search } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { toApiError } from '@/api/errors'
import { formatDate } from '@/composables/useDate'
import { usePermissions } from '@/composables/usePermissions'
import { useToast } from '@/composables/useToast'
import { WButton, WCard, WEmptyState, WInput, WModal } from '@/design'

import { floorPlansApi, useFloorPlanAction, useFloorPlans } from '../api'
import PlanCanvas from '../components/PlanCanvas.vue'
import { metres } from '../elements'
import type { FloorPlanInput } from '../types'

/** « Croquis » (feedback 20/11/2026): the plans of the venues, drawn to scale. */
const { t } = useI18n()
const router = useRouter()
const toast = useToast()
const { can } = usePermissions()
const plans = useFloorPlans()

const search = ref('')
const rows = computed(() => {
  const words = search.value.trim().toLowerCase()
  return (plans.data.value ?? []).filter(
    (plan) => !words || `${plan.name} ${plan.venue}`.toLowerCase().includes(words),
  )
})

// --- New plan: name, venue, length and width ------------------------------------------------
const createOpen = ref(false)
const form = ref<FloorPlanInput>({
  name: '',
  venue: '',
  length: 20,
  width: 12,
  elements: [],
  notes: '',
})
const errors = ref<Record<string, string>>({})
function openCreate(): void {
  form.value = { name: '', venue: '', length: 20, width: 12, elements: [], notes: '' }
  errors.value = {}
  createOpen.value = true
}
const create = useFloorPlanAction(floorPlansApi.create)
async function submit(): Promise<void> {
  errors.value = {}
  if (!form.value.name.trim()) {
    errors.value.name = t('floorplans.form.nameRequired')
    return
  }
  try {
    const plan = await create.mutateAsync(form.value)
    createOpen.value = false
    await router.push({ name: 'floorplan-edit', params: { id: plan.id } })
  } catch (error) {
    const apiError = toApiError(error)
    errors.value = Object.fromEntries(
      Object.entries(apiError.fields).map(([k, v]) => [k, v[0] ?? '']),
    )
    toast.error(apiError.message)
  }
}
</script>

<template>
  <div class="flex flex-col gap-[22px]">
    <header class="flex flex-wrap items-end gap-x-6 gap-y-3">
      <div class="min-w-0 flex-1">
        <h1>{{ t('floorplans.title') }}</h1>
        <p class="mt-1 max-w-[64ch] text-muted">{{ t('floorplans.subtitle') }}</p>
      </div>
      <WButton v-if="can('editWeddings')" @click="openCreate">
        <Plus class="size-[18px]" aria-hidden="true" />{{ t('floorplans.new') }}
      </WButton>
    </header>

    <WInput
      v-if="(plans.data.value?.length ?? 0) > 3"
      v-model="search"
      class="max-w-[420px]"
      type="search"
      :label="t('floorplans.search')"
      :placeholder="t('floorplans.search')"
      hide-label
    >
      <template #prefix><Search class="size-[18px] text-muted" aria-hidden="true" /></template>
    </WInput>

    <WCard v-if="plans.isError.value">
      <WEmptyState
        :title="t('floorplans.loadError')"
        :description="toApiError(plans.error.value).message"
      />
    </WCard>
    <div v-else-if="plans.isPending.value" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <div v-for="i in 3" :key="i" class="skeleton h-[240px]" />
    </div>
    <WCard v-else-if="!rows.length">
      <WEmptyState
        :icon="PencilRuler"
        :title="search ? t('floorplans.noMatch') : t('floorplans.emptyTitle')"
        :description="search ? undefined : t('floorplans.emptyText')"
      >
        <WButton v-if="can('editWeddings') && !search" @click="openCreate">
          <Plus class="size-[18px]" aria-hidden="true" />{{ t('floorplans.new') }}
        </WButton>
      </WEmptyState>
    </WCard>
    <ul v-else class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <li v-for="plan in rows" :key="plan.id">
        <RouterLink
          :to="{ name: 'floorplan-edit', params: { id: plan.id } }"
          class="block overflow-hidden rounded-wd border border-line bg-surface shadow-[var(--shadow)] transition hover:border-violet"
        >
          <div class="border-b border-line">
            <PlanCanvas
              compact
              :length="plan.length"
              :width="plan.width"
              :elements="plan.elements"
              class="max-h-[200px]"
            />
          </div>
          <div class="px-4 py-3">
            <p class="truncate font-bold">{{ plan.name }}</p>
            <p class="truncate text-[13px] text-ink-2">
              {{ plan.venue || t('floorplans.noVenue') }}
            </p>
            <p class="mt-1 text-[12.5px] text-muted">
              {{ t('floorplans.size', { length: metres(plan.length), width: metres(plan.width) }) }}
              · {{ t('floorplans.seats', { count: plan.chairs }, plan.chairs) }} ·
              {{ t('floorplans.updated', { date: formatDate(plan.updatedAt) }) }}
            </p>
          </div>
        </RouterLink>
      </li>
    </ul>

    <WModal v-model:open="createOpen" :title="t('floorplans.new')" size="sm">
      <form id="floorplan-form" class="flex flex-col gap-3" @submit.prevent="submit">
        <WInput
          v-model="form.name"
          :label="t('floorplans.form.name')"
          :placeholder="t('floorplans.form.namePlaceholder')"
          :error="errors.name"
          required
          autofocus
        />
        <WInput
          v-model="form.venue"
          :label="t('floorplans.form.venue')"
          :placeholder="t('floorplans.form.venuePlaceholder')"
        />
        <div class="grid grid-cols-2 gap-3">
          <WInput
            v-model.number="form.length"
            type="number"
            min="1"
            max="500"
            step="0.5"
            inputmode="decimal"
            addon="m"
            :label="t('floorplans.form.length')"
            :error="errors.length"
            required
          />
          <WInput
            v-model.number="form.width"
            type="number"
            min="1"
            max="500"
            step="0.5"
            inputmode="decimal"
            addon="m"
            :label="t('floorplans.form.width')"
            :error="errors.width"
            required
          />
        </div>
        <p class="text-[12.5px] text-muted">{{ t('floorplans.form.sizeHint') }}</p>
      </form>
      <template #footer>
        <WButton variant="secondary" @click="createOpen = false">{{ t('common.cancel') }}</WButton>
        <WButton type="submit" form="floorplan-form" :loading="create.isPending.value">{{
          t('floorplans.create')
        }}</WButton>
      </template>
    </WModal>
  </div>
</template>

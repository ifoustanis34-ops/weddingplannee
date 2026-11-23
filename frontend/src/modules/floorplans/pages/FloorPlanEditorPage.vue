<script setup lang="ts">
import {
  ArrowLeft,
  Copy,
  Download,
  MessageCircle,
  RotateCcw,
  RotateCw,
  Save,
  Trash2,
  Undo2,
} from '@lucide/vue'
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'

import { toApiError } from '@/api/errors'
import { usePermissions } from '@/composables/usePermissions'
import { useToast } from '@/composables/useToast'
import { useWhatsApp } from '@/composables/useWhatsApp'
import { WButton, WCard, WEmptyState, WInput, WModal, WSelect, WTextarea } from '@/design'

import { floorPlansApi, useFloorPlan, useFloorPlanAction } from '../api'
import PlanCanvas from '../components/PlanCanvas.vue'
// three.js is large: the 3D view loads only when it is opened.
const Plan3D = defineAsyncComponent(() => import('../components/Plan3D.vue'))
import { ELEMENTS, isTable, metres, newId, PALETTE, round, seatCount } from '../elements'
import { planToPng } from '../image'
import {
  type Ambiance,
  DEFAULT_AMBIANCE,
  type ElementType,
  type FloorPlanInput,
  type PlanElement,
} from '../types'

/**
 * « Croquis » (feedback 20/11/2026): the planner enters the length and the width of the venue,
 * then places tables, chairs, stage… to scale. Drag with the mouse or the finger; arrows move by
 * 10 cm (1 m with Maj), R turns by 15°, Suppr removes, Ctrl+Z undoes.
 */
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const toast = useToast()
const { can } = usePermissions()
const editable = computed(() => can('editWeddings'))

const planId = computed(() => String(route.params.id))
const plan = useFloorPlan(planId)

const draft = ref<FloorPlanInput & { ambiance: Ambiance }>({
  name: '',
  venue: '',
  length: 20,
  width: 12,
  elements: [],
  notes: '',
  ambiance: { ...DEFAULT_AMBIANCE },
})
const saved = ref('')
// Undo: the elements before each change.
const history: string[] = []
const canUndo = ref(false)
const dirty = computed(() => saved.value !== '' && JSON.stringify(draft.value) !== saved.value)
watch(
  () => plan.data.value,
  (value) => {
    if (!value || dirty.value) return
    draft.value = {
      name: value.name,
      venue: value.venue,
      length: value.length,
      width: value.width,
      elements: value.elements.map((e) => ({ ...e })),
      notes: value.notes,
      ambiance: { ...DEFAULT_AMBIANCE, ...(value.ambiance ?? {}) },
    }
    saved.value = JSON.stringify(draft.value)
    history.length = 0
    canUndo.value = false
  },
  { immediate: true },
)

// --- Undo ------------------------------------------------------------------------------------
/** Call before every change: the state to come back to. */
function remember(): void {
  history.push(JSON.stringify(draft.value.elements))
  if (history.length > 100) history.shift()
  canUndo.value = true
}
function undo(): void {
  const previous = history.pop()
  canUndo.value = history.length > 0
  if (previous === undefined) return
  draft.value.elements = JSON.parse(previous) as PlanElement[]
  if (!draft.value.elements.some((e) => e.id === selectedId.value)) selectedId.value = null
}

// --- Selection and changes -------------------------------------------------------------------
const selectedId = ref<string | null>(null)
const selected = computed(() => draft.value.elements.find((e) => e.id === selectedId.value) ?? null)
const seats = computed(() => seatCount(draft.value.elements))
const tables = computed(() => draft.value.elements.filter((e) => isTable(e.type)).length)

/** Guest tables get a number (T1, T2…); the head table keeps its name. */
const numbered = (type: ElementType) => isTable(type) && type !== 'head_table'

function add(type: ElementType): void {
  const spec = ELEMENTS[type]
  remember()
  // Large items are made to fit the room; new ones appear in the middle, a little apart.
  const w = Math.min(spec.w, draft.value.length)
  const h = Math.min(spec.h, draft.value.width)
  const shift = (draft.value.elements.length % 6) * 0.4
  const tableNumber = draft.value.elements.filter((e) => numbered(e.type)).length + 1
  const element: PlanElement = {
    id: newId(),
    type,
    x: round(Math.max(0, draft.value.length / 2 - w / 2 + shift), 0.05),
    y: round(Math.max(0, draft.value.width / 2 - h / 2 + shift), 0.05),
    w,
    h,
    rotation: 0,
    label: numbered(type) ? `T${tableNumber}` : type === 'text' ? t('floorplans.types.text') : '',
    seats: spec.seats ?? 0,
  }
  draft.value.elements.push(element)
  selectedId.value = element.id
}

function move(id: string, x: number, y: number): void {
  const element = draft.value.elements.find((e) => e.id === id)
  if (!element) return
  if (!dragging) {
    remember()
    dragging = true
  }
  element.x = x
  element.y = y
}
let dragging = false
const moved = () => (dragging = false)

function patch(changes: Partial<PlanElement>): void {
  if (!selected.value) return
  remember()
  Object.assign(selected.value, changes)
}
function setSize(key: 'w' | 'h', value: unknown): void {
  const size = Number(value)
  if (!selected.value || !Number.isFinite(size) || size < 0.1) return
  if (ELEMENTS[selected.value.type].square) patch({ w: round(size), h: round(size) })
  else patch({ [key]: round(size) })
}
function setSeats(value: unknown): void {
  const count = Math.round(Number(value))
  if (Number.isFinite(count) && count >= 0 && count <= 500) patch({ seats: count })
}
function rotate(by: number): void {
  if (!selected.value) return
  patch({ rotation: (((selected.value.rotation + by) % 360) + 360) % 360 })
}
function duplicate(): void {
  if (!selected.value) return
  remember()
  const copy: PlanElement = {
    ...selected.value,
    id: newId(),
    x: round(selected.value.x + 0.5),
    y: round(selected.value.y + 0.5),
  }
  if (numbered(copy.type)) {
    copy.label = `T${draft.value.elements.filter((e) => numbered(e.type)).length + 1}`
  }
  draft.value.elements.push(copy)
  selectedId.value = copy.id
}
function remove(): void {
  if (!selected.value) return
  remember()
  draft.value.elements = draft.value.elements.filter((e) => e.id !== selectedId.value)
  selectedId.value = null
}

function onKey(event: KeyboardEvent): void {
  if (!editable.value) return
  const target = event.target as HTMLElement | null
  if (target?.closest('input, textarea, select, [contenteditable]')) return
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') {
    event.preventDefault()
    undo()
    return
  }
  if (!selected.value) return
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'd') {
    event.preventDefault()
    duplicate()
    return
  }
  const stepSize = event.shiftKey ? 1 : 0.1
  const moves: Record<string, [number, number]> = {
    ArrowLeft: [-stepSize, 0],
    ArrowRight: [stepSize, 0],
    ArrowUp: [0, -stepSize],
    ArrowDown: [0, stepSize],
  }
  if (event.key in moves) {
    event.preventDefault()
    const [dx, dy] = moves[event.key]!
    patch({ x: round(selected.value.x + dx), y: round(selected.value.y + dy) })
  } else if (event.key === 'Delete' || event.key === 'Backspace') {
    event.preventDefault()
    remove()
  } else if (event.key.toLowerCase() === 'r') {
    rotate(event.shiftKey ? -15 : 15)
  } else if (event.key === 'Escape') {
    selectedId.value = null
  }
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))

// --- Save, delete ----------------------------------------------------------------------------
const errors = ref<Record<string, string>>({})
const save = useFloorPlanAction((input: FloorPlanInput) =>
  floorPlansApi.update(planId.value, input),
)
async function submit(): Promise<boolean> {
  errors.value = {}
  try {
    const result = await save.mutateAsync(draft.value)
    saved.value = JSON.stringify(draft.value)
    toast.success(t('floorplans.saved', { name: result.name }))
    return true
  } catch (error) {
    const apiError = toApiError(error)
    errors.value = Object.fromEntries(
      Object.entries(apiError.fields).map(([k, v]) => [k, v[0] ?? '']),
    )
    toast.error(apiError.message)
    return false
  }
}
const deleteOpen = ref(false)
const destroy = useFloorPlanAction(() => floorPlansApi.remove(planId.value))
async function confirmDelete(): Promise<void> {
  try {
    await destroy.mutateAsync(undefined)
    saved.value = JSON.stringify(draft.value)
    toast.success(t('floorplans.deleted'))
    await router.push({ name: 'floorplans' })
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
onBeforeRouteLeave(() => !dirty.value || window.confirm(t('floorplans.leaveUnsaved')))

// « Ambiance » of the 3D view: floor, walls (or outdoors), day or evening, ceiling height.
const AMBIANCE_CHOICES = {
  floor: ['tiles', 'parquet', 'marble', 'concrete', 'carpet', 'grass'],
  walls: ['white', 'cream', 'grey', 'none'],
  light: ['day', 'evening'],
} as const
const ambianceOptions = (key: keyof typeof AMBIANCE_CHOICES) =>
  AMBIANCE_CHOICES[key].map((value) => ({
    value,
    label: t(`floorplans.ambiance.${key}.${value}`),
  }))

// Elements outside a room that was made smaller.
const outside = computed(
  () =>
    draft.value.elements.filter(
      (e) => e.x + e.w / 2 > draft.value.length || e.y + e.h / 2 > draft.value.width,
    ).length,
)

// --- Image and WhatsApp ----------------------------------------------------------------------
const canvas = ref<{ svg: SVGSVGElement | null } | null>(null)
/** « Plan 2D » to draw, « Vue 3D » to see the room as the guests will (feedback 23/11/2026). */
const mode = ref<'2d' | '3d'>('2d')
const scene = ref<{ snapshot: () => Promise<Blob> } | null>(null)
const filename = computed(
  () =>
    `croquis-${mode.value === '3d' ? '3d-' : ''}${(draft.value.name || 'plan')
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .replace(/[^a-zA-Z0-9]+/g, '-')
      .toLowerCase()}.png`,
)
async function image(): Promise<Blob> {
  if (mode.value === '3d') {
    if (!scene.value) throw new Error(t('floorplans.imageError'))
    return scene.value.snapshot()
  }
  selectedId.value = null
  await new Promise((resolve) => requestAnimationFrame(resolve))
  if (!canvas.value?.svg) throw new Error(t('floorplans.imageError'))
  return planToPng(canvas.value.svg)
}
async function downloadImage(): Promise<void> {
  try {
    const href = URL.createObjectURL(await image())
    const link = document.createElement('a')
    link.href = href
    link.download = filename.value
    link.click()
    setTimeout(() => URL.revokeObjectURL(href), 60_000)
  } catch (error) {
    toast.error(error instanceof Error ? error.message : t('floorplans.imageError'))
  }
}
const whatsapp = useWhatsApp()
async function shareImage(): Promise<void> {
  try {
    await whatsapp.share({
      text: () =>
        t('floorplans.whatsappMessage', {
          name: draft.value.name,
          venue: draft.value.venue ? ` (${draft.value.venue})` : '',
          length: metres(draft.value.length),
          width: metres(draft.value.width),
          seats: seats.value,
        }),
      file: image,
      filename: filename.value,
    })
  } catch (error) {
    toast.error(error instanceof Error ? error.message : t('floorplans.imageError'))
  }
}
</script>

<template>
  <div class="flex flex-col gap-[18px]">
    <header class="flex flex-wrap items-center gap-x-4 gap-y-3">
      <WButton
        variant="ghost"
        icon
        :aria-label="t('floorplans.back')"
        @click="router.push({ name: 'floorplans' })"
      >
        <ArrowLeft class="size-[18px]" aria-hidden="true" />
      </WButton>
      <div class="min-w-0 flex-1">
        <h1 class="truncate">{{ draft.name || t('floorplans.title') }}</h1>
        <p class="mt-0.5 text-[13px] text-muted">
          {{ t('floorplans.size', { length: metres(draft.length), width: metres(draft.width) }) }}
          · {{ t('floorplans.seats', { count: seats }, seats) }} ·
          {{ t('floorplans.tables', { count: tables }, tables) }} ·
          {{ t('floorplans.area', { area: Math.round(draft.length * draft.width) }) }}
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <WButton variant="secondary" @click="downloadImage">
          <Download class="size-[18px]" aria-hidden="true" />{{ t('floorplans.image') }}
        </WButton>
        <WButton
          variant="secondary"
          class="text-green"
          :loading="whatsapp.pending.value"
          @click="shareImage"
        >
          <MessageCircle class="size-[18px]" aria-hidden="true" />{{ t('whatsapp.short') }}
        </WButton>
        <WButton v-if="editable" :loading="save.isPending.value" :disabled="!dirty" @click="submit">
          <Save class="size-[18px]" aria-hidden="true" />{{ t('floorplans.save') }}
        </WButton>
      </div>
    </header>

    <WCard v-if="plan.isError.value">
      <WEmptyState
        :title="t('floorplans.loadError')"
        :description="toApiError(plan.error.value).message"
      />
    </WCard>
    <div v-else-if="plan.isPending.value" class="skeleton h-[480px]" />

    <div v-else class="grid gap-[18px] xl:grid-cols-[240px_minmax(0,1fr)_280px]">
      <!-- Room and palette -->
      <aside class="flex flex-col gap-4">
        <WCard>
          <h2 class="text-[15px] font-semibold">{{ t('floorplans.room') }}</h2>
          <div class="mt-3 flex flex-col gap-3">
            <WInput
              v-model="draft.name"
              :label="t('floorplans.form.name')"
              :error="errors.name"
              :disabled="!editable"
            />
            <WInput
              v-model="draft.venue"
              :label="t('floorplans.form.venue')"
              :disabled="!editable"
            />
            <div class="grid grid-cols-2 gap-2">
              <WInput
                v-model.number="draft.length"
                type="number"
                min="1"
                max="500"
                step="0.5"
                inputmode="decimal"
                addon="m"
                :label="t('floorplans.form.length')"
                :error="errors.length"
                :disabled="!editable"
              />
              <WInput
                v-model.number="draft.width"
                type="number"
                min="1"
                max="500"
                step="0.5"
                inputmode="decimal"
                addon="m"
                :label="t('floorplans.form.width')"
                :error="errors.width"
                :disabled="!editable"
              />
            </div>
            <p v-if="outside" class="text-[12.5px] font-semibold text-coral">
              {{ t('floorplans.outside', { count: outside }, outside) }}
            </p>
          </div>
        </WCard>

        <WCard v-if="editable">
          <h2 class="text-[15px] font-semibold">{{ t('floorplans.add') }}</h2>
          <div class="mt-3 grid grid-cols-2 gap-1.5">
            <button
              v-for="type in PALETTE"
              :key="type"
              type="button"
              class="flex items-center gap-2 rounded-[8px] border border-line px-2 py-1.5 text-left text-[12.5px] font-semibold text-ink-2 hover:border-violet hover:text-violet"
              @click="add(type)"
            >
              <span
                class="size-3.5 shrink-0 rounded-[3px] border"
                :class="type === 'round_table' ? 'rounded-full' : ''"
                :style="{
                  background: ELEMENTS[type].fill === 'none' ? 'transparent' : ELEMENTS[type].fill,
                  borderColor: ELEMENTS[type].stroke === 'none' ? '#85829f' : ELEMENTS[type].stroke,
                }"
                aria-hidden="true"
              />
              {{ t(`floorplans.types.${type}`) }}
            </button>
          </div>
        </WCard>
      </aside>

      <!-- The plan -->
      <section class="flex min-w-0 flex-col gap-2">
        <div
          class="flex gap-1 self-start rounded-[10px] border border-line bg-surface p-1"
          role="tablist"
        >
          <button
            v-for="option in ['2d', '3d'] as const"
            :key="option"
            type="button"
            role="tab"
            :aria-selected="mode === option"
            class="rounded-[8px] px-3 py-1.5 text-[13px] font-bold"
            :class="mode === option ? 'bg-violet text-violet-ink' : 'text-ink-2 hover:text-violet'"
            @click="mode = option"
          >
            {{ t(`floorplans.modes.${option}`) }}
          </button>
        </div>
        <div
          v-if="mode === '3d'"
          class="overflow-hidden rounded-wd border border-line shadow-[var(--shadow)]"
        >
          <Plan3D
            ref="scene"
            :length="draft.length"
            :width="draft.width"
            :elements="draft.elements"
            :ambiance="draft.ambiance"
          />
        </div>
        <div v-else class="overflow-hidden rounded-wd border border-line shadow-[var(--shadow)]">
          <PlanCanvas
            ref="canvas"
            :name="draft.name"
            :venue="draft.venue"
            :length="draft.length"
            :width="draft.width"
            :elements="draft.elements"
            :selected="selectedId"
            :editable="editable"
            @select="selectedId = $event"
            @move="move"
            @moved="moved"
          />
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <p v-if="editable" class="flex-1 text-[12.5px] text-muted">{{ t('floorplans.help') }}</p>
          <WButton v-if="editable" size="sm" variant="secondary" :disabled="!canUndo" @click="undo">
            <Undo2 class="size-[15px]" aria-hidden="true" />{{ t('floorplans.undo') }}
          </WButton>
        </div>
      </section>

      <!-- Selected element -->
      <aside class="flex flex-col gap-4">
        <WCard v-if="selected && editable">
          <h2 class="text-[15px] font-semibold">{{ t(`floorplans.types.${selected.type}`) }}</h2>
          <div class="mt-3 flex flex-col gap-3">
            <WInput
              :model-value="selected.label"
              :label="t('floorplans.form.label')"
              maxlength="80"
              @update:model-value="patch({ label: String($event ?? '') })"
            />
            <div class="grid grid-cols-2 gap-2">
              <WInput
                :model-value="selected.w"
                type="number"
                min="0.1"
                step="0.1"
                inputmode="decimal"
                addon="m"
                :label="
                  ELEMENTS[selected.type].square
                    ? t('floorplans.form.diameter')
                    : t('floorplans.form.w')
                "
                @update:model-value="setSize('w', $event)"
              />
              <WInput
                v-if="!ELEMENTS[selected.type].square"
                :model-value="selected.h"
                type="number"
                min="0.1"
                step="0.1"
                inputmode="decimal"
                addon="m"
                :label="t('floorplans.form.h')"
                @update:model-value="setSize('h', $event)"
              />
            </div>
            <WInput
              v-if="ELEMENTS[selected.type].seated"
              :model-value="selected.seats"
              type="number"
              min="0"
              max="500"
              step="1"
              inputmode="numeric"
              :label="t('floorplans.form.seats')"
              @update:model-value="setSeats($event)"
            />
            <div class="grid grid-cols-2 gap-2">
              <WInput
                :model-value="selected.x"
                type="number"
                step="0.1"
                inputmode="decimal"
                addon="m"
                :label="t('floorplans.form.x')"
                @update:model-value="patch({ x: round(Number($event) || 0) })"
              />
              <WInput
                :model-value="selected.y"
                type="number"
                step="0.1"
                inputmode="decimal"
                addon="m"
                :label="t('floorplans.form.y')"
                @update:model-value="patch({ y: round(Number($event) || 0) })"
              />
            </div>
            <div>
              <p class="text-[13px] font-semibold text-ink-2">
                {{ t('floorplans.form.rotation', { angle: Math.round(selected.rotation) }) }}
              </p>
              <div class="mt-1.5 flex flex-wrap gap-1.5">
                <WButton
                  size="sm"
                  variant="secondary"
                  icon
                  :aria-label="t('floorplans.rotateLeft')"
                  @click="rotate(-15)"
                >
                  <RotateCcw class="size-[15px]" aria-hidden="true" />
                </WButton>
                <WButton
                  size="sm"
                  variant="secondary"
                  icon
                  :aria-label="t('floorplans.rotateRight')"
                  @click="rotate(15)"
                >
                  <RotateCw class="size-[15px]" aria-hidden="true" />
                </WButton>
                <WButton size="sm" variant="secondary" @click="rotate(90)">90°</WButton>
              </div>
            </div>
            <div class="flex flex-wrap gap-2 border-t border-line pt-3">
              <WButton size="sm" variant="secondary" @click="duplicate">
                <Copy class="size-[15px]" aria-hidden="true" />{{ t('floorplans.duplicate') }}
              </WButton>
              <WButton size="sm" variant="danger" @click="remove">
                <Trash2 class="size-[15px]" aria-hidden="true" />{{ t('common.delete') }}
              </WButton>
            </div>
          </div>
        </WCard>
        <WCard v-else-if="editable">
          <p class="text-[13px] text-muted">{{ t('floorplans.selectHint') }}</p>
        </WCard>

        <WCard>
          <h2 class="text-[15px] font-semibold">{{ t('floorplans.ambiance.title') }}</h2>
          <div class="mt-3 flex flex-col gap-3">
            <WSelect
              v-for="key in ['floor', 'walls', 'light'] as const"
              :key="key"
              v-model="draft.ambiance[key]"
              :options="ambianceOptions(key)"
              :label="t(`floorplans.ambiance.${key}.label`)"
              :disabled="!editable"
            />
            <WInput
              v-if="draft.ambiance.walls !== 'none'"
              v-model.number="draft.ambiance.height"
              type="number"
              min="2"
              max="20"
              step="0.5"
              inputmode="decimal"
              addon="m"
              :label="t('floorplans.ambiance.height')"
              :disabled="!editable"
            />
          </div>
        </WCard>

        <WCard>
          <WTextarea
            v-model="draft.notes"
            :label="t('floorplans.form.notes')"
            :rows="4"
            :disabled="!editable"
          />
        </WCard>
        <WButton
          v-if="editable"
          variant="ghost"
          class="self-start text-red"
          @click="deleteOpen = true"
        >
          <Trash2 class="size-[16px]" aria-hidden="true" />{{ t('floorplans.delete') }}
        </WButton>
      </aside>
    </div>

    <WModal v-model:open="deleteOpen" :title="t('floorplans.delete')" size="sm">
      <p>{{ t('floorplans.deleteConfirm', { name: draft.name }) }}</p>
      <template #footer>
        <WButton variant="secondary" @click="deleteOpen = false">{{ t('common.cancel') }}</WButton>
        <WButton variant="danger" :loading="destroy.isPending.value" @click="confirmDelete">{{
          t('common.delete')
        }}</WButton>
      </template>
    </WModal>
  </div>
</template>

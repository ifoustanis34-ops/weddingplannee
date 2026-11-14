<script setup lang="ts" generic="Row extends Record<string, unknown>">
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useMediaQuery } from '@/composables/useMediaQuery'

export interface TableColumn {
  key: string
  label: string
  sortable?: boolean
  align?: 'left' | 'right' | 'center'
}

export interface SortState {
  key: string
  direction: 'asc' | 'desc'
}

const props = withDefaults(
  defineProps<{
    columns: TableColumn[]
    rows: Row[]
    rowKey: Extract<keyof Row, string>
    caption: string
    loading?: boolean
    pageSize?: number
    /** Server-side sorting: emit `sort` and display rows as given. */
    manualSort?: boolean
    /** Rows open a detail view on click (emits `row-click`). */
    clickableRows?: boolean
  }>(),
  { loading: false, pageSize: 0, manualSort: false, clickableRows: false },
)

const emit = defineEmits<{ 'row-click': [row: Row] }>()
const sort = defineModel<SortState | null>('sort', { default: null })
const page = ref(1)
const { t } = useI18n()

// Phones: one card per row (first column as title, the others as label / value), instead of a
// table cut on the right.
const compact = useMediaQuery('(max-width: 639px)')
const titleColumn = computed(() => props.columns[0])
const detailColumns = computed(() => props.columns.slice(1).filter((column) => column.label))
const actionColumns = computed(() => props.columns.slice(1).filter((column) => !column.label))
const sortableColumns = computed(() => props.columns.filter((column) => column.sortable))

const collator = new Intl.Collator('fr', { numeric: true, sensitivity: 'base' })

function toText(value: unknown): string {
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return JSON.stringify(value) ?? ''
}

function compare(a: unknown, b: unknown): number {
  if (a == null) return b == null ? 0 : 1
  if (b == null) return -1
  if (typeof a === 'number' && typeof b === 'number') return a - b
  return collator.compare(toText(a), toText(b))
}

const sorted = computed(() => {
  const current = sort.value
  if (!current || props.manualSort) return props.rows
  const direction = current.direction === 'asc' ? 1 : -1
  return [...props.rows].sort((a, b) => compare(a[current.key], b[current.key]) * direction)
})

const pageCount = computed(() =>
  props.pageSize > 0 ? Math.max(1, Math.ceil(sorted.value.length / props.pageSize)) : 1,
)
const visible = computed(() =>
  props.pageSize > 0
    ? sorted.value.slice((page.value - 1) * props.pageSize, page.value * props.pageSize)
    : sorted.value,
)

watch(
  () => [props.rows, sort.value],
  () => (page.value = 1),
)

function toggleSort(column: TableColumn): void {
  if (!column.sortable) return
  const current = sort.value
  sort.value =
    current?.key === column.key && current.direction === 'asc'
      ? { key: column.key, direction: 'desc' }
      : { key: column.key, direction: 'asc' }
}

function ariaSort(column: TableColumn): 'ascending' | 'descending' | 'none' | undefined {
  if (!column.sortable) return undefined
  if (sort.value?.key !== column.key) return 'none'
  return sort.value.direction === 'asc' ? 'ascending' : 'descending'
}

const alignClass = (column: TableColumn) =>
  ({ left: 'text-left', right: 'text-right', center: 'text-center' })[column.align ?? 'left']
</script>

<template>
  <div>
    <!-- Phones: cards -->
    <div v-if="compact">
      <div v-if="sortableColumns.length" class="mb-2 flex flex-wrap gap-1.5">
        <button
          v-for="column in sortableColumns"
          :key="column.key"
          type="button"
          class="inline-flex h-8 items-center gap-1 rounded-full border px-3 text-[12.5px] font-bold"
          :class="
            sort?.key === column.key
              ? 'border-ink bg-ink text-surface'
              : 'border-line-2 bg-surface text-ink-2'
          "
          :aria-pressed="sort?.key === column.key"
          @click="toggleSort(column)"
        >
          {{ column.label }}
          <ArrowUp
            v-if="sort?.key === column.key && sort.direction === 'asc'"
            class="size-3.5"
            aria-hidden="true"
          />
          <ArrowDown v-else-if="sort?.key === column.key" class="size-3.5" aria-hidden="true" />
        </button>
      </div>
      <ul :aria-label="caption" class="flex flex-col gap-2.5">
        <template v-if="loading">
          <li v-for="n in 3" :key="`skeleton-${n}`" class="skeleton h-28 rounded-wd" />
        </template>
        <li v-else-if="!visible.length">
          <slot name="empty">
            <p class="py-6 text-center text-muted">{{ t('table.empty') }}</p>
          </slot>
        </li>
        <li
          v-for="row in visible"
          v-else
          :key="String(row[rowKey])"
          class="rounded-wd border border-line bg-surface p-3.5"
          :class="clickableRows ? 'cursor-pointer active:bg-surface-2' : undefined"
          @click="emit('row-click', row)"
        >
          <div v-if="titleColumn" class="min-w-0">
            <slot :name="`cell-${titleColumn.key}`" :row="row" :value="row[titleColumn.key]">
              <span class="font-bold">{{ row[titleColumn.key] ?? '—' }}</span>
            </slot>
          </div>
          <dl
            v-if="detailColumns.length"
            class="mt-2.5 grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1.5 text-[13.5px]"
          >
            <template v-for="column in detailColumns" :key="column.key">
              <dt class="text-muted">{{ column.label }}</dt>
              <dd class="min-w-0 text-right break-words">
                <slot :name="`cell-${column.key}`" :row="row" :value="row[column.key]">
                  {{ row[column.key] ?? '—' }}
                </slot>
              </dd>
            </template>
          </dl>
          <div
            v-if="actionColumns.length"
            class="mt-2.5 flex flex-wrap justify-end gap-2 border-t border-line pt-2.5"
          >
            <template v-for="column in actionColumns" :key="column.key">
              <slot :name="`cell-${column.key}`" :row="row" :value="row[column.key]" />
            </template>
          </div>
        </li>
      </ul>
    </div>

    <div v-else class="overflow-x-auto [-webkit-overflow-scrolling:touch]">
      <table class="w-full min-w-[640px] border-collapse text-[14px]">
        <caption class="sr-only">
          {{
            caption
          }}
        </caption>
        <thead>
          <tr>
            <th
              v-for="column in columns"
              :key="column.key"
              scope="col"
              :aria-sort="ariaSort(column)"
              class="border-b border-line px-3 py-2.5 text-[12.5px] font-bold whitespace-nowrap text-muted"
              :class="alignClass(column)"
            >
              <button
                v-if="column.sortable"
                type="button"
                class="inline-flex items-center gap-1 hover:text-ink"
                @click="toggleSort(column)"
              >
                {{ column.label }}
                <ArrowUp
                  v-if="sort?.key === column.key && sort.direction === 'asc'"
                  class="size-3.5"
                  aria-hidden="true"
                />
                <ArrowDown
                  v-else-if="sort?.key === column.key"
                  class="size-3.5"
                  aria-hidden="true"
                />
                <ArrowUpDown v-else class="size-3.5 opacity-50" aria-hidden="true" />
              </button>
              <template v-else>{{ column.label }}</template>
            </th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 4" :key="`skeleton-${n}`">
              <td
                v-for="column in columns"
                :key="column.key"
                class="border-b border-line px-3 py-[13px]"
              >
                <div class="skeleton h-4 w-3/4" />
              </td>
            </tr>
          </template>
          <tr v-else-if="!visible.length">
            <td :colspan="columns.length" class="px-3 py-2">
              <slot name="empty">
                <p class="py-6 text-center text-muted">{{ t('table.empty') }}</p>
              </slot>
            </td>
          </tr>
          <tr
            v-for="row in visible"
            v-else
            :key="String(row[rowKey])"
            class="hover:bg-surface-2"
            :class="clickableRows ? 'cursor-pointer' : undefined"
            @click="emit('row-click', row)"
          >
            <td
              v-for="column in columns"
              :key="column.key"
              class="border-b border-line px-3 py-[13px] align-top"
              :class="[alignClass(column), column.align === 'right' && 'num whitespace-nowrap']"
            >
              <slot :name="`cell-${column.key}`" :row="row" :value="row[column.key]">
                {{ row[column.key] ?? '—' }}
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <nav
      v-if="pageCount > 1"
      class="flex items-center justify-end gap-2 pt-3 text-[13px] text-ink-2"
      :aria-label="t('table.pagination')"
    >
      <button
        type="button"
        class="rounded-wd-sm border border-line p-1.5 disabled:opacity-40"
        :disabled="page === 1"
        :aria-label="t('table.previous')"
        @click="page--"
      >
        <ChevronLeft class="size-4" aria-hidden="true" />
      </button>
      <span class="tabular">{{ t('table.page', { page, count: pageCount }) }}</span>
      <button
        type="button"
        class="rounded-wd-sm border border-line p-1.5 disabled:opacity-40"
        :disabled="page === pageCount"
        :aria-label="t('table.next')"
        @click="page++"
      >
        <ChevronRight class="size-4" aria-hidden="true" />
      </button>
    </nav>
  </div>
</template>

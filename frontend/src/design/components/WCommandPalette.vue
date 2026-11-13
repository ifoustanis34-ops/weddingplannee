<script setup lang="ts">
import { Search } from '@lucide/vue'
import { type Component, computed, ref, useId, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useDialog } from './useDialog'

export interface CommandItem {
  id: string
  label: string
  group: string
  icon?: Component
  /** Secondary text on the right (client of a quote, status…). */
  hint?: string
  keywords?: string
  run: () => void
}

const props = withDefaults(
  defineProps<{
    items: CommandItem[]
    /** Results already filtered by the server (clients, quotes), shown after local matches. */
    remoteItems?: CommandItem[]
    loading?: boolean
    /** Group headings in this order; unknown groups follow in order of appearance. */
    groupOrder?: string[]
  }>(),
  { remoteItems: () => [], loading: false, groupOrder: () => [] },
)
const open = defineModel<boolean>('open', { default: false })
/** Typed text, exposed so the parent can query the server. */
const query = defineModel<string>('query', { default: '' })
const { t } = useI18n()
const id = useId()
const panel = ref<HTMLElement | null>(null)
const active = ref(0)
const { onKeydown: onDialogKeydown } = useDialog(open, panel, () => (open.value = false))

const normalize = (text: string) =>
  text
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()

/** Results grouped (« Pages », « Clients »…), 12 at most, first one selected. */
const MAX_RESULTS = 12
const results = computed(() => {
  const terms = normalize(query.value).split(/\s+/).filter(Boolean)
  const matches = props.items.filter((item) => {
    const haystack = normalize(`${item.label} ${item.group} ${item.keywords ?? ''}`)
    return terms.every((term) => haystack.includes(term))
  })
  const all = [...matches, ...props.remoteItems]
  const groups = [...new Set([...props.groupOrder, ...all.map((item) => item.group)])]
  return all.sort((a, b) => groups.indexOf(a.group) - groups.indexOf(b.group)).slice(0, MAX_RESULTS)
})
const startsGroup = (index: number) =>
  index === 0 || results.value[index - 1]?.group !== results.value[index]?.group

watch(query, () => (active.value = 0))
watch(open, (isOpen) => {
  if (isOpen) {
    query.value = ''
    active.value = 0
  }
})

function run(item: CommandItem | undefined): void {
  if (!item) return
  open.value = false
  item.run()
}

function onKeydown(event: KeyboardEvent): void {
  const count = results.value.length
  if (event.key === 'ArrowDown' && count) {
    event.preventDefault()
    active.value = (active.value + 1) % count
  } else if (event.key === 'ArrowUp' && count) {
    event.preventDefault()
    active.value = (active.value - 1 + count) % count
  } else if (event.key === 'Enter') {
    event.preventDefault()
    run(results.value[active.value])
  } else {
    onDialogKeydown(event)
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-start justify-center bg-scrim px-3 pt-[12vh] backdrop-blur-[2px]"
      @mousedown.self="open = false"
    >
      <div
        ref="panel"
        role="dialog"
        aria-modal="true"
        :aria-label="t('palette.title')"
        class="w-full max-w-[600px] overflow-hidden rounded-[16px] bg-surface shadow-wd-lg"
        @keydown="onKeydown"
      >
        <div class="flex items-center gap-3 border-b border-line px-4">
          <Search class="size-5 text-muted" aria-hidden="true" />
          <input
            v-model="query"
            autofocus
            type="text"
            role="combobox"
            aria-expanded="true"
            :aria-controls="`${id}-list`"
            :aria-activedescendant="results.length ? `${id}-item-${active}` : undefined"
            :aria-label="t('palette.placeholder')"
            :placeholder="t('palette.placeholder')"
            class="h-[54px] flex-1 bg-transparent text-[16px] outline-none placeholder:text-muted"
          />
          <kbd class="rounded border border-line px-1.5 text-[12px] text-muted">Échap</kbd>
        </div>
        <ul
          :id="`${id}-list`"
          role="listbox"
          class="max-h-[50vh] overflow-y-auto p-2"
          :aria-busy="loading || undefined"
        >
          <template v-for="(item, index) in results" :key="item.id">
            <li
              v-if="startsGroup(index)"
              role="presentation"
              class="px-3 pt-2.5 pb-1 text-[12px] font-bold text-muted"
            >
              {{ item.group }}
            </li>
            <li
              :id="`${id}-item-${index}`"
              role="option"
              :aria-selected="index === active"
              class="flex cursor-pointer items-center gap-3 rounded-wd px-3 py-2.5"
              :class="index === active ? 'bg-violet-soft text-ink' : 'text-ink-2'"
              @mouseenter="active = index"
              @click="run(item)"
            >
              <component :is="item.icon" v-if="item.icon" class="size-4" aria-hidden="true" />
              <span class="flex-1 truncate font-semibold">{{ item.label }}</span>
              <span v-if="item.hint" class="truncate text-[12.5px] text-muted">{{
                item.hint
              }}</span>
            </li>
          </template>
          <li v-if="!results.length" class="px-3 py-6 text-center text-muted">
            {{ loading ? t('palette.searching') : t('palette.empty') }}
          </li>
        </ul>
      </div>
    </div>
  </Teleport>
</template>

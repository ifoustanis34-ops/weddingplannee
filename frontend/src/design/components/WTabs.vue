<script setup lang="ts">
import { nextTick, ref, useId } from 'vue'

export interface TabItem {
  key: string
  label: string
  count?: number
}

const props = defineProps<{ tabs: TabItem[]; label: string }>()
const model = defineModel<string>({ required: true })
const id = useId()
const buttons = ref<HTMLButtonElement[]>([])

async function onKeydown(event: KeyboardEvent, index: number): Promise<void> {
  const last = props.tabs.length - 1
  const target = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: last }[event.key]
  if (target === undefined) return
  event.preventDefault()
  const next = (target + props.tabs.length) % props.tabs.length
  const tab = props.tabs[next]
  if (!tab) return
  model.value = tab.key
  await nextTick()
  buttons.value[next]?.focus()
}
</script>

<template>
  <div>
    <div
      role="tablist"
      :aria-label="label"
      class="flex gap-1 overflow-x-auto border-b border-line [scrollbar-width:none]"
    >
      <button
        v-for="(tab, index) in tabs"
        :id="`${id}-tab-${tab.key}`"
        :key="tab.key"
        ref="buttons"
        type="button"
        role="tab"
        :aria-selected="model === tab.key"
        :aria-controls="`${id}-panel`"
        :tabindex="model === tab.key ? 0 : -1"
        class="-mb-px inline-flex items-center gap-2 border-b-2 px-3.5 py-2.5 font-bold whitespace-nowrap"
        :class="
          model === tab.key
            ? 'border-violet text-ink'
            : 'border-transparent text-muted hover:text-ink'
        "
        @click="model = tab.key"
        @keydown="onKeydown($event, index)"
      >
        {{ tab.label }}
        <span v-if="tab.count !== undefined" class="tabular text-[12.5px] font-bold text-muted">{{
          tab.count
        }}</span>
      </button>
    </div>
    <div :id="`${id}-panel`" role="tabpanel" :aria-labelledby="`${id}-tab-${model}`" class="pt-4">
      <slot :active="model" />
    </div>
  </div>
</template>

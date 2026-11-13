<script setup lang="ts">
import { BookOpen, Pencil, Plus, Trash2 } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { usePermissions } from '@/composables/usePermissions'
import { useToast } from '@/composables/useToast'
import { WBadge, WButton, WCard, WEmptyState, WInput, WModal, WMoney } from '@/design'

import { catalogApi, useCatalog, useCatalogMutation } from '../api'
import ItemModal from '../components/ItemModal.vue'
import type { ServiceItem } from '../types'

/** `embedded`: shown inside Paramètres › Catalogue (complement §15), with a card header. */
withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false })
const { t } = useI18n()
const toast = useToast()
const { can } = usePermissions()
const canEdit = computed(() => can('manageCatalog'))
const catalog = useCatalog()
const categories = computed(() => catalog.data.value ?? [])

const itemOpen = ref(false)
const editedItem = ref<ServiceItem | null>(null)
const targetCategory = ref<string>()
function openItem(item: ServiceItem | null, categoryId?: string): void {
  editedItem.value = item
  targetCategory.value = categoryId
  itemOpen.value = true
}

const categoryOpen = ref(false)
const categoryName = ref('')
const categoryError = ref<string>()
const createCategory = useCatalogMutation(catalogApi.createCategory)
async function saveCategory(): Promise<void> {
  if (!categoryName.value.trim()) {
    categoryError.value = t('validation.required')
    return
  }
  try {
    await createCategory.mutateAsync(categoryName.value.trim())
    toast.success(t('catalog.categoryCreated'))
    categoryOpen.value = false
    categoryName.value = ''
  } catch (error) {
    categoryError.value = toApiError(error).fieldError('name') ?? toApiError(error).message
  }
}

const removeItem = useCatalogMutation(catalogApi.deleteItem)
const removeCategory = useCatalogMutation(catalogApi.deleteCategory)
async function remove(kind: 'item' | 'category', id: string): Promise<void> {
  try {
    await (kind === 'item' ? removeItem : removeCategory).mutateAsync(id)
    toast.success(t('catalog.deleted'))
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <header class="flex flex-wrap items-end gap-x-6 gap-y-3">
      <div class="min-w-0 flex-1">
        <h2 v-if="embedded">{{ t('settings.catalog.title') }}</h2>
        <h1 v-else>{{ t('catalog.title') }}</h1>
        <p class="mt-1 text-[13px] text-muted" :class="!embedded && 'text-[14.5px]'">
          {{ embedded ? t('settings.catalog.subtitle') : t('catalog.subtitle') }}
        </p>
      </div>
      <div v-if="canEdit" class="flex gap-2">
        <WButton variant="secondary" @click="categoryOpen = true"
          ><Plus class="size-4" aria-hidden="true" />{{ t('catalog.addCategory') }}</WButton
        >
        <WButton :disabled="!categories.length" @click="openItem(null)"
          ><Plus class="size-4" aria-hidden="true" />{{ t('catalog.addItem') }}</WButton
        >
      </div>
    </header>

    <div v-if="catalog.isPending.value" class="flex flex-col gap-3">
      <div v-for="n in 3" :key="n" class="skeleton h-32" />
    </div>
    <WEmptyState
      v-else-if="catalog.isError.value"
      :title="t('catalog.loadError')"
      :description="toApiError(catalog.error.value).message"
    >
      <WButton variant="secondary" @click="catalog.refetch()">{{ t('common.retry') }}</WButton>
    </WEmptyState>
    <WEmptyState
      v-else-if="!categories.length"
      :icon="BookOpen"
      :title="t('catalog.emptyTitle')"
      :description="t('catalog.emptyText')"
    >
      <WButton v-if="canEdit" @click="categoryOpen = true">{{ t('catalog.addCategory') }}</WButton>
    </WEmptyState>

    <WCard
      v-for="category in categories"
      v-else
      :key="category.id"
      :title="category.name"
      :padded="false"
    >
      <template #actions>
        <div v-if="canEdit" class="flex gap-1 pr-5 sm:pr-6">
          <WButton size="sm" variant="ghost" @click="openItem(null, category.id)"
            ><Plus class="size-4" aria-hidden="true" />{{ t('catalog.addItemShort') }}</WButton
          >
          <WButton
            v-if="!category.items.length"
            size="sm"
            variant="ghost"
            :aria-label="t('common.delete')"
            @click="remove('category', category.id)"
            ><Trash2 class="size-4" aria-hidden="true"
          /></WButton>
        </div>
      </template>
      <p v-if="!category.items.length" class="px-5 pb-5 text-muted sm:px-6">
        {{ t('catalog.categoryEmpty') }}
      </p>
      <ul v-else class="divide-y divide-line border-t border-line">
        <li
          v-for="item in category.items"
          :key="item.id"
          class="flex flex-wrap items-center gap-x-4 gap-y-1 px-5 py-3 sm:px-6"
        >
          <div class="min-w-0 flex-1">
            <p class="font-bold" :class="!item.isActive && 'text-muted line-through'">
              {{ item.name }}
            </p>
            <p v-if="item.description" class="text-[13px] text-muted">{{ item.description }}</p>
          </div>
          <WBadge v-if="!item.isActive" tone="grey" :dot="false">{{
            t('catalog.inactive')
          }}</WBadge>
          <span class="text-right">
            <WMoney :amount="item.unitPrice" class="font-semibold" />
            <span class="block text-[12px] text-muted">{{
              t('catalog.per', { unit: t(`catalog.units.${item.unit}`).toLowerCase() })
            }}</span>
          </span>
          <div v-if="canEdit" class="flex gap-1">
            <WButton
              size="sm"
              variant="ghost"
              :aria-label="t('common.edit')"
              @click="openItem(item)"
              ><Pencil class="size-4" aria-hidden="true"
            /></WButton>
            <WButton
              size="sm"
              variant="ghost"
              :aria-label="t('common.delete')"
              @click="remove('item', item.id)"
              ><Trash2 class="size-4" aria-hidden="true"
            /></WButton>
          </div>
        </li>
      </ul>
    </WCard>

    <ItemModal
      v-model:open="itemOpen"
      :item="editedItem"
      :categories="categories"
      :category-id="targetCategory"
    />
    <WModal v-model:open="categoryOpen" :title="t('catalog.addCategory')" size="sm">
      <form id="category-form" @submit.prevent="saveCategory">
        <WInput
          v-model="categoryName"
          :label="t('catalog.fields.categoryName')"
          :error="categoryError"
          required
          autofocus
        />
      </form>
      <template #footer>
        <WButton variant="secondary" @click="categoryOpen = false">{{
          t('common.cancel')
        }}</WButton>
        <WButton type="submit" form="category-form" :loading="createCategory.isPending.value">{{
          t('catalog.save')
        }}</WButton>
      </template>
    </WModal>
  </div>
</template>

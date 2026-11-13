import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick, ref } from 'vue'

import { useToast } from '@/composables/useToast'
import { WCommandPalette, WModal, WTable, WTabs, WToast } from '@/design'
import { i18n } from '@/i18n'

const global = { plugins: [i18n] }

afterEach(() => {
  document.body.innerHTML = ''
})

describe('WTable', () => {
  const columns = [
    { key: 'name', label: 'Client', sortable: true },
    { key: 'budget', label: 'Budget', sortable: true },
  ]
  const rows = [
    { id: '1', name: 'Kouassi', budget: 3_000_000 },
    { id: '2', name: 'Ahoua', budget: 12_000_000 },
    { id: '3', name: 'Élodie', budget: 800_000 },
  ]
  const names = (wrapper: ReturnType<typeof mount>) =>
    wrapper.findAll('tbody tr').map((row) => row.find('td').text())

  it('sorts with French collation, then reverses', async () => {
    const wrapper = mount(WTable, {
      props: { columns, rows, rowKey: 'id', caption: 'Clients' },
      global,
    })
    const header = wrapper.findAll('thead button')[0]!

    await header.trigger('click')
    expect(names(wrapper)).toEqual(['Ahoua', 'Élodie', 'Kouassi'])
    expect(wrapper.find('th').attributes('aria-sort')).toBe('ascending')

    await header.trigger('click')
    expect(names(wrapper)).toEqual(['Kouassi', 'Élodie', 'Ahoua'])
  })

  it('sorts numbers numerically and paginates', async () => {
    const wrapper = mount(WTable, {
      props: { columns, rows, rowKey: 'id', caption: 'Clients', pageSize: 2 },
      global,
    })
    await wrapper.findAll('thead button')[1]!.trigger('click')

    expect(names(wrapper)).toEqual(['Élodie', 'Kouassi'])
    expect(wrapper.text()).toContain('Page 1 sur 2')
  })

  it('shows an empty message', () => {
    const wrapper = mount(WTable, {
      props: { columns, rows: [], rowKey: 'id', caption: 'Vide' },
      global,
    })
    expect(wrapper.text()).toContain('Aucun élément à afficher.')
  })
})

describe('WTabs', () => {
  it('moves selection with the arrow keys', async () => {
    const tabs = [
      { key: 'draft', label: 'Brouillons' },
      { key: 'sent', label: 'Envoyés', count: 4 },
    ]
    const wrapper = mount(WTabs, { props: { tabs, label: 'Statut', modelValue: 'draft' } })
    await wrapper.findAll('[role="tab"]')[0]!.trigger('keydown', { key: 'ArrowRight' })

    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['sent'])
  })
})

describe('WModal', () => {
  it('traps the dialog role and closes on Escape', async () => {
    const open = ref(true)
    mount(
      defineComponent(
        () => () =>
          h(
            WModal,
            {
              title: 'Nouveau client',
              open: open.value,
              'onUpdate:open': (v: boolean) => (open.value = v),
            },
            () => h('button', 'Enregistrer'),
          ),
      ),
      { attachTo: document.body, global },
    )
    await nextTick()
    const dialog = document.querySelector('[role="dialog"]') as HTMLElement

    expect(dialog.getAttribute('aria-modal')).toBe('true')
    expect(document.body.style.overflow).toBe('hidden')
    dialog.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await nextTick()
    expect(open.value).toBe(false)
  })
})

describe('WCommandPalette', () => {
  it('filters accent-insensitively and runs the active item on Enter', async () => {
    const run = vi.fn()
    mount(WCommandPalette, {
      props: {
        open: true,
        items: [
          { id: 'a', label: 'Tableau de bord', group: 'Pages', run: vi.fn() },
          { id: 'b', label: 'Paramètres', group: 'Pages', run },
        ],
      },
      attachTo: document.body,
      global,
    })
    await nextTick()
    const input = document.querySelector('input') as HTMLInputElement
    input.value = 'parametres'
    input.dispatchEvent(new Event('input'))
    await nextTick()

    expect(document.querySelectorAll('[role="option"]')).toHaveLength(1)
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
    expect(run).toHaveBeenCalledOnce()
  })
})

describe('WToast', () => {
  it('renders toasts pushed from anywhere, errors as alerts', async () => {
    vi.useFakeTimers()
    const wrapper = mount(WToast, { global })
    const toast = useToast()
    toast.success('Devis envoyé')
    toast.error('Le montant dépasse le solde restant.')
    await flushPromises()

    expect(wrapper.text()).toContain('Devis envoyé')
    expect(wrapper.get('[role="alert"]').text()).toContain('solde restant')
    vi.advanceTimersByTime(10_000)
    await flushPromises()
    expect(wrapper.text()).not.toContain('Devis envoyé')
    vi.useRealTimers()
  })
})

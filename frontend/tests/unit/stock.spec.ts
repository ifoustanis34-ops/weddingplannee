import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import { i18n } from '@/i18n'
import ItemCard from '@/modules/stock/components/ItemCard.vue'
import StockBar from '@/modules/stock/components/StockBar.vue'
import type { Item } from '@/modules/stock/types'

const global = { plugins: [i18n] }

const item: Item = {
  id: 'i1',
  reference: 'MOB-002',
  name: 'Chaise Chiavari transparente',
  category: 'c1',
  categoryName: 'Mobilier',
  photoUrl: null,
  description: '',
  location: 'Allée 1',
  tracking: 'quantity',
  totalQuantity: 250,
  partnerQuantity: 0,
  rentPrice: 2000,
  rentUnit: 'event',
  salePrice: null,
  purchaseCost: null,
  deposit: 500,
  alertThreshold: 40,
  cleaningDays: null,
  delayDays: 0,
  isActive: true,
  today: { total: 250, available: 30, reserved: 200, out: 0, maintenance: 20, outOfService: 0 },
  stockValue: null,
  createdAt: '',
}

describe('StockBar', () => {
  it('splits by status and says it for screen readers', () => {
    const wrapper = mount(StockBar, {
      props: { available: 30, reserved: 200, out: 0, maintenance: 20 },
      global,
    })
    const parts = wrapper.findAll('span')
    expect(parts).toHaveLength(3) // empty parts are not drawn
    expect(parts[0]!.attributes('style')).toContain('width: 12%')
    expect(wrapper.attributes('aria-label')).toBe('Disponible 30, Réservé 200, Maintenance 20')
  })
})

describe('ItemCard', () => {
  it('shows what is available today and flags the alert threshold', () => {
    const wrapper = mount(ItemCard, { props: { item }, global })

    expect(wrapper.text()).toContain('30 disponibles sur 250')
    expect(wrapper.find('.text-coral').exists()).toBe(true) // 30 ≤ threshold 40
    expect(wrapper.text()).toMatch(/2\s000 \/ événement/)
  })

  it('shows no price to the storekeeper (the API sends none)', () => {
    const wrapper = mount(ItemCard, { props: { item: { ...item, rentPrice: null } }, global })

    expect(wrapper.text()).not.toContain('/ événement')
  })
})

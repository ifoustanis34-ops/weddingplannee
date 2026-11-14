import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { h, nextTick, ref } from 'vue'

import {
  WAreaChart,
  WAvatar,
  WChannelIcon,
  WChips,
  WCommandPalette,
  WDateBlock,
  WInput,
  WLogo,
  WTile,
} from '@/design'
import { areaChartGeometry, CHART_BOTTOM, niceStep } from '@/design/components/areaChart'
import { i18n } from '@/i18n'

const global = { plugins: [i18n] }

// Prototype cash-in curve (complement §7): mai 3,2 M … oct. 6,3 M.
const CASHFLOW = [3_200_000, 4_100_000, 2_800_000, 5_600_000, 4_900_000, 6_300_000]

describe('areaChartGeometry', () => {
  it('draws the prototype grid at 0, 2, 4 and 6 million', () => {
    const { ticks } = areaChartGeometry(CASHFLOW)
    expect(ticks.map((tick) => tick.value)).toEqual([0, 2_000_000, 4_000_000, 6_000_000])
    expect(ticks[0]?.y).toBe(CHART_BOTTOM)
  })

  it('places the first and last points 34px from the edges, highest value on top', () => {
    const { points } = areaChartGeometry(CASHFLOW)
    expect(points[0]?.x).toBe(34)
    expect(points[5]?.x).toBe(566)
    const lowest = Math.max(...points.map((p) => p.y))
    expect(points[2]?.y).toBe(lowest) // juillet, 2,8 M
    expect(points[5]?.y).toBe(Math.min(...points.map((p) => p.y)))
  })

  it('puts both control points of a segment at its horizontal middle', () => {
    const { line, points } = areaChartGeometry([0, 10])
    const [a, b] = points
    expect(line).toBe(`M34 ${a?.y} C300 ${a?.y} 300 ${b?.y} 566 ${b?.y}`)
  })

  it('closes the area on the baseline', () => {
    const { area } = areaChartGeometry([1, 2, 3])
    expect(area.endsWith(`L566 ${CHART_BOTTOM} L34 ${CHART_BOTTOM} Z`)).toBe(true)
  })

  it('stays drawable with no money collected', () => {
    const { ticks, points } = areaChartGeometry([0, 0, 0])
    expect(ticks).toHaveLength(1)
    expect(points.every((p) => p.y === CHART_BOTTOM)).toBe(true)
  })

  it('rounds grid steps to 1, 2 or 5 × 10ⁿ', () => {
    expect(niceStep(6_300_000)).toBe(2_000_000)
    expect(niceStep(14_000_000)).toBe(5_000_000)
    expect(niceStep(2_500)).toBe(1_000)
  })
})

describe('WAreaChart', () => {
  it('labels the last point and exposes an accessible summary', () => {
    const wrapper = mount(WAreaChart, {
      props: {
        points: CASHFLOW.map((value, i) => ({ label: `m${i}`, value })),
        label: 'Encaissements par mois',
        formatValue: (v: number) => `${v / 1_000_000} M`,
      },
    })
    expect(wrapper.get('svg').attributes('aria-label')).toBe('Encaissements par mois')
    expect(wrapper.get('[data-testid="area-chart-last"]').text()).toBe('6.3 M')
    expect(wrapper.findAll('circle')).toHaveLength(6)
    expect(wrapper.findAll('line[stroke-dasharray="3 5"]')).toHaveLength(3)
  })
})

describe('WAvatar', () => {
  it.each([
    ['Freddy Kouamé', 'FK'],
    ['Aïcha & Serge Kouassi', 'AK'],
    ['awa', 'A'],
    ['Élodie N’Dri', 'ÉN'],
  ])('shows the initials of %s', (name, initials) => {
    expect(mount(WAvatar, { props: { name } }).text()).toBe(initials)
  })

  it('uses a rounded hero square for an organisation', () => {
    const wrapper = mount(WAvatar, { props: { name: 'Maison Élégance', kind: 'organization' } })
    expect(wrapper.classes()).toContain('bg-hero')
  })
})

describe('WDateBlock', () => {
  it('shows the day and the abbreviated month without shifting the date', () => {
    const wrapper = mount(WDateBlock, { props: { date: '2026-10-31' } })
    expect(wrapper.findAll('span').map((span) => span.text())).toEqual(['31', 'oct.'])
    expect(wrapper.get('time').attributes('datetime')).toBe('2026-10-31')
  })

  it('can show the weekday instead', () => {
    const wrapper = mount(WDateBlock, { props: { date: '2026-11-14', weekday: true } })
    expect(wrapper.text()).toContain('sam.')
  })
})

describe('WChips', () => {
  it('marks the active chip and selects another on click', async () => {
    const value = ref<string | number>('all')
    const wrapper = mount(() =>
      h(WChips, {
        label: 'Catégories',
        modelValue: value.value,
        options: [
          { value: 'all', label: 'Tous' },
          { value: 'deco', label: 'Décoration' },
        ],
        'onUpdate:modelValue': (next: string | number) => (value.value = next),
      }),
    )
    const [all, deco] = wrapper.findAll('button')
    expect(all?.attributes('aria-pressed')).toBe('true')
    await deco?.trigger('click')
    expect(value.value).toBe('deco')
    expect(deco?.attributes('aria-pressed')).toBe('true')
    expect(deco?.classes()).toContain('bg-ink')
  })
})

describe('WInput addon', () => {
  it('renders the grey suffix inside the field frame', () => {
    const wrapper = mount(WInput, { props: { label: 'Adresse', addon: '.wedivo.pro' } })
    expect(wrapper.text()).toContain('.wedivo.pro')
    expect(wrapper.get('input').classes()).toContain('border-0')
  })
})

describe('WTile', () => {
  it('uses the hero background in its dark variant', () => {
    const wrapper = mount(WTile, { props: { label: 'Solde à recevoir', value: '1 M', dark: true } })
    expect(wrapper.classes()).toContain('bg-hero')
    expect(wrapper.text()).toContain('Solde à recevoir')
  })
})

describe('WLogo', () => {
  it('keeps the name readable for screen readers', () => {
    const wrapper = mount(WLogo)
    expect(wrapper.get('.sr-only').text()).toBe('Wedivo')
    expect(wrapper.get('img').attributes('alt')).toBe('')
  })
})

describe('WChannelIcon', () => {
  it('is decorative unless labelled', () => {
    expect(mount(WChannelIcon, { props: { channel: 'email' } }).attributes('aria-hidden')).toBe(
      'true',
    )
    const labelled = mount(WChannelIcon, { props: { channel: 'whatsapp', label: 'WhatsApp' } })
    expect(labelled.attributes('role')).toBe('img')
    expect(labelled.classes()).toContain('bg-green-soft')
  })
})

describe('WCommandPalette groups', () => {
  afterEach(() => (document.body.innerHTML = ''))

  it('groups results under a heading and shows 12 at most', async () => {
    const items = Array.from({ length: 20 }, (_, i) => ({
      id: `p${i}`,
      label: `Client ${i}`,
      group: i % 2 ? 'Clients' : 'Pages',
      run: vi.fn(),
    }))
    mount(WCommandPalette, { props: { open: true, items }, attachTo: document.body, global })
    await nextTick()

    const options = document.querySelectorAll('[role="option"]')
    expect(options).toHaveLength(12)
    const headings = [...document.querySelectorAll('[role="presentation"]')].map((el) =>
      el.textContent?.trim(),
    )
    expect(headings).toEqual(['Pages', 'Clients'])
    expect(options[0]?.getAttribute('aria-selected')).toBe('true')
  })
})

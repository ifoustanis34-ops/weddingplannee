import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { h, nextTick, ref } from 'vue'

import { WBadge, WButton, WInput, WProgress, WSwitch } from '@/design'
import { i18n } from '@/i18n'

const global = { plugins: [i18n] }

describe('WButton', () => {
  it('disables itself and announces work while loading', () => {
    const wrapper = mount(WButton, {
      props: { loading: true },
      slots: { default: 'Envoyer' },
      global,
    })
    const button = wrapper.get('button')

    expect(button.attributes('disabled')).toBeDefined()
    expect(button.attributes('aria-busy')).toBe('true')
  })

  it('uses the primary violet style by default', () => {
    const wrapper = mount(WButton, { slots: { default: 'OK' }, global })
    expect(wrapper.get('button').classes()).toContain('bg-violet')
  })
})

describe('WInput', () => {
  it('binds v-model and links the label', async () => {
    const value = ref('')
    const wrapper = mount(() =>
      h(WInput, {
        label: 'Ville',
        modelValue: value.value,
        'onUpdate:modelValue': (v: unknown) => (value.value = String(v)),
      }),
    )
    await wrapper.get('input').setValue('Abidjan')

    expect(value.value).toBe('Abidjan')
    expect(wrapper.get('label').attributes('for')).toBe(wrapper.get('input').attributes('id'))
  })

  it('exposes the error to assistive technologies', () => {
    const wrapper = mount(WInput, {
      props: { label: 'Email', error: 'Saisissez un email valide.' },
    })
    const input = wrapper.get('input')

    expect(input.attributes('aria-invalid')).toBe('true')
    expect(wrapper.get(`#${input.attributes('aria-describedby')}`).text()).toBe(
      'Saisissez un email valide.',
    )
  })
})

describe('WSwitch', () => {
  it('toggles and reflects aria-checked', async () => {
    const wrapper = mount(WSwitch, { props: { label: 'Résumé quotidien', modelValue: false } })
    await wrapper.get('[role="switch"]').trigger('click')

    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([true])
  })
})

describe('WBadge', () => {
  it('uses the tone colour', () => {
    expect(mount(WBadge, { props: { tone: 'green' } }).classes()).toContain('text-green')
    expect(mount(WBadge, { props: { tone: 'fuchsia' } }).classes()).toContain('text-fuchsia')
  })
})

describe('WProgress', () => {
  it('clamps the value and uses the ribbon only on request', async () => {
    const wrapper = mount(WProgress, { props: { value: 140, label: 'Avancement', ribbon: true } })
    await nextTick()

    expect(wrapper.get('[role="progressbar"]').attributes('aria-valuenow')).toBe('100')
    expect(wrapper.find('.bg-ribbon').exists()).toBe(true)
  })
})

import { describe, expect, it } from 'vitest'

import fr from '@/i18n/fr'
import { SCENARIOS, scenarioSeconds, stepDuration } from '@/modules/presentation/scenarios'

type Tree = Record<string, unknown>
const at = (path: string): unknown =>
  path.split('.').reduce<unknown>((node, key) => (node as Tree | undefined)?.[key], fr as Tree)

describe('presentation scenarios', () => {
  it('have a title, a description and a narration for every step', () => {
    for (const scenario of SCENARIOS) {
      const base = `presentation.scenarios.${scenario.id}`
      expect(typeof at(`${base}.title`), base).toBe('string')
      expect(typeof at(`${base}.description`), base).toBe('string')
      for (const step of scenario.steps) {
        expect(typeof at(`${base}.steps.${step.key}.title`), `${base}.${step.key}`).toBe('string')
        expect(typeof at(`${base}.steps.${step.key}.text`), `${base}.${step.key}`).toBe('string')
      }
    }
  })

  it('start with the role they show, so the point of view is right from step one', () => {
    for (const scenario of SCENARIOS) expect(scenario.steps[0]?.role, scenario.id).toBeDefined()
  })

  it('scale the display time with the speed', () => {
    const step = { key: 'x', route: '/', duration: 6000 }
    expect(stepDuration(step, 1)).toBe(6000)
    expect(stepDuration(step, 1.5)).toBe(4000)
    expect(scenarioSeconds({ id: 'x', icon: 'wallet', roles: [], steps: [step, step] })).toBe(12)
  })
})

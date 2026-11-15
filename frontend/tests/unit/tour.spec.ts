import { describe, expect, it } from 'vitest'

import type { Role } from '@/api/auth'
import { tourSteps } from '@/app/tour'
import fr from '@/i18n/fr'

const ROLES: Role[] = [
  'owner',
  'planner',
  'assistant',
  'accountant',
  'storekeeper',
  'team_lead',
  'staff',
]

function text(key: string): unknown {
  const steps = fr.tour.steps as Record<string, { text?: string } | undefined>
  return steps[key]?.text
}

// Guided tour (feedback 15/11/2026): every step of every role has its explanation.
describe('guided tour', () => {
  it.each(ROLES)('explains every step shown to the role %s', (role) => {
    const steps = tourSteps(role, true)
    expect(steps[0]?.key).toBe('welcome')
    expect(steps.at(-1)?.key).toBe('end')
    expect(steps.filter((step) => !text(step.key)).map((step) => step.key)).toEqual([])
  })

  it('only shows the modules the role opens, page by page', () => {
    const owner = tourSteps('owner', true).map((step) => step.key)
    const storekeeper = tourSteps('storekeeper', true).map((step) => step.key)
    const staff = tourSteps('staff', true).map((step) => step.key)

    expect(owner).toEqual(expect.arrayContaining(['finance', 'pay', 'settings', 'stock']))
    expect(storekeeper).toContain('stock')
    expect(storekeeper).not.toContain('finance')
    expect(staff).toEqual(expect.arrayContaining(['mySpace', 'missions']))
    expect(staff).not.toContain('settings')
    expect(tourSteps('owner', false).map((step) => step.key)).not.toContain('weddings')
    expect(tourSteps('owner', true).find((step) => step.key === 'stock')).toMatchObject({
      routeName: 'stock',
      target: 'stock',
    })
  })
})

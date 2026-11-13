import { describe, expect, it } from 'vitest'

import type { Mission } from '@/modules/staff/api'
import { groupMissions, taskProgress } from '@/modules/staff/missions'

const mission = (id: string, start: string, state: Mission['state'] = 'upcoming') =>
  ({ id, start, state }) as Mission
const day = (instant: string) => instant.slice(0, 10)

describe('groupMissions', () => {
  it('sorts missions into today, tomorrow, week, later and done', () => {
    const groups = groupMissions(
      [
        mission('later', '2026-11-25T09:00:00Z'),
        mission('tomorrow', '2026-11-14T09:00:00Z'),
        mission('running', '2026-11-12T09:00:00Z', 'in_progress'),
        mission('week', '2026-11-17T09:00:00Z'),
        mission('old', '2026-11-05T09:00:00Z', 'done'),
        mission('recent', '2026-11-10T09:00:00Z', 'done'),
        mission('today', '2026-11-13T15:00:00Z'),
      ],
      '2026-11-13',
      day,
    )
    expect(groups.map((g) => [g.key, g.items.map((m) => m.id)])).toEqual([
      ['today', ['running', 'today']],
      ['tomorrow', ['tomorrow']],
      ['week', ['week']],
      ['later', ['later']],
      ['done', ['recent', 'old']],
    ])
  })

  it('leaves out empty groups', () => {
    expect(groupMissions([], '2026-11-13', day)).toEqual([])
  })
})

describe('taskProgress', () => {
  it('counts done and validated tasks', () => {
    expect(taskProgress([{ status: 'todo' }, { status: 'done' }, { status: 'validated' }])).toEqual(
      { done: 2, total: 3 },
    )
  })
})

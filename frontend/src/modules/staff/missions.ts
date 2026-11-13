import type { Mission } from './api'

/**
 * « Mes missions » in order (feedback 13/11/2026): what is on today (or still running), tomorrow,
 * the rest of the week, later, then what was done recently. `day` is the agency's calendar day of
 * an instant (`YYYY-MM-DD`), given by the caller so this stays pure and testable.
 */
export type MissionGroupKey = 'today' | 'tomorrow' | 'week' | 'later' | 'done'
export interface MissionGroup {
  key: MissionGroupKey
  items: Mission[]
}

const addDays = (iso: string, days: number): string => {
  const date = new Date(`${iso}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

export function groupMissions(
  missions: Mission[],
  today: string,
  day: (instant: string) => string,
): MissionGroup[] {
  const groups: Record<MissionGroupKey, Mission[]> = {
    today: [],
    tomorrow: [],
    week: [],
    later: [],
    done: [],
  }
  const tomorrow = addDays(today, 1)
  const weekEnd = addDays(today, 7)
  for (const mission of missions) {
    const start = day(mission.start)
    if (mission.state === 'done') groups.done.push(mission)
    else if (mission.state === 'in_progress' || start <= today) groups.today.push(mission)
    else if (start === tomorrow) groups.tomorrow.push(mission)
    else if (start < weekEnd) groups.week.push(mission)
    else groups.later.push(mission)
  }
  const byStart = (a: Mission, b: Mission) => a.start.localeCompare(b.start)
  groups.done.sort((a, b) => byStart(b, a)) // the most recent first
  return (Object.keys(groups) as MissionGroupKey[])
    .map((key) => ({ key, items: key === 'done' ? groups.done : groups[key].sort(byStart) }))
    .filter((group) => group.items.length)
}

/** Share of the tasks done (validated included), for the small progress bar of a mission. */
export function taskProgress(tasks: { status: string }[]): { done: number; total: number } {
  return { done: tasks.filter((t) => t.status !== 'todo').length, total: tasks.length }
}

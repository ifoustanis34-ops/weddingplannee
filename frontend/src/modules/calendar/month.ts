/** Calendar date maths (complement §11, reservations-stock.md §4.3). Pure, unit-tested. */

export const iso = (date: Date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

/** Local midnight of a `YYYY-MM-DD` day (never UTC: no shift in Abidjan or Paris). */
export function fromIso(value: string): Date {
  const [y, m, d] = value.split('-').map(Number)
  return new Date(y!, m! - 1, d)
}

export function addDays(date: Date, days: number): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + days)
}

/** Whole days from `a` to `b` (both `YYYY-MM-DD`), daylight saving aside. */
export function daysBetween(a: string, b: string): number {
  return Math.round((fromIso(b).getTime() - fromIso(a).getTime()) / 86_400_000)
}

export function parseMonth(value: unknown, today = new Date()): { year: number; month: number } {
  const match = typeof value === 'string' ? /^(\d{4})-(\d{2})$/.exec(value) : null
  if (match) {
    const month = Number(match[2]) - 1
    if (month >= 0 && month <= 11) return { year: Number(match[1]), month }
  }
  return { year: today.getFullYear(), month: today.getMonth() }
}

export function parseDay(value: unknown, today = new Date()): Date {
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const date = fromIso(value)
    if (!Number.isNaN(date.getTime()) && iso(date) === value) return date
  }
  return new Date(today.getFullYear(), today.getMonth(), today.getDate())
}

export function monthKey(year: number, month: number): string {
  const date = new Date(year, month, 1)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
}

/** Monday on or before `date`. */
export function weekStart(date: Date): Date {
  return addDays(date, -((date.getDay() + 6) % 7))
}

/** The 42 days shown for a month, from the Monday on or before the 1st. */
export function monthDays(year: number, month: number): Date[] {
  const start = weekStart(new Date(year, month, 1))
  return Array.from({ length: 42 }, (_, i) => addDays(start, i))
}

export const VIEWS = ['mois', 'semaine', 'jour', 'liste', 'logistique'] as const
export type CalendarView = (typeof VIEWS)[number]

/** Days shown by a view around its anchor day. */
export function viewDays(view: CalendarView, anchor: Date): Date[] {
  const span = (start: Date, length: number) => Array.from({ length }, (_, i) => addDays(start, i))
  switch (view) {
    case 'mois':
      return monthDays(anchor.getFullYear(), anchor.getMonth())
    case 'semaine':
      return span(weekStart(anchor), 7)
    case 'jour':
      return [anchor]
    case 'liste': {
      const first = new Date(anchor.getFullYear(), anchor.getMonth(), 1)
      const last = new Date(anchor.getFullYear(), anchor.getMonth() + 1, 0)
      return span(first, last.getDate())
    }
    case 'logistique':
      return span(weekStart(anchor), 14)
  }
}

/** The anchor after « previous » (-1) or « next » (+1). */
export function shiftAnchor(view: CalendarView, anchor: Date, step: -1 | 1): Date {
  switch (view) {
    case 'mois':
    case 'liste':
      return new Date(anchor.getFullYear(), anchor.getMonth() + step, 1)
    case 'semaine':
      return addDays(anchor, 7 * step)
    case 'jour':
      return addDays(anchor, step)
    case 'logistique':
      return addDays(anchor, 14 * step)
  }
}

/** Items by day; a multi-day item shows on each of its days inside the range. */
export function groupByDay<T extends { date: string; endDate?: string | null }>(
  items: T[],
  days: Date[],
): Map<string, T[]> {
  const map = new Map<string, T[]>(days.map((d) => [iso(d), []]))
  const first = iso(days[0]!)
  const last = iso(days[days.length - 1]!)
  for (const item of items) {
    const end = item.endDate && item.endDate > item.date ? item.endDate : item.date
    let day = item.date < first ? first : item.date
    while (day <= end && day <= last) {
      map.get(day)?.push(item)
      day = iso(addDays(fromIso(day), 1))
    }
  }
  return map
}

import { describe, expect, it } from 'vitest'

import { useDropDay } from '@/modules/calendar/components/useDropDay'
import { DRAG_TYPE, readDrop } from '@/modules/calendar/kinds'
import {
  daysBetween,
  groupByDay,
  iso,
  parseDay,
  shiftAnchor,
  viewDays,
} from '@/modules/calendar/month'

/** A DragEvent stand-in: jsdom has no DataTransfer. */
function dragEvent(data: Record<string, string>) {
  let prevented = false
  return {
    event: {
      dataTransfer: {
        types: Object.keys(data),
        getData: (type: string) => data[type] ?? '',
        dropEffect: 'none',
      },
      preventDefault: () => {
        prevented = true
      },
    } as unknown as DragEvent,
    prevented: () => prevented,
  }
}

describe('calendar views', () => {
  const thursday = new Date(2026, 10, 12) // 12 Nov 2026

  it('spans each view from its anchor', () => {
    expect(viewDays('mois', thursday)).toHaveLength(42)
    expect(iso(viewDays('mois', thursday)[0]!)).toBe('2026-10-26') // Monday before 1 Nov
    expect(viewDays('semaine', thursday).map(iso)).toEqual([
      '2026-11-09',
      '2026-11-10',
      '2026-11-11',
      '2026-11-12',
      '2026-11-13',
      '2026-11-14',
      '2026-11-15',
    ])
    expect(viewDays('jour', thursday).map(iso)).toEqual(['2026-11-12'])
    expect(viewDays('liste', thursday)).toHaveLength(30)
    const logistics = viewDays('logistique', thursday)
    expect([iso(logistics[0]!), iso(logistics[13]!)]).toEqual(['2026-11-09', '2026-11-22'])
  })

  it('moves the anchor by the size of the view', () => {
    expect(iso(shiftAnchor('mois', thursday, 1))).toBe('2026-12-01')
    expect(iso(shiftAnchor('liste', new Date(2026, 0, 31), -1))).toBe('2025-12-01')
    expect(iso(shiftAnchor('semaine', thursday, -1))).toBe('2026-11-05')
    expect(iso(shiftAnchor('jour', thursday, 1))).toBe('2026-11-13')
    expect(iso(shiftAnchor('logistique', thursday, 1))).toBe('2026-11-26')
  })

  it('reads a day from the address, today otherwise', () => {
    expect(iso(parseDay('2026-02-28'))).toBe('2026-02-28')
    expect(iso(parseDay('2026-02-30', thursday))).toBe('2026-11-12')
    expect(iso(parseDay(undefined, thursday))).toBe('2026-11-12')
    expect(daysBetween('2026-10-30', '2026-11-02')).toBe(3)
    expect(daysBetween('2026-11-02', '2026-10-30')).toBe(-3)
  })

  it('shows a multi-day item on each of its days inside the range', () => {
    const days = viewDays('semaine', thursday)
    const map = groupByDay(
      [
        { id: 'a', date: '2026-11-07', endDate: '2026-11-10' }, // starts before the week
        { id: 'b', date: '2026-11-15', endDate: '2026-11-18' }, // ends after it
        { id: 'c', date: '2026-11-12', endDate: null },
      ],
      days,
    )
    expect(map.get('2026-11-09')!.map((i) => i.id)).toEqual(['a'])
    expect(map.get('2026-11-10')!.map((i) => i.id)).toEqual(['a'])
    expect(map.get('2026-11-11')).toEqual([])
    expect(map.get('2026-11-12')!.map((i) => i.id)).toEqual(['c'])
    expect(map.get('2026-11-15')!.map((i) => i.id)).toEqual(['b'])
  })
})

describe('drag to move', () => {
  const payload = JSON.stringify({ reservation: 'r1', date: '2026-11-12' })

  it('accepts only a dragged reservation and sends the shift in days', () => {
    const moves: unknown[] = []
    const drop = useDropDay((request) => moves.push(request))

    const foreign = dragEvent({ 'text/plain': 'hello' })
    drop.dragover(foreign.event, '2026-11-14')
    expect(foreign.prevented()).toBe(false) // a file or a text cannot land here

    const ours = dragEvent({ [DRAG_TYPE]: payload })
    drop.dragover(ours.event, '2026-11-14')
    expect(ours.prevented()).toBe(true)
    expect(drop.over.value).toBe('2026-11-14')
    drop.drop(ours.event, '2026-11-14')
    expect(moves).toEqual([{ reservation: 'r1', days: 2, to: '2026-11-14' }])
    expect(drop.over.value).toBeNull()

    drop.drop(dragEvent({ [DRAG_TYPE]: payload }).event, '2026-11-12') // same day: nothing
    expect(moves).toHaveLength(1)
  })

  it('ignores malformed data', () => {
    expect(readDrop(dragEvent({ [DRAG_TYPE]: '{"reservation": 3}' }).event)).toBeNull()
    expect(readDrop(dragEvent({ [DRAG_TYPE]: 'not json' }).event)).toBeNull()
  })
})

describe('dates typed in the agency’s zone', () => {
  it('reads and shows a datetime-local value in that zone, whatever the browser', async () => {
    const { fromZonedInput, toZonedInput } = await import('@/composables/useDate')
    expect(fromZonedInput('2026-11-14T15:00', 'Africa/Abidjan')).toBe('2026-11-14T15:00:00.000Z')
    expect(fromZonedInput('2026-11-14T15:00', 'Africa/Douala')).toBe('2026-11-14T14:00:00.000Z')
    expect(toZonedInput('2026-11-14T14:00:00Z', 'Africa/Douala')).toBe('2026-11-14T15:00')
    // Paris in summer (UTC+2) and across the October change.
    expect(fromZonedInput('2026-07-01T10:00', 'Europe/Paris')).toBe('2026-07-01T08:00:00.000Z')
    expect(toZonedInput('2026-10-25T12:00:00Z', 'Europe/Paris')).toBe('2026-10-25T13:00')
    expect(fromZonedInput('', 'Africa/Abidjan')).toBeNull()
  })
})

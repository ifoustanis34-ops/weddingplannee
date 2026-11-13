/** French dates in the organization's time zone (default Africa/Abidjan). */

export const DEFAULT_TIMEZONE = 'Africa/Abidjan'

/** The signed-in agency's zone (Paramètres › Entreprise), set by the app shell once the
 *  organization is loaded: every date of the app follows it (Douala is UTC+1, Abidjan UTC+0). */
let agencyZone = DEFAULT_TIMEZONE
export function setAgencyTimezone(zone: string | null | undefined): void {
  agencyZone = zone || DEFAULT_TIMEZONE
}
export const agencyTimezone = () => agencyZone

type DateInput = Date | string | number

const toDate = (value: DateInput): Date => (value instanceof Date ? value : new Date(value))

/** `2026-11-14` → `14 nov. 2026` */
export function formatDate(value: DateInput, timeZone = agencyTimezone()): string {
  return new Intl.DateTimeFormat('fr-FR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone,
  }).format(toDate(value))
}

/** `14 nov. 2026 à 18:30` */
export function formatDateTime(value: DateInput, timeZone = agencyTimezone()): string {
  const date = toDate(value)
  const time = new Intl.DateTimeFormat('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone,
  }).format(date)
  return `${formatDate(date, timeZone)} à ${time}`
}

/** Whole calendar days from `from` to `to` in the given zone (J-x countdowns). */
export function daysBetween(from: DateInput, to: DateInput, timeZone = agencyTimezone()): number {
  const day = (value: DateInput) => {
    const parts = new Intl.DateTimeFormat('en-CA', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      timeZone,
    }).format(toDate(value))
    return Date.parse(`${parts}T00:00:00Z`)
  }
  return Math.round((day(to) - day(from)) / 86_400_000)
}

export function useDate(timeZone: () => string = agencyTimezone) {
  return {
    formatDate: (value: DateInput) => formatDate(value, timeZone()),
    formatDateTime: (value: DateInput) => formatDateTime(value, timeZone()),
    daysUntil: (value: DateInput) => daysBetween(new Date(), value, timeZone()),
  }
}

/** Minutes the zone is ahead of UTC at that instant. */
function offsetMinutes(instant: number, timeZone: string): number {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat('en-US', {
      timeZone,
      hourCycle: 'h23',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
      .formatToParts(new Date(instant))
      .map((part) => [part.type, part.value]),
  )
  const wall = Date.UTC(
    Number(parts.year),
    Number(parts.month) - 1,
    Number(parts.day),
    Number(parts.hour),
    Number(parts.minute),
  )
  return Math.round((wall - Math.floor(instant / 60_000) * 60_000) / 60_000)
}

/** An instant as a `datetime-local` value (`2026-11-14T15:00`) in the agency's zone. */
export function toZonedInput(
  value: string | null | undefined,
  timeZone = agencyTimezone(),
): string {
  if (!value) return ''
  const instant = new Date(value).getTime()
  if (Number.isNaN(instant)) return ''
  return new Date(instant + offsetMinutes(instant, timeZone) * 60_000).toISOString().slice(0, 16)
}

/** A `datetime-local` value read in the agency's zone, as an ISO instant (whatever the
 *  browser's zone: a planner abroad books the right hour). */
export function fromZonedInput(value: string, timeZone = agencyTimezone()): string | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(value)
  if (!match) return null
  const [, y, m, d, h, min] = match.map(Number)
  const wall = Date.UTC(y!, m! - 1, d, h, min)
  let instant = wall - offsetMinutes(wall, timeZone) * 60_000
  const corrected = wall - offsetMinutes(instant, timeZone) * 60_000 // daylight saving edge
  if (corrected !== instant) instant = corrected
  return new Date(instant).toISOString()
}

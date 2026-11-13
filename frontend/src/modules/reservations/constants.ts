import type { BadgeTone } from '@/design'

import type { ReservationStatus } from './types'

/** Status badges (§4.1), consistent with the design system: preparation and logistics in
 *  violet, installation in fuchsia (calendar colors §4.3), money waiting in gold. */
export const STATUS_TONES: Record<ReservationStatus, BadgeTone> = {
  draft: 'grey',
  quote_sent: 'fuchsia',
  awaiting_deposit: 'gold',
  confirmed: 'green',
  preparing: 'violet',
  delivered: 'violet',
  installed: 'fuchsia',
  in_progress: 'coral',
  picked_up: 'coral',
  closed: 'grey',
  cancelled: 'red',
}

/** Logistic steps of the timeline, in order. */
export const STEPS = [
  'delivery_at',
  'setup_at',
  'event_start',
  'event_end',
  'teardown_at',
  'pickup_at',
  'return_at',
] as const

export const TABS = [
  'all',
  'drafts',
  'awaiting_deposit',
  'confirmed',
  'ongoing',
  'closed',
  'cancelled',
] as const

export const METHODS = ['orange_money', 'mtn_momo', 'wave', 'cash', 'transfer', 'cheque'] as const

export const EDITABLE: ReservationStatus[] = [
  'draft',
  'quote_sent',
  'awaiting_deposit',
  'confirmed',
  'preparing',
]
export const OUT: ReservationStatus[] = ['delivered', 'installed', 'in_progress', 'picked_up']

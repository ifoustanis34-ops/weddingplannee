import type { BadgeTone } from '@/design'

import type { QuoteStatus } from './types'

export const STATUS_TONES: Record<QuoteStatus, BadgeTone> = {
  draft: 'grey',
  sent: 'violet',
  accepted: 'green',
  refused: 'red',
  expired: 'grey',
}

export const QUOTE_TABS = [
  'all',
  'draft',
  'sent',
  'accepted',
  'refused',
  'expired',
  'templates',
] as const
export type QuoteTab = (typeof QUOTE_TABS)[number]

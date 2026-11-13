/** Guests and tickets of a wedding (docs/specs/devis-billets.md §6). */
export interface TicketDesign {
  id: string
  palette: string
  partner1: string
  partner2: string
  title: string
  subtitle: string
  intro: string
  panelText: string
  bottomSlogan: string
  scriptLine: string
  startsAt: string | null
  /** « 2027-06-12T15:00 » in the agency's time zone (what the ticket prints). */
  startsAtLocal: string | null
  venue: string
  address: string
  dressCode: string
  stubTitle: string
  stubSubtitle: string
  stubScript: string
  stubFooter: string
  showMonogram: boolean
  categories: string[]
  updatedAt: string
}

export type TicketDesignInput = Partial<Omit<TicketDesign, 'id' | 'updatedAt' | 'startsAt'>>

export interface TicketSummary {
  id: string
  code: string
  status: 'active' | 'cancelled' | 'reissued'
  issuedAt: string
  sentAt: string | null
  openedAt: string | null
  cancelledAt: string | null
  hasDocument: boolean
  /** The guest's link (signed), only for a valid ticket. */
  url: string | null
}

/** One status per guest in the list: from « non généré » to « confirmé » (§6). */
export type TicketState =
  'none' | 'generated' | 'sent' | 'opened' | 'confirmed' | 'declined' | 'cancelled'

export interface Guest {
  id: string
  name: string
  email: string
  phone: string
  seats: number
  category: string
  table: string
  notes: string
  rsvpStatus: 'pending' | 'accepted' | 'declined'
  rsvpAt: string | null
  ticket: TicketSummary | null
  ticketState: TicketState
  /** Latest ticket whatever its status (reissue a cancelled ticket). */
  lastTicketId: string | null
}

export type GuestInput = Pick<
  Guest,
  'name' | 'email' | 'phone' | 'seats' | 'category' | 'table' | 'notes'
>

export interface TicketBatch {
  batch: string
  total: number
  done: number
  failed: number
  status: 'running' | 'done'
}

export interface PublicTicket {
  status: TicketSummary['status']
  code: string
  guest: { name: string; seats: number; rsvpStatus: Guest['rsvpStatus'] }
  couple: string
  startsAt: string | null
  venue: string
  address: string
  agency: string
}

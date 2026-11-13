import type { Unit } from '@/modules/catalog/types'

export type QuoteStatus = 'draft' | 'sent' | 'accepted' | 'refused' | 'expired'

export interface QuoteLine {
  id?: string
  serviceItem: string | null
  label: string
  description: string
  unit: Unit
  unitLabel?: string
  unitPrice: number
  quantity: number
  amount?: number
  /** Line icon on the document; empty = guessed by the server from the label. */
  icon?: string
}

/** « En partenariat avec … » (docs/specs/devis-billets.md §2d), two at most. */
export interface QuotePartner {
  id?: string
  name: string
  activity: string
  signatory: string
  signatoryRole: string
}

export type QuoteDesign = 'A' | 'B' | 'C' | 'D'

export interface Quote {
  id: string
  number: string
  client: string | null
  clientDetail: { id: string; name: string; company: string; email: string; phone: string } | null
  status: QuoteStatus
  statusLabel: string
  issueDate: string
  validUntil: string
  weddingDate: string | null
  guestCount: number | null
  discountPct: number
  depositPct: number
  paymentTerms: string
  notes: string
  subtotal: number
  discountAmount: number
  total: number
  depositAmount: number
  sentAt: string | null
  acceptedAt: string | null
  refusedAt: string | null
  refusalReason: string
  isTemplate: boolean
  templateName: string
  publicUrl: string | null
  contract: { id: string; number: string } | null
  lines: QuoteLine[]
  /** Document look; empty = the agency's default. */
  design: QuoteDesign | ''
  palette: string
  tagline: string
  eventType: string
  venue: string
  partners: QuotePartner[]
  createdAt: string
  updatedAt: string
}

export interface QuoteListItem {
  id: string
  number: string
  /** A contract was created from this quote. */
  hasContract: boolean
  client: string | null
  clientName: string | null
  status: QuoteStatus
  statusLabel: string
  issueDate: string
  validUntil: string
  weddingDate: string | null
  total: number
  sentAt: string | null
  isTemplate: boolean
  templateName: string
  updatedAt: string
}

export type QuoteInput = Partial<
  Pick<
    Quote,
    | 'client'
    | 'validUntil'
    | 'weddingDate'
    | 'guestCount'
    | 'discountPct'
    | 'depositPct'
    | 'paymentTerms'
    | 'notes'
    | 'templateName'
    | 'design'
    | 'palette'
    | 'tagline'
    | 'eventType'
    | 'venue'
  >
> & { lines?: QuoteLine[]; partners?: QuotePartner[] }

/** Designs and palettes offered in the editor (GET /documents/designs). */
export interface DocumentDesigns {
  designs: { code: QuoteDesign; name: string }[]
  palettes: { code: string; name: string; dark: string; accent: string }[]
  defaultDesign: QuoteDesign
  defaultPalette: string
  defaultTagline: string
}

export interface GeneratedDocument {
  id: string
  version: number
  template: QuoteDesign
  sha256: string
  pageCount: number
  pdfUrl: string
  pngUrl: string | null
  createdAt: string
}

export type QuoteSummary = Record<QuoteStatus | 'templates', number>

export interface PublicQuote {
  number: string
  organization: { name: string; city: string; legalMentions: string; logo: string | null }
  clientName: string
  status: QuoteStatus
  statusLabel: string
  issueDate: string
  validUntil: string
  weddingDate: string | null
  guestCount: number | null
  discountPct: number
  depositPct: number
  paymentTerms: string
  notes: string
  subtotal: number
  discountAmount: number
  total: number
  depositAmount: number
  acceptedAt: string | null
  refusedAt: string | null
  lines: (QuoteLine & { unitLabel: string; amount: number })[]
}

/** Tiles of the quote list (complement §16). */
export interface QuoteStats {
  medianCreationMinutes: number | null
  sentThisMonth: number
  acceptanceRate: number | null
  pendingAmount: number
}

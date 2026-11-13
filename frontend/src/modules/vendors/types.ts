export type VendorCategory =
  | 'decoration'
  | 'caterer'
  | 'photographer'
  | 'videographer'
  | 'dj'
  | 'venue'
  | 'cake'
  | 'rental'
  | 'transport'
  | 'flowers'
  | 'sound'
  | 'supplies'
  | 'security'
  | 'other'

/** Feedback 13/11/2026: one address book, suppliers (sell to the agency) and partners. */
export type VendorKind = 'supplier' | 'partner'
export const VENDOR_KINDS: VendorKind[] = ['supplier', 'partner']

export const VENDOR_CATEGORIES: VendorCategory[] = [
  'decoration',
  'flowers',
  'caterer',
  'cake',
  'venue',
  'photographer',
  'videographer',
  'dj',
  'sound',
  'rental',
  'supplies',
  'transport',
  'security',
  'other',
]

export interface Vendor {
  id: string
  name: string
  kind: VendorKind
  kindLabel: string
  category: VendorCategory
  categoryLabel: string
  /** The person to call at the supplier's. */
  contactName: string
  phone: string
  whatsapp: string
  email: string
  city: string
  address: string
  /** NIU (Numéro d’identifiant unique). */
  taxId: string
  /** RCCM (registre du commerce). */
  tradeRegister: string
  paymentTerms: string
  mobileMoney: string
  bankDetails: string
  /** What they do for the agency (replaces the 1-5 rating, 13/11/2026). */
  services: string
  notes: string
  collaborations: number
  /** Hidden from roles without access to money (assistant). */
  due?: number
}

export type VendorInput = Omit<
  Vendor,
  'id' | 'kindLabel' | 'categoryLabel' | 'collaborations' | 'due'
>

export const emptyVendor = (kind: VendorKind = 'supplier'): VendorInput => ({
  name: '',
  kind,
  category: 'decoration',
  contactName: '',
  phone: '',
  whatsapp: '',
  email: '',
  city: '',
  address: '',
  taxId: '',
  tradeRegister: '',
  paymentTerms: '',
  mobileMoney: '',
  bankDetails: '',
  services: '',
  notes: '',
})

export interface Assignment {
  id: string
  wedding: string
  weddingTitle: string
  vendor: string
  vendorName: string
  vendorCategoryLabel: string
  vendorPhone: string
  service: string
  cost?: number
  paidAmount?: number
  due?: number
}

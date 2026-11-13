import { api } from './client'

/** Identity of the agency on its documents (docs/specs/devis-billets.md §4). */
export type BrandingFileKind = 'logo' | 'logoOnDark' | 'signatureImage' | 'stampImage'
export type BrandingIcon =
  | 'rings'
  | 'cake'
  | 'glass'
  | 'briefcase'
  | 'star'
  | 'team'
  | 'clock'
  | 'heart'
  | 'flower'
  | 'camera'
  | 'music'
  | 'gift'
  | 'car'
  | 'calendar'
  | 'shield'
  | 'sparkles'

export interface BrandingItem {
  label: string
  icon: BrandingIcon
}

export interface BrandingScripts {
  satisfaction: string
  detail: string
  detailSub: string
  priority: string
  thanks: string
  footer: string
}

export interface Branding {
  primaryColor: string
  secondaryColor: string
  monogramColor: string
  useBrandColors: boolean
  tradeName: string
  legalName: string
  activity: string
  slogan: string
  address: string
  phones: string[]
  whatsapp: string
  email: string
  website: string
  socials: Partial<Record<'facebook' | 'instagram' | 'tiktok' | 'linkedin' | 'youtube', string>>
  taxIds: Partial<Record<'rccm' | 'nif' | 'ncc' | 'niu' | 'ninea' | 'ifu', string>>
  vatRate: string | null
  bankDetails: string
  mobileMoneyNumbers: { provider: string; number: string }[]
  activities: BrandingItem[]
  engagements: BrandingItem[]
  quoteTagline: string
  scripts: BrandingScripts
  signatory: string
  signatoryRole: string
  footerKeywords: string[]
  quoteTerms: string
  paymentTerms: string
  footerText: string
  showWedivoMention: boolean
  logoContrastLight: number | null
  logoContrastDark: number | null
  files: Record<BrandingFileKind, string | null>
  monogram: string
  // Values, not keys: they keep the API's snake_case.
  missing: ('logo' | 'phones' | 'email' | 'address' | 'tax_ids')[]
  warnings: ('logo_light' | 'logo_dark')[]
  updatedAt: string
}

export type BrandingInput = Partial<
  Omit<
    Branding,
    | 'logoContrastLight'
    | 'logoContrastDark'
    | 'files'
    | 'monogram'
    | 'missing'
    | 'warnings'
    | 'updatedAt'
  >
>

/** The file kinds as the API names them (FormData values are not converted). */
const KIND: Record<BrandingFileKind, string> = {
  logo: 'logo',
  logoOnDark: 'logo_on_dark',
  signatureImage: 'signature_image',
  stampImage: 'stamp_image',
}

export const brandingApi = {
  get: () => api.get<Branding>('/organization/branding').then((r) => r.data),
  update: (input: BrandingInput) =>
    api.patch<Branding>('/organization/branding', input).then((r) => r.data),
  upload: (kind: BrandingFileKind, file: File) => {
    const form = new FormData()
    form.append('kind', KIND[kind])
    form.append('file', file)
    return api.post<Branding>('/organization/branding/files', form).then((r) => r.data)
  },
  remove: (kind: BrandingFileKind) =>
    api
      .delete<Branding>('/organization/branding/files', { params: { kind: KIND[kind] } })
      .then((r) => r.data),
}

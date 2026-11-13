/**
 * Wedivo's own contact details, shown on the sign-in pages (feedback 13/11/2026). They come from
 * the build environment (`VITE_SUPPORT_*`), never from the code: a block without a value is hidden.
 */
const env = import.meta.env

export const SUPPORT = {
  phone: (env.VITE_SUPPORT_PHONE as string | undefined)?.trim() ?? '',
  whatsapp: (env.VITE_SUPPORT_WHATSAPP as string | undefined)?.trim() ?? '',
  email: (env.VITE_SUPPORT_EMAIL as string | undefined)?.trim() ?? '',
  hours: (env.VITE_SUPPORT_HOURS as string | undefined)?.trim() ?? '',
}

export const hasSupport = Boolean(SUPPORT.phone || SUPPORT.whatsapp || SUPPORT.email)

/** `tel:+237699000000` from « +237 6 99 00 00 00 ». */
export const telHref = (phone: string): string => `tel:${phone.replace(/[^\d+]/g, '')}`

/** `https://wa.me/237699000000`: WhatsApp wants the digits only. */
export const whatsappHref = (phone: string): string => `https://wa.me/${phone.replace(/\D/g, '')}`

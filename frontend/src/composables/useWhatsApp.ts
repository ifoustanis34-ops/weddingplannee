import { ref } from 'vue'

import { whatsappHref } from '@/app/support'

/**
 * « Envoyer sur WhatsApp » (feedback 20/11/2026) for quotes, invoices and slips. Wedivo never sends
 * the message itself (CLAUDE.md §2: no WhatsApp Business API yet): it opens the planner's own
 * WhatsApp with a ready message, the planner presses « Envoyer ».
 *
 * - With a document and a phone able to share files (Android, iOS): the PDF is attached through
 *   the share sheet, where the planner picks WhatsApp then the contact.
 * - Otherwise (computer): the PDF is downloaded and the client's chat opens with the message; the
 *   planner drops the file in it.
 */
export interface WhatsAppShare {
  /** The recipient's number, any format (« +237 6 99 00 00 00 »); empty opens the contact list. */
  phone?: string | null
  /** The message; may do an async step first (e.g. mark a quote as sent to get its link). */
  text: () => string | Promise<string>
  /** The document to attach (PDF, or the PNG of a plan), fetched on click. */
  file?: () => Promise<Blob>
  filename?: string
}

const PDF = 'application/pdf'

function canShareFiles(): boolean {
  try {
    return (
      typeof navigator.canShare === 'function' &&
      navigator.canShare({ files: [new File([''], 'test.pdf', { type: PDF })] })
    )
  } catch {
    return false
  }
}

/** `https://wa.me/237…?text=…`: the chat of that number, or the contact list without one. */
export function whatsappUrl(phone: string | null | undefined, text: string): string {
  const digits = (phone ?? '').replace(/\D/g, '')
  const base = digits.length >= 8 ? whatsappHref(digits) : 'https://wa.me/'
  return `${base}?text=${encodeURIComponent(text)}`
}

function download(blob: Blob, filename: string): void {
  const href = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = filename
  link.click()
  setTimeout(() => URL.revokeObjectURL(href), 60_000)
}

export function useWhatsApp() {
  const pending = ref(false)

  /** Resolves false when the planner closed the share sheet; throws the API errors. */
  async function share(options: WhatsAppShare): Promise<boolean> {
    const filename = options.filename ?? 'document.pdf'
    const sheet = Boolean(options.file) && canShareFiles()
    // The tab is opened during the click, before any await, or the browser blocks it.
    const tab = sheet ? null : window.open('about:blank', '_blank')
    pending.value = true
    try {
      const text = await options.text()
      if (sheet && options.file) {
        const blob = await options.file()
        try {
          const type = blob.type || PDF
          await navigator.share({ files: [new File([blob], filename, { type })], text })
        } catch (error) {
          if (error instanceof DOMException && error.name === 'AbortError') return false
          throw error
        }
        return true
      }
      if (options.file) download(await options.file(), filename)
      const url = whatsappUrl(options.phone, text)
      if (tab) {
        tab.opener = null
        tab.location.href = url
      } else {
        window.location.href = url
      }
      return true
    } catch (error) {
      tab?.close()
      throw error
    } finally {
      pending.value = false
    }
  }

  return { share, pending }
}

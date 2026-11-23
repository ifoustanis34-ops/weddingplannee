import { ref, shallowRef } from 'vue'

import { whatsappHref } from '@/app/support'

/**
 * Sharing a document (feedback 20 and 23/11/2026): quotes, invoices, slips, plans. Wedivo never
 * sends the message itself (CLAUDE.md §2: no WhatsApp Business API yet): it opens the planner's
 * own app with the document and a ready message, the planner presses « Envoyer ».
 *
 * - `whatsapp`: on a phone the PDF alone goes through the share sheet (WhatsApp, then the
 *   contact); on a computer the PDF is downloaded and the client's chat opens, empty, to drop it in.
 * - `any` (« Partager »): the same share sheet, open to every app (email, Telegram, Drive…); on a
 *   computer the PDF is downloaded.
 *
 * A phone refuses the share sheet when preparing the PDF took too long after the tap: the file
 * then waits in `readyShare`, and `ShareReady.vue` offers one more tap to send it.
 */
export interface DocumentShare {
  /** The recipient's number, any format (« +237 6 99 00 00 00 »); empty opens the contact list. */
  phone?: string | null
  /** A step before sending (e.g. save the quote and mark it as sent). */
  prepare?: () => unknown
  /** The document to attach (PDF, or the PNG of a plan), fetched on click. */
  file?: () => Promise<Blob>
  filename?: string
  /** Title of the share sheet (some apps use it as the email subject). */
  title?: string
}
/** Kept for the existing callers. */
export type WhatsAppShare = DocumentShare

export type ShareResult = 'shared' | 'cancelled' | 'downloaded' | 'pending'

const PDF = 'application/pdf'

/** A document ready to share, waiting for one more tap (see `ShareReady.vue`). */
export const readyShare = shallowRef<{ data: ShareData; filename: string } | null>(null)

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

/** `https://wa.me/237…`: the chat of that number, or the contact list without one. */
export function whatsappUrl(phone: string | null | undefined): string {
  const digits = (phone ?? '').replace(/\D/g, '')
  return digits.length >= 8 ? whatsappHref(digits) : 'https://wa.me/'
}

export function downloadBlob(blob: Blob, filename: string): void {
  const href = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = filename
  link.click()
  setTimeout(() => URL.revokeObjectURL(href), 60_000)
}

/** Opens the share sheet; `pending` when the phone wants one more tap. */
export async function openShareSheet(data: ShareData, filename: string): Promise<ShareResult> {
  try {
    await navigator.share(data)
    return 'shared'
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') return 'cancelled'
    if (error instanceof DOMException && error.name === 'NotAllowedError') {
      readyShare.value = { data, filename }
      return 'pending'
    }
    throw error
  }
}

export function useWhatsApp() {
  const pending = ref(false)

  async function run(
    options: DocumentShare,
    target: 'whatsapp' | 'any',
  ): Promise<ShareResult | false> {
    const filename = options.filename ?? 'document.pdf'
    const sheet = Boolean(options.file) && canShareFiles()
    // A new tab is opened during the tap, before any await, or the browser blocks it.
    const tab = !sheet && target === 'whatsapp' ? window.open('about:blank', '_blank') : null
    pending.value = true
    try {
      // Only the document leaves, never a message (feedback 23/11/2026: « le PDF, sans autre
      // message »).
      await options.prepare?.()
      if (sheet && options.file) {
        const blob = await options.file()
        const file = new File([blob], filename, { type: blob.type || PDF })
        const result = await openShareSheet({ files: [file] }, filename)
        return result === 'cancelled' ? false : result
      }
      if (options.file) downloadBlob(await options.file(), filename)
      if (target === 'any') {
        // No share sheet (computer): the document is saved, ready to attach.
        return 'downloaded'
      }
      const url = whatsappUrl(options.phone)
      if (tab) {
        tab.opener = null
        tab.location.href = url
      } else {
        window.location.href = url
      }
      return 'shared'
    } catch (error) {
      tab?.close()
      throw error
    } finally {
      pending.value = false
    }
  }

  return {
    /** To WhatsApp; resolves false when the planner closed the share sheet. */
    share: (options: DocumentShare) => run(options, 'whatsapp'),
    /** To any app (« Partager »). */
    shareAnywhere: (options: DocumentShare) => run(options, 'any'),
    canShareFiles,
    pending,
  }
}

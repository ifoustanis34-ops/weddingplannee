import { describe, expect, it } from 'vitest'

import { telHref, whatsappHref } from '@/app/support'

describe('support links', () => {
  it('builds a dialable tel: link', () => {
    expect(telHref('+237 6 99 00 00 00')).toBe('tel:+237699000000')
  })
  it('keeps the digits only for WhatsApp', () => {
    expect(whatsappHref('+237 6 77 00 00 00')).toBe('https://wa.me/237677000000')
  })
})

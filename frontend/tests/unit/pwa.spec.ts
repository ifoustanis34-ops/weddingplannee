import { describe, expect, it } from 'vitest'

import { urlBase64ToUint8Array } from '@/app/pwa'

describe('urlBase64ToUint8Array', () => {
  it('decodes a base64url VAPID key without padding', () => {
    // « Wedivo » → V2VkaXZv ; with « - » and « _ » of the URL-safe alphabet
    expect([...urlBase64ToUint8Array('V2VkaXZv')]).toEqual([87, 101, 100, 105, 118, 111])
    expect([...urlBase64ToUint8Array('-_8')]).toEqual([251, 255])
  })
})

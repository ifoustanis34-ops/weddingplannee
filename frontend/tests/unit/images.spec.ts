import { describe, expect, it } from 'vitest'

import { cropBox, prepareImage, targetSize } from '@/app/images'

/** Phone photos made ready before sending (feedback 15/11/2026). */
describe('image preparation', () => {
  it('crops a portrait square, kept high to keep the face', () => {
    expect(cropBox(3000, 4000, true)).toEqual({ sx: 0, sy: 150, sw: 3000, sh: 3000 })
  })

  it('crops a landscape square in the middle', () => {
    expect(cropBox(4000, 3000, true)).toEqual({ sx: 500, sy: 0, sw: 3000, sh: 3000 })
  })

  it('keeps the whole picture when no square is asked', () => {
    expect(cropBox(4000, 3000, false)).toEqual({ sx: 0, sy: 0, sw: 4000, sh: 3000 })
  })

  it('reduces to the longest side and never enlarges', () => {
    expect(targetSize(4000, 3000, 1200)).toEqual([1200, 900])
    expect(targetSize(600, 400, 1200)).toEqual([600, 400])
  })

  it('sends a file it cannot read as is', async () => {
    const file = new File(['not an image'], 'notes.txt', { type: 'text/plain' })
    expect(await prepareImage(file)).toBe(file)
  })
})

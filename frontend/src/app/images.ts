/**
 * Photos taken with a phone, made ready before they leave the browser (feedback 15/11/2026):
 * turned the right way up, reduced, re-encoded as JPEG (4–8 MB from a phone become ~300 KB,
 * well under the server's 5 MB) and, for a person, cropped square on the upper part of the
 * picture where the face usually is (staff records, badges).
 *
 * A picture the browser cannot read (e.g. HEIC outside Safari) is sent as is: the server says
 * what is wrong.
 */
export interface PrepareOptions {
  /** Longest side of the result, px. */
  maxSide?: number
  /** Square crop for portraits (staff photo, badges). */
  square?: boolean
  quality?: number
}

const DEFAULTS = { maxSide: 1200, square: false, quality: 0.85 }

async function decode(file: File): Promise<ImageBitmap | null> {
  if (typeof createImageBitmap !== 'function') return null
  try {
    // « from-image »: the EXIF orientation of phone photos is applied.
    return await createImageBitmap(file, { imageOrientation: 'from-image' })
  } catch {
    return null
  }
}

/** Source rectangle: the whole picture, or a centred square kept high (faces are on top). */
export function cropBox(
  width: number,
  height: number,
  square: boolean,
): { sx: number; sy: number; sw: number; sh: number } {
  if (!square) return { sx: 0, sy: 0, sw: width, sh: height }
  const side = Math.min(width, height)
  const sx = Math.round((width - side) / 2)
  // Portrait: start at 15 % of the extra height rather than the middle, to keep the head.
  const sy = height > width ? Math.round((height - side) * 0.15) : 0
  return { sx, sy, sw: side, sh: side }
}

export function targetSize(sw: number, sh: number, maxSide: number): [number, number] {
  const scale = Math.min(1, maxSide / Math.max(sw, sh))
  return [Math.max(1, Math.round(sw * scale)), Math.max(1, Math.round(sh * scale))]
}

export async function prepareImage(file: File, options: PrepareOptions = {}): Promise<File> {
  const { maxSide, square, quality } = { ...DEFAULTS, ...options }
  if (!file.type.startsWith('image/') || file.type === 'image/svg+xml') return file
  const bitmap = await decode(file)
  if (!bitmap) return file
  const { sx, sy, sw, sh } = cropBox(bitmap.width, bitmap.height, square)
  const [width, height] = targetSize(sw, sh, maxSide)
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const context = canvas.getContext('2d')
  if (!context) {
    bitmap.close()
    return file
  }
  context.fillStyle = '#ffffff' // a transparent PNG becomes white, not black, in JPEG
  context.fillRect(0, 0, width, height)
  context.drawImage(bitmap, sx, sy, sw, sh, 0, 0, width, height)
  bitmap.close()
  const blob = await new Promise<Blob | null>((resolve) =>
    canvas.toBlob(resolve, 'image/jpeg', quality),
  )
  if (!blob) return file
  const name = file.name.replace(/\.[^.]+$/, '') || 'photo'
  return new File([blob], `${name}.jpg`, { type: 'image/jpeg' })
}

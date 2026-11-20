/**
 * The plan as a PNG (to download or to send on WhatsApp): the SVG drawn on a canvas, about
 * 80 px per metre, at most 4000 px wide. The SVG uses fixed colours (see `PAPER`), never CSS
 * variables, so the image is the same in light and dark mode.
 */
export async function planToPng(svg: SVGSVGElement): Promise<Blob> {
  const box = svg.viewBox.baseVal
  const scale = Math.min(80, 4000 / Math.max(box.width, box.height))
  const width = Math.round(box.width * scale)
  const height = Math.round(box.height * scale)

  const copy = svg.cloneNode(true) as SVGSVGElement
  copy.setAttribute('width', String(width))
  copy.setAttribute('height', String(height))
  copy.removeAttribute('class')
  const markup = new XMLSerializer().serializeToString(copy)
  const url = URL.createObjectURL(new Blob([markup], { type: 'image/svg+xml;charset=utf-8' }))
  try {
    const image = new Image()
    image.decoding = 'async'
    await new Promise<void>((resolve, reject) => {
      image.onload = () => resolve()
      image.onerror = () => reject(new Error('Image du croquis impossible à produire.'))
      image.src = url
    })
    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    const context = canvas.getContext('2d')
    if (!context) throw new Error('Image du croquis impossible à produire.')
    context.fillStyle = '#ffffff'
    context.fillRect(0, 0, width, height)
    context.drawImage(image, 0, 0, width, height)
    return await new Promise<Blob>((resolve, reject) =>
      canvas.toBlob(
        (blob) => (blob ? resolve(blob) : reject(new Error('Image du croquis impossible.'))),
        'image/png',
      ),
    )
  } finally {
    URL.revokeObjectURL(url)
  }
}

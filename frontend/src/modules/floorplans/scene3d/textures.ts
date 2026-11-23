import * as THREE from 'three'

import type { Ambiance } from '../types'

/**
 * Floors drawn on a canvas (no image to download, works offline): one tile of the pattern,
 * repeated over the room at its real size.
 */
type Painter = (context: CanvasRenderingContext2D, size: number) => void

const SIZE = 256

/** Metres covered by one tile of the pattern. */
const TILE: Record<Ambiance['floor'], number> = {
  tiles: 1.2,
  parquet: 1.6,
  marble: 2.4,
  concrete: 3,
  grass: 2,
  carpet: 2,
}

function noise(context: CanvasRenderingContext2D, size: number, colors: string[], count: number) {
  for (let i = 0; i < count; i++) {
    context.fillStyle = colors[i % colors.length]!
    const r = Math.random() * 2 + 0.6
    context.fillRect(Math.random() * size, Math.random() * size, r, r)
  }
}

const PAINTERS: Record<Ambiance['floor'], Painter> = {
  tiles: (c, s) => {
    c.fillStyle = '#efeae3'
    c.fillRect(0, 0, s, s)
    noise(c, s, ['#e6e0d7', '#f6f2ec'], 900)
    c.strokeStyle = '#cfc6b8'
    c.lineWidth = 3
    for (const v of [0, s / 2, s]) {
      c.beginPath()
      c.moveTo(v, 0)
      c.lineTo(v, s)
      c.moveTo(0, v)
      c.lineTo(s, v)
      c.stroke()
    }
  },
  parquet: (c, s) => {
    const planks = 6
    const h = s / planks
    for (let i = 0; i < planks; i++) {
      const tone = 120 + Math.round(Math.random() * 30)
      c.fillStyle = `rgb(${tone + 50}, ${tone}, ${tone - 50})`
      c.fillRect(0, i * h, s, h)
      c.strokeStyle = 'rgba(70, 40, 15, 0.18)'
      for (let k = 0; k < 6; k++) {
        c.beginPath()
        const y = i * h + Math.random() * h
        c.moveTo(0, y)
        c.bezierCurveTo(s / 3, y + 3, (2 * s) / 3, y - 3, s, y)
        c.stroke()
      }
      c.fillStyle = 'rgba(60, 35, 15, 0.45)'
      c.fillRect(0, i * h, s, 2)
      c.fillRect(((i * 97) % s) + 10, i * h, 2, h)
    }
  },
  marble: (c, s) => {
    c.fillStyle = '#f4f2f0'
    c.fillRect(0, 0, s, s)
    c.strokeStyle = 'rgba(150, 140, 135, 0.35)'
    for (let k = 0; k < 14; k++) {
      c.lineWidth = Math.random() * 2 + 0.5
      c.beginPath()
      let x = Math.random() * s
      let y = 0
      c.moveTo(x, y)
      while (y < s) {
        x += (Math.random() - 0.5) * 40
        y += 20 + Math.random() * 25
        c.lineTo(x, y)
      }
      c.stroke()
    }
    c.strokeStyle = '#ddd7d0'
    c.lineWidth = 2
    c.strokeRect(0, 0, s, s)
  },
  concrete: (c, s) => {
    c.fillStyle = '#c9c6c1'
    c.fillRect(0, 0, s, s)
    noise(c, s, ['#bdb9b3', '#d4d1cc', '#b3afa9'], 3000)
  },
  grass: (c, s) => {
    c.fillStyle = '#6f9e58'
    c.fillRect(0, 0, s, s)
    noise(c, s, ['#5f8d4a', '#84b26a', '#77a85f', '#4f7c3d'], 6000)
  },
  carpet: (c, s) => {
    c.fillStyle = '#8c2f4a'
    c.fillRect(0, 0, s, s)
    noise(c, s, ['#7c2840', '#9a3755'], 2500)
    c.strokeStyle = 'rgba(244, 166, 42, 0.35)'
    c.lineWidth = 2
    c.beginPath()
    c.arc(s / 2, s / 2, s / 3, 0, Math.PI * 2)
    c.stroke()
  },
}

export function floorTexture(
  kind: Ambiance['floor'],
  length: number,
  width: number,
): THREE.CanvasTexture {
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = SIZE
  PAINTERS[kind](canvas.getContext('2d')!, SIZE)
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping
  texture.repeat.set(length / TILE[kind], width / TILE[kind])
  texture.anisotropy = 4
  return texture
}

export const WALL_COLORS: Record<Exclude<Ambiance['walls'], 'none'>, number> = {
  white: 0xfbfaf7,
  cream: 0xf1e6d2,
  grey: 0xd9d8dc,
}

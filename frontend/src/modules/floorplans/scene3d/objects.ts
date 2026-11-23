import * as THREE from 'three'

import { CHAIR, chairsOf, isTable } from '../elements'
import type { ElementType, PlanElement } from '../types'

/**
 * The furniture of the 3D view, to scale (metres). Each element is built around its own centre;
 * `Plan3D` places and turns it. Everything made here is listed in `kit.disposables`, freed when
 * the scene is rebuilt.
 */
export const COLORS = {
  cloth: 0xffffff,
  chair: 0xe9e2f8,
  chairFrame: 0xc9a46b,
  stage: 0x8a5a3b,
  stageTop: 0xb98b5e,
  dance: 0x1f1d33,
  buffet: 0xf3f7f4,
  skirt: 0xdff4ec,
  bar: 0x3b2a20,
  barTop: 0xe8dccb,
  dj: 0x2b2946,
  entrance: 0x0e8f69,
  arch: 0xf6f3ee,
  flower: 0xe58bb5,
  flower2: 0xffffff,
  leaf: 0x3f8f5a,
  pillar: 0xe2ded7,
  gold: 0xd4a84b,
  sofa: 0xd8cbe8,
  screen: 0x0d0c20,
  pot: 0xb5652f,
  cake: 0xfffaf0,
}

/** What a guest cannot walk through (collisions of the visit). */
export const SOLID = new Set<ElementType>([
  'round_table',
  'rect_table',
  'head_table',
  'cocktail',
  'cake',
  'stage',
  'buffet',
  'bar',
  'dj',
  'pillar',
  'lounge',
  'photobooth',
  'plant',
  'chair',
  'chair_row',
  'screen',
])

export class Kit {
  readonly disposables: { dispose: () => void }[] = []
  lights = 0

  constructor(
    readonly evening: boolean,
    readonly height: number,
    private readonly name: (element: PlanElement) => string,
  ) {}

  material(color: number, extra: THREE.MeshStandardMaterialParameters = {}) {
    const made = new THREE.MeshStandardMaterial({ color, roughness: 0.8, ...extra })
    this.disposables.push(made)
    return made
  }

  geometry<T extends THREE.BufferGeometry>(made: T): T {
    this.disposables.push(made)
    return made
  }

  mesh(geo: THREE.BufferGeometry, mat: THREE.Material, shadow = true): THREE.Mesh {
    const made = new THREE.Mesh(geo, mat)
    made.castShadow = shadow
    made.receiveShadow = true
    return made
  }

  box(w: number, h: number, d: number, color: number, y = h / 2, extra = {}) {
    const made = this.mesh(
      this.geometry(new THREE.BoxGeometry(w, h, d)),
      this.material(color, extra),
    )
    made.position.y = y
    return made
  }

  cylinder(r: number, h: number, color: number, y = h / 2, extra = {}, top = r) {
    const made = this.mesh(
      this.geometry(new THREE.CylinderGeometry(top, r, h, 32)),
      this.material(color, extra),
    )
    made.position.y = y
    return made
  }

  sphere(r: number, color: number, extra = {}) {
    return this.mesh(
      this.geometry(new THREE.SphereGeometry(r, 14, 10)),
      this.material(color, extra),
    )
  }

  /** A floating name (table number, text) drawn on a canvas. */
  label(text: string, size = 0.4): THREE.Sprite {
    const canvas = document.createElement('canvas')
    const context = canvas.getContext('2d')!
    const font = 64
    context.font = `700 ${font}px Montserrat, Arial, sans-serif`
    canvas.width = Math.ceil(context.measureText(text).width) + 48
    canvas.height = font + 36
    context.font = `700 ${font}px Montserrat, Arial, sans-serif`
    context.fillStyle = 'rgba(23, 21, 59, 0.82)'
    context.beginPath()
    context.roundRect(0, 0, canvas.width, canvas.height, 24)
    context.fill()
    context.fillStyle = '#ffffff'
    context.textBaseline = 'middle'
    context.fillText(text, 24, canvas.height / 2 + 2)
    const texture = new THREE.CanvasTexture(canvas)
    texture.colorSpace = THREE.SRGBColorSpace
    const mat = new THREE.SpriteMaterial({ map: texture, depthTest: false })
    this.disposables.push(texture, mat)
    const sprite = new THREE.Sprite(mat)
    sprite.scale.set((size * canvas.width) / canvas.height, size, 1)
    sprite.renderOrder = 10
    return sprite
  }

  /** Warm light of the evening (a few only: each one costs on a phone). */
  glow(group: THREE.Group, y: number, intensity = 6, distance = 9): void {
    if (!this.evening || this.lights >= 10) return
    const light = new THREE.PointLight(0xffc98a, intensity, distance, 1.6)
    light.position.y = y
    group.add(light)
    this.lights += 1
  }

  // --- Pieces ---------------------------------------------------------------------------------

  /** A Chiavari chair facing its table: the back on the local -z side (as drawn in 2D). */
  chair(): THREE.Group {
    const group = new THREE.Group()
    const frame = this.material(COLORS.chairFrame, { metalness: 0.5, roughness: 0.35 })
    const seat = this.box(CHAIR, 0.07, CHAIR, COLORS.chair, 0.45)
    const back = this.mesh(this.geometry(new THREE.BoxGeometry(CHAIR, 0.5, 0.04)), frame)
    back.position.set(0, 0.73, -CHAIR / 2 + 0.02)
    group.add(seat, back)
    const leg = this.geometry(new THREE.CylinderGeometry(0.018, 0.018, 0.45, 6))
    for (const [x, z] of [
      [-1, -1],
      [1, -1],
      [-1, 1],
      [1, 1],
    ] as const) {
      const piece = this.mesh(leg, frame)
      piece.position.set((x * CHAIR) / 2.3, 0.225, (z * CHAIR) / 2.3)
      group.add(piece)
    }
    return group
  }

  bouquet(y = 0.76): THREE.Group {
    const group = new THREE.Group()
    const vase = this.cylinder(
      0.05,
      0.22,
      COLORS.gold,
      y + 0.11,
      { metalness: 0.6, roughness: 0.3 },
      0.07,
    )
    group.add(vase)
    for (let i = 0; i < 7; i++) {
      const bloom = this.sphere(0.07, i % 3 ? COLORS.flower : COLORS.flower2)
      const a = (i / 7) * Math.PI * 2
      bloom.position.set(Math.cos(a) * 0.09, y + 0.32 + (i % 2) * 0.05, Math.sin(a) * 0.09)
      group.add(bloom)
    }
    if (this.evening) {
      const candle = this.cylinder(0.025, 0.1, 0xfff4dc, y + 0.05)
      candle.position.x = 0.22
      const flame = this.sphere(0.02, 0xffb347, { emissive: 0xffa53a, emissiveIntensity: 2 })
      flame.position.set(0.22, y + 0.13, 0)
      group.add(candle, flame)
    }
    return group
  }

  plantPot(scale = 1): THREE.Group {
    const group = new THREE.Group()
    group.add(this.cylinder(0.18 * scale, 0.4 * scale, COLORS.pot, 0.2 * scale, {}, 0.22 * scale))
    for (let i = 0; i < 9; i++) {
      const leaf = this.sphere(0.16 * scale, COLORS.leaf)
      leaf.scale.y = 1.6
      const a = (i / 9) * Math.PI * 2
      leaf.position.set(
        Math.cos(a) * 0.12 * scale,
        (0.55 + (i % 3) * 0.18) * scale,
        Math.sin(a) * 0.12 * scale,
      )
      group.add(leaf)
    }
    return group
  }

  // --- Elements -------------------------------------------------------------------------------

  build(element: PlanElement): THREE.Group {
    const group = new THREE.Group()
    const { w, h } = element
    for (const spot of chairsOf(element)) {
      const seat = this.chair()
      seat.position.set(spot.x - w / 2, 0, spot.y - h / 2)
      seat.rotation.y = -(spot.rotation * Math.PI) / 180
      group.add(seat)
    }
    const cloth = this.material(COLORS.cloth, { roughness: 0.95 })
    switch (element.type) {
      case 'round_table': {
        const r = Math.min(w, h) / 2
        const top = this.mesh(
          this.geometry(new THREE.CylinderGeometry(r, r + 0.05, 0.76, 48)),
          cloth,
        )
        top.position.y = 0.38
        group.add(top, this.bouquet())
        break
      }
      case 'rect_table':
      case 'head_table': {
        const top = this.mesh(this.geometry(new THREE.BoxGeometry(w, 0.76, h)), cloth)
        top.position.y = 0.38
        group.add(top)
        if (element.type === 'head_table') {
          // A garland of flowers along the front.
          for (let x = -w / 2 + 0.15; x <= w / 2 - 0.15; x += 0.3) {
            const bloom = this.sphere(0.09, Math.round(x * 10) % 2 ? COLORS.flower : COLORS.flower2)
            bloom.position.set(x, 0.72, h / 2 + 0.03)
            group.add(bloom)
          }
        }
        const flowers = Math.max(1, Math.round(w / 1.6))
        for (let i = 0; i < flowers; i++) {
          const piece = this.bouquet()
          piece.position.x = (w * (i + 0.5)) / flowers - w / 2
          group.add(piece)
        }
        break
      }
      case 'cocktail': {
        const r = Math.min(w, h) / 2
        const top = this.mesh(this.geometry(new THREE.CylinderGeometry(r, r * 0.5, 1.1, 32)), cloth)
        top.position.y = 0.55
        group.add(top)
        break
      }
      case 'cake': {
        const r = Math.min(w, h) / 2
        const top = this.mesh(
          this.geometry(new THREE.CylinderGeometry(r, r + 0.05, 0.76, 40)),
          cloth,
        )
        top.position.y = 0.38
        group.add(top)
        let y = 0.76
        for (const [radius, height] of [
          [0.3, 0.22],
          [0.22, 0.2],
          [0.14, 0.18],
        ] as const) {
          group.add(this.cylinder(radius, height, COLORS.cake, y + height / 2))
          y += height
        }
        const topper = this.sphere(0.06, COLORS.flower)
        topper.position.y = y + 0.05
        group.add(topper)
        break
      }
      case 'chair': {
        const single = this.chair()
        single.scale.set(w / CHAIR, 1, h / CHAIR)
        group.add(single)
        break
      }
      case 'stage': {
        group.add(this.box(w, 0.55, h, COLORS.stage, 0.275))
        group.add(this.box(w, 0.05, h, COLORS.stageTop, 0.575, { roughness: 0.5 }))
        // A step in front.
        const step = this.box(Math.min(1.5, w), 0.27, 0.4, COLORS.stage, 0.135)
        step.position.z = h / 2 + 0.2
        group.add(step)
        break
      }
      case 'dance_floor': {
        // A dark glossy floor, lit squares in the evening.
        const tiles = Math.max(2, Math.round(Math.max(w, h)))
        const tw = w / tiles
        const td = h / Math.max(2, Math.round(h))
        for (let i = 0; i < tiles; i++) {
          for (let k = 0; k < Math.max(2, Math.round(h)); k++) {
            const lit = (i + k) % 2 === 0
            const tile = this.box(
              tw - 0.01,
              0.03,
              td - 0.01,
              lit ? 0x2d2a4a : COLORS.dance,
              0.015,
              {
                roughness: 0.15,
                metalness: 0.3,
                ...(this.evening && lit ? { emissive: 0x7a3cff, emissiveIntensity: 0.6 } : {}),
              },
            )
            tile.position.set(-w / 2 + tw * (i + 0.5), 0, -h / 2 + td * (k + 0.5))
            tile.castShadow = false
            group.add(tile)
          }
        }
        break
      }
      case 'buffet': {
        group.add(this.box(w, 0.88, h, COLORS.skirt, 0.44))
        group.add(this.box(w + 0.04, 0.04, h + 0.04, COLORS.buffet, 0.9))
        for (let x = -w / 2 + 0.4; x < w / 2 - 0.2; x += 0.8) {
          const dish = this.cylinder(
            0.18,
            0.1,
            0xc0c0c0,
            0.97,
            { metalness: 0.8, roughness: 0.25 },
            0.12,
          )
          dish.position.x = x
          group.add(dish)
        }
        break
      }
      case 'bar': {
        group.add(this.box(w, 1.05, h, COLORS.bar, 0.525))
        group.add(this.box(w + 0.1, 0.05, h + 0.1, COLORS.barTop, 1.075, { roughness: 0.3 }))
        for (let x = -w / 2 + 0.3; x < w / 2; x += 0.35) {
          const bottle = this.cylinder(0.035, 0.28, 0x2f6b4f, 1.24, {
            roughness: 0.2,
            metalness: 0.1,
          })
          bottle.position.set(x, 0, -h / 4)
          group.add(bottle)
        }
        break
      }
      case 'dj': {
        group.add(this.box(w, 1, h, COLORS.dj, 0.5))
        for (const side of [-1, 1]) {
          const speaker = this.box(0.4, 1.5, 0.4, 0x14132a, 0.75)
          speaker.position.x = side * (w / 2 + 0.35)
          group.add(speaker)
        }
        if (this.evening) {
          const spot = new THREE.SpotLight(0x9b6bff, 18, 12, Math.PI / 6, 0.5)
          spot.position.set(0, 2.6, 0)
          spot.target.position.set(0, 0, 3)
          group.add(spot, spot.target)
        }
        break
      }
      case 'entrance': {
        group.add(this.box(w, 0.02, Math.max(h, 0.3), COLORS.entrance, 0.01))
        for (const side of [-1, 1]) {
          const post = this.box(0.12, 2.3, 0.12, COLORS.entrance, 1.15)
          post.position.x = (side * w) / 2
          group.add(post)
        }
        break
      }
      case 'decor': {
        const rise = Math.max(w / 2, 2.2)
        const arch = this.mesh(
          this.geometry(new THREE.TorusGeometry(w / 2, 0.07, 10, 48, Math.PI)),
          this.material(COLORS.arch),
        )
        arch.scale.y = rise / (w / 2)
        group.add(arch)
        for (let i = 0; i <= 16; i++) {
          const angle = (Math.PI * i) / 16
          const bloom = this.sphere(0.12 + (i % 3) * 0.02, i % 2 ? COLORS.flower : COLORS.flower2)
          bloom.position.set((Math.cos(angle) * w) / 2, Math.sin(angle) * rise, 0)
          group.add(bloom)
        }
        break
      }
      case 'pillar':
        group.add(this.box(w, this.height, h, COLORS.pillar, this.height / 2))
        break
      case 'lounge': {
        // A sofa: seat, back, arms.
        group.add(this.box(w, 0.42, h, COLORS.sofa, 0.21))
        const back = this.box(w, 0.5, 0.2, COLORS.sofa, 0.67)
        back.position.z = -h / 2 + 0.1
        group.add(back)
        for (const side of [-1, 1]) {
          const arm = this.box(0.18, 0.25, h, COLORS.sofa, 0.545)
          arm.position.x = side * (w / 2 - 0.09)
          group.add(arm)
        }
        const table = this.cylinder(0.3, 0.4, COLORS.gold, 0.2, { metalness: 0.5 })
        table.position.z = h / 2 + 0.5
        group.add(table)
        break
      }
      case 'photobooth': {
        const wall = this.box(w, 2.4, 0.1, COLORS.flower2, 1.2)
        wall.position.z = -h / 2 + 0.05
        group.add(wall)
        for (let i = 0; i < 40; i++) {
          const bloom = this.sphere(0.1, i % 3 ? COLORS.flower : COLORS.flower2)
          bloom.position.set(-w / 2 + Math.random() * w, 0.2 + Math.random() * 2.2, -h / 2 + 0.12)
          group.add(bloom)
        }
        const tripod = this.cylinder(0.03, 1.4, 0x222222, 0.7)
        tripod.position.z = h / 2 - 0.2
        const camera = this.box(0.25, 0.18, 0.15, 0x222222, 1.45)
        camera.position.z = h / 2 - 0.2
        group.add(tripod, camera)
        break
      }
      case 'plant':
        group.add(this.plantPot(Math.min(w, h) / 0.6))
        break
      case 'chandelier': {
        // Hanging under the ceiling, crystal drops, lit in the evening.
        const y = this.height - 0.9
        const rod = this.cylinder(0.015, 0.9, COLORS.gold, this.height - 0.45, { metalness: 0.8 })
        const ring = this.mesh(
          this.geometry(new THREE.TorusGeometry(Math.min(w, h) / 2, 0.03, 8, 32)),
          this.material(COLORS.gold, { metalness: 0.8, roughness: 0.3 }),
          false,
        )
        ring.rotation.x = Math.PI / 2
        ring.position.y = y
        group.add(rod, ring)
        for (let i = 0; i < 12; i++) {
          const a = (i / 12) * Math.PI * 2
          const drop = this.sphere(0.05, 0xfff8e7, {
            emissive: 0xffd9a0,
            emissiveIntensity: this.evening ? 1.6 : 0.2,
            roughness: 0.1,
          })
          drop.castShadow = false
          drop.position.set(
            (Math.cos(a) * Math.min(w, h)) / 2,
            y - 0.12,
            (Math.sin(a) * Math.min(w, h)) / 2,
          )
          group.add(drop)
        }
        this.glow(group, y - 0.3, 9, 12)
        break
      }
      case 'screen': {
        const panel = this.box(
          w,
          w * 0.56,
          Math.max(0.05, h / 3),
          COLORS.screen,
          1.2 + (w * 0.56) / 2,
          {
            emissive: this.evening ? 0x2a3a8a : 0x000000,
            emissiveIntensity: 0.8,
            roughness: 0.2,
          },
        )
        group.add(panel)
        for (const side of [-1, 1]) {
          const leg = this.box(0.05, 1.2, 0.05, 0x333333, 0.6)
          leg.position.x = side * (w / 2 - 0.2)
          group.add(leg)
        }
        break
      }
      case 'text':
      case 'chair_row':
        break
    }
    // Table lights in the evening (the centrepieces glow a little).
    if (isTable(element.type)) this.glow(group, 1.6, 2.5, 4)

    const name = this.name(element)
    if (name && !['chair', 'pillar', 'plant', 'chandelier'].includes(element.type)) {
      const sprite = this.label(name, element.type === 'text' ? 0.55 : 0.36)
      // During the visit only the table numbers stay (guests look for their table).
      sprite.userData.label = isTable(element.type) ? 'table' : 'other'
      sprite.position.y =
        element.type === 'decor'
          ? Math.max(w / 2, 2.2) + 0.5
          : element.type === 'text'
            ? 1.8
            : element.type === 'photobooth' || element.type === 'screen'
              ? 2.9
              : 1.5
      group.add(sprite)
    }
    return group
  }
}

<script setup lang="ts">
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { CHAIR, chairsOf, isTable } from '../elements'
import type { PlanElement } from '../types'

/**
 * « Vue 3D » of a plan (feedback 23/11/2026): the room with its walls, the tables dressed,
 * chairs, stage, dance floor, arch… to scale, turned with the finger or the mouse. Read only:
 * the plan is edited in 2D, the 3D follows. Loaded on demand (three.js is a large library).
 */
const props = defineProps<{
  length: number
  width: number
  elements: PlanElement[]
}>()
const { t } = useI18n()

const host = ref<HTMLDivElement | null>(null)
const failed = ref(false)
const walls = ref(true)

const WALL_HEIGHT = 3
const COLORS = {
  floor: 0xf3ece2,
  wall: 0xffffff,
  cloth: 0xffffff,
  chair: 0xd9cff5,
  chairFrame: 0xb8a6ea,
  stage: 0xc9a46b,
  dance: 0xf7d6e6,
  buffet: 0xdff4ec,
  bar: 0xf6c9b0,
  dj: 0x4a4769,
  entrance: 0x0e8f69,
  arch: 0xf2f2f2,
  flower: 0xe58bb5,
  pillar: 0xd6d2e6,
  leaf: 0x6fae83,
}

let renderer: THREE.WebGLRenderer | null = null
let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let controls: OrbitControls | null = null
let content: THREE.Group | null = null
let wallGroup: THREE.Group | null = null
let resize: ResizeObserver | null = null
let frame = 0
const disposables: { dispose: () => void }[] = []

function material(color: number, extra: THREE.MeshStandardMaterialParameters = {}) {
  const made = new THREE.MeshStandardMaterial({ color, roughness: 0.8, ...extra })
  disposables.push(made)
  return made
}
function geometry<T extends THREE.BufferGeometry>(made: T): T {
  disposables.push(made)
  return made
}
function mesh(geo: THREE.BufferGeometry, mat: THREE.Material): THREE.Mesh {
  const made = new THREE.Mesh(geo, mat)
  made.castShadow = true
  made.receiveShadow = true
  return made
}

/** A floating name (table number, text) drawn on a canvas. */
function label(text: string, size = 0.45): THREE.Sprite {
  const canvas = document.createElement('canvas')
  const context = canvas.getContext('2d')!
  const font = 64
  context.font = `700 ${font}px Montserrat, Arial, sans-serif`
  const width = Math.ceil(context.measureText(text).width) + 48
  canvas.width = width
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
  disposables.push(texture, mat)
  const sprite = new THREE.Sprite(mat)
  sprite.scale.set((size * canvas.width) / canvas.height, size, 1)
  sprite.renderOrder = 10
  return sprite
}

// --- Shared pieces ----------------------------------------------------------------------------
let pieces: ReturnType<typeof makePieces> | null = null
function makePieces() {
  return {
    seat: geometry(new THREE.BoxGeometry(CHAIR, 0.06, CHAIR)),
    back: geometry(new THREE.BoxGeometry(CHAIR, 0.45, 0.05)),
    leg: geometry(new THREE.CylinderGeometry(0.02, 0.02, 0.45, 6)),
    chair: material(COLORS.chair),
    frame: material(COLORS.chairFrame, { metalness: 0.3, roughness: 0.4 }),
    cloth: material(COLORS.cloth, { roughness: 0.95 }),
    flower: material(COLORS.flower),
    leaf: material(COLORS.leaf),
  }
}

/** A chair facing its table: the back on the local -z side (as drawn in 2D). */
function chair(): THREE.Group {
  const p = pieces!
  const group = new THREE.Group()
  const seat = mesh(p.seat, p.chair)
  seat.position.y = 0.45
  const back = mesh(p.back, p.frame)
  back.position.set(0, 0.7, -CHAIR / 2 + 0.025)
  group.add(seat, back)
  for (const [x, z] of [
    [-1, -1],
    [1, -1],
    [-1, 1],
    [1, 1],
  ] as const) {
    const leg = mesh(p.leg, p.frame)
    leg.position.set((x * CHAIR) / 2.4, 0.225, (z * CHAIR) / 2.4)
    group.add(leg)
  }
  return group
}

function centrepiece(): THREE.Group {
  const p = pieces!
  const group = new THREE.Group()
  const vase = mesh(geometry(new THREE.CylinderGeometry(0.06, 0.08, 0.2, 12)), p.leaf)
  vase.position.y = 0.86
  const bouquet = mesh(geometry(new THREE.SphereGeometry(0.16, 14, 10)), p.flower)
  bouquet.position.y = 1.02
  group.add(vase, bouquet)
  return group
}

function box(w: number, height: number, d: number, color: number, y = height / 2) {
  const made = mesh(geometry(new THREE.BoxGeometry(w, height, d)), material(color))
  made.position.y = y
  return made
}

/** One element of the plan, centred on its own origin, in metres. */
function build(element: PlanElement): THREE.Group {
  const group = new THREE.Group()
  const { w, h } = element
  // Chairs of tables and rows, from the same layout as the 2D plan.
  for (const spot of chairsOf(element)) {
    const seat = chair()
    seat.position.set(spot.x - w / 2, 0, spot.y - h / 2)
    seat.rotation.y = -(spot.rotation * Math.PI) / 180
    group.add(seat)
  }
  switch (element.type) {
    case 'round_table': {
      const r = Math.min(w, h) / 2
      const cloth = mesh(geometry(new THREE.CylinderGeometry(r, r + 0.04, 0.76, 40)), pieces!.cloth)
      cloth.position.y = 0.38
      group.add(cloth, centrepiece())
      break
    }
    case 'rect_table': {
      const top = mesh(geometry(new THREE.BoxGeometry(w, 0.76, h)), pieces!.cloth)
      top.position.y = 0.38
      group.add(top)
      const flowers = Math.max(1, Math.round(w / 1.6))
      for (let i = 0; i < flowers; i++) {
        const piece = centrepiece()
        piece.position.x = (w * (i + 0.5)) / flowers - w / 2
        group.add(piece)
      }
      break
    }
    case 'chair': {
      const single = chair()
      single.scale.set(w / CHAIR, 1, h / CHAIR)
      group.add(single)
      break
    }
    case 'stage':
      group.add(box(w, 0.6, h, COLORS.stage))
      break
    case 'dance_floor': {
      const floor = box(w, 0.03, h, COLORS.dance)
      ;(floor.material as THREE.MeshStandardMaterial).roughness = 0.15
      ;(floor.material as THREE.MeshStandardMaterial).metalness = 0.2
      group.add(floor)
      break
    }
    case 'buffet':
      group.add(box(w, 0.9, h, COLORS.buffet))
      break
    case 'bar':
      group.add(box(w, 1.1, h, COLORS.bar))
      break
    case 'dj': {
      group.add(box(w, 1, h, COLORS.dj))
      const speaker = box(0.35, 1.4, 0.35, 0x2b2946)
      speaker.position.x = -w / 2 - 0.3
      const other = speaker.clone()
      other.position.x = w / 2 + 0.3
      group.add(speaker, other)
      break
    }
    case 'entrance': {
      group.add(box(w, 0.02, Math.max(h, 0.3), COLORS.entrance))
      for (const side of [-1, 1]) {
        const post = box(0.12, 2.3, 0.12, COLORS.entrance)
        post.position.x = (side * w) / 2
        group.add(post)
      }
      break
    }
    case 'decor': {
      // A floral arch across the width.
      const arch = mesh(
        geometry(new THREE.TorusGeometry(w / 2, 0.07, 10, 40, Math.PI)),
        material(COLORS.arch),
      )
      arch.position.y = 0
      arch.scale.y = Math.max(1, 2.2 / (w / 2))
      group.add(arch)
      for (let i = 0; i <= 8; i++) {
        const angle = (Math.PI * i) / 8
        const bloom = mesh(geometry(new THREE.SphereGeometry(0.13, 10, 8)), pieces!.flower)
        bloom.position.set((Math.cos(angle) * w) / 2, Math.sin(angle) * Math.max(w / 2, 2.2), 0)
        group.add(bloom)
      }
      break
    }
    case 'pillar':
      group.add(box(w, WALL_HEIGHT, h, COLORS.pillar))
      break
    case 'text':
      break
  }
  const name =
    element.type === 'text' || isTable(element.type) || element.label
      ? element.label || (element.type === 'chair' ? '' : t(`floorplans.types.${element.type}`))
      : ['stage', 'dance_floor', 'buffet', 'bar', 'dj', 'entrance'].includes(element.type)
        ? t(`floorplans.types.${element.type}`)
        : ''
  if (name && element.type !== 'chair' && element.type !== 'pillar') {
    const sprite = label(name, element.type === 'text' ? 0.55 : 0.38)
    sprite.position.y = element.type === 'decor' ? 3.2 : element.type === 'text' ? 1.8 : 1.45
    group.add(sprite)
  }
  return group
}

// --- Scene ------------------------------------------------------------------------------------
function rebuild(): void {
  if (!scene) return
  for (const old of [content, wallGroup]) if (old) scene.remove(old)
  for (const item of disposables.splice(0)) item.dispose()
  pieces = makePieces()

  const L = Math.max(1, props.length)
  const W = Math.max(1, props.width)
  content = new THREE.Group()

  const floor = mesh(geometry(new THREE.PlaneGeometry(L, W)), material(COLORS.floor))
  floor.rotation.x = -Math.PI / 2
  floor.castShadow = false
  content.add(floor)
  const grid = new THREE.GridHelper(Math.max(L, W), Math.round(Math.max(L, W)), 0xd6cbbb, 0xe7ded1)
  grid.scale.set(L / Math.max(L, W), 1, W / Math.max(L, W))
  grid.position.y = 0.002
  disposables.push(grid.geometry, grid.material)
  content.add(grid)

  for (const element of props.elements) {
    const item = build(element)
    item.position.set(element.x + element.w / 2 - L / 2, 0, element.y + element.h / 2 - W / 2)
    item.rotation.y = -((element.rotation || 0) * Math.PI) / 180
    content.add(item)
  }
  scene.add(content)

  wallGroup = new THREE.Group()
  const wall = material(COLORS.wall, { transparent: true, opacity: 0.35, side: THREE.DoubleSide })
  const t2 = 0.15
  for (const [w, d, x, z] of [
    [L + t2 * 2, t2, 0, -W / 2 - t2 / 2],
    [L + t2 * 2, t2, 0, W / 2 + t2 / 2],
    [t2, W, -L / 2 - t2 / 2, 0],
    [t2, W, L / 2 + t2 / 2, 0],
  ] as const) {
    const piece = mesh(geometry(new THREE.BoxGeometry(w, WALL_HEIGHT, d)), wall)
    piece.castShadow = false
    piece.position.set(x, WALL_HEIGHT / 2, z)
    wallGroup.add(piece)
  }
  wallGroup.visible = walls.value
  scene.add(wallGroup)
}

function view(kind: 'overview' | 'top' | 'guest'): void {
  if (!camera || !controls) return
  const L = Math.max(1, props.length)
  const W = Math.max(1, props.width)
  const size = Math.max(L, W)
  controls.target.set(0, 0.5, 0)
  if (kind === 'top') {
    camera.position.set(0, size * 1.25, 0.01)
  } else if (kind === 'guest') {
    // From the entrance when there is one, else from the middle of the front wall.
    const door = props.elements.find((e) => e.type === 'entrance')
    const x = door ? door.x + door.w / 2 - L / 2 : 0
    const z = door ? door.y + door.h / 2 - W / 2 : W / 2 - 0.5
    camera.position.set(x * 0.92, 1.6, z * 0.92)
    controls.target.set(0, 1.1, 0)
  } else {
    camera.position.set(L * 0.55, size * 0.65, W * 0.95)
  }
  controls.update()
}

function render(): void {
  frame = requestAnimationFrame(render)
  controls?.update()
  if (renderer && scene && camera) renderer.render(scene, camera)
}

onMounted(() => {
  if (!host.value) return
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true })
  } catch {
    failed.value = true
    return
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.outputColorSpace = THREE.SRGBColorSpace
  host.value.appendChild(renderer.domElement)

  scene = new THREE.Scene()
  scene.background = new THREE.Color(0xf5f4fa)
  scene.add(new THREE.HemisphereLight(0xffffff, 0xd8cfc2, 1.6))
  const sun = new THREE.DirectionalLight(0xffffff, 1.6)
  const size = Math.max(props.length, props.width)
  sun.position.set(size * 0.4, size * 0.9, size * 0.5)
  sun.castShadow = true
  sun.shadow.mapSize.set(1024, 1024)
  Object.assign(sun.shadow.camera, {
    left: -size,
    right: size,
    top: size,
    bottom: -size,
    near: 0.5,
    far: size * 3,
  })
  scene.add(sun)

  camera = new THREE.PerspectiveCamera(50, 1, 0.1, 2000)
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.maxPolarAngle = Math.PI / 2 - 0.03 // never under the floor
  controls.minDistance = 1
  controls.maxDistance = size * 4

  const fit = () => {
    if (!host.value || !renderer || !camera) return
    const width = host.value.clientWidth
    const height = Math.max(320, Math.min(640, Math.round(width * 0.62)))
    renderer.setSize(width, height)
    camera.aspect = width / height
    camera.updateProjectionMatrix()
  }
  resize = new ResizeObserver(fit)
  resize.observe(host.value)
  fit()
  rebuild()
  view('overview')
  render()
})

let pending: ReturnType<typeof setTimeout> | null = null
watch(
  () => [props.length, props.width, JSON.stringify(props.elements)],
  () => {
    if (pending) clearTimeout(pending)
    pending = setTimeout(rebuild, 150)
  },
)
watch(walls, (value) => {
  if (wallGroup) wallGroup.visible = value
})

onBeforeUnmount(() => {
  cancelAnimationFrame(frame)
  if (pending) clearTimeout(pending)
  resize?.disconnect()
  controls?.dispose()
  for (const item of disposables.splice(0)) item.dispose()
  renderer?.dispose()
  renderer?.domElement.remove()
  renderer = null
  scene = null
})

/** The current view as a PNG (to download or send on WhatsApp). */
function snapshot(): Promise<Blob> {
  return new Promise((resolve, reject) => {
    if (!renderer || !scene || !camera) return reject(new Error(t('floorplans.imageError')))
    renderer.render(scene, camera)
    renderer.domElement.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error(t('floorplans.imageError')))),
      'image/png',
    )
  })
}
defineExpose({ snapshot })
</script>

<template>
  <div class="relative">
    <div
      v-if="failed"
      class="flex h-[320px] items-center justify-center p-6 text-center text-muted"
    >
      {{ t('floorplans.view3d.unsupported') }}
    </div>
    <div ref="host" class="w-full touch-none" />
    <div v-if="!failed" class="absolute top-2 left-2 flex flex-wrap gap-1.5">
      <button
        v-for="kind in ['overview', 'top', 'guest'] as const"
        :key="kind"
        type="button"
        class="rounded-[8px] border border-line bg-surface px-2.5 py-1 text-[12.5px] font-semibold text-ink-2 shadow-[var(--shadow)] hover:text-violet"
        @click="view(kind)"
      >
        {{ t(`floorplans.view3d.${kind}`) }}
      </button>
      <label
        class="inline-flex items-center gap-1.5 rounded-[8px] border border-line bg-surface px-2.5 py-1 text-[12.5px] font-semibold text-ink-2 shadow-[var(--shadow)]"
      >
        <input v-model="walls" type="checkbox" class="accent-[var(--violet)]" />
        {{ t('floorplans.view3d.walls') }}
      </label>
    </div>
    <p
      v-if="!failed"
      class="pointer-events-none absolute right-2 bottom-2 rounded-[8px] bg-surface px-2 py-1 text-[11.5px] text-muted"
    >
      {{ t('floorplans.view3d.help') }}
    </p>
  </div>
</template>

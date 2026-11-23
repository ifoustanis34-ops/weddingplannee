<script setup lang="ts">
import { ArrowDown, ArrowLeft, ArrowRight, ArrowUp, DoorOpen, LogOut } from '@lucide/vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { isTable } from '../elements'
import { Kit } from '../scene3d/objects'
import { floorTexture, WALL_COLORS } from '../scene3d/textures'
import { Walker } from '../scene3d/walk'
import { type Ambiance, DEFAULT_AMBIANCE, type PlanElement } from '../types'

/**
 * « Vue 3D » of a plan (feedback 23/11/2026): the room dressed to scale — floor, walls,
 * ceiling, tables, chairs, stage, dance floor, flowers, chandeliers — by day or in the evening.
 * Turned around from above, or visited on foot (« Entrer dans la salle »). Read only: the plan
 * is edited in 2D, the 3D follows. Loaded on demand (three.js is a large library).
 */
const props = defineProps<{
  length: number
  width: number
  elements: PlanElement[]
  ambiance?: Ambiance
}>()
const { t } = useI18n()

const host = ref<HTMLDivElement | null>(null)
const failed = ref(false)
const showWalls = ref(true)
const walking = ref(false)

let renderer: THREE.WebGLRenderer | null = null
let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let controls: OrbitControls | null = null
let walker: Walker | null = null
let room: THREE.Group | null = null
let walls: THREE.Group | null = null
let ceiling: THREE.Mesh | null = null
let sun: THREE.DirectionalLight | null = null
let hemi: THREE.HemisphereLight | null = null
let kit: Kit | null = null
let resize: ResizeObserver | null = null
let frame = 0
const clock = new THREE.Clock()

const currentAmbiance = (): Ambiance => ({ ...DEFAULT_AMBIANCE, ...(props.ambiance ?? {}) })
const outdoors = () => currentAmbiance().walls === 'none'

function nameOf(element: PlanElement): string {
  if (element.label) return element.label
  if (element.type === 'chair' || element.type === 'chair_row') return ''
  if (isTable(element.type) && element.type !== 'head_table') return ''
  return t(`floorplans.types.${element.type}`)
}

// --- Scene ------------------------------------------------------------------------------------
function rebuild(): void {
  if (!scene) return
  for (const old of [room, walls]) if (old) scene.remove(old)
  for (const item of kit?.disposables.splice(0) ?? []) item.dispose()
  ceiling = null

  const look = currentAmbiance()
  const evening = look.light === 'evening'
  const L = Math.max(1, props.length)
  const W = Math.max(1, props.width)
  const H = look.height
  kit = new Kit(evening, H, nameOf)

  // Sky and light: day or evening, inside or outdoors.
  scene.background = new THREE.Color(evening ? 0x14122b : outdoors() ? 0xbfe0f5 : 0xf5f4fa)
  scene.fog = outdoors() && !evening ? new THREE.Fog(0xbfe0f5, 40, 160) : null
  if (hemi) hemi.intensity = evening ? 0.35 : 1.5
  if (sun) {
    sun.intensity = evening ? 0.15 : outdoors() ? 2.4 : 1.4
    sun.castShadow = !evening
  }

  room = new THREE.Group()
  const floorMap = floorTexture(look.floor, L, W)
  kit.disposables.push(floorMap)
  const floor = kit.mesh(
    kit.geometry(new THREE.PlaneGeometry(L, W)),
    kit.material(0xffffff, { map: floorMap, roughness: look.floor === 'marble' ? 0.25 : 0.85 }),
    false,
  )
  floor.rotation.x = -Math.PI / 2
  room.add(floor)
  if (outdoors()) {
    // The ground around a garden or a beach.
    const ground = kit.mesh(
      kit.geometry(new THREE.PlaneGeometry(L + 80, W + 80)),
      kit.material(look.floor === 'grass' ? 0x6f9e58 : 0xd9cdb4),
      false,
    )
    ground.rotation.x = -Math.PI / 2
    ground.position.y = -0.01
    room.add(ground)
  }

  for (const element of props.elements) {
    const item = kit.build(element)
    item.position.set(element.x + element.w / 2 - L / 2, 0, element.y + element.h / 2 - W / 2)
    item.rotation.y = -((element.rotation || 0) * Math.PI) / 180
    room.add(item)
  }
  // Evening without chandeliers: a few warm lights over the room.
  if (evening && kit.lights < 3) {
    for (const [x, z] of [
      [-L / 4, -W / 4],
      [L / 4, -W / 4],
      [-L / 4, W / 4],
      [L / 4, W / 4],
    ] as const) {
      const light = new THREE.PointLight(0xffc98a, 5, Math.max(L, W), 1.5)
      light.position.set(x, H - 0.3, z)
      room.add(light)
    }
  }
  scene.add(room)

  walls = new THREE.Group()
  if (!outdoors()) {
    const color = WALL_COLORS[look.walls as keyof typeof WALL_COLORS]
    const thick = 0.15
    const wallMaterial = kit.material(color, { side: THREE.DoubleSide, roughness: 0.95 })
    const seeThrough = kit.material(color, {
      transparent: true,
      opacity: 0.3,
      side: THREE.DoubleSide,
    })
    for (const [w, d, x, z] of [
      [L + thick * 2, thick, 0, -W / 2 - thick / 2],
      [L + thick * 2, thick, 0, W / 2 + thick / 2],
      [thick, W, -L / 2 - thick / 2, 0],
      [thick, W, L / 2 + thick / 2, 0],
    ] as const) {
      const piece = kit.mesh(kit.geometry(new THREE.BoxGeometry(w, H, d)), seeThrough, false)
      piece.userData.inside = wallMaterial
      piece.userData.outside = seeThrough
      piece.position.set(x, H / 2, z)
      walls.add(piece)
    }
    // Skirting and string lights along the walls in the evening.
    if (look.light === 'evening') {
      const bulb = kit.geometry(new THREE.SphereGeometry(0.04, 8, 6))
      const glow = kit.material(0xffe2a8, { emissive: 0xffc46b, emissiveIntensity: 2.2 })
      const step = 0.6
      for (let x = -L / 2; x <= L / 2; x += step) {
        for (const z of [-W / 2 + 0.05, W / 2 - 0.05]) {
          const b = kit.mesh(bulb, glow, false)
          b.position.set(x, H - 0.25 - Math.abs(Math.sin(x * 2)) * 0.15, z)
          walls.add(b)
        }
      }
    }
    ceiling = kit.mesh(
      kit.geometry(new THREE.PlaneGeometry(L, W)),
      kit.material(0xffffff, { side: THREE.DoubleSide }),
      false,
    )
    ceiling.rotation.x = Math.PI / 2
    ceiling.position.y = H
    walls.add(ceiling)
  }
  scene.add(walls)
  applyWalls()
  walker?.setRoom(L, W, props.elements, !outdoors())
}

/** Inside: opaque walls and the ceiling. From above: see-through walls, no ceiling. */
function applyWalls(): void {
  room?.traverse((child) => {
    if (!(child instanceof THREE.Sprite) || !child.userData.label) return
    child.visible = !walking.value || child.userData.label === 'table'
    // Seen from above, names stay readable over everything; on foot, things hide them.
    child.material.depthTest = walking.value
  })
  if (!walls) return
  walls.visible = walking.value || showWalls.value
  for (const child of walls.children) {
    if (child === ceiling) child.visible = walking.value
    else if (child instanceof THREE.Mesh && child.userData.inside)
      child.material = walking.value ? child.userData.inside : child.userData.outside
  }
}

// --- Views and visit --------------------------------------------------------------------------
function view(kind: 'overview' | 'top'): void {
  if (!camera || !controls) return
  if (walking.value) leave()
  const L = Math.max(1, props.length)
  const W = Math.max(1, props.width)
  const size = Math.max(L, W)
  controls.target.set(0, 0.5, 0)
  if (kind === 'top') camera.position.set(0, size * 1.25, 0.01)
  else camera.position.set(L * 0.55, size * 0.65, W * 0.95)
  controls.update()
}

function enter(): void {
  if (!camera || !controls || !walker) return
  walking.value = true
  controls.enabled = false
  camera.fov = 70
  camera.updateProjectionMatrix()
  walker.setRoom(props.length, props.width, props.elements, !outdoors())
  walker.enter(props.length, props.width, props.elements)
  applyWalls()
  host.value?.focus()
}

function leave(): void {
  if (!camera || !controls) return
  walking.value = false
  controls.enabled = true
  camera.fov = 50
  camera.updateProjectionMatrix()
  applyWalls()
  view('overview')
}

// Look around by dragging (mouse or finger) while walking.
let dragging: { x: number; y: number; id: number } | null = null
function down(event: PointerEvent): void {
  if (!walking.value) return
  dragging = { x: event.clientX, y: event.clientY, id: event.pointerId }
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
}
function move(event: PointerEvent): void {
  if (!dragging || dragging.id !== event.pointerId || !walker) return
  walker.look(event.clientX - dragging.x, event.clientY - dragging.y)
  dragging.x = event.clientX
  dragging.y = event.clientY
}
function up(event: PointerEvent): void {
  if (dragging?.id === event.pointerId) dragging = null
}

const KEYS = new Set([
  'arrowup',
  'arrowdown',
  'arrowleft',
  'arrowright',
  'w',
  'a',
  's',
  'd',
  'z',
  'q',
  'shift',
])
function keydown(event: KeyboardEvent): void {
  if (!walking.value || !walker) return
  const target = event.target as HTMLElement | null
  if (target?.closest('input, textarea, select')) return
  const key = event.key.toLowerCase()
  if (key === 'escape') return leave()
  if (!KEYS.has(key)) return
  event.preventDefault()
  walker.keys.add(key)
}
function keyup(event: KeyboardEvent): void {
  walker?.keys.delete(event.key.toLowerCase())
}
function press(direction: keyof Walker['pad'], on: boolean): void {
  if (walker) walker.pad[direction] = on
}

function render(): void {
  frame = requestAnimationFrame(render)
  const dt = Math.min(clock.getDelta(), 0.1)
  if (walking.value) walker?.step(dt)
  else controls?.update()
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
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  host.value.appendChild(renderer.domElement)

  scene = new THREE.Scene()
  hemi = new THREE.HemisphereLight(0xffffff, 0xd8cfc2, 1.5)
  scene.add(hemi)
  const size = Math.max(props.length, props.width)
  sun = new THREE.DirectionalLight(0xfff4e0, 1.4)
  sun.position.set(size * 0.4, size * 0.9, size * 0.5)
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

  camera = new THREE.PerspectiveCamera(50, 1, 0.05, 2000)
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.maxPolarAngle = Math.PI / 2 - 0.03 // never under the floor
  controls.minDistance = 1
  controls.maxDistance = size * 4
  walker = new Walker(camera)

  const fit = () => {
    if (!host.value || !renderer || !camera) return
    const width = host.value.clientWidth
    const height = Math.max(340, Math.min(680, Math.round(width * 0.62)))
    renderer.setSize(width, height)
    camera.aspect = width / height
    camera.updateProjectionMatrix()
  }
  resize = new ResizeObserver(fit)
  resize.observe(host.value)
  fit()
  rebuild()
  view('overview')
  window.addEventListener('keydown', keydown)
  window.addEventListener('keyup', keyup)
  render()
})

let pending: ReturnType<typeof setTimeout> | null = null
watch(
  () => [props.length, props.width, JSON.stringify(props.elements), JSON.stringify(props.ambiance)],
  () => {
    if (pending) clearTimeout(pending)
    pending = setTimeout(rebuild, 150)
  },
)
watch(showWalls, applyWalls)

onBeforeUnmount(() => {
  cancelAnimationFrame(frame)
  if (pending) clearTimeout(pending)
  window.removeEventListener('keydown', keydown)
  window.removeEventListener('keyup', keyup)
  resize?.disconnect()
  controls?.dispose()
  for (const item of kit?.disposables.splice(0) ?? []) item.dispose()
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

const PAD = [
  { key: 'forward', icon: ArrowUp, area: '[grid-area:1/2]' },
  { key: 'left', icon: ArrowLeft, area: '[grid-area:2/1]' },
  { key: 'back', icon: ArrowDown, area: '[grid-area:2/2]' },
  { key: 'right', icon: ArrowRight, area: '[grid-area:2/3]' },
] as const
</script>

<template>
  <div class="relative select-none">
    <div
      v-if="failed"
      class="flex h-[340px] items-center justify-center p-6 text-center text-muted"
    >
      {{ t('floorplans.view3d.unsupported') }}
    </div>
    <div
      ref="host"
      tabindex="-1"
      class="w-full touch-none outline-none"
      :class="walking ? 'cursor-grab active:cursor-grabbing' : ''"
      @pointerdown="down"
      @pointermove="move"
      @pointerup="up"
      @pointercancel="up"
    />

    <template v-if="!failed">
      <!-- Views -->
      <div class="absolute top-2 left-2 flex flex-wrap gap-1.5">
        <button
          v-if="!walking"
          type="button"
          class="inline-flex items-center gap-1.5 rounded-[8px] bg-violet px-3 py-1.5 text-[12.5px] font-bold text-violet-ink shadow-[var(--shadow)]"
          @click="enter"
        >
          <DoorOpen class="size-[15px]" aria-hidden="true" />{{ t('floorplans.view3d.enter') }}
        </button>
        <button
          v-else
          type="button"
          class="inline-flex items-center gap-1.5 rounded-[8px] bg-surface px-3 py-1.5 text-[12.5px] font-bold text-ink shadow-[var(--shadow)]"
          @click="leave"
        >
          <LogOut class="size-[15px]" aria-hidden="true" />{{ t('floorplans.view3d.leave') }}
        </button>
        <template v-if="!walking">
          <button
            v-for="kind in ['overview', 'top'] as const"
            :key="kind"
            type="button"
            class="rounded-[8px] border border-line bg-surface px-2.5 py-1 text-[12.5px] font-semibold text-ink-2 shadow-[var(--shadow)] hover:text-violet"
            @click="view(kind)"
          >
            {{ t(`floorplans.view3d.${kind}`) }}
          </button>
          <label
            v-if="ambiance?.walls !== 'none'"
            class="inline-flex items-center gap-1.5 rounded-[8px] border border-line bg-surface px-2.5 py-1 text-[12.5px] font-semibold text-ink-2 shadow-[var(--shadow)]"
          >
            <input v-model="showWalls" type="checkbox" class="accent-[var(--violet)]" />
            {{ t('floorplans.view3d.walls') }}
          </label>
        </template>
      </div>

      <!-- Walking pad (phones; arrows / ZQSD on a keyboard) -->
      <div
        v-if="walking"
        class="absolute bottom-3 left-3 grid grid-cols-[44px_44px_44px] grid-rows-[44px_44px] gap-1.5"
      >
        <button
          v-for="button in PAD"
          :key="button.key"
          type="button"
          class="flex items-center justify-center rounded-[10px] bg-surface text-ink shadow-[var(--shadow)] active:bg-violet active:text-violet-ink"
          :class="button.area"
          :aria-label="t(`floorplans.view3d.pad.${button.key}`)"
          @pointerdown.stop.prevent="press(button.key, true)"
          @pointerup="press(button.key, false)"
          @pointerleave="press(button.key, false)"
          @pointercancel="press(button.key, false)"
          @contextmenu.prevent
        >
          <component :is="button.icon" class="size-5" aria-hidden="true" />
        </button>
      </div>

      <p
        class="pointer-events-none absolute right-2 bottom-2 max-w-[60%] rounded-[8px] bg-surface px-2 py-1 text-right text-[11.5px] text-muted"
      >
        {{ walking ? t('floorplans.view3d.walkHelp') : t('floorplans.view3d.help') }}
      </p>
    </template>
  </div>
</template>

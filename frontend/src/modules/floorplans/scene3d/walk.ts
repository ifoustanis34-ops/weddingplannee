import * as THREE from 'three'

import { outerMargin } from '../elements'
import type { PlanElement } from '../types'
import { SOLID } from './objects'

/**
 * « Entrer dans la salle » (feedback 23/11/2026): walking in the room at eye height. Look by
 * dragging (mouse or finger), move with the arrows / ZQSD / WASD or the on-screen pad. Walls and
 * furniture stop the visitor (a circle of 25 cm), who slides along them.
 */
export const EYE = 1.65
const RADIUS = 0.25
const SPEED = 1.6 // m/s, a calm walk
const TURN = 0.0045 // radians per pixel dragged

/** A footprint on the floor, in room coordinates centred on the room (as in the scene). */
interface Box {
  cx: number
  cz: number
  hw: number
  hd: number
  cos: number
  sin: number
}

export class Walker {
  yaw = 0
  pitch = 0
  readonly keys = new Set<string>()
  /** Pressed buttons of the on-screen pad: forward, back, left, right. */
  readonly pad = { forward: false, back: false, left: false, right: false }
  private boxes: Box[] = []
  private halfL = 1
  private halfW = 1

  constructor(private readonly camera: THREE.PerspectiveCamera) {}

  /** Footprints of what blocks the way, from the plan. */
  setRoom(length: number, width: number, elements: PlanElement[], walls: boolean): void {
    this.halfL = walls ? length / 2 : length / 2 + 6
    this.halfW = walls ? width / 2 : width / 2 + 6
    this.boxes = elements
      .filter((e) => SOLID.has(e.type))
      .map((e) => {
        const margin = outerMargin(e)
        const angle = ((e.rotation || 0) * Math.PI) / 180
        return {
          cx: e.x + e.w / 2 - length / 2,
          cz: e.y + e.h / 2 - width / 2,
          hw: e.w / 2 + margin,
          hd: e.h / 2 + margin,
          cos: Math.cos(angle),
          sin: Math.sin(angle),
        }
      })
  }

  /** At the entrance (or the middle of the front wall), facing the room. */
  enter(length: number, width: number, elements: PlanElement[]): void {
    const door = elements.find((e) => e.type === 'entrance')
    let x = 0
    let z = width / 2 - 0.8
    if (door) {
      x = door.x + door.w / 2 - length / 2
      z = door.y + door.h / 2 - width / 2
      // One step inside, towards the centre.
      const towards = new THREE.Vector2(-x, -z).normalize().multiplyScalar(0.9)
      x += towards.x
      z += towards.y
    }
    x = THREE.MathUtils.clamp(x, -this.halfL + RADIUS, this.halfL - RADIUS)
    z = THREE.MathUtils.clamp(z, -this.halfW + RADIUS, this.halfW - RADIUS)
    if (this.blocked(x, z)) [x, z] = this.freeSpotNear(x, z)
    this.camera.position.set(x, EYE, z)
    this.yaw = Math.atan2(x, z) // look at the centre
    this.pitch = -0.05
    this.apply()
  }

  look(dx: number, dy: number): void {
    this.yaw -= dx * TURN
    this.pitch = THREE.MathUtils.clamp(this.pitch - dy * TURN, -1.1, 1.1)
    this.apply()
  }

  /** One frame of walking; `dt` in seconds. */
  step(dt: number): void {
    const k = this.keys
    const forward =
      Number(this.pad.forward || k.has('arrowup') || k.has('w') || k.has('z')) -
      Number(this.pad.back || k.has('arrowdown') || k.has('s'))
    const side =
      Number(this.pad.right || k.has('d')) - Number(this.pad.left || k.has('a') || k.has('q'))
    const turn = Number(k.has('arrowleft')) - Number(k.has('arrowright'))
    if (turn) {
      this.yaw += turn * dt * 1.8
      this.apply()
    }
    if (!forward && !side) return
    const distance = SPEED * dt * (k.has('shift') ? 1.8 : 1)
    const dirX = -Math.sin(this.yaw)
    const dirZ = -Math.cos(this.yaw)
    const moveX = (dirX * forward - dirZ * side) * distance
    const moveZ = (dirZ * forward + dirX * side) * distance
    const p = this.camera.position
    // Slide along what blocks: try both axes, then each alone.
    const tries: [number, number][] = [
      [p.x + moveX, p.z + moveZ],
      [p.x + moveX, p.z],
      [p.x, p.z + moveZ],
    ]
    for (const [x, z] of tries) {
      if (this.inside(x, z) && !this.blocked(x, z)) {
        p.x = x
        p.z = z
        break
      }
    }
  }

  private apply(): void {
    this.camera.rotation.set(this.pitch, this.yaw, 0, 'YXZ')
  }

  private inside(x: number, z: number): boolean {
    return Math.abs(x) <= this.halfL - RADIUS && Math.abs(z) <= this.halfW - RADIUS
  }

  private blocked(x: number, z: number): boolean {
    return this.boxes.some((b) => {
      // Into the element's own axes (its rotation is clockwise seen from above).
      const dx = x - b.cx
      const dz = z - b.cz
      const lx = dx * b.cos + dz * b.sin
      const lz = -dx * b.sin + dz * b.cos
      return Math.abs(lx) < b.hw + RADIUS && Math.abs(lz) < b.hd + RADIUS
    })
  }

  private freeSpotNear(x: number, z: number): [number, number] {
    for (let r = 0.5; r < 20; r += 0.5) {
      for (let a = 0; a < Math.PI * 2; a += Math.PI / 8) {
        const nx = x + Math.cos(a) * r
        const nz = z + Math.sin(a) * r
        if (this.inside(nx, nz) && !this.blocked(nx, nz)) return [nx, nz]
      }
    }
    return [0, 0]
  }
}

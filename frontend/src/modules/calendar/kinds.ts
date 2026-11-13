import {
  CalendarHeart,
  CircleCheck,
  Hammer,
  PackageCheck,
  PackageOpen,
  Truck,
  Undo2,
  Wallet,
  Wrench,
} from '@lucide/vue'
import type { Component } from 'vue'

import type { CalendarKind } from './api'

/**
 * Colors of §4.3: events ribbon, deliveries violet, setups fuchsia, pickups (teardown and
 * return too) coral, maintenance grey, expected payments gold; tasks stay outlined.
 */
export const KIND_STYLE: Record<CalendarKind, { chip: string; dot: string; icon: Component }> = {
  event: { chip: 'bg-ribbon text-white', dot: 'bg-fuchsia', icon: CalendarHeart },
  delivery: { chip: 'bg-violet-soft text-ink', dot: 'bg-violet', icon: Truck },
  setup: { chip: 'bg-fuchsia-soft text-ink', dot: 'bg-fuchsia', icon: Hammer },
  teardown: { chip: 'bg-coral-soft text-ink', dot: 'bg-coral', icon: PackageOpen },
  pickup: { chip: 'bg-coral-soft text-ink', dot: 'bg-coral', icon: PackageCheck },
  return: { chip: 'bg-coral-soft text-ink', dot: 'bg-coral', icon: Undo2 },
  maintenance: { chip: 'bg-grey-soft text-ink-2', dot: 'bg-muted', icon: Wrench },
  payment: { chip: 'bg-gold-soft text-ink', dot: 'bg-gold-bright', icon: Wallet },
  task: { chip: 'border border-line-2 bg-surface text-ink-2', dot: 'bg-ink-2', icon: CircleCheck },
}

/** Icon tint on light chips (the ribbon keeps white). */
export const ICON_TINT: Partial<Record<CalendarKind, string>> = {
  delivery: 'text-violet',
  setup: 'text-fuchsia',
  teardown: 'text-coral',
  pickup: 'text-coral',
  return: 'text-coral',
  maintenance: 'text-muted',
  payment: 'text-gold',
}

/** Legend and filter groups: teardown, pickup and return share the coral « Récupérations ». */
export const KIND_GROUPS: { key: string; kinds: CalendarKind[] }[] = [
  { key: 'event', kinds: ['event'] },
  { key: 'delivery', kinds: ['delivery'] },
  { key: 'setup', kinds: ['setup'] },
  { key: 'pickup', kinds: ['teardown', 'pickup', 'return'] },
  { key: 'maintenance', kinds: ['maintenance'] },
  { key: 'payment', kinds: ['payment'] },
  { key: 'task', kinds: ['task'] },
]

/** MIME type of a dragged reservation (no other drop is accepted). */
export const DRAG_TYPE = 'application/x-wedivo-reservation'

/** True while a reservation is dragged over a day (only then may it be dropped). */
export function acceptsDrop(event: DragEvent): boolean {
  return Array.from(event.dataTransfer?.types ?? []).includes(DRAG_TYPE)
}

/** The dragged reservation and the day it was taken from. */
export function readDrop(event: DragEvent): { reservation: string; date: string } | null {
  try {
    const data = JSON.parse(event.dataTransfer?.getData(DRAG_TYPE) ?? '') as unknown
    if (
      data &&
      typeof data === 'object' &&
      'reservation' in data &&
      'date' in data &&
      typeof data.reservation === 'string' &&
      typeof data.date === 'string'
    )
      return { reservation: data.reservation, date: data.date }
  } catch {
    // not one of ours
  }
  return null
}

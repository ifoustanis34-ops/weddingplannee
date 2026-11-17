import {
  Banknote,
  Bell,
  CalendarCheck,
  Clock,
  FileText,
  ListChecks,
  Package,
  TriangleAlert,
  Wallet,
} from '@lucide/vue'
import type { Component } from 'vue'

/** Icon of a notification by its kind (server `notifications.flow`, `push.notify`). */
export const KIND_ICON: Record<string, Component> = {
  mission: CalendarCheck,
  task: ListChecks,
  reservation: Package,
  payment: Wallet,
  pay: Banknote,
  attendance: Clock,
  quote: FileText,
  alert: TriangleAlert,
}
export const kindIcon = (kind: string): Component => KIND_ICON[kind] ?? Bell

/** How long ago, as an i18n key under `notifications.ago.` and its values (no text here). */
export type Ago = {
  key: 'now' | 'minutes' | 'hours' | 'yesterday' | 'days' | 'date'
  n: number
  date: string
}

export function ago(iso: string, now: Date = new Date()): Ago {
  const at = new Date(iso)
  const date = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short' }).format(at)
  const seconds = Math.max(0, Math.round((now.getTime() - at.getTime()) / 1000))
  if (seconds < 60) return { key: 'now', n: 0, date }
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return { key: 'minutes', n: minutes, date }
  const hours = Math.round(minutes / 60)
  if (hours < 24) return { key: 'hours', n: hours, date }
  const days = Math.round(hours / 24)
  if (days === 1) return { key: 'yesterday', n: 1, date }
  if (days < 7) return { key: 'days', n: days, date }
  return { key: 'date', n: days, date }
}

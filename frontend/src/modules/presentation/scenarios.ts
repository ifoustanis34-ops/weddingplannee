import type { RouteLocationRaw } from 'vue-router'

import type { Role } from '@/api/auth'
import { clientsApi } from '@/modules/crm/api'
import { reservationsApi } from '@/modules/reservations/api'
import { stockApi } from '@/modules/stock/api'

/**
 * Presentation mode (feedback 16/11/2026): journeys the app plays by itself on the demo agency's
 * fictitious data, while the presenter comments. Each step may switch to another role (the
 * storekeeper's or the staff's point of view), opens a screen — sometimes a real record of the
 * demo — and points at what to look at. Texts: `presentation.scenarios.<id>.steps.<key>`.
 */
export interface DemoStep {
  key: string
  /** Role to show this step with (switched without password, demo agencies only). */
  role?: Role
  /** Screen to open: fixed, or found among the demo's records. */
  route: RouteLocationRaw | (() => Promise<RouteLocationRaw>)
  /** CSS selector of what to point at (menu entry, open record…). */
  target?: string
  /** Display time in ms at normal speed. */
  duration?: number
}

export interface DemoScenario {
  id: string
  icon: 'building' | 'calendar' | 'package' | 'users' | 'wallet'
  /** Roles shown, in order (chips on the selection page). */
  roles: Role[]
  steps: DemoStep[]
}

const menu = (key: string) => `[data-tour="${key}"]`
const RECORD = '[role="dialog"]'

/** A reservation of the demo in this tab (the most relevant one first). */
async function reservation(...tabs: string[]): Promise<RouteLocationRaw> {
  for (const tab of tabs) {
    const rows = await reservationsApi.list({ tab })
    const first = rows[0]
    if (first) return { name: 'reservations', query: { onglet: tab, reservation: first.id } }
  }
  return { name: 'reservations' }
}
async function client(): Promise<RouteLocationRaw> {
  const page = await clientsApi.list({ ordering: '-revenue' })
  const first = page.results[0]
  return first ? { name: 'clients', query: { client: first.id } } : { name: 'clients' }
}
async function item(status: string): Promise<RouteLocationRaw> {
  const items = await stockApi.items({ status })
  const first = items[0]
  return first ? { name: 'stock', query: { article: first.id } } : { name: 'stock' }
}

export const SCENARIOS: DemoScenario[] = [
  {
    id: 'agency',
    icon: 'building',
    roles: ['owner'],
    steps: [
      { key: 'dashboard', role: 'owner', route: { name: 'dashboard' }, target: menu('dashboard') },
      { key: 'reservations', route: { name: 'reservations' }, target: menu('reservations') },
      { key: 'ongoing', route: () => reservation('ongoing', 'confirmed'), target: RECORD },
      {
        key: 'calendar',
        route: { name: 'calendar', query: { vue: 'logistique' } },
        target: menu('calendar'),
      },
      {
        key: 'availability',
        route: { name: 'stock', query: { onglet: 'availability' } },
        target: menu('stock'),
      },
      {
        key: 'treasury',
        route: { name: 'finance', query: { onglet: 'tresorerie' } },
        target: menu('finance'),
      },
      { key: 'reports', route: { name: 'reports' }, target: menu('reports') },
    ],
  },
  {
    id: 'rental',
    icon: 'calendar',
    roles: ['planner'],
    steps: [
      { key: 'client', role: 'planner', route: client, target: RECORD, duration: 8000 },
      {
        key: 'confirmed',
        route: () => reservation('confirmed', 'awaiting_deposit'),
        target: RECORD,
        duration: 9000,
      },
      {
        key: 'partners',
        route: { name: 'stock', query: { onglet: 'partners' } },
        target: menu('stock'),
      },
      {
        key: 'logistics',
        route: { name: 'calendar', query: { vue: 'semaine' } },
        target: menu('calendar'),
      },
      { key: 'quotes', route: { name: 'quotes' }, target: menu('quotes') },
      {
        key: 'invoices',
        route: { name: 'finance', query: { onglet: 'factures' } },
        target: menu('finance'),
      },
    ],
  },
  {
    id: 'storekeeper',
    icon: 'package',
    roles: ['storekeeper'],
    steps: [
      { key: 'home', role: 'storekeeper', route: { name: 'dashboard' }, target: menu('dashboard') },
      { key: 'stock', route: { name: 'stock' }, target: menu('stock') },
      { key: 'item', route: () => item('low'), target: RECORD, duration: 8000 },
      { key: 'checkout', route: () => reservation('confirmed', 'ongoing'), target: RECORD },
      { key: 'movements', route: { name: 'movements' }, target: menu('movements') },
      {
        key: 'inventory',
        route: { name: 'stock', query: { onglet: 'inventory' } },
        target: menu('stock'),
      },
    ],
  },
  {
    id: 'field',
    icon: 'users',
    roles: ['team_lead', 'staff'],
    steps: [
      { key: 'leadSpace', role: 'team_lead', route: { name: 'dashboard' }, duration: 8000 },
      { key: 'leadMissions', route: { name: 'missions' }, target: menu('missions') },
      { key: 'staffSpace', role: 'staff', route: { name: 'dashboard' }, duration: 8000 },
      { key: 'staffMissions', route: { name: 'missions' }, target: menu('missions') },
      { key: 'tasks', role: 'owner', route: { name: 'tasks' }, target: menu('tasks') },
      { key: 'attendance', route: { name: 'attendance' }, target: menu('attendance') },
    ],
  },
  {
    id: 'money',
    icon: 'wallet',
    roles: ['owner'],
    steps: [
      {
        key: 'treasury',
        role: 'owner',
        route: { name: 'finance', query: { onglet: 'tresorerie' } },
        target: menu('finance'),
      },
      { key: 'invoices', route: { name: 'finance', query: { onglet: 'factures' } } },
      { key: 'profitability', route: { name: 'finance', query: { onglet: 'rentabilite' } } },
      { key: 'staff', route: { name: 'staff' }, target: menu('staff') },
      {
        key: 'payDay',
        route: { name: 'pay', query: { onglet: 'jour' } },
        target: menu('pay'),
      },
      { key: 'salaries', route: { name: 'pay', query: { onglet: 'salaires' } } },
      { key: 'reports', route: { name: 'reports' }, target: menu('reports') },
    ],
  },
]

export const DEFAULT_DURATION = 7000
export const SPEEDS = [0.75, 1, 1.5] as const

/** Display time of a step at a speed (1 = normal; 1.5 = faster). */
export function stepDuration(step: DemoStep, speed: number): number {
  return Math.round((step.duration ?? DEFAULT_DURATION) / speed)
}

/** Total length of a scenario in seconds at normal speed (shown on the selection page). */
export function scenarioSeconds(scenario: DemoScenario): number {
  return Math.round(
    scenario.steps.reduce((sum, s) => sum + (s.duration ?? DEFAULT_DURATION), 0) / 1000,
  )
}

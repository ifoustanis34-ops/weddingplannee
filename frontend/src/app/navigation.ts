import {
  ArrowLeftRight,
  BarChart3,
  Banknote,
  BookOpen,
  ClipboardCheck,
  ListChecks,
  Briefcase,
  Calendar,
  CalendarCheck,
  Clock,
  FileText,
  Heart,
  House,
  Mail,
  Package,
  Settings,
  UserCog,
  Users,
  Wallet,
} from '@lucide/vue'
import type { Component } from 'vue'

import { FIELD_ROLES, type Role } from '@/api/auth'
import { FEATURES } from '@/app/features'

export type NavGroup =
  'pilotage' | 'activite' | 'materiel' | 'finances' | 'equipe' | 'evenementiel' | 'espace'

export interface NavItem {
  key: string
  /** i18n key under `nav.` */
  label: string
  icon: Component
  /** Shown only while this module is on for the space (« Mariages », 13/11/2026). */
  module?: 'weddings'
  routeName: string
  group: NavGroup
  /** Modules appear only once built: the UI never promises what is not integrated. */
  ready: boolean
  roles?: Role[]
  /** Mobile bottom tab bar (reservations-stock.md §3), short label `nav.tabs.<key>`. */
  mobileTab?: boolean
  /** Fills the tab bar while a `mobileTab` module is not built yet (clients, quotes). */
  mobileFallback?: boolean
  /** Product phase: once built, the menu shows « P2 » / « P3 » while `FEATURES.phaseTags` is on. */
  phase?: 2 | 3
  /** Reachable (palette, links) but not listed in the menu. */
  hiddenFromMenu?: boolean
}

const MONEY_ROLES: Role[] = ['owner', 'planner', 'accountant']
const STOCK_ROLES: Role[] = ['owner', 'planner', 'assistant', 'accountant', 'storekeeper']

/** Menu of reservations-stock.md §3, in this order. */
export const NAV_ITEMS: NavItem[] = [
  // Pilotage
  {
    key: 'dashboard',
    label: 'dashboard',
    icon: House,
    routeName: 'dashboard',
    group: 'pilotage',
    ready: true,
    mobileTab: true,
  },
  // Activité
  {
    key: 'reservations',
    label: 'reservations',
    icon: CalendarCheck,
    routeName: 'reservations',
    group: 'activite',
    ready: true,
    mobileTab: true,
    roles: STOCK_ROLES,
  },
  {
    key: 'calendar',
    label: 'calendar',
    icon: Calendar,
    routeName: 'calendar',
    group: 'activite',
    ready: true,
  },
  {
    key: 'clients',
    label: 'clients',
    icon: Users,
    routeName: 'clients',
    group: 'activite',
    ready: true,
    mobileFallback: true,
  },
  {
    key: 'quotes',
    label: 'quotes',
    icon: FileText,
    routeName: 'quotes',
    group: 'activite',
    ready: true,
    mobileFallback: true,
  },
  // The catalogue lives in Paramètres › Catalogue and « Gérer le catalogue » of the quotes;
  // planners, who edit it too, keep the /catalogue page.
  {
    key: 'catalog',
    label: 'catalog',
    icon: BookOpen,
    routeName: 'catalog',
    group: 'activite',
    ready: true,
    hiddenFromMenu: true,
  },
  // Matériel
  {
    key: 'stock',
    label: 'stock',
    icon: Package,
    routeName: 'stock',
    group: 'materiel',
    ready: true,
    mobileTab: true,
    roles: STOCK_ROLES,
  },
  {
    key: 'movements',
    label: 'movements',
    icon: ArrowLeftRight,
    routeName: 'movements',
    group: 'materiel',
    ready: true,
    roles: STOCK_ROLES,
  },
  // Finances
  {
    key: 'finance',
    label: 'finance',
    icon: Wallet,
    routeName: 'finance',
    group: 'finances',
    ready: true,
    mobileTab: true,
    roles: MONEY_ROLES,
  },
  {
    key: 'reports',
    label: 'reports',
    icon: BarChart3,
    routeName: 'reports',
    group: 'finances',
    ready: true,
    roles: ['owner', 'accountant'],
  },
  // Équipe
  {
    key: 'staff',
    label: 'staff',
    icon: UserCog,
    routeName: 'staff',
    group: 'equipe',
    ready: true,
    roles: ['owner', 'planner', 'assistant', 'accountant'],
  },
  {
    key: 'tasks',
    label: 'tasks',
    icon: ListChecks,
    routeName: 'tasks',
    group: 'equipe',
    ready: true,
    roles: ['owner', 'planner', 'assistant', 'accountant'],
  },
  {
    // « Paie » (feedback 13/11/2026): pay on the spot and monthly salaries.
    key: 'pay',
    label: 'pay',
    icon: Banknote,
    routeName: 'pay',
    group: 'equipe',
    ready: true,
    roles: ['owner', 'accountant'],
  },
  {
    key: 'attendance',
    label: 'attendance',
    icon: Clock,
    routeName: 'attendance',
    group: 'equipe',
    ready: true,
    roles: ['owner', 'planner', 'accountant'],
  },
  {
    // « Mes missions » (§7): the field roles' own space, on the phone.
    key: 'missions',
    label: 'missions',
    icon: ClipboardCheck,
    routeName: 'missions',
    group: 'equipe',
    ready: true,
    mobileTab: true,
    roles: ['team_lead', 'staff'],
  },
  // Événementiel
  {
    key: 'weddings',
    label: 'weddings',
    module: 'weddings',
    icon: Heart,
    routeName: 'weddings',
    group: 'evenementiel',
    ready: true,
    phase: 2,
  },
  {
    key: 'vendors',
    label: 'vendors',
    icon: Briefcase,
    routeName: 'vendors',
    group: 'evenementiel',
    ready: true,
    phase: 2,
  },
  {
    key: 'invitations',
    label: 'invitations',
    module: 'weddings',
    icon: Mail,
    routeName: 'invitations',
    group: 'evenementiel',
    ready: false, // tickets are reached from each wedding until the list screen exists
    phase: 3,
  },
  // Espace
  {
    key: 'settings',
    label: 'settings',
    icon: Settings,
    routeName: 'settings',
    group: 'espace',
    ready: true,
    roles: ['owner'],
  },
]

/** What the field roles open (reservations-stock.md §12); missions and check-in come with S7. */
const FIELD_ROLE_ITEMS: Partial<Record<Role, Set<string>>> = {
  storekeeper: new Set(['dashboard', 'reservations', 'calendar', 'stock', 'movements']),
  team_lead: new Set(['dashboard', 'missions']),
  staff: new Set(['dashboard', 'missions']),
}

export const NAV_GROUPS: readonly NavGroup[] = [
  'pilotage',
  'activite',
  'materiel',
  'finances',
  'equipe',
  'evenementiel',
  'espace',
]

export function menuItems(role: Role | null, weddings = true): NavItem[] {
  return visibleNavItems(role, weddings).filter((item) => !item.hiddenFromMenu)
}

/** Staff and team leads open « Mon espace » (their own day) instead of the dashboard. */
const PERSONAL_HOME: readonly Role[] = ['staff', 'team_lead']

export function visibleNavItems(role: Role | null, weddings = true): NavItem[] {
  const field = role !== null && FIELD_ROLES.includes(role)
  return NAV_ITEMS.filter(
    (item) =>
      item.ready &&
      (item.module !== 'weddings' || weddings) &&
      (!item.roles || (role !== null && item.roles.includes(role))) &&
      (!field || Boolean(role && FIELD_ROLE_ITEMS[role]?.has(item.key))),
  ).map((item) =>
    item.key === 'dashboard' && role && PERSONAL_HOME.includes(role)
      ? { ...item, label: 'mySpace' }
      : item,
  )
}

const TAB_COUNT = 4

/**
 * Mobile tabs: Accueil, Réservations, Stock, Finances (+ « Plus »). While a module is not built,
 * clients and quotes take its place, so the bar never shows an empty module.
 */
export function mobileTabItems(role: Role | null, weddings = true): NavItem[] {
  const visible = visibleNavItems(role, weddings)
  const [home, ...others] = visible.filter((item) => item.mobileTab)
  const room = Math.max(0, TAB_COUNT - 1 - others.length)
  const fill = visible.filter((item) => item.mobileFallback).slice(0, room)
  return home ? [home, ...fill, ...others] : [...fill, ...others]
}

/** Phase label shown next to a module (« P2 »), or null when the flag is off. */
export function phaseTag(item: NavItem): string | null {
  return item.phase && FEATURES.phaseTags ? `P${item.phase}` : null
}

import { ref } from 'vue'

import type { Role } from '@/api/auth'

import { menuItems } from './navigation'

/**
 * Guided tour (feedback 15/11/2026): offered at the first sign-in (« oui ou non »), it opens each
 * module of the menu in turn and says what it is for. Only the modules the person's role opens
 * are shown, so a storekeeper or a staff member gets their own, shorter tour. It can be replayed
 * at any time from the menu (« Visite guidée ») or Ctrl+K.
 *
 * Each step points at the element marked `data-tour="<target>"` when it is on screen (the menu
 * entry on a computer, the tab at the bottom on a phone); otherwise the card is shown alone.
 */
export interface TourStep {
  /** i18n key under `tour.steps.` for the title and text. */
  key: string
  /** Title from the menu (`nav.<label>`) rather than `tour.steps.<key>.title`. */
  navLabel?: string
  /** Page opened for this step. */
  routeName?: string
  /** `data-tour` value of the element pointed at. */
  target?: string
}

export function tourSteps(role: Role | null, weddings = true): TourStep[] {
  const modules = menuItems(role, weddings).map<TourStep>((item) => ({
    key: item.label,
    navLabel: item.label,
    routeName: item.routeName,
    target: item.key,
  }))
  const first = modules[0]?.routeName ?? 'dashboard'
  return [
    { key: 'welcome', routeName: first },
    ...modules,
    { key: 'search', target: 'search' },
    { key: 'alerts', target: 'alerts' },
    { key: 'profile', target: 'profile' },
    { key: 'end', target: 'tour', routeName: first },
  ]
}

/** Shared by the layout (which shows the tour), the menu and Ctrl+K (which start it). */
const running = ref(false)

export function useTour() {
  return {
    running,
    start: () => (running.value = true),
    stop: () => (running.value = false),
  }
}

/** « Plus tard »: not offered again in this tab (the next sign-in offers it again). */
const LATER_KEY = 'wedivo.tour.later'

export function tourPostponed(): boolean {
  try {
    return sessionStorage.getItem(LATER_KEY) === '1'
  } catch {
    return false
  }
}

export function postponeTour(): void {
  try {
    sessionStorage.setItem(LATER_KEY, '1')
  } catch {
    // Storage blocked: the offer simply comes back on the next page load.
  }
}

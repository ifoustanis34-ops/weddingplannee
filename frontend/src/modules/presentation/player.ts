import { ref } from 'vue'

import type { Role } from '@/api/auth'

import { type DemoScenario, SCENARIOS } from './scenarios'

/**
 * The presentation player's state, shared by the selection page (which starts it), the layout
 * (which shows it) and the guided tour (which keeps quiet meanwhile).
 */
export const presenting = ref(false)
export const scenario = ref<DemoScenario | null>(null)
export const stepIndex = ref(0)
export const paused = ref(false)
export const speed = ref(1)
/** Role of the presenter before the first switch: given back when the show ends. */
export const startRole = ref<Role | null>(null)

export function startPresentation(id: string, role: Role | null): void {
  const found = SCENARIOS.find((s) => s.id === id)
  if (!found) return
  scenario.value = found
  stepIndex.value = 0
  paused.value = false
  startRole.value = startRole.value ?? role
  presenting.value = true
}

export function stopPresentation(): void {
  presenting.value = false
  scenario.value = null
}

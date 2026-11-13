/**
 * Feature flags read at build time (Vite env). Off unless explicitly enabled.
 *
 * - `VITE_PHASE_TAGS=true`: show « P2 » / « P3 » next to Phase 2 and 3 modules in the menu
 *   (complement §2); turn it off when the module reaches production.
 */
export const FEATURES = {
  phaseTags: import.meta.env.VITE_PHASE_TAGS === 'true',
}

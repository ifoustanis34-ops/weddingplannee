import { useQuery } from '@tanstack/vue-query'
import { computed, watch } from 'vue'

import { organizationApi } from '@/api/organization'
import { DEFAULT_TIMEZONE, setAgencyTimezone } from '@/composables/useDate'
import { useSessionStore } from '@/stores/session'

/** The agency's time zone (Paramètres › Entreprise), Abidjan until it is loaded. */
export function useOrgTimezone() {
  const session = useSessionStore()
  const organization = useQuery({
    queryKey: computed(() => ['organization', session.currentOrganization?.slug]),
    queryFn: organizationApi.get,
    enabled: computed(() => Boolean(session.currentOrganization)),
  })
  const zone = computed(() => organization.data.value?.timezone ?? DEFAULT_TIMEZONE)
  // The whole app formats dates in the agency's zone.
  watch(zone, setAgencyTimezone, { immediate: true })
  return zone
}

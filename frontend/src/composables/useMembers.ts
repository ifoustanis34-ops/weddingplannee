import { useQuery } from '@tanstack/vue-query'

import { organizationApi } from '@/api/organization'

/** Team members of the current space (assignees, filters). Cached 5 minutes. */
export function useMembers() {
  return useQuery({ queryKey: ['members'], queryFn: organizationApi.members, staleTime: 300_000 })
}

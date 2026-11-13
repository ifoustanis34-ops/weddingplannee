import { api } from './client'

export interface SearchResults {
  clients: { id: string; name: string; company: string }[]
  quotes: { id: string; number: string; clientName: string; status: string; total: number }[]
}

/** Ctrl+K search, server side and limited to the current organization (CLAUDE.md §7.10). */
export const searchApi = {
  search: (q: string, signal?: AbortSignal) =>
    api.get<SearchResults>('/search', { params: { q }, signal }).then((r) => r.data),
}

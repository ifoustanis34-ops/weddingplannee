import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { type MaybeRefOrGetter, computed, toValue } from 'vue'

import { api } from '@/api/client'
import { clientKeys } from '@/modules/crm/api'

import type {
  DocumentDesigns,
  GeneratedDocument,
  PublicQuote,
  Quote,
  QuoteInput,
  QuoteListItem,
  QuoteStatus,
  QuoteStats,
  QuoteSummary,
} from './types'

interface Page<T> {
  results: T[]
  next: string | null
}

export interface QuoteFilters {
  status?: QuoteStatus | 'templates' | ''
  search?: string
}

export const quoteKeys = {
  all: ['quotes'] as const,
  list: (filters: QuoteFilters) => [...quoteKeys.all, 'list', filters] as const,
  summary: () => [...quoteKeys.all, 'summary'] as const,
  stats: () => [...quoteKeys.all, 'stats'] as const,
  detail: (id: string) => [...quoteKeys.all, 'detail', id] as const,
}

export const quotesApi = {
  list: (filters: QuoteFilters) =>
    api
      .get<Page<QuoteListItem>>('/quotes', {
        params: {
          pageSize: 100,
          status: filters.status && filters.status !== 'templates' ? filters.status : undefined,
          isTemplate: filters.status === 'templates' ? true : undefined,
          search: filters.search || undefined,
        },
      })
      .then((r) => r.data),
  summary: () => api.get<QuoteSummary>('/quotes/summary').then((r) => r.data),
  stats: () => api.get<QuoteStats>('/quotes/stats').then((r) => r.data),
  get: (id: string) => api.get<Quote>(`/quotes/${id}`).then((r) => r.data),
  create: (input: QuoteInput) => api.post<Quote>('/quotes', input).then((r) => r.data),
  update: (id: string, input: QuoteInput) =>
    api.patch<Quote>(`/quotes/${id}`, input).then((r) => r.data),
  remove: (id: string) => api.delete(`/quotes/${id}`).then(() => undefined),
  send: (id: string) => api.post<Quote>(`/quotes/${id}/send`).then((r) => r.data),
  accept: (id: string) => api.post<Quote>(`/quotes/${id}/accept`).then((r) => r.data),
  refuse: (id: string, reason: string) =>
    api.post<Quote>(`/quotes/${id}/refuse`, { reason }).then((r) => r.data),
  duplicate: (id: string, options: { asTemplate?: boolean; client?: string } = {}) =>
    api.post<Quote>(`/quotes/${id}/duplicate`, options).then((r) => r.data),
  convert: (id: string) => api.post<Quote>(`/quotes/${id}/convert`).then((r) => r.data),
  pdfUrl: (id: string) => `/api/v1/quotes/${id}/pdf`,
  /** « Générer le PDF »: freezes a version (a new one only when something changed). */
  generate: (id: string) =>
    api.post<GeneratedDocument>(`/quotes/${id}/generate`).then((r) => r.data),
}

export const documentsApi = {
  designs: () => api.get<DocumentDesigns>('/documents/designs').then((r) => r.data),
  /** Server rendering of the draft (all pages stacked, PNG), the same as the future PDF. */
  preview: (
    body: { kind: 'quote'; quote: string | null; draft: QuoteInput },
    signal?: AbortSignal,
  ) =>
    api
      .post<Blob>('/documents/preview', body, { responseType: 'blob', signal })
      .then((r) => ({ image: r.data, pages: Number(r.headers['x-page-count'] ?? 1) })),
}

export const publicQuoteApi = {
  get: (token: string) => api.get<PublicQuote>(`/public/quotes/${token}`).then((r) => r.data),
  accept: (token: string) =>
    api.post<PublicQuote>(`/public/quotes/${token}/accept`).then((r) => r.data),
  refuse: (token: string, reason: string) =>
    api.post<PublicQuote>(`/public/quotes/${token}/refuse`, { reason }).then((r) => r.data),
  pdfUrl: (token: string) => `/api/v1/public/quotes/${token}/pdf`,
  previewUrl: (token: string) => `/api/v1/public/quotes/${token}/preview`,
}

export function useQuotes(filters: MaybeRefOrGetter<QuoteFilters>) {
  return useQuery({
    queryKey: computed(() => quoteKeys.list({ ...toValue(filters) })),
    queryFn: () => quotesApi.list(toValue(filters)),
    placeholderData: (previous) => previous,
  })
}

export function useQuoteSummary() {
  return useQuery({ queryKey: quoteKeys.summary(), queryFn: quotesApi.summary })
}

export function useQuoteStats() {
  return useQuery({ queryKey: quoteKeys.stats(), queryFn: quotesApi.stats })
}

export function useQuote(id: MaybeRefOrGetter<string | null>) {
  return useQuery({
    queryKey: computed(() => quoteKeys.detail(toValue(id) ?? '')),
    queryFn: () => quotesApi.get(toValue(id)!),
    enabled: computed(() => Boolean(toValue(id))),
  })
}

/** Any quote action: store the fresh quote and refresh lists, counts and the client's totals. */
export function useQuoteAction<TArgs>(fn: (args: TArgs) => Promise<Quote>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (quote) => {
      queryClient.setQueryData(quoteKeys.detail(quote.id), quote)
      void queryClient.invalidateQueries({ queryKey: [...quoteKeys.all, 'list'] })
      void queryClient.invalidateQueries({ queryKey: quoteKeys.summary() })
      void queryClient.invalidateQueries({ queryKey: clientKeys.all })
    },
  })
}

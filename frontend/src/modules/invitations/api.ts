import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, type MaybeRefOrGetter, toValue } from 'vue'

import { api } from '@/api/client'

import type {
  Guest,
  GuestInput,
  PublicTicket,
  TicketBatch,
  TicketDesign,
  TicketDesignInput,
  TicketSummary,
} from './types'

export const ticketKeys = {
  all: ['tickets'] as const,
  design: (wedding: string) => [...ticketKeys.all, 'design', wedding] as const,
  guests: (wedding: string) => [...ticketKeys.all, 'guests', wedding] as const,
}

export const ticketsApi = {
  design: (wedding: string) =>
    api.get<TicketDesign>(`/weddings/${wedding}/ticket-design`).then((r) => r.data),
  updateDesign: (wedding: string, input: TicketDesignInput) =>
    api.patch<TicketDesign>(`/weddings/${wedding}/ticket-design`, input).then((r) => r.data),
  /** Server rendering of the design with an example guest (§6 « aperçu PNG serveur »). */
  preview: (wedding: string, draft: TicketDesignInput, signal?: AbortSignal) =>
    api
      .post<Blob>('/tickets/preview', { wedding, draft }, { responseType: 'blob', signal })
      .then((r) => r.data),
  guests: (wedding: string) => api.get<Guest[]>(`/weddings/${wedding}/guests`).then((r) => r.data),
  addGuest: (wedding: string, input: GuestInput) =>
    api.post<Guest>(`/weddings/${wedding}/guests`, input).then((r) => r.data),
  updateGuest: (id: string, input: Partial<GuestInput>) =>
    api.patch<Guest>(`/guests/${id}`, input).then((r) => r.data),
  removeGuest: (id: string) => api.delete(`/guests/${id}`).then(() => undefined),
  importGuests: (wedding: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api
      .post<{ created: number; skipped: { row: number; name: string; reason: string }[] }>(
        `/weddings/${wedding}/guests/import`,
        form,
      )
      .then((r) => r.data)
  },
  generate: (wedding: string, input: { guests?: string[]; all?: boolean }) =>
    api.post<TicketBatch>(`/weddings/${wedding}/tickets/generate`, input).then((r) => r.data),
  batch: (id: string) => api.get<TicketBatch>(`/ticket-batches/${id}`).then((r) => r.data),
  export: (wedding: string, type: 'pdf' | 'zip') =>
    api
      .get<Blob>(`/weddings/${wedding}/tickets/export`, { params: { type }, responseType: 'blob' })
      .then((r) => r.data),
  pdf: (ticket: string) =>
    api.get<Blob>(`/tickets/${ticket}/pdf`, { responseType: 'blob' }).then((r) => r.data),
  cancel: (ticket: string) =>
    api.post<TicketSummary>(`/tickets/${ticket}/cancel`).then((r) => r.data),
  reissue: (ticket: string) =>
    api.post<TicketSummary>(`/tickets/${ticket}/reissue`).then((r) => r.data),
}

export const publicTicketApi = {
  get: (token: string) => api.get<PublicTicket>(`/public/tickets/${token}`).then((r) => r.data),
  rsvp: (token: string, accepted: boolean) =>
    api
      .post<{ rsvpStatus: Guest['rsvpStatus'] }>(`/public/tickets/${token}/rsvp`, { accepted })
      .then((r) => r.data),
  imageUrl: (token: string) => `/api/v1/public/tickets/${token}/image`,
  pdfUrl: (token: string) => `/api/v1/public/tickets/${token}/pdf`,
  icsUrl: (token: string) => `/api/v1/public/tickets/${token}/ics`,
}

export function useTicketDesign(wedding: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => ticketKeys.design(toValue(wedding))),
    queryFn: () => ticketsApi.design(toValue(wedding)),
  })
}

export function useGuests(wedding: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => ticketKeys.guests(toValue(wedding))),
    queryFn: () => ticketsApi.guests(toValue(wedding)),
  })
}

/** Any change refreshes the guest list (statuses, tickets). */
export function useTicketAction<TArgs, TResult>(fn: (args: TArgs) => Promise<TResult>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ticketKeys.all }),
  })
}

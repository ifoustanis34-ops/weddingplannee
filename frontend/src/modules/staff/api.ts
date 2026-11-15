import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, type MaybeRefOrGetter, toValue } from 'vue'

import type { Role } from '@/api/auth'
import { api } from '@/api/client'
import { prepareImage } from '@/app/images'

/** Staff (reservations-stock.md §7): people, assignments, check-in, pay, « Mes missions ». */

export type StaffKind = 'employee' | 'day_worker' | 'freelance'
export type PayMode = 'monthly' | 'daily' | 'mission' | 'hourly'
export type Step = 'all' | 'delivery' | 'setup' | 'event' | 'teardown' | 'pickup' | 'return'
export type AttendanceStatus = 'present' | 'late' | 'absent'

export interface StaffMember {
  id: string
  fullName: string
  photoUrl: string | null
  phone: string
  position: string
  department: string
  employeeNumber: string
  kind: StaffKind
  kindLabel: string
  skills: string[]
  payMode: PayMode
  payModeLabel: string
  payRate: number | null
  mobileMoney: string
  emergencyContact: string
  notes: string
  hasAccount: boolean
  isActive: boolean
  today: {
    status: 'free' | 'busy' | 'absent'
    missions: { reservation: string; number: string; step: Step; start: string }[]
  }
}
export type StaffInput = Partial<
  Pick<
    StaffMember,
    | 'fullName'
    | 'phone'
    | 'position'
    | 'department'
    | 'kind'
    | 'skills'
    | 'payMode'
    | 'payRate'
    | 'mobileMoney'
    | 'emergencyContact'
    | 'notes'
    | 'isActive'
  >
>

export interface Assignment {
  id: string
  staff: string
  staffName: string
  staffPosition: string
  reservation: string
  reservationNumber: string
  reservationTitle: string
  step: Step
  stepLabel: string
  role: string
  start: string
  end: string
  attendance: {
    status: AttendanceStatus
    checkIn: string | null
    checkOut: string | null
    hours: number
    note: string
  } | null
  conflicts: string[]
}

export interface StaffTask {
  id: string
  staff: string
  staffName: string
  staffPosition: string
  reservation: string
  reservationNumber: string
  reservationTitle: string
  eventStart: string
  title: string
  status: 'todo' | 'done' | 'validated'
  statusLabel: string
  comment: string
  photoUrl: string | null
  venue: string
  staffHasAccount: boolean
  doneAt: string | null
  doneByName: string | null
  validatedAt: string | null
  validatedByName: string | null
  rejectionReason: string
}

export interface Mission extends Assignment {
  /** upcoming · in_progress (started or checked in) · done (over or checked out). */
  state: 'upcoming' | 'in_progress' | 'done'
  client: string
  clientPhone: string
  venue: string
  address: string
  mapsUrl: string | null
  equipment: { label: string; quantity: number }[]
  tasks: StaffTask[]
  team: { assignment: string; name: string; role: string; attendance: AttendanceStatus | null }[]
}

/** « Mon espace » (feedback 13/11/2026): the person's own figures, never an amount. */
export interface MyOverview {
  staff: {
    id: string
    name: string
    position: string
    department: string
    employeeNumber: string
    photoUrl: string | null
  } | null
  missionsWeek: number
  missionsMonth: number
  hoursMonth: number
  punctuality: number | null
  attendance: { present: number; late: number; absent: number }
  tasks: { todo: number; done: number; validated: number }
  hoursByWeek: { week: string; hours: number }[]
  nextMission: string | null
  team: {
    assignment: string
    name: string
    role: string
    reservation: string
    start: string
    attendance: AttendanceStatus | null
    checkedIn: boolean
  }[]
}

export interface PayLine {
  id: string
  staff: string
  staffName: string
  position: string
  payMode: PayMode
  payRate: number
  days: number
  missions: number
  hours: number
  base: number
  bonuses: number
  advances: number
  alreadyPaid: number
  total: number
  paidAt: string | null
  method: string
}
export interface PayPeriod {
  id: string
  start: string
  end: string
  status: 'draft' | 'validated' | 'paid'
  statusLabel: string
  validatedAt: string | null
  lines: PayLine[]
  total: number
}

export interface DaySheet {
  date: string
  reservations: { id: string; number: string; title: string }[]
  rows: {
    staff: string
    name: string
    position: string
    payMode: PayMode
    payRate: number
    mobileMoney: string
    status: 'present' | 'late' | 'absent' | 'planned'
    hours: number
    reservations: string[]
    salaried: boolean
    suggested: number
    alreadyPaid: number
  }[]
}
export interface StaffPayment {
  id: string
  staff: string
  staffName: string
  reservation: string | null
  reservationNumber: string | null
  date: string
  amount: number
  method: string
  note: string
}
export const BADGE_DESIGNS = ['carte', 'classique', 'portrait', 'elegant', 'minimal'] as const
export type BadgeDesign = (typeof BADGE_DESIGNS)[number]

export interface StaffStats {
  headcount: number
  missionsWeek: number
  hoursMonth: number
  payrollMonth: number | null
}
export interface Planning {
  from: string
  days: string[]
  rows: {
    staff: string
    name: string
    position: string
    absent?: string[]
    days: Record<
      string,
      {
        assignment: string
        reservation: string
        number: string
        title: string
        step: Step
        time: string
        attendance: AttendanceStatus | null
      }[]
    >
  }[]
}

export const staffApi = {
  list: (filters: { search?: string; active?: boolean } = {}) =>
    api
      .get<StaffMember[]>('/staff', {
        params: {
          search: filters.search || undefined,
          active: filters.active === false ? 'false' : undefined,
        },
      })
      .then((r) => r.data),
  get: (id: string) => api.get<StaffMember>(`/staff/${id}`).then((r) => r.data),
  create: (input: StaffInput) => api.post<StaffMember>('/staff', input).then((r) => r.data),
  update: (id: string, input: StaffInput) =>
    api.patch<StaffMember>(`/staff/${id}`, input).then((r) => r.data),
  stats: () => api.get<StaffStats>('/staff/stats').then((r) => r.data),
  planning: (from?: string) =>
    api.get<Planning>('/staff/planning', { params: { from } }).then((r) => r.data),
  assignments: (filters: { reservation?: string; staff?: string }) =>
    api.get<Assignment[]>('/assignments', { params: filters }).then((r) => r.data),
  assign: (input: { reservation: string; staff: string; step: Step; role: string }) =>
    api.post<Assignment>('/assignments', input).then((r) => r.data),
  unassign: (id: string) => api.delete(`/assignments/${id}`).then(() => undefined),
  checkIn: (id: string) => api.post<Assignment>(`/assignments/${id}/check-in`).then((r) => r.data),
  checkOut: (id: string) =>
    api.post<Assignment>(`/assignments/${id}/check-out`).then((r) => r.data),
  absent: (id: string, note = '') =>
    api.post<Assignment>(`/assignments/${id}/absent`, { note }).then((r) => r.data),
  tasks: (filters: { reservation?: string; staff?: string; status?: string }) =>
    api.get<StaffTask[]>('/staff-tasks', { params: filters }).then((r) => r.data),
  addTask: (input: { staff: string; reservation: string; title: string }) =>
    api.post<StaffTask>('/staff-tasks', input).then((r) => r.data),
  updateTask: (id: string, input: { status?: string; comment?: string }) =>
    api.patch<StaffTask>(`/staff-tasks/${id}`, input).then((r) => r.data),
  validateTask: (id: string) =>
    api.post<StaffTask>(`/staff-tasks/${id}/validate`).then((r) => r.data),
  rejectTask: (id: string, reason: string) =>
    api.post<StaffTask>(`/staff-tasks/${id}/reject`, { reason }).then((r) => r.data),
  taskPhoto: async (id: string, file: File) => {
    const form = new FormData()
    form.append('file', await prepareImage(file))
    return api.post<StaffTask>(`/staff-tasks/${id}/photo`, form).then((r) => r.data)
  },
  /** « Créer son accès »: a Wedivo account linked to the record (owner only). */
  /** Delete (owner, planner): for good without history, else out of every list. */
  remove: (id: string) =>
    api
      .delete<{
        permanent: boolean
        removedAssignments: number
        accessClosed: boolean
      }>(`/staff/${id}`)
      .then((r) => r.data),
  createAccess: (id: string, input: { email: string; role: Role; password: string }) =>
    api
      .post<{ email: string; role: Role; createdAccount: boolean }>(`/staff/${id}/account`, input)
      .then((r) => r.data),
  /** The person's photo: square, ready for the record and the badge (feedback 15/11/2026). */
  photo: async (id: string, file: File) => {
    const form = new FormData()
    form.append('file', await prepareImage(file, { square: true, maxSide: 800 }))
    return api.post<{ photoUrl: string }>(`/staff/${id}/photo`, form).then((r) => r.data)
  },
  daySheet: (day: string, reservation?: string) =>
    api
      .get<DaySheet>('/pay/day', { params: { date: day, reservation: reservation || undefined } })
      .then((r) => r.data),
  payNow: (input: {
    date: string
    reservation?: string | null
    method: string
    lines: { staff: string; amount: number; note?: string }[]
  }) => api.post<StaffPayment[]>('/staff-payments', input).then((r) => r.data),
  payments: () => api.get<StaffPayment[]>('/staff-payments').then((r) => r.data),
  /** One card as an image (object URL), to choose the design. */
  badgePreview: async (design: BadgeDesign, staff?: string) => {
    const response = await api.get<Blob>('/staff/badges/preview', {
      params: { design, staff },
      responseType: 'blob',
    })
    return URL.createObjectURL(response.data)
  },
  /** Badges PDF in a design: one person or the whole active team. */
  badges: async (ids: string[] = [], design: BadgeDesign = 'carte') => {
    const response = await api.get<Blob>('/staff/badges', {
      params: { ids: ids.length ? ids.join(',') : undefined, design },
      responseType: 'blob',
    })
    const href = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = href
    link.download = 'badges-personnel.pdf'
    link.click()
    setTimeout(() => URL.revokeObjectURL(href), 60_000)
  },
  missions: () =>
    api
      .get<{ staff: { id: string; name: string } | null; missions: Mission[] }>('/me/missions')
      .then((r) => r.data),
  overview: () => api.get<MyOverview>('/me/overview').then((r) => r.data),
  periods: () => api.get<PayPeriod[]>('/pay-periods').then((r) => r.data),
  createPeriod: (start: string, end: string) =>
    api.post<PayPeriod>('/pay-periods', { start, end }).then((r) => r.data),
  refreshPeriod: (id: string) =>
    api.post<PayPeriod>(`/pay-periods/${id}/refresh`).then((r) => r.data),
  validatePeriod: (id: string) =>
    api.post<PayPeriod>(`/pay-periods/${id}/validate`).then((r) => r.data),
  updateLine: (id: string, input: { bonuses: number; advances: number }) =>
    api.patch<PayLine>(`/pay-lines/${id}`, input).then((r) => r.data),
  payLine: (id: string, method: string) =>
    api.post<PayLine>(`/pay-lines/${id}/pay`, { method }).then((r) => r.data),
  /** « Feuille de paie du jour » (15/11/2026): everyone paid that day, with signatures. */
  daySheetPdf: async (day: string, reservation?: string) => {
    const response = await api.get<Blob>('/pay/day/sheet', {
      params: { date: day, reservation: reservation || undefined },
      responseType: 'blob',
    })
    const href = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = href
    link.download = `feuille-de-paie-${day}.pdf`
    link.click()
    setTimeout(() => URL.revokeObjectURL(href), 60_000)
  },
  statement: async (id: string, name: string) => {
    const response = await api.get<Blob>(`/pay-lines/${id}/statement`, { responseType: 'blob' })
    const href = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = href
    link.download = `releve-${name}.pdf`
    link.click()
    setTimeout(() => URL.revokeObjectURL(href), 60_000)
  },
}

export const staffKeys = { all: ['staff'] as const }

export function useStaff(filters: MaybeRefOrGetter<{ search?: string; active?: boolean }> = {}) {
  return useQuery({
    queryKey: computed(() => [...staffKeys.all, 'list', { ...toValue(filters) }]),
    queryFn: () => staffApi.list(toValue(filters)),
    placeholderData: keepPreviousData,
  })
}
export const useStaffStats = () =>
  useQuery({ queryKey: [...staffKeys.all, 'stats'], queryFn: staffApi.stats })
export function usePlanning(from: MaybeRefOrGetter<string | undefined>) {
  return useQuery({
    queryKey: computed(() => [...staffKeys.all, 'planning', toValue(from)]),
    queryFn: () => staffApi.planning(toValue(from)),
    placeholderData: keepPreviousData,
  })
}
export function useAssignments(
  filters: MaybeRefOrGetter<{ reservation?: string; staff?: string }>,
) {
  return useQuery({
    queryKey: computed(() => [...staffKeys.all, 'assignments', { ...toValue(filters) }]),
    queryFn: () => staffApi.assignments(toValue(filters)),
  })
}
export function useStaffTasks(
  filters: MaybeRefOrGetter<{ reservation?: string; staff?: string; status?: string }>,
) {
  return useQuery({
    queryKey: computed(() => [...staffKeys.all, 'tasks', { ...toValue(filters) }]),
    queryFn: () => staffApi.tasks(toValue(filters)),
  })
}
export const useMissions = () =>
  useQuery({ queryKey: [...staffKeys.all, 'missions'], queryFn: staffApi.missions })
export const useMyOverview = () =>
  useQuery({ queryKey: [...staffKeys.all, 'overview'], queryFn: staffApi.overview })
export const usePayPeriods = (enabled: MaybeRefOrGetter<boolean> = true) =>
  useQuery({
    queryKey: [...staffKeys.all, 'pay'],
    queryFn: staffApi.periods,
    enabled: computed(() => toValue(enabled)),
  })

/** Any staff change: lists, planning, calendar, dashboard (team of the day) follow. */
export function useStaffMutation<TArgs, TResult>(fn: (args: TArgs) => Promise<TResult>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      for (const key of [staffKeys.all, ['calendar'], ['dashboard'], ['billing']])
        void queryClient.invalidateQueries({ queryKey: key })
    },
  })
}

export const STEPS: Step[] = ['all', 'delivery', 'setup', 'event', 'teardown', 'pickup', 'return']
export const ATTENDANCE_TONES = { present: 'green', late: 'gold', absent: 'red' } as const

export type WeddingStatus = 'planned' | 'done' | 'cancelled'

export interface Wedding {
  id: string
  title: string
  date: string | null
  venue: string
  guestCount: number | null
  budget: number | null
  status: WeddingStatus
  statusLabel: string
  contract: string | null
  contractNumber: string | null
  client: string | null
  tasksTotal: number
  tasksDone: number
  progress: number
  vendorsCount: number
  daysLeft: number | null
}

export interface WeddingInput {
  title: string
  date: string | null
  venue: string
  guestCount: number | null
  budget?: number | null
  status?: WeddingStatus
  standardTasks?: boolean
}

export interface Task {
  id: string
  wedding: string
  title: string
  assignee: string | null
  assigneeName: string | null
  dueDate: string | null
  status: 'todo' | 'done'
  statusLabel: string
  notes: string
  doneAt: string | null
}

export interface TaskInput {
  title: string
  assignee?: string | null
  dueDate?: string | null
  notes?: string
}

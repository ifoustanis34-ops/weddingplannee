import { ref } from 'vue'

import { daysBetween } from '../month'
import { acceptsDrop, readDrop } from '../kinds'

export interface MoveRequest {
  reservation: string
  days: number
  to: string
}

/** Day cells as drop targets for a dragged reservation (§4.3). */
export function useDropDay(onMove: (request: MoveRequest) => void) {
  const over = ref<string | null>(null)
  return {
    over,
    dragover(event: DragEvent, day: string): void {
      if (!acceptsDrop(event)) return
      event.preventDefault()
      if (event.dataTransfer) event.dataTransfer.dropEffect = 'move'
      over.value = day
    },
    dragleave(day: string): void {
      if (over.value === day) over.value = null
    },
    drop(event: DragEvent, day: string): void {
      over.value = null
      const source = readDrop(event)
      if (!source) return
      event.preventDefault()
      const days = daysBetween(source.date, day)
      if (days !== 0) onMove({ reservation: source.reservation, days, to: day })
    },
  }
}

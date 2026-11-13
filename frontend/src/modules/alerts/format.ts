import { CircleAlert, ClipboardList, TriangleAlert } from '@lucide/vue'
import type { RouteLocationRaw } from 'vue-router'

import { formatMoney } from '@/composables/useMoney'
import { i18n } from '@/i18n'

import type { Alert } from './api'

/** Status colors always come with an icon and a label, never color alone. */
export const SEVERITY = {
  critical: { icon: CircleAlert, classes: 'bg-red-soft text-red', text: 'text-red' },
  serious: { icon: TriangleAlert, classes: 'bg-coral-soft text-coral', text: 'text-coral' },
  warning: { icon: ClipboardList, classes: 'bg-gold-soft text-gold', text: 'text-gold' },
} as const

type AlertLike = Pick<
  Alert,
  'kind' | 'amount' | 'days' | 'count' | 'available' | 'threshold' | 'subtitle'
>

/** « 360 000 FCFA en retard de 12 j », « 3 tâches en retard »… */
export function alertDetail(alert: AlertLike): string {
  const t = i18n.global.t
  const count = alert.count ?? 0
  const days = alert.days ?? 0
  switch (alert.kind) {
    case 'overdue_payment':
      return t('dashboard.alerts.overduePayment', { amount: formatMoney(alert.amount ?? 0), days })
    case 'overdue_invoice':
      return t('alerts.kinds.overdueInvoice', {
        amount: formatMoney(alert.amount ?? 0),
        days,
        number: alert.subtitle ?? '',
      })
    case 'late_tasks':
      return t('dashboard.alerts.lateTasks', { count }, count)
    case 'wedding_unready':
      return t('dashboard.alerts.weddingUnready', { count }, count)
    case 'below_threshold':
      return t('alerts.kinds.belowThreshold', { count, threshold: alert.threshold ?? 0 })
    case 'maintenance_late':
      return t('alerts.kinds.maintenanceLate', { days }, days)
    case 'damaged_unit':
      return t('alerts.kinds.damagedUnit', { serial: alert.subtitle ?? '' })
    case 'stock_shortage':
      return t('alerts.kinds.stockShortage', {
        needed: count,
        available: alert.available ?? 0,
        reservation: alert.subtitle ?? '',
      })
    case 'late_return':
      return t('alerts.kinds.lateReturn', { days, reservation: alert.subtitle ?? '' }, days)
  }
}

/** Where the alert's action leads: the contract (record the payment) or the wedding. */
export function alertTarget(
  alert: Pick<Alert, 'contract' | 'wedding' | 'reservation' | 'item'>,
): RouteLocationRaw | null {
  if (alert.reservation) return { name: 'reservations', query: { reservation: alert.reservation } }
  if (alert.contract) return { name: 'finance', query: { contract: alert.contract } }
  if (alert.wedding) return { name: 'weddings', query: { mariage: alert.wedding } }
  if (alert.item) return { name: 'stock', query: { article: alert.item } }
  return null
}

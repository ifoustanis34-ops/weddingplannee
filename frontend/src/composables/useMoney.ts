/** FCFA amounts are stored as integers. Thousands use a narrow no-break space (U+202F). */

const NARROW_NBSP = ' '

export type Currency = 'XOF' | 'XAF' | 'EUR'

const SYMBOLS: Record<Currency, string> = { XOF: 'FCFA', XAF: 'FCFA', EUR: '€' }

function group(value: number): string {
  const digits = Math.trunc(Math.abs(value)).toString()
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, NARROW_NBSP)
}

/** `1500000` → `1 500 000 FCFA` */
export function formatMoney(amount: number, currency: Currency = 'XOF'): string {
  const sign = amount < 0 ? '−' : ''
  return `${sign}${group(amount)} ${SYMBOLS[currency]}`
}

/** Amount without the currency, for tables that state it once (« 1 500 000 »). */
export function formatAmount(amount: number): string {
  return `${amount < 0 ? '−' : ''}${group(amount)}`
}

/** Short form for indicators: `6 300 000` → `6,3 M`, `9 350 000` → `9,35 M` (2 decimals max). */
export function formatMoneyShort(amount: number): string {
  const abs = Math.abs(amount)
  const sign = amount < 0 ? '−' : ''
  const short = (value: number, unit: string) => {
    const rounded = Math.round(value * 100) / 100
    const text = String(rounded).replace('.', ',')
    return `${sign}${text} ${unit}`
  }
  if (abs >= 1_000_000_000) return short(abs / 1_000_000_000, 'Md')
  if (abs >= 1_000_000) return short(abs / 1_000_000, 'M')
  return `${sign}${group(abs)}`
}

export function useMoney(currency: () => Currency = () => 'XOF') {
  return {
    format: (amount: number) => formatMoney(amount, currency()),
    formatShort: formatMoneyShort,
  }
}

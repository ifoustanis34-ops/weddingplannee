/**
 * The unread count outside the page (feedback 17/11/2026, like WhatsApp): on the installed app's
 * icon (Badging API: Android, Windows/macOS Chrome and Edge, iPhone 16.4+ once installed) and as
 * « (3) Wedivo » in the browser tab. Silently does nothing where unsupported.
 */
const BASE_TITLE = 'Wedivo'

type BadgeNavigator = Navigator & {
  setAppBadge?: (count?: number) => Promise<void>
  clearAppBadge?: () => Promise<void>
}

export function tabTitle(count: number): string {
  return count > 0 ? `(${count > 99 ? '99+' : count}) ${BASE_TITLE}` : BASE_TITLE
}

export function showUnread(count: number): void {
  if (typeof document !== 'undefined') document.title = tabTitle(count)
  if (typeof navigator === 'undefined') return
  const nav = navigator as BadgeNavigator
  try {
    if (count > 0) void nav.setAppBadge?.(count)?.catch(() => undefined)
    else void nav.clearAppBadge?.()?.catch(() => undefined)
  } catch {
    // Not supported here: the bell still shows the count.
  }
}

import { expect, test as base } from '@playwright/test'

/**
 * Journeys must not depend on the network: the interface fonts come from Google Fonts, and
 * an unreachable DNS would hold page loads until timeout. The local fallback fonts are used.
 */
export const test = base.extend<{ offlineFonts: void }>({
  offlineFonts: [
    async ({ page }, use) => {
      await page.route(/^https:\/\/fonts\.(googleapis|gstatic)\.com\//, (route) => route.abort())
      await use()
    },
    { auto: true },
  ],
})

export { expect }

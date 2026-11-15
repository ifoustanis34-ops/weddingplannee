import { expect, test as base } from '@playwright/test'

/**
 * Journeys must not depend on the network: the interface fonts come from Google Fonts, and
 * an unreachable DNS would hold page loads until timeout. The local fallback fonts are used.
 */
export const test = base.extend<{ offlineFonts: void; tourOffer: boolean; quietTour: void }>({
  /** The guided tour offer stays out of the way of the other journeys (« Plus tard »). */
  tourOffer: [false, { option: true }],
  quietTour: [
    async ({ page, tourOffer }, use) => {
      if (!tourOffer) {
        await page.addInitScript(() => sessionStorage.setItem('wedivo.tour.later', '1'))
      }
      await use()
    },
    { auto: true },
  ],
  offlineFonts: [
    async ({ page }, use) => {
      await page.route(/^https:\/\/fonts\.(googleapis|gstatic)\.com\//, (route) => route.abort())
      await use()
    },
    { auto: true },
  ],
})

export { expect }

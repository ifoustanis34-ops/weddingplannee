import { expect, test } from './fixtures'

const E2E = { email: 'e2e@wedivo.test', password: 'Mariage-E2E-2026' }

test.use({ tourOffer: true })

/**
 * Guided tour (feedback 15/11/2026): offered at sign-in (oui / plus tard / non), it opens each
 * module in turn; « Visite guidée » in the menu replays it.
 */
test('guided tour: offered at sign-in, then module after module', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === 'mobile', 'Covered on desktop')
  // A person who has never seen it, whatever earlier runs did to the e2e account.
  await page.route('**/api/v1/auth/me', async (route) => {
    const response = await route.fetch()
    const body = await response.json()
    if (body.user) body.user.tour_done = false
    await route.fulfill({ response, json: body })
  })
  let finished = 0
  await page.route('**/api/v1/auth/me/tour', async (route) => {
    finished += 1
    await route.fulfill({ status: 204 })
  })

  await page.goto('/connexion')
  await page.getByLabel('Email').fill(E2E.email)
  await page.getByLabel(/^Mot de passe/).fill(E2E.password)
  await page.getByRole('button', { name: 'Se connecter' }).click()

  const offer = page.getByRole('dialog', { name: /Bienvenue sur Wedivo/ })
  await expect(offer).toBeVisible()
  await offer.getByRole('button', { name: 'Oui, commencer la visite' }).click()

  const card = page.getByRole('dialog', { name: 'Visite guidée de Wedivo' })
  await expect(card.getByText(/^Étape 1 sur \d+$/)).toBeVisible()
  await card.getByRole('button', { name: 'Suivant' }).click()
  await expect(card.getByRole('heading', { name: 'Tableau de bord' })).toBeVisible()
  await card.getByRole('button', { name: 'Suivant' }).click()
  await expect(card.getByRole('heading', { name: 'Réservations' })).toBeVisible()
  await expect(page).toHaveURL(/\/reservations/)

  await card.getByRole('button', { name: 'Quitter la visite' }).click()
  await expect(card).toBeHidden()
  expect(finished).toBe(1)

  // Replayed from the menu, from the start.
  await page.getByRole('button', { name: 'Visite guidée' }).click()
  await expect(card.getByText(/^Étape 1 sur \d+$/)).toBeVisible()
})

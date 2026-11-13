import { type Page } from '@playwright/test'

import { expect, test } from './fixtures'

const E2E = { email: 'e2e@wedivo.test', password: 'Mariage-E2E-2026', slug: 'studio-e2e' }

async function login(page: Page): Promise<void> {
  await page.goto('/connexion')
  await page.getByLabel('Email').fill(E2E.email)
  await page.getByLabel(/^Mot de passe/).fill(E2E.password)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page).toHaveURL('/')
}

/**
 * CLAUDE.md §7.3 end to end: client → quote from the catalog (3 services) → send → the client
 * accepts on the public page → conversion into a contract → it shows in the client's sheet.
 */
test('quote journey: build, send, client accepts online, convert to contract', async ({
  page,
  browser,
}, testInfo) => {
  test.skip(testInfo.project.name === 'mobile', 'Covered on desktop')
  test.setTimeout(90_000)
  const tag = Date.now().toString(36)
  const couple = `Couple Devis ${tag}`

  await login(page)
  const started = Date.now()

  // 1. A new client with an email.
  await page.goto('/clients')
  await page.getByRole('button', { name: 'Nouveau client' }).first().click()
  const form = page.getByRole('dialog', { name: 'Nouveau client' })
  await form.getByLabel('Nom ou couple').fill(couple)
  await form.getByLabel('Email').fill(`couple-${tag}@e2e.wedivo.test`)
  await form.getByRole('button', { name: 'Ajouter le client' }).click()

  // 2. « Créer un devis » from the client sheet.
  await page
    .getByRole('dialog', { name: couple })
    .getByRole('link', { name: 'Créer un devis' })
    .click()
  await expect(page).toHaveURL(/\/devis\/nouveau\?client=/)

  // 3. Three catalog services in three clicks; « per guest » takes the 200 guests.
  await page.getByLabel('Nombre d’invités').fill('200')
  // A blank quote may start with the catalog's default services: start from an empty quote.
  await expect(page.getByRole('button', { name: 'Ajouter Menu traiteur ivoirien' })).toBeVisible()
  const remove = page.getByRole('button', { name: /^Retirer / })
  while ((await remove.count()) > 0) await remove.first().click()
  await page.getByRole('button', { name: 'Ajouter Menu traiteur ivoirien' }).click()
  await page.getByRole('button', { name: 'Ajouter Décoration de salle' }).click()
  await page.getByRole('button', { name: 'Ajouter Photographe' }).click()
  await expect(page.getByTestId('quote-line')).toHaveCount(3)
  // 200 × 12 000 + 900 000 + 300 000 = 3 600 000 FCFA
  await expect(page.getByTestId('editor-total')).toHaveText('3 600 000 FCFA')
  // The preview is the server rendering of the draft (the future PDF).
  await expect(page.getByTestId('server-preview')).toBeVisible({ timeout: 15_000 })

  await page.getByRole('button', { name: 'Enregistrer' }).click()
  await expect(page).toHaveURL(/\/devis\/[0-9a-f-]{36}$/)
  await expect(page.getByRole('heading', { name: /^DV-\d{4}-\d{4}$/ })).toBeVisible()
  expect(Date.now() - started).toBeLessThan(120_000) // « un devis de 3 prestations en moins de 2 minutes »

  // 4. Send.
  await page.getByRole('button', { name: 'Envoyer le devis' }).click()
  await page
    .getByRole('dialog', { name: 'Envoyer le devis' })
    .getByRole('button', { name: 'Envoyer le devis' })
    .click()
  // Reminders are gone (reservations-stock.md §2): the quote is emailed once, nothing planned.
  await expect(page.getByText(/^Devis DV-\d{4}-\d{4} envoyé\.$/)).toBeVisible()
  await expect(page.getByText('Envoyé', { exact: true })).toBeVisible()

  // 5. The client opens the public link (no account) and accepts.
  const quoteId = page.url().split('/').pop()!
  const details = await page.request.get(`/api/v1/quotes/${quoteId}`, {
    headers: { 'X-Organization': E2E.slug },
  })
  const { public_url: publicUrl } = (await details.json()) as { public_url: string }
  const visitor = await browser.newContext({ locale: 'fr-FR' })
  const publicPage = await visitor.newPage()
  await publicPage.goto(new URL(publicUrl).pathname)
  await expect(publicPage.getByRole('heading', { name: `Devis pour ${couple}` })).toBeVisible()
  await publicPage.getByRole('button', { name: 'Accepter le devis' }).click()
  await publicPage.getByRole('dialog').getByRole('button', { name: 'Accepter le devis' }).click()
  await expect(publicPage.getByText('Merci ! Vous avez accepté ce devis.')).toBeVisible()
  await visitor.close()

  // 6. The planner converts it into a contract.
  await page.reload()
  await expect(page.getByText('Accepté', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Convertir en contrat' }).click()
  await page
    .getByRole('dialog', { name: 'Convertir en contrat' })
    .getByRole('button', { name: 'Convertir en contrat' })
    .click()
  await expect(page.getByText(/^Contrat CT-\d{4}-\d{4} créé$/)).toBeVisible()

  // 7. The contract shows in the client's sheet.
  await page.goto('/clients')
  await page.getByLabel('Rechercher un client').fill(couple)
  await page.getByRole('cell', { name: couple }).click()
  const sheet = page.getByRole('dialog', { name: couple })
  await expect(sheet.getByText(/^CT-\d{4}-\d{4}$/)).toBeVisible()
  await expect(sheet.getByText('3 600 000 FCFA').first()).toBeVisible()
})

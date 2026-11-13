import { type Page } from '@playwright/test'

import { expect, test } from './fixtures'

const E2E = { email: 'e2e@wedivo.test', password: 'Mariage-E2E-2026' }

async function login(page: Page): Promise<void> {
  await page.goto('/connexion')
  await page.getByLabel('Email').fill(E2E.email)
  await page.getByLabel(/^Mot de passe/).fill(E2E.password)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page).toHaveURL('/')
}

/** reservations-stock.md §5: an article, its stock, maintenance, availability and journal. */
test('stock: create, buy, send to maintenance, see availability, cancel a movement', async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === 'mobile', 'Covered on desktop')
  test.setTimeout(60_000)
  const name = `Chaise E2E ${Date.now().toString(36)}`
  await login(page)
  await page.goto('/stock')

  // 1. A new article with 50 pieces.
  await page.getByRole('button', { name: 'Nouvel article' }).click()
  const form = page.getByRole('dialog', { name: 'Nouvel article' })
  await form.getByLabel('Nom de l’article').fill(name)
  await form.getByLabel('Catégorie').selectOption({ label: 'Mobilier' })
  await form.getByLabel('Quantité en stock').fill('50')
  await form.getByLabel('Seuil d’alerte').fill('10')
  await form.getByRole('button', { name: 'Ajouter l’article' }).click()
  await expect(page.getByText(`${name} ajouté au stock.`)).toBeVisible()
  const sheet = page.getByRole('dialog', { name })
  await expect(sheet.getByText('Stock aujourd’hui')).toBeVisible()

  // 2. Buy 10 more: 60.
  await sheet.getByRole('button', { name: 'Mouvement' }).click()
  const movement = page.getByRole('dialog', { name: 'Enregistrer un mouvement' })
  await movement.getByLabel('Quantité').fill('10')
  await movement.getByLabel('Motif').fill('Réassort')
  await movement.getByRole('button', { name: 'Enregistrer le mouvement' }).click()
  await expect(page.getByText(`Achat enregistré : ${name} × 10.`)).toBeVisible()

  // 3. 5 chairs go for repair: 55 available today.
  await sheet.getByRole('button', { name: 'Maintenance' }).click()
  const repair = page.getByRole('dialog', { name: 'Envoyer en maintenance' })
  await repair.getByLabel('Quantité').fill('5')
  await repair.getByLabel('Motif').fill('Pieds à resserrer')
  await repair.getByRole('button', { name: 'Envoyer en maintenance' }).click()
  await expect(page.getByText(`${name} part en maintenance.`)).toBeVisible()
  await expect(sheet.getByText('Pieds à resserrer').first()).toBeVisible()
  await sheet.getByRole('button', { name: 'Fermer' }).click()
  await page.getByLabel('Rechercher un article').fill(name)
  await expect(page.getByText('55 disponibles sur 60')).toBeVisible()

  // 4. The availability grid shows it day by day.
  await page.getByRole('tab', { name: 'Disponibilité' }).click()
  await expect(page.getByRole('button', { name })).toBeVisible()

  // 5. The purchase is cancelled with a reason: the journal keeps it, crossed out.
  await page.goto('/mouvements')
  const line = page.getByRole('row').filter({ hasText: name }).filter({ hasText: 'Réassort' })
  await line.getByRole('button', { name: 'Annuler' }).click()
  const cancel = page.getByRole('dialog', { name: 'Annuler ce mouvement' })
  await cancel.getByLabel('Motif de l’annulation').fill('Livraison refusée')
  await cancel.getByRole('button', { name: 'Annuler le mouvement' }).click()
  await expect(page.getByText('Mouvement annulé.')).toBeVisible()
  // Earlier runs leave their own cancelled purchases: look at this article's line only.
  await expect(
    page.getByRole('row').filter({ hasText: name }).getByText('Annulé : Livraison refusée'),
  ).toBeVisible()
})

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

/** `YYYY-MM-DDTHH:mm` in local time, `days` from today (datetime-local inputs). */
function at(days: number, hour: number): string {
  const d = new Date()
  d.setDate(d.getDate() + days)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(hour)}:00`
}

/**
 * reservations-stock.md §4.1–4.2: a reservation from the wizard to the closing — the stock is
 * blocked at confirmation, the deposit confirms it, the equipment leaves and comes back with
 * breakage billed on the reservation.
 */
test('reservations: create, confirm, deposit, checkout and return with breakage', async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === 'mobile', 'Covered on desktop')
  test.setTimeout(90_000)
  const stamp = Date.now().toString(36)
  const item = `Chaise Napoléon ${stamp}`
  const client = `Famille Mbarga ${stamp}`
  const title = `Dot Mbarga ${stamp}`
  // A far, unique window: earlier runs never compete for this stock.
  const offset = 200 + (Date.now() % 300)
  await login(page)

  // 1. 40 chairs in stock, rented 1 500 FCFA each.
  await page.goto('/stock')
  await page.getByRole('button', { name: 'Nouvel article' }).click()
  const form = page.getByRole('dialog', { name: 'Nouvel article' })
  await form.getByLabel('Nom de l’article').fill(item)
  await form.getByLabel('Catégorie').selectOption({ label: 'Mobilier' })
  await form.getByLabel('Quantité en stock').fill('40')
  await form.getByLabel('Prix de location (FCFA)').fill('1500')
  await form.getByLabel('Coût d’achat unitaire (FCFA)').fill('12000')
  await form.getByRole('button', { name: 'Ajouter l’article' }).click()
  await expect(page.getByText(`${item} ajouté au stock.`)).toBeVisible()

  // 2. The wizard: a new client, the event, its dates, 20 chairs.
  await page.goto('/reservations')
  await page.getByRole('button', { name: 'Nouvelle réservation' }).first().click()
  const wizard = page.getByRole('dialog', { name: 'Nouvelle réservation' })
  await wizard.getByLabel('Nom du nouveau client').fill(client)
  await wizard.getByRole('button', { name: 'Créer', exact: true }).click()
  await expect(page.getByText(`${client} ajouté aux clients.`)).toBeVisible()
  await wizard.getByLabel('Titre de l’événement').fill(title)
  await wizard.getByRole('button', { name: 'Continuer' }).click()

  await wizard.getByLabel('Livraison').fill(at(offset - 1, 9))
  await wizard.getByLabel('Début de l’événement').fill(at(offset, 15))
  await wizard.getByLabel('Fin de l’événement').fill(at(offset, 23))
  await wizard.getByLabel('Retour à l’entrepôt').fill(at(offset + 1, 12))
  await wizard.getByRole('button', { name: 'Continuer' }).click()

  await wizard.getByLabel('Ajouter un article').fill(item)
  const card = wizard.getByRole('listitem').filter({ hasText: item }).first()
  await expect(card.getByText('40 disponibles sur 40')).toBeVisible()
  await card.getByRole('button', { name: 'Location' }).click()
  await wizard.getByLabel(`Quantité : ${item}`).fill('20')
  await wizard.getByRole('button', { name: 'Continuer' }).click()
  await wizard.getByRole('button', { name: 'Continuer' }).click()

  // 3. Saved and confirmed: 30 % deposit expected, chairs blocked.
  await wizard.getByRole('button', { name: 'Enregistrer et confirmer' }).click()
  const sheet = page.getByRole('dialog', { name: title })
  await expect(sheet.getByText('En attente d’acompte').first()).toBeVisible()

  // 4. The client pays everything: the reservation is confirmed.
  await sheet.getByRole('button', { name: 'Enregistrer un paiement' }).click()
  const payment = page.getByRole('dialog', { name: 'Enregistrer un paiement' })
  await payment.getByRole('button', { name: 'Enregistrer', exact: true }).click()
  await expect(page.getByText(/Paiement de .* enregistré\./)).toBeVisible()
  await expect(sheet.getByText('Confirmée').first()).toBeVisible()

  // 4b. The final invoice (§6.3): numbered FA-…, already paid by the payment above.
  await sheet.getByRole('button', { name: 'Facture finale' }).click()
  await expect(page.getByText(/Facture FA-\d{4}-\d{4} émise\./)).toBeVisible()
  await expect(sheet.getByText('Payée', { exact: true })).toBeVisible()

  // 5. The chairs leave the warehouse.
  await sheet.getByRole('button', { name: 'Sortie du matériel' }).click()
  await page
    .getByRole('dialog', { name: 'Sortie du matériel' })
    .getByRole('button', { name: 'Valider la sortie' })
    .click()
  await expect(page.getByText('Matériel sorti de l’entrepôt.')).toBeVisible()

  // 6. 18 come back, 2 broken: the breakage is billed and the reservation closes.
  await sheet.getByRole('button', { name: 'Saisir le retour' }).click()
  const back = page.getByRole('dialog', { name: 'Retour du matériel' })
  await back.getByLabel(`Rendus : ${item}`).fill('18')
  await back.getByLabel(`Abîmés : ${item}`).fill('2')
  await back.getByRole('button', { name: 'Valider le retour' }).click()
  await expect(page.getByText('Retour enregistré, réservation clôturée.')).toBeVisible()
  await expect(sheet.getByText('Clôturée').first()).toBeVisible()
  await expect(sheet.getByText(/Casse/).first()).toBeVisible()
})

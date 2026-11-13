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

const pad = (n: number) => String(n).padStart(2, '0')
const isoDay = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
const local = (d: Date, hour: number) => `${isoDay(d)}T${pad(hour)}:00`
const plus = (d: Date, days: number) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + days)

/**
 * reservations-stock.md §4.3: a reservation shows its steps in the calendar and in the
 * logistic planning; dragging it to another day moves every date.
 */
test('calendar: steps in each view, drag a reservation to the next day', async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === 'mobile', 'Drag and drop is a desktop gesture')
  test.setTimeout(90_000)
  const stamp = Date.now().toString(36)
  const item = `Nappe ivoire ${stamp}`
  const client = `Famille Tano ${stamp}`
  // A Wednesday far ahead: delivery on Tuesday, pickup on Thursday, all in one week.
  let event = plus(new Date(), 300 + (Date.now() % 200))
  while (event.getDay() !== 3) event = plus(event, 1)
  await login(page)

  await page.goto('/stock')
  await page.getByRole('button', { name: 'Nouvel article' }).click()
  const form = page.getByRole('dialog', { name: 'Nouvel article' })
  await form.getByLabel('Nom de l’article').fill(item)
  await form.getByLabel('Catégorie').selectOption({ label: 'Linge de table' })
  await form.getByLabel('Quantité en stock').fill('60')
  await form.getByLabel('Prix de location (FCFA)').fill('2500')
  await form.getByRole('button', { name: 'Ajouter l’article' }).click()
  await expect(page.getByText(`${item} ajouté au stock.`)).toBeVisible()

  await page.goto('/reservations')
  await page.getByRole('button', { name: 'Nouvelle réservation' }).first().click()
  const wizard = page.getByRole('dialog', { name: 'Nouvelle réservation' })
  await wizard.getByLabel('Nom du nouveau client').fill(client)
  await wizard.getByRole('button', { name: 'Créer', exact: true }).click()
  await expect(page.getByText(`${client} ajouté aux clients.`)).toBeVisible()
  await wizard.getByLabel('Titre de l’événement').fill(`Dot ${stamp}`)
  await wizard.getByRole('button', { name: 'Continuer' }).click()
  await wizard.getByLabel('Livraison').fill(local(plus(event, -1), 9))
  await wizard.getByLabel('Début de l’événement').fill(local(event, 15))
  await wizard.getByLabel('Fin de l’événement').fill(local(event, 23))
  await wizard.getByLabel('Retour à l’entrepôt').fill(local(plus(event, 1), 12))
  await wizard.getByLabel('Véhicule').fill('Fourgon E2E')
  await wizard.getByRole('button', { name: 'Continuer' }).click()
  await wizard.getByLabel('Ajouter un article').fill(item)
  await wizard
    .getByRole('listitem')
    .filter({ hasText: item })
    .first()
    .getByRole('button', { name: 'Location' })
    .click()
  await wizard.getByLabel(`Quantité : ${item}`).fill('30')
  await wizard.getByRole('button', { name: 'Continuer' }).click()
  await wizard.getByRole('button', { name: 'Continuer' }).click()
  await wizard.getByRole('button', { name: 'Enregistrer et confirmer' }).click()
  await expect(page.getByRole('dialog', { name: `Dot ${stamp}` })).toBeVisible()

  // Week view: delivery the day before (violet), the event, the return the day after.
  await page.goto(`/calendrier?vue=semaine&jour=${isoDay(event)}`)
  const day = (d: Date) => page.locator(`[data-day="${isoDay(d)}"]`)
  await expect(day(plus(event, -1)).getByText(`09:00 · ${client}`)).toBeVisible()
  const chip = day(event).locator('button[draggable="true"]', { hasText: `15:00 · ${client}` })
  await expect(chip).toBeVisible()
  await expect(day(plus(event, 1)).getByText(`12:00 · ${client}`)).toBeVisible()

  // Logistic planning: the vehicle is there.
  await page.getByRole('button', { name: 'Planning logistique' }).click()
  await expect(page.getByText('Fourgon E2E').first()).toBeVisible()

  // Drag the event one day later: every step follows.
  await page.getByRole('button', { name: 'Semaine' }).click()
  await chip.dragTo(day(plus(event, 1)))
  await expect(page.getByText(/déplacée au/)).toBeVisible()
  await expect(
    day(plus(event, 1)).locator('button', { hasText: `15:00 · ${client}` }),
  ).toBeVisible()
  await expect(day(event).getByText(`09:00 · ${client}`)).toBeVisible() // delivery moved too
})

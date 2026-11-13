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
const today = () => {
  const d = new Date()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/**
 * reservations-stock.md §7: a day worker joins the team, is assigned to today's event, checks
 * in, and the month's pay counts his day.
 */
test('staff: add a person, assign to a reservation, check in, pay of the month', async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === 'mobile', 'Covered on desktop')
  test.setTimeout(90_000)
  const stamp = Date.now().toString(36)
  const name = `Brice E2E ${stamp}`
  await login(page)

  // 1. A day worker at 8 000 a day.
  await page.goto('/personnel')
  await page.getByRole('button', { name: 'Ajouter une personne' }).click()
  const form = page.getByRole('dialog', { name: 'Ajouter une personne' })
  await form.getByLabel('Nom complet').fill(name)
  await form.getByLabel('Poste').fill('Installateur')
  await form.getByLabel('Rémunération').selectOption('daily')
  await form.getByLabel('Taux (FCFA)').fill('8000')
  await form.getByRole('button', { name: 'Enregistrer' }).click()
  await expect(page.getByText(`${name} ajouté(e) à l’équipe.`)).toBeVisible()
  await expect(page.getByRole('button', { name: new RegExp(name) })).toContainText('Disponible')

  // 2. A draft reservation today, and the person on its event.
  await page.goto('/reservations')
  await page.getByRole('button', { name: 'Nouvelle réservation' }).first().click()
  const wizard = page.getByRole('dialog', { name: 'Nouvelle réservation' })
  await wizard.getByLabel('Nom du nouveau client').fill(`Client ${stamp}`)
  await wizard.getByRole('button', { name: 'Créer', exact: true }).click()
  await expect(page.getByText(`Client ${stamp} ajouté aux clients.`)).toBeVisible()
  await wizard.getByLabel('Titre de l’événement').fill(`Baptême ${stamp}`)
  await wizard.getByRole('button', { name: 'Continuer' }).click()
  await wizard.getByLabel('Début de l’événement').fill(`${today()}T00:30`)
  await wizard.getByLabel('Fin de l’événement').fill(`${today()}T23:30`)
  await wizard.getByRole('button', { name: 'Enregistrer le brouillon' }).click()
  const sheet = page.getByRole('dialog', { name: `Baptême ${stamp}` })
  await sheet
    .getByLabel('Personne', { exact: true })
    .selectOption({ label: `${name} · Installateur` })
  await sheet.getByLabel('Étape').selectOption('event')
  await sheet.getByRole('button', { name: 'Affecter' }).click()
  await expect(page.getByText(`${name} affecté(e).`)).toBeVisible()

  // 3. Today's check-in.
  await page.goto('/presences')
  const row = page.getByRole('listitem').filter({ hasText: name })
  await row.getByRole('button', { name: 'Arrivée' }).click()
  await expect(page.getByText('Arrivée pointée.')).toBeVisible()
  await expect(row.getByText(/Présent|En retard/)).toBeVisible()

  // 4. The month's pay counts the day: 8 000.
  await page.goto('/paie')
  await page.getByRole('tab', { name: 'Salaires du mois' }).click()
  await page.getByRole('button', { name: 'Préparer la paie du mois' }).click()
  const recalc = page.getByRole('button', { name: 'Recalculer' })
  await recalc.click()
  await expect(page.getByText('Paie recalculée depuis les présences.')).toBeVisible()
  await expect(page.getByRole('row').filter({ hasText: name })).toContainText(/8\s000/)
})

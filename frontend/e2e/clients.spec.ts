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

/** reservations-stock.md §4.4: one sheet per client, searchable, archived rather than lost. */
test('clients: create, find, archive, bring back, delete', async ({ page }) => {
  const name = `Société E2E ${Date.now().toString(36)}`
  await login(page)
  await page.goto('/clients')

  await page.getByRole('button', { name: 'Nouveau client' }).first().click()
  const form = page.getByRole('dialog', { name: 'Nouveau client' })
  await form.getByLabel('Nom ou couple').fill(name)
  await form.getByLabel('Entreprise').fill('Orange Events SARL')
  await form.getByLabel('Téléphone', { exact: true }).fill('+237 6 99 12 34 56')
  await form.getByLabel('Préférences').fill('Chaises Chiavari, nappes blanches')
  await form.getByRole('button', { name: 'Ajouter le client' }).click()

  // The new client opens in its sheet.
  const sheet = page.getByRole('dialog', { name })
  await expect(sheet.getByText('Chaises Chiavari, nappes blanches')).toBeVisible()
  await expect(sheet.getByText('Aucune commande pour l’instant.')).toBeVisible()

  // Archive: it leaves the list but stays reachable.
  await sheet.getByRole('button', { name: 'Archiver' }).click()
  await expect(page.getByText('Client archivé.')).toBeVisible()
  await sheet.getByRole('button', { name: 'Fermer' }).click()
  await page.getByLabel('Rechercher un client').fill(name)
  await expect(page.getByText('Aucun client ne correspond à cette recherche.')).toBeVisible()
  await page.getByRole('switch', { name: 'Afficher les archives' }).click()
  // A table row on desktop, a card on phones: the name opens the sheet in both.
  await page.getByRole('main').getByText(name, { exact: true }).click()
  await sheet.getByRole('button', { name: 'Sortir des archives' }).click()
  await expect(page.getByText('Client sorti des archives.')).toBeVisible()

  // Delete (traced on the server).
  await sheet.getByRole('button', { name: 'Supprimer' }).click()
  await page
    .getByRole('dialog', { name: 'Supprimer' })
    .getByRole('button', { name: 'Supprimer' })
    .click()
  await expect(page.getByText('Client supprimé.')).toBeVisible()
})

test('the old prospect and reminder addresses lead to live pages', async ({ page }) => {
  await login(page)
  await page.goto('/prospects')
  await expect(page).toHaveURL('/clients')
  await expect(page.getByRole('heading', { name: 'Clients', level: 1 })).toBeVisible()
  await page.goto('/relances')
  await expect(page).toHaveURL('/')
  await expect(page.getByRole('link', { name: /Relances/ })).toHaveCount(0)
})

/** reservations-stock.md §2: the bell is the internal alert center, never a reminder list. */
test('the bell opens the alert center', async ({ page }) => {
  await login(page)
  await page.getByTestId('alert-bell').click()
  const panel = page.getByRole('region', { name: 'Notifications et alertes' })
  await expect(panel).toBeVisible()
  await panel.getByRole('tab', { name: /Alertes/ }).click()
  await expect(panel.getByText(/Les plus urgentes d’abord/)).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(panel).toBeHidden()
})

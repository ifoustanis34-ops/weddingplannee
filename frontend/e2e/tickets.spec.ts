import { type Page } from '@playwright/test'

import { expect, test } from './fixtures'

const ORG = 'studio-e2e'

async function login(page: Page): Promise<void> {
  await page.goto('/connexion')
  await page.getByLabel('Email').fill('e2e@wedivo.test')
  await page.getByLabel(/^Mot de passe/).fill('Mariage-E2E-2026')
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page).toHaveURL('/')
}

/** docs/specs/devis-billets.md §6: guest list → ticket → the guest's page → answer. */
test('tickets: add a guest, generate the ticket, the guest opens it and confirms', async ({
  page,
  browser,
}, testInfo) => {
  test.skip(testInfo.project.name === 'mobile', 'Covered on desktop')
  await login(page)
  const csrf = (await page.context().cookies()).find((c) => c.name === 'csrftoken')!.value
  const couple = `Awa & Moussa ${Date.now().toString(36)}`
  const response = await page.request.post('/api/v1/weddings', {
    headers: { 'X-Organization': ORG, 'X-CSRFToken': csrf, Origin: 'http://localhost:8090' },
    data: { title: couple, date: '2027-06-12', venue: 'Salle Bellevue' },
  })
  expect(response.ok(), await response.text()).toBeTruthy()
  const wedding = (await response.json()) as { id: string }

  await page.goto(`/mariages/${wedding.id}/billets`)
  await expect(page.getByTestId('ticket-preview')).toBeVisible({ timeout: 20_000 })
  await page.getByRole('button', { name: 'Ajouter un invité' }).click()
  const modal = page.getByRole('dialog', { name: 'Ajouter un invité' })
  await modal.getByLabel('Nom de l’invité ou de la famille').fill('Famille Kouassi')
  await modal.getByLabel('Places').fill('4')
  await modal.getByRole('button', { name: 'Ajouter un invité' }).click()

  const row = page.getByTestId('guest-row').filter({ hasText: 'Famille Kouassi' })
  await expect(row).toContainText('Non généré')
  await row.getByRole('button', { name: 'Générer le billet de Famille Kouassi' }).click()
  await expect(page.getByText('Génération terminée')).toBeVisible({ timeout: 30_000 })
  await expect(row).toContainText('Généré')
  await expect(row).toContainText(/WDV-AM-\d{4}/)

  // The guest's link, as copied for WhatsApp, opens their ticket without an account.
  const guests = await page.request.get(`/api/v1/weddings/${wedding.id}/guests`, {
    headers: { 'X-Organization': ORG },
  })
  const url = ((await guests.json()) as { ticket: { url: string } }[])[0]?.ticket.url ?? ''
  const guest = await (await browser.newContext()).newPage()
  await guest.route(/^https:\/\/fonts\.(googleapis|gstatic)\.com\//, (route) => route.abort())
  await guest.goto(url)
  await expect(guest.getByRole('heading', { name: /Mariage de Awa & Moussa/ })).toBeVisible()
  await expect(guest.getByTestId('public-ticket')).toBeVisible()
  await guest.getByRole('button', { name: 'Confirmer ma présence' }).click()
  await expect(guest.getByText('Votre présence est confirmée')).toBeVisible()

  await page.reload()
  await expect(page.getByTestId('guest-row').filter({ hasText: 'Famille Kouassi' })).toContainText(
    'Confirmé',
  )
})

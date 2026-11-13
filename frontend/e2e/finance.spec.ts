import { type APIRequestContext, type Page } from '@playwright/test'

import { expect, test } from './fixtures'

const ORG = 'studio-e2e'
const NNBSP = ' '

async function login(page: Page): Promise<void> {
  await page.goto('/connexion')
  await page.getByLabel('Email').fill('e2e@wedivo.test')
  await page.getByLabel(/^Mot de passe/).fill('Mariage-E2E-2026')
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page).toHaveURL('/')
}

const money = (amount: number) =>
  `${String(amount).replace(/\B(?=(\d{3})+(?!\d))/g, NNBSP)}\u00a0FCFA`

async function dashboardBalance(page: Page): Promise<number> {
  const response = await page.request.get('/api/v1/dashboard/summary', {
    headers: { 'X-Organization': ORG },
  })
  const data = (await response.json()) as { signature: { to_collect: number } }
  return data.signature.to_collect
}

/** Accepted quote converted into a 1 500 000 FCFA contract, prepared through the API. */
async function contractThroughApi(page: Page, couple: string): Promise<string> {
  const csrf = (await page.context().cookies()).find((c) => c.name === 'csrftoken')!.value
  const request: APIRequestContext = page.request
  const headers = { 'X-Organization': ORG, 'X-CSRFToken': csrf, Origin: 'http://localhost:8090' }
  const post = async (url: string, data?: unknown) => {
    const response = await request.post(`/api/v1${url}`, { headers, data })
    expect(response.ok(), `${url}: ${await response.text()}`).toBeTruthy()
    return (await response.json()) as { id: string }
  }
  const client = await post('/clients', { name: couple, email: 'finance@e2e.wedivo.test' })
  const quote = await post('/quotes', {
    client: client.id,
    wedding_date: '2027-03-20',
    deposit_pct: 30,
    lines: [{ label: 'Mariage complet', unit: 'flat', unit_price: 1_500_000, quantity: 1 }],
  })
  await post(`/quotes/${quote.id}/accept`)
  const converted = (await post(`/quotes/${quote.id}/convert`)) as unknown as {
    contract: { id: string }
  }
  return converted.contract.id
}

/** Same short form as the dashboard figures (« 10,48 M », « 630 000 »). */
const short = (amount: number) =>
  amount >= 1_000_000
    ? `${String(Math.round((amount / 1_000_000) * 100) / 100).replace('.', ',')} M`
    : String(amount).replace(/\B(?=(\d{3})+(?!\d))/g, NNBSP)

/** CLAUDE.md §7.5 + reservations-stock.md §8: record a payment, balance and dashboard follow. */
test('payment: mark the deposit paid, refuse an overpayment, dashboard updated', async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === 'mobile', 'Covered on desktop')
  const couple = `Couple Finance ${Date.now().toString(36)}`
  await login(page)
  const contractId = await contractThroughApi(page, couple)
  const balanceBefore = await dashboardBalance(page)

  await page.goto(`/finances?contract=${contractId}`)
  const drawer = page.getByRole('dialog', { name: couple })
  await expect(
    drawer.getByText('Ce n’est pas le bénéfice net comptable de l’entreprise.'),
  ).toBeVisible()

  // « Marquer payé » on the deposit: the amount (450 000) is prefilled.
  await drawer
    .locator('li', { hasText: 'Acompte' })
    .getByRole('button', { name: 'Marquer payé' })
    .click()
  const modal = page.getByRole('dialog', { name: 'Enregistrer un paiement' })
  await expect(modal.getByLabel('Montant (FCFA)')).toHaveValue('450000')
  await modal.getByLabel('Référence').fill('OM-E2E-1')
  await modal.getByRole('button', { name: 'Enregistrer le paiement' }).click()
  await expect(
    page.getByText(`Paiement de ${money(450_000)} enregistré pour ${couple}`),
  ).toBeVisible()
  await expect(
    drawer.locator('li', { hasText: 'Acompte' }).getByText('Payé', { exact: true }),
  ).toBeVisible()
  await expect(drawer.getByText(/RC-\d{4}-\d{4}/)).toBeVisible()

  // A payment can never exceed the balance (1 050 000 left).
  await drawer.getByRole('button', { name: 'Enregistrer un paiement' }).click()
  await modal.getByLabel('Montant (FCFA)').fill('2000000')
  await modal.getByRole('button', { name: 'Enregistrer le paiement' }).click()
  await expect(
    modal.getByText(`Le montant dépasse le solde restant (1${NNBSP}050${NNBSP}000 FCFA).`),
  ).toBeVisible()
  await modal.getByRole('button', { name: 'Annuler' }).click()

  // The dashboard reflects the money received: its cache was dropped by the payment, so it
  // shows the server's balance now. Other journeys may add contracts in parallel (same
  // workspace): the payment's own effect is checked on this contract (1 050 000 left above).
  const balanceAfter = await dashboardBalance(page)
  expect(balanceAfter).not.toBe(balanceBefore)
  await page.goto('/')
  await expect(page.getByTestId('signature-toCollect')).toHaveText(short(balanceAfter))
})

/** reservations-stock.md §6.2 and §8: a general expense from the dashboard, then the year view. */
test('dashboard: record a general expense and switch the period', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === 'mobile', 'Covered on desktop')
  await login(page)
  await page.goto('/')
  await expect(page.getByRole('heading', { name: /^Bonjour/ })).toBeVisible()

  await page.getByRole('button', { name: 'Enregistrer une dépense' }).click()
  const modal = page.getByRole('dialog', { name: 'Enregistrer une dépense' })
  await modal.getByLabel('Libellé').fill('Carburant du camion')
  await modal.getByLabel('Montant (FCFA)').fill('45000')
  // A general expense needs its category: the form says so before calling the server.
  await modal.getByRole('button', { name: 'Enregistrer la dépense' }).click()
  await expect(modal.getByText('Choisissez la catégorie de cette dépense.')).toBeVisible()
  await modal.getByLabel('Catégorie').selectOption({ label: 'Transport et carburant' })
  await modal.getByRole('button', { name: 'Enregistrer la dépense' }).click()
  await expect(page.getByText(`Dépense de ${money(45_000)} enregistrée.`)).toBeVisible()

  await page.getByRole('radio', { name: 'Cette année' }).click()
  await expect(page).toHaveURL(/periode=year/)
  await expect(page.getByText('Chiffre d’affaires réalisé · cette année')).toBeVisible()
  await expect(page.getByText('Transport et carburant').first()).toBeVisible()
})

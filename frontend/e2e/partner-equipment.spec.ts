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

/**
 * Partner equipment (feedback 14/11/2026): the two lists imported from one sheet (checked
 * first, then saved), then shown under « Matériel des partenaires » and on the articles.
 */
test('partner equipment: import both lists, see what each partner lends', async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === 'mobile', 'Covered on desktop')
  test.setTimeout(60_000)
  const stamp = Date.now().toString(36)
  const ours = `Nappe E2E ${stamp}`
  const theirs = `Arche E2E ${stamp}`
  const partner = `Partenaire E2E ${stamp}`
  const csv = [
    'Type;Article;Catégorie;Quantité;Prix location;Partenaire;Prix partenaire',
    `Interne;${ours};Linge de table;80;800;;`,
    `Partenaire;${ours};Linge de table;40;;${partner};300`,
    `Partenaire;${theirs};Décoration;2;75000;${partner};40000`,
  ].join('\n')

  await login(page)
  await page.goto('/stock?onglet=partners')
  await page.getByRole('button', { name: 'Importer mes listes' }).first().click()
  const dialog = page.getByRole('dialog', { name: 'Importer mes listes du matériel' })
  await dialog.locator('input[type=file]').setInputFiles({
    name: 'materiel.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from(csv, 'utf-8'),
  })

  // 1. Checked first: nothing saved yet.
  await dialog.getByRole('button', { name: 'Vérifier le fichier' }).click()
  await expect(dialog.getByText('Aperçu : rien n’est encore enregistré.')).toBeVisible()
  await expect(dialog.getByText('offres partenaires créées')).toBeVisible()

  // 2. Imported.
  await dialog.getByRole('button', { name: 'Importer', exact: true }).click()
  await expect(dialog.getByText('Import terminé.')).toBeVisible()
  await dialog.getByRole('button', { name: 'Fermer' }).last().click()

  // 3. The partner and what it lends.
  await page.getByRole('searchbox').fill(stamp)
  await expect(page.getByText(partner)).toBeVisible()
  await expect(page.getByText(theirs)).toBeVisible()
  // Scoped to this run's item: earlier runs leave other « Nappe E2E » with the same quantity.
  await expect(page.getByRole('listitem').filter({ hasText: ours })).toContainText('À nous : 80')

  // 4. On the articles: ours with what partners add.
  await page.goto('/stock')
  await page.getByRole('searchbox').fill(ours)
  await expect(page.getByText('+40 chez partenaires')).toBeVisible()
})

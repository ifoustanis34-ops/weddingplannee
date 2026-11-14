import { execSync } from 'node:child_process'

import { expect, test } from './fixtures'

/**
 * Platform console (super-admin, 14/11/2026): a Wedivo team account lands in /plateforme, sees
 * every agency and account, gives an agency lifetime access and opens an account.
 */
const EMAIL = 'console-e2e@wedivo.test'
const PASSWORD = 'Console-e2e-2026'
const OWNER = { email: 'e2e@wedivo.test', password: 'Mariage-E2E-2026', name: 'Planner E2E' }

test.beforeAll(() => {
  execSync(
    'docker compose -f ../infra/docker-compose.dev.yml exec -T api python manage.py seed_e2e',
    {
      stdio: 'ignore',
    },
  )
  execSync(
    `docker compose -f ../infra/docker-compose.dev.yml exec -T api python manage.py ` +
      `create_platform_admin --email ${EMAIL} --name "Console E2E" --password ${PASSWORD}`,
    { stdio: 'ignore' },
  )
})

test('a super-admin manages agencies and accounts from the console', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === 'mobile', 'Covered on desktop')
  await page.goto('/connexion')
  await page.getByLabel('Email').fill(EMAIL)
  await page.getByLabel(/^Mot de passe/).fill(PASSWORD)
  await page.getByRole('button', { name: 'Se connecter' }).click()

  await expect(page).toHaveURL(/\/plateforme$/)
  await expect(page.getByRole('heading', { level: 1, name: 'Bonjour Console' })).toBeVisible()
  await expect(page.getByText('Croissance sur 12 mois')).toBeVisible()
  await page.screenshot({ path: 'test-results/platform-overview.png', fullPage: true })

  await page.goto('/plateforme/agences')
  await expect(page.getByRole('heading', { level: 1, name: 'Agences' })).toBeVisible()
  await page.getByRole('searchbox').fill('studio-e2e')
  const row = page.getByRole('button', { name: 'Studio E2E' })
  await expect(row).toBeVisible()
  await page.screenshot({ path: 'test-results/platform-agencies.png', fullPage: true })
  await row.click()
  const drawer = page.getByRole('dialog')
  await expect(drawer.getByText(OWNER.email).first()).toBeVisible()
  await page.screenshot({ path: 'test-results/platform-agency.png' })

  await page.goto('/plateforme/utilisateurs')
  await expect(page.getByRole('heading', { level: 1, name: 'Utilisateurs' })).toBeVisible()
  await page.getByRole('searchbox').fill(OWNER.email)
  await page.getByRole('button', { name: OWNER.name }).click()
  await expect(page.getByRole('dialog').getByText('Agences et rôles')).toBeVisible()
  await page.screenshot({ path: 'test-results/platform-account.png' })

  await page.goto('/plateforme/journal')
  await expect(page.getByRole('heading', { level: 1, name: 'Journal' })).toBeVisible()
})

test('an agency owner never reaches the console', async ({ page }) => {
  await page.goto('/connexion')
  await page.getByLabel('Email').fill(OWNER.email)
  await page.getByLabel(/^Mot de passe/).fill(OWNER.password)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page).toHaveURL('/')
  await page.goto('/plateforme')
  await expect(page).not.toHaveURL(/plateforme/)
})

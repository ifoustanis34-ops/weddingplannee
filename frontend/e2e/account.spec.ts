import { expect, test } from './fixtures'

/** CLAUDE.md §15: an agency creates its account, gets its subdomain, and signs back in. */
test('an agency creates its space, signs out and signs back in', async ({ page }, testInfo) => {
  const suffix = `${Date.now().toString(36)}${testInfo.project.name.charAt(0)}`
  const company = `Agence Test ${suffix}`
  const email = `planner-${suffix}@e2e.wedivo.test`
  const password = 'Mariage-E2E-2026'

  await page.goto('/inscription')
  await page.getByLabel('Nom de l’entreprise').fill(company)
  await page.getByLabel('Ville').fill('Abidjan')
  await page.getByRole('button', { name: 'Continuer' }).click()

  await page.getByLabel('Nom complet').fill('Fatou Bamba')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel(/^Mot de passe/).fill(password)
  await page.getByRole('button', { name: 'Continuer' }).click()

  const slug = page.getByLabel('Adresse de votre espace')
  await expect(slug).toHaveValue(`agence-test-${suffix}`)
  await expect(page.getByText('Adresse disponible.')).toBeVisible()
  await page.getByRole('button', { name: 'Créer mon espace' }).click()

  await expect(page).toHaveURL('/')
  await expect(page.getByRole('heading', { name: 'Bonjour Fatou' })).toBeVisible()
  // The space exists with its own subdomain (checked through the session, same on every screen).
  const me = (await (await page.request.get('/api/v1/auth/me')).json()) as {
    organizations: { name: string; slug: string; role: string }[]
  }
  expect(me.organizations).toEqual([
    expect.objectContaining({ name: company, slug: `agence-test-${suffix}`, role: 'owner' }),
  ])
  await expect(page.getByText('Confirmez votre email')).toBeVisible()

  await page.keyboard.press('Control+k')
  await page.getByRole('combobox').fill('deconnexion')
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/connexion/)

  await page.getByLabel('Email').fill(email)
  await page.getByLabel(/^Mot de passe/).fill(password)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page.getByRole('heading', { name: 'Bonjour Fatou' })).toBeVisible()
})

test('a protected page sends visitors to the login and back', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveURL(/\/connexion/)
  await page.getByLabel('Email').fill('aicha.kone@maison-elegance.ci')
  await page.getByLabel(/^Mot de passe/).fill('Wedivo-demo-2026')
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page.getByRole('heading', { name: 'Bonjour Aïcha' })).toBeVisible()
})

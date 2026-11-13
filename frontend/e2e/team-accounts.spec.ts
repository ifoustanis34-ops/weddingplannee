import { expect, test } from './fixtures'

const E2E = { email: 'e2e@wedivo.test', password: 'Mariage-E2E-2026' }

/**
 * Feedback 13/11/2026: the owner opens an account for a team member (temporary password); the
 * person signs in, is asked to choose their own password, then changes their name.
 */
test('the owner creates an account; the member chooses a password and edits the profile', async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === 'mobile', 'Covered on desktop')
  const stamp = Date.now().toString(36)
  const email = `linda-${stamp}@e2e.wedivo.test`

  await page.goto('/connexion')
  await page.getByLabel('Email').fill(E2E.email)
  await page.getByLabel(/^Mot de passe/).fill(E2E.password)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page).toHaveURL('/')

  await page.goto('/parametres/equipe')
  await page.getByRole('button', { name: 'Créer un compte' }).click()
  const dialog = page.getByRole('dialog', { name: 'Créer un compte' })
  await dialog.getByLabel('Nom complet').fill(`Linda ${stamp}`)
  await dialog.getByLabel('Email').fill(email)
  await dialog.getByLabel('Téléphone').fill('+237 657 84 74 84')
  const temporary = await dialog.getByLabel('Mot de passe provisoire').inputValue()
  expect(temporary).toMatch(/^\w{4}-\w{4}-\w{4}$/)
  await dialog.getByRole('button', { name: 'Créer le compte' }).click()

  const handover = page.getByRole('dialog', { name: 'Accès à transmettre' })
  await expect(handover).toContainText(`Mot de passe provisoire : ${temporary}`)
  await expect(handover.getByRole('link', { name: 'Envoyer par WhatsApp' })).toHaveAttribute(
    'href',
    /^https:\/\/wa\.me\/237657847484\?text=/,
  )
  await handover.getByRole('button', { name: 'Terminé' }).click()
  await expect(handover).toBeHidden()
  await expect(page.getByRole('cell', { name: new RegExp(email) })).toBeVisible()

  // The new member signs in and must choose their own password first.
  await page.getByRole('button', { name: 'Se déconnecter' }).click()
  await expect(page).toHaveURL(/\/connexion/)
  await page.getByLabel('Email').fill(email)
  await page.getByLabel(/^Mot de passe/).fill(temporary)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page).toHaveURL('/profil')
  await expect(page.getByText('Choisissez votre mot de passe')).toBeVisible()
  await page.goto('/')
  await expect(page).toHaveURL('/profil')

  await page.getByLabel('Mot de passe provisoire').fill(temporary)
  await page.getByLabel('Nouveau mot de passe').fill('Mon-Secret-Douala-77')
  await page.getByLabel('Confirmez le nouveau').fill('Mon-Secret-Douala-77')
  await page.getByRole('button', { name: 'Changer le mot de passe' }).click()
  await expect(page).toHaveURL('/')

  await page.goto('/profil')
  await page.getByLabel('Nom complet').fill(`Linda Abena ${stamp}`)
  await page.getByRole('button', { name: 'Enregistrer' }).click()
  await expect(page.getByText('Profil enregistré.')).toBeVisible()
  await expect(page.getByRole('link', { name: /Mon profil/ })).toContainText(`Linda Abena ${stamp}`)
})

import { describe, expect, it } from 'vitest'

import { accessMessage, generatePassword } from '@/app/passwords'

describe('temporary passwords', () => {
  it('reads easily and is long enough', () => {
    const password = generatePassword()
    expect(password).toMatch(/^[a-zA-Z2-9]{4}-[a-zA-Z2-9]{4}-[a-zA-Z2-9]{4}$/)
    expect(password).not.toMatch(/[01ilIoO]/)
  })
  it('differs from one call to the next', () => {
    expect(generatePassword()).not.toBe(generatePassword())
  })
  it('writes the message with the temporary password', () => {
    const text = accessMessage({
      name: 'Linda Abena',
      organization: 'Canopy House',
      email: 'linda@canopy.cm',
      password: 'abcd-efgh-jkmn',
      url: 'http://localhost:8090/connexion',
    })
    expect(text).toContain('Bonjour Linda,')
    expect(text).toContain('Mot de passe provisoire : abcd-efgh-jkmn')
  })
  it('tells an existing account to keep its own password', () => {
    const text = accessMessage({
      name: 'Koffi',
      organization: 'A',
      email: 'k@a.cm',
      password: null,
      url: 'u',
    })
    expect(text).toContain('mot de passe Wedivo habituel')
  })
})

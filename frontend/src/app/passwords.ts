/**
 * Temporary passwords the owner hands over (feedback 13/11/2026): easy to read aloud or type on
 * a phone (no 0/O, 1/l/I), long enough for the server's rules, from the browser's secure random.
 */
const ALPHABET = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'

export function generatePassword(groups = 3, size = 4): string {
  const bytes = new Uint8Array(groups * size)
  crypto.getRandomValues(bytes)
  const chars = [...bytes].map((byte) => ALPHABET[byte % ALPHABET.length]!)
  return Array.from({ length: groups }, (_, i) =>
    chars.slice(i * size, (i + 1) * size).join(''),
  ).join('-')
}

/** The message to send the person (copied, or opened in WhatsApp: never sent by Wedivo). */
export function accessMessage(input: {
  name: string
  organization: string
  email: string
  password: string | null
  url: string
}): string {
  const lines = [
    `Bonjour ${input.name.split(' ')[0]},`,
    `Voici votre accès à l’espace ${input.organization} sur Wedivo :`,
    `Adresse : ${input.url}`,
    `Email : ${input.email}`,
  ]
  if (input.password) {
    lines.push(`Mot de passe provisoire : ${input.password}`)
    lines.push('À la première connexion, choisissez votre propre mot de passe.')
  } else {
    lines.push('Connectez-vous avec votre mot de passe Wedivo habituel.')
  }
  return lines.join('\n')
}

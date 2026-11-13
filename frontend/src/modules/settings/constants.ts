/** Time zones offered in the settings (francophone Africa first, then Europe and Canada). */
export const TIMEZONES = [
  'Africa/Abidjan',
  'Africa/Dakar',
  'Africa/Bamako',
  'Africa/Ouagadougou',
  'Africa/Lome',
  'Africa/Porto-Novo',
  'Africa/Niamey',
  'Africa/Conakry',
  'Africa/Douala',
  'Africa/Libreville',
  'Africa/Brazzaville',
  'Africa/Kinshasa',
  'Africa/Bangui',
  'Africa/Ndjamena',
  'Africa/Casablanca',
  'Africa/Tunis',
  'Europe/Paris',
  'Europe/Brussels',
  'America/Toronto',
] as const

export const CURRENCIES = ['XOF', 'XAF', 'EUR'] as const

/** « Ce que chaque rôle peut faire » (CLAUDE.md §11): yes, read-only, balances only or no. */
export type Right = 'yes' | 'read' | 'balances' | 'no' | 'noDelete'
export const RIGHTS: {
  key: string
  owner: Right
  planner: Right
  assistant: Right
  accountant: Right
  storekeeper: Right
  team_lead: Right
  staff: Right
}[] = [
  // Field roles (reservations-stock.md §12) reach nothing of this yet: their stock, missions and
  // check-in screens come with the stock (S3) and staff (S7) modules.
  {
    key: 'sales',
    owner: 'yes',
    planner: 'yes',
    assistant: 'noDelete',
    accountant: 'read',
    storekeeper: 'no',
    team_lead: 'no',
    staff: 'no',
  },
  {
    key: 'money',
    owner: 'yes',
    planner: 'balances',
    assistant: 'no',
    accountant: 'yes',
    storekeeper: 'no',
    team_lead: 'no',
    staff: 'no',
  },
  {
    key: 'weddings',
    owner: 'yes',
    planner: 'yes',
    assistant: 'yes',
    accountant: 'read',
    storekeeper: 'no',
    team_lead: 'no',
    staff: 'no',
  },
  {
    key: 'admin',
    owner: 'yes',
    planner: 'no',
    assistant: 'no',
    accountant: 'no',
    storekeeper: 'no',
    team_lead: 'no',
    staff: 'no',
  },
]

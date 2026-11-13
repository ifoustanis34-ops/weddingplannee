import { z } from 'zod'

import { i18n } from '@/i18n'

/** Same rules as the backend (accounts/serializers.py, organizations/services.py). */
const t = (key: string) => i18n.global.t(key)

export const SLUG_PATTERN = /^[a-z0-9](?:[a-z0-9-]{1,30}[a-z0-9])$/

/** Required text; `message` says what to fill in (complement §6: « Indiquez… »). */
const required = (message = t('validation.required')) =>
  z.string({ required_error: message }).trim().min(1, message)

export const emailSchema = z
  .string({ required_error: t('validation.email') })
  .trim()
  .email(t('validation.email'))

export const passwordSchema = z
  .string({ required_error: t('validation.passwordLength') })
  .min(8, t('validation.passwordLength'))
  .refine((value) => !/^\d+$/.test(value), t('validation.passwordNumeric'))

export const loginSchema = z.object({
  email: emailSchema,
  password: z.string({ required_error: t('validation.required') }).min(1, t('validation.required')),
})

export const companyStepSchema = z.object({
  companyName: required(t('validation.companyName')).max(120),
  city: required(t('validation.city')).max(80),
  country: required().length(2),
  weddingsPerYear: z
    .union([z.number().int().min(0).max(1000), z.nan(), z.null(), z.literal('')])
    .optional()
    .transform((value) => (typeof value === 'number' && !Number.isNaN(value) ? value : null)),
})

export const accountStepSchema = z.object({
  fullName: required(t('validation.fullName')).max(120),
  email: emailSchema,
  phone: z.string().trim().max(32).optional().default(''),
  password: passwordSchema,
})

export const spaceStepSchema = z.object({
  slug: required(t('validation.slugShort'))
    .min(3, t('validation.slugShort'))
    .regex(SLUG_PATTERN, t('validation.slug')),
  plan: z.enum(['essentiel', 'pro', 'agence']),
})

/** Whole signup form; each wizard step requires only its own fields. */
export const signupSchema = companyStepSchema.merge(accountStepSchema).merge(spaceStepSchema)
export type SignupForm = z.input<typeof signupSchema>

export const resetSchema = z
  .object({ password: passwordSchema, confirm: z.string() })
  .refine((data) => data.password === data.confirm, {
    message: t('validation.passwordMismatch'),
    path: ['confirm'],
  })

/** Countries offered at sign-up, in the prototype order (complement §6). */
export const COUNTRIES = [
  ['CI', 'Côte d’Ivoire'],
  ['SN', 'Sénégal'],
  ['CM', 'Cameroun'],
  ['BJ', 'Bénin'],
  ['TG', 'Togo'],
  ['BF', 'Burkina Faso'],
  ['ML', 'Mali'],
  ['GA', 'Gabon'],
] as const

/**
 * « Mariages organisés par an » is asked as a range; the lower bound is stored
 * (`weddings_per_year`), which is enough to segment agencies.
 */
export const WEDDING_VOLUMES = [
  { value: 0, key: 'lt10' },
  { value: 10, key: '10to30' },
  { value: 30, key: '30to60' },
  { value: 60, key: 'gt60' },
] as const

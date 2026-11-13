import { chromium } from '@playwright/test'
const [,, out, w, h, theme] = process.argv
const browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_CHROME_PATH })
const page = await browser.newPage({ viewport: { width: +w, height: +h }, colorScheme: theme === 'dark' ? 'dark' : 'light' })
await page.goto('http://localhost:8090/connexion', { waitUntil: 'domcontentloaded', timeout: 90000 })
await page.getByLabel('Email').fill('aicha.kone@maison-elegance.ci')
await page.locator('input[type=password]').fill('Wedivo-demo-2026')
await page.locator('form button[type=submit]').click()
await page.waitForURL('http://localhost:8090/', { timeout: 60000 })
await page.waitForTimeout(4500)
console.log('scrollWidth', await page.evaluate(() => document.documentElement.scrollWidth))
await page.screenshot({ path: out, fullPage: true })
await browser.close()

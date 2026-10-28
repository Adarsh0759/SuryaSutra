import { expect, test } from '@playwright/test'

test('landing page renders and the demo CTA navigates to the app', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { level: 1 })).toContainText('safe action')
  await expect(page.getByRole('heading', { name: 'The problem' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'How it works' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'The safety guarantee' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Results' })).toBeVisible()

  await page.getByRole('link', { name: /Try the demo/ }).click()
  await expect(page.getByRole('heading', { name: 'Alarm queue' })).toBeVisible()
})

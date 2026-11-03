import { expect, test } from '@playwright/test'
import { signIn } from './signIn'

// Full CRUD cycle on /feedback, driven through the real UI against the real backend:
// POST (submit after a real triage run), GET (list), PATCH (edit), DELETE (remove).

test('feedback can be created, listed, edited, and deleted', async ({ page }) => {
  await signIn(page, 'Feedback CRUD Test')

  await page.locator('tbody tr').first().click()
  await page.getByRole('button', { name: 'Run triage' }).click()
  await expect(
    page.getByText(/Safety first/i).or(page.getByText(/Not enough evidence for a safe answer/)),
  ).toBeVisible({ timeout: 30_000 })

  const bodyText = await page.textContent('body')
  test.skip(
    bodyText?.includes('Not enough evidence for a safe answer') ?? false,
    'INSUFFICIENT is a valid, honest outcome (D-06), but this test needs an ANSWERED run to get a run_id to submit feedback against.',
  )

  // Create
  await page.getByRole('button', { name: 'Not fixed' }).click()
  await expect(page.getByText('Marked "Not fixed"')).toBeVisible()

  // Read
  await page.getByRole('tab', { name: 'Feedback' }).click()
  await expect(page.getByText('Not fixed').first()).toBeVisible()

  // Update
  await page.locator('button[aria-label^="Edit feedback"]').first().click()
  await page.locator('select').selectOption('fixed')
  await page.locator('input[type="text"]').fill('Edited by e2e test')
  await page.getByRole('button', { name: 'Save' }).click()
  await expect(page.getByText('Edited by e2e test')).toBeVisible()

  // Delete
  await page.locator('button[aria-label^="Delete feedback"]').first().click()
  await expect(page.getByText('Edited by e2e test')).not.toBeVisible()
})

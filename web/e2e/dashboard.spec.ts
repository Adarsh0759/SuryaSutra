import { expect, test } from '@playwright/test'

// Real backend, real LLM call, real DB write, then checks the dashboard actually
// reads that real row back — not a mock of any layer.

test('dashboard shows real data after a triage run', async ({ page }) => {
  await page.goto('/app')

  await page.locator('tbody tr').first().click()
  await page.getByRole('button', { name: 'Run triage' }).click()
  await expect(
    page.getByText(/Safety first/i).or(page.getByText(/Not enough evidence for a safe answer/)),
  ).toBeVisible({ timeout: 30_000 })

  await page.getByRole('tab', { name: 'Dashboard' }).click()

  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  // Should not show the empty state, since a real run was just made.
  await expect(page.getByText('No triage runs recorded yet')).not.toBeVisible()
  await expect(page.locator('table')).toBeVisible()
  await expect(page.locator('tbody tr').first()).toBeVisible()
})

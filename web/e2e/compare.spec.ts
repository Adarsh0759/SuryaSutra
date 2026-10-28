import { expect, test } from '@playwright/test'

// Drives the real backend with two real Groq calls (one per method) — genuine
// verification of CLAUDE.md §11's compare mode, not a mock.

test('compare mode runs two methods side by side on the same alarm', async ({ page }) => {
  await page.goto('/app')

  await page.locator('tbody tr').first().click()
  await page.getByLabel('Compare mode').check()

  await expect(page.getByRole('heading', { name: /Compare methods/ })).toBeVisible()

  await page.getByRole('button', { name: 'Run compare' }).click()

  // Both method panels should resolve to some status badge (ANSWERED or
  // INSUFFICIENT) within a reasonable time for two sequential-ish LLM calls.
  const badges = page.locator('span', { hasText: /^(ANSWERED|INSUFFICIENT)$/ })
  await expect(badges).toHaveCount(2, { timeout: 40_000 })

  await expect(page.getByRole('heading', { name: 'topk' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'requirement_complete' })).toBeVisible()
})

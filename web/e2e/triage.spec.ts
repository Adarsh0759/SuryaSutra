import { expect, test } from '@playwright/test'

// This drives the real backend, including a real call to the actual Groq model on
// "Run triage" (GROQ_API_KEY must be set in .env) — genuine browser verification of
// CLAUDE.md §11's triage view, not just a type-check or a mocked unit test.

test('alarm queue loads, triage runs, and a citation opens its source', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Alarm queue' })).toBeVisible()

  const firstRow = page.locator('tbody tr').first()
  await expect(firstRow).toBeVisible({ timeout: 10_000 })
  await firstRow.click()

  await expect(page.getByRole('heading', { name: /Triage alarm/ })).toBeVisible()

  await page.getByRole('button', { name: 'Run triage' }).click()

  const safetyOrInsufficient = page
    .getByText(/Safety first/i)
    .or(page.getByText(/Not enough evidence for a safe answer/))
  await expect(safetyOrInsufficient).toBeVisible({ timeout: 30_000 })

  const bodyText = await page.textContent('body')
  if (bodyText?.includes('Not enough evidence for a safe answer')) {
    // A genuinely possible outcome, not a test failure — INSUFFICIENT is a valid,
    // honest answer (D-06). Nothing further to check in this run.
    return
  }

  await expect(page.getByText('Input tokens:')).toBeVisible()

  const firstCitation = page.locator('button', { hasText: /^\[c\d+\]$/ }).first()
  await firstCitation.click()
  const sourcePanelHeading = page.getByRole('heading', { name: /^\[c\d+\]/ })
  await expect(sourcePanelHeading).toBeVisible()

  await page.getByRole('button', { name: 'Close' }).click()
  await expect(sourcePanelHeading).not.toBeVisible()
})

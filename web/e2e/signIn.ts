import type { Page } from '@playwright/test'

/** Shared helper: /app is gated by SignInGate (identification, not auth — see
 * useIdentity.ts). Every e2e test that reaches /app needs to sign in first. */
export async function signIn(page: Page, name = 'E2E Test') {
  await page.goto('/app')
  await page.getByPlaceholder('e.g. Ravi Kumar').fill(name)
  await page.getByRole('button', { name: 'Sign in' }).click()
}

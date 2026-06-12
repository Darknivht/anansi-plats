import { test, expect } from '@playwright/test';

test.describe('Marketplace', () => {
  test('should show marketplace browse page', async ({ page }) => {
    await page.goto('/app/marketplace');
    await expect(page.getByText(/marketplace/i).first()).toBeVisible();
  });

  test('should show billing page with plans', async ({ page }) => {
    await page.goto('/app/billing');
    await expect(page.getByText(/plan/i).first()).toBeVisible();
  });

  test('should show settings page', async ({ page }) => {
    await page.goto('/app/settings');
    await expect(page.getByText(/settings/i).first()).toBeVisible();
  });
});

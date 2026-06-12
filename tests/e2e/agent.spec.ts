import { test, expect } from '@playwright/test';

test.describe('Agent Workshop', () => {
  test('should show agent library page', async ({ page }) => {
    await page.goto('/app/agents');
    await expect(page.getByText(/agents/i).first()).toBeVisible();
  });

  test('should show create agent page with templates', async ({ page }) => {
    await page.goto('/app/agents/new');
    await expect(page.getByText(/template/i).first()).toBeVisible();
  });

  test('should navigate to integration hub', async ({ page }) => {
    await page.goto('/app/integrations');
    await expect(page.getByText(/integration/i).first()).toBeVisible();
  });
});

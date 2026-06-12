import { test, expect } from '@playwright/test';

test.describe('Second Brain', () => {
  test('should show brain overview page', async ({ page }) => {
    await page.goto('/app/brain');
    await expect(page.getByText(/brain/i).first()).toBeVisible();
  });

  test('should show memory library', async ({ page }) => {
    await page.goto('/app/brain/nodes');
    await expect(page.getByText(/memory/i).first()).toBeVisible();
  });

  test('should show daily notes', async ({ page }) => {
    await page.goto('/app/brain/daily');
    await expect(page.getByText(/daily/i).first()).toBeVisible();
  });

  test('should show spaced repetition review page', async ({ page }) => {
    await page.goto('/app/brain/review');
    await expect(page.getByText(/review/i).first()).toBeVisible();
  });

  test('should show graph view', async ({ page }) => {
    await page.goto('/app/brain/graph');
    await expect(page.getByText(/graph/i).first()).toBeVisible();
  });
});

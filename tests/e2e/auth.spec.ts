import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('should show login page', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible();
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
  });

  test('should show signup page', async ({ page }) => {
    await page.goto('/signup');
    await expect(page.getByRole('heading', { name: /create account/i })).toBeVisible();
  });

  test('should show forgot password page', async ({ page }) => {
    await page.goto('/forgot-password');
    await expect(page.getByText(/reset/i)).toBeVisible();
  });

  test('should show landing page with hero section', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText(/your ai.*your life.*your os/i)).toBeVisible();
  });

  test('should show pricing section on landing page', async ({ page }) => {
    await page.goto('/');
    await page.getByText(/free.*pro.*business/i).first().waitFor();
    await expect(page.getByText(/free/i).first()).toBeVisible();
  });
});

test.describe('Navigation', () => {
  test('should navigate from landing to login', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: /sign in/i }).first().click();
    await expect(page).toHaveURL(/\/login/);
  });
});

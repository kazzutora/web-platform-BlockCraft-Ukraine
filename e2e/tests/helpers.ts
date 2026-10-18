import { type Page, expect } from "@playwright/test";

/** A player created by `manage.py seed` (trusted: publishes without moderation). */
export const DEMO_PLAYER = {
  email: "kozak_craft@demo.blockcraft.test",
  password: "Creeper-Aww-Man-2026",
};

export async function signIn(page: Page, { email, password } = DEMO_PLAYER) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Пароль").fill(password);
  await page.getByRole("button", { name: "Увійти" }).click();
  await expect(page).toHaveURL(/\/$|\/welcome/);
}

/** Unique enough for names in a shared database. */
export function stamp(): string {
  return Date.now().toString(36).slice(-6);
}

import { type Page, expect } from "@playwright/test";

export const BASE_URL = process.env.BASE_URL ?? "http://localhost:8080";

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

/** «Моя гра» of a guest: the `bc_game` cookie the GameChip sets. */
export async function setGame(page: Page, gameVersion: string, loader: string) {
  await page.context().addCookies([
    { name: "bc_game", value: encodeURIComponent(`${gameVersion}:${loader}`), url: BASE_URL },
  ]);
}

/** Unique enough for names in a shared database. */
export function stamp(): string {
  return Date.now().toString(36).slice(-6);
}

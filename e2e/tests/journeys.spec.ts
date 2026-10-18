import path from "node:path";

import { expect, test } from "@playwright/test";

import { signIn, stamp } from "./helpers";

test("sign up → onboarding → save a mod → new collection", async ({ page }) => {
  const id = stamp();
  await page.goto("/register");
  await page.getByLabel("Email").fill(`e2e_${id}@example.com`);
  await page.getByLabel("Нік", { exact: true }).fill(`e2e_${id}`);
  await page.getByLabel("Пароль").fill("Creeper-Aww-Man-2026");
  await page.getByRole("button", { name: "Створити акаунт" }).click();

  await expect(page).toHaveURL(/\/welcome/);
  await page.getByText("Java", { exact: true }).click();
  await page.getByLabel("Версія гри").selectOption({ index: 1 });
  await page.getByText("Fabric", { exact: true }).click();
  await page.getByRole("button", { name: "Готово" }).click();
  await expect(page).not.toHaveURL(/\/welcome/);

  await page.goto("/mods?all=1");
  await page.locator("main article a").first().click();
  await expect(page).toHaveURL(/\/mods\/[\w-]+$/);
  const save = page.locator("main").getByRole("button", { name: "Зберегти" }).first();
  await save.click();
  await expect(save).toHaveAttribute("aria-pressed", "true");

  await page.getByRole("button", { name: "В колекцію" }).click();
  const popover = page.getByRole("dialog", { name: "Додати в колекцію" });
  await popover.getByLabel("Нова колекція").fill("Мій перший сетап");
  await popover.getByRole("button", { name: "Створити" }).click();
  await expect(page.getByText("Додано в «Мій перший сетап»").first()).toBeVisible();

  await page.goto("/me/collections");
  await expect(page.getByRole("link", { name: "Мій перший сетап" })).toBeVisible();
});

test("upload a skin and see it in 3D", async ({ page }) => {
  await signIn(page);
  await page.goto("/skins/new");
  await page.locator('input[type="file"]').setInputFiles(path.join(import.meta.dirname, "..", "fixtures", "skin.png"));
  await expect(page.getByRole("img", { name: /3D-модель/ })).toBeVisible();
  await expect(page.getByRole("radio", { name: "Тонкі руки" })).toBeChecked();
  const title = `E2E скін ${stamp()}`;
  await page.getByLabel("Назва").fill(title);
  await page.getByRole("button", { name: "Опублікувати" }).click();

  await expect(page).toHaveURL(/\/skins\/\d+$/);
  await expect(page.getByRole("heading", { name: title })).toBeVisible();
  await expect(page.getByRole("link", { name: "Завантажити PNG" })).toBeVisible();
});

test("add a server", async ({ page }) => {
  await signIn(page);
  await page.goto("/servers/new");
  const name = `E2E сервер ${stamp()}`;
  await page.getByLabel("Назва").fill(name);
  await page.getByLabel("Адреса").fill(`play-${stamp()}.e2e.blockcraft.test`);
  await page.locator("form").getByText("Виживання", { exact: true }).click();
  await page.getByRole("button", { name: "Додати сервер" }).click();

  await expect(page).toHaveURL(/\/servers\/[\w-]+$/);
  await expect(page.getByRole("heading", { name })).toBeVisible();
  await expect(page.getByRole("button", { name: "Скопіювати IP" })).toBeVisible();
});

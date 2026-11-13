import { readFile } from "node:fs/promises";

import { expect, test } from "@playwright/test";

import { BASE_URL, setGame, signIn, stamp } from "./helpers";

/**
 * The scenarios of product.md (С1–С5) and R8.5, against a running stack with real synced
 * data (`sync --source modrinth`, `sync --source mineskin`) and `manage.py seed`.
 */

test.beforeEach(async ({ page }) => {
  await setGame(page, "1.21.1", "fabric");
});

test("С1: a shader comes with its engine — «Що встановити» adds Iris", async ({
  page,
  request,
}) => {
  await page.goto("/mods?type=shader");
  await page.locator("main article a").first().click();
  await expect(page).toHaveURL(/\/mods\/[\w-]+$/);

  const install = page.getByRole("region", { name: "Що встановити" });
  await expect(install).toBeVisible();
  await expect(install.getByText(/додано: шейдерам на Fabric потрібен цей мод/)).toBeVisible();
  await expect(install.getByRole("link", { name: "Iris Shaders", exact: true })).toBeVisible();
  // Files come from Modrinth's CDN, not from us: our link records «Взяв» and redirects there
  const file = install.getByRole("link", { name: /^Завантажити Iris Shaders/ });
  const response = await request.get((await file.getAttribute("href")) ?? "", {
    maxRedirects: 0,
  });
  expect(response.status()).toBe(302);
  expect(response.headers().location).toMatch(/^https:\/\/cdn\.modrinth\.com\//);
});

test("С2: a friend without an account downloads a pack as .mrpack", async ({ page }) => {
  await page.goto("/packs?origin=community&all=1");
  await page.locator("main article a").first().click();
  await expect(page).toHaveURL(/\/packs\/[\w-]+$/);

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "Завантажити .mrpack", exact: true }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/\.mrpack$/);
  const bytes = await readFile(await download.path());
  // A zip archive with the index a launcher imports
  expect(bytes.subarray(0, 2).toString()).toBe("PK");
  expect(bytes.includes(Buffer.from("modrinth.index.json"))).toBe(true);
});

test("С2: a pack for a goal is picked and saved as a draft", async ({ page }) => {
  await signIn(page);
  await page.goto("/help/goal?goals=fps");

  await expect(page.getByRole("heading", { name: "Що підібрали" })).toBeVisible();
  await expect(page.getByText("Рушій рендерингу", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Зберегти як збірку" }).click();
  await expect(page).toHaveURL(/\/packs\/[\w-]+\/edit$/);
});

test("С3: /import recognizes mods by their hashes", async ({ page, request }) => {
  // The jar is not a real Sodium file: the hash lookup is answered as Modrinth would
  const versions = await (
    await request.get("/api/v1/mods/sodium/versions?game_version=1.21.1&loader=fabric")
  ).json();
  const version = versions.recommended;
  await page.route("**/api/v1/compat/identify", async (route) => {
    const body = route.request().postDataJSON() as { files: { hash: string; name: string }[] };
    await route.fulfill({
      json: {
        known: body.files.map((file) => ({
          hash: file.hash,
          name: file.name,
          project: {
            slug: "sodium",
            title: "Sodium",
            icon_url: "",
            project_type: "mod",
            hidden: false,
          },
          version: {
            id: version.id,
            version_number: version.version_number,
            version_type: version.version_type,
            file_name: version.file_name,
            file_size: version.file_size,
          },
          game_versions: version.game_versions,
          loaders: version.loaders,
        })),
        unknown: [],
        guess: { game_version: "1.21.1", loader: "fabric" },
        fitting: 1,
        identified: 1,
        source_unavailable: false,
      },
    });
  });

  await page.goto("/import");
  await page
    .locator('input[type="file"][accept=".jar,.zip,.mrpack"]')
    .setInputFiles({ name: "sodium.jar", mimeType: "application/java-archive", buffer: Buffer.from(`e2e ${stamp()}`) });

  await expect(page.getByText("Впізнали")).toBeVisible();
  await expect(page.getByText("Схоже, це 1.21.1 · Fabric")).toBeVisible();
  await expect(page.getByText("Sodium").first()).toBeVisible();
});

test("С4: a server says what it takes to join", async ({ page }) => {
  await page.goto("/servers?all=1");
  await page.locator('main a[href^="/servers/"]:not([href="/servers/add"])').first().click();
  await expect(page).toHaveURL(/\/servers\/[\w.-]+$/);

  await expect(page.getByRole("heading", { name: "Щоб зайти" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Скопіювати IP" }).first()).toBeVisible();
});

test("С5: a skin in 3D with a PNG to take", async ({ page, request }) => {
  await page.goto("/skins");
  await page.locator("main article a").first().click();
  await expect(page).toHaveURL(/\/skins\/\d+$/);

  const png = page.getByRole("link", { name: "Завантажити PNG" });
  await expect(png).toBeVisible();
  await expect(page.getByRole("tab", { name: "Як поставити" })).toBeVisible();
  const file = await request.get((await png.getAttribute("href")) ?? "", { maxRedirects: 0 });
  expect([200, 302]).toContain(file.status());
});

test("R8.5: a crash log names what is missing", async ({ page }) => {
  // Lines of a real Fabric log (github.com/enjarai/a-good-place/issues/34)
  const log = [
    "[14:07:37] [main/INFO]: Loading Minecraft 26.1 with Fabric Loader 0.19.2",
    "[14:07:37] [main/ERROR]: Incompatible mods found!",
    "\t - Mod 'A Good Place' (a_good_place) 26.1-1.3.1 requires any version of fabric, which is missing!",
  ].join("\n");

  await page.goto("/help/crash");
  await page.getByLabel("Лог гри").fill(log);
  await page.getByRole("button", { name: "Знайти причину" }).click();

  await expect(page.getByText(/потребує Fabric API, а його не встановлено/)).toBeVisible();
  await expect(page.getByRole("link", { name: "Взяти Fabric API" })).toBeVisible();
});

test("sign up → «Моя гра» → save a mod", async ({ page }) => {
  const id = stamp();
  await page.goto("/register");
  await page.getByLabel("Email").fill(`e2e_${id}@example.com`);
  await page.getByLabel("Нік", { exact: true }).fill(`e2e_${id}`);
  await page.getByLabel("Пароль").fill("Creeper-Aww-Man-2026");
  await page.getByRole("button", { name: "Створити акаунт" }).click();
  await expect(page).toHaveURL(/\/welcome/);

  await page.goto(`${BASE_URL}/mods/sodium`);
  const save = page.locator("main").getByRole("button", { name: "Зберегти" }).first();
  await save.click();
  await expect(save).toHaveAttribute("aria-pressed", "true");
});

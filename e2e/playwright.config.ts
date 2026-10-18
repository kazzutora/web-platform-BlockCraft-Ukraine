import { defineConfig, devices } from "@playwright/test";

/**
 * Key journeys against a running stack (docker compose + `manage.py seed`).
 * BASE_URL defaults to the local Nginx; the stack must allow sign-up without email
 * confirmation (ACCOUNT_EMAIL_VERIFICATION=none).
 */
export default defineConfig({
  testDir: "./tests",
  globalSetup: "./tunnel.ts",
  // The journeys share one database: run them one after another
  workers: 1,
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: process.env.BASE_URL ?? "http://localhost:8080",
    locale: "uk-UA",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});

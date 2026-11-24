import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  fullyParallel: false,
  outputDir: process.env.CINEMA_E2E_OUTPUT,
  use: {
    baseURL: process.env.CINEMA_E2E_ORIGIN,
    launchOptions: { executablePath: process.env.CINEMA_BROWSER || undefined },
    headless: true,
  },
});

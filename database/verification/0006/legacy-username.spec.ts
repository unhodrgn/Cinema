import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";

test("legacy registration rejects edge spaces and signs in with a normalized email ID", async ({ page }) => {
  const testPassword = randomUUID();
  await page.goto("/register.html");
  await expect(page.locator("#register-form")).toBeVisible();
  const username = page.getByLabel("Account ID");
  const password = page.getByLabel("Password", { exact: true });
  await username.fill("  Legacy+demo@example.test");
  await password.fill(testPassword);
  await page.getByRole("button", { name: "Register", exact: true }).click();
  await expect(username).toHaveAttribute("aria-invalid", "true");
  await username.fill("Ｌｅｇａｃｙ+demo@example.test");
  const result = page.waitForResponse(response => response.url().endsWith("/api/auth/register"));
  await page.getByRole("button", { name: "Register", exact: true }).click();
  const response = await result;
  expect(response.status()).toBe(201);
  await expect(page).toHaveURL(/registered=1/);
  await page.getByLabel("Account ID").fill("legacy+demo@example.test");
  await page.getByLabel("Password", { exact: true }).fill(testPassword);
  const resultLogin = page.waitForResponse(response => response.url().endsWith("/api/auth/login"));
  await page.locator("#login-form button[type=submit]").click();
  expect((await resultLogin).status()).toBe(200);
});


test("the browser can type and log in with 60 supplementary-plane letters", async ({ page }) => {
  const account = "𐐀".repeat(60);
  const testPassword = randomUUID();
  await page.goto("/register.html");
  await page.getByLabel("Account ID").fill(account);
  await page.getByLabel("Password", { exact: true }).fill(testPassword);
  await page.getByRole("button", { name: "Register", exact: true }).click();
  await expect(page).toHaveURL(/registered=1/);
  const name = page.getByLabel("Account ID");
  await name.pressSequentially(account);
  await expect(name).toHaveValue(account);
  await page.getByLabel("Password", { exact: true }).fill(testPassword);
  const loggedIn = page.waitForResponse(response => response.url().endsWith("/api/auth/login"));
  await page.getByRole("button", { name: /log in/i, exact: true }).click();
  expect((await loggedIn).status()).toBe(200);
});

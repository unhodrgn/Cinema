import { expect, test, type Page } from "@playwright/test";

// The Python harness owns a newly seeded DB, a private API and a static server.
test.beforeEach(() => {
  expect(process.env.CINEMA_E2E_ORIGIN).toBeTruthy();
});

async function login(page: Page, username: string, password: string) {
  await expect(page).toHaveURL(/\/login\.html/);
  await page.getByLabel("Account ID").fill(username);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Log in", exact: true }).click();
}
test("guest selection survives registration, login, payment, reload and cancellation", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Now Showing" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "All movies" }).click();
  await page.locator(".movie-title a").first().click();
  await expect(
    page.getByRole("heading", { name: "Screenings", exact: true }),
  ).toBeVisible();
  const date = page.getByLabel("Screening date");
  await expect(date).toHaveValue(/\d{4}-\d{2}-\d{2}/);
  const tomorrow = new Date((await date.inputValue()) + "T12:00:00Z");
  tomorrow.setUTCDate(tomorrow.getUTCDate() + 1);
  await date.fill(tomorrow.toISOString().slice(0, 10));
  await page.getByRole("link", { name: "Select Seats" }).first().click();
  const steps = page.getByRole("list", { name: "Booking steps" });
  await expect(steps.locator('[aria-current="step"]')).toHaveText("Seats");
  const first = page.getByRole("button", { name: "Seat A1", exact: true });
  await first.click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Proceed to booking" }).click();
  await expect(page).toHaveURL(/login\.html\?next=/);
  await page.locator("main").getByRole("link", { name: "Register" }).click();
  const user = "browser_" + Date.now();
  await page.getByLabel("Account ID").fill(user);
  await page.getByLabel("Password", { exact: true }).fill("test-browser-1234");
  await page.getByRole("button", { name: "Register", exact: true }).click();
  await login(page, user, "test-browser-1234");
  await expect(first).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Proceed to booking" }).click();
  await expect(steps.locator('[aria-current="step"]')).toHaveText("Booking");
  await page.getByRole("button", { name: "Pay Now" }).click();
  await expect(page.getByText(/Payment confirmed for booking/)).toBeVisible();
  await expect(steps.locator('[aria-current="step"]')).toHaveText("Payment");
  await page.reload();
  await expect(page.getByText(/Payment confirmed for booking/)).toBeVisible();
  await page.locator("main").getByRole("link", { name: "My Bookings" }).click();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(page.getByText("CANCELLED", { exact: true })).toBeVisible();
  await expect(page.getByText("PAID", { exact: true })).toBeVisible();
  await page.goto("/screenings.html");
  await expect(page.getByLabel("Screening date")).toBeVisible();
  expect(errors).toEqual([]);
});

test("the catalog and screening schedule fit desktop and phone layouts", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/movies.html");
  const cards = page.locator(".movie-card");
  await expect(cards.nth(1)).toBeVisible();
  const first = await cards.first().boundingBox();
  const second = await cards.nth(1).boundingBox();
  expect(second!.x).toBeGreaterThan(first!.x);
  expect(second!.y).toBe(first!.y);

  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto("/screenings.html");
  await expect(page.getByLabel("Screening date")).toHaveValue(
    /\d{4}-\d{2}-\d{2}/,
  );
  const row = page.locator(".screening").first();
  const poster = row.locator(".poster");
  await expect(poster).toBeVisible();
  expect((await poster.boundingBox())!.width).toBeLessThan(80);
  expect((await row.boundingBox())!.height).toBeLessThan(200);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(
    320,
  );
});

test("admin manages movies and screenings and inspects bookings", async ({
  page,
}) => {
  await page.goto("/admin-movies.html");
  await login(page, "admin", "admin1234");
  await expect(
    page.getByRole("heading", { name: "Manage Movies" }),
  ).toBeVisible();
  const title = "Browser premiere " + Date.now();
  await page.getByLabel("Title", { exact: true }).fill(title);
  await page.getByLabel("Running time (minutes)").fill("100");
  await page.getByRole("button", { name: "Save Movie" }).click();
  const row = page.getByRole("row").filter({ hasText: title });
  await row.getByRole("button", { name: "Edit" }).click();
  await page.getByLabel("Genre", { exact: true }).fill("Drama");
  await page.getByRole("button", { name: "Save Movie" }).click();
  await expect(row).toContainText("Drama");
  await page.getByRole("link", { name: "Screenings (Admin)" }).click();
  await page
    .getByLabel("Movie", { exact: true })
    .selectOption({ label: title });
  await page.getByLabel("Room", { exact: true }).selectOption({ index: 1 });
  const day = new Date();
  day.setUTCDate(day.getUTCDate() + 50);
  await page
    .getByLabel("Start time")
    .fill(day.toISOString().slice(0, 10) + "T09:00");
  await page.getByLabel("Ticket price").fill("12000");
  await page.getByRole("button", { name: "Save Screening" }).click();
  const show = page.getByRole("row").filter({ hasText: title });
  await show.getByRole("button", { name: "Edit" }).click();
  const room = page.getByLabel("Room", { exact: true });
  const savedRoom = await room.inputValue();
  const filter = page.getByLabel("Filter by movie");
  await filter.selectOption({ label: title });
  await expect(show).toBeVisible();
  expect(savedRoom).not.toBe("");
  await expect(room).toHaveValue(savedRoom);
  await page.getByLabel("Ticket price").fill("13500");
  await page.getByRole("button", { name: "Save Screening" }).click();
  await expect(show).toContainText("13,500");
  const movieFilter = await filter.inputValue();
  const screeningId = (await show.getByRole("cell").first().innerText()).trim();
  const removeScreening = show.getByRole("button", {
    name: "Delete",
    exact: true,
  });
  page.once("dialog", (dialog) => dialog.dismiss());
  await removeScreening.click();
  await expect(show).toBeVisible();
  const screeningConfirmation = page.waitForEvent("dialog");
  const clickRemoveScreening = removeScreening.click();
  const screeningDialog = await screeningConfirmation;
  expect(screeningDialog.message()).toContain(`Delete screening #${screeningId}`);
  await screeningDialog.accept();
  await clickRemoveScreening;
  await expect(
    page.getByText(`Screening #${screeningId} was deleted.`),
  ).toBeVisible();
  await expect(page.getByText("No screenings found.")).toBeVisible();
  await expect(filter).toHaveValue(movieFilter);
  await page.getByRole("link", { name: "All Bookings" }).click();
  await page.getByLabel("Status", { exact: true }).selectOption("CANCELLED");
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expect(
    page.getByRole("heading", { name: "All Bookings" }),
  ).toBeVisible();

  await page.getByRole("link", { name: "Movies (Admin)" }).click();
  const remove = row.getByRole("button", { name: "Delete", exact: true });
  page.once("dialog", (dialog) => dialog.dismiss());
  await remove.click();
  await expect(row).toBeVisible();
  const confirmation = page.waitForEvent("dialog");
  const click = remove.click();
  const dialog = await confirmation;
  expect(dialog.message()).toContain(title);
  await dialog.accept();
  await click;
  await expect(
    page.getByText(`"${title}" was deleted.`, { exact: true }),
  ).toBeVisible();
  await expect(row).toHaveCount(0);
  await page.reload();
  await expect(page.locator("tbody tr").first()).toBeVisible();
  await expect(row).toHaveCount(0);
});

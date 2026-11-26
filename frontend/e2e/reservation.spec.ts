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

test("UI-01: double-clicking Proceed to booking sends only one POST request and shows loading state", async ({
  page,
}) => {
  await page.goto("/screenings.html");
  const date = page.getByLabel("Screening date");
  await expect(date).toHaveValue(/\d{4}-\d{2}-\d{2}/);
  const tomorrow = new Date((await date.inputValue()) + "T12:00:00Z");
  tomorrow.setUTCDate(tomorrow.getUTCDate() + 1);
  await date.fill(tomorrow.toISOString().slice(0, 10));
  await page.getByRole("link", { name: "Select Seats" }).first().click();

  const freeSeat = page.locator("button.seat-btn:not([disabled])").first();
  const seatLabel = await freeSeat.getAttribute("aria-label");
  expect(seatLabel).toBeTruthy();
  await freeSeat.click();
  await page.getByRole("button", { name: "Proceed to booking" }).click();
  await login(page, "customer1", "customer1234");
  await expect(
    page.getByRole("button", { name: seatLabel!, exact: true }),
  ).toHaveAttribute("aria-pressed", "true");

  let postCount = 0;
  await page.route("**/api/bookings", async (route) => {
    if (route.request().method() === "POST") {
      postCount += 1;
      await new Promise((resolve) => setTimeout(resolve, 350));
    }
    await route.continue();
  });

  const confirmBtn = page.getByRole("button", { name: "Proceed to booking" });
  await confirmBtn.dblclick();

  await expect(page.getByRole("button", { name: "Booking…" })).toBeDisabled();
  await expect(page).toHaveURL(/\/booking\.html\?id=\d+/);
  expect(postCount).toBe(1);
});

test("UI-01: keyboard repeat, network-failure retry, and reload/back/forward do not duplicate bookings", async ({
  page,
}) => {
  await page.goto("/screenings.html");
  const date = page.getByLabel("Screening date");
  await expect(date).toHaveValue(/\d{4}-\d{2}-\d{2}/);
  const tomorrow = new Date((await date.inputValue()) + "T12:00:00Z");
  tomorrow.setUTCDate(tomorrow.getUTCDate() + 1);
  await date.fill(tomorrow.toISOString().slice(0, 10));
  await page.getByRole("link", { name: "Select Seats" }).first().click();

  const freeSeat = page.locator("button.seat-btn:not([disabled])").first();
  const seatLabel = await freeSeat.getAttribute("aria-label");
  expect(seatLabel).toBeTruthy();
  await freeSeat.click();
  await page.getByRole("button", { name: "Proceed to booking" }).click();
  await login(page, "customer2", "customer1234");
  const seatBtn = page.getByRole("button", { name: seatLabel!, exact: true });
  await expect(seatBtn).toHaveAttribute("aria-pressed", "true");

  // 1. Network drop on first POST unlocks the button and allows a clean retry
  let postCount = 0;
  await page.route("**/api/bookings", async (route) => {
    if (route.request().method() === "POST") {
      postCount += 1;
      if (postCount === 1) {
        await route.abort("failed");
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
    await route.continue();
  });

  const confirmBtn = page.getByRole("button", { name: "Proceed to booking" });
  await confirmBtn.click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(confirmBtn).toBeEnabled();
  expect(postCount).toBe(1);

  // 2. Rapid keyboard Enter presses send only one additional POST
  await confirmBtn.focus();
  await page.keyboard.press("Enter");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/booking\.html\?id=\d+/);
  expect(postCount).toBe(2);

  // 3. Reload, Back, Forward never replay POST /api/bookings
  const bookingUrl = page.url();
  await page.reload();
  await expect(page).toHaveURL(bookingUrl);
  await page.goBack();
  await expect(page).toHaveURL(/\/seats\.html\?screening_id=/);
  await expect(
    page.getByRole("button", { name: `${seatLabel!} (Occupied)`, exact: true }),
  ).toBeDisabled();
  await page.goForward();
  await expect(page).toHaveURL(bookingUrl);
  expect(postCount).toBe(2);
});

test("SEC-01: stored and reflected XSS payloads render safely as text without executing scripts", async ({
  page,
}) => {
  const dialogs: string[] = [];
  const errors: string[] = [];
  page.on("dialog", async (dialog) => {
    dialogs.push(dialog.message());
    await dialog.dismiss();
  });
  page.on("pageerror", (err) => errors.push(err.message));

  const xssTitle = `<img src=x onerror="window.__xss=1"><script>window.__xss=2</script>_${Date.now()}`;
  const xssUser = `xss_<svg onload=alert(1)>_${Date.now()}`;

  // Reflected XSS / open-redirect URL parameters are neutralized while logged out
  await page.goto("/login.html?next=javascript:alert(1)");
  await expect(page.getByRole("link", { name: "Register" }).first()).toHaveAttribute(
    "href",
    "/register.html",
  );

  // Register customer with XSS-like username
  await page.goto("/register.html");
  await page.getByLabel("Account ID").fill(xssUser);
  await page.getByLabel("Password", { exact: true }).fill("xss-test-1234");
  await page.getByRole("button", { name: "Register", exact: true }).click();
  await expect(page).toHaveURL(/\/login\.html\?registered=1/);

  // Admin creates a movie with XSS payloads in title, genre, rating, synopsis
  await page.goto("/admin-movies.html");
  await login(page, "admin", "admin1234");
  await page.getByLabel("Title", { exact: true }).fill(xssTitle);
  await page.getByLabel("Running time (minutes)").fill("95");
  await page.getByLabel("Genre", { exact: true }).fill("<script>window.__xss=3</script>");
  await page.getByLabel("Synopsis", { exact: true }).fill("<svg onload=\"window.__xss=4\">");
  await page.getByRole("button", { name: "Save Movie" }).click();

  const movieRow = page.getByRole("row").filter({ hasText: xssTitle });
  await expect(movieRow).toBeVisible();

  // Public catalog & detail pages render XSS payloads strictly as plain text
  await page.goto("/movies.html");
  const movieLink = page.getByRole("link", { name: xssTitle });
  await expect(movieLink).toBeVisible();
  await movieLink.click();
  await expect(page.getByRole("heading", { name: xssTitle })).toBeVisible();
  await expect(page.getByText("<svg onload=\"window.__xss=4\">")).toBeVisible();

  for (const target of [
    "/movie.html?id=<script>alert(1)</script>",
    "/seats.html?screening_id=<img src=x onerror=alert(1)>",
    "/screenings.html?date=\"><script>alert(1)</script>",
  ]) {
    await page.goto(target);
  }

  // Log out admin, then log in as XSS-named customer and check nav rendering
  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL(/\/(index\.html)?$/);
  await page.goto("/login.html");
  await login(page, xssUser, "xss-test-1234");
  await expect(page.getByText(`${xssUser} (CUSTOMER)`)).toBeVisible();

  expect(await page.evaluate(() => (window as unknown as { __xss?: unknown }).__xss)).toBeUndefined();
  expect(dialogs).toEqual([]);
  expect(errors).toEqual([]);
});

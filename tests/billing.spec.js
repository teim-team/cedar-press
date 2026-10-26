import { expect, test } from "./fixtures.js";

const summary = {
  available: true, cohort: "early_access", annualPrices: { press: 50000, press_pro: 100000 },
  subscriptions: [], invoices: [], payments: [], refunds: [], hasCustomer: false,
};

async function account(page, billing = summary) {
  await page.route("**/api/me", (route) => route.fulfill({ json: {
    email: "billing@cedar-press.invalid", workspace_tier: "free",
  } }));
  await page.route("**/api/billing", (route) => route.fulfill({ json: billing }));
}

test("unpaid account can choose annual billing and submit a discount", async ({ page }) => {
  await account(page);
  let submitted;
  await page.route("**/api/billing/checkout", async (route) => {
    submitted = route.request().postDataJSON();
    await route.fulfill({ status: 400, json: { code: "DISCOUNT_INVALID", message: "That discount code is not available." } });
  });
  await page.goto("/settings");
  await page.getByLabel("Discount code (optional)").fill("SUMMIT");
  await page.getByRole("button", { name: "Cedar Press: $500.00/year", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText("That discount code is not available.");
  expect(submitted).toEqual({ tier: "press", discount_code: "SUMMIT" });
  await expect(page.getByRole("button", { name: "Cedar Press+: $1,000.00/year", exact: true })).toBeEnabled();
});

test("existing annual subscriber sees management and invoice history", async ({ page }) => {
  await account(page, { ...summary, hasCustomer: true,
    subscriptions: [{ tier: "press_pro", status: "active", cancel_at_period_end: true, period_end: "2027-10-25T12:00:00Z" }],
    invoices: [{ id: "in_fixture", created_at: "2026-10-25T12:00:00Z", currency: "usd", amount_due: 90000, status: "paid", hosted_url: "https://invoice.stripe.com/i/fixture" }],
  });
  await page.goto("/settings");
  await expect(page.getByText(/Access is scheduled to end/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Manage billing and plan" })).toBeVisible();
  await expect(page.getByLabel("Discount code (optional)")).toHaveCount(0);
  await expect(page.getByRole("link", { name: "View invoice", exact: true })).toHaveAttribute("href", "https://invoice.stripe.com/i/fixture");
});

test("billing unavailable preserves the account settings page", async ({ page }) => {
  await account(page, { ...summary, available: false });
  await page.goto("/settings");
  await expect(page.getByText("Online billing is temporarily unavailable.")).toBeVisible();
  await expect(page.getByRole("button", { name: /Refresh billing/ })).toBeVisible();
});

test("annual upgrade uses a hosted confirmation and shows provider errors", async ({ page }) => {
  await account(page, { ...summary, hasCustomer: true,
    subscriptions: [{ tier: "press", status: "active", cancel_at_period_end: false }],
  });
  let calls = 0;
  await page.route("**/api/billing/change-plan", async (route) => {
    calls++;
    expect(route.request().method()).toBe("POST");
    await route.fulfill({ status: 502, json: { code: "STRIPE_UNAVAILABLE", message: "Please try again." } });
  });
  await page.goto("/settings");
  await page.getByRole("button", { name: "Upgrade to Cedar Press+", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText("Please try again.");
  expect(calls).toBe(1);
});

test("new visitor goes straight to Stripe without an email or discount form", async ({ page }) => {
  await page.route("**/api/me", (route) => route.fulfill({ status: 401, json: {} }));
  await page.route("**/api/billing/plans", (route) => route.fulfill({ json: summary }));
  let submitted;
  await page.route("**/api/billing/guest/checkout", (route) => {
    submitted = route.request().postDataJSON();
    return route.fulfill({ json: { url: "https://checkout.stripe.com/c/pay/fixture" } });
  });
  await page.route("https://checkout.stripe.com/c/pay/fixture", route => route.fulfill({ body: "Stripe checkout fixture" }));
  await page.goto("/subscribe");
  await expect(page.getByLabel("Email address")).toHaveCount(0);
  await expect(page.getByLabel("Discount code (optional)")).toHaveCount(0);
  await page.getByRole("button", { name: "Subscribe to Cedar Press", exact: true }).click();
  await expect(page).toHaveURL("https://checkout.stripe.com/c/pay/fixture");
  expect(submitted).toEqual({ tier: "press" });
});

test("guest return waits for email verification without signing in", async ({ page }) => {
  await page.route("**/api/me", (route) => route.fulfill({ status: 401, json: { detail: "Not signed in." } }));
  await page.route("**/api/billing/plans", (route) => route.fulfill({ json: summary }));
  await page.route("**/api/billing/guest/status", (route) => route.fulfill({ json: { status: "complete", email: "guest@example.invalid", emailSent: true } }));
  await page.goto("/subscribe?billing=processing");
  await expect(page.getByRole("status")).toHaveText("We’ve sent your account setup link to");
  await expect(page.locator(".cp-confirm__email")).toHaveText("guest@example.invalid");
  await expect(page.getByRole("heading", { name: "You’re subscribed." })).toBeVisible();
  await expect(page.getByRole("button", { name: "Continue to checkout" })).toHaveCount(0);
});

test("account creation uses its own focused page and keeps the paid email fixed", async ({ page }) => {
  await page.route("**/api/me", (route) => route.fulfill({ status: 401, json: {} }));
  await page.route("**/api/auth/account-setup/check", (route) => route.fulfill({ json: { email: "paid@example.invalid" } }));
  await page.route("**/api/auth/account-setup/confirm", (route) => route.fulfill({ status: 400, json: { code: "ACCOUNT_LINK_INVALID", message: "This account link was already used." } }));
  await page.goto("/create-account#token=synthetic-mailbox-token");
  await expect(page).toHaveURL(/\/create-account$/);
  await expect(page.getByRole("heading", { name: "Create your account." })).toBeVisible();
  await expect(page.getByLabel("Email address")).toHaveValue("paid@example.invalid");
  await expect(page.getByLabel("Email address")).toHaveAttribute("readonly", "");
  await page.getByLabel("Name", { exact: true }).fill("Test Reader");
  await page.getByLabel("Create password", { exact: true }).fill("synthetic-password-123");
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText("This account link was already used.");
  await expect(page.locator(".cp-login__side")).toHaveCount(0);
});

test("membership prices sit beside plan names and select the correct Stripe tier", async ({ page }, testInfo) => {
  if (testInfo.project.name === "desktop") await page.setViewportSize({ width: 1366, height: 768 });
  await page.route("**/api/me", (route) => route.fulfill({ status: 401, json: {} }));
  await page.route("**/api/billing/plans", (route) => route.fulfill({ json: summary }));
  let submitted;
  await page.route("**/api/billing/guest/checkout", (route) => {
    submitted = route.request().postDataJSON();
    return route.fulfill({ status: 502, json: { message: "Synthetic checkout refusal." } });
  });
  await page.goto("/subscribe");
  for (const [name, amount] of [["Cedar Press", "$500"], ["Cedar Press+", "$1,000"]]) {
    const card = page.getByRole("article", { name, exact: true });
    const price = card.locator(".cp-membership__price strong");
    await expect(price).toHaveText(amount);
    const heading = await card.getByRole("heading", { name, exact: true }).boundingBox();
    const priceBox = await price.boundingBox();
    expect(priceBox.x).toBeGreaterThan(heading.x + heading.width);
    if (testInfo.project.name === "desktop") {
      const box = await card.boundingBox();
      expect(box.y + box.height).toBeLessThanOrEqual(768);
      await expect(card.getByRole("button")).toBeInViewport();
      await expect(card.locator(".cp-membership__features li").last()).toBeInViewport();
    }
  }
  await page.getByRole("button", { name: "Subscribe to Cedar Press+", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText("Synthetic checkout refusal.");
  expect(submitted).toEqual({ tier: "press_pro" });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("purchase confirmation resends account email and keeps sign in secondary", async ({ page }) => {
  await page.route("**/api/me", route => route.fulfill({ status: 401, json: {} }));
  await page.route("**/api/billing/plans", route => route.fulfill({ json: summary }));
  const purchase = { status: "complete", email: "guest@example.invalid", emailSent: true, accountSetup: true };
  await page.route("**/api/billing/guest/status", route => route.fulfill({ json: purchase }));
  let sent = 0;
  await page.route("**/api/billing/guest/resend", route => { sent++; return route.fulfill({ json: purchase }); });
  await page.goto("/subscribe?billing=processing");
  await page.getByRole("button", { name: "Resend email", exact: true }).click();
  await expect(page.getByText("Email sent. Please use the newest link.")).toBeVisible();
  expect(sent).toBe(1);
  await expect(page.getByRole("link", { name: "Sign in to Cedar Press", exact: true })).toHaveCount(0);
});

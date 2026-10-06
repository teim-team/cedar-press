// What a reader sees when the connection fails them, and what brings the
// page back. Found by the 2026-10-04 throttled audit (Slow 3G, 4x CPU):
//
// - a sample that failed once stayed failed until a reload, and the viewer
//   reported it as "No matching records in this preview. Widen a filter";
// - a page whose code did not arrive kept its Reload button after the
//   connection came back, and did nothing on its own.
//
// The connected-only half (the API deadline behind the session check, an
// article and the spreadsheet list) runs no browser here, because this suite
// builds standalone; src/features/grove/apiTimeout.test.js holds it.
import { expect, test } from "@playwright/test";

// The sample tables every reader fetches: one customer table per collection.
const SAMPLES = "**/data/cedar/downloads/**";

/** A signed-in Cedar Press+ reader, as the standalone gate stores one. */
async function signedIn(page) {
  await page.addInitScript(() => {
    localStorage.setItem("cedar-press-session", JSON.stringify({ email: "smoke@cedar-press.invalid", workspace_tier: "press_pro" }));
  });
}

test("the door's preview says a failed sample failed, and Retry reads it again", async ({ page }) => {
  await page.route(SAMPLES, (route) => route.abort("internetdisconnected"));
  await page.goto("/");
  const stage = page.getByTestId("collection-stage");
  await expect(stage).toContainText("The sample could not be read");
  const retry = stage.getByRole("button", { name: "Retry" });
  await expect(retry).toBeVisible();

  await page.unroute(SAMPLES);
  await retry.click();
  await expect(stage.locator(".cp-pane__records")).toBeVisible();
  await expect(stage).not.toContainText("The sample could not be read");
});

test("the door's preview reads the sample again when the browser is back online", async ({ page, context }) => {
  await page.route(SAMPLES, (route) => route.abort("internetdisconnected"));
  await page.goto("/");
  const stage = page.getByTestId("collection-stage");
  await expect(stage).toContainText("The sample could not be read");
  await page.unroute(SAMPLES);
  await context.setOffline(true);
  await context.setOffline(false);
  await expect(stage.locator(".cp-pane__records")).toBeVisible();
});

test("the viewer does not call a failed read an empty result", async ({ page }) => {
  await signedIn(page);
  await page.route(SAMPLES, (route) => route.abort("internetdisconnected"));
  await page.goto("/data?c=funding");
  const empty = page.locator(".cp-ex__empty");
  await expect(empty).toContainText("The preview records could not be loaded");
  await expect(empty).not.toContainText("Widen a filter");

  await page.unroute(SAMPLES);
  await empty.getByRole("button", { name: "Retry" }).click();
  await expect(page.getByTestId("explore-record").first()).toBeVisible();
});

test("a page whose code did not arrive offline loads itself when the connection returns", async ({ page, context }) => {
  await signedIn(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Know what");
  await context.setOffline(true);
  // A client-side navigation to a route whose chunk has not been fetched.
  await page.evaluate(() => {
    history.pushState({}, "", "/methods");
    dispatchEvent(new PopStateEvent("popstate"));
  });
  const boundary = page.getByRole("alert").filter({ hasText: "did not load" });
  await expect(boundary).toBeVisible();
  await expect(boundary.getByRole("button", { name: "Reload" })).toBeVisible();

  await context.setOffline(false);
  await expect(boundary).toHaveCount(0);
  await expect(page).toHaveURL(/\/methods$/);
  await expect(page.locator("#cp-main")).toBeVisible();
});

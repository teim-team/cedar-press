import { expect, test } from "@playwright/test";

test("the preview collection rail scrolls to the last dataset on a phone", async ({ page, context }, testInfo) => {
  test.skip(testInfo.project.name !== "phone", "touch navigation");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  const rail = page.getByRole("navigation", { name: "Collections", exact: true });
  await rail.evaluate((el) => el.scrollIntoView({ block: "center", behavior: "instant" }));
  const bounds = await rail.boundingBox();
  expect(bounds.width).toBeLessThanOrEqual(page.viewportSize().width);
  const before = await rail.evaluate((el) => el.scrollLeft);
  const client = await context.newCDPSession(page);
  // Real touch input: assigning scrollLeft can pass even when a user cannot swipe.
  const y = bounds.y + bounds.height / 2;
  await client.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: bounds.x + bounds.width - 24, y }] });
  for (let step = 1; step <= 10; step += 1) {
    await client.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [{ x: bounds.x + bounds.width - 24 - (bounds.width - 48) * step / 10, y }] });
  }
  await client.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  await expect.poll(() => rail.evaluate((el) => el.scrollLeft)).toBeGreaterThan(before + 30);
  // Check the far end too, including the second subscription shelf.
  await rail.evaluate((el) => { el.scrollLeft = el.scrollWidth; });
  const last = rail.locator(".cp-rail__item").last();
  await expect(last).toBeInViewport();
  await last.tap();
  await expect(last).toHaveAttribute("aria-pressed", "true");
  await expect(page).toHaveURL(/collection=/);
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBe(0);
});

test("audience names remain on mobile and disappear beside the desktop illustrations", async ({ page }, testInfo) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  const band = page.locator(".cp-aud");
  await band.scrollIntoViewIfNeeded();
  const tabs = page.getByRole("tablist", { name: "Audiences" });
  if (testInfo.project.name === "phone") await expect(tabs).toBeVisible();
  else {
    await expect(tabs).toBeHidden();
    await expect(band.locator(".cp-aud__panel.is-on .cp-aud__media")).toBeVisible();
  }
  await page.getByRole("button", { name: "Next use case" }).click();
  await expect(band.locator(".cp-aud__count")).toHaveText(/^02 \//);
  await page.getByRole("button", { name: "Previous use case" }).click();
  await expect(band.locator(".cp-aud__count")).toHaveText(/^01 \//);
});

import { expect, test } from "@playwright/test";

async function expectRailSettled(rail, testInfo, phase) {
  const result = await rail.evaluate(async (el) => {
    const samples = [];
    let baseline = null;
    let stableFrames = 0;
    for (let frame = 0; frame < 180; frame += 1) {
      const timestamp = await new Promise(requestAnimationFrame);
      const box = el.getBoundingClientRect();
      const last = el.querySelector(".cp-rail__item:last-child");
      // Select across both shelves, not the last child in the first shelf.
      const items = el.querySelectorAll(".cp-rail__item");
      const target = (items[items.length - 1] ?? last)?.getBoundingClientRect();
      const geometry = [
        el.scrollLeft, el.scrollTop,
        box.x, box.y, box.width, box.height,
        target?.x ?? 0, target?.y ?? 0, target?.width ?? 0, target?.height ?? 0,
      ];
      const unchanged = baseline && geometry.every(
        (value, index) => Math.abs(value - baseline[index]) <= 0.01,
      );
      if (unchanged) stableFrames += 1;
      else {
        baseline = geometry;
        stableFrames = 0;
      }
      samples.push({ timestamp, geometry, stableFrames });
      if (stableFrames >= 8) break;
    }
    const style = getComputedStyle(el);
    return {
      settled: stableFrames >= 8,
      scrollBehavior: style.scrollBehavior,
      scrollSnapType: style.scrollSnapType,
      touchAction: style.touchAction,
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
      samples,
    };
  });
  await testInfo.attach("rail-" + phase + "-geometry.json", {
    body: JSON.stringify(result, null, 2),
    contentType: "application/json",
  });
  expect(result.settled, "Rail and last-button geometry must stop moving: " + phase).toBe(true);
}

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
  // Dispatch actual touch events on rendered frames. Ease the finger to a
  // stop, then measure completed scrolling and snapping before the next tap.
  // Headless touch emulation does not reliably emit native scrollend here.
  const y = bounds.y + bounds.height / 2;
  const startX = bounds.x + bounds.width - 24;
  expect(await rail.evaluate((el, point) => el.contains(
    document.elementFromPoint(point.x, point.y),
  ), { x: startX, y })).toBe(true);
  await client.send("Input.dispatchTouchEvent", {
    type: "touchStart", touchPoints: [{ x: startX, y }],
  });
  try {
    for (let step = 1; step <= 10; step += 1) {
      await page.evaluate(() => new Promise(requestAnimationFrame));
      await client.send("Input.dispatchTouchEvent", {
        type: "touchMove",
        touchPoints: [{ x: startX - (bounds.width - 48) * (1 - (1 - step / 10) ** 3), y }],
      });
    }
  } finally {
    await client.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  }
  await expect.poll(() => rail.evaluate((el) => el.scrollLeft)).toBeGreaterThan(before + 30);
  await expectRailSettled(rail, testInfo, "swipe");
  // Check the far end too, including the second subscription shelf.
  await rail.evaluate((el) => { el.scrollLeft = el.scrollWidth; });
  const last = rail.locator(".cp-rail__item").last();
  await last.scrollIntoViewIfNeeded();
  await expectRailSettled(rail, testInfo, "last-collection");
  await expect(last).toBeInViewport({ ratio: 1 });
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

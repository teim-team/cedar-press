// Keyboard, screen reader and phone-width behaviour found by the 2026-10-04
// accessibility pass (axe-core 4.13 plus keyboard walks, at 375 and 1280 px).
// Each test names the defect it holds closed; each was checked by breaking
// the fix and watching the test fail.
import { expect, test } from "@playwright/test";

const SAMPLES = "**/data/cedar/samples/**";

/** A signed-in Cedar Press+ reader, as the standalone gate stores one. */
async function signedIn(page) {
  await page.addInitScript(() => {
    localStorage.setItem("cedar-press-session", JSON.stringify({ email: "smoke@cedar-press.invalid", workspace_tier: "press_pro" }));
  });
}

/** Wait for a focus move scheduled on the next animation frame. */
async function focused(page) {
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  return page.evaluateHandle(() => document.activeElement);
}

async function isFocused(locator) {
  return locator.evaluate((el) => el === document.activeElement);
}

test.describe("panels hand focus back", () => {
  test("the collection profile holds Tab and returns focus to what opened it", async ({ page }) => {
    await signedIn(page);
    await page.goto("/data?c=funding");
    const opener = page.locator(".cp-ex__aboutbtn");
    await opener.focus();
    await page.keyboard.press("Enter");
    const sheet = page.getByRole("dialog", { name: /^About / });
    await expect(sheet).toBeVisible();
    await expect(sheet).toHaveAttribute("aria-modal", "true");
    await expect(sheet.locator(".cp-ab__close")).toBeFocused();

    // Off the end and off the start, it wraps rather than leaving the sheet.
    const stops = await sheet.evaluate((el) => [...el.querySelectorAll("a[href], button, summary")].filter((n) => n.getClientRects().length).length);
    for (let i = 0; i < stops + 2; i += 1) {
      await page.keyboard.press("Tab");
      expect(await page.evaluate(() => !!document.activeElement.closest(".cp-ab")), "Tab stop " + i + " stays in the sheet").toBe(true);
    }
    await sheet.locator(".cp-ab__close").focus();
    await page.keyboard.press("Shift+Tab");
    expect(await page.evaluate(() => !!document.activeElement.closest(".cp-ab"))).toBe(true);

    await page.keyboard.press("Escape");
    await expect(sheet).toHaveCount(0);
    await focused(page);
    expect(await isFocused(opener)).toBe(true);
  });

  test("the door's Cedar returns focus to the button that opened it", async ({ page }) => {
    await page.goto("/");
    const opener = page.locator(".cp-pane__act--btn").first();
    await opener.focus();
    await page.keyboard.press("Enter");
    const panel = page.getByRole("dialog", { name: "Ask Cedar" });
    await expect(panel).toBeVisible();
    await expect(panel.locator("input, textarea").first()).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(panel).toHaveCount(0);
    await focused(page);
    expect(await isFocused(opener)).toBe(true);
  });

  test("signed in, Cedar takes focus when it opens and gives it back when it closes", async ({ page }, testInfo) => {
    await signedIn(page);
    await page.goto("/");
    const launcher = page.locator(".cedar-widget__launcher");
    await launcher.focus();
    await page.keyboard.press("Enter");
    const panel = page.getByRole("dialog", { name: "Ask Cedar" });
    await expect(panel).toBeVisible();
    // Standalone, the composer is disabled, so focus lands on the close
    // button. On a phone the launcher is hidden while the panel is open, so
    // without this focus fell to <body>.
    await focused(page);
    expect(await page.evaluate(() => !!document.activeElement.closest('[role="dialog"]')), testInfo.project.name + ": focus is inside Cedar").toBe(true);
    await page.keyboard.press("Escape");
    await expect(panel).toHaveCount(0);
    await focused(page);
    expect(await isFocused(launcher)).toBe(true);
  });
});

test.describe("menus over the table", () => {
  for (const name of ["Filters", "More actions"]) {
    test(`${name} closes on Escape and on a click elsewhere`, async ({ page }) => {
      await signedIn(page);
      await page.goto("/data?c=funding");
      const details = page.locator(name === "Filters" ? ".cp-ex__filters" : ".cp-ex__bar .cp-ex__more");
      const summary = details.locator("> summary");
      await summary.focus();
      await page.keyboard.press("Enter");
      await expect(details).toHaveAttribute("open", "");
      await page.keyboard.press("Tab");
      await page.keyboard.press("Escape");
      await expect(details).not.toHaveAttribute("open", "");
      await expect(summary).toBeFocused();

      await summary.click();
      await expect(details).toHaveAttribute("open", "");
      await page.locator(".cp-ex__title, h1").first().click();
      await expect(details).not.toHaveAttribute("open", "");
    });
  }

  test("on a phone the Filters panel and the Sections menu stay on screen", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "phone", "the narrow layout");
    await signedIn(page);
    await page.goto("/data?c=funding");
    const width = page.viewportSize().width;

    await page.locator(".cp-ex__filters > summary").click();
    const panel = await page.locator(".cp-ex__filtersin").boundingBox();
    expect(panel.x, "Filters panel left edge").toBeGreaterThanOrEqual(0);
    expect(panel.x + panel.width, "Filters panel right edge").toBeLessThanOrEqual(width);
    await page.keyboard.press("Escape");

    await page.locator(".cp-navm > summary").click();
    const menu = await page.locator(".cp-navm__menu").boundingBox();
    expect(menu.x).toBeGreaterThanOrEqual(0);
    expect(menu.x + menu.width, "Sections menu right edge").toBeLessThanOrEqual(width);
  });
});

test.describe("headings and announcements", () => {
  test("the door's collection name is a level-two heading under the page's one", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("collection-stage").getByRole("heading", { level: 2 }).first()).toBeVisible();
    await expect(page.getByTestId("collection-stage").getByRole("heading", { level: 3 })).toHaveCount(0);
  });

  test("the priorities lists sit under level-two headings", async ({ page }) => {
    await signedIn(page);
    await page.goto("/priorities");
    for (const type of ["research_question", "dataset"]) {
      await expect(page.getByTestId(`priorities-${type}`).getByRole("heading", { level: 2 })).toHaveCount(1);
    }
  });

  test("an article that is not available still has a page heading", async ({ page }) => {
    await signedIn(page);
    await page.goto("/articles/brief-owned");
    await expect(page.getByRole("status")).toContainText("Articles are unavailable");
    await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
  });

  test("a failed sample read is announced by the live region that said it was loading", async ({ page }) => {
    let release;
    const held = new Promise((resolve) => { release = resolve; });
    await page.route(SAMPLES, async (route) => { await held; await route.abort("internetdisconnected"); });
    await page.goto("/");
    const stage = page.getByTestId("collection-stage");
    const region = stage.getByRole("status");
    await expect(region).toContainText("Reading the sample");
    const before = await region.elementHandle();
    release();
    await expect(region).toContainText("could not be loaded");
    expect(await before.evaluate((el) => el.isConnected && el.textContent.includes("could not be loaded")), "the same element carries the failure").toBe(true);
  });

  test("the viewer's failed read is announced", async ({ page }) => {
    await signedIn(page);
    await page.route(SAMPLES, (route) => route.abort("internetdisconnected"));
    await page.goto("/data?c=funding");
    await expect(page.locator('.cp-ex__empty[role="status"]')).toContainText("could not be loaded");
  });
});

test.describe("contrast and targets", () => {
  test("the rail's observation counts clear 4.5:1 on the navy rail", async ({ page }) => {
    await signedIn(page);
    await page.goto("/data?c=funding");
    await expect(page.locator(".cp-rail__rows").first()).toBeVisible();
    const ratios = await page.locator(".cp-rail__rows").evaluateAll((nodes) => {
      const parse = (value) => value.match(/[\d.]+/g).map(Number);
      const lum = ([r, g, b]) => {
        const ch = (v) => { const c = v / 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
        return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b);
      };
      const blend = (top, under) => {
        const a = top[3] ?? 1;
        return [0, 1, 2].map((i) => top[i] * a + under[i] * (1 - a));
      };
      // The opaque ground behind a node, compositing translucent fills on the way down.
      const ground = (node) => {
        const layers = [];
        for (let el = node; el; el = el.parentElement) {
          const bg = parse(getComputedStyle(el).backgroundColor);
          if ((bg[3] ?? 1) > 0) layers.push(bg);
          if ((bg[3] ?? 1) === 1) break;
        }
        return layers.reverse().reduce((under, top) => blend(top, under), [255, 255, 255]);
      };
      return nodes.filter((n) => n.getClientRects().length).map((n) => {
        const bg = ground(n);
        const fg = blend(parse(getComputedStyle(n).color), bg);
        const [hi, lo] = [lum(fg), lum(bg)].sort((a, b) => b - a);
        return (hi + 0.05) / (lo + 0.05);
      });
    });
    expect(ratios.length).toBeGreaterThan(0);
    for (const ratio of ratios) expect(ratio).toBeGreaterThanOrEqual(4.5);
  });

  test("the footer's tribal-government link is at least 24px tall", async ({ page }) => {
    await signedIn(page);
    await page.goto("/settings");
    const box = await page.locator(".cp-foot__gov a").first().boundingBox();
    expect(box.height).toBeGreaterThanOrEqual(24);
  });
});

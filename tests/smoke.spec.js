// Smoke: the paths a subscriber actually takes.
//
// The unit tests under src/features/grove cover the catalogue's arithmetic
// and the API tests cover every route. Neither of them opens the page, and
// the regressions that have reached this branch got through both: an export
// renamed on one side of an import, which the bundler shipped and which
// broke sign-in silently; a stylesheet truncated mid-file, which left the
// section grid as a stack of full-width blocks; a `position: fixed` panel
// laid out against the page box instead of the window. These are the checks
// that would have caught them.
//
// What belongs here is the short list of things whose failure means the site
// is broken for everyone: the gate, sign-in, the overview and its sections,
// a download, and sign-out. Anything narrower belongs in a unit test.
import { expect, test } from "@playwright/test";

const ACCOUNT = { email: "press@cedarpress.ai", password: "cedar-demo-2026" };

/** The pages behind the gate, by the route a reader reaches them at. */
const SECTIONS = [
  { name: "Articles", path: "/articles" },
  { name: "Collections", path: "/data" },
  { name: "What's new", path: "/whats-new" },
  { name: "Methods", path: "/methods" },
  { name: "Settings", path: "/settings" },
];

/**
 * Fail the test on anything the browser logged as an error.
 *
 * A page that renders and throws is not a page that works, and a thrown
 * render leaves React showing the last good tree — which looks correct in a
 * screenshot. Collected per test and asserted at the end, so the failure
 * names the console text rather than reporting a timeout somewhere else.
 */
function watchConsole(page) {
  const errors = [];
  page.on("pageerror", (error) => errors.push(String(error)));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  return errors;
}

/** Sign in through the gate, the way a subscriber does. */
async function signIn(page) {
  await page.goto("/");
  await page.getByRole("tab", { name: "Log in" }).click();
  await page.getByLabel("Email address").fill(ACCOUNT.email);
  await page.getByLabel("Password", { exact: true }).fill(ACCOUNT.password);
  await page.locator(".cp-gate__form").getByRole("button", { name: "Log in" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Know what’s shaping Indian Country",
  );
}

test.describe("the gate", () => {
  test("a signed-out visitor gets the gate, not the reader", async ({ page }) => {
    const errors = watchConsole(page);
    await page.goto("/");
    await expect(page.locator(".cp-split")).toBeVisible();
    // Asserted as the absence of the catalogue rather than the presence of
    // the gate: a gate painted over a rendered reader is not access control.
    await expect(page.locator("#catalog")).toHaveCount(0);
    expect(errors).toEqual([]);
  });

  test("a wrong password is refused and says so", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("tab", { name: "Log in" }).click();
    await page.getByLabel("Email address").fill(ACCOUNT.email);
    await page.getByLabel("Password", { exact: true }).fill("not-the-password");
    await page.locator(".cp-gate__form").getByRole("button", { name: "Log in" }).click();
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page.locator(".cp-split")).toBeVisible();
  });

  test("a deep link while signed out lands on the gate", async ({ page }) => {
    // Also a static-hosting check. These routes resolve only because the
    // build copies index.html to 404.html; served from dist without that,
    // this is the host's 404 rather than the app.
    await page.goto("/data");
    await expect(page.locator(".cp-split")).toBeVisible();
  });
});

test.describe("the subscriber's path", () => {
  test("sign in, read the overview, sign out", async ({ page }) => {
    const errors = watchConsole(page);
    await signIn(page);

    // Six tiles, each a real destination. The count is asserted because the
    // layout is built on it: they wrapped as five and one once, orphaning
    // Contact on a row of its own.
    await expect(page.locator(".cp-hub__tile")).toHaveCount(6);
    await expect(page.locator(".cp-close__head")).toContainText("Nothing here is a snapshot");

    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page.locator(".cp-split")).toBeVisible();
    expect(errors).toEqual([]);
  });

  for (const section of SECTIONS) {
    test(`${section.name} renders for a subscriber`, async ({ page }) => {
      const errors = watchConsole(page);
      await signIn(page);
      await page.goto(section.path);
      // These render behind an entitlement check, and the failure mode is
      // the gate appearing in place of the page rather than an error.
      await expect(page.locator(".cp-split")).toHaveCount(0);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      expect(errors).toEqual([]);
    });
  }

  test("a collection hands over a file with its citation", async ({ page }) => {
    // The product is that readers download things. If this breaks, nothing
    // else on the page matters.
    //
    // The interaction differs by pointer, and deliberately so: a fine
    // pointer downloads from the tile, while on touch the first tap opens
    // the read panel and the panel carries the action, so a finger is not
    // sent back to the grid. Both routes end in the same file.
    const errors = watchConsole(page);
    await signIn(page);
    await page.goto("/data");

    // One collection, from a tile in the shelf grid — not the shelf's
    // "download all", which hands over a ZIP and would not exercise the
    // citation the CSV carries.
    const tile = page.locator(".cp-band__grid .cp-badge--act").first();
    await expect(tile).toBeVisible();

    const panelAction = page.locator(".cp-read__act");
    const download = page.waitForEvent("download");
    await tile.click();
    if (await panelAction.isVisible().catch(() => false)) await panelAction.click();
    const file = await download;

    expect(file.suggestedFilename()).toMatch(/\.csv$/);
    const stream = await file.createReadStream();
    const csv = (await stream.toArray()).map(String).join("");
    // Every release carries its provenance. A file that leaves without it is
    // the fabricated-provenance failure the citation register exists to
    // prevent, and it leaves the reader unable to say where a figure came
    // from.
    expect(csv.toLowerCase()).toContain("cedarpress.ai");
    expect(errors).toEqual([]);
  });
});

test.describe("Ask Cedar", () => {
  test("the launcher opens a panel and closes it again", async ({ page }, testInfo) => {
    const errors = watchConsole(page);
    await signIn(page);

    const launcher = page.locator(".cedar-widget__launcher");
    await expect(launcher).toBeVisible();
    await launcher.click();

    const panel = page.getByRole("dialog", { name: /ask cedar/i });
    await expect(panel).toBeVisible();
    await expect(panel).toBeInViewport();

    // The panel is anchored to the window, not to the page box. It was laid
    // out inside the page's measure once, because a retained identity
    // transform on an ancestor makes that ancestor the containing block for
    // fixed children. The only symptom was a sheet narrower than the screen
    // it was supposed to span, which is what the width is checked for here:
    // on a phone this is a bottom sheet and it spans the window.
    const box = await panel.boundingBox();
    const viewport = page.viewportSize();
    expect(box.width).toBeLessThanOrEqual(viewport.width + 1);
    if (testInfo.project.name === "phone") {
      expect(box.width).toBeGreaterThanOrEqual(viewport.width - 1);
    }

    await launcher.click();
    await expect(panel).toHaveCount(0);
    expect(errors).toEqual([]);
  });
});

test.describe("sponsorship", () => {
  // Nothing is booked, so every house slot shows the invitation to buy it.
  // One per page and never more, and never on a trust surface — Methods
  // exists to be believed and carries no inventory at any price.
  for (const { name, path, expected } of [
    { name: "the overview", path: "/", expected: 1 },
    { name: "Articles", path: "/articles", expected: 1 },
    { name: "an article", path: "/articles/brief-deals", expected: 1 },
    { name: "What's new", path: "/whats-new", expected: 1 },
    { name: "Methods", path: "/methods", expected: 0 },
  ]) {
    test(`${name} carries ${expected} invitation(s)`, async ({ page }) => {
      await signIn(page);
      await page.goto(path);
      await expect(page.locator(".cp-ad--house")).toHaveCount(expected);
      if (!expected) return;
      // Labelled above itself, so nobody reads a house panel as editorial.
      await expect(page.locator(".cp-ad--house .cp-ad__cap")).toHaveText("Sponsorship");
      // Laid out, not collapsed: the panel switches to a column in a rail and
      // on a phone, and the flex bases have to switch with it. Left unreset,
      // the body's 22rem basis becomes a height and the panel grows a screen
      // of empty green under two lines of text.
      const box = await page.locator(".cp-ad--house").first().boundingBox();
      expect(box.height).toBeLessThan(360);
      expect(box.height).toBeGreaterThan(60);
    });
  }
});

test.describe("crawlers", () => {
  // These live in public/ and are only correct if the build copies them. A
  // missing robots.txt is not a 404 a person ever sees, so nothing else here
  // would notice it.
  test("robots.txt is served and keeps crawlers out of the subscriber pages", async ({ request }) => {
    const response = await request.get("/robots.txt");
    expect(response.status()).toBe(200);
    const body = await response.text();
    expect(body).toContain("Sitemap: https://cedarpress.ai/sitemap.xml");
    for (const path of ["/articles", "/data", "/whats-new", "/methods", "/settings"]) {
      expect(body).toContain(`Disallow: ${path}`);
    }
  });

  test("the sitemap lists only what a visitor can reach", async ({ request }) => {
    const response = await request.get("/sitemap.xml");
    expect(response.status()).toBe(200);
    const body = await response.text();
    expect(body).toContain("http://www.sitemaps.org/schemas/sitemap/0.9");
    expect(body).toContain("<loc>https://cedarpress.ai/</loc>");
    // A sitemap that lists a page answering with a sign-in asks a search
    // engine to rank a login wall.
    for (const path of ["/articles", "/data", "/whats-new", "/settings"]) {
      expect(body).not.toContain(`<loc>https://cedarpress.ai${path}</loc>`);
    }
  });

  test("the page carries a policy and describes itself", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Cedar Press/);
    const csp = await page.locator('meta[http-equiv="Content-Security-Policy"]').getAttribute("content");
    expect(csp).toContain("object-src 'none'");
    expect(csp).toContain("script-src 'self'");
    const ld = await page.locator('script[type="application/ld+json"]').textContent();
    expect(() => JSON.parse(ld)).not.toThrow();
  });
});

test.describe("the stylesheet", () => {
  // press.css was once truncated mid-file by a bad edit and the build was
  // perfectly happy: CSS has no compile step to fail, the browser drops the
  // rules it cannot parse, and every other check here still passed because
  // the DOM was unchanged. The page rendered as a stack of unstyled blocks.
  //
  // So: two assertions the stylesheet is the only source of. Neither names a
  // colour, because that palette has changed twice and a smoke test should
  // not have an opinion about it.
  test("survived the build", async ({ page }, testInfo) => {
    await signIn(page);

    const band = page.locator(".cp-close");
    await expect(band).toHaveCSS("background-color", /^rgba?\((?!0, 0, 0, 0\)).+\)$/);

    if (testInfo.project.name !== "desktop") return;
    // The tiles are a grid. Stated without naming a column count, because
    // that is six, three or two depending on the width and all three are
    // correct: what is never correct is six full-width blocks stacked down
    // the page, which is what a grid that has stopped being a grid gives
    // you, and what the truncation gave. A tile narrower than half the row,
    // and some tile sharing a row with another, are true at every
    // breakpoint above a phone and false the moment the rules stop applying.
    const shape = await page.locator(".cp-hub__grid").evaluate((grid) => {
      const tiles = [...grid.querySelectorAll(".cp-hub__tile")];
      return {
        gridWidth: grid.getBoundingClientRect().width,
        widest: Math.max(...tiles.map((tile) => tile.getBoundingClientRect().width)),
        rows: new Set(tiles.map((tile) => Math.round(tile.getBoundingClientRect().top))).size,
        count: tiles.length,
      };
    });
    expect(shape.count).toBe(6);
    expect(shape.widest).toBeLessThan(shape.gridWidth / 2);
    expect(shape.rows).toBeLessThan(shape.count);
  });
});

test.describe("layout", () => {
  // Sideways scroll is the failure this page has produced most often: the
  // full-bleed bands are laid out with 100vw, which on a platform with a
  // classic scrollbar is wider than the layout viewport.
  for (const { name, path } of [{ name: "the overview", path: "/" }, ...SECTIONS]) {
    test(`${name} does not scroll sideways`, async ({ page }) => {
      await signIn(page);
      await page.goto(path);
      await page.evaluate(() => document.fonts.ready);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow).toBeLessThanOrEqual(1);
    });
  }
});

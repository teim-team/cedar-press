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
import { readdir, readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { expect, test } from "@playwright/test";

import { EMAIL, HASH, PASSWORD } from "./demoAccount.js";

// The throwaway account playwright.config.js provisions into the build it
// starts. It is not a credential and it opens nothing that is deployed
// anywhere; see tests/demoAccount.js.
const ACCOUNT = { email: EMAIL, password: PASSWORD };

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

  // This asserted the opposite until 2026-09-02: that the panel explained it
  // was a browser-checked preview gate. The owner had that copy removed
  // (f9633b4 — "you don't need the metatext on the website... it's kind of
  // dumb, like, preview build"), and the assertion was left behind, so main
  // shipped with two red smoke tests describing copy the product no longer
  // has.
  //
  // Deleting it would leave the decision unguarded, and this is exactly the
  // kind of copy that creeps back: it reads as diligence, and the reasoning
  // for removing it lives in a commit message nobody re-reads. So the test
  // is turned around. It now holds the decision — no build meta-copy on the
  // door — and holds the thing that copy was sitting next to, which is a
  // sign-in that actually works.
  //
  // What the copy said is still true and still written down where it is
  // load-bearing: pressDemoGate.js's docstring and SECURITY.md.
  test("the sign-in panel offers a working form and no build meta-copy", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("tab", { name: "Log in" }).click();
    const panel = page.locator("#cp-panel-signin");
    await expect(panel.getByLabel("Email address")).toBeVisible();
    await expect(panel.getByLabel("Password", { exact: true })).toBeVisible();
    await expect(panel.getByRole("button", { name: "Log in" })).toBeVisible();
    for (const gone of [/preview build/i, /not access control/i, /your own browser/i]) {
      await expect(panel).not.toContainText(gone);
    }
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
    // citation the CSV carries. The tile opens the collection in the viewer
    // and the reader panel beside the grid carries the sample download.
    const tile = page.locator(".cp-band__grid .cp-badge--act").first();
    await expect(tile).toBeVisible();
    await tile.click();
    await expect(tile).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByTestId("explore-scope")).toBeVisible();

    const panelAction = page.locator(".cp-read__act").first();
    await expect(panelAction).toBeVisible();
    const download = page.waitForEvent("download");
    await panelAction.click();
    const file = await download;

    // The sample rows, not the description fallback. This is the assertion
    // that makes the test worth running in a browser at all: the rows are a
    // static file the page fetches at click time, and `csvFor` falls back to
    // the two-column collection description when that fetch fails. Checking
    // only for "cedarpress.ai" passed either way, so a broken fetch would
    // have shipped green — the filename is what tells the two apart.
    expect(file.suggestedFilename()).toMatch(/\.csv$/);
    expect(file.suggestedFilename()).not.toContain("collection-description");

    const stream = await file.createReadStream();
    const csv = (await stream.toArray()).map(String).join("");
    // Ten sampled rows and a header, so the file is a table rather than the
    // handful of metadata lines the fallback produces.
    expect(csv.split("\n").length).toBeGreaterThan(10);
    // Every download carries its provenance. A file that leaves without it is
    // the fabricated-provenance failure the citation register exists to
    // prevent, and it leaves the reader unable to say where a figure came
    // from.
    expect(csv.toLowerCase()).toContain("cedarpress.ai");
    expect(csv).toContain("cite_as");
    expect(errors).toEqual([]);
  });
});

test.describe("Explore the collections", () => {
  /** A stored (uncompressed) ZIP, as pressDownload writes it: name -> text. */
  function unzipStored(bytes) {
    const files = {};
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    let at = 0;
    while (at + 30 <= bytes.length && view.getUint32(at, true) === 0x04034b50) {
      const method = view.getUint16(at + 8, true);
      const size = view.getUint32(at + 18, true);
      const nameLength = view.getUint16(at + 26, true);
      const extraLength = view.getUint16(at + 28, true);
      const name = Buffer.from(bytes.subarray(at + 30, at + 30 + nameLength)).toString("utf8");
      const start = at + 30 + nameLength + extraLength;
      expect(method).toBe(0);
      files[name] = Buffer.from(bytes.subarray(start, start + size)).toString("utf8");
      at = start + size;
    }
    return files;
  }

  /** On a phone the three pickers sit behind "Filters"; open it when it is there. */
  async function openFilters(page) {
    const filters = page.locator(".cp-ex__filters > summary");
    if (await filters.isVisible().catch(() => false) && !(await page.locator(".cp-ex__filters").getAttribute("open").then((v) => v !== null))) {
      await filters.click();
    }
  }

  test("the viewer filters the preview records, permalinks the cut and hands over exactly what it lists", async ({ page }) => {
    // The viewer is one object, the cut, drawn four ways: the URL, the
    // table, the download and the question to Cedar. This walks the first
    // three on the real samples the build serves and asserts they agree.
    const errors = watchConsole(page);
    await signIn(page);
    await page.goto("/data");
    const phone = (page.viewportSize()?.width ?? 1200) <= 720;

    const card = page.getByTestId("explore");
    await expect(card).toBeVisible();
    const caption = page.getByTestId("explore-caption");
    const records = page.getByTestId("explore-record");
    // Every open collection contributes its dataset's preview; the caption
    // counts sample records and says so, because ten rows is not the dataset.
    await expect(caption).toContainText("sample records");
    await expect(caption).toContainText("all collections");
    await expect(records.first()).toBeVisible();

    // Narrow to one entity from the picker; the URL now carries the cut.
    // `click` and an expectation rather than `check`: the box is controlled
    // by the URL, and React Router commits a navigation in a transition, so
    // the instant after the click the box still reads its old state.
    await openFilters(page);
    const entityPicker = page.getByTestId("explore-entity");
    await entityPicker.locator("summary").click();
    await expect(entityPicker).toHaveAttribute("open", "");
    const first = entityPicker.locator(".cp-ex__list input[type=checkbox]").first();
    await first.click();
    await expect(first).toBeChecked();
    await expect(page).toHaveURL(/[?&]e=CE-/);
    await expect(caption).not.toContainText("every record");
    // Escape closes the panel and the control keeps focus.
    await page.keyboard.press("Escape");
    await expect(entityPicker).not.toHaveAttribute("open", "");
    await expect(entityPicker.locator("summary")).toBeFocused();
    // The Close button closes it too.
    await entityPicker.locator("summary").click();
    await entityPicker.getByRole("button", { name: "Close Entity" }).click();
    await expect(entityPicker).not.toHaveAttribute("open", "");

    // The permalink reproduces the cut on a fresh load.
    const url = page.url();
    await page.goto(url);
    await expect(page.getByTestId("explore-caption")).not.toContainText("every record");

    // Typing a search and changing a filter at once: both survive, because
    // nothing waits in a timer to overwrite the newer change.
    await page.goto("/data");
    await page.getByLabel("Search these records").fill("tribal");
    await openFilters(page);
    await page.getByTestId("explore-type").locator("summary").click();
    await page.getByTestId("explore-type").locator(".cp-ex__list input[type=checkbox]").first().click();
    await expect(page).toHaveURL(/q=tribal/);
    await expect(page).toHaveURL(/[?&]t=/);
    await page.keyboard.press("Escape");

    // One collection is one dataset: choosing it shows the table's own
    // columns, the declared ones first, the header counting them, and the
    // scope line saying what the entity, the years and the amounts are.
    // From a clean cut: the search and the type above would narrow the
    // ten-record preview to nothing, which is its own case below.
    await page.goto("/data");
    await expect(records.first()).toBeVisible();
    await page.getByTestId("explore-collection").selectOption("lobbying");
    await expect(page).toHaveURL(/[?&]c=lobbying/);
    await expect(page.getByTestId("explore-caption")).toContainText("columns");
    await expect(page.getByTestId("explore-scope")).toContainText("filing year");
    if (!phone) {
      await expect(page.locator(".cp-ex__table--table")).toBeVisible();
      await expect(page.locator(".cp-ex__table--table thead th").first()).toBeVisible();
      await page.getByRole("button", { name: /Show all \d+ columns/ }).click();
      await expect(page.getByTestId("explore-caption")).toContainText(/(\d+) of \1 columns/);
    }
    // The record opens with a hierarchy: the main fields, then source and
    // attribution, then the technical fields folded away, and a source URL
    // that is a link.
    await records.first().locator("button").first().click();
    const record = page.locator(".cp-ex__inner").first();
    await expect(record).toBeVisible();
    await expect(record.locator("details.cp-ex__group").last()).toContainText("Technical fields");
    await expect(record.locator("dd a[href^='http']").first()).toBeVisible();

    // An out-of-coverage year range is shown AS REQUESTED, said in words,
    // and the empty result says what it does not establish.
    await page.goto("/data?c=lobbying&y=1800-1801");
    await expect(page.locator(".cp-ex__empty")).toContainText("does not establish");
    await openFilters(page);
    await expect(page.getByLabel("From year", { exact: true })).toHaveValue("1800");
    await expect(page.getByLabel("To year", { exact: true })).toHaveValue("1801");
    await expect(page.getByTestId("explore-years")).toContainText("Requested 1800–1801");
    // Unchecking the last type is "none", never "everything".
    await page.goto("/data?c=lobbying&t=");
    await expect(page.locator(".cp-ex__empty")).toBeVisible();
    await openFilters(page);
    await expect(page.getByTestId("explore-type")).toContainText("None");
    // A link naming two collections says two, not "all".
    await page.goto("/data?c=funding%7Cdeals");
    await expect(page.getByTestId("explore-collection")).toContainText("2 collections from this link");
    await expect(caption).toContainText("2 collections");
    // A link to a collection this catalog does not have is not widened.
    await page.goto("/data?c=gaming");
    await expect(page.getByTestId("explore-notes")).toContainText("Not a collection here: gaming");
    await expect(page.locator(".cp-ex__empty")).toContainText("No collection is selected");
    // A visible identifier is searchable.
    await page.goto("/data?c=lobbying&h=1");
    const someId = await records.first().getAttribute("data-record-id");
    expect(someId).toBeTruthy();
    await page.getByLabel("Search these records").fill(someId);
    await expect(records).toHaveCount(1);

    // The download is the cut's records and nothing else, re-importable as
    // such, with the citation and the cut in the README beside it.
    await page.goto("/data");
    await expect(records.first()).toBeVisible();
    await expect(caption).not.toContainText("loading");
    const shown = await records.count();
    const download = page.waitForEvent("download");
    await card.getByRole("button", { name: /Download summary results/ }).click();
    const file = await download;
    expect(file.suggestedFilename()).toMatch(/^cedar-press-summary-results-.*\.zip$/);
    const bytes = Buffer.concat((await (await file.createReadStream()).toArray()).map((c) => Buffer.from(c)));
    const files = unzipStored(bytes);
    expect(Object.keys(files).sort()).toEqual(["README.txt", "records.csv"]);
    const lines = files["records.csv"].split("\n");
    expect(lines[0].split(",")).toContain("record_id");
    // Every matching record, not only the page shown: the caption's count
    // is the file's count.
    const said = (await caption.innerText()).match(/(\d+) of \d+ sample records/i);
    expect(said).toBeTruthy();
    expect(lines.length - 1).toBe(Number(said[1]));
    expect(shown).toBeLessThanOrEqual(lines.length - 1);
    const width = lines[0].split(",").length;
    for (const line of lines) expect(line.split(",").length).toBeGreaterThanOrEqual(width);
    expect(files["records.csv"]).not.toContain("cite_as");
    expect(files["README.txt"]).toContain("cedarpress.ai");
    expect(files["README.txt"]).toContain("Cut query");
    expect(errors).toEqual([]);
  });

  test("a tile on the shelf opens its collection in the viewer, and the viewer lights the tile", async ({ page }) => {
    const errors = watchConsole(page);
    await signIn(page);
    await page.goto("/data");
    const tile = page.locator(".cp-band__grid .cp-badge--act").nth(1);
    await tile.click();
    await expect(tile).toHaveAttribute("aria-pressed", "true");
    await expect(page).toHaveURL(/[?&]c=/);
    await expect(page.getByTestId("explore-scope")).toBeVisible();
    // Choosing another collection in the viewer moves the light.
    await page.getByTestId("explore-collection").selectOption("deals");
    await expect(tile).toHaveAttribute("aria-pressed", "false");
    await expect(page.locator(".cp-badge.is-selected")).toHaveCount(1);
    // Cedar's launcher steps aside while the viewer is on screen; the
    // viewer's own action opens the panel.
    await page.getByTestId("explore").scrollIntoViewIfNeeded();
    await expect(page.locator(".cedar-widget__launcher")).toBeHidden();
    await page.getByTestId("explore").getByRole("button", { name: /Ask Cedar about this collection/ }).click();
    await expect(page.getByRole("dialog", { name: "Ask Cedar" })).toBeVisible();
    expect(errors).toEqual([]);
  });
});

test.describe("Shape the research", () => {
  test("the priorities page lists both kinds, says the counting needs the service, and the profile carries the card", async ({ page }) => {
    // This build has no service, so no point is counted and no point can be
    // placed; the page and the profile say exactly that rather than showing
    // a zero that means "unknown".
    const errors = watchConsole(page);
    await signIn(page);
    await page.goto("/priorities");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("What should Cedar research and build next?");
    await expect(page.getByTestId("priorities-research_question").getByTestId("priority").first()).toBeVisible();
    await expect(page.getByTestId("priorities-dataset").getByTestId("priority").first()).toBeVisible();
    await expect(page.getByTestId("priorities-static")).toContainText("not connected");
    await expect(page.getByTestId("priority-total").first()).toContainText("0 points · 0 subscribers");
    // The request form reads the words against the list before sending.
    await page.getByLabel("Tell Cedar what you need").fill("I wish you had a dataset showing which tribal enterprises own which subsidiaries");
    await expect(page.getByTestId("request-match")).toContainText("Tribal enterprise ownership and subsidiary relationships");
    await expect(page.getByRole("button", { name: "Submit my specific use case" })).toBeDisabled();
    // The profile's card and the homepage block.
    await page.goto("/settings");
    await expect(page.getByTestId("influence")).toContainText("Your research influence");
    await expect(page.getByTestId("influence")).toContainText("not connected");
    await page.goto("/");
    await expect(page.getByTestId("priorities-block")).toContainText("Subscriber research priorities");
    await expect(page.getByTestId("priorities-block")).toContainText("not yet counted");
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

test.describe("the bundle", () => {
  // The standalone gate is a demonstration gate and everything it reads is
  // public. That is survivable only while what it reads is a DIGEST. Until
  // 2026-09, this repository committed two preview accounts with their
  // passwords in plaintext and every build shipped them — grep the deployed
  // JavaScript and there they were.
  //
  // Read off disk rather than over HTTP so the check covers every emitted
  // chunk, including the lazily loaded ones no page in this suite opens.
  test("carries the digest and not the password", async () => {
    const dir = fileURLToPath(new URL("../dist-site/", import.meta.url));
    const assets = await readdir(dir, { recursive: true, withFileTypes: true });
    const text = assets.filter(
      (entry) => entry.isFile() && /\.(js|css|html|json|map)$/.test(entry.name),
    );
    expect(text.length, "nothing was built to check").toBeGreaterThan(0);

    let digestSeen = false;
    for (const entry of text) {
      const body = await readFile(`${entry.parentPath}/${entry.name}`, "utf8");
      expect(body, `${entry.name} ships the plaintext password`).not.toContain(PASSWORD);
      if (body.includes(HASH)) digestSeen = true;
    }
    // Without this the test would pass just as happily against a build with
    // no account configured at all, which proves nothing about the digest.
    expect(digestSeen, "the configured digest is not in the build").toBe(true);
  });
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

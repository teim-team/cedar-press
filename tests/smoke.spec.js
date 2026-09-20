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

import { EMAIL, HASH, PASSWORD, PRESS_EMAIL } from "./demoAccount.js";
// The twelve, read from the catalog rather than typed: a list typed here
// would pass while the door advertised something else.
import { STOREFRONT_CATALOG } from "../src/features/grove/pressCatalog.js";

// The throwaway account playwright.config.js provisions into the build it
// starts. It is not a credential and it opens nothing that is deployed
// anywhere; see tests/demoAccount.js.
const ACCOUNT = { email: EMAIL, password: PASSWORD };
const PRESS_ACCOUNT = { email: PRESS_EMAIL, password: PASSWORD };
const STOREFRONT_NAMES = STOREFRONT_CATALOG.map((entry) => entry.short || entry.name);

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

/**
 * Wait until an element has finished animating, before measuring it.
 *
 * The panels here slide in (`cp-dc-sheet` rises from `translateY(100%)`,
 * `cedar-rise` from 18px), and `toBeVisible()` is satisfied the moment the
 * animation starts. A `boundingBox()` taken then is of a box in motion: a
 * full-screen panel measured 0.18s in reported `y = 292` on a 664px window,
 * which is not where it is and not where it lands. Assertions about geometry
 * have to come after the motion, or they describe a frame.
 */
async function settled(locator) {
  await locator.waitFor({ state: "visible" });
  await locator.evaluate((el) =>
    Promise.all(el.getAnimations().map((animation) => animation.finished.catch(() => {}))),
  );
}

/** Sign in through the gate, the way a subscriber does. */
async function signIn(page, account = ACCOUNT) {
  await page.goto("/");
  await page.getByRole("tab", { name: "Log in" }).click();
  await page.getByLabel("Email address").fill(account.email);
  await page.getByLabel("Password", { exact: true }).fill(account.password);
  await page.locator(".cp-gate__form").getByRole("button", { name: "Log in" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Know what’s shaping Indian Country",
  );
}

/**
 * Open the door's Cedar, the way a reader on that scroll position actually can.
 *
 * The floating pill steps aside while the hero's preview object is on screen
 * (implementation brief §2.2: it sat on the collection strip, which is part of
 * the thing the object exists to demonstrate). Cedar is not unreachable there
 * — the preview's own foot carries "Ask Cedar", which dispatches
 * `cedar:ask-collection` — so this uses whichever control is actually offered.
 */
async function openDoorCedar(page) {
  const fab = page.locator(".cp-dc__fab");
  if (await fab.isVisible()) {
    await fab.click();
    return;
  }
  await page.locator(".cp-pane__act--btn").first().click();
}

test.describe("the gate", () => {
  test("the private preview note invites feedback and gives an access contact", async ({ page }) => {
    await page.goto("/");
    const notice = page.getByTestId("press-preview-note");
    await expect(notice).toBeVisible();
    await expect(notice).toContainText("small group");
    await expect(notice.getByRole("link", { name: "elijah.moreno@lumecon.ai" }))
      .toHaveAttribute("href", /mailto:elijah\.moreno@lumecon\.ai/);
    // The way out is a close control, not a "Continue →" pill. A reader who
    // does not want to continue anywhere still has to be able to shut it.
    await notice.getByRole("button", { name: "Close this notice" }).click();
    await expect(notice).toHaveCount(0);
  });

  test("the preview note is the door's, and is not carried into the product", async ({ page }) => {
    // It used to render inside `PressMast`, which every signed-in page
    // mounts, so a subscriber met an explanation of how they got in on the
    // collections table, on an entity profile and on the methods page —
    // above the product, addressed to somebody already inside it. Owner,
    // 2026-09-20: it should only be on the landing page.
    await signIn(page);
    for (const path of ["/data", "/data?c=funding", "/entity/CE-001CC-8N", "/methods", "/whats-new"]) {
      await page.goto(path);
      await expect(page.getByTestId("press-preview-note")).toHaveCount(0);
    }
  });

  test("a signed-out visitor gets the gate, not the reader", async ({ page }) => {
    const errors = watchConsole(page);
    await page.goto("/");
    await expect(page.locator(".cp-split")).toBeVisible();
    // Asserted as the absence of the catalogue rather than the presence of
    // the gate: a gate painted over a rendered reader is not access control.
    await expect(page.locator("#catalog")).toHaveCount(0);
    expect(errors).toEqual([]);
  });

  // The door stages the product: the twelve collections down the frame's
  // rail, one group a shelf, and the pane with real sample records of the
  // one in hand. Twelve is the
  // catalog's count; the records are the point, since a preview with a
  // description and no rows is a brochure. The reader's shelf (#catalog)
  // stays absent — asserted above — because the preview reads the public
  // ten-row samples and nothing else.
  test("the door lists every collection and stages real records", async ({ page }) => {
    const errors = watchConsole(page);
    await page.goto("/");
    // `.cp-rail__item` rather than `.cp-app__item`: the frame drew its own
    // navy list until the door started mounting the shared rail. Scoped to
    // the frame, since the strip below it is the same twelve again.
    await expect(page.getByTestId("press-frame").locator(".cp-rail__item")).toHaveCount(12);
    await expect(page.locator('[data-testid="collection-stage"]')).toHaveCount(1);
    await expect(page.locator('[data-testid="stage-record"]').first()).toBeVisible();
    // Scoped to the frame: the door now also carries a full-size strip of the
    // same twelve below it, so an unscoped name matches two controls.
    await page.getByTestId("press-frame").getByRole("button", { name: /Prime Contracting/ }).click();
    const stage = page.locator('[data-testid="collection-stage"][data-collection="contractors"]');
    await expect(stage).toBeVisible();
    await expect(stage.locator('[data-testid="stage-record"]').first()).toBeVisible();
    // The way in is named on the stage, never a route past the paywall.
    await expect(stage.getByRole("link", { name: /^Get Cedar Press/ })).toBeVisible();
    await expect(stage.getByRole("link", { name: /Browse the records/ })).toHaveCount(0);
    await expect(page.locator("#catalog")).toHaveCount(0);
    expect(errors).toEqual([]);
  });

  // Cedar on the door answers from a prepared bank (doorCedar.js) and never
  // reaches the network. The three things that matter: it answers, it says
  // the answers are prepared, and it refuses what it does not have rather
  // than guessing — a door assistant that improvises about a research
  // product is worse than none.
  test("Cedar on the door answers from the prepared bank", async ({ page }) => {
    const errors = watchConsole(page);
    await page.goto("/");
    await openDoorCedar(page);
    await expect(page.locator(".cp-dc__panel")).toBeVisible();
    await expect(page.locator(".cp-dc__context")).toContainText("Cedar Press");
    // The standing disclaimer is the one line the panel owes its reader.
    await expect(page.locator(".cp-dc__disclaimer")).toContainText("Cedar can make mistakes");
    // Opened from the preview the panel arrives with that collection's answer
    // already in it, which is the point of that control; opened from the pill
    // it arrives empty with starters. Either way there is a bot turn to read.
    const chip = page.locator(".cp-dc__chip").first();
    if (await chip.count()) await chip.click();
    await expect(page.locator(".cp-dc__msg--bot").nth(1)).toBeVisible();
    // A question it has nothing for is refused, not answered.
    await page.locator(".cp-dc__input").fill("what is the weather in Oslo");
    await page.locator(".cp-dc__send").click();
    await expect(page.locator(".cp-dc__msg--bot").last()).toContainText("do not have that one");
    expect(errors).toEqual([]);
  });

  // The door's Cedar is a dock, not a float, and on a phone it is the sheet
  // the whole window wide. The three things that were wrong on an iPhone: the
  // panel hung in the middle of the screen with page showing under it, the
  // launcher stayed on top of it, and every answer re-printed the whole
  // starter stack underneath itself.

  // THE PROOF OBJECT IS NOT SOMETHING TO PUT A BUTTON ON TOP OF.
  // Measured at 1440x900 the pill sat over the Advocacy tile in the preview's
  // collection strip. It steps aside while the object is on screen and comes
  // back once the reader scrolls past it; the preview's own foot carries the
  // Cedar action in the meantime, so nothing is lost.
  test("the launcher does not sit on the hero's preview", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop", "the preview fills the hero on desktop only");
    await page.goto("/");
    const fab = page.locator(".cp-dc__fab");
    await expect(fab).toBeHidden();
    // The object's own Cedar action is the way in while it is on screen.
    await expect(page.locator(".cp-pane__act--btn").first()).toBeVisible();
    // Past the hero, the pill is back.
    await page.locator(".cp-hero3__proof").scrollIntoViewIfNeeded();
    await page.mouse.wheel(0, 1400);
    await expect(fab).toBeVisible();
  });

  test("the door's Cedar docks to the bottom and the launcher steps aside", async ({ page }, testInfo) => {
    const errors = watchConsole(page);
    await page.goto("/");
    const launcher = page.locator(".cp-dc__fab");
    // The pill, deliberately, and not the preview's own action: this test is
    // about the EMPTY panel — how it docks and how its starter stack behaves —
    // and opening from the preview arrives with a collection answer already
    // in the thread, so there are no starters to collapse. Scroll past the
    // preview first, which is where the pill is offered.
    await page.locator(".cp-hero3__proof").scrollIntoViewIfNeeded();
    await page.mouse.wheel(0, 1400);
    await expect(launcher).toBeVisible();
    await launcher.click();

    const panel = page.locator(".cp-dc__panel");
    await expect(panel).toBeVisible();
    await expect(panel).toBeInViewport();
    await settled(panel);
    // The launcher is gone while the panel is up: the panel's own close is
    // the way out, and a pill over the sheet's corner covers its last line.
    await expect(launcher).toBeHidden();

    // Flush to the bottom edge of the window, within the safe-area inset a
    // headless browser reports as zero.
    const box = await panel.boundingBox();
    const viewport = page.viewportSize();
    expect(viewport.height - (box.y + box.height)).toBeLessThanOrEqual(1);
    expect(box.width).toBeLessThanOrEqual(viewport.width + 1);
    if (testInfo.project.name === "phone") {
      // A phone gets the whole screen, not a sheet across part of it. This
      // assertion used to read `toBeLessThan(viewport.height * 0.85)` — the
      // panel was capped at 78dvh and the rule under test was that it left
      // the page showing above itself. lumecon.ai moved off exactly that
      // arrangement (CedarFAB.astro, `max-width: 600px`), because the strip
      // of page it leaves is not worth the half-screen it costs the
      // transcript, and cedarpress.ai was landing its teal header across the
      // middle of the hero headline. The rule now is the reference's rule.
      expect(box.width).toBeGreaterThanOrEqual(viewport.width - 1);
      expect(box.height).toBeGreaterThanOrEqual(viewport.height - 1);
      expect(box.y).toBeLessThanOrEqual(1);
    }

    // The starter stack is an opening, not a toolbar: asking collapses it for
    // good, and the answer carries at most three next questions instead.
    const starters = await page.locator(".cp-dc__chip").count();
    expect(starters).toBeGreaterThan(1);
    await page.locator(".cp-dc__chip").first().click();
    await expect(page.locator(".cp-dc__chip")).toHaveCount(0);
    const followups = page.locator(".cp-dc__follow");
    await expect(followups.first()).toBeVisible();
    expect(await followups.count()).toBeLessThanOrEqual(3);

    // A follow-up answers and is replaced by the next answer's own row, so
    // the suggestions never pile up under the thread.
    const first = await followups.first().textContent();
    await followups.first().click();
    await expect(page.locator(".cp-dc__msg--you").last()).toContainText(first.trim());
    await expect(page.locator(".cp-dc__followups")).toHaveCount(1);

    // An explicit close hands focus back, because the launcher was hidden and
    // a keyboard user would otherwise be dropped at the top of the document.
    await page.locator(".cp-dc__close").click();
    await expect(panel).toHaveCount(0);
    await expect(launcher).toBeVisible();
    await expect(launcher).toBeFocused();

    // Codex, PR #80: a dismissal is not a close. Clicking outside handed focus
    // back to the launcher a frame after the browser focused what was clicked,
    // so dismissing the sheet ate the click that dismissed it and the control
    // had to be clicked twice. The sheet is not modal; the click belongs to
    // the control. `#cp-tab-signin` sits in the header, which the corner card
    // never covers.
    //
    // That premise holds at a desktop width and no longer holds on a phone,
    // where the panel is now the screen and there is no "outside" to click.
    // Both contracts are checked, because both are real: the phone's way out
    // is the close button, which is why it is 44px.
    const behind = page.locator("#cp-tab-signin");
    await launcher.click();
    await expect(panel).toBeVisible();
    await settled(panel);
    if (testInfo.project.name === "phone") {
      // Covered, not hidden: the control is still in the layout and still
      // `visible` to CSS, and the panel is simply painted over it. So the
      // assertion is what is actually on top at its centre, which is the only
      // thing that decides whether a tap can reach it.
      const covered = await behind.evaluate((el) => {
        const box = el.getBoundingClientRect();
        const top = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
        return Boolean(top?.closest(".cp-dc__panel"));
      });
      expect(covered).toBe(true);
      await page.locator(".cp-dc__input").click();
      await page.locator(".cp-dc__close").click();
      await expect(panel).toHaveCount(0);
      await expect(behind).toBeVisible();
    } else {
      await expect(behind).toBeVisible();
      await page.locator(".cp-dc__input").click();
      await behind.click();
      await expect(panel).toHaveCount(0);
      await expect(behind).toBeFocused();
    }
    expect(errors).toEqual([]);
  });

  test("the collection pane hands its collection to Cedar", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector('[data-testid="stage-record"]');
    await page.locator('[data-testid="collection-stage"]').getByRole("button", { name: /Ask Cedar/ }).click();
    await expect(page.locator(".cp-dc__msg--you").last()).toContainText("Federal Funding");
    await expect(page.locator(".cp-dc__msg--bot").last()).toContainText("federal government");
  });

  test("the door does not scroll sideways", async ({ page }) => {
    await page.goto("/");
    await page.evaluate(() => document.fonts.ready);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(1);
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

    // Signing out is inside the account menu now: the masthead is one row at
    // every width, and an errand does not get a row of its own.
    await page.locator(".cp-acct > summary").click();
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

    // One collection's own sample, not the toolbar's Download: that one
    // hands over the current CUT as a ZIP with its README, and it is the
    // per-collection CSV that carries `cite_as` in the rows. This used to
    // live on the shelf's reader panel; the shelf's tiles were deleted when
    // the table became the Collections page, and the action moved into the
    // pane head rather than going with them.
    await expect(page.locator(".cp-rail__item").first()).toBeVisible();
    // In the actions menu since 2026-09-20: the toolbar collapsed to one row
    // so the table could have the screen, and the secondary downloads went
    // behind "More" together. Still one click from the records.
    await page.locator(".cp-ex__bar .cp-ex__more > summary").click();
    const panelAction = page.locator(".cp-ex__sample").first();
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
    // Collections opens on one collection now (Federal Funding), so the
    // all-collections view this test walks is reached the way a reader
    // reaches it: the rail's first row.
    // Scrolled to the top first: the rail is sticky, so Playwright's
    // scroll-into-view can chase an element that never moves relative to the
    // viewport. A reader clicking the rail is at the top of the page anyway.
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.locator(".cp-rail__item--all").click({ timeout: 10000 });
    const caption = page.getByTestId("explore-caption");
    const records = page.getByTestId("explore-record");
    // Before a reader asks for a record, this is a collection catalog.
    await expect(page.getByTestId("atlas-row")).toHaveCount(STOREFRONT_CATALOG.length);
    await expect(caption).toContainText("choose a collection to browse records");
    // "12 collections", not "all collections": an explicit all is an explicit
    // list now (the rail writes the ids), because clearing the parameter
    // means "unspecified" and resolves to the default collection.
    await expect(caption).toContainText(/\d+ collections/);

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
    await expect(records.first()).toBeVisible();
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
    await page.locator(".cp-rail__item").filter({ hasText: "Advocacy" }).first().click();
    await expect(page).toHaveURL(/[?&]c=lobbying/);
    await expect(page.getByTestId("explore-caption")).toContainText("columns");
    await expect(page.getByTestId("explore-scope")).toContainText("filing year");
    if (!phone) {
      await expect(page.locator(".cp-ex__table--table")).toBeVisible();
      await expect(page.locator(".cp-ex__table--table thead th").first()).toBeVisible();
      await page.getByRole("button", { name: /Show all \d+ columns/ }).click();
      await expect(page.getByTestId("explore-caption")).toContainText(/(\d+)\/\1 columns/);
    }
    // A row opens the record's own page, which carries the cut it came from.
    // Covered end to end in "the record page" below; here the only claim is
    // that the table's control leads there and comes back.
    await page.goto("/data?c=lobbying");
    await expect(records.first()).toBeVisible();
    await records.first().locator("a").first().click();
    await page.waitForURL(/\/record\?/);
    await expect(page.getByTestId("record-head")).toBeVisible();
    await page.getByRole("link", { name: "Back to results" }).first().click();
    await page.waitForURL(/\/data\?/);
    // Coming back from a record restores the cut, which the rail shows.
    await expect(page.locator(".cp-rail__item[aria-pressed='true']")).toContainText("Advocacy");

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
    // The picker that used to say "2 collections from this link" is gone —
    // the rail replaced it, and a two-collection cut has no single row to
    // light. The caption is where that state lives now.
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

    // With every collection selected, the table becomes the collection atlas.
    // It is a catalog, not a pooled record set: select a collection before
    // any record export is enabled.
    await page.goto("/data");
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.locator(".cp-rail__item--all").click({ timeout: 10000 });
    const atlasRows = page.getByTestId("atlas-row");
    await expect(atlasRows).toHaveCount(STOREFRONT_CATALOG.length);
    await expect(caption).toContainText("choose a collection to browse records");
    await expect(card.getByRole("button", { name: /^Download$/ })).toBeDisabled();
    await page.getByLabel("Find a collection").fill("Federal Funding");
    await expect(atlasRows).toHaveCount(1);
    await expect(page.locator(".cp-ex__pages")).toHaveCount(0);
    await page.getByLabel("Find a collection").fill("");
    await atlasRows.getByRole("button", { name: "Federal Funding" }).click();
    await expect(page).not.toHaveURL(/[?&]q=/);
    await expect(records.first()).toBeVisible();
    const download = page.waitForEvent("download");
    await card.getByRole("button", { name: /^Download$/ }).click();
    const file = await download;
    expect(file.suggestedFilename()).toMatch(/^cedar-press-sample-results-.*\.zip$/);
    const bytes = Buffer.concat((await (await file.createReadStream()).toArray()).map((c) => Buffer.from(c)));
    const files = unzipStored(bytes);
    expect(Object.keys(files).sort()).toEqual(["README.txt", "records.csv"]);
    const lines = files["records.csv"].split("\n");
    expect(lines[0].split(",")).toContain("assistance_transaction_unique_key");
    // Every listed preview record is in the export.
    expect(lines.length - 1).toBe(await records.count());
    const width = lines[0].split(",").length;
    for (const line of lines) expect(line.split(",").length).toBeGreaterThanOrEqual(width);
    expect(files["records.csv"]).not.toContain("cite_as");
    expect(files["README.txt"]).toContain("cedarpress.ai");
    expect(files["README.txt"]).toContain("Cut query");
    expect(errors).toEqual([]);
  });

  // This was "a tile on the shelf opens its collection in the viewer, and
  // the viewer lights the tile" — two controls for one choice, kept in sync.
  // There is one control now. The tiles were the catalogue a reader had to
  // browse before reaching a table, and the rail is the catalogue.
  test("the rail selects a collection, and the pane and the URL follow", async ({ page }) => {
    const errors = watchConsole(page);
    await signIn(page);
    await page.goto("/data");

    // It opens on a collection, not on twelve searched at once.
    await expect(page.getByTestId("explore-caption")).toContainText("Federal Funding");

    const row = page.locator(".cp-rail__item").filter({ hasText: "Deals" }).first();
    await row.click();
    await expect(row).toHaveAttribute("aria-pressed", "true");
    await expect(page).toHaveURL(/[?&]c=deals/);
    await expect(page.getByTestId("explore")).toContainText("Deals");
    // One row lit, never two.
    await expect(page.locator(".cp-rail__item[aria-pressed='true']")).toHaveCount(1);

    // Cedar's launcher steps aside while the viewer is on screen; the
    // viewer's own action opens the panel.
    await page.getByTestId("explore").scrollIntoViewIfNeeded();
    await expect(page.locator(".cedar-widget__launcher")).toBeHidden();
    await page.getByTestId("explore").getByRole("button", { name: /Ask Cedar about this collection/ }).click();
    await expect(page.getByRole("dialog", { name: "Ask Cedar" })).toBeVisible();
    expect(errors).toEqual([]);
  });

  test("a Cedar Press reader sees the Plus boundary in the table", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop", "the desktop table exposes its column headers");
    const errors = watchConsole(page);
    await signIn(page, PRESS_ACCOUNT);

    const protectedRequests = [];
    page.on("request", (request) => {
      if (/\/contractors\//.test(new URL(request.url()).pathname)) protectedRequests.push(request.url());
    });
    await page.goto("/data?c=contractors");

    const locked = page.getByTestId("explore-locked");
    await expect(locked).toBeVisible();
    await expect(locked.getByRole("heading", { name: "Federal Prime Contracting" })).toBeVisible();
    const headings = await locked.locator("th").allInnerTexts();
    expect(headings.join(" | ").toUpperCase()).toContain("ACTION DATE");
    expect(headings.join(" | ").toUpperCase()).toContain("AMOUNT");
    await expect(locked.locator(".cp-lock__row")).toHaveCount(22);
    await expect(locked.locator(".cp-lock__bar").first()).toBeVisible();
    await expect(locked.locator(".cp-lock__say")).toContainText("Available with Cedar Press+");
    expect(protectedRequests).toEqual([]);

    await locked.getByTestId("explore-about").click();
    await expect(page.locator(".cp-ab")).toBeVisible();
    expect(errors).toEqual([]);
  });

  for (const { label, account } of [
    { label: "Cedar Press", account: PRESS_ACCOUNT },
    { label: "Cedar Press+", account: ACCOUNT },
  ]) {
    test(`${label} sees a deliberate no-preview state when publication is withheld`, async ({ page }) => {
      const errors = watchConsole(page);
      await signIn(page, account);
      await page.goto("/data?c=owned");

      const unavailable = page.getByTestId("explore-unavailable");
      await expect(unavailable).toBeVisible();
      await expect(unavailable.getByRole("heading", { name: "Preview unavailable" })).toBeVisible();
      await expect(unavailable).toContainText("Not available for self-service browsing");
      await expect(unavailable.locator(".cp-lock__row")).toHaveCount(0);
      await expect(unavailable).not.toContainText("Available with Cedar Press+");
      await unavailable.getByTestId("explore-about").click();
      await expect(page.locator(".cp-ab")).toBeVisible();
      expect(errors).toEqual([]);
    });
  }

  test("All collections is a catalog table with the Plus shelf in place", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop", "the full catalog table is a desktop surface");
    const errors = watchConsole(page);
    await signIn(page, PRESS_ACCOUNT);
    await page.goto("/data");
    await page.locator(".cp-rail__item--all").click();

    const atlas = page.locator(".cp-atlas");
    await expect(atlas).toBeVisible();
    await expect(atlas.getByTestId("atlas-row")).toHaveCount(STOREFRONT_CATALOG.length);
    await expect(atlas.locator(".cp-atlas__included")).toHaveCount(
      STOREFRONT_CATALOG.filter((entry) => entry.shelf === "standard").length,
    );
    await expect(atlas.locator(".cp-atlas__locked")).toHaveCount(
      STOREFRONT_CATALOG.filter((entry) => entry.shelf === "pro" && entry.id !== "owned").length,
    );
    await expect(atlas.locator(".cp-atlas__pending")).toHaveCount(1);
    await expect(page.locator(".cp-ex__pages")).toHaveCount(0);

    await atlas.getByRole("button", { name: "Federal Prime Contracting" }).click();
    await expect(page.getByTestId("explore-locked")).toBeVisible();
    expect(errors).toEqual([]);
  });

  test("the Cedar Grove fragment reaches the compact workspace handoff", async ({ page }) => {
    const errors = watchConsole(page);
    await signIn(page);
    await page.goto("/data#grove");
    await expect(page.locator("#grove")).toBeInViewport({ timeout: 10_000 });
    expect(errors).toEqual([]);
  });
});

test.describe("the table's default columns", () => {
  // Eleven flagships declare a 6-8 column view in their contract, chosen by
  // the owner and recorded in docs/PUBLIC_DATASET_SPEC_2026-09-05.md. The
  // viewer preferred the CODEBOOK, which is a dictionary of every column, so
  // `listed` was never empty and the declared view was never read: Prime
  // Contracting opened on 44 columns beginning with five raw ids.
  test("a single collection opens on the declared view, not the whole dictionary", async ({ page }, testInfo) => {
    // A phone gets the card list instead of a table, which carries the four
    // things a thumb can read and is a different presentation of the same
    // narrowing. The column choice is a desktop question.
    test.skip(testInfo.project.name !== "desktop", "desktop renders the table; a phone renders cards");
    const errors = watchConsole(page);
    await signIn(page);
    await page.goto("/data?c=contractors");
    await page.locator(".cp-ex__table thead th").first().waitFor();
    const heads = await page.locator(".cp-ex__table thead th").allInnerTexts();
    // The declared seven, plus the pinned uid and the row opener.
    expect(heads.length).toBeLessThanOrEqual(10);
    const text = heads.join(" | ").toUpperCase();
    for (const wanted of ["NATIVE ENTITY", "ACTION DATE", "AWARDEE", "FUNDING AGENCY", "DESCRIPTION", "AMOUNT"]) {
      expect(text).toContain(wanted);
    }
    // The raw keys stay in the open record, where the reviewer asked for them.
    for (const raw of ["TRANSACTION ID", "AWARDEE UEI", "PRODUCT OR SERVICE CODE", "RECIPIENT COUNTY FIPS"]) {
      expect(text).not.toContain(raw);
    }
    // And everything is still one click away.
    const all = page.getByRole("button", { name: /Show all \d+ columns/ });
    await expect(all).toBeVisible();
    await all.click();
    expect((await page.locator(".cp-ex__table thead th").allInnerTexts()).length).toBeGreaterThan(30);
    expect(errors).toEqual([]);
  });
});

test.describe("the question mark", () => {
  // One control, two behaviours, decided by the pointer. Both projects run it,
  // because the phone project is where the tap-latch lives and the desktop
  // project is where hover does.
  test("opens and closes the way this pointer expects", async ({ page }, testInfo) => {
    const errors = watchConsole(page);
    await signIn(page);
    await page.goto("/data?c=contractors");
    const btn = page.locator(".cp-ex1__btn").first();
    await btn.waitFor();
    const panel = page.locator(".cp-ex1__panel").first();
    await expect(panel).toBeHidden();

    if (testInfo.project.name === "desktop") {
      await btn.hover();
      await expect(panel).toBeVisible();
      await page.mouse.move(4, 4);
      await expect(panel).toBeHidden();
      // Keyboard reaches it, and Escape closes it.
      await btn.focus();
      await expect(panel).toBeVisible();
      await page.keyboard.press("Escape");
      await expect(panel).toBeHidden();
    } else {
      // A tap latches. It used to open and then reopen on the second tap,
      // because tapping also focuses and onFocus opened it again.
      await btn.tap();
      await expect(panel).toBeVisible();
      await btn.tap();
      await expect(panel).toBeHidden();
      // The sheet carries its own way out: the question mark that opened it
      // has usually scrolled behind it by then.
      await btn.tap();
      await expect(panel).toBeVisible();
      await panel.getByRole("button", { name: "Close" }).tap();
      await expect(panel).toBeHidden();
    }

    // Whatever the pointer, the panel carries declared prose and stays inside
    // the viewport. Opened the way this pointer opens it: a mouse click is
    // deliberately inert, because hover governs a mouse.
    if (testInfo.project.name === "desktop") await btn.hover(); else await btn.tap();
    await expect(panel).toContainText("up to ten sample rows");
    const box = await panel.boundingBox();
    const width = page.viewportSize().width;
    expect(box.x).toBeGreaterThanOrEqual(-1);
    expect(box.x + box.width).toBeLessThanOrEqual(width + 1);

    // Codex, PR #80: the placement ran only when `open` changed, so a panel
    // left open across a rotation or a crossing of the 560px breakpoint kept
    // the nudge measured for the old viewport — and on the bottom sheet, which
    // pins itself to the gutters, a negative nudge takes its left edge off the
    // screen. Resize it while it is open and it has to still be inside.
    //
    // Opened without the mouse resting on it, because a resize moves the
    // pointer out of a hovered panel and closing on that is correct: it is the
    // LATCHED panel that has to survive a viewport change. A phone taps; on
    // desktop the keyboard latches the same way.
    const before = page.viewportSize();
    await page.mouse.move(4, 4);
    await btn.blur();
    await expect(panel).toBeHidden();
    if (testInfo.project.name === "desktop") await btn.focus(); else await btn.tap();
    await expect(panel).toBeVisible();
    for (const next of [{ width: 640, height: 900 }, { width: 380, height: 820 }, before]) {
      await page.setViewportSize(next);
      await expect(panel).toBeVisible();
      const now = await panel.boundingBox();
      expect(now.x).toBeGreaterThanOrEqual(-1);
      expect(now.x + now.width).toBeLessThanOrEqual(next.width + 1);
    }
    expect(errors).toEqual([]);
  });
});

test.describe("About this collection", () => {
  // The paragraph that used to stand between the table's headline and its
  // toolbar. Review, 2026-09-15: "keep collection coverage and methodology
  // available through 'About this collection'." Declared prose, still: the
  // coverage row rendered for none of the twelve once, because `coverage` is
  // an object and a string filter dropped it silently.
  test("holds the collection's declared coverage and method, and nothing is typed into it", async ({ page }) => {
    const errors = watchConsole(page);
    await signIn(page);
    await page.goto("/data?c=contractors");
    // It was a `<details>` in the pane head holding four lines. It is a
    // deep-linkable profile now, so the test opens it the way a reader does
    // and then checks the address it leaves behind — the whole point of
    // making it a panel is that a method can be sent to somebody.
    const about = page.getByTestId("explore-about");
    await expect(about).toBeVisible();
    await about.click();
    await expect(page).toHaveURL(/about=1/);
    const panel = page.locator(".cp-ab");
    await expect(panel).toBeVisible();
    await expect(panel).toContainText("Awardees are matched to a Native entity");
    // The release facts a reader checks a figure against.
    for (const field of ["Release", "Updated", "Coverage", "Records"]) {
      await expect(panel.locator("dt", { hasText: new RegExp(`^${field}$`) }).first()).toBeVisible();
    }
    // The unit of observation, in the codebook's own words: the sentence
    // anyone about to cite a count needs and the old disclosure never had.
    await expect(panel).toContainText("One row is");
    const notes = panel.locator(".cp-ab__more");
    await expect(notes.getByText("Read the full collection notes")).toBeVisible();
    await notes.getByText("Read the full collection notes").click();
    await expect(panel.getByRole("heading", { name: "What is not in it" })).toBeVisible();

    // Closing returns the reader to the cut they opened it from.
    await panel.getByRole("button", { name: /close the collection profile/i }).click();
    await expect(panel).toHaveCount(0);
    await expect(page).toHaveURL(/c=contractors/);
    await expect(page).not.toHaveURL(/about=1/);
    expect(errors).toEqual([]);
  });
});

test.describe("the door's twelve", () => {
  // A visitor deciding whether to subscribe should be able to see what the
  // twelve are and what each holds without signing in. The product frame's
  // rail has always been clickable, but the frame renders at about 0.63
  // scale: seventeen-pixel rows in six-point type.
  test("the pre-login page previews all twelve and drives the frame", async ({ page }, testInfo) => {
    const errors = watchConsole(page);
    await page.goto("/");
    const tiles = page.locator(".cp-dcol__tile");
    await tiles.first().waitFor();
    await expect(tiles).toHaveCount(12);
    // Grouped by the plan each comes with, which is the question a visitor has.
    await expect(page.locator(".cp-dcol__tier")).toHaveCount(2);
    await expect(page.locator(".cp-dcol__shelf").first()).toContainText("See what's happening");

    const pane = page.locator(".cp-app__pane");
    const before = await pane.innerText();
    const target = tiles.nth(8);
    if (testInfo.project.name === "desktop") await target.hover(); else await target.tap();
    // The line under the strip answers whether or not the frame is on screen,
    // and the frame above follows the same selection.
    await expect(page.locator(".cp-dcol__note")).not.toContainText(/for what it holds|window above/);
    await expect(pane).not.toHaveText(before);
    expect(errors).toEqual([]);
  });
});

test.describe("the record page", () => {
  // The review that produced this page, 2026-09-14: the expanded row was a
  // record page squeezed into a table, with no address and no way back to the
  // result it was opened from. These are the four claims that replaced it.
  test("a row opens a linkable record, walks its neighbours and returns to the exact result", async ({ page }) => {
    const errors = watchConsole(page);
    await signIn(page);
    await page.goto("/data?c=funding");
    const records = page.getByTestId("explore-record");
    await expect(records.first()).toBeVisible();
    const openedId = await records.first().getAttribute("data-record-id");

    await records.first().locator("a").first().click();
    await page.waitForURL(/\/record\?/);
    // The address carries the table, the record and the cut it came from, so
    // the page can be sent to someone and still know where "back" is.
    const url = new URL(page.url());
    expect(url.searchParams.get("k")).toBe("funding/federal_funding_transactions");
    expect(url.searchParams.get("r")).toBe(openedId);
    expect(url.searchParams.get("from")).toContain("c=funding");

    // The first screen answers the row: the entity, what it funded, the money.
    const head = page.getByTestId("record-head");
    await expect(head.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByTestId("record-summary")).toBeVisible();

    // Definitions are a control, not a paragraph under every value.
    const definitions = page.getByTestId("record-definitions");
    await expect(page.locator(".cp-rec__mean")).toHaveCount(0);
    await definitions.click();
    await expect(page.locator(".cp-rec__mean").first()).toBeVisible();

    // The rest of the record is folded until it is asked for, and it opens
    // in groups rather than as one list of fifty-four fields.
    await expect(page.locator(".cp-rec__group")).toHaveCount(0);
    await page.getByTestId("record-more").click();
    const groups = page.locator(".cp-rec__group");
    expect(await groups.count()).toBeGreaterThan(1);
    await expect(groups.first().locator(".cp-rec__fields")).toBeHidden();
    await groups.first().locator("summary").click();
    await expect(groups.first().locator(".cp-rec__fields")).toBeVisible();

    // Next walks the reader's own ordering and stays on a record page.
    await page.getByRole("link", { name: /^Next/ }).first().click();
    await page.waitForURL(/\/record\?/);
    await expect(page.getByTestId("record-head")).toBeVisible();
    const second = new URL(page.url()).searchParams.get("r");
    expect(second).not.toBe(openedId);

    // And back is back: the same cut, reproduced.
    await page.getByRole("link", { name: "Back to results" }).first().click();
    await page.waitForURL(/\/data\?/);
    await expect(page.locator(".cp-rail__item[aria-pressed='true']")).toContainText("Federal Funding");
    expect(errors).toEqual([]);
  });

  test("a record that is not in the preview says so rather than showing a neighbour", async ({ page }) => {
    await signIn(page);
    await page.goto("/record?k=funding/federal_funding_transactions&r=not-a-real-record");
    await expect(page.getByTestId("record-empty")).toContainText("not in this preview");
  });

  test("the entity name opens a profile that gathers the entity's records", async ({ page }) => {
    const errors = watchConsole(page);
    await signIn(page);
    await page.goto("/data?c=funding");
    await page.getByTestId("explore-record").first().locator("a").first().click();
    await page.waitForURL(/\/record\?/);
    const name = page.locator(".cp-rec__name a").first();
    await expect(name).toBeVisible();
    await name.click();
    await page.waitForURL(/\/entity\/CE-/);
    await expect(page.getByTestId("entity-head").getByRole("heading", { level: 1 })).toBeVisible();
    // Counts on this page are counts of preview records, and it says so.
    await expect(page.getByTestId("entity-head")).toContainText(/published previews/);
    // And the way back is the record it was opened from.
    await expect(page.getByRole("link", { name: "Back to the record" })).toBeVisible();
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
    // The influence card carries the "no service" sentence; the note under it
    // says what the list is, given that. It used to repeat "not connected" a
    // second time in the same column.
    await expect(page.getByTestId("influence")).toContainText("not connected");
    await expect(page.getByTestId("priorities-static")).toContainText("Support cannot be placed here");
    // Eleven cards reading "0 points · 0 subscribers" is a product nobody
    // uses; with no service those zeros are not measurements, so the row says
    // who does the counting instead.
    await expect(page.getByTestId("priority-total").first()).toContainText("Support is counted by the Cedar Press service");
    // Writing anything is the point of the page, so the box leads it and the
    // use case is a free field rather than a menu of seven guesses.
    await expect(page.getByRole("textbox", { name: "What you would use it for" })).toBeVisible();
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
    await settled(panel);

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
      // Full screen, the same rule the door's Cedar now follows and the same
      // rule lumecon.ai's panel follows: a question gets the screen while it
      // is being asked. It was a 70vh sheet holding 5.2rem of padding open at
      // its foot to keep its last line clear of the launcher.
      expect(box.width).toBeGreaterThanOrEqual(viewport.width - 1);
      expect(box.height).toBeGreaterThanOrEqual(viewport.height - 1);
    }

    if (testInfo.project.name === "phone") {
      // The launcher is hidden while a full-screen dialog is up — it would
      // sit on top of the answer, and it is no longer the way out. The
      // panel's own close is, so that is what a phone closes with.
      await expect(launcher).toBeHidden();
      await panel.getByRole("button", { name: /close ask cedar/i }).click();
    } else {
      await launcher.click();
    }
    await expect(panel).toHaveCount(0);
    expect(errors).toEqual([]);
  });
});

test.describe("house style", () => {
  // "No visible copy uses an ampersand" — implementation brief, acceptance
  // criteria. Asserted against RENDERED TEXT rather than by grepping source,
  // because the rule is about what a reader sees: `&amp;` in JSX and `&` in a
  // string are the same character on the page and a grep for one misses the
  // other.
  //
  // THE RULE IS ABOUT AUTHORED COPY, NOT ABOUT QUOTED NAMES.
  //
  // Two exemptions, and both were found by running this rather than by
  // reasoning about it:
  //
  //   1. "Native Federal Advocacy & Engagement" is a COLLECTION NAME from
  //      `data/cedar/collections.manifest.json` — the generated release
  //      manifest, which is also what Cedar Grove's descriptors are built
  //      from. Rewriting it here would make the product disagree with the
  //      release it publishes, and with Grove, about the name of a thing
  //      readers are invited to cite.
  //   2. "Quechan Tribe of the Fort Yuma Indian Reservation, California &
  //      Arizona" is a CANONICAL ENTITY NAME from the register — the tribe's
  //      name as the federal record states it. Editing a Nation's legal name
  //      to satisfy a house style is not a copy fix; it is the product
  //      asserting something the source does not say, which is the one thing
  //      the whole identity layer exists to prevent.
  //
  // So the table and the register's name cells are excluded by selector,
  // which keeps the rule enforceable as new names arrive rather than needing
  // a string added here every time one does.
  // `.cp-ex__cards` is the phone's record surface — the same rows the desktop
  // draws as a table. Missing it was the whole reason this test failed on the
  // phone project and passed on desktop, which is a useful reminder that
  // "visible copy" is per-composition, not per-page.
  const QUOTED = [
    ".cp-ex__table",
    ".cp-ex__cards",
    ".cp-pane__table",
    ".cp-ex__lname",
    ".cp-ex__uid",
    ".cp-rec",
    ".cp-ent",
  ].join(", ");
  const FROM_THE_MANIFEST = ["Native Federal Advocacy & Engagement"];

  for (const { name, path } of [
    { name: "the door", path: "/" },
    { name: "the overview", path: "/" },
    { name: "Collections", path: "/data" },
    { name: "Methods", path: "/methods" },
    { name: "What's new", path: "/whats-new" },
    { name: "Settings", path: "/settings" },
    { name: "Research access", path: "/research-access" },
    { name: "Tribal data request", path: "/tribal-data-request" },
  ]) {
    test(`${name} uses no ampersand in visible copy`, async ({ page }) => {
      if (path !== "/" || name !== "the door") await signIn(page);
      await page.goto(path);
      await page.locator("main, .cp-door").first().waitFor();
      let text = await page.evaluate((quoted) => {
        // A detached clone, so removing the quoted subtrees to read the rest
        // does not change the page the next assertion sees.
        const body = document.body.cloneNode(true);
        for (const node of body.querySelectorAll(quoted)) node.remove();
        return body.innerText;
      }, QUOTED);
      for (const allowed of FROM_THE_MANIFEST) text = text.split(allowed).join("");
      const offending = text
        .split("\n")
        .map((line) => line.trim())
        .filter((line) => line.includes("&"));
      expect(offending, `ampersand in visible copy on ${path}`).toEqual([]);
    });
  }
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

  // The public pages are prerendered (scripts/prerender.mjs): their text is
  // in the document a crawler fetches, before any script runs. Asserted on
  // the raw response, not the rendered page, because the rendered page looks
  // identical whether or not the prerender happened.
  for (const [path, heading] of [
    // "data" is emphasised inside the headline, so the string a crawler
    // sees is split by a tag; the tail of the sentence is contiguous.
    ["/", "behind Indian Country."],
    ["/tribal-data-request", "See what Cedar knows about your Nation"],
    ["/research-access", "Need one or two Cedar collections for a defined project"],
  ]) {
    test(`${path} is served with its text in the HTML, before any script runs`, async ({ request }) => {
      const response = await request.get(path);
      expect(response.status()).toBe(200);
      const body = await response.text();
      expect(body).toContain(heading);
      expect(body).toMatch(/<meta name="robots" content="index, follow" ?\/?>/);
      expect(body).toContain('<script type="application/ld+json">');
    });
  }

  test("the door names all twelve collections in the HTML a crawler fetches", async ({ request }) => {
    // The strip is what a visitor uses to preview what they get, and it is
    // also the only place the door spells the twelve out at readable size.
    // Prerendered, so it is text in the document rather than something that
    // appears after a script runs; a crawler and a reader with JS off both
    // get the list.
    const body = await (await request.get("/")).text();
    const names = STOREFRONT_NAMES;
    expect(names).toHaveLength(12);
    for (const name of names) expect(body).toContain(name);
    expect(body).toContain("Twelve collections");
  });

  test("a page behind the gate is not offered to crawlers", async ({ request }) => {
    // Unknown and gated paths get the shell (404.html is the shell), whose
    // static head says nothing a crawler should rank; the app adds noindex
    // once it mounts.
    const body = await (await request.get("/data")).text();
    expect(body).not.toContain("Every collection, and what it holds");
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
    // The hub is two ranks now — two lead cards and four quieter ones — so
    // the tiles live in two containers rather than one. The property this
    // test exists for is unchanged: every rank is still laid out, and none of
    // them has collapsed into full-width blocks stacked down the page.
    const shape = await page.evaluate(() => {
      const measure = (selector) => {
        const box = document.querySelector(selector);
        const tiles = [...box.querySelectorAll(".cp-hub__tile")];
        return {
          width: box.getBoundingClientRect().width,
          widest: Math.max(...tiles.map((t) => t.getBoundingClientRect().width)),
          rows: new Set(tiles.map((t) => Math.round(t.getBoundingClientRect().top))).size,
          count: tiles.length,
        };
      };
      return { lead: measure(".cp-hub__lead"), rest: measure(".cp-hub__grid--rest") };
    });
    // Six doors, same as before the split.
    expect(shape.lead.count + shape.rest.count).toBe(6);
    // Each rank is one row across, and no tile owns its whole row.
    expect(shape.lead.rows).toBe(1);
    expect(shape.lead.widest).toBeLessThan(shape.lead.width);
    expect(shape.rest.rows).toBe(1);
    expect(shape.rest.widest).toBeLessThan(shape.rest.width / 2);
  });
});

test.describe("Methods", () => {
  test("the twelve marks index the collections, and one profile opens beneath", async ({ page }) => {
    const errors = watchConsole(page);
    await page.goto("/methods");
    // The section was twelve stacked accordions; it is the twelve marks now,
    // and the count is the catalog's, so a collection cannot go missing here
    // without going missing from the shelf too.
    const tiles = page.locator(".cp-mbc__tile");
    await expect(tiles).toHaveCount(12);
    await expect(page.locator("#mbc-panel")).toBeVisible();
    const first = await page.locator(".cp-mbc__name").innerText();
    await tiles.nth(5).click();
    await expect(page.locator(".cp-mbc__name")).not.toHaveText(first);
    // Arrow keys walk the index: twelve separate tab stops is not a tablist.
    await tiles.nth(5).focus();
    await page.keyboard.press("ArrowRight");
    await expect(page.locator(".cp-mbc__tile.is-on")).toHaveCount(1);
    expect(errors).toEqual([]);
  });

  test("the identity section names both identifiers and does not claim an endorsement", async ({ page }) => {
    await page.goto("/methods");
    const cards = page.locator(".cp-idp__card");
    await expect(cards).toHaveCount(2);
    await expect(cards.first()).toContainText("Cedar entity id");
    await expect(cards.nth(1)).toContainText("Cedar business id");
    // Both display forms, per the owner's specification of 2026-09-13.
    await expect(page.locator(".cp-idp__shape").first()).toHaveText(/^CE-[0-9A-Z]{5}-[0-9A-Z]{2}$/);
    await expect(page.locator(".cp-idp__shape").nth(1)).toHaveText(/^CB-\d{7}$/);
    // The business register is not claimed as live while nothing mints it.
    await expect(page.locator(".cp-idp__pending")).toContainText("being minted");
    // A nation and the company it owns are two subjects, and the page says so
    // with the ownership as a dated edge rather than a merged row.
    // The uid on the page must be the nation's real one. It was not: the
    // example paired CE-00001-6S with Cherokee Nation, which the register
    // binds to Asa'carsarmiut Tribe.
    await expect(page.locator(".cp-wb__id").first()).toHaveText("CE-00134-BX");
    await expect(page.locator(".cp-wb__card").first()).toContainText("Cherokee Nation");
    await expect(page.locator(".cp-wb__id").nth(1)).toHaveText(/^CB-/);
    // The entity card advertises the column the exports actually carry.
    await expect(page.locator(".cp-idp__card").first()).toContainText("cedar_uid");
    await expect(page.locator(".cp-wb__edgelabel")).toContainText(/effective dates/i);
    await expect(page.locator(".cp-wb__close")).toContainText("never goes in a business column");
    // Everything that can change is named as living outside the identifier.
    await expect(page.locator(".cp-ko")).toContainText("UEI");
    await expect(page.locator(".cp-ko")).toContainText("NAICS");
    // Coverage is published with its reasons, and two of the three are marked
    // as intentional rather than left reading as 94% failure.
    await expect(page.locator(".cp-ur__item")).toHaveCount(3);
    await expect(page.locator(".cp-ur__item.is-by-design")).toHaveCount(2);
    await expect(page.locator(".cp-ur")).toContainText("Never a failed match");
    await expect(page.locator(".cp-ur")).toContainText("not by failure");
    // Codex, PR #79: the two phrases above come only from the intentional
    // statuses, so an empty "Still to do" card passed. Every card must carry
    // a real definition, and none may be the missing-definition fallback.
    for (const body of await page.locator(".cp-ur__body").allInnerTexts()) {
      expect(body.trim().length).toBeGreaterThan(20);
      expect(body).not.toContain("Definition missing");
    }
    await expect(page.locator(".cp-ur__item:not(.is-by-design)")).toContainText("could not place");
    // The loop says where the methods come from. It must not say the Federal
    // Reserve uses or endorses them: the workspace evidences affiliation and
    // nothing more, and that is the one claim here a reader could disprove.
    const loop = await page.locator(".cp-loop").innerText();
    expect(loop).toContain("Federal Reserve");
    expect(loop).not.toMatch(/Federal Reserve[^.]*\b(uses|endorses|relies on)\b/i);
    // "Accuracy has a time dimension" came off the page with its timeline.
    await expect(page.locator("body")).not.toContainText("Accuracy has a time dimension");
    await expect(page.locator(".cp-tl")).toHaveCount(0);
  });
});

test.describe("the first screen", () => {
  // WHAT A READER SEES BEFORE SCROLLING, ASSERTED.
  //
  // The 2026-09-15 review found what a passing suite could not: "the
  // Collections screenshot contains no collections, and the record screenshot
  // never reaches the $500,000 amount", and asked that "the next review
  // should explicitly check what users can see before scrolling, whether
  // button labels wrap, and whether the main content arrives before its
  // explanation. The reported tests do not establish those visual qualities."
  //
  // These are those checks. They run on the phone profile, where the failure
  // shows first, and they measure the built page rather than describing it.
  // The phone profile only: the first screen is where this fails first, and
  // the desktop project renders a different layout for the same pages.
  test.beforeEach(({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "phone", "the first screen is a phone question");
    void page;
  });

  /** How far down the page the top of this element sits, in viewport heights. */
  async function topOf(page, selector) {
    return page.locator(selector).first().evaluate((node) => node.getBoundingClientRect().top);
  }

  test("the header is one row, and the section menu is a control rather than two rows of links", async ({ page }) => {
    const errors = watchConsole(page);
    await signIn(page);
    await page.goto("/data");
    const header = await page.locator(".cp-mast").first().boundingBox();
    const viewport = page.viewportSize().height;
    // It was four rows: wordmark, avatar with a wrapped "Sign out", and two
    // rows of section links.
    expect(header.height).toBeLessThan(viewport * 0.16);
    // Signing out is in the account menu, not loose in the header.
    await expect(page.getByRole("button", { name: "Sign out" })).toHaveCount(0);
    await expect(page.locator(".cp-navm__btn")).toBeVisible();
    await expect(page.locator(".cp-nav__item")).toHaveCount(0);
    expect(errors).toEqual([]);
  });

  // "No full-screen catalog sits between /data and a first useful record."
  //
  // This used to assert that a shelf TILE was on the first screen, which was
  // the right intent measured against the old arrangement: the tier bands ran
  // above the viewer, so a tile was the first collection-shaped thing a
  // reader met. The explorer carries its own rail now and is mounted first,
  // so the catalogue and the records arrive together, and the bands were
  // asking the reader to choose twice. Asserting the tile now would be
  // asserting the arrangement that was removed.
  test("Collections opens on the records, with the rail beside them", async ({ page }) => {
    const errors = watchConsole(page);
    await signIn(page);
    await page.goto("/data");
    await page.locator(".cp-rail__item").first().waitFor();
    await page.evaluate(() => document.fonts.ready);
    const viewport = page.viewportSize().height;
    // The catalogue, as the rail.
    expect(await topOf(page, ".cp-rail__item")).toBeLessThan(viewport);
    // And a record with it, not a screen of chooser first. The phone lays the
    // rail down as a strip above the records, so both fit either way.
    const record = page.locator(".cp-ex__table tbody tr, .cp-ex__cardbtn").first();
    await record.waitFor();
    // ONE SCREEN, NOT TWO. This allowed `viewport * 2` while the page still
    // carried a title band above the frame and the toolbar ran to three rows
    // on a phone. Owner, 2026-09-20: "the collection page we want the table
    // to just take up that screen in full." A record on the first screen is
    // what that means, and it is the assertion that keeps it true.
    expect(await topOf(page, ".cp-ex__table tbody tr, .cp-ex__cardbtn")).toBeLessThan(viewport);
    expect(errors).toEqual([]);
  });


  test("a record opens on its amount", async ({ page }) => {
    const errors = watchConsole(page);
    await signIn(page);
    await page.goto("/data?c=funding");
    await page.getByTestId("explore-record").first().waitFor();
    await page.getByTestId("explore-record").first().locator("a").first().click();
    await page.waitForURL(/\/record\?/);
    await page.locator(".cp-rec__fig").waitFor();
    await page.evaluate(() => document.fonts.ready);
    const viewport = page.viewportSize().height;
    // The money the row is about, before any scrolling.
    expect(await topOf(page, ".cp-rec__fig")).toBeLessThan(viewport);
    // And the row's definition is no longer standing in front of it.
    await expect(page.getByTestId("record-head")).not.toContainText("What one row is");
    expect(errors).toEqual([]);
  });

  test("an entity profile opens on its records", async ({ page }) => {
    const errors = watchConsole(page);
    await signIn(page);
    await page.goto("/entity/CE-001CC-8N");
    await page.locator(".cp-ent__row").first().waitFor();
    await page.evaluate(() => document.fonts.ready);
    const viewport = page.viewportSize().height;
    expect(await topOf(page, ".cp-ent__row")).toBeLessThan(viewport);
    expect(errors).toEqual([]);
  });

  test("no action label wraps past two lines", async ({ page }) => {
    const errors = watchConsole(page);
    await signIn(page);
    await page.goto("/data?c=funding");
    await page.getByTestId("explore-record").first().waitFor();
    // "Download sample results" wrapped onto four lines beside two-line
    // neighbours. A control is allowed two lines; four is a broken label.
    const tall = await page.locator(".cp-ex__acts .cp-ex__act").evaluateAll((nodes) =>
      nodes
        .map((node) => {
          const line = Number.parseFloat(getComputedStyle(node).lineHeight) || 16;
          const box = node.getBoundingClientRect();
          return { text: node.textContent.trim(), lines: Math.round((box.height - 16) / line) };
        })
        .filter((entry) => entry.lines > 2));
    expect(tall).toEqual([]);
    expect(errors).toEqual([]);
  });
});

test.describe("the loop between the records and the journalism", () => {
  // THE LOOP BETWEEN THE RECORDS AND THE JOURNALISM.
  //
  // Owner, 2026-09-20: "maybe articles that have used those data sets get
  // populated... because we have links to the data sets on the article page.
  // But that feedback loop seems helpful."
  //
  // One relationship, `draws`, read both ways. The risk a test is worth here
  // is not that the link renders — it is that the two ends drift apart, so
  // both directions are asserted against the same collection.
  test("a collection names what was written from it, and the writing links back", async ({ page }) => {
    const errors = watchConsole(page);
    await signIn(page);
    await page.goto("/data?c=funding");
    await page.locator(".cp-rail__item").first().waitFor();
    // Out: the collection's records to a piece built on them.
    const read = page.locator(".cp-ex__wrote").first();
    await expect(read).toBeVisible();
    await expect(read).toContainText("Read:");
    // Federal Funding has two, and the second is not crammed into the row:
    // it opens the collection's profile, where every one is listed.
    await page.locator(".cp-ex__wrotemore").click();
    await expect(page.getByRole("heading", { name: "Research built from this collection" })).toBeVisible();
    expect(await page.locator(".cp-ab__read").count()).toBeGreaterThan(1);

    // Back: a piece to the collection, open in the table rather than only as
    // a ten-row file.
    await page.goto("/articles/brief-deals");
    const open = page.getByRole("link", { name: /Open it in the table/ }).first();
    await expect(open).toBeVisible();
    await open.click();
    await expect(page).toHaveURL(/\/data\?c=deals/);
    await page.locator(".cp-rail__item").first().waitFor();
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Deals");
    expect(errors).toEqual([]);
  });

  // The third way in: an entity's profile reads ten sample rows per table,
  // and each collection heading on it opens the release itself — carrying
  // BOTH the collection and the entity, so it lands narrowed to what the
  // heading was about rather than on the collection's first page.
  test("an entity's collection heading opens the table already narrowed to it", async ({ page }) => {
    const errors = watchConsole(page);
    await signIn(page);
    await page.goto("/entity/CE-001CC-8N");
    const heading = page.locator(".cp-ent__glink").first();
    await heading.waitFor({ timeout: 20000 });
    await heading.click();
    await expect(page).toHaveURL(/\/data\?c=[a-z-]+&e=CE-001CC-8N/);
    await page.locator(".cp-rail__item").first().waitFor();
    // Narrowed, not just opened: the caption names the entity the cut is on.
    await expect(page.getByTestId("explore-caption")).toContainText("Yakama");
    expect(errors).toEqual([]);
  });
});

test.describe("the reveal", () => {
  // .cp-fade is opacity: 0 in CSS and revealed by JavaScript. The rules were
  // deleted by accident once and nothing broke visibly, because a class with
  // no rule does nothing: forty-odd marked sections simply stopped arriving.
  // This is the assertion that would have caught it.
  test("marked sections start hidden and arrive on scroll", async ({ page }) => {
    await page.goto("/methods");
    await page.locator(".cp-mbc__tile").first().waitFor();
    await page.evaluate(() => document.fonts.ready);
    const below = await page.evaluate(() =>
      [...document.querySelectorAll(".cp-fade")]
        .filter((el) => el.getBoundingClientRect().top > window.innerHeight * 1.2)
        .map((el) => Number(getComputedStyle(el).opacity)));
    expect(below.length).toBeGreaterThan(0);
    expect(below.every((o) => o === 0)).toBe(true);

    await page.evaluate(() => window.scrollTo(0, window.innerHeight * 1.5));
    await page.waitForTimeout(1200);
    // `is-in`, not a computed opacity: a section that entered the viewport a
    // moment ago is mid-transition and reads as 0.4, which is the reveal
    // working. The invariant is that nothing a reader can see stays unrevealed.
    // The observer runs with rootMargin -6%, so something peeking in by a few
    // pixels is deliberately not revealed yet. Ask the same question it does.
    const hidden = await page.evaluate(() => {
      const inset = window.innerHeight * 0.06;
      return [...document.querySelectorAll(".cp-fade")]
        .filter((el) => { const r = el.getBoundingClientRect(); return r.bottom > inset && r.top < window.innerHeight - inset; })
        .filter((el) => !el.classList.contains("is-in"))
        .map((el) => el.className);
    });
    expect(hidden).toEqual([]);
    const revealed = await page.evaluate(() => document.querySelectorAll(".cp-fade.is-in").length);
    expect(revealed).toBeGreaterThan(0);
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

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
// The fourteen, read from the catalog rather than typed: a list typed here
// would pass while the door advertised something else.
import { STOREFRONT_CATALOG } from "../src/features/grove/pressCatalog.js";
import { LUMECON_URL, TBN_URL } from "../src/features/grove/pressArticles.js";
import {
  AUDIENCE_JOBS,
  ENTITY_JOBS,
  collectionQuestions,
  researchExamples,
  uncoveredIds,
  visibleAudiences,
} from "../src/features/grove/pressJobs.js";

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
  test("the early access note names the summit and gives an access contact", async ({ page }) => {
    await page.goto("/");
    const notice = page.getByTestId("press-preview-note");
    await expect(notice).toBeVisible();
    await expect(notice.locator("b")).toHaveText("Early access.");
    await expect(notice.locator(".cp-preview__copy")).toHaveText(
      "Early access. Cedar Press is open early to attendees of the Great Lakes Tribal Economic Summit ahead of its public launch. Need a login? elijah.moreno@lumecon.ai",
    );
    await expect(notice).not.toContainText("small group");
    await expect(notice.getByRole("link", { name: "elijah.moreno@lumecon.ai" }))
      .toHaveAttribute("href", "mailto:elijah.moreno@lumecon.ai?subject=Cedar%20Press%20preview%20access");
    // The way out is a close control, not a "Continue →" pill. A reader who
    // does not want to continue anywhere still has to be able to shut it.
    await notice.getByRole("button", { name: "Close this notice" }).click();
    await expect(notice).toHaveCount(0);
    await page.reload();
    await expect(page.getByTestId("press-preview-note")).toHaveCount(0);
  });

  // The maintenance story and the NEED enrichment sources (owner,
  // 2026-09-27), on the door; the figure is 600+ (owner, 2026-09-27).
  test("the door says how Cedar Press is maintained and names the NEED enrichment sources", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("door-maintenance")).toContainText(
      "Cedar Press maintains its datasets weekly with human review, expands their source coverage and useful fields over time and develops new collections.",
    );
    const panel = page.locator(".cp-hero3__proof");
    for (const label of ["Patent publication and family records", "Historical S&P and Fitch ratings", "AM Best insurance financial-strength releases", "IRS Form 990-PF grant schedules", "Recorded deeds and land transfers"]) {
      await expect(panel).toContainText(label);
    }
    await expect(panel.locator(".cp-hero3__proofcount")).toContainText("600+ source websites");
  });

  // The sticky masthead is opaque (owner, 2026-09-27): no alpha, no blur,
  // and the hero's old source-reach line under the partners is gone.
  test("the masthead is opaque and the hero carries no source-reach line", async ({ page }) => {
    await page.goto("/");
    const bar = page.locator(".cp-door__bar");
    await expect(bar).toHaveCSS("background-color", "rgb(255, 255, 255)");
    await expect(bar).toHaveCSS("backdrop-filter", "none");
    await expect(page.locator(".cp-hero3__reach")).toHaveCount(0);
    await expect(page.locator(".cp-hero3")).not.toContainText("distinct source websites in dataset construction");
    await expect(page.locator(".cp-hero3__proofcount")).toContainText("600+ source websites");
  });

  // The landing layout of 2026-09-27: the source banner in the navy
  // passage's right column, the summary figures one line under the viewer
  // caption with nothing below the hero's button, the passage in three
  // paragraphs with Lumecon, its team page and Tribal Business News linked,
  // and the long-run trust line gone.
  test("the source banner sits in the navy passage and the figures sit under the viewer", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator(".cp-why .cp-why__side .cp-hero3__proof")).toHaveCount(1);
    await expect(page.locator(".cp-hero3__copy .cp-hero3__facts")).toHaveCount(0);
    await expect(page.locator(".cp-hero3__stage figcaption + .cp-hero3__facts")).toHaveCount(1);
    const ledes = page.locator(".cp-why__lede");
    await expect(ledes).toHaveCount(3);
    await expect(ledes.nth(1).locator('a[href="https://lumecon.ai"]')).toHaveCount(1);
    await expect(ledes.nth(1).locator('a[href="https://lumecon.ai/team/"]')).toHaveCount(1);
    await expect(ledes.nth(2).locator('a[href="https://tribalbusinessnews.com"]')).toHaveCount(1);
    await expect(page.locator("body")).not.toContainText("As search and analytical tools improve");
  });

  // The navy banner does not pause, cannot be selected, and is not in the
  // order the source list is written in (owner, 2026-09-27).
  test("the source banner keeps moving, cannot be selected, and is not in list order", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop", "a pointer question");
    await page.goto("/");
    const runs = page.locator(".cp-why__runs");
    await runs.scrollIntoViewIfNeeded();
    await runs.hover();
    const states = await page.locator(".cp-why__sources .cp-hero3__marquee").evaluateAll((els) => els.map((el) => getComputedStyle(el).animationPlayState));
    expect(states.every((s) => s === "running")).toBe(true);
    await expect(runs).toHaveCSS("user-select", "none");
    const covered = await runs.evaluate((el) => {
      const r = el.getBoundingClientRect();
      const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return hit === el;
    });
    expect(covered, "the layer over the runs takes the pointer").toBe(true);
    const shown = await page.locator(".cp-why__runs .cp-hero3__run:not([aria-hidden])").evaluateAll((uls) => uls.flatMap((ul) => [...ul.querySelectorAll("li")].map((li) => li.textContent)));
    const sorted = [...shown].sort((a, b) => a.localeCompare(b));
    expect(shown).not.toEqual(sorted);
  });

  test("a reader who closed the old private-preview note sees the early access note once", async ({ page }) => {
    await page.goto("/");
    await page.evaluate(() => sessionStorage.setItem("cedar-press-private-preview-notice", "dismissed"));
    await page.reload();
    await expect(page.getByTestId("press-preview-note")).toBeVisible();
    await expect(page.getByTestId("press-preview-note")).toContainText("Early access.");
  });

  test("every signed-in route wears the same masthead", async ({ page }) => {
    // The collections page used to hide the standing line and shrink the
    // wordmark and the mark to buy 86px for the records. Owner, 2026-09-20:
    // "trusted intelligence for Indian Country looks like it's on a header
    // on some pages and not others." A masthead is the one thing that must
    // not change between routes, because it is what says this is still the
    // same publication.
    await signIn(page);
    const seen = new Map();
    // EVERY route, not the seven section pages. The three that were left out
    // were the three that were wrong: the two public pages passed the reader
    // to the masthead but no sign-out, so their Sign out button was wired to
    // `undefined`, and an article id that is not hosted rendered a masthead
    // with no reader at all and stood 12px shorter than the rest.
    for (const path of [
      "/", "/data", "/articles", "/whats-new", "/methods", "/priorities", "/settings",
      "/research-access", "/tribal-data-request", "/record",
      "/entity/CE-001CC-8N", "/articles/not-a-piece-we-host",
    ]) {
      await page.goto(path);
      await page.locator(".cp-mast").waitFor();
      await page.evaluate(() => document.fonts.ready);
      const signature = await page.evaluate(() => {
        const mast = document.querySelector(".cp-mast");
        const line = document.querySelector(".cp-mast__of--line");
        const word = document.querySelector(".cp-mast__word");
        const mark = document.querySelector(".cp-mast__mark");
        const shown = line && getComputedStyle(line).display !== "none";
        return [
          Math.round(mast.getBoundingClientRect().height),
          shown ? "line" : "no-line",
          word && getComputedStyle(word).fontSize,
          mark && Math.round(mark.getBoundingClientRect().width),
          document.querySelector(".cp-acct") ? "account" : "no-account",
        ].join("|");
      });
      if (!seen.has(signature)) seen.set(signature, []);
      seen.get(signature).push(path);
    }
    // One signature across every route. That is the invariant at both
    // widths; what the signature IS differs between them, because a phone
    // masthead genuinely has no room for the standing line and drops it at
    // 760px. What it may not do is differ between two routes at one width.
    // Keyed by signature so a failure names the routes that disagreed rather
    // than only the count.
    expect(Object.fromEntries(seen)).toEqual({ [[...seen.keys()][0]]: expect.any(Array) });
    // And where there is room, the line is there, with the reader's menu.
    const wide = (page.viewportSize().width ?? 0) > 760;
    expect([...seen.keys()][0]).toContain(wide ? "|line|" : "|no-line|");
    expect([...seen.keys()][0]).toContain("|account");
  });

  test("Sign out signs out, from whichever page offered it", async ({ page }) => {
    // The research-access and tribal-data-request pages handed the masthead a
    // reader and no way to sign one out, so the menu drew a Sign out wired to
    // `undefined`. It looked exactly like the working one on every other page.
    await signIn(page);
    await page.goto("/research-access");
    await page.locator(".cp-acct__btn").click();
    await page.locator(".cp-acct__out").click();
    // This page is public, so signing out leaves the reader on it rather than
    // bouncing them to the door: the masthead loses the menu and the sections
    // in place. The door is the proof the session actually ended.
    await expect(page.locator(".cp-acct")).toHaveCount(0);
    await expect(page.locator(".cp-nav")).toHaveCount(0);
    await page.goto("/");
    await expect(page.locator(".cp-split")).toBeVisible();
    await expect(page.locator("#catalog")).toHaveCount(0);
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

  // The door stages the product: the fourteen collections down the frame's
  // rail, one group a shelf, and the pane with real sample records of the
  // one in hand. Fourteen is the
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
    await expect(page.getByTestId("press-frame").locator(".cp-rail__item")).toHaveCount(STOREFRONT_CATALOG.length);
    expect(STOREFRONT_CATALOG.length).toBe(14);
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

  // Cedar on the door answers from its own bank (doorCedar.js) and never
  // reaches the network. The three things that matter: it answers, it sets
  // the same expectation the site's Cedar sets, and it says so when it has
  // nothing for a question rather than guessing — a door assistant that
  // improvises about a research product is worse than none.
  test("Cedar on the door answers from its own bank", async ({ page }) => {
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
    const answered = page.locator(".cp-dc__msg--bot:not([aria-hidden])");
    await expect(answered.nth(1)).toBeVisible();
    // A question it has nothing for is said to be so, not answered.
    await page.locator(".cp-dc__input").fill("what is the weather in Oslo");
    await page.locator(".cp-dc__send").click();
    await expect(answered.last()).toContainText("do not have that one");
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
    // The catalog's own words, not a phrase typed here: the blurb is owner copy
    // and changes on the owner's say.
    const blurb = STOREFRONT_CATALOG.find((entry) => entry.id === "funding").blurb;
    await expect(page.locator(".cp-dc__msg--bot").last()).toContainText(blurb.slice(0, 60));
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

    // THE OVERVIEW IS A BRIEFING NOW, NOT SIX DOORS.
    // It asserted six hub tiles — Collections, Research Briefs, Priorities,
    // What's new, Methods, Plans — which is the masthead's own nav bar
    // restated underneath itself. Owner, 2026-09-20: "Make it feel more like
    // a briefing: one lead development, three signals worth watching, one
    // collection or research brief to explore, one Cedar question worth
    // asking." Those four are what is asserted, because those four are what
    // the page is for; every one of them is read from the release record or
    // the article list, so none of it can go stale in place.
    await expect(page.locator(".cp-brief__lead")).toBeVisible();
    // The lead's PICTURE, in the DOM and decoded -- not its JSX. The unit
    // test beside this one reads the source, and source can be commented out
    // or put behind a condition that never fires while every regex over it
    // still matches. `naturalWidth` is the only assertion that distinguishes
    // "the element rendered" from "the file actually arrived", and the page
    // was measurably the thinnest in the product for want of exactly this.
    const leadImage = page.locator(".cp-brief__img");
    await expect(leadImage).toBeVisible();
    await expect
      .poll(() => leadImage.evaluate((el) => el.naturalWidth), { timeout: 5000 })
      .toBeGreaterThan(0);
    await expect(page.locator(".cp-brief__signals a")).toHaveCount(3);
    await expect(page.locator(".cp-brief__coll")).toBeVisible();
    await expect(page.getByRole("button", { name: /Ask Cedar what changed/ })).toBeVisible();
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
    // And no record rows behind it: the catalogue replaces the pooled
    // sample rather than sitting above them.
    await expect(records).toHaveCount(0);

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

  // FOUNDATION & CORPORATE GIVING AND PLOT ARE LIVE ON THEIR PLANS (owner,
  // 2026-09-27). Each opens for the plan that includes it like any other
  // collection on its shelf, and where another collection shows sample
  // records it shows what each record holds. No row count, span or version
  // is stated for either, anywhere a reader can see.
  const NUMERIC_COUNT = /\d[\d,.]*\s*(k|m|million|thousand)?\s*(rows?|records?)\b/i;
  for (const { id, fields, cases } of [
    { id: "foundation-corporate-giving", fields: 27, cases: [{ account: PRESS_ACCOUNT, open: true }, { account: ACCOUNT, open: true }] },
    { id: "plot", fields: 9, cases: [{ account: PRESS_ACCOUNT, open: false }, { account: ACCOUNT, open: true }] },
  ]) {
    for (const { account, open } of cases) {
      test(`${id} ${open ? "opens on what each record holds" : "is offered on Cedar Press+"} for ${account === ACCOUNT ? "Cedar Press+" : "Cedar Press"}`, async ({ page }) => {
        const errors = watchConsole(page);
        await signIn(page, account);
        await page.goto(`/data?c=${id}`);
        const explore = page.getByTestId("explore");
        await expect(explore).not.toContainText(/not yet published|first release/i);
        await expect(page.getByTestId("explore-unavailable")).toHaveCount(0);
        if (open) {
          const view = page.getByTestId("explore-structure");
          await expect(view).toBeVisible();
          await expect(page.getByTestId("explore-locked")).toHaveCount(0);
          await expect(view).toContainText("What each record holds");
          await expect(view.getByTestId("record-structure").locator("tbody tr")).toHaveCount(fields);
          expect(await view.innerText()).not.toMatch(NUMERIC_COUNT);
        } else {
          const locked = page.getByTestId("explore-locked");
          await expect(locked).toBeVisible();
          await expect(locked.locator(".cp-lock__say")).toContainText("Available with Cedar Press+");
          expect((await locked.locator("thead th").allInnerTexts()).join(" | ").toUpperCase()).toContain("OWNER OR ENTITY");
          expect(await locked.innerText()).not.toMatch(NUMERIC_COUNT);
        }
        const rail = page.locator(".cp-rail__item").filter({ has: page.locator(`text=${id === "plot" ? "PLOT" : "Foundation & Corporate Giving"}`) }).first();
        await expect(rail.locator(".cp-rail__lock")).toHaveText(open ? [] : ["Plus"]);
        expect(errors).toEqual([]);
      });
    }

    test(`the door shows ${id} by what each record holds, with no count`, async ({ page }) => {
      const errors = watchConsole(page);
      await page.goto(`/?collection=${id}`);
      const stage = page.locator(`[data-testid="collection-stage"][data-collection="${id}"]`);
      await expect(stage).toBeVisible();
      await expect(stage.getByTestId("record-structure").locator("tbody tr")).toHaveCount(fields);
      await expect(stage).toContainText("What each record holds");
      await expect(stage).not.toContainText(/not yet published|first release/i);
      await expect(stage.locator(".cp-pane__facts")).not.toContainText(/\d/);
      expect(await stage.innerText()).not.toMatch(NUMERIC_COUNT);
      expect(errors).toEqual([]);
    });
  }

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
    // Every collection on the reader's shelf is included and every one on
    // the Plus shelf is offered, Foundation & Corporate Giving and PLOT like
    // the rest (owner, 2026-09-27). Owned alone is its own state: a release
    // whose sample preview is not published.
    await expect(atlas.locator(".cp-atlas__included")).toHaveCount(
      STOREFRONT_CATALOG.filter((entry) => entry.shelf === "standard").length,
    );
    await expect(atlas.locator(".cp-atlas__locked")).toHaveCount(
      STOREFRONT_CATALOG.filter((entry) => entry.shelf === "pro" && entry.id !== "owned").length,
    );
    await expect(atlas.locator(".cp-atlas__pending")).toHaveCount(1);
    await expect(atlas).not.toContainText(/not yet published|first release/i);
    // Neither states a row count, a span or a version: the cells are empty
    // rather than holding a placeholder.
    for (const name of ["PLOT", "Foundation & Corporate Giving"]) {
      const row = atlas.getByTestId("atlas-row").filter({ has: page.getByRole("button", { name, exact: true }) });
      await expect(row.getByTestId("atlas-rows")).toHaveText("");
      await expect(row.locator("td").nth(1)).toHaveText("");
      await expect(row.locator("td").nth(3)).toHaveText("");
    }
    await expect(page.locator(".cp-ex__pages")).toHaveCount(0);

    await atlas.getByRole("button", { name: "Federal Prime Contracting" }).click();
    await expect(page.getByTestId("explore-locked")).toBeVisible();
    expect(errors).toEqual([]);
  });

  // Owner, 2026-09-27: the viewer page carries no Cedar Grove line under the
  // table, and on a wide window the frame runs the full width.
  test("the viewer runs full width with no Cedar Grove line under it", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop", "a wide-window question");
    const errors = watchConsole(page);
    await page.setViewportSize({ width: 1680, height: 900 });
    await signIn(page);
    await page.goto("/data");
    const frame = page.locator(".cp-ex__frame");
    await expect(frame).toBeVisible({ timeout: 10_000 });
    const box = await frame.boundingBox();
    expect(box.x).toBeLessThanOrEqual(1);
    expect(box.x + box.width).toBeGreaterThanOrEqual(1680 - 20);
    await expect(page.locator("#grove")).toHaveCount(0);
    await expect(page.getByText("brings these collections into a shared workspace")).toHaveCount(0);
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

  // A CARD ON THE DOOR IS STILL A CARD.
  //
  // `Cards` renders the signed-in variant as a `Link` and the signed-out one
  // as a `div`, because a card on the door is the record rather than a way
  // to a page behind the paywall. The one rule that gave a card its layout
  // was written `a.cp-ex__cardbtn`, so the div matched nothing: it stayed
  // `display: block`, its three children are spans, and the entity, the
  // meta line and the observation ran together into one unpadded paragraph.
  // Reported from a phone against the live site.
  //
  // This asserts the READING, not the rule. `display: flex` would pass on a
  // row direction, which is the same illegible result; what a person needs
  // is the meta line starting below the name rather than inside it. Both
  // projects run it: desktop draws `Rows` instead, so it skips there, and
  // the skip is what records that the desktop pass could never have caught
  // this.
  test("a record card on the door stacks rather than running together", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "phone", "the card list is the phone's record surface; desktop renders the table");
    const errors = watchConsole(page);
    await page.goto("/");
    const card = page.locator('[data-testid="stage-record"]').first();
    await card.waitFor();
    const who = card.locator(".cp-ex__cardwho");
    const meta = card.locator(".cp-ex__cardmeta");
    await expect(who).toBeVisible();
    await expect(meta).toBeVisible();
    const [whoBox, metaBox] = [await who.boundingBox(), await meta.boundingBox()];
    expect(whoBox, "the entity block has a box").not.toBeNull();
    expect(metaBox, "the meta line has a box").not.toBeNull();
    // Stacked: the meta line begins at or below where the name block ends.
    // A 1px tolerance for sub-pixel layout, not enough to hide a shared line.
    expect(
      metaBox.y,
      `meta line at y=${metaBox.y} should start below the name block ending at y=${whoBox.y + whoBox.height}`,
    ).toBeGreaterThanOrEqual(whoBox.y + whoBox.height - 1);
    // And the card is padded, which went with the layout when it was lost.
    const padding = await card.locator(".cp-ex__cardbtn").evaluate(
      (node) => getComputedStyle(node).paddingLeft,
    );
    expect(parseFloat(padding)).toBeGreaterThan(0);

    // THE IDENTITY BLOCK STACKS TOO, and it is its own regression: fixing the
    // card's layout left this one live, because `.cp-ex__uid` is a block
    // everywhere except inside a card, where a rule pulled it back inline to
    // save a line. A short council name survives that. A Nation's full legal
    // name does not — the name wrapped, the uid ran on from it, and the uid
    // broke at its own hyphen across two lines ("CE-001C7-" / "AR record
    // names: …"), which is a Nation's name running into its own identifier.
    const idLines = card.locator(".cp-ex__cardwho .cp-ex__uid");
    const idCount = await idLines.count();
    expect(idCount, "the identity block names at least the uid").toBeGreaterThan(0);
    const idBoxes = [];
    for (let i = 0; i < idCount; i += 1) idBoxes.push(await idLines.nth(i).boundingBox());
    // Each line is a line: below the one before it, and below where the name
    // block starts rather than trailing off the end of it.
    expect(idBoxes[0].y).toBeGreaterThan(whoBox.y);
    for (let i = 1; i < idBoxes.length; i += 1) {
      expect(
        idBoxes[i].y,
        `identity line ${i} at y=${idBoxes[i].y} should sit below line ${i - 1} ending at y=${idBoxes[i - 1].y + idBoxes[i - 1].height}`,
      ).toBeGreaterThanOrEqual(idBoxes[i - 1].y + idBoxes[i - 1].height - 1);
    }
    // A block line spans the card; an inline one is only as wide as its text.
    // This is what separates "stacked" from "happened to wrap onto its own
    // line because the name above filled the previous one".
    const cardBox = await card.locator(".cp-ex__cardbtn").boundingBox();
    expect(idBoxes[0].width).toBeGreaterThan(cardBox.width * 0.5);
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
    // Immediately after what it holds: the questions its fields can answer,
    // read from COLLECTION_JOBS rather than typed into the page.
    const asks = panel.locator(".cp-ab__block", { has: page.getByRole("heading", { name: "Questions this collection can help answer" }) });
    await expect(asks).toBeVisible();
    await expect(asks.locator("li")).toHaveText(collectionQuestions("contractors").map((item) => item.q));
    const order = await panel.locator(".cp-ab__h").allInnerTexts();
    expect(order.indexOf("Questions this collection can help answer")).toBe(order.indexOf("What is in this collection") + 1);
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

test.describe("the use cases drive the viewer", () => {
  // The door's collection shelf was replaced by the use-case band
  // (owner, 2026-09-26). The shelf existed because the frame's rail renders at
  // about 0.63 scale, seventeen-pixel rows in six-point type; the band's chips
  // do its job now, and these hold them to everything the shelf's test held
  // it to: every collection reachable, the plan split visible, the selected
  // description shown, the address round-tripping.
  const chips = (page) => page.locator(".cp-aud__panel.is-on .cp-aud__col");

  test("pointing previews, a click commits, and the address round-trips", async ({ page }, testInfo) => {
    const errors = watchConsole(page);
    await page.goto("/");
    await page.locator(".cp-aud").scrollIntoViewIfNeeded();
    const pane = page.locator(".cp-app__pane");
    const note = page.locator(".cp-aud__note");
    const first = STOREFRONT_CATALOG[0];
    await expect(note).toContainText(first.blurb);

    // The first example cites something other than the collection in hand.
    const chip = page.locator(`.cp-aud__panel.is-on .cp-aud__col:not([data-collection="${first.id}"])`).first();
    const id = await chip.getAttribute("data-collection");
    const entry = STOREFRONT_CATALOG.find((e) => e.id === id);
    const before = await pane.innerText();
    if (testInfo.project.name === "desktop") {
      await chip.hover();
      // A preview: the frame and the line follow, the address does not.
      await expect(note).toContainText(entry.blurb);
      await expect(pane).not.toHaveText(before);
      expect(new URL(page.url()).searchParams.get("collection")).toBeNull();
    }
    await chip.click();
    await expect(page).toHaveURL(new RegExp(`[?&]collection=${id}(&|$)`));
    await expect(chip).toHaveAttribute("aria-pressed", "true");
    await expect(note).toContainText(entry.blurb);
    await expect(pane).not.toHaveText(before);
    // A choice inside the band stops it turning.
    await expect(page.locator(".cp-aud")).toHaveAttribute("data-stopped", "true");

    // The address brings the same collection back. The pointer is moved off
    // first: left where the chip was, it rests over the hero rail after the
    // reload, and a rail row under a mouse previews its own collection.
    if (testInfo.project.name === "desktop") await page.mouse.move(2, 2);
    await page.goto(`/?collection=${id}`);
    await expect(page.locator(".cp-aud__note")).toContainText(entry.blurb);
    expect(errors).toEqual([]);
  });

  test("a preview is cleared when hover preview switches off under the pointer", async ({ page }, testInfo) => {
    // PR #131, Codex thread 4113064956: if the preview media flips off (a
    // narrowed window, a pointer change) while a mouse is on a chip, the
    // leave that follows was guarded on the *current* media and skipped its
    // clear, so the frame kept a collection the address does not name.
    // The fine-pointer query is flipped directly, with no layout change, so
    // the chip stays under the pointer and nothing else can clear it.
    test.skip(testInfo.project.name !== "desktop", "hover preview exists on desktop only");
    await page.addInitScript(() => {
      const real = window.matchMedia.bind(window);
      const listeners = new Set();
      let fine = true;
      window.__setFinePointer = (on) => {
        fine = on;
        for (const fn of listeners) fn({ matches: fine });
      };
      window.matchMedia = (query) => {
        if (!query.includes("pointer: fine")) return real(query);
        return {
          get matches() { return fine; },
          media: query,
          addEventListener: (_type, fn) => listeners.add(fn),
          removeEventListener: (_type, fn) => listeners.delete(fn),
          addListener: (fn) => listeners.add(fn),
          removeListener: (fn) => listeners.delete(fn),
        };
      };
    });
    await page.goto("/");
    await page.locator(".cp-aud").scrollIntoViewIfNeeded();
    const note = page.locator(".cp-aud__note");
    const first = STOREFRONT_CATALOG[0];
    await expect(note).toContainText(first.blurb);
    const chip = page.locator(`.cp-aud__panel.is-on .cp-aud__col:not([data-collection="${first.id}"])`).first();
    const id = await chip.getAttribute("data-collection");
    const entry = STOREFRONT_CATALOG.find((e) => e.id === id);
    await chip.hover();
    await expect(note).toContainText(entry.blurb);
    await page.evaluate(() => window.__setFinePointer(false));
    const box = await page.locator(".cp-aud").boundingBox();
    // Inside the band, outside the chip list: the hero rail also sets the
    // preview on hover, so leaving through it would mask the bug.
    await page.mouse.move(box.x + 2, box.y + 2);
    await expect(note).toContainText(first.blurb);
    expect(new URL(page.url()).searchParams.get("collection")).toBeNull();
  });

  test("every collection a use case names is reachable through it, at this width", async ({ page }, testInfo) => {
    // Run on both projects: on the phone (390 wide) this is the answer to "how
    // does a visitor reach a collection from a use case": pick one in the
    // scrolling selector, then tap one of its chips. Whether EVERY live
    // collection is named by some use case is a review report, not a rule
    // (owner, 2026-09-26): it is attached to this test as an annotation.
    await page.goto("/");
    await page.locator(".cp-aud").scrollIntoViewIfNeeded();
    const reached = new Set();
    const tabs = page.locator(".cp-aud__tab");
    const count = await tabs.count();
    for (let i = 0; i < count; i += 1) {
      await tabs.nth(i).click();
      const visible = chips(page);
      const n = await visible.count();
      for (let j = 0; j < n; j += 1) {
        const chip = visible.nth(j);
        const id = await chip.getAttribute("data-collection");
        if (reached.has(id)) continue;
        await chip.click();
        await expect(page).toHaveURL(new RegExp(`[?&]collection=${id}(&|$)`));
        reached.add(id);
      }
    }
    const named = new Set(visibleAudiences().flatMap((audience) => audience.collections.map((entry) => entry.id)));
    expect([...reached].sort()).toEqual([...named].sort());
    const uncovered = uncoveredIds();
    testInfo.annotations.push({ type: "coverage report", description: uncovered.length ? `not named by any use case: ${uncovered.join(", ")}` : "every live collection is named by some use case" });
  });

  test("the plan split is on the chips and in the line under them", async ({ page }) => {
    await page.goto("/");
    const all = page.locator(".cp-aud__col");
    const shelves = await all.evaluateAll((els) => els.map((el) => [el.dataset.shelf, Boolean(el.querySelector(".cp-plus"))]));
    expect(shelves.length).toBeGreaterThan(0);
    for (const [shelf, plus] of shelves) expect(plus, `a ${shelf} chip`).toBe(shelf === "pro");
    const pro = STOREFRONT_CATALOG.find((entry) => entry.shelf === "pro");
    await page.goto(`/?collection=${pro.id}`);
    await expect(page.locator(".cp-aud__meta")).toContainText("Cedar Press");
    await expect(page.locator(".cp-aud__meta .cp-plus")).toHaveCount(1);
  });

  test("the rotation never changes the collection in hand, and the note follows the card", async ({ page }) => {
    await page.clock.install();
    await page.goto("/");
    await page.locator(".cp-aud").evaluate((el) => el.scrollIntoView({ block: "center", behavior: "instant" }));
    if (!test.info().project.use.hasTouch) await page.mouse.move(2, 2);
    // Turning before the clock is advanced: the band starts once it is seen
    // on screen, which is an observer callback, not a timer.
    await expect(page.locator(".cp-aud")).toHaveAttribute("data-rotating", "true");
    const pane = page.locator(".cp-app__pane");
    const before = await pane.innerText();
    const url = page.url();
    await page.clock.runFor(40_000);
    await expect(page.locator(".cp-aud__count")).not.toHaveText(/^01 \//);
    // The frame and the address keep the collection in hand...
    expect(await pane.innerText()).toBe(before);
    expect(page.url()).toBe(url);
    // ...and the line under the card describes a collection the card shows.
    const onCard = await page.locator(".cp-aud__panel.is-on .cp-aud__col").evaluateAll((els) => els.map((el) => el.dataset.collection));
    expect(onCard).toContain(await page.locator(".cp-aud__note").getAttribute("data-collection"));
  });

  test("the note never describes a collection the card does not show", async ({ page }) => {
    await page.goto("/");
    await page.locator(".cp-aud").evaluate((el) => el.scrollIntoView({ block: "center", behavior: "instant" }));
    const note = page.locator(".cp-aud__note");
    const tabs = page.locator(".cp-aud__tab");
    const count = await tabs.count();
    for (let i = 0; i < count; i += 1) {
      await tabs.nth(i).click();
      const onCard = await page.locator(".cp-aud__panel.is-on .cp-aud__col").evaluateAll((els) => els.map((el) => el.dataset.collection));
      const described = await note.getAttribute("data-collection");
      expect(onCard, `use case ${i + 1}`).toContain(described);
      const entry = STOREFRONT_CATALOG.find((e) => e.id === described);
      await expect(note).toContainText(entry.blurb);
    }
    // A collection picked in the hero frame that this card does not name is
    // not described under it: the card's first chip is.
    const last = page.locator(".cp-aud__panel.is-on .cp-aud__col");
    const shown = await last.evaluateAll((els) => els.map((el) => el.dataset.collection));
    const elsewhere = STOREFRONT_CATALOG.find((entry) => !shown.includes(entry.id));
    await page.goto(`/?collection=${elsewhere.id}`);
    await page.locator(".cp-aud").evaluate((el) => el.scrollIntoView({ block: "center", behavior: "instant" }));
    await page.locator(".cp-aud__tab").nth(count - 1).click();
    await expect(note).toHaveAttribute("data-collection", shown[0]);
  });
});

test.describe("the door's use cases", () => {
  // One audience at a time, under the hero (PressAudienceExample). The rules
  // are held in milliseconds by pressRotation.test.js; these check that the
  // built page actually obeys them. The clock is Playwright's, so eight
  // seconds of rotation cost nothing.
  const band = (page) => page.locator(".cp-aud");
  const counter = (page) => page.locator(".cp-aud__count");

  async function reach(page) {
    // Instant, not the page's smooth scroll: with Playwright's clock installed
    // a smooth scroll never finishes, and the band never comes on screen.
    await band(page).evaluate((el) => el.scrollIntoView({ block: "center", behavior: "instant" }));
    await expect(band(page)).toBeVisible();
    // Seen, by the band's own observer, before any clock is advanced; under
    // reduced motion it is seen and still does not turn.
    await expect.poll(() => band(page).evaluate((el) => el.dataset.rotating === "true" || matchMedia("(prefers-reduced-motion: reduce)").matches)).toBe(true);
    // Off the band, so a fine pointer is not resting on it and pausing it.
    if (!test.info().project.use.hasTouch) await page.mouse.move(2, 2);
  }

  test("shows one example, from the catalog, and never an unreleased collection", async ({ page }) => {
    const errors = watchConsole(page);
    await page.goto("/");
    await reach(page);
    const shown = await page.locator(".cp-aud__panel").count();
    await expect(counter(page)).toHaveText(`01 / ${String(shown).padStart(2, "0")}`);
    await expect(page.locator(".cp-aud__panel.is-on")).toHaveCount(1);
    await expect(page.locator(".cp-aud__tab")).toHaveCount(shown);
    // Every collection named in the band is one the strip below sells.
    const cited = await page.locator(".cp-aud__col").evaluateAll((els) => [...new Set(els.map((el) => el.dataset.collection))]);
    const sold = new Set(STOREFRONT_CATALOG.map((entry) => entry.id));
    for (const id of cited) expect(sold.has(id), `${id} is not a live collection`).toBe(true);
    // Every declared use case, counted from the layer rather than typed:
    // Foundations and philanthropy and the government audience among them,
    // and the two newest collections on the chips the owner wrote them into.
    expect(shown).toBe(AUDIENCE_JOBS.length);
    await expect(counter(page)).toHaveText(`01 / ${String(AUDIENCE_JOBS.length).padStart(2, "0")}`);
    for (const id of ["foundations-philanthropy", "government-officials", "advisors"]) {
      await expect(page.locator(`.cp-aud__panel[data-audience="${id}"]`)).toHaveCount(1);
    }
    for (const id of ["plot", "foundation-corporate-giving"]) expect(cited, id).toContain(id);
    expect(errors).toEqual([]);
  });

  test("it turns slowly, a choice holds it, and it turns again once the visitor is idle", async ({ page }, testInfo) => {
    await page.clock.install();
    await page.goto("/");
    await reach(page);
    await expect(counter(page)).toHaveText(/^01 \//);
    await page.clock.runFor(8_100);
    await expect(counter(page)).toHaveText(/^02 \//);

    if (testInfo.project.name === "desktop") {
      // Hovered, it holds; released, it carries on.
      await band(page).hover();
      await page.clock.runFor(20_000);
      await expect(counter(page)).toHaveText(/^02 \//);
      await page.mouse.move(2, 2);
      await page.clock.runFor(8_100);
      await expect(counter(page)).toHaveText(/^03 \//);
    }

    const tab = page.locator(".cp-aud__tab").nth(4);
    await tab.click();
    await expect(tab).toHaveAttribute("aria-selected", "true");
    await expect(counter(page)).toHaveText(/^05 \//);
    await expect(band(page)).toHaveAttribute("data-stopped", "true");
    // Playwright's click is a mouse click on the phone project too, and the
    // pointer would stay over the band and hold it; a finger leaves nothing
    // hovering, so the pointer is moved off in both projects.
    await page.mouse.move(2, 2);
    await page.locator(".cp-aud__tab").nth(4).evaluate((el) => el.blur());
    // Held while the visitor is still about (under twelve seconds)...
    await page.clock.runFor(11_000);
    await expect(counter(page)).toHaveText(/^05 \//);
    // ...then it turns again, one step at a time.
    await page.clock.runFor(1_100);
    await expect(band(page)).toHaveAttribute("data-stopped", "false");
    await page.clock.runFor(8_100);
    await expect(counter(page)).toHaveText(/^06 \//);
  });

  test("under reduced motion it never cycles", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.clock.install();
    await page.goto("/");
    await reach(page);
    await expect(band(page)).toHaveAttribute("data-rotating", "false");
    await page.clock.runFor(60_000);
    await expect(counter(page)).toHaveText(/^01 \//);
    // The controls still work: reduced motion removes the cycling, not the choice.
    await page.getByRole("button", { name: "Next use case" }).click();
    await expect(counter(page)).toHaveText(/^02 \//);
  });

  test("changing the example does not move the page", async ({ page }, testInfo) => {
    // Above 720 wide. On a phone each card takes its own height (the test
    // below), so a shorter card does not stand over a block of empty card.
    test.skip(testInfo.project.name === "phone", "on a phone each card is its own height");
    await page.goto("/");
    await reach(page);
    // Page coordinates, not viewport ones: a click may scroll the window, and
    // that is not the layout moving.
    // Layout offsets, not rects: the sections below arrive with a `.cp-fade`
    // rise, and a transform mid-reveal is not the layout moving.
    const measure = () => page.evaluate(() => {
      const top = (sel) => {
        let y = 0;
        for (let node = document.querySelector(sel); node; node = node.offsetParent) y += node.offsetTop;
        return y;
      };
      return { height: document.querySelector(".cp-aud").offsetHeight, below: top(".cp-hero3__proof") };
    });
    const before = await measure();
    const total = await page.locator(".cp-aud__panel").count();
    for (let i = 0; i < total; i += 1) {
      await page.getByRole("button", { name: "Next use case" }).click();
      const now = await measure();
      expect(Math.abs(now.height - before.height), "band height").toBeLessThan(0.5);
      expect(Math.abs(now.below - before.below), "the band below it").toBeLessThan(0.5);
    }
  });

  test("on a phone each card is its own height, with no empty block under the chips", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "phone", "a phone layout");
    await page.goto("/");
    await reach(page);
    const total = await page.locator(".cp-aud__panel").count();
    for (let i = 0; i < total; i += 1) {
      await page.locator(".cp-aud__tab").nth(i).click();
      const gap = await page.locator(".cp-aud__panel.is-on").evaluate((panel) => {
        const chips = panel.querySelector(".cp-aud__cols").getBoundingClientRect();
        return panel.getBoundingClientRect().bottom - chips.bottom;
      });
      // The text's own bottom padding, and no more.
      expect(gap, `use case ${i + 1}`).toBeLessThan(24);
    }
  });

  // At most two lines above 1100; at or below it, one row that scrolls
  // sideways inside itself while the page does not. The phone project
  // measures 390 on its own viewport.
  test("the audience names are one row until there is room for two lines", async ({ page }, testInfo) => {
    const widths = testInfo.project.name === "desktop" ? [1440, 1040, 720] : [null];
    for (const width of widths) {
      if (width) await page.setViewportSize({ width, height: 900 });
      await page.goto("/");
      const at = width ?? page.viewportSize().width;
      const lines = await page.locator(".cp-aud__tab").evaluateAll((tabs) => new Set(tabs.map((tab) => Math.round(tab.getBoundingClientRect().top))).size);
      expect(lines, `at ${at}`).toBeLessThanOrEqual(at > 1100 ? 2 : 1);
      if (at <= 1100) {
        const row = await page.locator(".cp-aud__tabs").evaluate((el) => ({ scroll: el.scrollWidth, client: el.clientWidth, overflow: getComputedStyle(el).overflowX }));
        expect(row.overflow, `the row scrolls at ${at}`).toBe("auto");
        expect(row.scroll, `the names overflow the row at ${at}, so it scrolls`).toBeGreaterThan(row.client);
      }
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow, `the page scrolls sideways at ${at}`).toBeLessThanOrEqual(0);
    }
  });

  // The government card carries the longest headline the band has. It must
  // fit its card at every width: nothing clipped, nothing spilling, and on a
  // phone the card is its own height (the test above checks the gap).
  test("the longest headline fits its card at every width", async ({ page }, testInfo) => {
    const widths = testInfo.project.name === "desktop" ? [1440, 1040, 720] : [null];
    const index = visibleAudiences().findIndex((audience) => audience.id === "government-officials");
    expect(index).toBeGreaterThanOrEqual(0);
    for (const width of widths) {
      if (width) await page.setViewportSize({ width, height: 900 });
      await page.goto("/");
      await band(page).evaluate((el) => el.scrollIntoView({ block: "center", behavior: "instant" }));
      await page.locator(".cp-aud__tab").nth(index).click();
      const panel = page.locator('.cp-aud__panel.is-on[data-audience="government-officials"]');
      await expect(panel).toHaveCount(1);
      const fit = await panel.evaluate((el) => {
        const box = el.getBoundingClientRect();
        const stack = el.closest(".cp-aud__stack").getBoundingClientRect();
        const parts = [...el.querySelectorAll(".cp-aud__outcome, .cp-aud__use, .cp-aud__cols")].map((node) => ({
          name: node.className,
          right: node.getBoundingClientRect().right,
          bottom: node.getBoundingClientRect().bottom,
          clipped: node.scrollWidth > node.clientWidth + 1 || node.scrollHeight > node.clientHeight + 1,
        }));
        return { right: Math.min(box.right, stack.right), bottom: Math.min(box.bottom, stack.bottom), parts };
      });
      for (const part of fit.parts) {
        expect(part.clipped, `${part.name} is clipped at ${width ?? "phone"}`).toBe(false);
        expect(part.right, `${part.name} spills right at ${width ?? "phone"}`).toBeLessThanOrEqual(fit.right + 0.5);
        expect(part.bottom, `${part.name} spills below the card at ${width ?? "phone"}`).toBeLessThanOrEqual(fit.bottom + 0.5);
      }
    }
  });

  test("on a phone the facts keep one line each and the launcher waits past the first screen and the use cases", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "phone", "a phone layout");
    await page.goto("/");
    const heights = await page.locator(".cp-hero3__facts li").evaluateAll((items) => items.map((li) => li.getBoundingClientRect().height));
    const one = Math.min(...heights);
    for (const h of heights) expect(h).toBeLessThan(one * 1.5);
    await expect(page.locator(".cp-dc__fab")).toBeHidden();
    // Nor over the use cases, whose card and note run to the screen's edge.
    await page.locator(".cp-aud").evaluate((el) => el.scrollIntoView({ block: "center", behavior: "instant" }));
    await expect(page.locator(".cp-dc__fab")).toBeHidden();
    // From the navy passage down it is back.
    await page.locator(".cp-why").evaluate((el) => el.scrollIntoView({ block: "start", behavior: "instant" }));
    await expect(page.locator(".cp-dc__fab")).toBeVisible();
  });

  test("the partners are named on the first screen, and each name links to its site", async ({ page }) => {
    await page.goto("/");
    const line = page.locator(".cp-hero3__by");
    await expect(line).toHaveText("Built by Lumecon in partnership with Tribal Business News.");
    await expect(line.getByRole("link", { name: "Lumecon" })).toHaveAttribute("href", LUMECON_URL);
    await expect(line.getByRole("link", { name: "Tribal Business News" })).toHaveAttribute("href", TBN_URL);
    // Teal text is --dteal (#0A7F74), and the door's own `a { color: inherit }`
    // must not win over it.
    await expect(line.getByRole("link", { name: "Lumecon" })).toHaveCSS("color", "rgb(10, 127, 116)");
  });

  // THE PREVIEW LOGIN. The named reviewer at Indian Country Media signs in to
  // the standalone preview through this door's "Log in" tab, with an account
  // the deploy provisions from a repository secret (pressDemoGate.test.js
  // holds that wiring). This is the same path with the suite's own Cedar
  // Press account, after the band was added above the strip: the door still
  // opens the form and the form still lets the reviewer in.
  test("the preview login still signs a Cedar Press reader in through the door", async ({ page }) => {
    const errors = watchConsole(page);
    await page.goto("/");
    await expect(band(page)).toHaveCount(1);
    await signIn(page, PRESS_ACCOUNT);
    await expect(page.locator(".cp-aud")).toHaveCount(0);
    expect(errors).toEqual([]);
  });
});

test.describe("the use-case card", () => {
  // Owner's brief, 2026-09-26, second pass: an outcome as the headline, what
  // Cedar Press lets the audience understand, the collections as chips, and
  // a duotone sector photograph as a panel of the card.
  const band = (page) => page.locator(".cp-aud");
  const on = (page) => page.locator(".cp-aud__panel.is-on");

  test("leads with the outcome and the job, with no quiet line under it", async ({ page }) => {
    const errors = watchConsole(page);
    await page.goto("/");
    await band(page).evaluate((el) => el.scrollIntoView({ block: "center", behavior: "instant" }));
    const first = AUDIENCE_JOBS[0];
    await expect(on(page).locator(".cp-aud__outcome")).toHaveText(first.outcome);
    await expect(on(page).locator(".cp-aud__job")).toHaveText(first.job);
    // The quiet line under the band was removed (owner, 2026-09-27).
    await expect(page.locator(".cp-aud__quiet")).toHaveCount(0);
    await expect(page.locator("body")).not.toContainText("not rebuilding public data");
    expect(errors).toEqual([]);
  });

  test("the photograph is a lazy panel with a responsive source, and it lands", async ({ page }, testInfo) => {
    await page.goto("/");
    // Before the band is reached, only the first use case holds a photograph,
    // and it is lazy: a visitor who never scrolls here downloads none.
    const imgs = page.locator(".cp-aud__media img");
    await expect(imgs).toHaveCount(1);
    await expect(imgs.first()).toHaveAttribute("loading", "lazy");
    await expect(imgs.first()).toHaveAttribute("srcset", /-sm\.webp 600w, .*\.webp 1200w/);
    await expect(page.locator(".cp-aud__media source")).toHaveAttribute("srcset", /-wide\.webp \d+w/);
    await band(page).evaluate((el) => el.scrollIntoView({ block: "center", behavior: "instant" }));
    const img = on(page).locator(".cp-aud__media img");
    await expect.poll(() => img.evaluate((el) => el.complete && el.naturalWidth > 0)).toBe(true);
    // The photograph fills its panel and the panel is the card's own height.
    // All three boxes in one read: the section's fade-in rise moves the band
    // between separate reads, which is not the layout.
    const boxes = () => on(page).evaluate((panel) => {
      const box = (sel) => { const r = panel.querySelector(sel).getBoundingClientRect(); return { x: r.x, y: r.y, width: r.width, height: r.height }; };
      return { media: box(".cp-aud__media"), shot: box(".cp-aud__media img"), text: box(".cp-aud__text") };
    });
    await page.waitForTimeout(600);
    const { media, shot, text } = await boxes();
    expect(Math.abs(media.height - shot.height)).toBeLessThan(1);
    expect(Math.abs(media.width - shot.width)).toBeLessThan(1);
    if (testInfo.project.name === "phone") {
      // A banner on top, at 5:2.
      expect(Math.abs(media.width / media.height - 2.5)).toBeLessThan(0.05);
      expect(media.y + media.height).toBeLessThanOrEqual(text.y + 1);
    } else {
      // Beside the text, and the side alternates from one use case to the next.
      expect(media.x + media.width).toBeLessThanOrEqual(text.x + 1);
      await page.getByRole("button", { name: "Next use case" }).click();
      await expect.poll(async () => (await boxes()).shot.width).toBeGreaterThan(0);
      const next = await boxes();
      expect(next.text.x + next.text.width).toBeLessThanOrEqual(next.media.x + 1);
    }
  });

  test("a use case shows the next photograph in its pool on each visit", async ({ page }) => {
    await page.goto("/");
    await band(page).evaluate((el) => el.scrollIntoView({ block: "center", behavior: "instant" }));
    const pool = AUDIENCE_JOBS[0].imagePool;
    const shown = () => on(page).locator(".cp-aud__media img").getAttribute("data-image");
    await expect.poll(shown).toBe(pool[0]);
    await page.getByRole("button", { name: "Next use case" }).click();
    await page.getByRole("button", { name: "Previous use case" }).click();
    await expect.poll(shown).toBe(pool[1]);
  });
});

test.describe("the product copy reads the jobs layer", () => {
  test("the signed-in homepage, its briefing, and the entity page's actions", async ({ page }) => {
    const errors = watchConsole(page);
    await signIn(page);
    await expect(page.locator(".cp-hero__deck")).toHaveText(
      "Compare peers, follow funding and business activity, spot changes worth investigating and trace the evidence behind them.",
    );
    const caps = await page.locator(".cp-brief__cap").allInnerTexts();
    expect(caps.map((c) => c.toLowerCase())).toEqual(expect.arrayContaining(["what changed", "explore the records"]));
    expect(caps.join(" ")).not.toMatch(/worth watching|open today|insight|opportunit/i);

    await page.goto("/data?c=funding");
    await page.getByTestId("explore-record").first().locator("a").first().click();
    await page.waitForURL(/\/record\?/);
    await page.locator(".cp-rec__name a").first().click();
    await page.waitForURL(/\/entity\/CE-/);
    const head = page.getByTestId("entity-head");
    await expect(head.locator(".cp-ent__line")).toHaveText(ENTITY_JOBS.line);
    // Only what works today: no dead button for the two that are not built.
    for (const action of ENTITY_JOBS.actions.filter((a) => !a.available)) {
      await expect(page.getByRole("link", { name: action.label })).toHaveCount(0);
      await expect(page.getByRole("button", { name: action.label })).toHaveCount(0);
    }
    const overTime = head.locator('[data-action="over-time"]');
    await expect(overTime).toHaveAttribute("href", /\?e=CE-[^&]+&s=date:asc$/);
    await overTime.click();
    await page.waitForURL(/s=date(%3A|:)asc/);
    await expect(page.getByTestId("explore-record").first()).toBeVisible();
    expect(errors).toEqual([]);
  });

  test("Research access shows the owner's two examples, from the layer", async ({ page }) => {
    await page.goto("/research-access");
    const fit = page.locator(".cp-fit__side--yes p");
    await expect(fit).toHaveText(researchExamples().map((example) => example.text));
    await expect(page.locator(".cp-trh__sub")).toContainText("without rebuilding the underlying collection yourself");
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
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Help set the research agenda.");
    // Points inform the agenda and do not decide it, said in the deck itself.
    await expect(page.locator(".cp-mh__sub")).toContainText("do not decide it");
    // The owner's examples, visibly examples and not a roadmap, with causal
    // research questions told apart from descriptive ones.
    const examples = page.getByTestId("priority-examples");
    await expect(examples).toContainText("Examples, not a roadmap");
    await expect(examples.locator(".cp-pri__exkind")).toHaveCount(2);
    await expect(examples.locator(".cp-pri__exkind").nth(1)).toContainText("Causal");
    // The narrower asks are smaller than the ambitious ones.
    const small = await examples.locator(".cp-pri__exsmall li").first().evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
    const lead = await examples.locator(".cp-pri__exlist li").first().evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
    expect(small).toBeLessThan(lead);
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

    // This build is standalone: nothing reaches the collections. The
    // composer is disabled, and so are the starters, which used to render
    // scoped chips whose every tap became a NOT_CONNECTED error turn.
    await expect(panel.locator(".cp-dc__input")).toBeDisabled();
    await expect(panel.locator(".cp-dc__chip")).toHaveCount(0);
    await expect(panel.locator(".cp-dc__bubble").first()).toContainText("can't reach the collections");

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

test.describe("the Cedar panel is the site's panel", () => {
  // THE OWNER PUT THE TWO SIDE BY SIDE. "The website chat we have for cedar
  // is better and not as wide as it is for cedar press." So the Press panel
  // is now lumecon.ai's panel, and this holds it there by measurement rather
  // than by reading the stylesheet.
  //
  // The numbers are the site's, measured off its built page on 2026-09-23
  // (`CedarFAB.astro`'s `.cedar-fab-panel` with `cedar-chat.css`): at 1280,
  // 1440 and 1920 wide by 900 high the open panel is 380 x 577.88 with 24px
  // to the window's right edge and none to its bottom; the transcript sits
  // at its 400px cap. The height is 1px of border, a 66.77px header, the
  // 400px transcript, a 67.39px composer and a three-line note of 42.72px,
  // so a note that wraps to four lines is the one thing that moves it, and
  // this would name it.
  const SITE = { width: 380, height: 577.88, rightGap: 24, bottomGap: 0 };
  const TOLERANCE = 2;

  const measure = async (panel, page) => {
    await settled(panel);
    const box = await panel.boundingBox();
    const viewport = page.viewportSize();
    return { width: box.width, height: box.height, rightGap: viewport.width - (box.x + box.width), bottomGap: viewport.height - (box.y + box.height) };
  };
  const expectSite = (got) => {
    for (const key of Object.keys(SITE)) {
      expect(Math.abs(got[key] - SITE[key]), `${key}: ${got[key]} against the site's ${SITE[key]}`).toBeLessThanOrEqual(TOLERANCE);
    }
  };

  for (const width of [1280, 1440, 1920]) {
    test(`at ${width} wide the door's panel measures the site's`, async ({ page }, testInfo) => {
      test.skip(testInfo.project.name !== "desktop", "a desktop layout question");
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/");
      await page.evaluate(() => document.fonts.ready);
      await page.locator(".cp-hero3__proof").scrollIntoViewIfNeeded();
      await page.mouse.wheel(0, 1400);
      await page.locator(".cp-dc__fab").click();
      const panel = page.locator(".cp-dc__panel");
      expectSite(await measure(panel, page));
      // And after an exchange: the site's transcript is at its cap by then,
      // and this one does not grow on the first answer.
      await page.locator(".cp-dc__chip").first().click();
      await expect(page.locator(".cp-dc__msg--bot:not([aria-hidden])").nth(1)).toBeVisible();
      expectSite(await measure(panel, page));
    });

    test(`at ${width} wide the reader's panel measures the site's`, async ({ page }, testInfo) => {
      test.skip(testInfo.project.name !== "desktop", "a desktop layout question");
      await page.setViewportSize({ width, height: 900 });
      await signIn(page);
      await page.evaluate(() => document.fonts.ready);
      // The widget is a child of the page's entering `main`, whose transform
      // is its fixed descendants' containing block for the 340ms it runs.
      await page.waitForFunction(() => {
        const box = document.querySelector(".cedar-widget__launcher")?.getBoundingClientRect();
        return Boolean(box) && box.bottom <= innerHeight && box.top >= 0;
      });
      await page.locator(".cedar-widget__launcher").click();
      const panel = page.getByRole("dialog", { name: /ask cedar/i });
      expectSite(await measure(panel, page));
    });
  }

  // The door reads as a conversation: it remembers the last topic, goes
  // deeper on it when asked, and when it has nothing for a question it says
  // so and offers the closest things it can speak to. Before this it refused
  // "tell me more" as a question it had nothing for, and every miss printed
  // the same sentence.
  test("the door keeps the thread: a follow-up goes deeper and a miss offers the closest topics", async ({ page }) => {
    const errors = watchConsole(page);
    await page.goto("/");
    await page.locator(".cp-hero3__proof").scrollIntoViewIfNeeded();
    await page.mouse.wheel(0, 1400);
    await page.locator(".cp-dc__fab").click();
    const answered = page.locator(".cp-dc__msg--bot:not([aria-hidden])");
    const ask = async (text) => {
      const before = await answered.count();
      await page.locator(".cp-dc__input").fill(text);
      await page.locator(".cp-dc__send").click();
      await expect(answered).toHaveCount(before + 1);
      return answered.last();
    };

    await expect(await ask("what is in the deals collection")).toContainText("It is included in Cedar Press");
    // The starters are gone; the next questions ride under the answer, and
    // the first of them is the way deeper.
    await expect(page.locator(".cp-dc__chip")).toHaveCount(0);
    const more = page.locator(".cp-dc__follow", { hasText: "Tell me more" });
    await expect(more).toBeVisible();
    await more.click();
    await expect(page.locator(".cp-dc__msg--you").last()).toContainText("Tell me more");
    await expect(answered.last()).toContainText("Going deeper on how Deals is built");
    // Deeper is not offered twice.
    await expect(page.locator(".cp-dc__follow", { hasText: "Tell me more" })).toHaveCount(0);

    const miss = await ask("what is the weather in Oslo");
    await expect(miss).toContainText("I do not have that one here on the front page");
    await expect(miss).toContainText("closest things I can speak to");
    const offered = page.locator(".cp-dc__follow");
    await expect(offered.first()).toBeVisible();
    expect(await offered.count()).toBeLessThanOrEqual(3);
    // The note under the composer is the site's, not a description of the
    // machinery.
    await expect(page.locator(".cp-dc__disclaimer")).toContainText("Verify important details");
    await expect(page.locator(".cp-dc__disclaimer")).not.toContainText("prepared");
    expect(errors).toEqual([]);
  });

  // A page-level "Ask Cedar about this collection" while a turn is still
  // composing (the pause runs up to 1.6s) replaces that turn. It used to be
  // dropped at the hook's one-at-a-time guard: the panel reopened, the
  // collection question never appeared, and the earlier answer landed instead.
  test("a collection asked for while the door is composing replaces the turn in flight", async ({ page }) => {
    const errors = watchConsole(page);
    await page.goto("/");
    await page.locator(".cp-hero3__proof").scrollIntoViewIfNeeded();
    await page.mouse.wheel(0, 1400);
    await page.locator(".cp-dc__fab").click();
    await page.locator(".cp-dc__input").fill("what is nagpra");
    await page.locator(".cp-dc__send").click();
    await expect(page.locator(".cp-dc__bubble--typing")).toBeVisible();
    // Mid-pause: close, then ask for a collection from the page.
    await page.locator(".cp-dc__close").click();
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent("cedar:ask-collection", { detail: { id: "deals", name: "Deals in Indian Country" } }));
    });
    const answered = page.locator(".cp-dc__msg--bot:not([aria-hidden])");
    await expect(page.locator(".cp-dc__msg--you").last()).toContainText("What is in Deals in Indian Country?");
    await expect(answered.last()).toContainText("It is included in Cedar Press");
    await expect(answered.last()).not.toContainText("Notices of Inventory Completion");
    // The replaced turn's answer never lands, even after its pause would have ended.
    await page.waitForTimeout(1800);
    await expect(answered).toHaveCount(2);
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
  //   1. WITHDRAWN. "Native Federal Advocacy & Engagement" was exempted
  //      here as a COLLECTION NAME out of the release manifest, on the
  //      reasoning that rewriting it in the product would make the product
  //      disagree with the release. The collection was then renamed at the
  //      source — the manifest, the catalog, the descriptors and Grove all
  //      say "and" now — so the exemption stopped protecting a name and
  //      started hiding a straggler: `code/1176_build_review_artifact.py`
  //      was still writing the ampersand into the downloadable review page,
  //      and this test was told not to look. The lesson is that an exemption
  //      for a generated value has to be withdrawn when the value changes,
  //      or the rule quietly stops being a rule.
  //   2. "Quechan Tribe of the Fort Yuma Indian Reservation, California &
  //      Arizona" is a CANONICAL ENTITY NAME from the register — the tribe's
  //      name as the federal record states it. Editing a Nation's legal name
  //      to satisfy a house style is not a copy fix; it is the product
  //      asserting something the source does not say, which is the one thing
  //      the whole identity layer exists to prevent.
  //
  //   3. "Foundation & Corporate Giving" is a COLLECTION NAME the owner keeps
  //      with its ampersand (2026-09-27). It is exempted by exact name, not by
  //      selector: the name is removed from the text before the check, so the
  //      same line carrying any other ampersand still fails, and a variant
  //      spelling ("Foundation &amp; Corporate Giving" rendered literally, or
  //      "Foundations & Corporate Giving") is not exempt.
  //
  // So the table and the register's name cells are excluded by selector,
  // which keeps the rule enforceable as new names arrive rather than needing
  // a string added here every time one does.
  // `.cp-ex__cards` is the phone's record surface — the same rows the desktop
  // draws as a table. Missing it was the whole reason this test failed on the
  // phone project and passed on desktop, which is a useful reminder that
  // "visible copy" is per-composition, not per-page.
  /**
   * The one collection name allowed its ampersand (exemption 3 above). The
   * only tolerance is whitespace after the ampersand, because the Methods
   * ring sets a long name on two SVG lines ("Foundation &" / "Corporate
   * Giving") and the text of two <tspan>s joins with no space between them.
   */
  // S&P is a company's legal name (the ratings source on the door's banner).
  const AMPERSAND_EXEMPT = /Foundation &\s*Corporate Giving|\bS&P\b/g;

  const QUOTED = [
    ".cp-ex__table",
    ".cp-ex__cards",
    ".cp-pane__table",
    ".cp-ex__lname",
    ".cp-ex__uid",
    ".cp-rec",
    ".cp-ent",
  ].join(", ");

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
      const offending = text
        .split("\n")
        .map((line) => line.trim().replaceAll(AMPERSAND_EXEMPT, ""))
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

  // Foundation & Corporate Giving and PLOT are published and live (owner,
  // 2026-09-27): no page, prerendered route, SEO text or door answer in the
  // build calls anything "not yet published", or waits on a first release.
  test("says nothing is not yet published", async () => {
    const dir = fileURLToPath(new URL("../dist-site/", import.meta.url));
    const assets = await readdir(dir, { recursive: true, withFileTypes: true });
    const files = assets.filter((entry) => entry.isFile() && /\.(js|html|json|xml|txt)$/.test(entry.name));
    expect(files.length, "nothing was built to check").toBeGreaterThan(0);
    for (const entry of files) {
      const body = await readFile(`${entry.parentPath}/${entry.name}`, "utf8");
      expect(body, `${entry.name} says "not yet published"`).not.toMatch(/not yet published/i);
      expect(body, `${entry.name} waits on a first release`).not.toMatch(/with (its|their) first release/i);
    }
  });

  // BOTH NEW COLLECTIONS ARE IN THE BUILD.
  //
  // Foundation & Corporate Giving and PLOT were held out of the bundle while
  // they were gated: this test used to prove every string about them was
  // ABSENT from dist-site. The owner made them part of Cedar Press on
  // 2026-09-27, so the proof runs the other way: their ids, names, owner
  // descriptions, profile questions, the owner's use-case sentences that
  // name them and the path data of both marks must all be PRESENT in what
  // the production build emitted. A collection that renders on a developer's
  // machine and is missing from the build fails here.
  test("carries both new collections, their questions, sentences and marks", async () => {
    const dir = fileURLToPath(new URL("../dist-site/", import.meta.url));
    const assets = await readdir(dir, { recursive: true, withFileTypes: true });
    const files = assets.filter((entry) => entry.isFile() && /\.(js|css|html|json|map|xml|txt)$/.test(entry.name));
    expect(files.length, "nothing was built to check").toBeGreaterThan(0);
    const bodies = await Promise.all(files.map((entry) => readFile(`${entry.parentPath}/${entry.name}`, "utf8")));
    const build = bodies.join("\n");

    const ids = ["plot", "foundation-corporate-giving"];
    const needles = [];
    for (const id of ids) {
      const entry = STOREFRONT_CATALOG.find((item) => item.id === id);
      expect(entry, `${id} is not in the catalog`).toBeTruthy();
      needles.push(id, entry.name, entry.short, entry.blurb, entry.linkage);
      const questions = collectionQuestions(id);
      expect(questions.length, `${id} has no questions`).toBeGreaterThanOrEqual(2);
      needles.push(...questions.map((item) => item.q));
    }
    const citing = AUDIENCE_JOBS.filter((audience) => audience.collections.some((id) => ids.includes(id)));
    expect(citing.map((audience) => audience.id).sort()).toEqual(
      ["ancs-nhos", "banks-lenders", "economic-development", "foundations-philanthropy", "journalists", "native-nonprofits"],
    );
    for (const audience of citing) needles.push(audience.explanation);
    needles.push("Foundations and philanthropy");
    // The marks, read from the family file so the list cannot drift from it.
    const icons = await readFile(new URL("../src/pages/grove/pressCollectionIcons.jsx", import.meta.url), "utf8");
    for (const name of ["GivingIcon", "PlotIcon"]) {
      const start = icons.indexOf(`const ${name} = (`);
      expect(start, `${name} is not in the family`).toBeGreaterThanOrEqual(0);
      const body = icons.slice(start, icons.indexOf(");", start));
      const paths = [...body.matchAll(/\bd="([^"]+)"/g)].map((m) => m[1]);
      expect(paths.length, `${name}'s path data`).toBeGreaterThanOrEqual(2);
      needles.push(...paths);
    }

    // A strict string search, whole needle, so a partial string cannot pass
    // for the whole description. JSX-escaped ampersands are compared both
    // ways, since the minifier may keep either spelling.
    const missing = needles.filter((needle) => !build.includes(needle) && !build.includes(needle.replaceAll("&", "\\u0026")));
    expect(needles.length, "nothing to search for: the proof would pass vacuously").toBeGreaterThan(20);
    expect(missing, "new-collection material missing from the build").toEqual([]);
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

  test("the door names all fourteen collections in the HTML a crawler fetches", async ({ request }) => {
    // The viewer's rail and the use cases' chips (every example is in the
    // document, one shown at a time) spell the collections out. Prerendered,
    // so it is text in the document rather than something that appears after
    // a script runs; a crawler and a reader with JS off both get the list.
    const body = await (await request.get("/")).text();
    const names = STOREFRONT_NAMES;
    expect(names).toHaveLength(14);
    // The HTML escapes the one ampersand a collection name carries.
    for (const name of names) expect(body.includes(name) || body.includes(name.replaceAll("&", "&amp;")), name).toBe(true);
    // The count is the hero's own fact line, read from the catalog.
    expect(body).toMatch(new RegExp(`<b[^>]*>${names.length}</b> collections`));
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
    // THE HUB GRID IS GONE WITH THE HUB. This measured that six tiles stayed
    // laid out as a grid rather than collapsing into full-width blocks —
    // the failure a truncated stylesheet produces. The briefing has the same
    // exposure and the same tell: it is two columns on a wide screen, and a
    // stylesheet that did not survive gives one column of stacked blocks.
    const shape = await page.evaluate(() => {
      const brief = document.querySelector(".cp-brief");
      const lead = document.querySelector(".cp-brief__lead");
      const side = document.querySelector(".cp-brief__side");
      return {
        width: brief.getBoundingClientRect().width,
        leadWidth: lead.getBoundingClientRect().width,
        sameRow:
          Math.abs(lead.getBoundingClientRect().top - side.getBoundingClientRect().top) < 8,
      };
    });
    // The lead and its margin share a row, and neither owns the whole of it.
    expect(shape.sameRow).toBe(true);
    expect(shape.leadWidth).toBeLessThan(shape.width);
  });
});

test.describe("Methods", () => {
  // THE RING IS NEVER UNDER THE LAUNCHER, AND ITS NAMES STAY READABLE.
  //
  // The Ask Cedar launcher is fixed to the lower right of the viewport, and
  // the ring is the first figure on the page: at 1280 to 1440 it sat
  // directly over the Advocacy and NAGPRA nodes on first paint. The launcher
  // is the shared Cedar surface and does not move; the ring takes the left
  // column instead, and this measures both against each other rather than
  // trusting the CSS. The launcher is measured once it is fixed: the widget
  // mounts in flow and takes its corner when the script runs, and a box read
  // before that is a box at the foot of the page, which clears everything.
  //
  // The names: the canvas is 752 units wide with 22px labels, so a narrow
  // column renders them small. At 900, where the ring first sits beside the
  // text, and at 1100, where the index column takes 14rem from it, the
  // labels rendered around nine pixels. The ring's column has a floor now,
  // and this reads the rendered size at every width the layout changes at.
  //
  // WHEN THE LAUNCHER CAN BE MEASURED. `.cedar-widget` is `position: fixed`
  // from its first frame, but it is a child of `main.cp-page`, and that main
  // enters with the `cp-page-in` animation, a transform. A transformed
  // ancestor is the containing block of its fixed descendants, so for the
  // animation's 340ms the launcher's box is at the foot of the document,
  // thousands of pixels below the viewport and clear of everything. A read
  // taken then passes whatever the page does once it settles. The launcher
  // is settled when its box is inside the viewport.
  const launcherSettled = (page) =>
    page.waitForFunction(() => {
      const box = document.querySelector(".cedar-widget__launcher")?.getBoundingClientRect();
      return Boolean(box) && box.bottom <= innerHeight && box.top >= 0;
    });
  for (const width of [900, 1100, 1280, 1440, 1920]) {
    test(`at ${width} wide the ecosystem ring clears the Ask Cedar launcher and its labels read above 11px`, async ({ page }, testInfo) => {
      test.skip(testInfo.project.name !== "desktop", "a desktop layout question");
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/methods");
      await page.locator(".cp-eco__svg").waitFor();
      await page.evaluate(() => document.fonts.ready);
      await launcherSettled(page);
      const boxes = await page.evaluate(() => {
        const box = (el) => {
          const b = el.getBoundingClientRect();
          return { left: b.left, top: b.top, right: b.right, bottom: b.bottom };
        };
        const svg = document.querySelector(".cp-eco__svg");
        const [, , viewWidth] = svg.getAttribute("viewBox").split(" ").map(Number);
        const labelPx = parseFloat(getComputedStyle(document.querySelector(".cp-eco__label")).fontSize);
        return {
          launcher: box(document.querySelector(".cedar-widget__launcher")),
          svg: box(svg),
          lead: box(document.querySelector(".cp-meth__lead")),
          text: box(document.querySelector(".cp-meth__leadtext")),
          // The size a label renders at: its canvas size scaled by the
          // canvas's rendered width over its viewBox width.
          renderedLabelPx: (labelPx * svg.getBoundingClientRect().width) / viewWidth,
          nodes: [...document.querySelectorAll(".cp-eco__hit")].map((node) => ({
            name: node.textContent.trim(),
            ...box(node),
          })),
        };
      });
      expect(boxes.nodes.length).toBe(STOREFRONT_CATALOG.length);
      const GAP = 8;
      for (const node of boxes.nodes) {
        const apart =
          node.right + GAP <= boxes.launcher.left ||
          node.left >= boxes.launcher.right + GAP ||
          node.bottom + GAP <= boxes.launcher.top ||
          node.top >= boxes.launcher.bottom + GAP;
        expect(apart, `${node.name} at ${width}: ${JSON.stringify(node)} meets the launcher ${JSON.stringify(boxes.launcher)}`).toBe(true);
      }
      // Beside the text, and to its left, at every one of these widths.
      expect(boxes.svg.right, `ring left of the text at ${width}`).toBeLessThanOrEqual(boxes.text.left);
      expect(boxes.renderedLabelPx, `label size at ${width}`).toBeGreaterThanOrEqual(11);
    });
  }

  // THE TEXT IS NEVER UNDER THE LAUNCHER EITHER.
  //
  // Clearing the nodes moved the lead paragraph into the corner the ring had
  // left, and at 1440 the pill sat on the ends of its lines at first paint:
  // "its res", "an", cut off under a floating button, which is the desktop
  // overlap the page was reported for. The launcher stays where it is; the
  // Methods page keeps a right gutter the size of its footprint from 1280 up,
  // and this walks every text node of the lead and the chapter body with a
  // Range and holds each of its line boxes apart from the launcher's box.
  // Line boxes rather than element boxes, because a paragraph's box reaches
  // under the pill whenever its column does, and what matters is whether a
  // line of text does. Three widths: the bottom of the band, the width it was
  // seen at, and the top the page is centred from. At 1920 the page's own
  // centring gutter is wider than the pill and the rule no longer adds
  // anything.
  for (const width of [1280, 1440, 1600]) {
    test(`at ${width} wide no line of the Methods text sits under the Ask Cedar launcher at first paint`, async ({ page }, testInfo) => {
      test.skip(testInfo.project.name !== "desktop", "a desktop layout question");
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/methods");
      await page.locator(".cp-eco__svg").waitFor();
      await page.evaluate(() => document.fonts.ready);
      await launcherSettled(page);
      const { launcher, lines, under } = await page.evaluate(() => {
        const rect = (b) => ({ left: b.left, top: b.top, right: b.right, bottom: b.bottom });
        const launcher = rect(document.querySelector(".cedar-widget__launcher").getBoundingClientRect());
        const roots = [document.querySelector(".cp-meth__lead"), document.querySelector(".cp-meth__body")];
        const lines = [];
        for (const root of roots) {
          const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
          let node;
          while ((node = walker.nextNode())) {
            if (!node.textContent.trim()) continue;
            const range = document.createRange();
            range.selectNodeContents(node);
            for (const box of range.getClientRects()) {
              if (box.width === 0 || box.height === 0) continue;
              // Only what is on screen at first paint: a line below the fold
              // is not under anything.
              if (box.top >= innerHeight || box.bottom <= 0) continue;
              lines.push({ text: node.textContent.trim().slice(0, 40), ...rect(box) });
            }
          }
        }
        const under = lines.filter(
          (line) =>
            !(line.right <= launcher.left || line.left >= launcher.right || line.bottom <= launcher.top || line.top >= launcher.bottom),
        );
        return { launcher, lines, under };
      });
      // The lead is on screen at this height, so the walk saw text.
      expect(lines.length, `text lines on screen at ${width}`).toBeGreaterThan(20);
      expect(under, `lines under the launcher ${JSON.stringify(launcher)} at ${width}`).toEqual([]);
    });
  }

  test("under 900 wide the ring stacks above the text at the lead's full width", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop", "a desktop layout question");
    await page.setViewportSize({ width: 800, height: 900 });
    await page.goto("/methods");
    await page.locator(".cp-eco__svg").waitFor();
    const boxes = await page.evaluate(() => {
      const box = (el) => el.getBoundingClientRect();
      return { svg: box(document.querySelector(".cp-eco__svg")), lead: box(document.querySelector(".cp-meth__lead")), text: box(document.querySelector(".cp-meth__leadtext")) };
    });
    expect(Math.abs(boxes.svg.width - boxes.lead.width)).toBeLessThan(2);
    expect(boxes.svg.bottom).toBeLessThanOrEqual(boxes.text.top);
  });

  test("the fourteen marks index the collections, and one profile opens beneath", async ({ page }) => {
    const errors = watchConsole(page);
    await page.goto("/methods");
    // The section was twelve stacked accordions; it is the marks now, and
    // the count is the catalog's, so a collection cannot go missing here
    // without going missing from the shelf too.
    const tiles = page.locator(".cp-mbc__tile");
    await expect(tiles).toHaveCount(STOREFRONT_CATALOG.length);
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

test.describe("dead ends", () => {
  // Each of these was a control that led nowhere, or a sentence that
  // described something the page did not have (walkthrough, 2026-09-23).
  test("the Priorities page does not link to itself from its own card", async ({ page }) => {
    await signIn(page);
    await page.goto("/priorities");
    const card = page.getByTestId("influence");
    await expect(card).toBeVisible();
    await expect(card.getByRole("link", { name: /Shape the research/ })).toHaveCount(0);
  });

  test("Settings still links from the card to the Priorities page", async ({ page }) => {
    await signIn(page);
    await page.goto("/settings");
    await expect(page.getByTestId("influence").getByRole("link", { name: /Shape the research/ })).toHaveCount(1);
  });

  test("a record that is not in the preview offers one way back, not two", async ({ page }) => {
    await signIn(page);
    await page.goto("/record");
    await expect(page.getByTestId("record-empty")).toContainText("not in this preview");
    await expect(page.getByRole("link", { name: /Back to results/ })).toHaveCount(1);
  });

  test("an unknown Cedar id neither describes its records nor offers its table", async ({ page }) => {
    await signIn(page);
    await page.goto("/entity/not-a-cedar-id");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("No entity with that Cedar id");
    await expect(page.getByRole("link", { name: /View in table/ })).toHaveCount(0);
    await expect(page.getByText("Records Cedar Press has resolved to this entity")).toHaveCount(0);
  });
});

test.describe("Settings: your work", () => {
  // The offered answers are the landing audiences: same set, same order,
  // same labels (readerWork.js reads them from pressJobs.js). A preserved
  // stored answer is shown under the government audience with its level, to
  // its holder only, and its stored value is never rewritten.
  const OFFERED = visibleAudiences().map((audience) => audience.audience);

  test("offers the landing audiences, in order, as the landing names them", async ({ page }) => {
    await page.goto("/");
    const landing = await page.locator(".cp-aud__tab").allTextContents();
    expect(landing).toEqual(OFFERED);
    await signIn(page);
    await page.goto("/settings");
    await expect(page.locator("#cp-work option")).toHaveText(["Rather not say", ...landing]);
    await expect(page.locator("#cp-work option", { hasText: "Consultants and advisors" })).toHaveAttribute("value", "advisor");
    await expect(page.locator("#cp-work option", { hasText: /^Government and public agency officials$/ })).toHaveAttribute("value", "government");
  });

  for (const [id, level] of [["federal", "federal"], ["state_local", "state or local"]]) {
    test(`keeps a stored ${id} answer under the government audience, unchanged`, async ({ page }) => {
      await signIn(page);
      await page.evaluate((value) => localStorage.setItem("cedar-press-work", value), id);
      await page.goto("/settings");
      const select = page.locator("#cp-work");
      await expect(select).toHaveValue(id);
      const at = OFFERED.indexOf("Government and public agency officials");
      const expected = ["Rather not say", ...OFFERED.slice(0, at + 1), `Government and public agency officials (${level})`, ...OFFERED.slice(at + 1)];
      await expect(select.locator("option")).toHaveText(expected);
      expect(await page.evaluate(() => localStorage.getItem("cedar-press-work"))).toBe(id);
    });
  }
});

/* ── Interaction: arrival, response, state ─────────────────────────────────
 * The motion contract is docs/DESIGN_SYSTEM.md, "Motion". These measure it
 * in a browser: the twelve arrive in order once they are scrolled to and
 * settle; a tile lifts under a fine pointer on the site's one curve and
 * comes back; reduced motion is immediate; a finger gets no hover state.
 * `pressMotion.test.js` holds the rules to what these assume. */

/**
 * One style read, after a rendering update: the animation clock only
 * advances with one, and a read straight after `hover()` can land on the
 * frame before the transition has started.
 */
const readMotion = (el) =>
  new Promise((resolve) => {
    let done = false;
    const read = () => {
      if (done) return;
      done = true;
      const cs = getComputedStyle(el);
      const m = cs.transform.match(/matrix\(1, 0, 0, 1, 0, (-?[\d.]+)\)/);
      resolve({
        transform: cs.transform,
        translateY: cs.transform === "none" ? 0 : m ? Number(m[1]) : null,
        timing: cs.transitionTimingFunction,
        transition: cs.transitionDuration,
        animation: cs.animationName,
        delay: cs.animationDelay,
        opacity: Number(cs.opacity),
        shadow: cs.boxShadow,
      });
    };
    requestAnimationFrame(() => requestAnimationFrame(read));
    setTimeout(read, 250);
  });

/** Every running animation on the element and its descendants, finished. */
const settledDeep = (el) =>
  Promise.all(
    [el, ...el.querySelectorAll("*")]
      .flatMap((n) => n.getAnimations())
      .map((a) => a.finished.catch(() => {})),
  );

/** The one curve, as Chromium serialises it. */
const THE_CURVE = "cubic-bezier(0.22, 1, 0.36, 1)";

/*
 * The door's collection shelf, and its staggered arrival, were replaced by the
 * use-case band on 2026-09-26. Its chips carry the tiles' response contract:
 * a 2px lift on the curve for a fine pointer or keyboard focus, immediate
 * under reduced motion, nothing for a finger.
 */
const settledBand = async (page) => {
  const band = page.locator(".cp-aud");
  await band.scrollIntoViewIfNeeded();
  await expect(band).toHaveClass(/\bis-in\b/);
  await band.evaluate(settledDeep);
  return page.locator(".cp-aud__panel.is-on .cp-aud__col");
};

test.describe("the use-case chips respond", () => {
  test("a chip lifts under a fine pointer on the site's curve, and keyboard focus lifts it too", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop", "a fine pointer");
    await page.goto("/");
    const chips = await settledBand(page);
    const chip = chips.nth(1);
    expect((await chip.evaluate(readMotion)).transform, "rests untransformed").toBe("none");

    await chip.hover();
    await expect
      .poll(async () => (await chip.evaluate(readMotion)).translateY, { message: "the chip lifts" })
      .toBeLessThanOrEqual(-1.5);
    const lifted = await chip.evaluate(readMotion);
    expect(lifted.translateY).toBeGreaterThanOrEqual(-2.5);
    expect(lifted.shadow, "a soft shadow under the lift").not.toBe("none");
    expect(lifted.timing.replaceAll(THE_CURVE, "").replace(/[, ]/g, ""), `on ${THE_CURVE}, got ${lifted.timing}`).toBe("");

    let nudge = 0;
    await expect
      .poll(async () => {
        nudge = (nudge + 1) % 4;
        await page.mouse.move(2 + nudge, 2 + nudge);
        return (await chip.evaluate(readMotion)).transform;
      }, { message: "settles back on leave", timeout: 8000 })
      .toBe("none");

    await chips.nth(2).focus();
    await expect
      .poll(async () => (await chips.nth(2).evaluate(readMotion)).translateY, { message: "focus lifts" })
      .toBeLessThanOrEqual(-1.5);
  });

  test("reduced motion: the example is simply there, and a lift is immediate", async ({ page }, testInfo) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/");
    const chips = await settledBand(page);
    const panel = page.locator(".cp-aud__panel.is-on");
    for (const duration of (await panel.evaluate(readMotion)).transition.match(/[\d.e-]+(?=s)/g)) {
      expect(Number(duration)).toBeLessThanOrEqual(0.001);
    }
    if (testInfo.project.name !== "desktop") return;
    const chip = chips.nth(0);
    await chip.hover();
    const lifted = await chip.evaluate(readMotion);
    expect(lifted.transform).toBe("matrix(1, 0, 0, 1, 0, -2)");
    for (const duration of lifted.transition.match(/[\d.e-]+(?=s)/g)) expect(Number(duration)).toBeLessThanOrEqual(0.001);
  });
});

test.describe("a finger gets no hover state", () => {
  test.use({ hasTouch: true });

  test("a tapped chip is chosen, never raised", async ({ page }) => {
    await page.goto("/");
    const emulated = await page.evaluate(() => matchMedia("(hover: none)").matches);
    test.skip(!emulated, "this engine does not emulate a hoverless pointer from hasTouch");
    const chips = await settledBand(page);
    const chip = chips.nth(1);
    await chip.tap();
    await expect(chip).toHaveAttribute("aria-pressed", "true");
    await expect(chip).toHaveClass(/is-on/);
    // A pointer parked over a chip on this screen raises nothing: the lift is
    // written for `(hover: hover) and (pointer: fine)`. `hover()` rather than
    // a second tap, because a tap does not leave :hover behind and could not
    // reach an unguarded rule.
    await chips.nth(2).hover();
    await page.waitForTimeout(400);
    expect((await chips.nth(2).evaluate(readMotion)).transform, "no lift for a finger").toBe("none");
    // The four claims respond to nothing under a finger either.
    const claim = page.locator(".cp-why__item").first();
    await claim.scrollIntoViewIfNeeded();
    await claim.hover();
    await page.waitForTimeout(300);
    expect(await claim.locator(".cp-why__ic").evaluate((el) => getComputedStyle(el).transform)).toBe("none");
  });
});

test.describe("Methods' seven stages arrive as a sequence", () => {
  test("each stage lands on its own beat, then the rail is still", async ({ page }) => {
    const errors = watchConsole(page);
    await page.goto("/methods");
    await page.locator(".cp-proc__stage").first().waitFor();
    await page.evaluate(() => document.fonts.ready);
    const chapter = page.locator("#m-records");
    const top = await chapter.evaluate((el) => el.getBoundingClientRect().top / window.innerHeight);
    expect(top, "the chapter sits below the fold on arrival").toBeGreaterThan(1.1);
    await chapter.scrollIntoViewIfNeeded();
    await expect(chapter).toHaveClass(/\bis-in\b/);
    const stages = await page.locator(".cp-proc__stage").evaluateAll((list) =>
      list.map((li) => ({ name: getComputedStyle(li).animationName, delay: parseFloat(getComputedStyle(li).animationDelay) })));
    expect(stages.length).toBeGreaterThanOrEqual(5);
    stages.forEach((s, i) => {
      expect(s.name).toBe("cp-stage-in");
      expect(s.delay).toBeCloseTo(i * 0.055, 3);
    });
    await chapter.evaluate(settledDeep);
    const rest = await page.locator(".cp-proc__stage").evaluateAll((list) =>
      list.map((li) => [getComputedStyle(li).opacity, getComputedStyle(li).transform]));
    expect(rest).toEqual(Array(stages.length).fill(["1", "none"]));
    expect(errors).toEqual([]);
  });
});

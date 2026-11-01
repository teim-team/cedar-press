// REVIEW OWNER: Havala
//
// Cedar Press: the way in.
//
// The door is built the way the marketing site's home is built: one
// promise, and beside it the real product. Cedar Press's product is rows,
// so what stands beside the promise is not a screenshot but a live frame of
// the product: the twelve collections down its rail, each with its mark,
// and the one in hand open in the pane with six of its real records
// (PressCollectionPreview). A visitor who heard "Cedar Press" at a
// conference learns what is inside by looking at it.
//
// Nothing in the frame is confidential: the ten-row samples ship in the
// public bundle by design, and they are the whole of what
// the frame can reach. The reader's own shelf (#catalog on /data) is never
// rendered here, and the smoke suite holds the door to its absence.
//
// The page below the hero changes material the way the marketing site
// does: a navy passage with the licensed photograph and the three pillars,
// then the ways in on white, then a short foot. "Subscribe" and "Sign in"
// sit top right, where a visitor looks for them, and each opens a small
// panel under the bar; the page underneath stays the page.
//
// "Subscribe" goes to the membership cards (CedarPressSubscribe), where Stripe
// takes payment and the account follows from the emailed setup link. "Sign in"
// goes to the login page (CedarPressLogin).

import { useEffect, useRef, useState } from "react";
import { Link, Navigate, useLocation, useSearchParams } from "react-router";

import { isWorkspaceHost, loginRedirect, subscribeHref as subscribeHrefFor, workspaceSignInHref } from "../../features/grove/pressSessionNavigation.js";
import { useAuth } from "../../context/useAuth";
import { useFadeIn } from "../../features/grove/useFadeIn";
import { LUMECON_URL } from "../../features/grove/appLink.js";
import { coverageFrom } from "../../features/grove/pressAccess";
import { PRESS_CATALOG_BY_ID, PRESS_TIERS, STOREFRONT_CATALOG, collectionsOnShelf } from "../../features/grove/pressCatalog";
import { LAUNCH_COLLECTION, LAUNCH_ROWS_TOTAL, OBSERVATIONS_NOTE } from "../../features/grove/collection";
import { formatUpdated, recentlyUpdated } from "../../features/grove/pressReleases";
import { SOURCE_REACH_UPDATED, SOURCE_ROTATION_ORDER } from "../../features/grove/sourceRotation.js";
import { MAINTENANCE } from "../../features/grove/pressMethod.js";
import {
  PRESS_LOGIN_PATH,
  PRESS_METHODS_PATH,
  PRESS_PRIVACY_PATH,
  PRESS_REQUEST_PATH,
  PRESS_RESEARCH_PATH,
  PRESS_TERMS_PATH,
} from "../../features/grove/pressRoutes";
import { EVENT, track } from "../../features/grove/telemetry.js";
import { useRegister } from "../../features/grove/useRegister.js";
import { COLLECTION_ICONS } from "./pressCollectionIcons";
import CollectionPreview from "./PressCollectionPreview";
import PressCollectionRail from "./PressCollectionRail.jsx";
import PressDoorCedar from "./PressDoorCedar";
import PressAudienceExample from "./PressAudienceExample";
import { TierName } from "./TierName";
import { useTicker } from "../../features/grove/useTicker";

/** The source list dealt into rows for the navy banner, from the scrambled
 * order, so no row reads as a list someone could copy in sequence. */
const SOURCE_ROW_COUNT = 7;
const SOURCE_ROWS = Array.from({ length: SOURCE_ROW_COUNT }, (_, r) =>
  SOURCE_ROTATION_ORDER.filter((_, i) => i % SOURCE_ROW_COUNT === r),
).filter((row) => row.length);

/** A hero figure that ticks to its value once, in view (owner, 2026-09-27).
 * The year counts back from this year to the earliest record, the others up
 * from zero. The final value is what is prerendered and what a reader who
 * prefers reduced motion sees. */
const formatCount = (n) => n.toLocaleString("en-US");
function Tick({ value, from = 0, format = String }) {
  const ref = useTicker(value, { from, format });
  const final = format(value);
  // The final value's width is held while the count runs, so a number
  // ticking up from 0 never rewraps the line it sits in (the hero's facts
  // line wrapped mid-count and moved the page by a line, 2026-10-06).
  return <b ref={ref} className="cp-tick" style={{ minWidth: `${final.length}ch` }}>{final}</b>;
}

/** The brand mark, served from public/. The all-teal mark is the current one. */
const MARK = "/brand/lumecon-logo-mark-teal.png";

// What the product is made of, in the catalog's and the release record's
// own numbers, for the line under the statement. The earliest year is the
// deepest single collection, so the line says "as far back as", never
// "since": the rest start later and two of them are rosters with no start.
const COLLECTION_STARTS = STOREFRONT_CATALOG.map((entry) => coverageFrom(entry)).filter(Boolean);
const EARLIEST_YEAR = COLLECTION_STARTS.length ? Math.min(...COLLECTION_STARTS) : null;
// Page revisions and collection refreshes have separate dates. A source-band
// revision updates the landing page without rewriting any collection release.
const PAGE_UPDATED = [SOURCE_REACH_UPDATED, ...recentlyUpdated(1).map((release) => release.updated)].sort().at(-1);
// The data refresh is a third date, apart from the page revision and from
// the period the records cover (2026-10-06): the newest producer refresh
// any collection was staged from (collection.js `refreshed`).
const DATA_REFRESHED = LAUNCH_COLLECTION.map((dataset) => dataset.refreshed).filter(Boolean).sort().at(-1) ?? null;

// The shelves, each with its collections, in the storefront's order.
const SHELVES = PRESS_TIERS.filter((tier) => tier.storefront).map((tier) => ({
  tier,
  entries: collectionsOnShelf(tier.shelf),
}));
const TIER_OF = Object.fromEntries(SHELVES.flatMap(({ tier, entries }) => entries.map((entry) => [entry.id, tier])));

// The source systems are read from `pressSources.js`, which breaks each
// collection descriptor's sources prose into the systems it names and is
// held to them by a test. The door names every one of them rather than a
// hand-picked seven: the breadth IS the argument, and a visitor who counts
// six familiar federal systems concludes Cedar repackages open data.

// The three pillars. Each names something a reader can check on this page or
// on Methods, because "data-driven insights" and "credible research" are
// adjectives a reader has no way to test. Rewritten 2026-09-13 on review.
//
// NOTE FOR THE OWNER: the second pillar names entity resolution. The long
// linkage SENTENCE came off the door on 2026-09-04; this is a short
// restatement of the same claim, added because a review found the door said
// nothing about the one thing that distinguishes the collections. Revert this
// pillar if that ruling was meant to cover the claim and not only the wording.
// Owner copy, 2026-10-06: each block a distinct purpose (usable data,
// connected information, guided exploration). The old
// blocks repeated the sourcing and matching story the section already tells,
// claimed "every row" carries an entity (a record about Indian Country
// broadly need not), and promised Cedar would answer any question with the
// underlying record, which it does not do. Cedar answers what a collection
// covers, how it is built and what changed.
const PROOF_POINTS = [
  {
    id: "collections",
    label: "Put the data to work",
    short: "Put the data to work",
    body: "Explore original datasets on funding, business, policy and philanthropy. Download collections for your own research, reporting and planning, with the definitions and source references needed to use them.",
  },
  {
    id: "insights",
    label: "Follow connections across collections",
    short: "Connections",
    body: "Connect a nation\u2019s enterprises with their contracts, funding and transactions. Read those relationships alongside broader policy and economic records to understand individual organizations and the developments shaping Indian Country.",
  },
  {
    id: "cedar",
    label: "Explore with Cedar",
    short: "Explore with Cedar",
    body: "Ask Cedar what a collection covers, how it is built and what has changed. Find relevant data and understand how the collections can help you approach your question.",
  },
];

// The marketing door belongs to cedarpress.ai. On the workspace host a
// signed-out visitor goes to the login page instead, and returns here after.
export default function PressGate(props) {
  const here = useLocation();
  if (isWorkspaceHost(window.location)) return <Navigate to={loginRedirect(here)} replace />;
  return <Door {...props} />;
}

function Door({ user }) {
  const { logout } = useAuth();
  // The page reads as one long scroll on a phone, so its sections arrive as
  // they enter the viewport instead of standing there already.
  const fadeRoot = useFadeIn();
  // Closed on arrival: the panel covers what is behind it, so it opens only
  // when asked for (owner, 2026-09-14).
  const [plansOpen, setPlansOpen] = useState(false);
  // The workspace's login page on the public site, this origin's own anywhere
  // else (a dev server, a preview host).
  const loginHref = workspaceSignInHref(window.location) ?? PRESS_LOGIN_PATH;
  const subscribeHref = subscribeHrefFor(window.location);
  // The source band moves until a reader stops it (WCAG 2.2.2): the button
  // beside its count pauses and resumes it, and reduced motion stills it.

  // The collection in hand: the first on the rail on arrival, never none.
  // THE COLLECTION IN HAND IS IN THE URL.
  //
  // It was local state, so the one thing a visitor might want to send
  // somebody — "look at this collection" — had no address, and every link to
  // the door landed on Federal Funding whatever the sender was looking at.
  // `?collection=<id>` is read on arrival and written on every pick.
  //
  // Written with `replace`: choosing a collection is looking around, not
  // navigating, and twelve picks should not put twelve entries between the
  // visitor and the page they came from. An id nobody publishes falls back to
  // the first collection rather than to an empty pane.
  const [params, setParams] = useSearchParams();
  const asked = params.get("collection");
  const first = SHELVES[0]?.entries[0]?.id ?? null;
  // Pointing at a collection describes it; choosing one is what the URL
  // records. Both move the frame, and only the second is worth an address —
  // a replace per hover would rewrite the URL a dozen times crossing a rail.
  const [pointed, setPointed] = useState(null);
  const addressed = STOREFRONT_CATALOG.some((entry) => entry.id === asked) ? asked : first;
  const selectedId = pointed ?? addressed;
  const selected = STOREFRONT_CATALOG.find((entry) => entry.id === selectedId) ?? null;
  const register = useRegister();

  const setSelectedId = (id) => setPointed(id);

  const pick = (entry) => {
    track(EVENT.collectionViewed, { collection: entry.id, shelf: entry.shelf, gated: true });
    setPointed(entry.id);
    const next = new URLSearchParams(params);
    next.set("collection", entry.id);
    // Looking around, not navigating: twelve picks should not put twelve
    // entries between the visitor and the page they arrived from.
    setParams(next, { replace: true });
  };

  // The panel closes on Escape and on a click outside it or its tabs.
  const panelRef = useRef(null);
  const tabsRef = useRef(null);
  // CEDAR'S LAUNCHER STEPS ASIDE FOR THE PROOF OBJECT.
  //
  // The preview is the page's one proof surface, and a fixed pill in the
  // bottom-right corner sat on top of it — measured at 1440x900, over the
  // Advocacy tile in the collection strip, which is part of the thing the
  // object exists to demonstrate. A launcher that covers the evidence makes
  // an otherwise finished surface look accidental.
  //
  // Same mechanism `PressExplore` already uses for the signed-in viewer
  // (`data-cp-explore-in-view`), so there is one way this is done rather than
  // two. The OPEN panel is untouched: a reader who has asked a question is no
  // longer looking at the preview.
  const previewRef = useRef(null);
  useEffect(() => {
    const stage = previewRef.current;
    if (!stage || typeof IntersectionObserver !== "function") return undefined;
    const observer = new IntersectionObserver(
      ([entry]) => document.body.toggleAttribute("data-cp-preview-in-view", entry.isIntersecting),
      // A sliver of the frame showing at the very bottom is not the reader
      // looking at it, and toggling on that sliver makes the launcher flicker
      // on every scroll through the hero. The frame is taller than the screen
      // at full width, so the share it needs is small.
      { threshold: 0.15 },
    );
    observer.observe(stage);
    return () => {
      observer.disconnect();
      document.body.removeAttribute("data-cp-preview-in-view");
    };
  }, []);
  // THE SAME, ON A PHONE, FOR THE FIRST SCREEN AND THE USE CASES. At 390 the
  // launcher sat on the hero's facts row and, lower down, on the use-case
  // card's last lines. While either is on screen it stays away (the
  // stylesheet applies this below 720 only); the door's other ways into
  // Cedar are a scroll away, and from the navy passage down it is back.
  const heroCopyRef = useRef(null);
  useEffect(() => {
    const nodes = [heroCopyRef.current, document.querySelector(".cp-aud")].filter(Boolean);
    if (!nodes.length || typeof IntersectionObserver !== "function") return undefined;
    const showing = new Set();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) showing.add(entry.target);
          else showing.delete(entry.target);
        }
        document.body.toggleAttribute("data-cp-launcher-away", showing.size > 0);
      },
      { threshold: 0 },
    );
    for (const node of nodes) observer.observe(node);
    return () => {
      observer.disconnect();
      document.body.removeAttribute("data-cp-launcher-away");
    };
  }, []);
  useEffect(() => {
    if (!plansOpen) return undefined;
    const onKey = (event) => { if (event.key === "Escape") setPlansOpen(false); };
    const onDown = (event) => {
      if (panelRef.current?.contains(event.target) || tabsRef.current?.contains(event.target)) return;
      setPlansOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onDown);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onDown);
    };
  }, [plansOpen]);

  return (
    // .cp-split is the name the smoke suite knows the door by; the layout
    // is no longer a split.
    <main className="cp-door cp-split" ref={fadeRoot}>
      <header className="cp-door__bar">
        <div className="cp-door__barin">
          <span className="cp-door__lockup">
            <img className="cp-door__mark" src={MARK} alt="" aria-hidden="true" />
            <span className="cp-door__word">Cedar Press</span>
          </span>
          <nav className="cp-door__nav" aria-label="Public navigation">
            <a href="#cp-viewer">Explore</a>
            <Link to={PRESS_METHODS_PATH}>Methods</Link>
          </nav>
          {user ? (
            // Someone signed in on the wrong membership has one move,
            // upgrading; the bar says who they are and offers the other account.
            <span className="cp-door__user">
              <span className="cp-door__who">Signed in as {user.email} · no Cedar Press</span>
              <a className="cp-btn cp-btn--primary" href={subscribeHref}>
                Subscribe <span className="cp-btn__arrow" aria-hidden="true">&#8594;</span>
              </a>
              <button type="button" className="cp-split__linkbtn" onClick={() => logout()}>
                Use a different account
              </button>
            </span>
          ) : (
            // One question, two answers: get Cedar Press, or you already have
            // it. Tabs, so the panel under the bar shows one at a time.
            <div className="cp-door__tabs" ref={tabsRef}>
              <a id="cp-tab-signin" className="cp-door__signin" href={loginHref}>Sign in</a>
              <button
                type="button"
                id="cp-tab-plans"
                className="cp-btn cp-btn--primary cp-door__tab--plans"
                aria-expanded={plansOpen}
                aria-controls="cp-panel-plans"
                onClick={() => setPlansOpen((open) => !open)}
              >
                Subscribe
              </button>
            </div>
          )}
        </div>

        {!user && plansOpen ? (
          <div id="cp-panel-plans" className="cp-door__panel" ref={panelRef}>
            <h2 className="cp-gate__sub">Choose your annual Cedar Press plan.</h2>
            <p className="cp-door__panelp">Pay securely through Stripe, then confirm your email and set your password.</p>
            <a className="cp-btn cp-btn--primary cp-btn--wide" href={subscribeHref}>
              Subscribe annually <span className="cp-btn__arrow" aria-hidden="true">&#8594;</span>
            </a>
          </div>
        ) : null}

      </header>

      {/* ── The hero: the promise, and beside it the product ─────────── */}
      <section className="cp-hero3" aria-label="Cedar Press">
        <div className="cp-hero3__in">
          {/* A short introduction above the viewer, so the viewer gets the
              full width of the page. */}
          <div className="cp-hero3__copy" ref={heroCopyRef}>
            <p className="cp-kicker cp-hero3__kicker cp-fade">Intelligence for Indian Country</p>
            <h1 className="cp-hero3__title cp-fade">
              See what&rsquo;s possible.<br /> Shape what&rsquo;s next.
            </h1>
            <p className="cp-hero3__lede cp-fade">
              Explore funding, enterprises and policy through original research and connected
              records you can trace to their sources.
            </p>
            {/* Who made it, on the first screen (owner's brief, 2026-09-26):
                one restrained line rather than logos, so the product frame
                stays the proof object. */}
            <p className="cp-hero3__by cp-fade">
              Built by <a href={LUMECON_URL} target="_blank" rel="noreferrer">Lumecon</a>.
            </p>
            <div className="cp-hero3__cta cp-fade">
              <a className="cp-btn cp-btn--primary cp-btn--lg" href="#cp-viewer">Explore the data</a>
              <a className="cp-btn cp-btn--quiet cp-btn--lg" href={subscribeHref}>View membership</a>
            </div>
          </div>

          {/* The product frame. The rail is the twelve collections with
              their marks, one group a shelf; the pane is the one in hand.
              Not `#catalog`: that id is the reader's shelf on /data. */}
          <figure className="cp-hero3__stage cp-fade" id="cp-viewer" ref={previewRef}>
            {/* The frame holds a real desktop window at real desktop size and
                scales it to fit, the way a product screenshot does. Rendering
                the app at the ~800px the column actually offers gave a narrow
                window with cramped columns; rendering it at 1280x800 and
                scaling gives the true desktop layout at 16:10. The scale is
                container-query units, so it needs no JavaScript and no
                resize listener. Below the stack point the app goes fluid
                again — a 1280px window scaled onto a phone is unreadable. */}
            <div className="cp-hero3__frame">
            <div className="cp-app" data-testid="press-frame">
              <div className="cp-app__chrome">
                <span className="cp-app__chromeword">
                  <img src={MARK} alt="" aria-hidden="true" />
                  Cedar Press
                </span>
                <span className="cp-app__chromeat">Collections</span>
                <span className="cp-app__chromemeta">{STOREFRONT_CATALOG.length} collections</span>
              </div>
              <div className="cp-app__body">
                <div className="cp-app__railwrap">
                {/* THE RAIL IS THE RAIL.
                    This drew its own navy list of the twelve — the third
                    separately authored way of showing one catalogue, and the
                    reason `PressCollectionRail` was written. It mounts that
                    component in `preview` mode now: nothing is locked, since
                    nobody is signed in and the question a visitor has is what
                    exists, not what their plan reaches. */}
                <PressCollectionRail
                  selectedId={selectedId}
                  onSelect={(entry) => (entry ? pick(entry) : null)}
                  onPoint={setSelectedId}
                  mode="preview"
                />
                </div>
                <div className="cp-app__pane">
                  {selected ? (
                    <CollectionPreview key={selected.id} entry={selected} tier={TIER_OF[selected.id]} register={register} />
                  ) : null}
                </div>
              </div>
            </div>
            </div>
            <p className="cp-kicker cp-hero3__tagline">Tribal Nations · Enterprises · Research &amp; Policy</p>
            <figcaption className="cp-fade">
              The Cedar Press viewer, showing example records from each collection&rsquo;s
              current dataset.
            </figcaption>
            {/* The summary figures, one line under the caption (owner,
                2026-09-27), so nothing sits below the hero's button and the
                use cases start higher. */}
            <ul className="cp-hero3__facts" aria-label="What Cedar Press holds">
              <li><Tick value={STOREFRONT_CATALOG.length} /> collections</li>
              {/* Observations across every collection's dataset (owner,
                  2026-10-06), from the manifest's own count per collection. */}
              {LAUNCH_ROWS_TOTAL ? <li title={OBSERVATIONS_NOTE}><Tick value={LAUNCH_ROWS_TOTAL} format={formatCount} /> observations</li> : null}
              {EARLIEST_YEAR ? <li>as far back as <Tick value={EARLIEST_YEAR} from={new Date().getFullYear()} /></li> : null}
              {DATA_REFRESHED ? <li data-testid="door-data-refreshed">data as of <b>{formatUpdated(DATA_REFRESHED)}</b></li> : null}
              <li data-testid="door-page-updated">page updated <b>{formatUpdated(PAGE_UPDATED)}</b></li>
            </ul>
            {/* The total adds rows of different kinds, so it says what it
                counts (2026-10-06): not organizations, not dollars. */}
            {LAUNCH_ROWS_TOTAL ? <p className="cp-gate__fine cp-hero3__factsnote" data-testid="door-observations-note">{OBSERVATIONS_NOTE}</p> : null}
          </figure>

        </div>

        {/* THE SPACE UNDER THE HERO IS HOW THE COLLECTIONS GET USED.
            This slot held the full-size collection shelf, which was there
            because the frame renders the real app at 1280px and scales it to
            fit, so a rail row is about seventeen pixels tall: visible, not
            pointable. The owner replaced the shelf on 2026-09-26 (it repeated
            what the viewer already shows) with the use-case band, which keeps
            the shelf's jobs: its chips preview a collection in the frame on
            point and commit it on click through the same `pick`, and the
            selected collection's description sits under it. Whether every live
            collection is named by some use case is a review report
            (pressJobs.test.js), not a rule. */}
        <PressAudienceExample
          selected={selected}
          onPick={pick}
          onPoint={setSelectedId}
        />

      </section>

      {/* ── The passage: why, on navy, with the photograph ────────────── */}
      <section className="cp-why" aria-labelledby="cp-why-title">
        <div className="cp-why__in">
          <header className="cp-why__head">
            <div>
              <h2 className="cp-why__title cp-fade" id="cp-why-title">
                The hard part is knowing who a record is about.
              </h2>
              <p className="cp-why__lede cp-fade">
                <a href={LUMECON_URL} target="_blank" rel="noreferrer">Lumecon</a> connects scattered
                records while keeping each nation, enterprise and related organization distinct.
              </p>
            </div>
            {/* The source banner sits here (owner, 2026-09-27): the passage
                is already about how the records are gathered, and this column
                was empty above the shelves. */}
            <div className="cp-why__side">
              <aside className="cp-hero3__proof cp-why__sources cp-fade" aria-label="Source systems">
                <div className="cp-hero3__proofhead">
                  <Link className="cp-hero3__prooflabel" to={PRESS_METHODS_PATH}>
                    Sources and methods
                  </Link>
                </div>
                {/* Several runs, alternating direction, so the banner fills
                    the column rather than one line at its foot. Each run is
                    duplicated for a seamless loop; the copy is aria-hidden so
                    a screen reader hears every source once. It pauses on
                    hover, and a transparent layer over the
                    runs keeps the moving text from being selected and copied
                    (owner, 2026-09-27). */}
                <div className="cp-why__runs">
                  {SOURCE_ROWS.map((row, r) => (
                    <div className="cp-hero3__marqwrap" key={r}>
                      <div
                        className={`cp-hero3__marquee${r % 2 ? " cp-hero3__marquee--back" : ""}`}
                        style={{ "--run-dur": `${row.length * 3.2}s` }}
                      >
                        <ul className="cp-hero3__run">
                          {row.map((label) => <li key={label}>{label}</li>)}
                        </ul>
                        <ul className="cp-hero3__run" aria-hidden="true">
                          {row.map((label) => <li key={`${label}-echo`}>{label}</li>)}
                        </ul>
                      </div>
                    </div>
                  ))}
                </div>
              </aside>
            </div>
          </header>
          <div className="cp-why__photo cp-fade" aria-hidden="true">
            <picture>
              <source srcSet="/photo/tribal-flags-sm.webp" media="(max-width: 720px)" />
              <img src="/photo/tribal-flags-wide.webp" alt="" width="1500" height="600" loading="lazy" decoding="async" />
            </picture>
            <p className="cp-why__photolabel">
              <span>Tribal economies</span>
              Governments, enterprises, ANCs, NHOs and nonprofits
            </p>
          </div>
          <ol className="cp-why__proof">
            {PROOF_POINTS.map((point) => (
              // Owner, 2026-10-06: the headline is enough at a glance; the
              // paragraph opens on request. A native disclosure, so it works
              // from the keyboard and with a screen reader as it is.
              <li className="cp-why__item cp-fade" key={point.id}>
                <details className="cp-why__more">
                  <summary className="cp-why__sum">
                    <span className="cp-why__label" title={point.label}>{point.short}</span>
                  </summary>
                  <p className="cp-why__body">{point.body}</p>
                </details>
              </li>
            ))}
          </ol>
          <p className="cp-why__note cp-fade">Photography is illustrative and does not identify Cedar Press customers.</p>
        </div>
      </section>

      {/* ── The ways in ───────────────────────────────────────────────── */}
      <section className="cp-ways" aria-labelledby="cp-ways-title">
        <div className="cp-ways__in">
          <header className="cp-ways__head cp-fade">
            <p className="cp-kicker">Get Cedar Press</p>
            <h2 className="cp-ways__title" id="cp-ways-title">
              Choose your <span>annual membership.</span>
            </h2>
            <p className="cp-ways__lede">
              A Cedar Press membership opens the collections and Cedar.
              Tribal governments and approved research projects can work with Cedar without one.
            </p>
            <div className="cp-hero3__cta">
              <a className="cp-btn cp-btn--primary cp-btn--lg" href={subscribeHref}>
                Subscribe annually <span className="cp-btn__arrow" aria-hidden="true">&#8594;</span>
              </a>
              {user ? null : (
                <a className="cp-btn cp-btn--quiet cp-btn--lg" href={loginHref}>
                  Sign in <span className="cp-btn__arrow" aria-hidden="true">&#8594;</span>
                </a>
              )}
            </div>
          </header>
          {/* Governance before commerce: a nation's right to its own records
              leads, the project pathway follows, and the methods close. */}
          <ol className="cp-ways__ledger">
            <li className="cp-ways__row cp-fade">
              <span className="cp-ways__label">Tribal governments</span>
              <div>
                <h3>Request and review the Cedar records associated with your nation.</h3>
                <p>Federally recognized tribal governments can request and review their records. No subscription required.</p>
                <Link className="cp-ways__act" to={PRESS_REQUEST_PATH}>Tribal government data requests <span aria-hidden="true">&#8594;</span></Link>
              </div>
            </li>
            <li className="cp-ways__row cp-fade">
              <span className="cp-ways__label">Research</span>
              <div>
                <h3>One or two collections for a defined project.</h3>
                <p>For researchers, journalists, students, nonprofits and public-interest projects.</p>
                <Link className="cp-ways__act" to={PRESS_RESEARCH_PATH}>Research access <span aria-hidden="true">&#8594;</span></Link>
              </div>
            </li>
            <li className="cp-ways__row cp-fade">
              <span className="cp-ways__label">Methods</span>
              <div>
                <h3>How a collection is built, and how it is kept current.</h3>
                <p data-testid="door-maintenance">{MAINTENANCE.sentence} Methods shows how records are sourced and resolved to Native entities: the reference to open before citing a number.</p>
                <Link className="cp-ways__act" to={PRESS_METHODS_PATH}>How Cedar builds its collections <span aria-hidden="true">&#8594;</span></Link>
              </div>
            </li>
          </ol>
        </div>
      </section>

      <footer className="cp-door__foot cp-fade">
        <span>
          Built by <a href={LUMECON_URL} target="_blank" rel="noreferrer">Lumecon</a>.{" "}
          <Link to={PRESS_TERMS_PATH}>Terms</Link> · <Link to={PRESS_PRIVACY_PATH}>Privacy</Link>
        </span>
        <button
          type="button"
          className="cp-split__linkbtn"
          onClick={() => window.dispatchEvent(new CustomEvent("cedar:open"))}
        >
          Ask Cedar what Cedar Press can answer
        </button>
      </footer>

      {/* Cedar meets the visitor at the door. Everyone here is outside the
          product, so this Cedar answers from a prepared bank rather than
          from the collections: it explains what is inside without opening
          anything a subscriber pays for, and it never reaches the network.
          See doorCedar.js. */}
      <PressDoorCedar />
    </main>
  );
}

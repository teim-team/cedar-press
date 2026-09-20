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
// public bundle by design (pressDemoGate.js), and they are the whole of what
// the frame can reach. The reader's own shelf (#catalog on /data) is never
// rendered here, and the smoke suite holds the door to its absence.
//
// The page below the hero changes material the way the marketing site
// does: a navy passage with the licensed photograph and the four pillars,
// then the ways in on white, then a short foot. "View plans" and "Log in"
// sit top right, where a visitor looks for them, and each opens a small
// panel under the bar; the page underneath stays the page.
//
// Tribal Business News owns payment, renewals, upgrades and code issuance.
// There is deliberately no "create account" here: an account exists because
// an entitlement does. Activation is two steps: the access code and an
// email address first, a password only once the code has been accepted.
// Which screen opens is what this browser did last time.
//
// THREE STATES, AND THE COPY HAS TO MATCH
// Connected, this form posts to the platform and the session is a signed,
// HTTP-only cookie. Standalone with a preview account configured, the check
// runs in the reader's browser. Standalone with nothing configured, there is
// no form at all, because a form that can only fail is worse than a sentence
// explaining why there is none.

import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";

import { contactHref } from "../../features/grove/appLink.js";
import { useAuth } from "../../context/useAuth";
import { useFadeIn } from "../../features/grove/useFadeIn";
import { activatePressAccount, validatePressCode } from "../../api";
import { LAUNCH_COLLECTION, LAUNCH_ROWS_TOTAL } from "../../features/grove/collection";
import { coverageFrom } from "../../features/grove/pressAccess";
import { LUMECON_URL, TBN_PLANS_URL, TBN_URL } from "../../features/grove/pressArticles";
import { PRESS_TIERS, STOREFRONT_CATALOG, collectionsOnShelf } from "../../features/grove/pressCatalog";
import { formatUpdated, recentlyUpdated } from "../../features/grove/pressReleases";
import { PRESS_SOURCES, SOURCE_COUNT } from "../../features/grove/pressSources.js";
import {
  PRESS_METHODS_PATH,
  PRESS_REQUEST_PATH,
  PRESS_RESEARCH_PATH,
} from "../../features/grove/pressRoutes";
import {
  PRESS_DEMO_UNCONFIGURED,
  PRESS_SIGN_IN_AVAILABLE,
} from "../../features/grove/pressDemoGate";
import {
  PRESS_ACTIVATION_AVAILABLE,
  PRESS_STEP,
  formatPressCode,
  initialPressStep,
  isPlausiblePressCode,
  normalizePressCode,
  pressSignupError,
  rememberPressAccount,
} from "../../features/grove/pressSignup";
import { EVENT, track } from "../../features/grove/telemetry.js";
import { useRegister } from "../../features/grove/useRegister.js";
import { COLLECTION_ICONS } from "./pressCollectionIcons";
import {
  CedarIcon,
  CredibleResearchIcon,
  InsightsIcon,
  OriginalCollectionsIcon,
} from "./pressGateIcons";
import CollectionPreview from "./PressCollectionPreview";
import PressDoorCedar from "./PressDoorCedar";
import PressDoorCollections from "./PressDoorCollections";
import { TierName } from "./TierName";
import PressReleaseSpecimen from "./PressReleaseSpecimen";

/** The brand mark, served from public/. The all-teal mark is the current one. */
const MARK = "/brand/lumecon-logo-mark-teal.png";

// What the product is made of, in the catalog's and the release record's
// own numbers, for the line under the statement. The earliest year is the
// deepest single collection, so the line says "as far back as", never
// "since": the rest start later and two of them are rosters with no start.
const COLLECTION_STARTS = STOREFRONT_CATALOG.map((entry) => coverageFrom(entry)).filter(Boolean);
const EARLIEST_YEAR = COLLECTION_STARTS.length ? Math.min(...COLLECTION_STARTS) : null;
const ROWS_LABEL = Object.fromEntries(LAUNCH_COLLECTION.map((entry) => [entry.id, entry.rowsLabel]));

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

// The four pillars. Each names something a reader can check on this page or
// on Methods, because "data-driven insights" and "credible research" are
// adjectives a reader has no way to test. Rewritten 2026-09-13 on review.
//
// NOTE FOR THE OWNER: the second pillar names entity resolution. The long
// linkage SENTENCE came off the door on 2026-09-04; this is a short
// restatement of the same claim, added because a review found the door said
// nothing about the one thing that distinguishes the collections. Revert this
// pillar if that ruling was meant to cover the claim and not only the wording.
const PROOF_POINTS = [
  {
    id: "collections",
    label: "Documented source records",
    body: "Federal systems, tribal publications and agency dockets are assembled here into one collection for the first time.",
    icon: OriginalCollectionsIcon,
  },
  {
    id: "insights",
    label: "Resolved to Native entities",
    body: "Every row carries the nation, corporation or organization behind it, tracked through name changes, subsidiaries and reorganizations.",
    icon: InsightsIcon,
  },
  {
    id: "credible",
    label: "Published with its limits",
    body: "Every collection ships its inclusion rules, its known gaps and its corrections. Indigenous researchers with Federal Reserve and university experience build them.",
    icon: CredibleResearchIcon,
  },
  {
    id: "cedar",
    label: "Ask Cedar, and see the basis",
    body: "Ask a question of any collection and get the answer with the record it came from. Where Cedar holds no published figure, it says so.",
    icon: CedarIcon,
  },
];

function browserStorage() {
  // Reading window.localStorage itself throws under a storage-denying policy
  // (sandboxed iframe, blocked site data); the callers' fallbacks only help
  // if this helper survives to hand them null.
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

export default function PressGate({ user }) {
  const { login, logout, refreshSession } = useAuth();
  // The page reads as one long scroll on a phone, so its sections arrive as
  // they enter the viewport instead of standing there already.
  const fadeRoot = useFadeIn();
  const [step, setStep] = useState(() => initialPressStep(browserStorage()));
  // Plans or sign-in, one at a time, or NEITHER ON ARRIVAL.
  //
  // This opened on "signin" for any browser that had signed in before, on the
  // theory that a returning visitor came back to get in. The owner's note,
  // 2026-09-14: the panel is the first thing on the page every time and it
  // covers what is behind it. A door that greets a returning reader with a
  // form has decided for them what they came for, and the two tabs are
  // already sitting in the bar where a visitor looks for them. Nothing opens
  // until it is asked for.
  const [panel, setPanel] = useState(null);
  const [code, setCode] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);

  // The collection in hand: the first on the rail on arrival, never none.
  const [selectedId, setSelectedId] = useState(() => SHELVES[0]?.entries[0]?.id ?? null);
  const selected = STOREFRONT_CATALOG.find((entry) => entry.id === selectedId) ?? null;
  const register = useRegister();

  const pick = (entry) => {
    track(EVENT.collectionViewed, { collection: entry.id, shelf: entry.shelf, gated: true });
    setSelectedId(entry.id);
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
      // on every scroll through the hero.
      { threshold: 0.35 },
    );
    observer.observe(stage);
    return () => {
      observer.disconnect();
      document.body.removeAttribute("data-cp-preview-in-view");
    };
  }, []);
  useEffect(() => {
    if (!panel) return undefined;
    const onKey = (event) => { if (event.key === "Escape") setPanel(null); };
    const onDown = (event) => {
      if (panelRef.current?.contains(event.target) || tabsRef.current?.contains(event.target)) return;
      setPanel(null);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onDown);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onDown);
    };
  }, [panel]);

  const go = (next) => {
    setStep(next);
    setError(null);
    setPending(false);
  };

  // Step one: the code and the address it was issued to. Nothing is created
  // yet, so a wrong code costs a message rather than a half-made account.
  const submitCode = async (event) => {
    event.preventDefault();
    setError(null);
    if (!isPlausiblePressCode(code)) {
      setError(
        "That code does not look complete. It is 8 to 32 letters and digits, on your Tribal Business News confirmation.",
      );
      return;
    }
    setPending(true);
    try {
      await validatePressCode({ code: normalizePressCode(code), email });
      setStep(PRESS_STEP.SET_PASSWORD);
    } catch (err) {
      setError(pressSignupError(err?.code, err?.message));
    } finally {
      setPending(false);
    }
  };

  const submitPassword = async (event) => {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      await activatePressAccount({ code: normalizePressCode(code), email, password });
      rememberPressAccount(browserStorage());
      await refreshSession();
    } catch (err) {
      setError(pressSignupError(err?.code, err?.message));
    } finally {
      setPending(false);
    }
  };

  const submitSignIn = async (event) => {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      await login({ email, password });
      rememberPressAccount(browserStorage());
    } catch (err) {
      setError(err?.message || "That sign-in did not work. Check the address and password.");
    } finally {
      setPending(false);
    }
  };

  const toggle = (which) => setPanel((current) => (current === which ? null : which));
  const openSignIn = () => {
    setPanel("signin");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

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
          <span className="cp-door__of">Trusted intelligence for Indian Country</span>
          {user ? (
            // Someone signed in on the wrong membership has one move,
            // upgrading; the bar says who they are and offers the other account.
            <span className="cp-door__user">
              <span className="cp-door__who">Signed in as {user.email} · no Cedar Press</span>
              <a className="cp-btn cp-btn--primary" href={TBN_PLANS_URL} target="_blank" rel="noreferrer">
                View Cedar Press plans <span className="cp-btn__arrow" aria-hidden="true">&#8594;</span>
              </a>
              <button type="button" className="cp-split__linkbtn" onClick={() => logout()}>
                Use a different account
              </button>
            </span>
          ) : (
            // One question, two answers: get Cedar Press, or you already have
            // it. Tabs, so the panel under the bar shows one at a time.
            <div className="cp-door__tabs" role="tablist" aria-label="Get Cedar Press or log in" ref={tabsRef}>
              <button
                type="button"
                id="cp-tab-plans"
                role="tab"
                className="cp-btn cp-btn--quiet cp-door__tab--plans"
                aria-selected={panel === "plans"}
                aria-controls="cp-panel-plans"
                onClick={() => toggle("plans")}
              >
                View plans
              </button>
              <button
                type="button"
                id="cp-tab-signin"
                role="tab"
                className="cp-btn cp-btn--primary"
                aria-selected={panel === "signin"}
                aria-controls="cp-panel-signin"
                onClick={() => toggle("signin")}
              >
                Log in
              </button>
            </div>
          )}
        </div>

        {!user && panel === "plans" ? (
          <div id="cp-panel-plans" role="tabpanel" aria-labelledby="cp-tab-plans" className="cp-door__panel" ref={panelRef}>
            <h2 className="cp-gate__sub">Cedar Press is available exclusively through Tribal Business News.</h2>
            <p className="cp-door__panelp">Upgrade your Tribal Business News membership to access Cedar Press.</p>
            <a className="cp-btn cp-btn--primary cp-btn--wide" href={TBN_PLANS_URL} target="_blank" rel="noreferrer">
              View Cedar Press plans <span className="cp-btn__arrow" aria-hidden="true">&#8594;</span>
            </a>
          </div>
        ) : null}

        {!user && panel === "signin" ? (
          <div id="cp-panel-signin" role="tabpanel" aria-labelledby="cp-tab-signin" className="cp-door__panel" ref={panelRef}>
            {!PRESS_SIGN_IN_AVAILABLE ? (
              // Standalone, provisioned with nothing. There is no account any
              // password could match, so there is no form to offer one to.
              <p className="cp-gate__fine" role="status">{PRESS_DEMO_UNCONFIGURED}</p>
            ) : step === PRESS_STEP.SIGN_IN || !PRESS_ACTIVATION_AVAILABLE ? (
              <>
                <h2 className="cp-gate__sub">Log in with your email and password.</h2>
                <form className="cp-gate__form" onSubmit={submitSignIn}>
                  <input
                    type="email"
                    autoComplete="email"
                    placeholder="Email address"
                    aria-label="Email address"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    required
                  />
                  <input
                    type="password"
                    autoComplete="current-password"
                    placeholder="Password"
                    aria-label="Password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                  />
                  {error ? <p className="cp-gate__error" role="alert">{error}</p> : null}
                  <button type="submit" className="cp-btn cp-btn--primary cp-btn--wide" disabled={pending}>
                    {pending ? "Logging in" : "Log in"}
                  </button>
                </form>
                <p className="cp-gate__aside">
                  <a href={contactHref("Cedar Press password help")}>Forgot password?</a>
                </p>
                {/* The access-code flow only appears once its server routes
                    exist; a form that ends at a 404 is worse than no form.
                    Until then, subscriptions are provisioned and the login
                    above is the whole way in. */}
                {PRESS_ACTIVATION_AVAILABLE ? (
                  <p className="cp-gate__aside">
                    Have an access code?{" "}
                    <button type="button" className="cp-split__linkbtn" onClick={() => go(PRESS_STEP.ACTIVATE)}>
                      Activate Cedar Press
                    </button>
                  </p>
                ) : (
                  <p className="cp-gate__aside">
                    New subscriber? Your account is set up with your Tribal Business News
                    subscription, and your login details arrive by email.
                  </p>
                )}
                {/* No build meta-copy on the door (owner, 2026-09-02). What it
                    said is still true and still recorded where it is
                    load-bearing: pressDemoGate.js's docstring and SECURITY.md. */}
              </>
            ) : step === PRESS_STEP.SET_PASSWORD ? (
              <>
                {/* The code is accepted by this point, so the only thing left is
                    a password. Showing it earlier would have put four fields in
                    front of someone who had not yet been told the code works. */}
                <p className="cp-gate__ok" role="status">
                  Code accepted for {email}. Choose a password to finish.
                </p>
                <form className="cp-gate__form" onSubmit={submitPassword}>
                  <input
                    type="password"
                    autoComplete="new-password"
                    placeholder="Choose a password"
                    aria-label="Choose a password"
                    minLength={12}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                  />
                  {error ? <p className="cp-gate__error" role="alert">{error}</p> : null}
                  <button type="submit" className="cp-btn cp-btn--primary cp-btn--wide" disabled={pending}>
                    {pending ? "Activating" : "Activate Cedar Press"}
                  </button>
                </form>
                <p className="cp-gate__aside">
                  <button type="button" className="cp-split__linkbtn" onClick={() => go(PRESS_STEP.ACTIVATE)}>
                    Use a different code
                  </button>
                </p>
              </>
            ) : (
              <>
                <h2 className="cp-gate__sub">Enter your access code to sign in.</h2>
                <form className="cp-gate__form" onSubmit={submitCode}>
                  <input
                    type="text"
                    inputMode="text"
                    autoComplete="one-time-code"
                    spellCheck={false}
                    className="cp-code"
                    placeholder="Access code"
                    aria-label="Access code"
                    value={code}
                    onChange={(event) => setCode(event.target.value)}
                    onBlur={() => setCode((current) => formatPressCode(current))}
                    required
                  />
                  <input
                    type="email"
                    autoComplete="email"
                    placeholder="Email address"
                    aria-label="Email address"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    required
                  />
                  {error ? <p className="cp-gate__error" role="alert">{error}</p> : null}
                  <button type="submit" className="cp-btn cp-btn--primary cp-btn--wide" disabled={pending}>
                    {pending ? "Checking your code" : "Activate Cedar Press"}
                  </button>
                </form>
                <p className="cp-gate__fine">
                  Each Cedar Press access code is issued to one authorized user and may not be
                  shared.
                </p>
                <p className="cp-gate__aside">
                  Already set a password?{" "}
                  <button type="button" className="cp-split__linkbtn" onClick={() => go(PRESS_STEP.SIGN_IN)}>
                    Log in <span aria-hidden="true">&#8594;</span>
                  </button>
                </p>
              </>
            )}
          </div>
        ) : null}
      </header>

      {/* ── The hero: the promise, and beside it the product ─────────── */}
      <section className="cp-hero3" aria-label="Cedar Press">
        <div className="cp-hero3__in">
          <div className="cp-hero3__copy">
            <p className="cp-kicker cp-fade">Original intelligence collections</p>
            {/* Two messages, on purpose: the door sells the asset, the
                signed-in overview keeps the editorial "Know what's shaping
                Indian Country." */}
            <h1 className="cp-hero3__title cp-fade">
              The <em>data</em> behind Indian Country.
            </h1>
            <p className="cp-hero3__lede cp-fade">
              Original collections built from fragmented records, connected through original
              research, and maintained as Indian Country changes. Every record traces back to the
              document it came from.
            </p>
            <div className="cp-hero3__cta cp-fade">
              <a className="cp-btn cp-btn--primary cp-btn--lg" href={TBN_PLANS_URL} target="_blank" rel="noreferrer">
                View plans <span className="cp-btn__arrow" aria-hidden="true">&#8594;</span>
              </a>
              {user ? null : (
                <button type="button" className="cp-btn cp-btn--quiet cp-btn--lg" onClick={openSignIn}>
                  Log in <span className="cp-btn__arrow" aria-hidden="true">&#8594;</span>
                </button>
              )}
            </div>
            <ul className="cp-hero3__facts cp-fade" aria-label="What Cedar Press holds">
              <li><b>{STOREFRONT_CATALOG.length}</b> collections</li>
              {LAUNCH_ROWS_TOTAL ? <li><b>{LAUNCH_ROWS_TOTAL.toLocaleString("en-US")}</b> records</li> : null}
              {EARLIEST_YEAR ? <li>as far back as <b>{EARLIEST_YEAR}</b></li> : null}
              {recentlyUpdated(1)[0] ? <li>updated <b>{formatUpdated(recentlyUpdated(1)[0].updated)}</b></li> : null}
            </ul>
          </div>

          {/* The product frame. The rail is the twelve collections with
              their marks, one group a shelf; the pane is the one in hand.
              Not `#catalog`: that id is the reader's shelf on /data. */}
          <figure className="cp-hero3__stage cp-fade" ref={previewRef}>
            {/* The specimen sits over the frame's top-right corner rather
                than beside it, which is what makes the hero a layered
                object instead of a headline next to a screenshot. It is the
                SELECTED collection's, so the rail below drives both. */}
            <PressReleaseSpecimen entry={selected} />
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
                <nav className="cp-app__rail" aria-label="The collections">
                  {SHELVES.map(({ tier, entries }) => (
                    <div className="cp-app__group" key={tier.id}>
                      <span className="cp-app__groupcap"><TierName name={tier.name} /></span>
                      <ul className="cp-app__list">
                        {entries.map((entry) => {
                          const on = entry.id === selectedId;
                          return (
                            <li key={entry.id}>
                              <button
                                type="button"
                                className={`cp-app__item${on ? " is-on" : ""}`}
                                aria-pressed={on}
                                onClick={() => pick(entry)}
                                onMouseEnter={() => setSelectedId(entry.id)}
                                onFocus={() => setSelectedId(entry.id)}
                              >
                                <span className="cp-app__mark" aria-hidden="true">{COLLECTION_ICONS[entry.id]}</span>
                                <span className="cp-app__label">
                                  <span className="cp-app__name"><TierName name={entry.short || entry.name} /></span>
                                  {ROWS_LABEL[entry.id] ? <span className="cp-app__rows">{ROWS_LABEL[entry.id]}</span> : null}
                                </span>
                              </button>
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  ))}
                </nav>
                </div>
                <div className="cp-app__pane">
                  {selected ? (
                    <CollectionPreview key={selected.id} entry={selected} tier={TIER_OF[selected.id]} register={register} />
                  ) : null}
                </div>
              </div>
            </div>
            </div>
            <figcaption className="cp-fade">
              A live preview. Each collection shows six of the ten sample records in its
              current release.
            </figcaption>
          </figure>

        </div>

        {/* THE TWELVE, AT A SIZE YOU CAN ACTUALLY POINT AT.
            Its own band under the hero, full page width. Inside the hero's
            split it landed in the right-hand column and every tile shrank to
            one character wide.

            The frame's rail lists all twelve and has always been clickable,
            but the frame renders the real app at 1280px and scales it to fit,
            so a rail row is about seventeen pixels tall in six-point type:
            visible, not pointable. A visitor deciding whether to subscribe
            should be able to see what the twelve are and what each holds.

            Pointing at one drives the frame above and answers in the line
            below, so it works whether or not the frame is still on screen. */}
        <PressDoorCollections
          selectedId={selectedId}
          onPick={pick}
          onPoint={setSelectedId}
        />

        {/* The provenance band: every source system the twelve collections
            name, on a slow run so the breadth reads as breadth rather than
            as a paragraph nobody finishes.

            The run is duplicated and the track translated by half its width,
            which is what makes the loop seamless; the copy is aria-hidden so
            a screen reader hears the list once. Hover or focus stops it, and
            prefers-reduced-motion turns it into a wrapped list (CSS). */}
        <aside className="cp-hero3__proof cp-fade" aria-label="Source systems">
          <div className="cp-hero3__proofhead">
            <Link className="cp-hero3__prooflabel" to={PRESS_METHODS_PATH}>
              Every collection begins with documented source records
            </Link>
            <span className="cp-hero3__proofcount">
              {SOURCE_COUNT} kinds of source · {STOREFRONT_CATALOG.length} collections
            </span>
          </div>
          <div className="cp-hero3__marqwrap">
          <div className="cp-hero3__marquee" style={{ "--run-dur": `${SOURCE_COUNT * 2.4}s` }}>
            <ul className="cp-hero3__run">
              {PRESS_SOURCES.map((source) => <li key={source.name}>{source.name}</li>)}
            </ul>
            <ul className="cp-hero3__run" aria-hidden="true">
              {PRESS_SOURCES.map((source) => <li key={`${source.name}-echo`}>{source.name}</li>)}
            </ul>
          </div>
          </div>
        </aside>
      </section>

      {/* ── The passage: why, on navy, with the photograph ────────────── */}
      <section className="cp-why" aria-labelledby="cp-why-title">
        <div className="cp-why__in">
          <header className="cp-why__head">
            <div>
              <p className="cp-kicker cp-kicker--light cp-fade">What Cedar does with them</p>
              {/* "Records are only the beginning" was cut on the owner's
                  ruling of 2026-09-13, here and on the Methods page. It names
                  a starting point and stops, which describes a gap rather
                  than a product and could sit on any data company's page. The
                  claim underneath is narrower and much harder to copy: the
                  records are abundant, the key that would let them be added
                  up does not exist, and Cedar mints it and maintains it.
                  The lede also opened on a federal contract, which made a
                  twelve-collection product read as a contracting product with
                  eleven extras. It names four kinds of record now. */}
              <h2 className="cp-why__title cp-fade" id="cp-why-title">
                The hard part is knowing who a record is about.
              </h2>
              <p className="cp-why__lede cp-fade">
                A contract names a vendor. A 990 names a filer. A royalty statement names a payee.
                None of them says whether those are one nation or three, and no public system will
                tell you. Cedar reads {SOURCE_COUNT} kinds of source, assigns every organization it
                can resolve a permanent identifier, and maintains that identifier as they rename,
                merge and change hands. That is what makes {LAUNCH_COLLECTION.length} datasets
                answer as one collection.
              </p>
            </div>
            <ul className="cp-why__shelves cp-fade" aria-label="The shelves">
              {SHELVES.map(({ tier, entries }) => (
                <li key={tier.id}>
                  <b><TierName name={tier.name} /></b>
                  <span>{tier.question} {entries.length} collections.</span>
                </li>
              ))}
            </ul>
          </header>
          <div className="cp-why__photo cp-fade" aria-hidden="true">
            <picture>
              <source srcSet="/photo/tribal-flags-sm.webp" media="(max-width: 720px)" />
              <img src="/photo/tribal-flags-wide.webp" alt="" width="1500" height="600" loading="lazy" decoding="async" />
            </picture>
            <p className="cp-why__photolabel">
              <span>Tribal economies</span>
              Governments, enterprises, and the institutions around them
            </p>
          </div>
          <ol className="cp-why__proof">
            {PROOF_POINTS.map((point, i) => (
              <li className="cp-why__item cp-fade" key={point.id}>
                <span className="cp-why__step" aria-hidden="true">{String(i + 1).padStart(2, "0")}</span>
                <span className="cp-why__ic" aria-hidden="true">{point.icon}</span>
                <span className="cp-why__label">{point.label}</span>
                <span className="cp-why__body">{point.body}</span>
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
              Available exclusively through <span>Tribal Business News.</span>
            </h2>
            <p className="cp-ways__lede">
              A Cedar Press membership opens the collections, the research briefs and Cedar. Two
              other relationships need no subscription at all.
            </p>
            <div className="cp-hero3__cta">
              <a className="cp-btn cp-btn--primary cp-btn--lg" href={TBN_PLANS_URL} target="_blank" rel="noreferrer">
                View plans <span className="cp-btn__arrow" aria-hidden="true">&#8594;</span>
              </a>
              {user ? null : (
                <button type="button" className="cp-btn cp-btn--quiet cp-btn--lg" onClick={openSignIn}>
                  Log in <span className="cp-btn__arrow" aria-hidden="true">&#8594;</span>
                </button>
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
                <p>How records are sourced, resolved to Native entities and maintained: the reference to open before citing a number.</p>
                <Link className="cp-ways__act" to={PRESS_METHODS_PATH}>How Cedar builds its collections <span aria-hidden="true">&#8594;</span></Link>
              </div>
            </li>
          </ol>
        </div>
      </section>

      <footer className="cp-door__foot cp-fade">
        <span>
          Built by <a href={LUMECON_URL} target="_blank" rel="noreferrer">Lumecon</a>. Available
          exclusively through <a href={TBN_URL} target="_blank" rel="noreferrer">Tribal Business News</a>.
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

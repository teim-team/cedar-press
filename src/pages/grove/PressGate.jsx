// REVIEW OWNER: Havala
//
// Cedar Press: the way in.
//
// The entrance to a professional intelligence service, not a SaaS login. Left
// side answers "why should I trust this?"; right side does one thing, which is
// get an authorized Tribal Business News member inside. Anything longer about
// method belongs on the methods page, and the one link out is the only route
// to it from here.
//
// Built on the app's own split (.auth-split / .auth-hero in redesign.css), so
// a change to the platform sign-in carries here and the reader never feels
// handed to a different company.
//
// Activation is two steps. Step one is the access code and an email address
// and nothing else; a password is only worth choosing once the code has been
// accepted. Which screen opens is what this browser did last time, so someone
// who has already activated is not asked for a code they have spent.
//
// Tribal Business News owns payment, renewals, upgrades and code issuance.
// There is deliberately no "create account" here: an account exists because an
// entitlement does.
//
// THREE STATES, AND THE COPY HAS TO MATCH
// Connected, this form posts to the platform and the session is a signed,
// HTTP-only cookie. Standalone with a preview account configured, the check
// runs in the reader's browser and the panel says so in as many words — a
// demonstration gate that let someone believe it was access control would be
// the dishonest version of this. Standalone with nothing configured, there is
// no form at all, because a form that can only fail is worse than a sentence
// explaining why there is none.

import { useState } from "react";
import { Link } from "react-router";

import { useAuth } from "../../context/useAuth";
import { useFadeIn } from "../../features/grove/useFadeIn";
import { activatePressAccount, validatePressCode } from "../../api";
import { TBN_PLANS_URL } from "../../features/grove/pressArticles";
import {
  PRESS_METHODS_PATH,
  PRESS_REQUEST_PATH,
  PRESS_RESEARCH_PATH,
} from "../../features/grove/pressRoutes";
import {
  PRESS_DEMO_GATE_ACTIVE,
  PRESS_DEMO_NOTICE,
  PRESS_DEMO_UNCONFIGURED,
  PRESS_SIGN_IN_AVAILABLE,
} from "../../features/grove/pressDemoGate";
import {
  PRESS_ACTIVATION_AVAILABLE,
  PRESS_STEP,
  formatPressCode,
  hasPressAccount,
  initialPressStep,
  isPlausiblePressCode,
  normalizePressCode,
  pressSignupError,
  rememberPressAccount,
} from "../../features/grove/pressSignup";
import {
  AcademicIcon,
  CedarIcon,
  CredibleResearchIcon,
  InsightsIcon,
  InstitutionIcon,
  OriginalCollectionsIcon,
} from "./pressGateIcons";
import {
  CREDIBILITY_DISCLAIMER,
  CREDIBILITY_STRIP,
} from "../../features/grove/pressMethod";
import { NATIVE_LINKAGE, PRESS_CATALOG } from "../../features/grove/pressCatalog";
import { PressCedarFab } from "./PressCedarFab";

// The Cedar Press shelves by name, for the door. Names only, from the
// catalog itself so a new collection appears here the day it ships; the
// Grove-exclusive shelf stays inside, since it is a different product's
// pitch. What the names mean is Cedar's job, one click away.
const CATALOG_NAMES = PRESS_CATALOG.filter((entry) => entry.shelf !== "grove").map(
  (entry) => entry.short,
);

const STRIP_ICONS = { institution: InstitutionIcon, academic: AcademicIcon };

// The four pillars, in the order the supporting sentence names them: what the
// data is, what is made from it, why it can be trusted, and Cedar.
const PROOF_POINTS = [
  {
    id: "collections",
    label: "Original Collections",
    body: "Built from fragmented records and sources that have never been assembled into a single collection anywhere else.",
    icon: OriginalCollectionsIcon,
  },
  {
    id: "insights",
    label: "Data-Driven Insights",
    body: "Original analysis reveals the institutions, industries and decisions shaping Indian Country.",
    icon: InsightsIcon,
  },
  {
    id: "credible",
    label: "Credible Research",
    body: "Built by Indigenous researchers with Federal Reserve experience, leading academic backgrounds and decades of work in Indian Country.",
    icon: CredibleResearchIcon,
  },
  {
    id: "cedar",
    label: "Cedar, Your AI Economic Analyst",
    body: "Ask questions across Cedar Press and explore the stories, sources, collections and trends behind the data.",
    icon: CedarIcon,
  },
];

// Questions the gate suggests to Cedar: enough to show what the product
// answers, none requiring data the visitor is not yet entitled to see.
const GATE_CEDAR_EXAMPLES = [
  "What does Cedar Press cover?",
  "Which collections track federal contracting?",
  "What is in the Individually Owned Native Businesses collection?",
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
  // The gate reads as one long scroll on a phone, so its sections arrive as
  // they enter the viewport instead of standing there already.
  const fadeRoot = useFadeIn();
  const [step, setStep] = useState(() => initialPressStep(browserStorage()));
  // Plans or sign-in, one at a time. Stacking both read as one long column
  // of competing calls to action; the panel opens on the side of the hinge
  // this browser is likely on (a remembered account lands on Log in, a new
  // visitor sees the plans first).
  const [panel, setPanel] = useState(() =>
    hasPressAccount(browserStorage()) ? "signin" : "plans",
  );
  const [code, setCode] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);

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

  return (
    <main className="empty-state auth-split cp-split" ref={fadeRoot}>
      <aside className="auth-hero cp-hero2">
        <span className="auth-hero__glow auth-hero__glow--a" aria-hidden="true" />
        <span className="auth-hero__glow auth-hero__glow--b" aria-hidden="true" />
        {/* One ripple, and it is ours. The panel used to carry two nested
            contour rises that read as generic circles beside the mark; the
            mark's own asymmetric rings are the ripple now, breathing on a
            slow cycle so the panel is alive without anything sliding around.

            The all-teal mark, which is the current one. */}
        <img
          className="auth-hero__mark cp-hero2__ripple"
          src="/brand/lumecon-logo-mark-teal.png"
          alt=""
          aria-hidden="true"
        />
        <div className="auth-hero__inner cp-hero2__inner">
          <span className="cp-split__brand">Cedar Press</span>
          <p className="cp-hero2__tagline cp-fade">Trusted intelligence for Indian Country.</p>
          {/* Two messages, on purpose: the door sells the asset ("this is
              the data you should want access to"), the signed-in overview
              keeps the editorial "Know what's shaping Indian Country."
              ("here's what you can do with it"). Neither repeats the tier
              lines: the shelves explain the ladder. */}
          <h1 className="auth-hero__headline cp-hero2__headline cp-fade">
            The data behind Indian Country.
          </h1>
          <p className="auth-hero__lede cp-hero2__lede cp-fade">
            Original collections built from fragmented records, connected through original
            research, and maintained as Indian Country changes.
          </p>
          <ul className="cp-proof cp-fade">
            {PROOF_POINTS.map((point) => (
              <li className="cp-proof__item" key={point.id}>
                {/* The title leads and holds the tile in both states; below
                    it, only the icon and the paragraph trade places on
                    hover. The swap is opacity, never display:none, so the
                    paragraph stays in the accessibility tree, and hoverless
                    devices show it outright. */}
                <span className="cp-proof__label">{point.label}</span>
                <span className="cp-proof__swap">
                  <span className="cp-proof__ic" aria-hidden="true">{point.icon}</span>
                  <span className="cp-proof__body">{point.body}</span>
                </span>
              </li>
            ))}
          </ul>
          {/* The shelves, by name: a prospect who heard "Cedar Press" at a
              conference should learn what is actually inside from the door,
              and eleven specific collection names say more than any
              adjective. Cedar is the way to ask what any of them means. */}
          <div className="cp-cats cp-fade">
            <p className="cp-cats__head">The intelligence inside</p>
            <p className="cp-cats__names">
              {CATALOG_NAMES.map((name, index) => (
                <span key={name}>
                  {index > 0 ? <span className="cp-cats__dot" aria-hidden="true"> · </span> : null}
                  {name}
                </span>
              ))}
            </p>
            {/* The sentence that separates these from open-data keyword
                filters. One source of truth with the Data page's linkage
                copy, so the door never promises what the shelf retracts. */}
            <p className="cp-cats__how">{NATIVE_LINKAGE.door}</p>
            <button
              type="button"
              className="cp-cats__cedar"
              onClick={() => window.dispatchEvent(new CustomEvent("cedar:open"))}
            >
              Ask Cedar what Cedar Press can answer <span aria-hidden="true">&#8594;</span>
            </button>
          </div>
          {/* The cards state the idea; the strip is what proves it. Text
              only: a row of institutional logos reads as sponsorship, which
              none of these have given, so the disclaimer travels with it. */}
          <p className="cp-cred__head cp-fade">Team experience</p>
          <div className="cp-cred cp-fade">
            {CREDIBILITY_STRIP.map((group) => (
              <div className="cp-cred__group" key={group.id}>
                <span className="cp-cred__ic" aria-hidden="true">{STRIP_ICONS[group.kind]}</span>
                <span className="cp-cred__names">{group.names.join(" · ")}</span>
              </div>
            ))}
          </div>
          <p className="cp-cred__note cp-fade">{CREDIBILITY_DISCLAIMER}</p>
          <Link className="cp-split__method cp-fade" to={PRESS_METHODS_PATH}>
            How Cedar builds its collections <span aria-hidden="true">&#8594;</span>
          </Link>
        </div>
      </aside>

      <div className="auth-editorial">
        <div className="cp-split__form">
          {/* On phones the form panel leads the page (the hero follows), so
              the wordmark opens it; on desktop the hero carries the brand and
              this stays hidden. */}
          <span className="cp-split__brand cp-split__brand--form" aria-hidden="true">
            Cedar Press
          </span>
          {/* "Through", not "to subscribers": the first sounds like every
              subscriber gets Cedar Press, and the upgrade line right below
              says otherwise. The distribution relationship is the claim —
              once. The "Built by Lumecon / available through TBN" eyebrow
              that used to sit above this title said the same thing in the
              same breath at every width, so the title carries it alone;
              who built it is the hero's and the footer's line. */}
          <h2 className="auth-editorial__title">
            Cedar Press is available exclusively through Tribal Business News.
          </h2>
          {user ? (
            <>
              {/* Someone signed in on the wrong membership has one move,
                  upgrading, so the box stands alone with no hinge. */}
              <div className="cp-split__upgrade">
                <p>Upgrade your Tribal Business News membership to access Cedar Press.</p>
                <a className="gv-btn gv-btn--primary" href={TBN_PLANS_URL} target="_blank" rel="noreferrer">
                  View Cedar Press plans <span aria-hidden="true">&#8594;</span>
                </a>
              </div>
              <p className="cp-gate__signedin">
                Signed in as {user.email} · this membership does not include Cedar Press
              </p>
              <button type="button" className="gv-btn gv-btn--quiet" onClick={() => logout()}>
                Use a different account
              </button>
            </>
          ) : (
            <>
              {/* One question, two answers: get Cedar Press, or you already
                  have it. A tab shows one at a time instead of stacking the
                  plans button over the sign-in forms as competing calls. */}
              <div className="cp-tabs" role="tablist" aria-label="Get Cedar Press or log in">
                <button
                  type="button"
                  id="cp-tab-plans"
                  role="tab"
                  className="cp-tab"
                  aria-selected={panel === "plans"}
                  aria-controls="cp-panel-plans"
                  onClick={() => setPanel("plans")}
                >
                  View plans
                </button>
                <button
                  type="button"
                  id="cp-tab-signin"
                  role="tab"
                  className="cp-tab"
                  aria-selected={panel === "signin"}
                  aria-controls="cp-panel-signin"
                  onClick={() => setPanel("signin")}
                >
                  Log in
                </button>
              </div>
              {panel === "plans" ? (
                <div
                  id="cp-panel-plans"
                  role="tabpanel"
                  aria-labelledby="cp-tab-plans"
                  className="cp-tabpanel"
                >
                  <div className="cp-split__upgrade">
                    <p>Upgrade your Tribal Business News membership to access Cedar Press.</p>
                    <a className="gv-btn gv-btn--primary" href={TBN_PLANS_URL} target="_blank" rel="noreferrer">
                      View Cedar Press plans <span aria-hidden="true">&#8594;</span>
                    </a>
                  </div>
                </div>
              ) : (
                <div
                  id="cp-panel-signin"
                  role="tabpanel"
                  aria-labelledby="cp-tab-signin"
                  className="cp-tabpanel"
                >
                  {!PRESS_SIGN_IN_AVAILABLE ? (
            // Standalone, provisioned with nothing. There is no account any
            // password could match, so there is no form to offer one to.
            <p className="cp-gate__fine" role="status">{PRESS_DEMO_UNCONFIGURED}</p>
          ) : step === PRESS_STEP.SIGN_IN || !PRESS_ACTIVATION_AVAILABLE ? (
            <>
              <h3 className="cp-gate__sub">Log in with your email and password.</h3>
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
                <button type="submit" className="gv-btn gv-btn--primary" disabled={pending}>
                  {pending ? "Logging in" : "Log in"}
                </button>
              </form>
              <p className="cp-gate__aside">
                <a href="mailto:contact@lumecon.ai?subject=Cedar%20Press%20password%20help">Forgot password?</a>
              </p>
              {/* The access-code flow only appears once its server routes
                  exist; a form that ends at a 404 is worse than no form.
                  Until then, subscriptions are provisioned and the login
                  above is the whole way in. */}
              {PRESS_ACTIVATION_AVAILABLE ? (
                <p className="cp-gate__aside">
                  Have an access code?{" "}
                  <button
                    type="button"
                    className="cp-split__linkbtn"
                    onClick={() => go(PRESS_STEP.ACTIVATE)}
                  >
                    Activate Cedar Press
                  </button>
                </p>
              ) : (
                <p className="cp-gate__aside">
                  New subscriber? Your account is set up with your Tribal Business News
                  subscription, and your login details arrive by email.
                </p>
              )}
              {/* Said on the page, not only in the code. On a build with no
                  server the password is checked in the reader's own browser,
                  and everything the check reads is in the bundle they already
                  downloaded — so this is a demonstration gate and the panel
                  must not let anyone mistake it for access control. It
                  disappears the moment the deployment connects, because the
                  platform's session is what checks then. */}
              {PRESS_DEMO_GATE_ACTIVE ? (
                <p className="cp-gate__fine">{PRESS_DEMO_NOTICE}</p>
              ) : null}
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
                <button type="submit" className="gv-btn gv-btn--primary" disabled={pending}>
                  {pending ? "Activating" : "Activate Cedar Press"}
                </button>
              </form>
              <p className="cp-gate__aside">
                <button
                  type="button"
                  className="cp-split__linkbtn"
                  onClick={() => go(PRESS_STEP.ACTIVATE)}
                >
                  Use a different code
                </button>
              </p>
            </>
          ) : (
            <>
              <h3 className="cp-gate__sub">Enter your access code to sign in.</h3>
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
                <button type="submit" className="gv-btn gv-btn--primary" disabled={pending}>
                  {pending ? "Checking your code" : "Activate Cedar Press"}
                </button>
              </form>
              <p className="cp-gate__fine">
                Each Cedar Press access code is issued to one authorized user and may not be
                shared.
              </p>
              <p className="cp-gate__aside">
                Already set a password?{" "}
                <button
                  type="button"
                  className="cp-split__linkbtn"
                  onClick={() => go(PRESS_STEP.SIGN_IN)}
                >
                  Log in <span aria-hidden="true">&#8594;</span>
                </button>
              </p>
            </>
          )}
                </div>
              )}
            </>
          )}
          {/* The gate is the public front door, not only a paywall. Three
              relationships with Cedar Press exist — subscribing through TBN,
              project-scoped research access, and a tribal government's right
              to its own records — and the second two require no subscription,
              so they are named here where a non-subscriber actually arrives.
              Both pages are public. */}
          <div className="cp-gate__other cp-fade">
            <span className="cp-gate__othercap">Other ways to work with Cedar Press</span>
            {/* Governance before commerce: a nation's right to its own
                records leads, and the project pathway follows. */}
            <Link className="cp-gate__otherlink" to={PRESS_REQUEST_PATH}>
              <b>Tribal government data requests <span aria-hidden="true">&#8594;</span></b>
              <span className="cp-gate__otherdesc">
                Federally recognized tribal governments can request and review the Cedar records
                associated with their nation. No subscription required.
              </span>
            </Link>
            <Link className="cp-gate__otherlink" to={PRESS_RESEARCH_PATH}>
              <b>Research access <span aria-hidden="true">&#8594;</span></b>
              <span className="cp-gate__otherdesc">
                For researchers, journalists, students, nonprofits and public-interest projects
                needing one or two collections for a defined project.
              </span>
            </Link>
          </div>
        </div>
      </div>
      {/* Cedar meets the visitor at the door. Everyone here is outside the
          product — signed out, or signed in on a membership without Cedar
          Press — so Cedar explains and converts rather than answering past
          the paywall, and the notice names the reader's actual next step. */}
      <PressCedarFab gated={user ? "unentitled" : "signedout"} examples={GATE_CEDAR_EXAMPLES} />
    </main>
  );
}

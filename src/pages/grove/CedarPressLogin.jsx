// REVIEW OWNER: Havala
//
// The workspace's way in: app.cedarpress.ai/login. The marketing site's Sign in
// lands here, and so does any signed-out visit to a page behind the gate, with
// `?next=` carrying where the visitor was going. New readers subscribe at
// /subscribe and choose their password from the emailed account link.
import { AccountPage } from "./AccountPage.jsx";
import { cloneElement, useEffect, useId, useState } from "react";
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from "react-router";

import { confirmPasswordReset, requestPasswordReset } from "../../api";
import { useAuth } from "../../context/useAuth";
import { contactHref } from "../../features/grove/appLink.js";
import { canReadCedarPress } from "../../features/grove/pressAccess";
import { isConnected } from "../../config.js";
import { safeNext } from "../../features/grove/pressSessionNavigation.js";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";


// The public site is another host in production; a dev server has only itself.
const MARKETING_URL = import.meta.env.DEV ? "/" : "https://cedarpress.ai";

const PITCH = [
  "Maintained collections on federal funding, contracting, deals, policy, giving, land and Native enterprise ownership",
  "Cedar, the AI economic analyst",
  "Source records behind every figure",
  "Downloadable spreadsheets",
];

const STEP = Object.freeze({ SIGN_IN: "sign-in", FORGOT: "forgot", RESET: "reset" });

function Field({ label, aside = null, children }) {
  const id = useId();
  return (
    <div className="cp-login__field">
      <div className="cp-login__row"><label htmlFor={id}>{label}</label>{aside}</div>
      {cloneElement(children, { id })}
    </div>
  );
}

export default function CedarPressLogin() {
  useDocumentTitle("Sign in");
  const { user, loading, login, refreshSession } = useAuth();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  const location = useLocation();
  const navigate = useNavigate();
  // The emailed link carries the token in the fragment, which never reaches a server log.
  const linkedToken = new URLSearchParams(location.hash.slice(1)).get("reset");
  const [resetToken, setResetToken] = useState(linkedToken);
  const [step, setStep] = useState(linkedToken ? STEP.RESET : STEP.SIGN_IN);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  const [resetSent, setResetSent] = useState(false);

  // A link opened in a tab already on this page changes only the fragment, so
  // the page does not remount and the initial state above never sees it.
  if (linkedToken && linkedToken !== resetToken) {
    setResetToken(linkedToken);
    setStep(STEP.RESET);
    setError(null);
  }

  useEffect(() => {
    document.head.querySelector('meta[name="robots"]')?.setAttribute("content", "noindex");
  }, []);

  // The token is held in state, so it can leave the address bar and history.
  useEffect(() => {
    if (linkedToken) navigate({ pathname: location.pathname, search: location.search }, { replace: true });
  }, [linkedToken, location.pathname, location.search, navigate]);

  if (!loading && user) return <Navigate to={canReadCedarPress(user) ? next : "/settings"} replace />;

  const go = (to) => {
    setStep(to);
    setError(null);
    setResetSent(false);
  };

  const run = (action, describe = (err) => err?.message) => async (event) => {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      await action();
    } catch (err) {
      setError(describe(err) || "That did not work. Check the details and try again.");
    } finally {
      setPending(false);
    }
  };

  const submitSignIn = run(async () => {
    const session = await login({ email, password });
    if (!canReadCedarPress(session)) navigate("/settings");
  });

  const submitForgot = run(async () => {
    await requestPasswordReset({ email, next });
    setResetSent(true);
  });

  const submitReset = run(async () => {
    await confirmPasswordReset({ token: resetToken, newPassword: password });
    await refreshSession();
  });

  const signingIn = step === STEP.SIGN_IN || !isConnected();
  const emailField = (
    <Field label="Work email">
      <input type="email" autoComplete="email" placeholder="you@organization.org"
        value={email} onChange={(event) => setEmail(event.target.value)} required />
    </Field>
  );
  const errorLine = error ? <p className="cp-gate__error" role="alert">{error}</p> : null;

  return (
    <AccountPage>
        <div className="cp-login__card">
          {!isConnected() && !import.meta.env.DEV ? (
            <>
              <h1 className="cp-login__h">Sign in</h1>
              <p className="cp-gate__fine" role="status">Sign-in is not available yet.</p>
            </>
          ) : signingIn ? (
            <>
              <h1 className="cp-login__h">Welcome back.</h1>
              <p className="cp-login__lede">Sign in to Cedar Press.</p>
              {!isConnected() ? (
                <p className="cp-gate__ok" role="status">
                  Dev server, not connected to the API, so signing in will fail. Run <code>npm run dev:connected</code> with the API running (docs/CONNECTING.md).
                </p>
              ) : null}
              <form className="cp-gate__form" onSubmit={submitSignIn}>
                {emailField}
                <Field label="Password" aside={isConnected()
                  ? <button type="button" className="cp-split__linkbtn" onClick={() => go(STEP.FORGOT)}>Forgot password?</button>
                  : <a href={contactHref("Cedar Press password help")}>Forgot password?</a>}>
                  <input type="password" autoComplete="current-password" value={password}
                    onChange={(event) => setPassword(event.target.value)} required />
                </Field>
                {errorLine}
                <button type="submit" className="cp-btn cp-btn--primary cp-btn--wide" disabled={pending}>
                  {pending ? "Signing in" : "Sign in"}
                </button>
              </form>
              <p className="cp-login__terms">By continuing, you agree to our Terms of Service and acknowledge our Privacy Policy.</p>
            </>
          ) : step === STEP.FORGOT ? (
            <>
              <h1 className="cp-login__h">Reset your password</h1>
              {resetSent ? (
                <p className="cp-gate__ok" role="status">
                  If {email} has a Cedar Press account, a reset link is on its way. The link works once, within an hour.
                </p>
              ) : (
                <>
                  <p className="cp-login__lede">Enter your work email and we will send you a link to choose a new password.</p>
                  <form className="cp-gate__form" onSubmit={submitForgot}>
                    {emailField}
                    {errorLine}
                    <button type="submit" className="cp-btn cp-btn--primary cp-btn--wide" disabled={pending}>
                      {pending ? "Sending" : "Send reset link"}
                    </button>
                  </form>
                </>
              )}
              <p className="cp-gate__aside">
                <button type="button" className="cp-split__linkbtn" onClick={() => go(STEP.SIGN_IN)}>Back to log in</button>
              </p>
              <p className="cp-gate__aside"><a href={contactHref("Cedar Press password help")}>Contact us for help</a></p>
            </>
          ) : (
            <>
              <h1 className="cp-login__h">Choose a new password</h1>
              <form className="cp-gate__form" onSubmit={submitReset}>
                <Field label="New password">
                  <input type="password" autoComplete="new-password" placeholder="10 or more characters"
                    minLength={10} value={password} onChange={(event) => setPassword(event.target.value)} required />
                </Field>
                {errorLine}
                <button type="submit" className="cp-btn cp-btn--primary cp-btn--wide" disabled={pending}>
                  {pending ? "Saving" : "Save and log in"}
                </button>
              </form>
              <p className="cp-gate__aside">
                <button type="button" className="cp-split__linkbtn" onClick={() => go(STEP.FORGOT)}>Request a new link</button>
              </p>
            </>
          )}
        </div>
        {!user && signingIn ? (
          <section className="cp-login__pitch" aria-labelledby="cp-login-pitch">
            <p className="cp-login__pitch-kicker">Not a Cedar Press subscriber?</p>
            <h2 id="cp-login-pitch">See what you&rsquo;re missing</h2>
            <p>Trusted intelligence for Indian Country.</p>
            <ul>
              {PITCH.map((line) => <li key={line}>{line}</li>)}
            </ul>
            <div className="cp-login__pitch-actions">
              <a className="cp-btn cp-btn--quiet" href={MARKETING_URL}>Learn more</a>
              <Link className="cp-btn cp-btn--primary" to="/subscribe">Create an account</Link>
            </div>
          </section>
        ) : null}
        <p className="cp-login__back"><a href={MARKETING_URL}>&larr; Back to Cedar Press</a></p>
    </AccountPage>
  );
}

// REVIEW OWNER: Havala
//
// The workspace's way in: app.cedarpress.ai/login. The marketing site's Log in
// lands here, and so does any signed-out visit to a page behind the gate, with
// `?next=` carrying where the visitor was going. Activation is the sign-up:
// Tribal Business News issues the code, and the password is chosen here.
import { cloneElement, useEffect, useId, useState } from "react";
import { Navigate, useLocation, useNavigate, useSearchParams } from "react-router";

import { activatePressAccount, confirmPasswordReset, requestPasswordReset, validatePressCode } from "../../api";
import { useAuth } from "../../context/useAuth";
import { EARLY_ACCESS_HREF, EARLY_ACCESS_LABEL, contactHref } from "../../features/grove/appLink.js";
import { canReadCedarPress } from "../../features/grove/pressAccess";
import { isConnected } from "../../config.js";
import { safeNext } from "../../features/grove/pressSessionNavigation.js";
import {
  PRESS_ACTIVATION_AVAILABLE,
  PRESS_STEP,
  formatPressCode,
  isPlausiblePressCode,
  normalizePressCode,
  pressSignupError,
} from "../../features/grove/pressSignup";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";

const MARK = "/brand/lumecon-logo-mark-teal.png";
// The public site is another host in production; a dev server has only itself.
const MARKETING_URL = import.meta.env.DEV ? "/" : "https://cedarpress.ai";

const describeSignup = (err) => pressSignupError(err?.code, err?.message);

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
  useDocumentTitle("Log in");
  const { user, loading, login, refreshSession } = useAuth();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  const location = useLocation();
  const navigate = useNavigate();
  // The emailed link carries the token in the fragment, which never reaches a server log.
  const linkedToken = new URLSearchParams(location.hash.slice(1)).get("reset");
  const [resetToken, setResetToken] = useState(linkedToken);
  const [step, setStep] = useState(linkedToken ? PRESS_STEP.RESET : PRESS_STEP.SIGN_IN);
  const [code, setCode] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  const [resetSent, setResetSent] = useState(false);

  // A link opened in a tab already on this page changes only the fragment, so
  // the page does not remount and the initial state above never sees it.
  if (linkedToken && linkedToken !== resetToken) {
    setResetToken(linkedToken);
    setStep(PRESS_STEP.RESET);
    setError(null);
  }

  useEffect(() => {
    document.head.querySelector('meta[name="robots"]')?.setAttribute("content", "noindex");
  }, []);

  // The token is held in state, so it can leave the address bar and history.
  useEffect(() => {
    if (linkedToken) navigate({ pathname: location.pathname, search: location.search }, { replace: true });
  }, [linkedToken, location.pathname, location.search, navigate]);

  if (!loading && canReadCedarPress(user)) return <Navigate to={next} replace />;

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
    if (!canReadCedarPress(session)) throw new Error("This account does not include Cedar Press.");
  });

  const submitCode = run(async () => {
    if (!isPlausiblePressCode(code)) {
      throw new Error("That code does not look complete. It is 8 to 32 letters and digits, on your Tribal Business News confirmation.");
    }
    await validatePressCode({ code: normalizePressCode(code), email });
    setStep(PRESS_STEP.SET_PASSWORD);
  }, describeSignup);

  const submitPassword = run(async () => {
    await activatePressAccount({ code: normalizePressCode(code), email, password });
    await refreshSession();
  }, describeSignup);

  const submitForgot = run(async () => {
    await requestPasswordReset({ email });
    setResetSent(true);
  });

  const submitReset = run(async () => {
    await confirmPasswordReset({ token: resetToken, newPassword: password });
    await refreshSession();
  });

  const signingIn = step === PRESS_STEP.SIGN_IN || !PRESS_ACTIVATION_AVAILABLE;
  const emailField = (
    <Field label="Work email">
      <input type="email" autoComplete="email" placeholder="you@organization.org"
        value={email} onChange={(event) => setEmail(event.target.value)} required />
    </Field>
  );
  const errorLine = error ? <p className="cp-gate__error" role="alert">{error}</p> : null;

  return (
    <div className="teim-rd teim-rd--paper cp-login">
      <aside className="cp-login__side" aria-hidden="true">
        <img className="cp-login__mark" src={MARK} alt="" />
        <p className="cp-login__tag">Know what&rsquo;s shaping Indian Country.</p>
        <p className="cp-login__sub">Original collections, research briefs and Cedar, the AI economic analyst, in one workspace.</p>
      </aside>
      <main id="cp-main" className="cp-login__main">
        <a className="cp-login__brand" href={MARKETING_URL}>
          <img src={MARK} alt="" width="28" height="28" />
          <span>Cedar Press</span>
        </a>
        <div className="cp-login__card">
          {!isConnected() && !import.meta.env.DEV ? (
            <>
              <h1 className="cp-login__h">Log in</h1>
              <p className="cp-gate__fine" role="status">Sign-in is not available yet.</p>
            </>
          ) : signingIn ? (
            <>
              <h1 className="cp-login__h">Log in to Cedar Press</h1>
              <p className="cp-login__lede">Enter your work email and password to continue.</p>
              {!isConnected() ? (
                <p className="cp-gate__ok" role="status">
                  Dev server, not connected to the API, so signing in will fail. Run <code>npm run dev:connected</code> with the API running (docs/CONNECTING.md).
                </p>
              ) : null}
              <form className="cp-gate__form" onSubmit={submitSignIn}>
                {emailField}
                <Field label="Password" aside={PRESS_ACTIVATION_AVAILABLE
                  ? <button type="button" className="cp-split__linkbtn" onClick={() => go(PRESS_STEP.FORGOT)}>Forgot password?</button>
                  : <a href={contactHref("Cedar Press password help")}>Forgot password?</a>}>
                  <input type="password" autoComplete="current-password" value={password}
                    onChange={(event) => setPassword(event.target.value)} required />
                </Field>
                {errorLine}
                <button type="submit" className="cp-btn cp-btn--primary cp-btn--wide" disabled={pending}>
                  {pending ? "Logging in" : "Log in"}
                </button>
              </form>
              {PRESS_ACTIVATION_AVAILABLE ? (
                <>
                  <p className="cp-login__or"><span>or</span></p>
                  <button type="button" className="cp-btn cp-btn--quiet cp-btn--wide" onClick={() => go(PRESS_STEP.ACTIVATE)}>
                    Activate with an access code
                  </button>
                </>
              ) : null}
            </>
          ) : step === PRESS_STEP.FORGOT ? (
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
                <button type="button" className="cp-split__linkbtn" onClick={() => go(PRESS_STEP.SIGN_IN)}>Back to log in</button>
              </p>
              <p className="cp-gate__aside"><a href={contactHref("Cedar Press password help")}>Contact us for help</a></p>
            </>
          ) : step === PRESS_STEP.RESET ? (
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
                <button type="button" className="cp-split__linkbtn" onClick={() => go(PRESS_STEP.FORGOT)}>Request a new link</button>
              </p>
            </>
          ) : step === PRESS_STEP.SET_PASSWORD ? (
            <>
              <h1 className="cp-login__h">Choose a password</h1>
              <p className="cp-gate__ok" role="status">Code accepted for {email}.</p>
              <form className="cp-gate__form" onSubmit={submitPassword}>
                <Field label="Choose a password">
                  <input type="password" autoComplete="new-password" placeholder="10 or more characters"
                    minLength={10} value={password} onChange={(event) => setPassword(event.target.value)} required />
                </Field>
                {errorLine}
                <button type="submit" className="cp-btn cp-btn--primary cp-btn--wide" disabled={pending}>
                  {pending ? "Activating" : "Activate Cedar Press"}
                </button>
              </form>
              <p className="cp-gate__aside">
                <button type="button" className="cp-split__linkbtn" onClick={() => go(PRESS_STEP.ACTIVATE)}>Use a different code</button>
              </p>
            </>
          ) : (
            <>
              <h1 className="cp-login__h">Activate Cedar Press</h1>
              <form className="cp-gate__form" onSubmit={submitCode}>
                <Field label="Access code">
                  <input type="text" autoComplete="one-time-code" spellCheck={false} className="cp-code"
                    value={code} onChange={(event) => setCode(event.target.value)}
                    onBlur={() => setCode((current) => formatPressCode(current))} required />
                </Field>
                {emailField}
                {errorLine}
                <button type="submit" className="cp-btn cp-btn--primary cp-btn--wide" disabled={pending}>
                  {pending ? "Checking your code" : "Continue"}
                </button>
              </form>
              <p className="cp-gate__fine">
                Each access code is issued to one authorized user through Tribal Business News and may not be shared.
              </p>
              <p className="cp-gate__aside">
                Already set a password?{" "}
                <button type="button" className="cp-split__linkbtn" onClick={() => go(PRESS_STEP.SIGN_IN)}>Log in</button>
              </p>
              <p className="cp-gate__aside"><a href={EARLY_ACCESS_HREF}>{EARLY_ACCESS_LABEL}</a></p>
            </>
          )}
        </div>
        <p className="cp-login__back"><a href={MARKETING_URL}>&larr; Back to Cedar Press</a></p>
      </main>
    </div>
  );
}

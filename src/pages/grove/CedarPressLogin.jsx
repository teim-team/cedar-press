// REVIEW OWNER: Havala
//
// The workspace's way in: app.cedarpress.ai/login. The marketing site's Log in
// lands here, and so does any signed-out visit to a page behind the gate, with
// `?next=` carrying where the visitor was going. Activation is the sign-up:
// Tribal Business News issues the code, and the password is chosen here.
import { useEffect, useState } from "react";
import { Navigate, useSearchParams } from "react-router";

import { activatePressAccount, validatePressCode } from "../../api";
import { useAuth } from "../../context/useAuth";
import { EARLY_ACCESS_HREF, EARLY_ACCESS_LABEL, contactHref } from "../../features/grove/appLink.js";
import { canReadCedarPress } from "../../features/grove/pressAccess";
import { PRESS_DEMO_UNCONFIGURED, PRESS_SIGN_IN_AVAILABLE } from "../../features/grove/pressDemoGate";
import { safeNext } from "../../features/grove/pressSessionNavigation.js";
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
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";

const MARK = "/brand/lumecon-logo-mark-teal.png";
const MARKETING_URL = "https://cedarpress.ai";

const describeSignup = (err) => pressSignupError(err?.code, err?.message);

function browserStorage() {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export default function CedarPressLogin() {
  useDocumentTitle("Log in");
  const { user, loading, login, refreshSession } = useAuth();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  const [step, setStep] = useState(() => initialPressStep(browserStorage(), { signInRequested: true }));
  const [code, setCode] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    document.head.querySelector('meta[name="robots"]')?.setAttribute("content", "noindex");
  }, []);

  if (!loading && canReadCedarPress(user)) return <Navigate to={next} replace />;

  const go = (to) => {
    setStep(to);
    setError(null);
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
    rememberPressAccount(browserStorage());
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
    rememberPressAccount(browserStorage());
    await refreshSession();
  }, describeSignup);

  const signingIn = step === PRESS_STEP.SIGN_IN || !PRESS_ACTIVATION_AVAILABLE;
  const emailField = (
    <input type="email" autoComplete="email" placeholder="Email address" aria-label="Email address"
      value={email} onChange={(event) => setEmail(event.target.value)} required />
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
          {!PRESS_SIGN_IN_AVAILABLE ? (
            <p className="cp-gate__fine" role="status">{PRESS_DEMO_UNCONFIGURED}</p>
          ) : signingIn ? (
            <>
              <h1 className="cp-login__h">Log in</h1>
              <form className="cp-gate__form" onSubmit={submitSignIn}>
                {emailField}
                <input type="password" autoComplete="current-password" placeholder="Password" aria-label="Password"
                  value={password} onChange={(event) => setPassword(event.target.value)} required />
                {errorLine}
                <button type="submit" className="cp-btn cp-btn--primary cp-btn--wide" disabled={pending}>
                  {pending ? "Logging in" : "Log in"}
                </button>
              </form>
              <p className="cp-gate__aside"><a href={contactHref("Cedar Press password help")}>Forgot password?</a></p>
              {PRESS_ACTIVATION_AVAILABLE ? (
                <p className="cp-gate__aside">
                  New to Cedar Press?{" "}
                  <button type="button" className="cp-split__linkbtn" onClick={() => go(PRESS_STEP.ACTIVATE)}>
                    Activate with an access code
                  </button>
                </p>
              ) : null}
            </>
          ) : step === PRESS_STEP.SET_PASSWORD ? (
            <>
              <h1 className="cp-login__h">Choose a password</h1>
              <p className="cp-gate__ok" role="status">Code accepted for {email}.</p>
              <form className="cp-gate__form" onSubmit={submitPassword}>
                <input type="password" autoComplete="new-password" placeholder="Choose a password (12 or more characters)"
                  aria-label="Choose a password" minLength={12} value={password}
                  onChange={(event) => setPassword(event.target.value)} required />
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
                <input type="text" autoComplete="one-time-code" spellCheck={false} className="cp-code"
                  placeholder="Access code" aria-label="Access code" value={code}
                  onChange={(event) => setCode(event.target.value)}
                  onBlur={() => setCode((current) => formatPressCode(current))} required />
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
        <p className="cp-login__back"><a href={MARKETING_URL}>&larr; Back to cedarpress.ai</a></p>
      </main>
    </div>
  );
}

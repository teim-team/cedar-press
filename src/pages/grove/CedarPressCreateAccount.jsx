import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router";
import { checkAccountSetup, completeAccountSetup } from "../../api.js";
import { useAuth } from "../../context/useAuth.js";
import { safeNext } from "../../features/grove/pressSessionNavigation.js";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle.js";
import { AccountPage } from "./AccountPage.jsx";

export default function CedarPressCreateAccount() {
  useDocumentTitle("Create account");
  const location = useLocation();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { refreshSession } = useAuth();
  const [token] = useState(() => new URLSearchParams(location.hash.slice(1)).get("token") || "");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let stopped = false;
    // Keep mailbox credentials out of browser history and referrer headers.
    if (location.hash) navigate({ pathname: location.pathname, search: location.search }, { replace: true });
    checkAccountSetup(token).then((result) => { if (!stopped) setEmail(result.email); })
      .catch((failure) => { if (!stopped) setError(failure.message); });
    return () => { stopped = true; };
  }, [token, navigate, location.hash, location.pathname, location.search]);

  const submit = async (event) => {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      await completeAccountSetup({ token, name, password });
      await refreshSession();
      navigate(safeNext(params.get("next")), { replace: true });
    } catch (failure) { setError(failure.message); setPending(false); }
  };

  return <AccountPage><section className="cp-login__card" aria-label="Create account">
    <h1 className="cp-login__h">Create your account.</h1>
    <p className="cp-login__lede">Connect your membership and start exploring.</p>
    {email ? <form className="cp-gate__form" onSubmit={submit}>
      <div className="cp-login__field"><label htmlFor="account-name">Name</label><input id="account-name" autoComplete="name" placeholder="Your full name" required maxLength={120} value={name} onChange={(event) => setName(event.target.value)} /></div>
      <div className="cp-login__field"><label htmlFor="account-email">Email address</label><input id="account-email" type="email" autoComplete="email" value={email} readOnly /></div>
      <div className="cp-login__field"><label htmlFor="account-password">Create password</label><input id="account-password" type="password" autoComplete="new-password" placeholder="Choose a secure password" minLength={10} required value={password} onChange={(event) => setPassword(event.target.value)} /></div>
      <button className="cp-btn cp-btn--primary cp-btn--wide" type="submit" disabled={pending}>{pending ? "Creating account…" : "Create account"}</button>
    </form> : !error ? <p role="status">Checking your account link…</p> : null}
    {error ? <p role="alert" className="cp-gate__error">{error}</p> : null}
    <p className="cp-gate__aside">Already have an account? <Link to="/login">Sign in</Link>.</p>
  </section></AccountPage>;
}

// The front door. Standalone Cedar Press opens on the sign-in, because the
// page is a subscriber page: the reader tier arrives with a Tribal Business
// News subscription, and Cedar Grove and Tree include everything the page
// shows. The form is the app's gate dressed as a full page; the preview
// credentials are printed right on it, because a mockup people cannot get
// into demonstrates nothing. Real auth replaces src/auth.js, not this form.
import { useState } from "react";

import { DEMO_ACCOUNT, signIn } from "../auth.js";
import { LUMECON_URL, TBN_URL } from "../data/pressArticles.js";

export default function SignIn({ onSignedIn }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);

  const submit = async (event) => {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      onSignedIn(await signIn({ email, password }));
    } catch (err) {
      setError(err?.message || "That sign-in did not work. Check the address and password.");
      setPending(false);
    }
  };

  return (
    <main className="cp-gatepage">
      <header className="cp-mast cp-mast--gate">
        <span className="cp-mast__word">CEDAR PRESS</span>
        <span className="cp-mast__of">
          A <a href={TBN_URL} target="_blank" rel="noreferrer">Tribal Business News</a> ×{" "}
          <a href={LUMECON_URL} target="_blank" rel="noreferrer">Lumecon</a> partnership
        </span>
      </header>

      <section className="cp-gate" aria-label="Sign in">
        <span className="cp-sec__band">Subscribers only</span>
        <h1>Cedar Press comes with a Tribal Business News subscription.</h1>
        <p className="cp-gate__text">
          Original economic datasets, rigorous journalism and a public citation register for
          Indian Country. Everything here is available through{" "}
          <a href={TBN_URL} target="_blank" rel="noreferrer">Tribal Business News</a> and
          included with Cedar Grove. Sign in with the account your subscription created.
        </p>
        <form className="cp-gate__form" onSubmit={submit}>
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
            {pending ? "Signing in" : "Sign in"}
          </button>
        </form>

        <div className="cp-gate__demo">
          <span className="cp-gate__demo-cap">Preview access</span>
          <p>
            This is a working mockup: accounts and the real datasets arrive with the pilot.
            To look around, sign in with{" "}
            <code>{DEMO_ACCOUNT.email}</code> / <code>{DEMO_ACCOUNT.password}</code>.
          </p>
        </div>

        <div className="cp-gate__paths">
          <p className="cp-gate__path">
            Reading without a subscription?{" "}
            <a href={TBN_URL} target="_blank" rel="noreferrer">Subscribe at Tribal Business News</a>{" "}
            and Cedar Press comes with it.
          </p>
          <p className="cp-gate__path">
            Need the full collection with bulk export, benchmarks and Cedar?{" "}
            <a href={LUMECON_URL} target="_blank" rel="noreferrer">Get Cedar Grove</a>, which
            includes this page.
          </p>
        </div>
      </section>

      <footer className="cp-foot cp-foot--gate">
        <span>
          Cedar Press ·{" "}
          <a href="mailto:contact@lumecon.ai?subject=Cedar%20Press%20feedback">send feedback</a>
        </span>
        <span>
          <a href={TBN_URL} target="_blank" rel="noreferrer">tribalbusinessnews.com</a>
          {" · "}
          <a href={LUMECON_URL} target="_blank" rel="noreferrer">lumecon.ai</a>
        </span>
      </footer>
    </main>
  );
}

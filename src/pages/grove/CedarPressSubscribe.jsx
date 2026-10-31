import { AccountPage } from "./AccountPage.jsx";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { fetchBillingPlans, fetchCheckout, resendCheckoutEmail, startCheckout } from "../../api.js";
import { useAuth } from "../../context/useAuth.js";
import { collectionsOnShelf } from "../../features/grove/pressCatalog.js";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle.js";

const label = (tier) => tier === "press_pro" ? "Cedar Press+" : "Cedar Press";
const money = (cents) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(cents / 100);

const standard = collectionsOnShelf("standard");
const pro = collectionsOnShelf("pro");
const collectionNames = Object.fromEntries([...standard, ...pro].map((entry) => [entry.id, entry.short]));
const featureGroups = {
  press: [
    { title: "Funding & philanthropy", ids: ["funding", "foundation-corporate-giving"] },
    { title: "Policy & public action", ids: ["federal-register", "legislation", "lobbying", "nagpra"] },
    { title: "Deals & transactions", ids: ["deals"] },
  ],
  press_pro: [
    { title: "Federal contracting", ids: ["contractors", "subcontracting"] },
    { title: "Native enterprises", ids: ["owned", "need"] },
    { title: "Organizations, resources & land", ids: ["nonprofits", "natural-resources", "plot"] },
  ],
};

export default function CedarPressSubscribe() {
  useDocumentTitle("Subscribe");
  const { user } = useAuth();
  const [params] = useSearchParams();
  const [plans, setPlans] = useState(null);
  const [selected, setSelected] = useState(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  const [purchase, setPurchase] = useState(null);
  const [resent, setResent] = useState(false);
  const returning = params.get("billing") === "processing";
  const checkoutId = params.get("checkout");

  useEffect(() => {
    const controller = new AbortController();
    fetchBillingPlans({ signal: controller.signal }).then(setPlans).catch((failure) => {
      if (!controller.signal.aborted) setError(failure);
    });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!returning) return undefined;
    let stopped = false;
    let timer;
    let count = 0;
    const check = async () => {
      try {
        const result = await fetchCheckout(checkoutId);
        if (stopped) return;
        setPurchase(result);
        if (result.emailSent || ++count >= 20) return;
        timer = window.setTimeout(check, 3000);
      } catch (failure) { if (!stopped) setError(failure); }
    };
    check();
    return () => { stopped = true; window.clearTimeout(timer); };
  }, [returning, checkoutId]);

  const choose = async (tier) => {
    setPending(true);
    setSelected(tier);
    setError(null);
    try {
      const result = await startCheckout({ tier });
      window.location.assign(result.url);
    } catch (failure) { setError(failure); setPending(false); }
  };

  const resendEmail = async () => {
    setPending(true);
    setError(null);
    try { setPurchase(await resendCheckoutEmail(checkoutId)); setResent(true); }
    catch (failure) { setError(failure); }
    finally { setPending(false); }
  };
  const confirmed = purchase?.status === "complete";
  const existingAccount = purchase?.accountSetup === false;

  return <AccountPage wide={!returning}>
    {returning ? <section className="cp-login__card cp-confirm" aria-label="Purchase confirmation">
      <div className={`cp-confirm__icon ${!confirmed ? "cp-confirm__icon--pending" : ""}`} aria-hidden="true">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none"><path d={confirmed ? "m5 12 4 4L19 6" : "M12 6v6l4 2"} stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />{!confirmed ? <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" /> : null}</svg>
      </div>
      <p className="cp-confirm__eyebrow">{confirmed ? "Payment confirmed" : "One moment"}</p>
      <h1 className="cp-login__h">{confirmed ? "You’re subscribed." : "Confirming your payment…"}</h1>
      <p className="cp-confirm__intro" role="status">{confirmed
        ? existingAccount ? "Your membership is ready to explore." : purchase.emailSent ? "We’ve sent your account setup link to" : "Your account setup email is on its way."
        : "We’re confirming your payment with Stripe. Your next steps will appear here."}</p>
      {confirmed && purchase.email ? <div className="cp-confirm__email"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2" stroke="currentColor" strokeWidth="1.5" /><path d="m4 7 8 6 8-6" stroke="currentColor" strokeWidth="1.5" /></svg><strong>{purchase.email}</strong></div> : null}
      {confirmed ? <>
        <div className="cp-confirm__next"><span className="cp-confirm__step" aria-hidden="true">{existingAccount ? "✓" : "1"}</span><div><h2>{existingAccount ? "Pick up your research" : "Create your account"}</h2><p>{existingAccount ? "Sign in with your existing email and password to access your membership." : "Open the email to confirm your address and choose a password. Then you’re ready to start your research."}</p></div></div>
        {existingAccount ? <Link className="cp-btn cp-btn--primary cp-btn--wide" to="/login">Sign in to Cedar Press <span aria-hidden="true">→</span></Link> : null}
        <div className="cp-confirm__help"><p>Can’t find the email? Check your spam folder.</p><button className="cp-btn cp-btn--quiet" type="button" disabled={pending} onClick={resendEmail}>{pending ? "Sending…" : "Resend email"}</button></div>
        {resent ? <p className="cp-confirm__resent" role="status">Email sent. Check your inbox for your account setup link.</p> : null}
        {!existingAccount ? <p className="cp-confirm__signin">Already set your password? <Link to="/login">Sign in</Link></p> : null}
      </> : null}
      {error ? <p role="alert" className="cp-gate__error">{error.message}</p> : null}
    </section> : <section className="cp-memberships" aria-labelledby="membership-title">
      <div className="cp-memberships__intro">
        <p className="cp-kicker">{plans?.cohort === "early_access" ? "Early access membership" : "Annual membership"}</p>
        <h1 id="membership-title">Choose your Cedar Press membership.</h1>
        <p>Original data. Connected research. A clearer view of Indian Country.</p>
      </div>
      {plans ? <>
        <div className="cp-memberships__cards">
          {Object.entries(plans.annualPrices).map(([id, amount]) => <article key={id} className={`cp-membership ${id === "press_pro" ? "cp-membership--plus" : ""}`} aria-label={label(id)}>
            <div className="cp-membership__heading">
              <div><h2>{label(id)}</h2><p className="cp-membership__eyebrow">{id === "press_pro" ? "Complete research access" : "Core research"}</p></div>
              <div className="cp-membership__price"><strong>{money(amount)}</strong><span>per year</span></div>
            </div>
            <p className="cp-membership__description">{id === "press_pro" ? "Connect the enterprises, contracts and assets behind the tribal economy." : "Follow the funding, policy and transactions shaping Indian Country."}</p>
            <button type="button" className={`cp-btn cp-btn--wide ${id === "press_pro" ? "cp-btn--primary" : "cp-btn--quiet"}`} disabled={pending || !!user} onClick={() => choose(id)}>
              {pending && selected === id ? "Opening Stripe…" : `Subscribe to ${label(id)}`}<span aria-hidden="true">↗</span>
            </button>
            <div className="cp-membership__included"><span>{id === "press_pro" ? "Everything in Cedar Press, plus" : "Included in Cedar Press"}</span><span>{id === "press_pro" ? standard.length + pro.length : standard.length} collections total</span></div>
            <ul className="cp-membership__features">{featureGroups[id].map((group) => <li key={group.title}>
              <span className="cp-membership__check" aria-hidden="true"><svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="m3 8 3 3 7-7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg></span>
              <div><strong>{group.title}</strong><span>{group.ids.map((entryId) => collectionNames[entryId]).join(" · ")}</span></div>
            </li>)}
              <li>
                <span className="cp-membership__check" aria-hidden="true"><svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="m3 8 3 3 7-7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg></span>
                <div><strong>Full historical coverage &amp; original source data</strong><span>Explore every available year and trace records to their sources.</span></div>
              </li>
            </ul>
          </article>)}
        </div>
        <p className="cp-memberships__terms">Paid annually. Renews automatically. Your rate stays the same while your subscription is active.{plans.cohort === "early_access" ? " Early-access offer ends December 31, 2026." : ""} By subscribing you agree to the <Link to="/terms">Terms of Service</Link> and acknowledge the <Link to="/privacy">Privacy Policy</Link>.</p>
      </> : !error ? <p role="status">Loading annual plans…</p> : null}
      {error ? <p role="alert" className="cp-memberships__error">{error.message}</p> : null}
      <p className="cp-memberships__footer">{user ? <Link to="/settings">Manage your membership</Link> : <>Already a subscriber? <Link to="/login">Sign in</Link></>}</p>
    </section>}
  </AccountPage>;
}

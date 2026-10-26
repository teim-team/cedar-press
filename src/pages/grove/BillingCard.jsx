import { useCallback, useEffect, useState } from "react";
import { changeBillingPlan, fetchBilling, openBillingPortal, startBillingCheckout } from "../../api.js";
import { useAuth } from "../../context/useAuth.js";

const money = (value, currency = "usd") => new Intl.NumberFormat("en-US", {
  style: "currency", currency: currency.toUpperCase(),
}).format(value / 100);
const name = (tier) => tier === "press_pro" ? "Cedar Press+" : "Cedar Press";

export function BillingCard() {
  const { user, refreshSession } = useAuth();
  const [billing, setBilling] = useState(null);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    try {
      setBilling(await fetchBilling());
      setError("");
    } catch (failure) { setError(failure.message); }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetchBilling({ signal: controller.signal }).then(setBilling).catch((failure) => {
      if (failure.name !== "AbortError") setError(failure.message);
    });
    const refresh = () => { load(); refreshSession(); };
    window.addEventListener("focus", refresh);
    // Returning from Checkout does not grant access. Wait for the server's
    // verified webhook, while allowing the reader to refresh again afterward.
    let polls = 0;
    const processing = new URLSearchParams(window.location.search).get("billing") === "processing";
    const timer = processing ? window.setInterval(() => {
      refresh();
      if (++polls >= 10) window.clearInterval(timer);
    }, 3000) : null;
    return () => {
      controller.abort();
      window.removeEventListener("focus", refresh);
      if (timer) window.clearInterval(timer);
    };
  }, [user?.email, load, refreshSession]);

  const begin = async (tier) => {
    setBusy(true);
    setError("");
    try {
      const result = tier === "change" ? await changeBillingPlan()
        : tier ? await startBillingCheckout({ tier, discountCode: code }) : await openBillingPortal();
      window.location.assign(result.url);
    } catch (failure) {
      setError(failure.message);
      setBusy(false);
    }
  };
  const current = billing?.subscriptions.find((subscription) => !["canceled", "incomplete_expired"].includes(subscription.status));
  return (
    <section className="cp-set__card cp-fade" aria-label="Billing">
      <span className="cp-set__cap">Billing</span>
      {error ? <p role="alert" className="cp-gate__error">{error}</p> : null}
      {!billing && !error ? <p role="status">Loading billing…</p> : null}
      {billing && !billing.available ? <p>Online billing is temporarily unavailable.</p> : null}
      {current ? (
        <p>{name(current.tier)}: {current.status.replaceAll("_", " ")}.{current.cancel_at_period_end && current.period_end
          ? ` Access is scheduled to end ${new Date(current.period_end).toLocaleDateString()}.` : ""}</p>
      ) : null}
      {billing?.available && !current ? (
        <>
          <p>Choose annual access, paid upfront and renewed automatically.</p>
          {billing.cohort === "early_access" ? <>
            <label htmlFor="billing-discount">Discount code (optional)</label>
            <input id="billing-discount" value={code} maxLength={64} onChange={(event) => setCode(event.target.value)} />
          </> : null}
          <div className="cp-set__acts">
            {Object.entries(billing.annualPrices).map(([tier, amount]) => (
              <button key={tier} className="gv-btn gv-btn--primary" disabled={busy} onClick={() => begin(tier)}>
                {name(tier)}: {money(amount)}/year
              </button>
            ))}
          </div>
          <p className="cp-set__fine">{billing.cohort === "early_access" ? "The Summit code takes $100 off the first year. " : ""}Your underlying annual rate stays the same while your subscription remains active.</p>
        </>
      ) : null}
      {billing?.available && current?.status === "active" && !current.cancel_at_period_end ? (
        <button className="gv-btn gv-btn--primary" disabled={busy} onClick={() => begin("change")}>
          {current.tier === "press" ? "Upgrade to Cedar Press+" : "Switch to Cedar Press at renewal"}
        </button>
      ) : null}
      {billing?.available && billing.hasCustomer ? (
        <button className="gv-btn gv-btn--quiet" disabled={busy} onClick={() => begin()}>Manage billing and plan</button>
      ) : null}
      <button className="gv-btn gv-btn--quiet" disabled={busy} onClick={() => { load(); refreshSession(); }}>Refresh billing</button>
      {billing?.invoices.length ? (
        <>
          <h3>Invoices</h3>
          <ul className="cp-set__links cp-set__links--flat">
            {billing.invoices.map((invoice) => <li key={invoice.id}>
              <span>{new Date(invoice.created_at).toLocaleDateString()}: {money(invoice.amount_due, invoice.currency)} ({invoice.status})</span>
              {invoice.hosted_url ? <a href={invoice.hosted_url} target="_blank" rel="noreferrer">View invoice</a> : null}
            </li>)}
          </ul>
        </>
      ) : null}
    </section>
  );
}

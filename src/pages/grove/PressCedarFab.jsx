// Ask Cedar, from the reader.
//
// The launcher opens a panel that asks Cedar about the collections this
// subscription can open, and the answer arrives beside the data it came
// from. Where the service cannot answer, the panel routes the question to
// the research desk rather than inventing a reply: an assistant that
// produces a plausible sentence it cannot support is worse than one that
// hands the question to a person.
import { useEffect, useRef, useState } from "react";

import { askCedar } from "../../api.js";
import { appUrl } from "../../features/grove/appLink.js";
import { isConnected } from "../../config.js";
import { EVENT, track, trackError } from "../../features/grove/telemetry.js";

export function PressCedarFab({ signedOut = false, examples = [] }) {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  const [gateNotice, setGateNotice] = useState(false);
  const inputRef = useRef(null);
  const connected = isConnected();

  useEffect(() => {
    if (open && connected) inputRef.current?.focus();
  }, [open, connected]);

  const ask = async (event) => {
    event.preventDefault();
    const asked = question.trim();
    if (!asked) return;
    // On the gate, Cedar is a doorbell, not a side door: a visitor without
    // a session gets told what would answer their question and how to get
    // in, rather than a reply that leaks the collections past the paywall.
    if (signedOut) {
      setAnswer(null);
      setError(null);
      setGateNotice(true);
      track(EVENT.cedarAsked, { length: asked.length, gated: true });
      return;
    }
    setPending(true);
    setError(null);
    setAnswer(null);
    setGateNotice(false);
    try {
      const result = await askCedar({ question: asked });
      setAnswer(result?.answer ?? result?.text ?? "");
      track(EVENT.cedarAsked, { length: asked.length });
    } catch (err) {
      trackError(err, { at: "cedarAsk" });
      setError(
        err?.code === "NETWORK"
          ? "Cedar could not be reached. Try again in a moment."
          : err?.message || "Cedar could not answer that.",
      );
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="cedar-widget cedar-widget--launcher-only">
      {open ? (
        <div className="cedar-widget__panel" role="dialog" aria-label="Ask Cedar">
          {connected ? (
            <>
              <form className="cedar-widget__ask" onSubmit={ask}>
                <label className="cedar-widget__label" htmlFor="cedar-question">
                  {signedOut ? "Ask Cedar about Cedar Press" : "Ask about the collections"}
                </label>
                <textarea
                  id="cedar-question"
                  ref={inputRef}
                  rows={3}
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="Which collections cover federal contracting?"
                />
                {examples.length ? (
                  <div className="cedar-widget__examples">
                    {examples.map((example) => (
                      <button
                        key={example}
                        type="button"
                        className="cedar-widget__example"
                        onClick={() => {
                          setQuestion(example);
                          inputRef.current?.focus();
                        }}
                      >
                        {example}
                      </button>
                    ))}
                  </div>
                ) : null}
                <button type="submit" className="gv-btn gv-btn--primary" disabled={pending}>
                  {pending ? "Asking Cedar" : "Ask Cedar"}
                </button>
              </form>
              {gateNotice ? (
                <p className="cedar-widget__note" role="status">
                  Cedar answers questions like this from the Cedar Press collections once
                  you&rsquo;re signed in. Log in above, or get Cedar Press through a{" "}
                  <a href="https://tribalbusinessnews.com/subscribe" target="_blank" rel="noreferrer">
                    Tribal Business News membership
                  </a>.
                </p>
              ) : null}
              {error ? <p className="cp-gate__error" role="alert">{error}</p> : null}
              {answer ? <p className="cedar-widget__answer">{answer}</p> : null}
            </>
          ) : (
            <p className="cedar-widget__note">
              Cedar is answering inside the platform while the press surface is being wired
              in. Send the question to{" "}
              <a href="mailto:contact@lumecon.ai?subject=Cedar%20Press%20question">
                the research desk
              </a>{" "}
              and a person answers it, or{" "}
              <a href={appUrl("/app")} target="_blank" rel="noreferrer">open the platform</a>.
            </p>
          )}
        </div>
      ) : null}
      <button
        type="button"
        className="cedar-widget__launcher"
        aria-expanded={open}
        aria-label="Ask Cedar"
        onClick={() => setOpen((current) => !current)}
      >
        {/* The platform's launcher, to the mark: status dot, then the name
            with the surface it is being asked about under it. Same markup as
            teim-app's CedarWidget so the control a subscriber meets here is
            the control they meet inside Cedar Grove. */}
        <span className="cedar-widget__status-dot" aria-hidden="true" />
        <span className="cedar-widget__launcher-copy">
          <span className="cedar-widget__launcher-label">Ask Cedar</span>
          <span className="cedar-widget__launcher-context">Cedar Press</span>
        </span>
      </button>
    </div>
  );
}

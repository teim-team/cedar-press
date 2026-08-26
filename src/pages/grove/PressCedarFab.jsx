// Ask Cedar, from the reader.
//
// Connected, the launcher opens a panel that asks the platform's Cedar
// endpoint about the collections this subscription can open, and the answer
// arrives here beside the data it came from. Standalone, there is no Cedar
// to ask, so the panel says so and offers the desk instead of pretending to
// think. The launcher itself is the product's own: status dot, label,
// surface context.
import { useEffect, useRef, useState } from "react";

import { askCedar } from "../../api.js";
import { appUrl } from "../../features/grove/appLink.js";
import { isConnected } from "../../config.js";
import { EVENT, track, trackError } from "../../features/grove/telemetry.js";

export function PressCedarFab() {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);
  const connected = isConnected();

  useEffect(() => {
    if (open && connected) inputRef.current?.focus();
  }, [open, connected]);

  const ask = async (event) => {
    event.preventDefault();
    const asked = question.trim();
    if (!asked) return;
    setPending(true);
    setError(null);
    setAnswer(null);
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
                  Ask about the collections
                </label>
                <textarea
                  id="cedar-question"
                  ref={inputRef}
                  rows={3}
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="Which collections cover federal contracting?"
                />
                <button type="submit" className="gv-btn gv-btn--primary" disabled={pending}>
                  {pending ? "Asking Cedar" : "Ask Cedar"}
                </button>
              </form>
              {error ? <p className="cp-gate__error" role="alert">{error}</p> : null}
              {answer ? <p className="cedar-widget__answer">{answer}</p> : null}
            </>
          ) : (
            <p className="cedar-widget__note">
              Cedar answers questions about the collections inside the platform. This deployment is
              not connected to it, so the question goes to the people who build the data:{" "}
              <a href="mailto:contact@lumecon.ai?subject=Cedar%20Press%20question">
                contact@lumecon.ai
              </a>
              . <a href={appUrl("/app")} target="_blank" rel="noreferrer">Open the platform</a> to
              ask Cedar directly.
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
        <span className="cedar-widget__status-dot" aria-hidden="true" />
        <span className="cedar-widget__launcher-copy">
          <span className="cedar-widget__launcher-label">Ask Cedar</span>
          <span className="cedar-widget__launcher-context">
            {connected ? "Cedar Press" : "Opens a note"}
          </span>
        </span>
      </button>
    </div>
  );
}

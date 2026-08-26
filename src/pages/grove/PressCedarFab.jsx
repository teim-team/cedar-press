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
        {/* The mark inside the circle: a spoken line and its answer, which is
            what Cedar is, rather than a sparkle meaning "AI". */}
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
             strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M20.2 11.3a7.7 7.7 0 0 1-10.6 7.15L4.4 19.6l1.16-5.16A7.7 7.7 0 1 1 20.2 11.3z" />
          <path d="M8.9 10.4h6.2M8.9 13.6h3.8" />
        </svg>
        {/* aria-hidden because the button already carries the same words as
            its label; read out twice it is a stutter, not a clarification. */}
        <span className="cedar-widget__launcher-copy" aria-hidden="true">
          <span className="cedar-widget__launcher-label">Ask Cedar</span>
          <span className="cedar-widget__launcher-context">Cedar Press</span>
        </span>
      </button>
    </div>
  );
}

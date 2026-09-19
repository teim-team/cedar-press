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
import { appUrl, contactHref } from "../../features/grove/appLink.js";
import { TBN_PLANS_URL } from "../../features/grove/pressArticles.js";
import { PRESS_METHODS_PATH } from "../../features/grove/pressRoutes.js";
import { isConnected } from "../../config.js";
import { EVENT, track, trackError } from "../../features/grove/telemetry.js";
import { CedarIcon } from "./pressGateIcons";

// Questions every collection profile can answer; shown whenever Cedar is
// scoped to a collection.
const SCOPED_EXAMPLES = [
  "What does this collection cover?",
  "How was this collection constructed?",
  "What are its headline figures?",
];

/**
 * WHAT IS UNDER THE ANSWER, SAID IN THE PANEL.
 *
 * A box in the corner of a page that takes a question and returns prose is,
 * to a reader, indistinguishable from a chat model wired to a search index.
 * Cedar is not that, and nothing in this panel said so: the panel asked for a
 * question and printed a sentence, which is exactly the shape of the thing it
 * is not.
 *
 * Every sentence below is a fact about this service, checked against the code
 * that produces the answers, not positioning:
 *
 *  - `server/cedar_press/collection_profiles.answer_from_profile` answers
 *    from the collection's own profile fields and "never composes beyond
 *    them". No prompt, no model, no memory. Its own module docstring opens
 *    with it: "Cedar does not 'know' the collections because copy was stuffed
 *    into a prompt."
 *  - Every answer carries a `basis` naming the release it was read off
 *    (`{collection} {version}`), which is why the answer above prints one.
 *  - A question the profiles cannot answer returns `None` and the route
 *    refuses, naming the research desk — `app.ask_cedar`. It does not
 *    improvise.
 *  - The identifiers are the register's, documented on Methods: a Cedar
 *    entity id (CE-) names a Native entity, a Cedar business id (CB-) names a
 *    distinct business, and they are maintained through renames, mergers and
 *    reorganizations.
 *
 * It renders in both modes. Standalone, the panel cannot take a question at
 * all, and a visitor reading that Cedar is "being wired in" should still
 * learn what it is being wired to.
 */
function CedarBasis() {
  return (
    <div className="cedar-widget__basisnote">
      <span className="cedar-widget__basiscap">How Cedar answers</span>
      <p>
        Cedar reads each collection&rsquo;s own profile &mdash; its sources, its method, its
        release and its published figures &mdash; and names the release it answered from.
        Nothing is generated from a model&rsquo;s memory, and a question the collections
        cannot answer goes to the research desk rather than to a guess.
      </p>
      <p>
        The records behind an answer are held by identifier, not by name: a Cedar entity
        id (<span className="cedar-widget__uid">CE-</span>) for a Native government,
        enterprise or nonprofit, a Cedar business id
        (<span className="cedar-widget__uid">CB-</span>) for a distinct business, each
        maintained through renames, acquisitions and reorganizations.
      </p>
      <a className="cedar-widget__basislink" href={PRESS_METHODS_PATH}>
        How Cedar builds its collections <span aria-hidden="true">&#8594;</span>
      </a>
    </div>
  );
}

// `gated` names why Cedar will not query the collections for this reader:
// "signedout" (no session) or "unentitled" (a membership without Cedar
// Press). Falsy means fully entitled.
export function PressCedarFab({ gated = null, examples = [] }) {
  const signedOut = Boolean(gated);
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  const [gateNotice, setGateNotice] = useState(false);
  // Which collection Cedar is currently asked about. Set by the shelf's
  // "Ask Cedar about this collection" (a window event, so the shelf does
  // not need a prop path to a control that floats outside it), cleared by
  // the reader.
  const [scope, setScope] = useState(null);
  const inputRef = useRef(null);
  const abortRef = useRef(null);
  const connected = isConnected();

  useEffect(() => {
    if (open && connected) inputRef.current?.focus();
  }, [open, connected]);

  // Escape closes the panel. The launcher toggles it too, but on phones the
  // browser's own toolbar can sit over the launcher while the panel is open,
  // which left no visible way back out — the panel carries its own close.
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  useEffect(() => {
    const onScope = (event) => {
      const next = event?.detail;
      if (!next?.id || !next?.name) return;
      abortRef.current?.abort();
      setScope({ id: next.id, name: next.name });
      // A caller can hand the question over with the scope (the What's New
      // feed asks about a specific release), so the reader arrives with the
      // ask already phrased and only has to send it.
      if (next.q) setQuestion(next.q);
      setAnswer(null);
      setError(null);
      setPending(false);
      setOpen(true);
    };
    // A plain open, for surfaces that want to hand the reader to Cedar
    // without scoping it (the gate's "Ask Cedar what Cedar Press can
    // answer").
    const onOpen = () => setOpen(true);
    window.addEventListener("cedar:ask-collection", onScope);
    window.addEventListener("cedar:open", onOpen);
    return () => {
      window.removeEventListener("cedar:ask-collection", onScope);
      window.removeEventListener("cedar:open", onOpen);
    };
  }, []);

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
    // Unscoped, Cedar has nothing to answer from yet; say so here rather
    // than spending a request on a refusal the client can word better.
    if (!scope) {
      setAnswer(null);
      setError(
        "Cedar answers per collection for now. Open Collections and choose \u201cAsk Cedar about this collection\u201d, and the question lands already scoped.",
      );
      return;
    }
    // A reader can re-scope mid-flight; the late answer must not land under
    // the new collection's name.
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setPending(true);
    setError(null);
    setAnswer(null);
    setGateNotice(false);
    try {
      const result = await askCedar({ question: asked, collectionId: scope.id, signal: controller.signal });
      if (controller.signal.aborted) return;
      setAnswer({ text: result?.answer ?? result?.text ?? "", basis: result?.basis ?? null });
      track(EVENT.cedarAsked, { length: asked.length, collectionId: scope.id });
    } catch (err) {
      if (controller.signal.aborted) return;
      trackError(err, { at: "cedarAsk" });
      setError(
        err?.code === "NETWORK"
          ? "Cedar could not be reached. Try again in a moment."
          : err?.message || "Cedar could not answer that.",
      );
    } finally {
      if (!controller.signal.aborted) setPending(false);
    }
  };

  return (
    <div className={`cedar-widget cedar-widget--launcher-only${open ? " cedar-widget--open" : ""}`}>
      {open ? (
        <div className="cedar-widget__panel" role="dialog" aria-label="Ask Cedar">
          {/* A dialog header, not a floating glyph: the caption names the
              panel and the close sits where every dialog keeps it. Sticky,
              so a scrolled answer never carries the way out with it. */}
          <div className="cedar-widget__panelhead">
            <span className="cedar-widget__panelcap">Ask Cedar</span>
            <button
              type="button"
              className="cedar-widget__close"
              aria-label="Close Ask Cedar"
              onClick={() => setOpen(false)}
            >
              <span aria-hidden="true">&#215;</span>
            </button>
          </div>
          {/* The body scrolls; the head above it and the dialog's own edges do
              not. On a phone the panel is the screen, so a long answer must
              not carry the close button off the top of it. */}
          <div className="cedar-widget__scroll">
          {connected ? (
            <>
              <form className="cedar-widget__ask" onSubmit={ask}>
                <label className="cedar-widget__label" htmlFor="cedar-question">
                  {scope
                    ? `Ask about ${scope.name}`
                    : signedOut
                      ? "Ask Cedar about Cedar Press"
                      : "Ask about the collections"}
                </label>
                {scope ? (
                  /* The label above already carries the collection's name, so
                     this line says only that the scope is on and how to leave
                     it. Both carrying the name put it twice inside one panel,
                     which on a phone is two wrapped lines of the same
                     twenty-eight characters. */
                  <p className="cedar-widget__scope">
                    Scoped{" · "}
                    <button
                      type="button"
                      className="cedar-widget__scopeclear"
                      onClick={() => {
                        abortRef.current?.abort();
                        setScope(null);
                        setPending(false);
                      }}
                    >
                      All collections
                    </button>
                  </p>
                ) : null}
                <textarea
                  id="cedar-question"
                  ref={inputRef}
                  rows={3}
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="Which collections cover federal contracting?"
                />
                {(scope ? SCOPED_EXAMPLES : examples).length ? (
                  <div className="cedar-widget__examples">
                    {(scope ? SCOPED_EXAMPLES : examples).map((example) => {
                      const label = typeof example === "string" ? example : example.q;
                      return (
                        <button
                          key={label}
                          type="button"
                          className="cedar-widget__example"
                          onClick={() => {
                            // A suggestion that names a collection scopes to
                            // it in the same tap, so every suggestion shown
                            // is answerable as shown.
                            if (typeof example !== "string" && example.scope) {
                              abortRef.current?.abort();
                              setScope(example.scope);
                              setAnswer(null);
                              setError(null);
                              setPending(false);
                            }
                            setQuestion(label);
                            inputRef.current?.focus();
                          }}
                        >
                          {typeof example === "string" ? label : `${label} (${example.scope.name})`}
                        </button>
                      );
                    })}
                  </div>
                ) : null}
                <button type="submit" className="gv-btn gv-btn--primary" disabled={pending}>
                  {pending ? "Asking Cedar" : "Ask Cedar"}
                </button>
              </form>
              {gateNotice ? (
                <p className="cedar-widget__note" role="status">
                  Cedar answers questions like this from the Cedar Press collections once
                  your membership includes Cedar Press.{" "}
                  {gated === "unentitled"
                    ? "Upgrade through your"
                    : "Log in above, or get Cedar Press through a"}{" "}
                  <a href={TBN_PLANS_URL} target="_blank" rel="noreferrer">
                    Tribal Business News membership
                  </a>.
                </p>
              ) : null}
              {error ? <p className="cp-gate__error" role="alert">{error}</p> : null}
              {answer ? (
                <div className="cedar-widget__answer">
                  <p>{answer.text}</p>
                  {answer.basis ? <p className="cedar-widget__basis">{answer.basis}</p> : null}
                </div>
              ) : null}
            </>
          ) : (
            <p className="cedar-widget__note">
              Cedar is answering inside the platform while the press surface is being wired
              in. Send the question to{" "}
              <a href={contactHref("Cedar Press question")}>
                the research desk
              </a>{" "}
              and a person answers it, or{" "}
              <a href={appUrl("/app")} target="_blank" rel="noreferrer">open the platform</a>.
            </p>
          )}
          <CedarBasis />
          </div>
        </div>
      ) : null}
      <button
        type="button"
        className="cedar-widget__launcher"
        aria-expanded={open}
        aria-label="Ask Cedar"
        onClick={() => setOpen((current) => !current)}
      >
        {/* THIS NO LONGER MATCHES teim-app's CedarWidget, AND THAT IS A
            DECISION SOMEBODY HAS TO MAKE.
            It used to be the platform's launcher to the mark — status dot,
            then the name with the surface under it — and the point of that
            was that the control a subscriber meets here is the control they
            meet inside Cedar Grove. Collapsing it to a circle (because the
            pill covered content on most surfaces) broke the parity, and the
            mark below is a Press gate icon, not a Cedar brand asset: checked,
            `teim-app/src/components/CedarWidget.jsx` has no icon in its
            launcher at all, only the dot and the label.
            So the two products' assistants now look different at rest. Either
            Grove adopts the same collapse or Press keeps a launcher of its
            own deliberately; that is the owner's call, not a thing to settle
            inside a stylesheet. Flagged rather than quietly left as a comment
            claiming a parity that no longer holds.
            At rest the launcher is a circle and this mark is what is in it;
            the dot and the name arrive with the pointer. A lone status dot in
            a circle says nothing, and the mark is the one thing here a reader
            has already met — it is the wordmark's own glyph. */}
        <span className="cedar-widget__launcher-mark" aria-hidden="true">{CedarIcon}</span>
        <span className="cedar-widget__status-dot" aria-hidden="true" />
        <span className="cedar-widget__launcher-copy">
          <span className="cedar-widget__launcher-label">Ask Cedar</span>
          <span className="cedar-widget__launcher-context">Cedar Press</span>
        </span>
      </button>
    </div>
  );
}

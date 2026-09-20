// Ask Cedar, from the reader — the same Cedar, in the same panel.
//
// WHAT CHANGED, AND WHY IT HAD TO
// This used to be a form. A label, a three-row textarea, a row of example
// buttons and an "Ask Cedar" submit, which returned one paragraph and then
// sat there. Nothing else in this company's software looks like that:
// lumecon.ai's FAB (`src/components/CedarFAB.astro`), the door's panel
// (`PressDoorCedar.jsx`) and teim-app's `CedarWidget.jsx` are all the same
// conversation — teal identity band with a status dot, a transcript of
// bubbles with the mark beside Cedar's, quick replies inside that transcript,
// a single-line composer with a send button, one line of expectation-setting
// under it. A reader who met Cedar on the door and then signed in met a
// second, unrelated thing wearing the name.
//
// So the markup below is the door's, class for class (`.cp-dc__*`, styled in
// `styles/grove/press.css` and scoped to `.teim-rd`, which is this app's
// shell too). Full screen on a phone comes with it, because that rule lives
// on `.cp-dc__panel`.
//
// WHAT IS DIFFERENT FROM THE DOOR, DELIBERATELY
// The door never reaches the network — it answers from `doorCedar.js`, by
// design, because it sits in front of the paywall. This one is behind it and
// answers from the service:
//
//   * `POST /cedar/ask` -> the collection's own profile, cited by release,
//     when the question is one a release already answers;
//   * otherwise the Cedar service in the `cedar` repository, over contract
//     1.0.0 — the same Cedar teim-app talks to. See
//     `server/cedar_press/cedar_service.py`.
//
// `threadId` rides with every turn after the first, so this is a
// conversation on the service's side too and not a row of isolated
// questions.
//
// THE LAUNCHER IS UNCHANGED, AND THAT IS STILL SOMEBODY'S CALL
// The circle-with-a-mark launcher stays as it was, with the note it already
// carried: it no longer matches teim-app's pill, and whether Grove adopts
// this collapse or Press keeps its own is the owner's decision, not one to
// settle in a stylesheet. The panel is the part that had drifted.
import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router";

import { askCedar } from "../../api.js";
import { appUrl, contactHref } from "../../features/grove/appLink.js";
import { TBN_PLANS_URL } from "../../features/grove/pressArticles.js";
import { PRESS_DATA_PATH, PRESS_METHODS_PATH } from "../../features/grove/pressRoutes.js";
import { isConnected } from "../../config.js";
import { EVENT, track, trackError } from "../../features/grove/telemetry.js";
import { CedarIcon } from "./pressGateIcons";

const MARK = "/brand/lumecon-logo-mark-teal.png";

// The collection-scoped prompt set, from the implementation brief §3, minus
// one.
//
// Every starter here was run against `answer_from_profile` before it was
// offered, because a starter that falls through to Cedar is a starter that
// comes back uncited — and the point of offering them is that they come back
// read off the release.
//
// THE ONE THAT IS NOT HERE. The brief also lists "Why is this record
// connected to this entity?", and that question does not fall through: it
// returns the collection's ROW COUNT. `_STATS_WORDS` in
// `collection_profiles.py` contains `"record"`, so any question carrying that
// word routes to headline figures — an identity question answered with
// "3,345,971 rows", confidently and in the release's name. That is the exact
// failure the answer-basis work exists to prevent, so the prompt is withheld
// until the router is fixed rather than shipped as a demonstration of it.
const SCOPED_EXAMPLES = [
  "What does this collection cover?",
  "How are entities resolved?",
  "What sources are included?",
  "What changed in the latest release?",
];

let nextId = 0;
const turn = (role, text, extra = {}) => ({ key: `t${(nextId += 1)}`, role, text, ...extra });

/**
 * THE ANSWER BASIS, ABOVE THE ANSWER.
 *
 * It used to sit under the bubble, which meant a reader learned what kind of
 * claim they had just read only after reading it. The brief is right that the
 * distinction has to be legible before the bottom of a long answer, and on a
 * phone a long answer's foot can be two screens down.
 *
 * Three states are declared; two can occur.
 *
 *   release    read off the collection's own release and cited to it.
 *   synthesis  Cedar composed it. The SCOPE is real — the question was asked
 *              against this collection — and nothing else is claimed.
 *   review     ambiguous identity, evidence or scope. No producer yet; see
 *              `_answer_basis` in the service for why it is declared anyway.
 *
 * WHAT THIS DELIBERATELY DOES NOT RENDER. The brief asks for a cited-record
 * count ("Cedar synthesis from 3 cited records") and an expandable evidence
 * trail of the records used. Cedar returns neither: there is no collections
 * tool and no retrieval, so a synthesis today is grounded in the model, not
 * in this collection's records. Printing a count would be inventing one, and
 * the brief's own scope rule — an answer "may not imply that it understands a
 * particular entity, record, or filtered table state unless that context is
 * actually passed to the service" — forbids it. The field is in the contract
 * and renders the moment the service fills it.
 */
const BASIS_LABEL = {
  release: "Release-grounded",
  synthesis: "Cedar synthesis",
  review: "Needs review",
};

const releaseOf = (basis) => [basis?.collectionName, basis?.version].filter(Boolean).join(" ");

/** The label, above the answer. What kind of claim is about to be read. */
function AnswerBasisLabel({ basis }) {
  if (!basis?.kind) return null;
  const { kind, citedRecords } = basis;
  const label = BASIS_LABEL[kind] ?? BASIS_LABEL.synthesis;
  const release = releaseOf(basis);
  return (
    <div className={`cp-dc__basis cp-dc__basis--${kind}`}>
      <p className="cp-dc__basisline">
        <span className="cp-dc__basislabel">{label}</span>
        {release ? <span className="cp-dc__basisrelease">{release}</span> : null}
        {/* Rendered only when the service supplies it. Absent is absent; a
            zero here would read as "checked, found none". */}
        {typeof citedRecords === "number" ? (
          <span className="cp-dc__basiscount">{citedRecords} cited records</span>
        ) : null}
      </p>
      {kind === "synthesis" ? (
        <p className="cp-dc__basisnote-inline">
          Scoped to this collection. Not read from its records.
        </p>
      ) : null}
    </div>
  );
}

/**
 * The evidence, under the answer.
 *
 * Under, not above — it was above for one build and the screenshot settled it:
 * an opened disclosure between the label and the prose pushes the answer off
 * the bottom of the panel, so expanding the evidence hides the thing the
 * evidence is for. The brief says "under each answer" and it is right.
 */
function EvidenceUsed({ basis }) {
  if (!basis?.kind) return null;
  const { updated, sources, collectionId } = basis;
  const release = releaseOf(basis);
  if (!updated && !sources) return null;
  return (
    <details className="cp-dc__evidence">
      <summary>Evidence used</summary>
      <dl>
        {release ? (
          <>
            <dt>Release</dt>
            <dd>{release}</dd>
          </>
        ) : null}
        {updated ? (
          <>
            <dt>Updated</dt>
            <dd>{updated}</dd>
          </>
        ) : null}
        {sources ? (
          <>
            <dt>Sources</dt>
            <dd>{sources}</dd>
          </>
        ) : null}
      </dl>
      {collectionId ? (
        <Link className="cp-dc__evidencelink" to={`${PRESS_DATA_PATH}?c=${collectionId}`}>
          View in table <span aria-hidden="true">&#8594;</span>
        </Link>
      ) : null}
    </details>
  );
}

/**
 * WHAT IS UNDER THE ANSWER, SAID IN THE PANEL.
 *
 * A box in the corner of a page that takes a question and returns prose is,
 * to a reader, indistinguishable from a chat model wired to a search index.
 * Cedar is not that, and nothing in this panel said so.
 *
 * Every sentence below is a fact about this service, checked against the code
 * that produces the answers, not positioning:
 *
 *  - `server/cedar_press/collection_profiles.answer_from_profile` answers
 *    from the collection's own profile fields and "never composes beyond
 *    them", and the route tries it first. Every such answer carries a
 *    `basis` naming the release it was read off — which is why an answer
 *    above prints one, and why an answer without one is marked as Cedar's
 *    own rather than the release's.
 *  - Past the profiles the question goes to Cedar itself, on the contract
 *    teim-app uses, not to a second assistant.
 *  - A question neither can answer refuses and names the research desk. It
 *    does not improvise.
 *  - The identifiers are the register's, documented on Methods: a Cedar
 *    entity id (CE-) names a Native entity, a Cedar business id (CB-) names
 *    a distinct business, maintained through renames, mergers and
 *    reorganizations.
 *
 * It renders in both modes. Standalone, the panel cannot take a question at
 * all, and a visitor reading that Cedar is "being wired in" should still
 * learn what it is being wired to.
 */
function CedarBasis() {
  return (
    /* Collapsed by default, and that is a measured decision rather than a
       preference: expanded, this note is about two thirds of the panel's
       36rem transcript, so the starter questions — the thing a reader
       actually needs first — fell below the fold on a 900px window. The
       claim still has to be on the face of the panel, so the summary line
       stays visible and the evidence is one click under it. */
    <details className="cedar-widget__basisnote">
      <summary className="cedar-widget__basiscap">How Cedar answers</summary>
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
      <Link className="cedar-widget__basislink" to={PRESS_METHODS_PATH}>
        How Cedar builds its collections <span aria-hidden="true">&#8594;</span>
      </Link>
    </details>
  );
}

// `gated` names why Cedar will not query the collections for this reader:
// "signedout" (no session) or "unentitled" (a membership without Cedar
// Press). Falsy means fully entitled.
export function PressCedarFab({ gated = null, examples = [] }) {
  const signedOut = Boolean(gated);
  const [open, setOpen] = useState(false);
  const [asked, setAsked] = useState("");
  const [thread, setThread] = useState([]);
  const [pending, setPending] = useState(false);
  // Which collection Cedar is currently asked about. Set by the shelf's
  // "Ask Cedar about this collection" (a window event, so the shelf does
  // not need a prop path to a control that floats outside it), cleared by
  // the reader.
  const [scope, setScope] = useState(null);
  // Cedar's conversation id, for as long as this panel is open. Held in a
  // ref rather than state: it is sent with the next request, never rendered,
  // and a re-render between turns would be noise.
  const threadRef = useRef(null);
  const inputRef = useRef(null);
  const abortRef = useRef(null);
  const endRef = useRef(null);
  const panelRef = useRef(null);
  const connected = isConnected();

  useEffect(() => {
    if (open && connected) {
      const frame = requestAnimationFrame(() => inputRef.current?.focus());
      return () => cancelAnimationFrame(frame);
    }
    return undefined;
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

  // A new turn scrolls into view inside the panel, never the page.
  useEffect(() => {
    if (thread.length || pending) endRef.current?.scrollIntoView({ block: "nearest" });
  }, [thread, pending]);

  useEffect(() => {
    const onScope = (event) => {
      const next = event?.detail;
      if (!next?.id || !next?.name) return;
      abortRef.current?.abort();
      setScope({ id: next.id, name: next.name });
      // A caller can hand the question over with the scope (the What's New
      // feed asks about a specific release), so the reader arrives with the
      // ask already phrased and only has to send it.
      if (next.q) setAsked(next.q);
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

  const say = useCallback((role, text, extra) => {
    setThread((prev) => [...prev, turn(role, text, extra)]);
  }, []);

  const ask = useCallback(
    async (raw) => {
      const question = String(raw ?? "").trim();
      if (!question || pending) return;
      setAsked("");
      say("you", question);

      // On the gate, Cedar is a doorbell, not a side door: a visitor without
      // a session gets told what would answer their question and how to get
      // in, rather than a reply that leaks the collections past the paywall.
      if (signedOut) {
        say("cedar", null, { gate: gated });
        track(EVENT.cedarAsked, { length: question.length, gated: true });
        return;
      }
      // Unscoped, the profiles have nothing to answer from; say so here
      // rather than spending a request on a refusal the client words better.
      // Cedar itself still answers unscoped questions — this is the one case
      // where the panel knows the answer is a routing instruction.
      if (!scope && !connected) {
        say("cedar", "Open a collection and choose “Ask Cedar about this collection”, and the question lands already scoped.");
        return;
      }

      // A reader can re-scope mid-flight; the late answer must not land under
      // the new collection's name.
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setPending(true);
      try {
        const result = await askCedar({
          question,
          collectionId: scope?.id ?? null,
          threadId: threadRef.current,
          pathname: typeof window === "undefined" ? null : window.location.pathname,
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        if (result?.threadId) threadRef.current = result.threadId;
        say("cedar", result?.answer ?? result?.text ?? "", {
          basis: result?.answerBasis ?? null,
          source: result?.source ?? null,
        });
        track(EVENT.cedarAsked, { length: question.length, collectionId: scope?.id ?? null });
      } catch (err) {
        if (controller.signal.aborted) return;
        trackError(err, { at: "cedarAsk" });
        say("cedar", null, {
          error:
            err?.code === "NETWORK"
              ? "Cedar could not be reached. Try again in a moment."
              : err?.message || "Cedar could not answer that.",
        });
      } finally {
        if (!controller.signal.aborted) setPending(false);
      }
    },
    [connected, gated, pending, say, scope, signedOut],
  );

  const submit = (event) => {
    event.preventDefault();
    ask(asked);
  };

  // The starter stack belongs to the empty panel, as it does on the door and
  // on lumecon.ai: once a question has been asked the chips are gone, rather
  // than sitting under every reply like a control panel that had not been
  // listening.
  const starters = thread.length
    ? []
    : (scope ? SCOPED_EXAMPLES : examples).slice(0, 5).map((example) =>
        typeof example === "string"
          ? { label: example, scope: null }
          : { label: example.q, scope: example.scope ?? null },
      );

  const openingLine = scope
    ? `Ask me about ${scope.name} — what it holds, how it was built, or what its release reports. I answer from the release itself and name it.`
    : "I can tell you what each collection holds, where the records come from, and how they reach the right nation. Open a collection to get an answer cited to its release.";

  return (
    <div className={`cedar-widget cedar-widget--launcher-only${open ? " cedar-widget--open" : ""}`}>
      {open ? (
        <section className="cp-dc__panel" ref={panelRef} role="dialog" aria-label="Ask Cedar">
          {/* The identity band the app, the door and lumecon.ai all use:
              status dot, uppercase title, context line, all white on the one
              teal that carries white text. The context line is where the
              scope lives, so the collection's name is stated once in the
              panel rather than twice. */}
          <header className="cp-dc__head">
            <span className="cp-dc__heading">
              <span className="cp-dc__titlerow">
                <span className="cp-dc__statusdot" aria-hidden="true" />
                <span className="cp-dc__title">Ask Cedar</span>
              </span>
              <span className="cp-dc__context">
                {scope ? `Cedar Press · ${scope.name}` : "Cedar Press · Questions about the collections"}
              </span>
            </span>
            <button
              type="button"
              className="cp-dc__close"
              aria-label="Close Ask Cedar"
              onClick={() => setOpen(false)}
            >
              <span aria-hidden="true">&times;</span>
            </button>
          </header>

          <div className="cp-dc__thread" role="log" aria-live="polite">
            <div className="cp-dc__msg cp-dc__msg--bot">
              <span className="cp-dc__avatar" aria-hidden="true">
                <img src={MARK} alt="" width="30" height="30" />
              </span>
              <div className="cp-dc__bubble">
                <p>{connected ? openingLine : "Cedar is answering inside the platform while the press surface is being wired in."}</p>
                {connected ? null : (
                  <p className="cp-dc__links">
                    <a href={contactHref("Cedar Press question")}>Send the question to the research desk</a>
                    <a href={appUrl("/app")} target="_blank" rel="noreferrer">Open the platform</a>
                  </p>
                )}
              </div>
            </div>

            {/* What is under an answer, said once, at the top of the
                transcript where the welcome is — not pinned to the foot,
                which on a phone would take the height the conversation
                needs. It scrolls away as the conversation starts. */}
            {thread.length ? null : <CedarBasis />}

            {scope ? (
              <p className="cp-dc__scope">
                Scoped to {scope.name}
                {" · "}
                <button
                  type="button"
                  className="cp-dc__scopeclear"
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

            {starters.length ? (
              <div className="cp-dc__quickreply">
                {starters.map((starter) => (
                  <button
                    type="button"
                    key={starter.label}
                    className="cp-dc__chip"
                    onClick={() => {
                      // A suggestion that names a collection scopes to it in
                      // the same tap, so every suggestion shown is
                      // answerable as shown.
                      if (starter.scope) setScope(starter.scope);
                      ask(starter.label);
                    }}
                  >
                    {starter.scope ? `${starter.label} (${starter.scope.name})` : starter.label}
                  </button>
                ))}
              </div>
            ) : null}

            {thread.map((item) =>
              item.role === "you" ? (
                <div className="cp-dc__msg cp-dc__msg--you" key={item.key}>
                  <div className="cp-dc__bubble">
                    <p>{item.text}</p>
                  </div>
                </div>
              ) : (
                <div className="cp-dc__msg cp-dc__msg--bot" key={item.key}>
                  <span className="cp-dc__avatar" aria-hidden="true">
                    <img src={MARK} alt="" width="30" height="30" />
                  </span>
                  <div className="cp-dc__bubble">
                    {/* The label above the answer; the evidence under it. */}
                    {item.basis ? <AnswerBasisLabel basis={item.basis} /> : null}
                    {item.gate ? (
                      <p>
                        Cedar answers questions like this from the Cedar Press collections once
                        your membership includes Cedar Press.{" "}
                        {item.gate === "unentitled"
                          ? "Upgrade through your"
                          : "Log in above, or get Cedar Press through a"}{" "}
                        <a href={TBN_PLANS_URL} target="_blank" rel="noreferrer">
                          Tribal Business News membership
                        </a>
                        .
                      </p>
                    ) : item.error ? (
                      <p role="alert">{item.error}</p>
                    ) : (
                      (item.text || "").split("\n\n").map((para, i) => <p key={i}>{para}</p>)
                    )}
                    {item.basis ? <EvidenceUsed basis={item.basis} /> : null}
                  </div>
                </div>
              ),
            )}

            {pending ? (
              <div className="cp-dc__msg cp-dc__msg--bot" aria-hidden="true">
                <span className="cp-dc__avatar">
                  <img src={MARK} alt="" width="30" height="30" />
                </span>
                <div className="cp-dc__bubble cp-dc__bubble--typing">
                  <span className="cp-dc__dot" />
                  <span className="cp-dc__dot" />
                  <span className="cp-dc__dot" />
                </div>
              </div>
            ) : null}
            <div ref={endRef} />
          </div>

          <form className="cp-dc__form" onSubmit={submit} autoComplete="off">
            <label className="cp-dc__inputwrap">
              <span className="cp-badge__sr">Ask Cedar a question</span>
              <input
                ref={inputRef}
                className="cp-dc__input"
                type="text"
                value={asked}
                disabled={!connected}
                placeholder={scope ? `Ask about ${scope.name}` : "Ask about a collection"}
                onChange={(event) => setAsked(event.target.value)}
              />
            </label>
            <button
              type="submit"
              className="cp-dc__send"
              disabled={!asked.trim() || pending || !connected}
              aria-label="Send"
            >
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M4 12h15M13 6l6 6-6 6" />
              </svg>
            </button>
          </form>
          {/* The one line of expectation-setting the panel owes its reader,
              in the same place and the same words the marketing site uses —
              with the sentence that is true on this side of the paywall: an
              answer here is read off a release, or it is Cedar's and says so. */}
          <p className="cp-dc__disclaimer">
            Cedar can make mistakes. Verify anything important against the methods page or the
            release it came from.
          </p>
        </section>
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
            The PANEL is now the platform's, class for class. The launcher is
            the one part still diverging, and whether Grove adopts this
            collapse or Press keeps a launcher of its own is the owner's call,
            not a thing to settle inside a stylesheet. */}
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

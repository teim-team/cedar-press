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
import { answerSource } from "../../features/grove/cedarAnswer.js";
import { LAUNCH_COLLECTION } from "../../features/grove/collection.js";
import { appUrl, contactHref } from "../../features/grove/appLink.js";
import { TBN_PLANS_URL } from "../../features/grove/pressArticles.js";
import { PRESS_DATA_PATH, PRESS_METHODS_PATH } from "../../features/grove/pressRoutes.js";
import { isConnected } from "../../config.js";
import { EVENT, track, trackError } from "../../features/grove/telemetry.js";

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

/**
 * WHAT AN UNSCOPED PANEL OFFERS.
 *
 * Every page but the overview mounted this with no `examples`, so nine of
 * the eleven places a reader can open Cedar opened on a greeting and an
 * empty box. "Ask Cedar" is the product's own invitation and answering it
 * with a blank prompt is the worst moment to ask somebody to think of a
 * question.
 *
 * Each of these carries the collection it is about, so the tap scopes the
 * panel and the question is answerable as shown — the same rule the
 * overview's own set follows. They are collections rather than topics
 * because an unscoped question has no release to be answered from, and an
 * answer with no release behind it is the thing the basis line exists to
 * mark.
 */
const OPEN_EXAMPLES = [
  { q: "What does this collection cover?", at: 0 },
  { q: "How was this collection built?", at: 1 },
  { q: "What sources are included?", at: 2 },
  { q: "What changed in the latest release?", at: 3 },
]
  .map(({ q, at }) => {
    const entry = LAUNCH_COLLECTION[at];
    return entry ? { q, scope: { id: entry.id, name: entry.name } } : null;
  })
  .filter(Boolean);

let nextId = 0;
const turn = (role, text, extra = {}) => ({ key: `t${(nextId += 1)}`, role, text, ...extra });

/** "2026-09-04" as a person would say it. */
function said(date) {
  if (!date) return null;
  const parsed = new Date(`${date}T00:00:00Z`);
  if (Number.isNaN(parsed.valueOf())) return date;
  return parsed.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

/**
 * THE ANSWER BASIS, ABOVE THE ANSWER.
 *
 * It sits above the bubble's foot rather than under it, because a reader who
 * learns what kind of claim they have just read only after reading it has
 * learned it too late, and on a phone a long answer's foot can be two
 * screens down.
 *
 * It was once a badge and a disclosure: an uppercase RELEASE-GROUNDED chip,
 * then an "Evidence used" toggle hiding a definition list of Release /
 * Updated / Sources. That is the shape of a compliance widget bolted to a
 * conversation, and a reader has to decode a chip before they learn
 * anything. A sentence does the same job and needs no key.
 *
 * FOUR LINES, FROM TWO AXES. `answerSource` decides which; see
 * `features/grove/cedarAnswer.js` for why that decision is a function and
 * not this component's business. What the four say:
 *
 *   release      read off the collection's release, cited to it, records
 *                offered — the reader can open them.
 *   description  read off the release and cited the same way, records NOT
 *                offered: this subscription does not include the collection,
 *                so there are no records to send them to.
 *   synthesis    Cedar composed it. The SCOPE is real — the question was
 *                asked against this collection — and nothing else is claimed.
 *   review       ambiguous identity, evidence or scope. No producer yet; see
 *                `_answer_basis` in the service for why it is declared anyway.
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
 *
 * Nor does it say how many records an answer cites, for the same reason: a
 * "0 cited records" would read as a count somebody took.
 */
function AnswerSource({ basis }) {
  const line = answerSource(basis);
  if (!line) return null;
  const { tone, release, updated, records } = line;
  const when = said(updated);

  if (tone === "review") {
    return (
      <p className="cp-dc__src cp-dc__src--review">
        This one needs a person. The identity or the scope is unclear, so Cedar has not
        answered it.
      </p>
    );
  }

  // A general answer says so once, briefly, because the alternative is a
  // reader assuming it was read from the release. It does not offer a
  // records link: there are no supporting records to open.
  if (tone === "synthesis") {
    return <p className="cp-dc__src">Not read from {release || "the collections"}.</p>;
  }

  // WHAT A LOCKED COLLECTION'S LINE SAYS, AND WHAT IT WITHHOLDS.
  // The description was read off the release and is cited to it, so the
  // sentence opens the same way. What it must not do is offer the records:
  // the answer above it has just said they open with Cedar Press+, and a
  // "View supporting records" link under that sentence contradicts it in the
  // one place a reader is deciding whether to believe the product. The plan
  // is named in the answer already and is not repeated here.
  if (tone === "description") {
    return (
      <p className="cp-dc__src cp-dc__src--release">
        Based on <b>{release}</b>
        {when ? `, updated ${when}` : ""} &mdash; what the collection is, not its records.
      </p>
    );
  }

  // The source list lived here for one build and it was machinery. A reader
  // trusting an answer wants to know it came from a published release and
  // when; the seven source families behind that release are the collection's
  // business, and the collection's own page says them properly.
  return (
    <p className="cp-dc__src cp-dc__src--release">
      Based on <b>{release}</b>
      {when ? `, updated ${when}` : ""}.{" "}
      {records ? (
        <Link to={`${PRESS_DATA_PATH}?c=${records}`}>View supporting records</Link>
      ) : null}
    </p>
  );
}

// `gated` names why Cedar will not query the collections for this reader:
// "signedout" (no session) or "unentitled" (a membership without Cedar
// Press). Falsy means fully entitled.
export function PressCedarFab({ gated = null, examples = OPEN_EXAMPLES }) {
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

  // ONE LINE, AND IT IS NOT A CAPABILITY LIST.
  //
  // Owner, 2026-09-20: "Do not make Cedar lead with system language, explain
  // its capabilities repeatedly, or show a long technical answer in a narrow
  // right panel." This greeting was a sentence listing three things Cedar can
  // be asked, followed by a second paragraph explaining how it answers and a
  // link to the methodology — an interface introducing itself twice before
  // anybody had said anything. The four suggestions directly below already
  // show what can be asked, better than a list of it can.
  const openingLine = scope ? `Ask me about ${scope.name}.` : "Ask me about any of the collections.";

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
                <p>{connected ? openingLine : "I can't reach the collections from here yet."}</p>
                {connected ? null : (
                  <p className="cp-dc__links">
                    <a href={contactHref("Cedar Press question")}>Send the question to the research desk</a>
                    <a href={appUrl("/app")} target="_blank" rel="noreferrer">Open the platform</a>
                  </p>
                )}
              </div>
            </div>

            {scope ? (
              <p className="cp-dc__scope">
                {/* The header's context line already says which collection
                    this is scoped to. This row repeated it in caps and then
                    offered the way out; only the way out is news. */}
                <button
                  type="button"
                  className="cp-dc__scopeclear"
                  onClick={() => {
                    abortRef.current?.abort();
                    setScope(null);
                    setPending(false);
                  }}
                >
                  Ask about all collections instead
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
                    {/* Under the answer, where a citation goes. */}
                    {item.basis ? <AnswerSource basis={item.basis} /> : null}
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
            {/* Two lines became one. The sentence after it told a reader to
                check an answer against the release it came from — which the
                basis line under every answer already names and links. */}
            Cedar can make mistakes. Check anything important against the release.
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
        {/* THE OWNER MADE THE CALL: this matches teim-app's CedarWidget again.
            The note that used to sit here said the divergence was the owner's
            to settle and not a thing to decide inside a stylesheet. It has
            been settled — one launcher across the product — so the collapse
            to a circle is gone and so is the icon that went with it.
            The icon was a Press gate glyph rather than a Cedar brand asset,
            and `teim-app/src/components/CedarWidget.jsx` carries none: its
            launcher is the dot and the label, which is also what the door's
            own `.cp-dc__fab` shows. Three surfaces, one control. */}
        <span className="cedar-widget__status-dot" aria-hidden="true" />
        <span className="cedar-widget__launcher-copy">
          <span className="cedar-widget__launcher-label">Ask Cedar</span>
          <span className="cedar-widget__launcher-context">Cedar Press</span>
        </span>
      </button>
    </div>
  );
}

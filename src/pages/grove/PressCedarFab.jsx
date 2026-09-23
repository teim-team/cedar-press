// Ask Cedar, from the reader: the same Cedar, in the same panel.
//
// WHAT THIS IS
// The reader's Cedar renders `CedarPanel`, the one panel the door and
// lumecon.ai render too: teal identity band with a status dot, a transcript
// of bubbles with the mark beside Cedar's, quick replies inside that
// transcript, a single-line composer with a send button, one line of
// expectation-setting under it. The conversation is `useCedarThread`, shared
// with the door. A reader who met Cedar on the door and then signed in meets
// the same thing, and it remembers what was just said.
//
// WHAT IS DIFFERENT FROM THE DOOR, DELIBERATELY
// The door never reaches the network: it answers from `doorCedar.js`, by
// design, because it sits in front of the paywall. This one is behind it and
// answers from the service:
//
//   * `POST /cedar/ask` -> the collection's own profile, cited by release,
//     when the question is one a release already answers;
//   * otherwise the Cedar service in the `cedar` repository, over contract
//     1.0.0, the same Cedar teim-app talks to. See
//     `server/cedar_press/cedar_service.py`.
//
// `threadId` rides with every turn after the first, so this is a
// conversation on the service's side too and not a row of isolated
// questions. On this side, the thread's memory does three things the
// service cannot: the quick replies under an answer never re-offer a
// question this thread has already asked, a bare "tell me more" is sent
// with the last question attached so the service knows what "more" is
// about, and a question asked twice is acknowledged as a repeat rather than
// printed cold a second time. The answer-basis line under every answer is a
// product requirement and stays.
//
// THE LAUNCHER IS UNCHANGED, AND THAT IS STILL SOMEBODY'S CALL
// The launcher matches teim-app's; whether it moves is the owner's decision,
// not one to settle in a stylesheet. The panel is the part that had drifted.
import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router";

import { askCedar } from "../../api.js";
import { answerSource } from "../../features/grove/cedarAnswer.js";
import { REPEAT_BRIDGES } from "../../features/grove/cedarConversation.js";
import { appUrl, contactHref } from "../../features/grove/appLink.js";
import { TBN_PLANS_URL } from "../../features/grove/pressArticles.js";
import { PRESS_DATA_PATH } from "../../features/grove/pressRoutes.js";
import { OPEN_EXAMPLES, SCOPED_EXAMPLES, fabFollowUps, isDrillDown, topicOf } from "../../features/grove/readerCedar.js";
import { isConnected } from "../../config.js";
import { EVENT, track, trackError } from "../../features/grove/telemetry.js";
import { useCedarThread } from "../../features/grove/useCedarThread.js";
import { CedarPanel, Paragraphs } from "./CedarPanel";

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
 * THE ANSWER BASIS, UNDER THE ANSWER.
 *
 * FOUR LINES, FROM TWO AXES. `answerSource` decides which; see
 * `features/grove/cedarAnswer.js` for why that decision is a function and
 * not this component's business. What the four say:
 *
 *   release      read off the collection's release, cited to it, records
 *                offered: the reader can open them.
 *   description  read off the release and cited the same way, records NOT
 *                offered: this subscription does not include the collection,
 *                so there are no records to send them to.
 *   synthesis    Cedar composed it. The SCOPE is real (the question was
 *                asked against this collection) and nothing else is claimed.
 *   review       ambiguous identity, evidence or scope. No producer yet; see
 *                `_answer_basis` in the service for why it is declared anyway.
 *
 * WHAT THIS DELIBERATELY DOES NOT RENDER. The brief asks for a cited-record
 * count ("Cedar synthesis from 3 cited records") and an expandable evidence
 * trail of the records used. Cedar returns neither: there is no collections
 * tool and no retrieval, so a synthesis today is grounded in the model, not
 * in this collection's records. Printing a count would be inventing one, and
 * the brief's own scope rule (an answer "may not imply that it understands a
 * particular entity, record, or filtered table state unless that context is
 * actually passed to the service") forbids it. The field is in the contract
 * and renders the moment the service fills it.
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
        {when ? `, updated ${when}` : ""}: what the collection is, not its records.
      </p>
    );
  }

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
  const panelRef = useRef(null);
  const connected = isConnected();

  // The reader's resolver: the service, with the thread's memory around it.
  const resolve = useCallback(
    async (question, { memory, signal, scope: at }) => {
      // On the gate, Cedar is a doorbell, not a side door: a visitor without
      // a session gets told what would answer their question and how to get
      // in, rather than a reply that leaks the collections past the paywall.
      if (signedOut) {
        track(EVENT.cedarAsked, { length: question.length, gated: true });
        return { text: "", kind: "gate", gate: gated };
      }
      // Unscoped, the profiles have nothing to answer from; say so here
      // rather than spending a request on a refusal the client words better.
      if (!at && !connected) {
        return {
          text: "Open a collection and choose “Ask Cedar about this collection”, and the question lands already scoped.",
          kind: "routing",
        };
      }

      // A bare "tell me more" is about the last thing Cedar said. The
      // service sees the question with that topic attached; the reader sees
      // their own words.
      const prior = memory.priorTopic ?? null;
      const drilling = isDrillDown(question) && Boolean(prior);
      const topic = drilling ? prior : topicOf(question, at);
      const sent = drilling ? `${question}: ${prior.chip}` : question;

      try {
        const result = await askCedar({
          question: sent,
          collectionId: at?.id ?? null,
          threadId: threadRef.current,
          pathname: typeof window === "undefined" ? null : window.location.pathname,
          signal,
        });
        if (result?.threadId) threadRef.current = result.threadId;
        track(EVENT.cedarAsked, { length: question.length, collectionId: at?.id ?? null });
        const answer = result?.answer ?? result?.text ?? "";
        // A question asked twice in this thread is acknowledged as a repeat
        // rather than printed cold a second time.
        const seen = memory.answered[topic.id] ?? 0;
        const text = !drilling && seen > 0 ? REPEAT_BRIDGES[(seen - 1) % REPEAT_BRIDGES.length] + answer : answer;
        return {
          text,
          intent: topic,
          kind: drilling ? "drilldown" : seen > 0 ? "repeat" : "answer",
          basis: result?.answerBasis ?? null,
          source: result?.source ?? null,
        };
      } catch (err) {
        if (signal?.aborted) throw err;
        trackError(err, { at: "cedarAsk" });
        return {
          text: "",
          kind: "error",
          error:
            err?.code === "NETWORK"
              ? "Cedar could not be reached. Try again in a moment."
              : err?.message || "Cedar could not answer that.",
        };
      }
    },
    [connected, gated, signedOut],
  );

  // The quick replies are built at the scope the turn was asked at, which
  // rides in the turn's own context rather than in state that may have
  // moved by the time the answer lands.
  const followUpsFor = useCallback(
    (memory, reply, question, { scope: at } = {}) => fabFollowUps(memory, reply, { scope: at ?? null, examples }),
    [examples],
  );

  const { thread, pending, ask, cancel } = useCedarThread({ resolve, followUpsFor });

  useEffect(() => {
    if (open && connected) {
      const frame = requestAnimationFrame(() => inputRef.current?.focus());
      return () => cancelAnimationFrame(frame);
    }
    return undefined;
  }, [open, connected]);

  // Escape closes the panel. The launcher toggles it too, but on phones the
  // browser's own toolbar can sit over the launcher while the panel is open,
  // which left no visible way back out; the panel carries its own close.
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
      // A reader can re-scope mid-flight; the late answer must not land
      // under the new collection's name.
      cancel();
      setScope({ id: next.id, name: next.name });
      // A caller can hand the question over with the scope (the What's New
      // feed asks about a specific release), so the reader arrives with the
      // ask already phrased and only has to send it.
      if (next.q) setAsked(next.q);
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
  }, [cancel]);

  // Every question is asked at an explicit scope, so a chip that sets one
  // does not race the state update. `echo` is what the transcript shows when
  // a chip's label and the question it sends differ.
  const askAt = (question, at, echo) => {
    setAsked("");
    void ask(question, { scope: at, echo });
  };

  const starters = (scope ? SCOPED_EXAMPLES : examples).slice(0, 5).map((example) => {
    const item = typeof example === "string" ? { q: example, scope: null } : { q: example.q, scope: example.scope ?? null };
    // A suggestion that names a collection scopes to it in the same tap, so
    // every suggestion shown is answerable as shown.
    const at = scope ?? item.scope;
    return {
      label: item.scope && !scope ? `${item.q} (${item.scope.name})` : item.q,
      onSelect: () => {
        if (item.scope && !scope) setScope(item.scope);
        askAt(item.q, at);
      },
    };
  });

  const followUps = thread.followUps.map((next) => ({
    label: next.label,
    onSelect: () => {
      const at = scope ?? next.scope ?? null;
      if (next.scope && !scope) setScope(next.scope);
      askAt(next.text, at, next.label);
    },
  }));

  const renderTurn = (item) => (
    <>
      {item.kind === "gate" ? (
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
      ) : item.kind === "error" ? (
        <p role="alert">{item.error}</p>
      ) : (
        <Paragraphs text={item.text} />
      )}
      {/* Under the answer, where a citation goes. */}
      {item.basis ? <AnswerSource basis={item.basis} /> : null}
    </>
  );

  // ONE LINE, AND IT IS NOT A CAPABILITY LIST.
  //
  // Owner, 2026-09-20: "Do not make Cedar lead with system language, explain
  // its capabilities repeatedly, or show a long technical answer in a narrow
  // right panel." The suggestions directly below already show what can be
  // asked, better than a list of it can.
  const openingLine = scope ? `Ask me about ${scope.name}.` : "Ask me about any of the collections.";

  return (
    <div className={`cedar-widget cedar-widget--launcher-only${open ? " cedar-widget--open" : ""}`}>
      {open ? (
        <CedarPanel
          contextLine={scope ? `Cedar Press · ${scope.name}` : "Cedar Press · Questions about the collections"}
          welcome={
            <>
              <p>{connected ? openingLine : "I can't reach the collections from here yet."}</p>
              {connected ? null : (
                <p className="cp-dc__links">
                  <a href={contactHref("Cedar Press question")}>Send the question to the research desk</a>
                  <a href={appUrl("/app")} target="_blank" rel="noreferrer">Open the platform</a>
                </p>
              )}
            </>
          }
          aboveThread={
            scope ? (
              <p className="cp-dc__scope">
                {/* The header's context line already says which collection
                    this is scoped to; only the way out is news. */}
                <button
                  type="button"
                  className="cp-dc__scopeclear"
                  onClick={() => {
                    cancel();
                    setScope(null);
                  }}
                >
                  Ask about all collections instead
                </button>
              </p>
            ) : null
          }
          starters={starters}
          thread={thread}
          pending={pending}
          followUps={followUps}
          renderTurn={renderTurn}
          asked={asked}
          onAsked={setAsked}
          onSubmit={(question) => askAt(question, scope)}
          placeholder={scope ? `Ask about ${scope.name}` : "Ask about a collection"}
          inputDisabled={!connected}
          onClose={() => setOpen(false)}
          panelRef={panelRef}
          inputRef={inputRef}
        />
      ) : null}
      <button
        type="button"
        className="cedar-widget__launcher"
        aria-expanded={open}
        aria-label="Ask Cedar"
        onClick={() => setOpen((current) => !current)}
      >
        {/* THE OWNER MADE THE CALL: this matches teim-app's CedarWidget.
            One launcher across the product, the dot and the label, which is
            also what the door's own `.cp-dc__fab` shows. Three surfaces, one
            control. */}
        <span className="cedar-widget__status-dot" aria-hidden="true" />
        <span className="cedar-widget__launcher-copy">
          <span className="cedar-widget__launcher-label">Ask Cedar</span>
          <span className="cedar-widget__launcher-context">Cedar Press</span>
        </span>
      </button>
    </div>
  );
}

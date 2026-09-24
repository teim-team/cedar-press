// REVIEW OWNER: Havala
//
// Cedar on the door: a floating control and a conversation.
//
// It never reaches the network. `doorCedar.js` says why, and says where the
// twelve dataset answers come from (the catalog, at module load, so they
// cannot drift from the collections they describe). The conversation around
// that bank (memory, drill-downs, repeats, quick replies, the graceful miss)
// is `cedarConversation.js`, shared with the reader's panel through
// `useCedarThread`, and the panel itself is `CedarPanel`, shared the same way.
//
// WHAT IT MAY NOT DO
// Answer past the paywall. Everything it says is either a position about the
// product or a fact the catalog already publishes on this page: coverage, row
// counts, sources, release dates. It holds no records, so it cannot leak one.
//
// WHY IT NO LONGER SAYS "PREPARED MATERIAL"
// The panel used to end with "This page answers from prepared material and
// does not query the collections." The owner read it as a menu of preset
// answers, which is what a panel that announces its mechanism and forgets
// the last question is. It now keeps the thread: "tell me more" goes deeper
// on the last topic, the same question twice gets a deeper or acknowledged
// answer rather than the same paragraph, a question naming two topics gets
// the second as the first quick reply, and a miss offers the closest topics
// it has rather than one fixed refusal. The line under the composer sets the
// same expectation lumecon.ai's does.
//
// The pane's "Ask Cedar" button dispatches `cedar:ask-collection` and the
// hero's dispatches `cedar:open`; both are handled here, so the door's
// buttons work without a prop threaded through three components.
//
// HOW IT BEHAVES, AND WHY IT MATCHES lumecon.ai
// The marketing site's FAB (src/components/CedarFAB.astro) is the reference:
//
//   1. Open is a dock, not a float. The panel pins to the bottom edge of the
//      viewport, the site's 380px wide and its measured height, and a full
//      screen on a phone.
//   2. The launcher steps aside while the panel is open. The panel carries
//      its own close button.
//   3. Starter chips are an opening, not a toolbar. They collapse for good
//      on the first question, and each answer carries at most three next
//      questions under it.
//
// Clicking outside the sheet closes it, as it does there.

import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router";

import { detectAudience } from "../../features/grove/cedarConversation.js";
import {
  DOOR_AUDIENCES,
  DOOR_CHIPS,
  NON_TOPIC_IDS,
  doorFollowUps,
  intentForCollection,
  resolveDoor,
} from "../../features/grove/doorCedar.js";
import { TBN_PLANS_URL } from "../../features/grove/pressArticles";
import { PRESS_METHODS_PATH, PRESS_REQUEST_PATH, PRESS_RESEARCH_PATH } from "../../features/grove/pressRoutes";
import { EVENT, track } from "../../features/grove/telemetry.js";
import { useCedarThread } from "../../features/grove/useCedarThread.js";
import { CedarPanel, Paragraphs } from "./CedarPanel";

/** The routes an answer can offer, by the key an intent names. */
const LINKS = {
  plans: { label: "View plans at Tribal Business News", href: TBN_PLANS_URL, external: true },
  request: { label: "Tribal government data requests", to: PRESS_REQUEST_PATH },
  research: { label: "Research access", to: PRESS_RESEARCH_PATH },
  methods: { label: "Read the methods", to: PRESS_METHODS_PATH },
};

const audienceOf = (question) => detectAudience(DOOR_AUDIENCES, question);

export default function PressDoorCedar() {
  const [open, setOpen] = useState(false);
  const [asked, setAsked] = useState("");
  const panelRef = useRef(null);
  const inputRef = useRef(null);
  const fabRef = useRef(null);

  // The door's resolver is the local bank against the thread's memory. It
  // is synchronous underneath; the hook's pause is what lets a reply read
  // as composed rather than looked up.
  const resolve = useCallback(async (question, { memory, forced }) => {
    const resolution = resolveDoor(memory, question, { forced });
    track(EVENT.cedarAsked, {
      length: question.length,
      gated: true,
      intent: resolution.intent?.id ?? null,
      kind: resolution.kind,
    });
    return resolution;
  }, []);

  const { thread, pending, ask, cancel } = useCedarThread({
    resolve,
    followUpsFor: doorFollowUps,
    nonTopicIds: NON_TOPIC_IDS,
    detectAudience: audienceOf,
  });

  // The launcher is hidden while the panel is open, so an explicit close has
  // to hand focus back to it once it is on the page again.
  //
  // `restoreFocus` is false for a click outside the sheet. Codex, PR #80: the
  // browser is about to focus whatever was clicked, and the queued frame would
  // then pull focus off it and onto the launcher, so dismissing the sheet
  // would eat the click that dismissed it, and the reader would have to click
  // the field a second time. A dismissal leaves focus where the pointer put it.
  const close = useCallback((restoreFocus = true) => {
    const returning = restoreFocus && panelRef.current?.contains(document.activeElement);
    setOpen(false);
    if (returning) requestAnimationFrame(() => fabRef.current?.focus());
  }, []);

  // The hero and the pane both hand questions over.
  useEffect(() => {
    const onOpen = () => setOpen(true);
    const onCollection = (event) => {
      const detail = event?.detail;
      if (!detail?.id) return;
      const intent = intentForCollection(detail.id);
      setOpen(true);
      // A turn may still be composing (the pause lasts up to 1.6s, and the
      // panel may have been closed over it). The reader has asked for a
      // collection now; that request replaces the one in flight rather
      // than being dropped at the hook's one-at-a-time guard.
      cancel();
      if (intent) void ask(`What is in ${detail.name ?? intent.chip}?`, { forced: intent });
    };
    window.addEventListener("cedar:open", onOpen);
    window.addEventListener("cedar:ask-collection", onCollection);
    return () => {
      window.removeEventListener("cedar:open", onOpen);
      window.removeEventListener("cedar:ask-collection", onCollection);
    };
  }, [ask, cancel]);

  // Escape closes, a click outside closes, and the panel takes focus when it
  // opens. The outside click is captured on pointerdown so a chip that
  // re-renders the thread under the pointer cannot be mistaken for one.
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event) => { if (event.key === "Escape") close(); };
    const onOutside = (event) => {
      const panel = panelRef.current;
      if (!panel) return;
      if (panel.contains(event.target) || fabRef.current?.contains(event.target)) return;
      close(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onOutside);
    const frame = requestAnimationFrame(() => inputRef.current?.focus());
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onOutside);
      cancelAnimationFrame(frame);
    };
  }, [open, close]);

  const submit = (question) => {
    setAsked("");
    void ask(question);
  };

  // A chip is an explicit choice of intent: it routes straight to that
  // answer rather than re-classifying its own label.
  const askChip = (intent) => {
    setAsked("");
    void ask(intent.chip, { forced: intent });
  };

  const starters = DOOR_CHIPS.slice(0, 5).map((intent) => ({ label: intent.chip, onSelect: () => askChip(intent) }));
  const followUps = thread.followUps.map((next) => ({
    label: next.label,
    onSelect: () => {
      setAsked("");
      // The transcript shows the chip's own words; the bank sees its text.
      void ask(next.text, { echo: next.label, forced: next.intent ?? null });
    },
  }));

  // A bot turn: its paragraphs, and under an answer that has somewhere to
  // send the reader, the route. An internal route stays inside the app; a
  // full reload would throw the conversation away.
  const renderTurn = (item) => (
    <>
      <Paragraphs text={item.text} />
      {item.kind !== "drilldown" && item.intent?.links?.length ? (
        <p className="cp-dc__links">
          {item.intent.links.map((key) => {
            const link = LINKS[key];
            if (!link) return null;
            return link.external ? (
              <a key={key} href={link.href} target="_blank" rel="noreferrer">{link.label}</a>
            ) : (
              <Link key={key} to={link.to} onClick={() => close(false)}>{link.label}</Link>
            );
          })}
        </p>
      ) : null}
    </>
  );

  return (
    <div className={`cp-dc${open ? " is-open" : ""}`}>
      {open ? (
        <CedarPanel
          contextLine="Cedar Press · Questions about the collections"
          welcome={
            <p>
              Hi, I'm Cedar. Ask me what any collection holds, where the records come from, how they
              reach the right nation, or how to get access. Pick a question or type your own.
            </p>
          }
          starters={starters}
          thread={thread}
          pending={pending}
          followUps={followUps}
          renderTurn={renderTurn}
          asked={asked}
          onAsked={setAsked}
          onSubmit={submit}
          placeholder="Ask about a collection"
          onClose={() => close()}
          panelRef={panelRef}
          inputRef={inputRef}
        />
      ) : null}

      <button
        type="button"
        ref={fabRef}
        className="cp-dc__fab"
        onClick={() => (open ? close() : setOpen(true))}
        aria-expanded={open}
      >
        <span className="cp-dc__statusdot" aria-hidden="true" />
        <span className="cp-dc__fabid">
          <b>Ask Cedar</b>
          <small>Cedar Press</small>
        </span>
      </button>
    </div>
  );
}

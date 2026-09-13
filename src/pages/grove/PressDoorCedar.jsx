// REVIEW OWNER: Havala
//
// Cedar on the door: a floating control and a panel of prepared answers.
//
// It never reaches the network. `doorCedar.js` says why, and says where the
// twelve dataset answers come from (the catalog, at module load, so they
// cannot drift from the collections they describe).
//
// WHAT IT MAY NOT DO
// Answer past the paywall. Everything it says is either a position about the
// product or a fact the catalog already publishes on this page — coverage,
// row counts, sources, release dates. It holds no records, so it cannot leak
// one, and the panel says "prepared answers" on its face rather than
// implying a model is thinking.
//
// The pane's "Ask Cedar" button dispatches `cedar:ask-collection` and the
// hero's dispatches `cedar:open`; both are handled here, so the door's
// buttons work without a prop threaded through three components.
//
// HOW IT BEHAVES, AND WHY IT MATCHES lumecon.ai
// The marketing site's FAB (src/components/CedarFAB.astro) is the reference,
// and three of its rules were missing here:
//
//   1. Open is a dock, not a float. The panel pins to the bottom edge of the
//      viewport — a full-width sheet on a phone — instead of hovering as a
//      card above the launcher, which on an 844px screen left it stranded
//      mid-air with page showing underneath.
//   2. The launcher steps aside while the panel is open. The panel carries
//      its own close button; two close affordances and a FAB covering the
//      sheet's own corner is the worse arrangement.
//   3. Starter chips are an opening, not a toolbar. They collapse for good
//      on the first question, and each answer carries at most three next
//      questions under it (`followUpsFor`). Re-printing the whole stack under
//      every reply read as a control panel that had not been listening.
//
// Clicking outside the sheet closes it, as it does there.

import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router";

import { DOOR_CHIPS, answer as answerFor, followUpsFor, intentForCollection } from "../../features/grove/doorCedar.js";
import { TBN_PLANS_URL } from "../../features/grove/pressArticles";
import { PRESS_METHODS_PATH, PRESS_REQUEST_PATH, PRESS_RESEARCH_PATH } from "../../features/grove/pressRoutes";
import { EVENT, track } from "../../features/grove/telemetry.js";

const MARK = "/brand/lumecon-logo-mark-teal.png";

/** The routes an answer can offer, by the key an intent names. */
const LINKS = {
  plans: { label: "View plans at Tribal Business News", href: TBN_PLANS_URL, external: true },
  request: { label: "Tribal government data requests", to: PRESS_REQUEST_PATH },
  research: { label: "Research access", to: PRESS_RESEARCH_PATH },
  methods: { label: "Read the methods", to: PRESS_METHODS_PATH },
};

let nextId = 0;
const turn = (role, intent, text) => ({ key: `t${(nextId += 1)}`, role, intent, text });

export default function PressDoorCedar() {
  const [open, setOpen] = useState(false);
  const [asked, setAsked] = useState("");
  const [thread, setThread] = useState([]);
  const panelRef = useRef(null);
  const inputRef = useRef(null);
  const fabRef = useRef(null);
  const endRef = useRef(null);

  const say = useCallback((question, intent) => {
    setThread((prev) => [...prev, turn("you", null, question), turn("cedar", intent, intent.answer)]);
    track(EVENT.cedarAsked, { length: question.length, gated: true, intent: intent.id });
  }, []);

  // The launcher is hidden while the panel is open, so closing has to hand
  // focus back to it once it is on the page again.
  const close = useCallback(() => {
    const returning = panelRef.current?.contains(document.activeElement);
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
      if (intent) say(`What is in ${detail.name ?? intent.chip}?`, intent);
    };
    window.addEventListener("cedar:open", onOpen);
    window.addEventListener("cedar:ask-collection", onCollection);
    return () => {
      window.removeEventListener("cedar:open", onOpen);
      window.removeEventListener("cedar:ask-collection", onCollection);
    };
  }, [say]);

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
      close();
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

  // A new turn scrolls into view inside the panel, never the page.
  useEffect(() => {
    if (thread.length) endRef.current?.scrollIntoView({ block: "nearest" });
  }, [thread]);

  const submit = (event) => {
    event.preventDefault();
    const question = asked.trim();
    if (!question) return;
    setAsked("");
    say(question, answerFor(question));
  };

  const askChip = (intent) => {
    setAsked("");
    say(intent.chip, intent);
  };

  // Everything the conversation has already answered. It keeps a follow-up
  // from offering a question that is already sitting in the thread.
  const answered = new Set(thread.filter((t) => t.role === "cedar").map((t) => t.intent?.id));
  // The starter stack belongs to the empty panel. Once a question has been
  // asked it is gone, and the next questions ride under the last answer.
  const starters = thread.length ? [] : DOOR_CHIPS.slice(0, 5);
  const last = thread.length ? thread[thread.length - 1] : null;
  const nextUp = last?.role === "cedar" ? followUpsFor(last.intent, answered) : [];

  return (
    <div className={`cp-dc${open ? " is-open" : ""}`}>
      {open ? (
        <section className="cp-dc__panel" ref={panelRef} role="dialog" aria-label="Ask Cedar">
          {/* The identity band the app and lumecon.ai both use: status dot,
              uppercase title, context line, all white on the one teal that
              carries white text. */}
          <header className="cp-dc__head">
            <span className="cp-dc__heading">
              <span className="cp-dc__titlerow">
                <span className="cp-dc__statusdot" aria-hidden="true" />
                <span className="cp-dc__title">Ask Cedar</span>
              </span>
              <span className="cp-dc__context">Cedar Press · Questions about the collections</span>
            </span>
            <button type="button" className="cp-dc__close" onClick={close} aria-label="Close Cedar">
              <span aria-hidden="true">&times;</span>
            </button>
          </header>

          <div className="cp-dc__thread" role="log" aria-live="polite">
            <div className="cp-dc__msg cp-dc__msg--bot">
              <span className="cp-dc__avatar" aria-hidden="true">
                <img src={MARK} alt="" width="30" height="30" />
              </span>
              <div className="cp-dc__bubble">
                <p>
                  I can tell you what each collection holds, where the records come from, how they
                  reach the right nation, and how to get access. Pick a question or type your own.
                </p>
              </div>
            </div>
            {starters.length ? (
              <div className="cp-dc__quickreply">
                {starters.map((intent) => (
                  <button type="button" key={intent.id} className="cp-dc__chip" onClick={() => askChip(intent)}>
                    {intent.chip}
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
                    {item.text.split("\n\n").map((para, i) => <p key={i}>{para}</p>)}
                    {item.intent?.links?.length ? (
                      <p className="cp-dc__links">
                        {item.intent.links.map((key) => {
                          const link = LINKS[key];
                          if (!link) return null;
                          // An internal route stays inside the app; a full
                          // reload would throw the conversation away.
                          return link.external ? (
                            <a key={key} href={link.href} target="_blank" rel="noreferrer">{link.label}</a>
                          ) : (
                            <Link key={key} to={link.to} onClick={close}>{link.label}</Link>
                          );
                        })}
                      </p>
                    ) : null}
                  </div>
                </div>
              ),
            )}
            {nextUp.length ? (
              <div className="cp-dc__followups" role="group" aria-label="Suggested next questions">
                {nextUp.map((intent) => (
                  <button type="button" key={intent.id} className="cp-dc__follow" onClick={() => askChip(intent)}>
                    {intent.chip}
                  </button>
                ))}
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
                placeholder="Ask about a collection"
                onChange={(event) => setAsked(event.target.value)}
              />
            </label>
            <button type="submit" className="cp-dc__send" disabled={!asked.trim()} aria-label="Send">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M4 12h15M13 6l6 6-6 6" />
              </svg>
            </button>
          </form>
          {/* The one line of expectation-setting the panel owes its reader,
              in the same place and the same words the marketing site uses. */}
          <p className="cp-dc__disclaimer">
            Cedar can make mistakes. Verify anything important against the methods page or the
            release it came from. This page answers from prepared material and does not query the
            collections.
          </p>
        </section>
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

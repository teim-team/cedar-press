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

import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router";

import {
  DOOR_CHIPS,
  DOOR_INTENTS,
  answer as answerFor,
  intentForCollection,
} from "../../features/grove/doorCedar.js";
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
  const endRef = useRef(null);

  const say = useCallback((question, intent) => {
    setThread((prev) => [...prev, turn("you", null, question), turn("cedar", intent, intent.answer)]);
    track(EVENT.cedarAsked, { length: question.length, gated: true, intent: intent.id });
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

  // Escape closes; the panel takes focus when it opens.
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event) => { if (event.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", onKey);
    const frame = requestAnimationFrame(() => inputRef.current?.focus());
    return () => {
      document.removeEventListener("keydown", onKey);
      cancelAnimationFrame(frame);
    };
  }, [open]);

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

  // Chips narrow as the conversation goes: the ones already asked drop out.
  const used = new Set(thread.filter((t) => t.role === "cedar").map((t) => t.intent?.id));
  const chips = DOOR_CHIPS.filter((intent) => !used.has(intent.id));

  return (
    <div className="cp-dc">
      {open ? (
        <section className="cp-dc__panel" ref={panelRef} aria-label="Ask Cedar">
          <header className="cp-dc__head">
            <span className="cp-dc__id">
              <img className="cp-dc__mark" src={MARK} alt="" aria-hidden="true" />
              <span>
                <b>Ask Cedar</b>
                {/* Said plainly. A visitor should not have to work out
                    whether a model is answering. */}
                <small>Prepared answers about Cedar Press</small>
              </span>
            </span>
            <button type="button" className="cp-dc__close" onClick={() => setOpen(false)} aria-label="Close Cedar">
              <span aria-hidden="true">&times;</span>
            </button>
          </header>

          <div className="cp-dc__thread" role="log" aria-live="polite">
            <div className="cp-dc__turn cp-dc__turn--cedar">
              <p>
                I can tell you what each of the collections holds, where the records come from, how they
                are linked to nations, and how to get access. Pick a question or type your own.
              </p>
            </div>
            {thread.map((item) =>
              item.role === "you" ? (
                <div className="cp-dc__turn cp-dc__turn--you" key={item.key}>
                  <p>{item.text}</p>
                </div>
              ) : (
                <div className="cp-dc__turn cp-dc__turn--cedar" key={item.key}>
                  {item.text.split("\n\n").map((para, i) => <p key={i}>{para}</p>)}
                  {item.intent?.links?.length ? (
                    <p className="cp-dc__links">
                      {item.intent.links.map((key) => {
                        const link = LINKS[key];
                        if (!link) return null;
                        // An internal route stays inside the app; a full
                        // reload here would throw the conversation away.
                        return link.external ? (
                          <a key={key} href={link.href} target="_blank" rel="noreferrer">{link.label} &#8594;</a>
                        ) : (
                          <Link key={key} to={link.to} onClick={() => setOpen(false)}>{link.label} &#8594;</Link>
                        );
                      })}
                    </p>
                  ) : null}
                </div>
              ),
            )}
            <div ref={endRef} />
          </div>

          {chips.length ? (
            <div className="cp-dc__chips">
              {chips.slice(0, 6).map((intent) => (
                <button type="button" key={intent.id} className="cp-dc__chip" onClick={() => askChip(intent)}>
                  {intent.chip}
                </button>
              ))}
            </div>
          ) : null}

          <form className="cp-dc__form" onSubmit={submit} autoComplete="off">
            <label className="cp-dc__field">
              <span className="cp-badge__sr">Ask Cedar a question</span>
              <input
                ref={inputRef}
                type="text"
                value={asked}
                placeholder="Ask about a collection…"
                onChange={(event) => setAsked(event.target.value)}
              />
            </label>
            <button type="submit" className="cp-btn cp-btn--primary" disabled={!asked.trim()}>
              Ask
            </button>
          </form>
        </section>
      ) : null}

      <button
        type="button"
        className={`cp-dc__fab${open ? " is-open" : ""}`}
        onClick={() => setOpen((was) => !was)}
        aria-expanded={open}
      >
        <span className="cp-dc__dot" aria-hidden="true" />
        <span className="cp-dc__fabid">
          <b>Ask Cedar</b>
          <small>{DOOR_INTENTS.length} prepared answers</small>
        </span>
      </button>
    </div>
  );
}
